"""验证假设：所谓"颜色分类模型"其实是"直接检测三种颜色的检测器"

若成立，则可用它一步完成 检测+判色（优于两阶段管线）。
"""

import glob
import os
import sys

API = r"E:\output\1\api"
sys.path.insert(0, API)
os.chdir(API)

import cv2  # noqa: E402
from ultralytics import YOLO  # noqa: E402

CLS_AS_DET = glob.glob(r"E:\output\_models_dl\traffic_light_color*\**\weights\best.pt", recursive=True)[0]
DET = glob.glob(r"E:\output\_models_dl\traffic_light_detection*\**\weights\best.pt", recursive=True)[0]
VIDEO = r"E:\output\1\test_assets\traffic_videos\ea1ca6cbb27653af24ebe585d56f0ffd.mp4"

print("=" * 78)
print("A) 把颜色模型当作检测器用（1x84 输出 -> 检测结果）")
print("=" * 78)
m = YOLO(CLS_AS_DET, task="detect")
print(f"  names: {m.names}")

cap = cv2.VideoCapture(VIDEO)
total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
for fi in (0, 41, 82, 123, 164, 205):
    cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
    ok, frame = cap.read()
    if not ok:
        continue
    for conf in (0.05, 0.10, 0.25):
        r = m.predict(frame, imgsz=640, conf=conf, verbose=False, device=0)[0]
        n = len(r.boxes) if r.boxes is not None else 0
        labels = []
        for b in (r.boxes or []):
            ci = int(b.cls[0])
            labels.append(f"{m.names[ci]}({float(b.conf[0]):.2f})")
        if n:
            print(f"  帧{fi:4d} conf={conf}: {n} 个 -> {', '.join(labels[:6])}")
        else:
            print(f"  帧{fi:4d} conf={conf}: 0 个")
    print()
cap.release()

print("=" * 78)
print("B) 专用检测器（1类 traffic_light）在不同 conf 下的检出")
print("=" * 78)
md = YOLO(DET)
cap = cv2.VideoCapture(VIDEO)
for fi in (0, 41, 82, 123, 164, 205):
    cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
    ok, frame = cap.read()
    if not ok:
        continue
    line = f"  帧{fi:4d}: "
    for conf in (0.05, 0.10, 0.25):
        r = md.predict(frame, imgsz=1280, conf=conf, verbose=False, device=0)[0]
        n = len(r.boxes) if r.boxes is not None else 0
        line += f"conf{conf}={n}个  "
    print(line)
cap.release()
