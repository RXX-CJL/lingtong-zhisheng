"""用真实视频帧直接调用项目的 analyze_with_doubao，拿到真实错误"""

import os
import sys
import time

API = r"E:\output\1\api"
sys.path.insert(0, API)
os.chdir(API)

import cv2  # noqa: E402
import numpy as np  # noqa: E402

# 从测试视频抽一帧真实画面
cap = cv2.VideoCapture(r"E:\output\1\test_assets\traffic_videos\test1.mp4")
ok = False
frame = None
for _ in range(30):
    ok, frame = cap.read()
    if ok:
        break
cap.release()
print("抽帧:", ok, frame.shape if ok else None)

import image_recognizer as ir  # noqa: E402

print()
print("=" * 74)
print("直接调用 analyze_with_doubao（项目真实函数）")
print("=" * 74)
t0 = time.time()
try:
    r = ir.analyze_with_doubao(frame, "illegal_parking", "测试：请判断是否违停")
    print(f"  耗时: {time.time()-t0:.1f}s")
    print(f"  返回类型: {type(r)}")
    if isinstance(r, dict):
        for k in ("success", "message", "result_text", "is_violation_confirmed",
                  "confidence_adjusted", "error", "prompt"):
            if k in r:
                v = str(r[k])
                print(f"    {k}: {v[:220]}")
    else:
        print("   ", str(r)[:400])
except Exception as e:
    print(f"  抛出异常: {type(e).__name__}: {str(e)[:400]}")

print()
print("=" * 74)
print("检查 DASHSCOPE_AVAILABLE 与 SDK 版本")
print("=" * 74)
print("  DASHSCOPE_AVAILABLE:", getattr(ir, "DASHSCOPE_AVAILABLE", "?"))
try:
    import dashscope
    print("  dashscope 版本:", getattr(dashscope, "__version__", "?"))
except Exception as e:
    print("  dashscope 导入失败:", e)
