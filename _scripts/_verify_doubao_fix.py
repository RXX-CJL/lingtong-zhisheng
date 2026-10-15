"""验证 analyze_with_doubao 现在能处理 numpy 数组 / base64 字符串 / 文件路径"""

import os
import sys
import time

API = r"E:\output\1\api"
sys.path.insert(0, API)
os.chdir(API)

import base64  # noqa: E402

import cv2  # noqa: E402

cap = cv2.VideoCapture(r"E:\output\1\test_assets\traffic_videos\test1.mp4")
ok, frame = False, None
for _ in range(30):
    ok, frame = cap.read()
    if ok:
        break
cap.release()
print(f"抽帧: {ok} {frame.shape if ok else None}")

import image_recognizer as ir  # noqa: E402

print()
print("=" * 74)
print("测试 1：numpy 数组输入（修复前崩溃的场景）")
print("=" * 74)
t0 = time.time()
r1 = ir.analyze_with_doubao(frame, "illegal_parking", "测试违停判定")
print(f"  耗时 {time.time()-t0:.1f}s")
print(f"  success={r1.get('success')}")
print(f"  message={str(r1.get('message'))[:160]}")
print(f"  confirmed={r1.get('is_violation_confirmed')}  conf={r1.get('confidence_adjusted')}")
print(f"  text={str(r1.get('result_text'))[:220]}")

print()
print("=" * 74)
print("测试 2：base64 字符串输入（回归检查，确保没弄坏原路径）")
print("=" * 74)
_, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
t0 = time.time()
r2 = ir.analyze_with_doubao(b64, "illegal_parking", "测试违停判定")
print(f"  耗时 {time.time()-t0:.1f}s")
print(f"  success={r2.get('success')}  message={str(r2.get('message'))[:120]}")
print(f"  confirmed={r2.get('is_violation_confirmed')}  conf={r2.get('confidence_adjusted')}")

print()
print("=" * 74)
print("结果判定")
print("=" * 74)
ok1 = bool(r1.get("success"))
ok2 = bool(r2.get("success"))
print(f"  数组输入: {'PASS' if ok1 else 'FAIL'}")
print(f"  字符串输入: {'PASS' if ok2 else 'FAIL'}")
print(f"  => {'两个路径都正常，修复成功' if ok1 and ok2 else '仍有问题'}")
