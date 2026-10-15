"""批量抽取红绿灯裁剪图 + HSV 预标注（供人工核验）

设计要点（便于人工快速核验）：
  1. 裁剪时**向外扩边**（灯光需要灯壳上下文，纯紧框反而不易判断）
  2. 按 HSV 预判结果分目录存放：red/ yellow/ green/ unknown/
  3. 文件名带来源信息：v{视频}_{帧号}_{序号}_{宽}x{高}.png
  4. 每张放大 4 倍保存（便于肉眼核验）
  5. 同时生成一份 CSV 索引，便于核对

用法：跑完后人工只需浏览 4 个目录，把放错的图拖到正确目录即可。
"""

import csv
import os
import sys

API = r"E:\output\1\api"
sys.path.insert(0, API)
os.chdir(API)

import cv2  # noqa: E402
from ultralytics import YOLO  # noqa: E402

VIDEOS = [
    ("v1", r"E:\output\1\test_assets\traffic_videos\ea1ca6cbb27653af24ebe585d56f0ffd.mp4"),
    ("v2", r"E:\output\1\test_assets\traffic_videos\701c5154f47975564a8039bb03bd3340.mp4"),
]
OUT_ROOT = r"E:\output\_tl_dataset"
COCO = r"E:\output\1\zhitong\training\models\yolov8s.pt"
IMGSZ = int(os.environ.get("YOLO_IMGSZ", "1280"))
PAD_RATIO = 0.25          # 向外扩边比例
UPSCALE = 4               # 保存时放大倍数

for sub in ("red", "yellow", "green", "unknown"):
    os.makedirs(os.path.join(OUT_ROOT, sub), exist_ok=True)

m = YOLO(COCO)


def hsv_state(img, bb):
    x1, y1, x2, y2 = [int(v) for v in bb[:4]]
    h, w = img.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 - x1 < 4 or y2 - y1 < 4:
        return "unknown", 0
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
    ok = total > 0 and counts[best] >= max(6, int(total * 0.02))
    return (best if ok else "unknown"), counts[best]


rows = []
counter = {}
for tag, vp in VIDEOS:
    cap = cv2.VideoCapture(vp)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = max(1, total // 40)      # 每个视频取 ~40 帧
    print(f"{tag}: {os.path.basename(vp)[:14]}  {total} 帧, 步长 {step}")
    for fi in range(0, total, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
        ok, frame = cap.read()
        if not ok:
            continue
        r = m.predict(frame, imgsz=IMGSZ, conf=0.25, verbose=False, device=0)[0]
        for i, b in enumerate(r.boxes or []):
            cls = r.names.get(int(b.cls[0])) if isinstance(r.names, dict) else r.names[int(b.cls[0])]
            if "traffic light" not in str(cls).lower():
                continue
            bb = [float(v) for v in b.xyxy[0].tolist()]
            w = int(bb[2] - bb[0]); h = int(bb[3] - bb[1])
            if w < 8 or h < 8:        # 太小，颜色信息不足
                continue
            state, cnt = hsv_state(frame, bb)
            # 扩边裁剪
            padx, pady = int(w * PAD_RATIO), int(h * PAD_RATIO)
            H, W = frame.shape[:2]
            x1 = max(0, int(bb[0]) - padx); y1 = max(0, int(bb[1]) - pady)
            x2 = min(W, int(bb[2]) + padx); y2 = min(H, int(bb[3]) + pady)
            crop = frame[y1:y2, x1:x2]
            if crop.size == 0:
                continue
            key = (tag, state)
            counter[key] = counter.get(key, 0) + 1
            fname = f"{tag}_f{fi:04d}_{counter[key]:03d}_{w}x{h}.png"
            big = cv2.resize(crop, None, fx=UPSCALE, fy=UPSCALE,
                             interpolation=cv2.INTER_NEAREST)
            cv2.imwrite(os.path.join(OUT_ROOT, state, fname), big)
            rows.append({
                "file": f"{state}/{fname}", "video": tag, "frame": fi,
                "hsv_pred": state, "hsv_pixels": cnt,
                "bbox_w": w, "bbox_h": h, "conf": round(float(b.conf[0]), 3),
                "human_label": "",       # 留给人工填
            })
    cap.release()

# 写索引 CSV
csv_path = os.path.join(OUT_ROOT, "index.csv")
with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else
                       ["file", "video", "frame", "hsv_pred", "hsv_pixels",
                        "bbox_w", "bbox_h", "conf", "human_label"])
    w.writeheader()
    w.writerows(rows)

print()
print("=" * 74)
print(f"共导出 {len(rows)} 张裁剪图 -> {OUT_ROOT}")
for sub in ("red", "yellow", "green", "unknown"):
    d = os.path.join(OUT_ROOT, sub)
    n = len([f for f in os.listdir(d) if f.endswith('.png')])
    print(f"  {sub:8s}: {n:>3} 张")
print(f"索引: {csv_path}")
print("=" * 74)
print("人工核验方式：浏览 4 个目录，把放错的图拖到正确目录即可。")
print("核验完成后运行训练脚本（我会提供）。")
