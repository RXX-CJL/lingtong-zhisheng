"""速度标定 —— 重复实验测方差（替代单次测量）

背景（2026-10-03 由 DSH 说明）：
  上一轮我用**单次测量**给每个帧率拟合了补偿系数，结果补偿后 15fps 从
  -15.3% 变成 +16.2%（过冲）。这说明**单次测量不足以标定** ——
  tracker 的像素速度估计本身就有可观方差。

本脚本对每个工况重复 N 次，给出：
  · 均值误差与标准差（衡量偏差 vs 抖动）
  · 最小/最大误差
  · 结论：这个工况下测速**能不能用**（决定是否允许用于超速判定）
"""

import io
import os
import statistics
import sys
import time

sys.path.insert(0, r"E:\output\1\api")
os.chdir(r"E:\output\1\api")

os.environ["SPEED_FPS_COMPENSATION"] = "0"          # 确保测的是未补偿值

from speed_calibration import SpeedCalibrator, speed_from_history  # noqa: E402
from vehicle_tracker import VehicleTracker  # noqa: E402

W, H = 1280, 576
SCENE = {"frame_width": W, "frame_height": H}
REPEATS = 8
out = []


def trial(true_kmh, y, fps, n_frames=None):
    """跑一次，返回反算 km/h（未补偿）"""
    cal = SpeedCalibrator(SCENE, frame_width=W, frame_height=H)
    want = cal.px_speed_to_kmh(1.0, y)
    pxps = true_kmh / want if want > 0 else 0.0
    nf = n_frames or max(6, int(fps))          # 约 1 秒
    tr = VehicleTracker(use_bytetrack=True)
    tk = {}
    dt = 1.0 / fps
    for i in range(nf):
        x = 100 + pxps * (i / fps)
        d = {"class_name": "car", "class_name_cn": "轿车", "confidence": 0.9,
             "bbox": [x, y - 40, x + 160, y + 40]}
        tk = tr.update([d], W, H)
        time.sleep(dt)
    if not tk:
        return None
    v = tk[list(tk.keys())[0]]
    est = speed_from_history(v.get("history") or [], cal)
    return est.get("kmh_raw")


out.append("=" * 88)
out.append(f"速度标定重复实验（每工况 {REPEATS} 次，取未补偿值 kmh_raw）")
out.append("=" * 88)
out.append("")

CASES = [
    ("60km/h@15fps", 60.0, 430, 15),
    ("60km/h@25fps", 60.0, 430, 25),
    ("40km/h@15fps", 40.0, 430, 15),
    ("80km/h@15fps", 80.0, 430, 15),
    ("60km/h@15fps y=300", 60.0, 300, 15),
    ("60km/h@15fps y=500", 60.0, 500, 15),
]

summary = []
for label, true_kmh, y, fps in CASES:
    vals = []
    for _ in range(REPEATS):
        r = trial(true_kmh, y, fps)
        if r is not None:
            vals.append(r)
    if not vals:
        out.append(f"  [{label}] 全部失败（追踪为空）")
        continue
    errs = [(v - true_kmh) / true_kmh * 100 for v in vals]
    mean = statistics.mean(errs)
    sd = statistics.pstdev(errs) if len(errs) > 1 else 0.0
    out.append(f"  [{label}]  n={len(vals)}")
    out.append(f"      反算 km/h: {[round(v,1) for v in vals]}")
    out.append(f"      误差: 均值 {mean:+.1f}%  标准差 {sd:.1f}%  "
               f"范围 [{min(errs):+.1f}%, {max(errs):+.1f}%]")
    usable = abs(mean) <= 20 and sd <= 15
    out.append(f"      可用性: {'✅ 可用于筛查' if usable else '❌ 偏差/抖动过大，不宜用于超速判定'}")
    summary.append((label, mean, sd, usable))
    out.append("")

out.append("=" * 88)
out.append("总体结论")
out.append("=" * 88)
if summary:
    ok = [s for s in summary if s[3]]
    out.append(f"  {len(ok)}/{len(summary)} 个工况满足「|偏差|<=20% 且 标准差<=15%」")
    for label, mean, sd, usable in summary:
        out.append(f"    {'✅' if usable else '❌'} {label:22s} 均值 {mean:+6.1f}%  标准差 {sd:4.1f}%")
    out.append("")
    out.append("  含义：")
    out.append("    · 均值误差 = 系统性偏差（可通过标定/补偿修正）")
    out.append("    · 标准差   = 随机抖动（无法通过补偿修正，只能靠更多采样/更好追踪）")
    out.append("    · 标准差大 -> **必须**用容差与人工复核，不能单点判定超速")

io.open(r"E:\output\_speed_variance.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
