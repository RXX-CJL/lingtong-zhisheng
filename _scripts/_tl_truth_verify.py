"""红绿灯判色精度验证 —— 真值对照（终于有条件做了）

真值来源（无需猜）：
  录制 carla_tl_face_28s.mp4 时，我每帧都执行
      near_tl.set_state(Green if fi < 80 else Red)
  并记录了状态变化日志：
      t=0.00 Green -> t=3.45 Yellow -> t=3.50 Green -> t=4.05 Red
  因此：
      frame < 80  (t < 4.0s)  -> 真值 Green
      frame >= 81 (t > 4.05s) -> 真值 Red

待验对象：
  视频里稳定可见的 1 个红绿灯（bbox≈[2051,33,2075,85]，24x52 px）

方法：
  在 Green 期抽 N 帧、Red 期抽 N 帧，对同一个灯框跑项目判色链路，
  统计判对率。同时输出放大图供人工核对。
"""

import io
import os
import sys

sys.path.insert(0, r"E:\output\1\api")
os.chdir(r"E:\output\1\api")

import cv2
import numpy as np
from ultralytics import YOLO

from traffic_light_classifier import (classify_traffic_light,
                                      hsv_fallback_state, is_available)

OUT = r"E:\output\_tl_review"
os.makedirs(OUT, exist_ok=True)
out = []

VIDEO = r"E:\output\_carla_video4\carla_tl_face_28s.mp4"
FRAME_GREEN_UNTIL = 80          # 前 80 帧为 Green（t<4.0s）
out.append(f"真值: frame<{FRAME_GREEN_UNTIL} -> Green ; frame>={FRAME_GREEN_UNTIL+1} -> Red")
out.append(f"CNN4 可用: {is_available()}")

model = YOLO(r"E:\output\1\yolov8n.pt")
cap = cv2.VideoCapture(VIDEO)

samples = []
# 在两种灯态期各取若干帧（避开切换瞬间 +/- 5 帧）
green_frames = [10, 25, 40, 55, 70]
red_frames = [90, 120, 200, 300, 400, 480]
for fi in green_frames + red_frames:
    cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
    ok, frame = cap.read()
    if not ok:
        continue
    truth = "green" if fi < FRAME_GREEN_UNTIL else "red"
    r = model.predict(frame, conf=0.2, imgsz=1280, verbose=False)[0]
    for bx in r.boxes:
        if r.names[int(bx.cls)] != "traffic light":
            continue
        x1, y1, x2, y2 = [int(v) for v in bx.xyxy[0].tolist()]
        det_conf = float(bx.conf)
        H, W = frame.shape[:2]
        w, h = max(1, x2 - x1), max(1, y2 - y1)
        px, py = int(w * 0.25), int(h * 0.25)
        roi = frame[max(0, y1 - py):min(H, y2 + py),
                    max(0, x1 - px):min(W, x2 + px)]
        if roi.size == 0:
            continue
        cnn, cnn_conf = classify_traffic_light(roi)
        hsv_st = hsv_fallback_state(roi) if hsv_fallback_state else "?"
        samples.append({
            "frame": fi, "truth": truth, "bbox": [x1, y1, x2, y2],
            "det_conf": round(det_conf, 2), "cnn": cnn,
            "cnn_conf": round(cnn_conf, 2), "hsv": hsv_st,
            "roi": roi.copy(), "size": f"{w}x{h}",
        })
cap.release()

out.append("")
out.append("=" * 84)
out.append(f"逐样本结果（共 {len(samples)}）")
out.append("=" * 84)
out.append(f"  {'帧':>5} {'真值':>6} {'框尺寸':>8} {'检测conf':>8} {'CNN':>8} "
           f"{'CNNconf':>8} {'HSV':>8} {'CNN判定':>8}")
n_ok = n_tot = 0
for s in samples:
    ok = (s["cnn"] == s["truth"])
    if s["cnn"] != "unknown":
        n_tot += 1
        n_ok += int(ok)
    out.append(f"  {s['frame']:>5} {s['truth']:>6} {s['size']:>8} {s['det_conf']:>8} "
               f"{s['cnn']:>8} {s['cnn_conf']:>8} {s['hsv']:>8} "
               f"{'✅' if ok else '❌'}")

out.append("")
out.append("=" * 84)
out.append("判色精度")
out.append("=" * 84)
if n_tot:
    out.append(f"  CNN 给出有效判定的样本: {n_tot}/{len(samples)}")
    out.append(f"  其中判对: {n_ok}/{n_tot} = {n_ok/n_tot*100:.0f}%")
g_all = [s for s in samples if s["truth"] == "green"]
r_all = [s for s in samples if s["truth"] == "red"]
for nm, arr in (("Green 真值", g_all), ("Red 真值", r_all)):
    if not arr:
        continue
    from collections import Counter
    c = Counter(s["cnn"] for s in arr)
    out.append(f"  {nm}: {len(arr)} 样本, CNN 判定分布 {dict(c)}")

# HSV 对照（说明为什么收紧它）
out.append("")
out.append("  【对照】HSV 兜底在同一批样本上的表现:")
from collections import Counter as _C
ch = _C(s["hsv"] for s in samples)
out.append(f"     HSV 判定分布: {dict(ch)}")
hsv_ok = sum(1 for s in samples if s["hsv"] == s["truth"])
hsv_tot = sum(1 for s in samples if s["hsv"] != "unknown")
out.append(f"     HSV 判对: {hsv_ok}/{hsv_tot} "
           f"({hsv_ok/hsv_tot*100:.0f}%)" if hsv_tot else "     HSV 全部 unknown")

# 拼图
if samples:
    tiles = []
    for s in samples:
        t = cv2.resize(s["roi"], (130, 220), interpolation=cv2.INTER_NEAREST)
        col = (0, 255, 0) if s["cnn"] == s["truth"] else (0, 0, 255)
        cv2.putText(t, s["truth"][:5], (3, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(t, s["cnn"][:5], (3, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.55, col, 2)
        cv2.putText(t, f"{s['cnn_conf']:.2f}", (3, 214), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                    (200, 200, 200), 1)
        tiles.append(t)
    while len(tiles) % 6 != 0:
        tiles.append(np.zeros_like(tiles[0]))
    grid = np.vstack([np.hstack(tiles[i:i + 6]) for i in range(0, len(tiles), 6)])
    p = os.path.join(OUT, "tl_truth_grid.png")
    cv2.imwrite(p, grid)
    out.append("")
    out.append(f"  拼图（上排=Green真值, 下排=Red真值；白字=真值, 彩字=CNN判定）: {p}")

io.open(r"E:\output\_tl_truth_verify.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
