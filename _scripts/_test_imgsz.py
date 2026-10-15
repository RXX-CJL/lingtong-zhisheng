"""对照实验：提高 YOLO 推理分辨率能否检出红绿灯

假设：原图 960x432 被下采样到 288x640，远处小目标（红绿灯）消失。
验证：imgsz=640 vs 1280 vs 1920 三种设置下的红绿灯检出数。
"""

import os
import sys
import time

API = r"E:\output\1\api"
sys.path.insert(0, API)
os.chdir(API)

import cv2  # noqa: E402
from ultralytics import YOLO  # noqa: E402

VIDEO = r"E:\output\1\test_assets\traffic_videos\test1.mp4"
MODEL = r"E:\output\1\zhitong\training\models\yolov8s.pt"

# 取 3 帧有代表性的画面（含路口远景）
FRAMES = [0, 150, 300]

cap = cv2.VideoCapture(VIDEO)
frames = {}
for fi in FRAMES:
    cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
    ok, f = cap.read()
    if ok:
        frames[fi] = f
cap.release()
print(f"取到 {len(frames)} 帧，尺寸 {list(frames.values())[0].shape}")

m = YOLO(MODEL)

print()
print("=" * 76)
print("不同 imgsz 下的检出统计（关注 traffic light）")
print("=" * 76)
print(f"{'imgsz':>7} | {'帧':>5} | {'总检出':>6} | {'红绿灯':>7} | {'推理ms':>7}")
print("-" * 76)

for imgsz in (640, 960, 1280, 1920):
    for fi, frame in frames.items():
        t0 = time.time()
        r = m.predict(frame, imgsz=imgsz, conf=0.25, verbose=False, device=0)[0]
        ms = (time.time() - t0) * 1000
        names = m.names
        boxes = r.boxes
        n = len(boxes) if boxes is not None else 0
        tl = 0
        for b in (boxes or []):
            cls = names.get(int(b.cls[0]), "") if isinstance(names, dict) else names[int(b.cls[0])]
            if "traffic light" in str(cls).lower():
                tl += 1
        print(f"{imgsz:>7} | {fi:>5} | {n:>6} | {tl:>7} | {ms:>7.1f}")

print()
print("=" * 76)
print("若高 imgsz 下 traffic light > 0，说明是分辨率问题（可修）")
print("若始终为 0，说明该视频中红绿灯确实不可检（需换模型/数据）")
print("=" * 76)
