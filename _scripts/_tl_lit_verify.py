"""红绿灯判色：发光灯珠法 vs 整体颜色法

拼图观察（tl_truth_grid.png）：
  · ROI 是黄色灯箱 + 三个圆形灯头
  · 红灯真值批次的某几格，最下面一盏灯**明显发绿光**
  · 但 CNN 对 11/11 样本都判 yellow（conf 0.98~1.0）

推论：
  CNN 学到的很可能是"灯箱整体主色"（黄色），而不是"点亮的那盏灯"。
  因此需要改成【找发光灯珠】再判它的颜色。

本脚本对比两种方法在【有真值】的同一批样本上的准确率：
  A) 整体颜色法（CNN 当前行为）
  B) 发光灯珠法：找高饱和+高亮的小连通域，取它所在位置的色相
"""

import io
import os
import sys

sys.path.insert(0, r"E:\output\1\api")
os.chdir(r"E:\output\1\api")

import cv2
import numpy as np
from ultralytics import YOLO

from traffic_light_classifier import classify_traffic_light

OUT = r"E:\output\_tl_review"
VIDEO = r"E:\output\_carla_video4\carla_tl_face_28s.mp4"
GREEN_UNTIL = 80

out = []
model = YOLO(r"E:\output\1\yolov8n.pt")
cap = cv2.VideoCapture(VIDEO)


def hue_class(h):
    if h < 0:
        return "unknown"
    if h < 14 or h > 166:
        return "red"
    if 14 <= h <= 37:
        return "yellow"
    if 38 <= h <= 95:
        return "green"
    return "unknown"


def lit_lens_state(roi):
    """发光灯珠法：找高饱和+高亮连通域，返回其色相归类与置信度"""
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    # 发光灯珠：饱和度高 且 亮度高
    m = ((s > 120) & (v > 160)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    n, lab, stats, cents = cv2.connectedComponentsWithStats(m, 8)
    if n <= 1:
        return "unknown", 0.0, None
    best = None
    for i in range(1, n):
        a = int(stats[i, cv2.CC_STAT_AREA])
        if a < 4:
            continue
        mm = (lab == i)
        med_h = float(np.median(h[mm]))
        # 面积 × 平均亮度 作为"像灯珠"的评分
        score = a * float(v[mm].mean())
        if best is None or score > best[0]:
            best = (score, med_h, a, float(v[mm].mean()), int(cents[i][0]), int(cents[i][1]))
    if best is None:
        return "unknown", 0.0, None
    _, med_h, a, vv, cx, cy = best
    return hue_class(med_h), round(med_h, 1), (a, round(vv, 0), cx, cy)


rows = []
for fi in [10, 25, 40, 55, 70, 90, 120, 200, 300, 400, 480]:
    cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
    ok, frame = cap.read()
    if not ok:
        continue
    truth = "green" if fi < GREEN_UNTIL else "red"
    r = model.predict(frame, conf=0.2, imgsz=1280, verbose=False)[0]
    for bx in r.boxes:
        if r.names[int(bx.cls)] != "traffic light":
            continue
        x1, y1, x2, y2 = [int(v) for v in bx.xyxy[0].tolist()]
        H, W = frame.shape[:2]
        w, h = max(1, x2 - x1), max(1, y2 - y1)
        px, py = int(w * 0.25), int(h * 0.25)
        roi = frame[max(0, y1 - py):min(H, y2 + py),
                    max(0, x1 - px):min(W, x2 + px)]
        if roi.size == 0:
            continue
        cnn, cnn_conf = classify_traffic_light(roi)
        lit, medh, info = lit_lens_state(roi)
        rows.append({"frame": fi, "truth": truth, "cnn": cnn,
                     "cnn_conf": round(cnn_conf, 2), "lit": lit,
                     "medh": medh, "info": info, "roi": roi.copy()})
cap.release()

out.append("=" * 90)
out.append(f"两种方法在同一批样本上的对比（真值: frame<{GREEN_UNTIL}=Green, 否则 Red）")
out.append("=" * 90)
out.append(f"  {'帧':>5} {'真值':>6} {'A)整体CNN':>10} {'conf':>6} "
           f"{'B)发光灯珠':>10} {'色相H':>7} {'灯珠信息(面积,亮度,x,y)':>26} {'A对':>5} {'B对':>5}")
a_ok = b_ok = tot = 0
for r in rows:
    tot += 1
    ao = (r["cnn"] == r["truth"])
    bo = (r["lit"] == r["truth"])
    a_ok += int(ao)
    b_ok += int(bo)
    out.append(f"  {r['frame']:>5} {r['truth']:>6} {r['cnn']:>10} {r['cnn_conf']:>6} "
               f"{r['lit']:>10} {r['medh']:>7} {str(r['info']):>26} "
               f"{'✅' if ao else '❌':>5} {'✅' if bo else '❌':>5}")

out.append("")
out.append("=" * 90)
out.append("准确率对比")
out.append("=" * 90)
if tot:
    out.append(f"  A) 整体颜色法（CNN 当前）：{a_ok}/{tot} = {a_ok/tot*100:.0f}%")
    out.append(f"  B) 发光灯珠法            ：{b_ok}/{tot} = {b_ok/tot*100:.0f}%")
    out.append("")
    if b_ok > a_ok:
        out.append("  -> ✅ 发光灯珠法明显更准，建议改用此方法（或用它给 CNN 做二次校验）")
    elif b_ok == a_ok:
        out.append("  -> 两法持平")
    else:
        out.append("  -> 整体颜色法更好（与预期相反，需再查）")

# 可视化：把发光灯珠位置画出来
if rows:
    tiles = []
    for r in rows:
        t = r["roi"].copy()
        if r["info"]:
            a, vv, cx, cy = r["info"]
            cv2.circle(t, (cx, cy), max(4, int(np.sqrt(a))), (0, 255, 255), 2)
        t = cv2.resize(t, (130, 220), interpolation=cv2.INTER_NEAREST)
        cv2.putText(t, r["truth"][:5], (3, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
        cv2.putText(t, f"B:{r['lit'][:5]}", (3, 214), cv2.FONT_HERSHEY_SIMPLEX,
                    0.45, (0, 255, 0) if r["lit"] == r["truth"] else (0, 0, 255), 2)
        tiles.append(t)
    while len(tiles) % 6 != 0:
        tiles.append(np.zeros_like(tiles[0]))
    grid = np.vstack([np.hstack(tiles[i:i + 6]) for i in range(0, len(tiles), 6)])
    p = os.path.join(OUT, "tl_lit_lens.png")
    cv2.imwrite(p, grid)
    out.append("")
    out.append(f"  可视화（黄圈=检测到的发光灯珠）: {p}")

io.open(r"E:\output\_tl_lit_verify.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
