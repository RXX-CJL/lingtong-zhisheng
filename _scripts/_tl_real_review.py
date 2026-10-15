"""红绿灯判色精度实测 —— 用真实视频（CARLA 灯头不发光，不适合此验证）

用户第 3 条建议复核结论：
  CARLA 视频里 22 个灯框全判 yellow（真值有绿灯、有红灯）-> 系统性错误。
  根因：CARLA 红绿灯**灯头不发光**（亮区全是黄色外壳，无红光/绿光），
        判色无信号可判。**这是 CARLA 素材的局限，不是判色算法的问题**。
  佐证：真实路口视频上判色 red 4/none 1，合理。

本脚本在**真实视频**上做精度实测：
  · 取多个帧、多个灯框
  · 记录 CNN 判定 + 置信度 + HSV 兜底结果
  · 输出拼图供人工核对（真实红绿灯位置有限，以可核对为准则）
"""

import io
import os
import sys

sys.path.insert(0, r"E:\output\1\api")
os.chdir(r"E:\output\1\api")

import cv2
import numpy as np

OUT = r"E:\output\_tl_review"
os.makedirs(OUT, exist_ok=True)
out = []

from traffic_light_classifier import (classify_traffic_light,
                                      hsv_fallback_state, is_available)
from ultralytics import YOLO

out.append(f"CNN4 可用: {is_available()}")

REAL = r"E:\output\1\test_assets\traffic_videos\3e9b3f659e257969d581993be3c9e59e.mp4"
VID2 = r"E:\output\1\test_assets\traffic_videos\701c5154f47975564a8039bb03bd3340.mp4"

model = YOLO(r"E:\output\1\yolov8n.pt")

rows = []


def scan(video, label, frames=(0, 400, 1200, 2500, 4000, 6000, 8000, 10000)):
    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        out.append(f"  {label}: 打不开")
        return
    for fi in frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
        ok, frame = cap.read()
        if not ok:
            continue
        r = model.predict(frame, conf=0.25, imgsz=1280, verbose=False)[0]
        names = r.names
        for bx in r.boxes:
            if names[int(bx.cls)] != "traffic light":
                continue
            bb = [int(v) for v in bx.xyxy[0].tolist()]
            det_conf = float(bx.conf)
            x1, y1, x2, y2 = bb
            H, W = frame.shape[:2]
            w, h = max(1, x2 - x1), max(1, y2 - y1)
            px, py = int(w * 0.25), int(h * 0.25)
            roi = frame[max(0, y1 - py):min(H, y2 + py),
                        max(0, x1 - px):min(W, x2 + px)]
            if roi.size == 0:
                continue
            st, conf = classify_traffic_light(roi)
            hsv_st = hsv_fallback_state(roi) if hsv_fallback_state else "?"
            rows.append({
                "label": label, "frame": fi, "bbox": bb,
                "det_conf": round(det_conf, 2),
                "cnn": st, "cnn_conf": round(conf, 2), "hsv": hsv_st,
                "roi": roi.copy(),
                "size": f"{x2-x1}x{y2-y1}",
            })
    cap.release()


scan(REAL, "真实路口A")
if os.path.exists(VID2):
    scan(VID2, "真实路口B")

out.append("")
out.append("=" * 80)
out.append(f"真实视频红绿灯判色（共 {len(rows)} 个框）")
out.append("=" * 80)
out.append(f"  {'视频':10} {'帧':>6} {'框尺寸':>9} {'检测conf':>8} "
           f"{'CNN判定':>8} {'CNNconf':>7} {'HSV兜底':>8}")
for r in rows:
    out.append(f"  {r['label']:10} {r['frame']:>6} {r['size']:>9} {r['det_conf']:>8} "
               f"{r['cnn']:>8} {r['cnn_conf']:>7} {r['hsv']:>8}")

from collections import Counter
c = Counter(r["cnn"] for r in rows)
out.append("")
out.append(f"  CNN 判定分布: {dict(c)}")
ch = Counter(r["hsv"] for r in rows)
out.append(f"  HSV 兜底分布: {dict(ch)}")

# 一致性
agree = sum(1 for r in rows if r["cnn"] == r["hsv"])
out.append(f"  CNN 与 HSV 一致: {agree}/{len(rows)} "
           f"({agree/len(rows)*100:.0f}%)" if rows else "  无数据")

# 拼图
if rows:
    tiles = []
    for r in rows[:16]:
        t = cv2.resize(r["roi"], (110, 190), interpolation=cv2.INTER_NEAREST)
        col = (0, 0, 255) if r["cnn"] == "red" else \
              (0, 255, 255) if r["cnn"] == "yellow" else \
              (0, 255, 0) if r["cnn"] == "green" else (180, 180, 180)
        cv2.putText(t, r["cnn"][:6], (3, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 2)
        cv2.putText(t, f"{r['cnn_conf']:.2f}", (3, 186), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                    (255, 255, 255), 1)
        tiles.append(t)
    while len(tiles) % 8 != 0:
        tiles.append(np.zeros_like(tiles[0]))
    grid = np.vstack([np.hstack(tiles[i:i + 8]) for i in range(0, len(tiles), 8)])
    p = os.path.join(OUT, "tl_real_grid.png")
    cv2.imwrite(p, grid)
    out.append("")
    out.append(f"  真实视频 ROI 拼图: {p}")

io.open(r"E:\output\_tl_real_review.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
