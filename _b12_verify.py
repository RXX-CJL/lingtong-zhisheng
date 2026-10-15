"""B1/B2 独立验证脚本 v2（零安装，不依赖 pytest，不联网）

v1 失败原因：测试脚本自身 bug——
  1) 未给实例设置 claude_api_key，方法在 `if not self.claude_api_key: return {}` 处早退；
  2) `_analyze_event_with_claude` 第一参是 `frames: List`，v1 传了裸字符串。

v2 修正：显式设置 key + 传 list + patch 掉 key 获取函数（避免真实网络/凭据判断）。
原理不变：autospec=True 让 mock 强制校验"调用点实参 ↔ 真实签名"。

用法：E:\\output\\1\\.venv\\Scripts\\python.exe E:\\output\\_b12_verify.py
"""

import os
import sys
import base64
import inspect
from unittest.mock import patch

API_DIR = r"E:\output\1\api"
sys.path.insert(0, API_DIR)
os.chdir(API_DIR)

import numpy as np  # noqa: E402
import cv2  # noqa: E402
import image_recognizer as ir  # noqa: E402
import cloud_collaborator as cc  # noqa: E402

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(f"{name}{(' — ' + detail) if detail else ''}")
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))


def body(src):
    """去掉注释行后的源码，避免把'修复说明注释'误当实现"""
    return "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))


print("=" * 74)
print("1) 真实签名（源码事实）")
print("=" * 74)
sig_c = inspect.signature(ir.analyze_with_claude)
sig_d = inspect.signature(ir.analyze_with_deepseek_judge)
print(f"  analyze_with_claude         {sig_c}")
print(f"  analyze_with_deepseek_judge {sig_d}")
check("analyze_with_claude 为 3 参", len(sig_c.parameters) == 3, str(list(sig_c.parameters)))
check("analyze_with_deepseek_judge 为 3 参", len(sig_d.parameters) == 3, str(list(sig_d.parameters)))

print()
print("=" * 74)
print("2) 事件闭环调用点（autospec 强制校验实参）")
print("=" * 74)

# 构造一个真实 JPEG 帧（走 hasattr(frame,'shape') 分支）
frame = np.zeros((32, 32, 3), dtype=np.uint8)
ok, buf = cv2.imencode(".jpg", frame)
assert ok
frames = [frame]          # v2 修正：传 list

DOUBAO = {"success": True, "is_violation": True, "confidence_adjusted": 0.9,
          "result_text": "doubao ok", "message": "m"}
CLAUDE_RES = {"success": True, "is_violation": True, "confidence_adjusted": 0.88,
              "result_text": "claude ok", "message": "m"}
DEEPSEEK_RES = {"success": True, "is_violation_confirmed": True, "confidence_adjusted": 0.91,
                "result_text": "deepseek ok", "message": "m", "risk_level": "medium"}

collab = cc.CloudCollaborator()
collab.claude_api_key = "test-key-not-real"   # v2 修正：绕过 key 早退

with patch.object(ir, "_get_deepseek_key", return_value="test-key-not-real"), \
     patch.object(ir, "analyze_with_claude", autospec=True, return_value=dict(CLAUDE_RES)) as m1:
    out1 = collab._analyze_event_with_claude(frames, "illegal_parking", "ctx")
    a1 = m1.call_args.args if m1.call_args else ()
    check("B1 mock 被调用（真实走到云端调用点）", bool(m1.call_args))
    check("B1 传入 3 个实参", len(a1) == 3, f"args={a1}")
    if len(a1) == 3:
        check("B1 第 2 参是事件类型字符串", a1[1] == "illegal_parking", repr(a1[1]))
        check("B1 第 3 参是 context_prompt", a1[2] == "ctx", repr(a1[2]))
    check("B1 拿到真实结果（非静默降级 {}）",
          bool(out1) and out1.get("success") is True, f"success={out1.get('success') if out1 else None}")

with patch.object(ir, "analyze_with_deepseek_judge", autospec=True,
                  return_value=dict(DEEPSEEK_RES)) as m2:
    out2 = collab._analyze_event_with_deepseek(
        DOUBAO, CLAUDE_RES, "illegal_parking", "ctx",
        {"success": True, "confidence": 0.8,
         "detections": [{"class_name": "car", "confidence": 0.8}]})
    a2 = m2.call_args.args if m2.call_args else ()
    check("B2 mock 被调用（真实走到云端调用点）", bool(m2.call_args))
    check("B2 传入 3 个实参", len(a2) == 3, f"args={a2}")
    if len(a2) == 3:
        check("B2 第 1 参是事件类型字符串", a2[0] == "illegal_parking", repr(a2[0]))
        check("B2 第 2 参是结构化 dict（含 success/detections）",
              isinstance(a2[1], dict) and "success" in a2[1] and "detections" in a2[1],
              f"keys={list(a2[1].keys()) if isinstance(a2[1], dict) else type(a2[1]).__name__}")
        check("B2 第 3 参是主视觉结果 dict", isinstance(a2[2], dict),
              type(a2[2]).__name__)
    check("B2 拿到真实结果（非 _empty_ai_result 降级）",
          bool(out2) and out2.get("success") is True, f"success={out2.get('success') if out2 else None}")

print()
print("=" * 74)
print("3) 优雅降级是否保留（交接报告要求：对齐参数，不删 try/except）")
print("=" * 74)
s1 = body(inspect.getsource(cc.CloudCollaborator._analyze_event_with_claude))
s2 = body(inspect.getsource(cc.CloudCollaborator._analyze_event_with_deepseek))
check("B1 保留 try/except 降级", "except Exception" in s1 and "return {}" in s1)
check("B2 保留 try/except 降级", "except Exception" in s2 and "_empty_ai_result" in s2)
check("B1 降级时记 warning 日志（可观测）", "logger.warning" in s1)
check("B2 降级时记 error 日志（可观测）", "logger.error" in s2)

print()
print("=" * 74)
print(f"结果：PASS {len(PASS)} / FAIL {len(FAIL)}")
if FAIL:
    print("失败项：")
    for f in FAIL:
        print("   -", f)
print("=" * 74)
sys.exit(1 if FAIL else 0)
