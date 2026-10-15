"""复现豆包调用失败：用与项目完全相同的 dashscope 调用方式"""

import os
import sys

API = r"E:\output\1\api"
sys.path.insert(0, API)
os.chdir(API)

import config as C  # noqa: E402

KEY = C.Config.DASHSCOPE_API_KEY
print(f"key: len={len(KEY)} fp={KEY[:6]}...{KEY[-4:]}")

import dashscope  # noqa: E402

dashscope.api_key = KEY

# 极小的 1x1 红色 PNG（base64），避免依赖测试图片
TINY = ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAF"
        "BQH/qZ9wCQAAAABJRU5ErkJggg==")
img_uri = "data:image/png;base64," + TINY

messages = [{
    "role": "user",
    "content": [
        {"image": img_uri},
        {"text": "这是什么颜色？只回答颜色。"},
    ],
}]

print("=" * 74)
print("测试 1：项目使用的 model = qwen3-vl-flash")
print("=" * 74)
try:
    r = dashscope.MultiModalConversation.call(model="qwen3-vl-flash",
                                              messages=messages, timeout=30)
    print("  status_code:", r.status_code)
    print("  code:", getattr(r, "code", None))
    print("  message:", str(getattr(r, "message", None))[:300])
    if r.status_code == 200:
        try:
            print("  content:", r.output.choices[0].message.content)
        except Exception as e:
            print("  解析输出失败:", e)
except Exception as e:
    print("  抛出异常:", type(e).__name__, str(e)[:400])

print()
print("=" * 74)
print("测试 2：对照 model = qwen-vl-plus（已知可用）")
print("=" * 74)
try:
    r2 = dashscope.MultiModalConversation.call(model="qwen-vl-plus",
                                               messages=messages, timeout=30)
    print("  status_code:", r2.status_code)
    print("  code:", getattr(r2, "code", None))
    print("  message:", str(getattr(r2, "message", None))[:200])
    if r2.status_code == 200:
        print("  content:", str(r2.output.choices[0].message.content)[:200])
except Exception as e:
    print("  抛出异常:", type(e).__name__, str(e)[:300])

print()
print("=" * 74)
print("测试 3：列出该账号可用的多模态模型（compatible-mode /models）")
print("=" * 74)
import json  # noqa: E402
import urllib.request  # noqa: E402

try:
    req = urllib.request.Request(
        "https://dashscope.aliyuncs.com/compatible-mode/v1/models",
        headers={"Authorization": f"Bearer {KEY}"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        j = json.loads(resp.read().decode("utf-8", "ignore"))
        ids = [m.get("id") for m in j.get("data", [])]
        vl = sorted([i for i in ids if i and "vl" in i.lower()])
        print(f"  模型总数: {len(ids)}  其中 VL 类: {len(vl)}")
        for i in vl[:25]:
            print("    -", i)
except Exception as e:
    print("  查询失败:", type(e).__name__, str(e)[:200])
