"""粗测两个候选视频：红绿灯检出质量（尺寸是否够判色）"""

import os
import sys
import collections

API = r"E:\output\1\api"
sys.path.insert(0, API)
os.chdir(API)

import cv2  # noqa: E402
from ultralytics import YOLO  # noqa: E402

MODEL = r"E:\output\1\zhitong\training\models\yolov8s.pt"
VIDEOS = [
    r"E:\output\1\test_assets\traffic_videos\ea1ca6cbb27653af24ebe585d56f0ffd.mp4",
    r"E:\output\1\test_assets\traffic_videos\701c5154f47975564a8039bb03bd3340.mp4",
]
OUT = r"E:\output\_tl_crops2"
os.makedirs(OUT, exist_ok=True)

m = YOLO(MODEL)


def hsv_state(img, bbox):
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


for vp in VIDEOS:
    name = os.path.basename(vp)[:12]
    cap = cv2.VideoCapture(vp)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    w0 = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h0 = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print("=" * 78)
    print(f"{name}  {w0}x{h0}  {total} 帧  {fps:.1f} fps")
    print("=" * 78)

    sizes = []
    states = []
    n_tl_total = 0
    step = max(1, total // 6)
    for fi in range(0, total, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
        ok, frame = cap.read()
        if not ok:
            continue
        r = m.predict(frame, imgsz=1280, conf=0.25, verbose=False, device=0)[0]
        for i, b in enumerate(r.boxes or []):
            cls = m.names.get(int(b.cls[0]), "") if isinstance(m.names, dict) else m.names[int(b.cls[0])]
            if "traffic light" not in str(cls).lower():
                continue
            bb = [float(v) for v in b.xyxy[0].tolist()]
            w = int(bb[2] - bb[0]); h = int(bb[3] - bb[1])
            sizes.append((w, h))
            st, counts = hsv_state(frame, bb)
            states.append(st)
            n_tl_total += 1
            x1, y1, x2, y2 = [int(v) for v in bb]
            crop = frame[max(0, y1):y2, max(0, x1):x2]
            if crop.size and w >= 8:
                big = cv2.resize(crop, None, fx=5, fy=5, interpolation=cv2.INTER_NEAREST)
                cv2.imwrite(os.path.join(OUT, f"{name}_f{fi}_{i}_{st}_{w}x{h}.png"), big)
        print(f"  帧{fi:4d}: 红绿灯 {sum(1 for b in (r.boxes or []) if 'traffic light' in str(m.names.get(int(b.cls[0]),'') if isinstance(m.names,dict) else m.names[int(b.cls[0])]).lower())}")
    cap.release()

    print()
    print(f"  红绿灯检出总数: {n_tl_total}")
    if sizes:
        ws = [s[0] for s in sizes]; hs = [s[1] for s in sizes]
        print(f"  尺寸: 宽 {min(ws)}-{max(ws)} (均值 {sum(ws)/len(ws):.1f})  高 {min(hs)}-{max(hs)} (均值 {sum(hs)/len(hs):.1f})")
        big = sum(1 for s in sizes if s[0] >= 12)
        print(f"  >=12px 宽（可判色）: {big}/{len(sizes)}")
    print(f"  判色分布: {dict(collections.Counter(states))}")
    print()

print("裁剪图目录:", OUT)
