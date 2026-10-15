"""诊断 DashScope/豆包 调用失败原因（不回显完整 key）"""

import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request

API = r"E:\output\1\api"
sys.path.insert(0, API)
os.chdir(API)

print("=" * 78)
print("1) 当前 DashScope key 的来源与指纹")
print("=" * 78)
env_path = os.path.join(API, ".env")
if os.path.exists(env_path):
    txt = open(env_path, encoding="utf-8").read()
    m = re.search(r"DASHSCOPE_API_KEY\s*=\s*(\S+)", txt)
    if m:
        k = m.group(1)
        print(f"  .env 中的 DASHSCOPE_API_KEY: len={len(k)} fp={k[:6]}...{k[-4:]} "
              f"sha12={hashlib.sha256(k.encode()).hexdigest()[:12]}")
    else:
        print("  .env 中未找到 DASHSCOPE_API_KEY")

cfg = os.path.join(API, "config_runtime.json")
j = json.load(open(cfg, encoding="utf-8"))
ds = (j.get("dashscope") or {}).get("api_key", "")
print(f"  config_runtime.json dashscope.api_key: {'(空)' if not ds else f'len={len(ds)} fp={ds[:6]}...{ds[-4:]}'}")

print()
print("=" * 78)
print("2) 导入 config 后实际生效的 key")
print("=" * 78)
import config as C  # noqa: E402

k = C.Config.DASHSCOPE_API_KEY or ""
print(f"  Config.DASHSCOPE_API_KEY: len={len(k)} fp={k[:6]}...{k[-4:]} sha12="
      f"{hashlib.sha256(k.encode()).hexdigest()[:12] if k else '-'}")

print()
print("=" * 78)
print("3) 用该 key 实际调用 DashScope（验证真假）")
print("=" * 78)
if not k:
    print("  key 为空，无法测试")
else:
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    body = {
        "model": "qwen-vl-plus",
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 5,
    }
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"  HTTP {r.status} -> key 有效")
            print("  " + r.read().decode("utf-8", "ignore")[:200])
    except urllib.error.HTTPError as e:
        body_txt = e.read().decode("utf-8", "ignore")
        print(f"  HTTP {e.code} -> key 无效或权限不足")
        print("  " + body_txt[:400])

print()
print("=" * 78)
print("4) 项目里豆包调用用的是哪个函数/端点")
print("=" * 78)
ir = open(os.path.join(API, "image_recognizer.py"), encoding="utf-8").read()
for pat in (r"def analyze_with_doubao", r"dashscope\.", r"compatible-mode",
            r"dashscope\.aliyuncs\.com[^\s\"']*", r"model\s*=\s*['\"][^'\"]+['\"]"):
    hits = list(dict.fromkeys(re.findall(pat, ir)))
    if hits:
        print(f"  {pat}: {hits[:5]}")
