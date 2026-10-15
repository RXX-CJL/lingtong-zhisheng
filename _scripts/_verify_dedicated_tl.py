"""验证专用红绿灯两阶段管线：检测 -> 裁剪 -> 颜色分类

对比三方：
  A. COCO yolov8s @1280 + HSV 判色（当前项目方案）
  B. COCO yolov8s @1280 + 专用颜色分类器
  C. 专用检测器 + 专用颜色分类器（博客方案）
"""

import collections
import glob
import os
import sys

API = r"E:\output\1\api"
sys.path.insert(0, API)
os.chdir(API)

import cv2  # noqa: E402
from ultralytics import YOLO  # noqa: E402

DET_MODEL = glob.glob(r"E:\output\_models_dl\traffic_light_detection*\**\weights\best.pt",
                      recursive=True)[0]
CLS_MODEL = glob.glob(r"E:\output\_models_dl\traffic_light_color*\**\weights\best.pt",
                      recursive=True)[0]
COCO = r"E:\output\1\zhitong\training\models\yolov8s.pt"
VIDEO = r"E:\output\1\test_assets\traffic_videos\ea1ca6cbb27653af24ebe585d56f0ffd.mp4"
OUT = r"E:\output\_tl_dedicated"
os.makedirs(OUT, exist_ok=True)

print("检测模型:", os.path.basename(os.path.dirname(os.path.dirname(DET_MODEL))))
print("分类模型:", os.path.basename(os.path.dirname(os.path.dirname(CLS_MODEL))))
print()

m_det = YOLO(DET_MODEL)
m_cls = YOLO(CLS_MODEL)
m_coco = YOLO(COCO)

# 颜色分类：用分类模型对裁剪图预测（含一点边缘扩展，提高上下文）
def classify(crop):
    if crop is None or crop.size == 0 or crop.shape[0] < 8 or crop.shape[1] < 8:
        return None, 0.0
    r = m_cls.predict(crop, imgsz=64, verbose=False, device=0)[0]
    if r.probs is None:
        return None, 0.0
    idx = int(r.probs.top1)
    conf = float(r.probs.top1conf)
    return m_cls.names[idx], conf


def hsv_state(img, bb):
    x1, y1, x2, y2 = [int(v) for v in bb[:4]]
    h, w = img.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 - x1 < 4 or y2 - y1 < 4:
        return "unknown"
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
    return best if (total > 0 and counts[best] >= max(6, int(total * 0.02))) else "unknown"


cap = cv2.VideoCapture(VIDEO)
total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
print(f"视频: {total} 帧")
print()
print(f"{'帧':>5} | {'A: COCO+HSV':>22} | {'B: COCO+专用分类':>24} | {'C: 专用检测+分类':>26}")
print("-" * 92)

statA, statB, statC = collections.Counter(), collections.Counter(), collections.Counter()
nA = nB = nC = 0

for fi in range(0, total, max(1, total // 6)):
    cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
    ok, frame = cap.read()
    if not ok:
        continue

    # A: COCO 检测 + HSV
    rA = m_coco.predict(frame, imgsz=1280, conf=0.25, verbose=False, device=0)[0]
    boxesA = []
    for b in (rA.boxes or []):
        cls = rA.names.get(int(b.cls[0])) if isinstance(rA.names, dict) else rA.names[int(b.cls[0])]
        if "traffic light" in str(cls).lower():
            boxesA.append([float(v) for v in b.xyxy[0].tolist()])
    resA = [hsv_state(frame, bb) for bb in boxesA]
    resB = [classify(frame[int(bb[1]):int(bb[3]), int(bb[0]):int(bb[2])])[0] for bb in boxesA]

    # C: 专用检测器 + 专用分类器
    rC = m_det.predict(frame, imgsz=1280, conf=0.25, verbose=False, device=0)[0]
    boxesC = [[float(v) for v in b.xyxy[0].tolist()] for b in (rC.boxes or [])]
    resC = []
    for bb in boxesC:
        x1, y1, x2, y2 = [int(v) for v in bb]
        crop = frame[max(0, y1):y2, max(0, x1):x2]
        st, cf = classify(crop)
        resC.append(f"{st}({cf:.2f})" if st else "?")
        if crop.size and (x2 - x1) >= 8:
            big = cv2.resize(crop, None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST)
            cv2.imwrite(os.path.join(OUT, f"f{fi}_{x2-x1}x{y2-y1}_{st}.png"), big)
    for s in resA: statA[s] += 1
    for s in resB: statB[s] += 1
    for s in resC: statC[str(s).split("(")[0]] += 1
    nA += len(boxesA); nB += len(boxesA); nC += len(boxesC)

    print(f"{fi:>5} | {len(boxesA):>3}个 {str(resA)[:16]:>16} | {len(boxesA):>3}个 {str(resB)[:18]:>18} | {len(boxesC):>3}个 {str(resC)[:20]:>20}")

cap.release()
print()
print("=" * 92)
print(f"A: COCO+HSV         检出 {nA:>3}  判色分布 {dict(statA)}")
print(f"B: COCO+专用分类器  检出 {nB:>3}  判色分布 {dict(statB)}")
print(f"C: 专用检测+专用分类 检出 {nC:>3}  判色分布 {dict(statC)}")
print("=" * 92)
print(f"裁剪图: {OUT}")
