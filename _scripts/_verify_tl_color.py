"""验证：提高 imgsz 后红绿灯可检出，且 HSV 判色给出合理结果"""

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
OUT = r"E:\output\_tl_crops"
os.makedirs(OUT, exist_ok=True)

m = YOLO(MODEL)


def hsv_state(img, bbox):
    """与 annotation_renderer._analyze_traffic_light_color 相同的判色逻辑"""
    x1, y1, x2, y2 = [int(v) for v in bbox[:4]]
    h, w = img.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 - x1 < 4 or y2 - y1 < 4:
        return "unknown", {}
    roi = img[y1:y2, x1:x2]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    masks = {
        "red": cv2.bitwise_or(cv2.inRange(hsv, (0, 70, 60), (10, 255, 255)),
                              cv2.inRange(hsv, (170, 70, 60), (180, 255, 255))),
        "yellow": cv2.inRange(hsv, (15, 70, 70), (35, 255, 255)),
        "green": cv2.inRange(hsv, (40, 60, 60), (90, 255, 255)),
    }
    counts = {k: int(cv2.countNonZero(v)) for k, v in masks.items()}
    total = roi.shape[0] * roi.shape[1]
    best = max(counts, key=counts.get)
    if total <= 0 or counts[best] < max(6, int(total * 0.02)):
        return "unknown", counts
    return best, counts


cap = cv2.VideoCapture(VIDEO)
print(f"{'帧':>5} | {'红绿灯':>6} | {'判色结果（尺寸 / 色量）'}")
print("-" * 78)
allstates = []
for fi in (0, 150, 300, 450, 600):
    cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
    ok, frame = cap.read()
    if not ok:
        continue
    r = m.predict(frame, imgsz=1280, conf=0.25, verbose=False, device=0)[0]
    tls = []
    for b in (r.boxes or []):
        cls = m.names.get(int(b.cls[0]), "") if isinstance(m.names, dict) else m.names[int(b.cls[0])]
        if "traffic light" in str(cls).lower():
            xy = [float(v) for v in b.xyxy[0].tolist()]
            tls.append(xy)
    desc = []
    for i, bb in enumerate(tls):
        state, counts = hsv_state(frame, bb)
        allstates.append(state)
        w = int(bb[2] - bb[0]); h = int(bb[3] - bb[1])
        desc.append(f"#{i} {w}x{h} -> {state} {counts}")
        # 导出裁剪图（放大便于人工核验）
        x1, y1, x2, y2 = [int(v) for v in bb]
        crop = frame[max(0, y1):y2, max(0, x1):x2]
        if crop.size:
            big = cv2.resize(crop, None, fx=6, fy=6, interpolation=cv2.INTER_NEAREST)
            cv2.imwrite(os.path.join(OUT, f"f{fi}_{i}_{state}_{w}x{h}.png"), big)
    print(f"{fi:>5} | {len(tls):>6} | {'; '.join(desc) if desc else '(无)'}")
cap.release()

print()
print("=" * 78)
import collections  # noqa: E402
c = collections.Counter(allstates)
print(f"判色分布: {dict(c)}")
n_known = sum(v for k, v in c.items() if k != "unknown")
print(f"可判定比例: {n_known}/{len(allstates)}")
print(f"裁剪图（放大6倍）: {OUT}")
print("=" * 78)
