"""合成受控交通视频 —— 用于精确验证速度标定与超速门禁

为什么自己造素材（2026-10-03 由 DSH 决定）：
  · 全网可用的高清交通视频源已逐一排除（UA-DETRAC 下线 / CityFlow 是仿真器 /
    GitHub 搜索无果），而真实违规素材无法控制
  · **合成素材的优势**：车辆速度是**已知真值**，可以精确测出标定误差，
    这是任何真实视频都做不到的（真实视频不知道真车速）

设计（按 speed_calibration.py 的公式反推）：
  · 画面 1280x576（与项目测试视频一致）
  · 标定：无人工标定 -> 走 assumed_lanes 兜底
        ar = 1280/576 = 2.222
        n_lanes = 2.0 + (2.222-1.0)*5 = 8.11 -> 8.11
        est_width = 8.11 * 4.0 = 32.4 m
        ppm_ref = 1280 / 32.4 = 39.4 px/m（在 y_ref = 0.75*576 = 432 处）
    另：y_horizon = 0.30*576 = 172.8
        透视校正 ppm(y) = ppm_ref * (432-172.8)/(y-172.8)
  · 车辆 1（快车）：目标真实车速 90 km/h
        -> 在 y=432 处需要 px/s = 90/3.6*39.4 = 985 px/s
  · 车辆 2（慢车）：目标真实车速 30 km/h
        -> px/s = 30/3.6*39.4 = 328 px/s

输出：E:\\output\\_synth_videos\\synth_traffic.mp4
"""

import io
import os

import cv2
import numpy as np

OUT_DIR = r"E:\output\_synth_videos"
os.makedirs(OUT_DIR, exist_ok=True)

W, H = 1280, 576
FPS = 25
DURATION = 12
N = FPS * DURATION

# 标定参数（与 speed_calibration 的 assumed_lanes 一致）
AR = W / H
N_LANES = max(2.0, min(8.0, 2.0 + (AR - 1.0) * 5.0))
EST_WIDTH_M = N_LANES * 4.0
PPM_REF = W / EST_WIDTH_M
Y_REF = 0.75 * H
Y_HORIZON = 0.30 * H

info = []
info.append(f"画面 {W}x{H} @ {FPS}fps  {DURATION}s  共 {N} 帧")
info.append(f"标定: n_lanes={N_LANES:.2f} est_width={EST_WIDTH_M:.1f}m "
            f"ppm_ref={PPM_REF:.2f} px/m @ y_ref={Y_REF:.0f}  horizon={Y_HORIZON:.0f}")


def ppm_at(y):
    denom = (y - Y_HORIZON)
    if abs(denom) < 1e-6:
        return PPM_REF
    ratio = max(0.25, min(4.0, (Y_REF - Y_HORIZON) / denom))
    return PPM_REF * ratio


def kmh_to_px_per_sec(kmh, y):
    """按标定反推：真实 km/h -> 该 y 处的 px/s（车辆在 y 行运动）"""
    return kmh / 3.6 * ppm_at(y)


# 车辆定义：(名称, 真车速km/h, 所在y行, 颜色BGR)
TRACK_Y = 430          # 车道中心线（透视下，越靠下越近）
CARS = [
    ("fast", 90.0, TRACK_Y, (60, 60, 235)),      # 红车：真值 90 km/h -> 应判超速
    ("slow", 30.0, TRACK_Y + 60, (80, 200, 80)),  # 绿车：真值 30 km/h -> 不应超速
]
for name, kmh, y, _c in CARS:
    info.append(f"  {name}: 真值 {kmh} km/h  y={y}  ppm(y)={ppm_at(y):.2f}  "
                f"-> {kmh_to_px_per_sec(kmh, y):.0f} px/s")

out_path = os.path.join(OUT_DIR, "synth_traffic.mp4")
writer = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))

# 背景：天空 + 路面 + 车道线（静态，只画一次后复制）
bg = np.zeros((H, W, 3), dtype=np.uint8)
bg[:int(Y_HORIZON)] = (130, 140, 150)                      # 天空（灰蓝）
bg[int(Y_HORIZON):] = (70, 72, 75)                         # 沥青
# 远处地平线过渡
cv2.line(bg, (0, int(Y_HORIZON)), (W, int(Y_HORIZON)), (110, 115, 120), 2)
# 车道虚线（透视：越远越短越密）
for lane_x_top, lane_x_bot in ((320, 180), (640, 640), (960, 1100)):
    for k in range(14):
        t0 = k / 14.0
        t1 = t0 + 0.045
        y0 = int(Y_HORIZON + (H - Y_HORIZON) * t0 ** 1.6)
        y1 = int(Y_HORIZON + (H - Y_HORIZON) * t1 ** 1.6)
        x0 = int(lane_x_top + (lane_x_bot - lane_x_top) * t0 ** 1.6)
        x1 = int(lane_x_top + (lane_x_bot - lane_x_top) * t1 ** 1.6)
        if y1 > y0:
            cv2.line(bg, (x0, y0), (x1, y1), (215, 218, 220), 3)

# 逐帧渲染
for f in range(N):
    frame = bg.copy()
    t = f / FPS
    for name, kmh, y, color in CARS:
        pxps = kmh_to_px_per_sec(kmh, y)
        x = int(120 + pxps * t) % (W + 400) - 200     # 从左侧驶入，循环
        w, h = 150, 78
        x1, y1 = max(0, x), max(0, y - h // 2)
        x2, y2 = min(W, x + w), min(H, y + h // 2)
        if x2 > x1 and y2 > y1:
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, -1)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), 2)
            # 车头标记（供方向判断）
            cv2.circle(frame, (min(W - 5, int(x + w - 18)), int(y)), 7, (255, 255, 255), -1)
    # 左上角叠加真值（便于人工核对，不影响检测）
    cv2.putText(frame, f"GT: fast=90km/h slow=30km/h  t={t:.1f}s",
                (12, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    writer.write(frame)

writer.release()

size_mb = os.path.getsize(out_path) / 1024 / 1024
info.append("")
info.append(f"输出: {out_path}")
info.append(f"大小: {size_mb:.2f} MB  帧数: {N}")

# 校验：用 OpenCV 读回确认可解码
cap = cv2.VideoCapture(out_path)
ok, fr = cap.read()
info.append(f"回读校验: isOpened={cap.isOpened()} 首帧={fr.shape if ok else None} "
            f"fps={cap.get(cv2.CAP_PROP_FPS):.1f} 总帧={int(cap.get(cv2.CAP_PROP_FRAME_COUNT))}")
cap.release()

io.open(r"E:\output\_synth_video.md", "w", encoding="utf-8").write("\n".join(info) + "\n")
print("OK")
