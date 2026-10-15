"""红绿灯判色复核（用户第 3 条建议）

用户反馈原话：
  "红绿灯的信号颜色估计是检测错了"
  "有一个红绿灯的侧面全是黄的，被误认为是黄灯了"

复核方法：
  ① 从真实视频里跑 YOLO，取所有 traffic light 检测框
  ② 对每个框用项目当前的判色链路（CNN4 -> HSV 兜底）判色
  ③ 把 ROI 与判定结果存成拼图，人工核对判得对不对
  ④ 统计各状态分布 —— 若 yellow 占比异常高，说明存在系统性误判
"""

import io
import os
import sys

sys.path.insert(0, r"E:\output\1\api")
os.chdir(r"E:\output\1\api")

import cv2
import numpy as np

OUT_DIR = r"E:\output\_tl_review"
os.makedirs(OUT_DIR, exist_ok=True)
out = []

VIDEOS = [
    (r"E:\output\_carla_video\carla_scene_2k.mp4", "CARLA 2K"),
    (r"E:\output\_carla_video3\carla_simple_28s.mp4", "CARLA 简单 28s"),
    (r"E:\output\1\test_assets\traffic_videos\3e9b3f659e257969d581993be3c9e59e.mp4", "真实路口"),
]

# 判色链路
try:
    from traffic_light_classifier import (classify_traffic_light,
                                          hsv_fallback_state, is_available)
    out.append(f"CNN4 可用: {is_available()}")
except Exception as e:
    out.append(f"CNN4 导入失败: {e}")
    classify_traffic_light = None
    hsv_fallback_state = None

# YOLO
from ultralytics import YOLO
import glob
weights = glob.glob(r"E:\output\1\**\yolov8*.pt", recursive=True) + \
          glob.glob(r"E:\output\1\*.pt") + glob.glob(r"E:\output\*.pt")
out.append(f"找到权重候选: {[os.path.basename(w) for w in weights[:5]]}")
model = None
for w in weights:
    try:
        model = YOLO(w)
        out.append(f"已加载: {os.path.basename(w)}")
        break
    except Exception:
        continue

TL_CLASSES = ("traffic light",)

def analyze(video, label, max_frames=5, sample_step=60):
    res = {"n_tl": 0, "states": {}, "rows": []}
    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        return res
    fi = 0
    taken = 0
    while taken < max_frames:
        ok, frame = cap.read()
        if not ok:
            break
        if fi % sample_step == 0:
            taken += 1
            if model is not None:
                r = model.predict(frame, conf=0.25, imgsz=1280, verbose=False)[0]
                names = r.names
                for bx in r.boxes:
                    cname = names[int(bx.cls)]
                    if cname not in TL_CLASSES:
                        continue
                    bb = [int(v) for v in bx.xyxy[0].tolist()]
                    res["n_tl"] += 1
                    x1, y1, x2, y2 = bb
                    H, W = frame.shape[:2]
                    w, h = max(1, x2 - x1), max(1, y2 - y1)
                    px, py = int(w * 0.25), int(h * 0.25)
                    roi = frame[max(0, y1 - py):min(H, y2 + py),
                                max(0, x1 - px):min(W, x2 + px)]
                    if roi.size == 0:
                        continue
                    st, conf = ("unknown", 0.0)
                    src = "-"
                    if classify_traffic_light is not None:
                        st, conf = classify_traffic_light(roi)
                        if st != "unknown":
                            src = "cnn"
                    if st == "unknown" and hsv_fallback_state is not None:
                        hs = hsv_fallback_state(roi)
                        if hs != "unknown":
                            st, src, conf = hs, "hsv", 0.0
                    res["states"][st] = res["states"].get(st, 0) + 1
                    res["rows"].append((label, fi, bb, st, round(conf, 2), src, roi.copy()))
        fi += 1
    cap.release()
    return res

all_rows = []
out.append("")
out.append("=" * 78)
out.append("判色复核结果")
out.append("=" * 78)
for video, label in VIDEOS:
    if not os.path.exists(video):
        out.append(f"  {label}: 文件不存在，跳过")
        continue
    r = analyze(video, label)
    out.append(f"  {label}: 检出红绿灯框 {r['n_tl']} 个")
    out.append(f"     判色分布: {r['states']}")
    all_rows.extend(r["rows"])

# 汇总
from collections import Counter
c = Counter(x[3] for x in all_rows)
out.append("")
out.append(f"  合计 {len(all_rows)} 个框，判色分布: {dict(c)}")
if c:
    tot = sum(c.values())
    out.append(f"    yellow 占比: {c.get('yellow',0)/tot*100:.0f}%   "
               f"red {c.get('red',0)/tot*100:.0f}%   "
               f"green {c.get('green',0)/tot*100:.0f}%   "
               f"none {c.get('none',0)/tot*100:.0f}%   "
               f"unknown {c.get('unknown',0)/tot*100:.0f}%")

# 拼接 ROI 图供人工核对
if all_rows:
    tiles = []
    for label, fi, bb, st, conf, src, roi in all_rows[:24]:
        t = cv2.resize(roi, (110, 190), interpolation=cv2.INTER_NEAREST)
        cv2.putText(t, st[:6], (3, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (0, 0, 255) if st == "red" else
                    (0, 255, 255) if st == "yellow" else
                    (0, 255, 0) if st == "green" else (200, 200, 200), 2)
        cv2.putText(t, src[:3], (3, 186), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)
        tiles.append(t)
    while len(tiles) % 8 != 0:
        tiles.append(np.zeros_like(tiles[0]))
    rows_img = [np.hstack(tiles[i:i + 8]) for i in range(0, len(tiles), 8)]
    grid = np.vstack(rows_img)
    p = os.path.join(OUT_DIR, "tl_roi_grid.png")
    cv2.imwrite(p, grid)
    out.append("")
    out.append(f"  ROI 拼图（供人工核对）: {p}   尺寸 {grid.shape[1]}x{grid.shape[0]}")
    out.append("  每格: 左上角=判定状态, 左下角=来源(cnn/hsv)")

io.open(r"E:\output\_tl_review.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
