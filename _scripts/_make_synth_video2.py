"""合成受控交通视频 v2 —— 车辆画得更真实，让 YOLO 能识别

v1 失败原因：纯色矩形 YOLO 识别不出（实测 0 检测）。
v2 加入 YOLO 训练分布里的视觉特征：车窗、车轮、车身分色、车灯、进气格栅。
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

AR = W / H
N_LANES = max(2.0, min(8.0, 2.0 + (AR - 1.0) * 5.0))
EST_WIDTH_M = N_LANES * 4.0
PPM_REF = W / EST_WIDTH_M
Y_REF = 0.75 * H
Y_HORIZON = 0.30 * H

info = [f"画面 {W}x{H} @ {FPS}fps {DURATION}s",
        f"标定: ppm_ref={PPM_REF:.2f} @ y_ref={Y_REF:.0f} horizon={Y_HORIZON:.0f}"]


def ppm_at(y):
    denom = (y - Y_HORIZON)
    if abs(denom) < 1e-6:
        return PPM_REF
    return PPM_REF * max(0.25, min(4.0, (Y_REF - Y_HORIZON) / denom))


def kmh_to_px(kmh, y):
    return kmh / 3.6 * ppm_at(y)


def draw_car(img, x, y, w, h, body, facing='right'):
    """画一辆"像真车"的车（侧视），含车窗/车轮/车灯"""
    x, y, w, h = int(x), int(y), int(w), int(h)
    x2, y2 = x + w, y + h
    if x2 <= 0 or x >= W or y2 <= 0 or y >= H:
        return
    x1c, y1c = max(0, x), max(0, y)
    x2c, y2c = min(W, x2), min(H, y2)
    if x2c <= x1c or y2c <= y1c:
        return
    # 车身（主色）
    cv2.rectangle(img, (x1c, y1c), (x2c, y2c), body, -1)
    # 车顶/车厢（同色深一点）
    roof_h = max(6, int(h * 0.34))
    roof = tuple(max(0, int(c * 0.75)) for c in body)
    cv2.rectangle(img, (x1c + int(w * 0.22), y1c - roof_h + 2),
                  (x2c - int(w * 0.18), y1c + 2), roof, -1)
    # 车窗（浅蓝灰，YOLO 认车窗很强）
    if y1c - roof_h + 5 < y1c:
        cv2.rectangle(img, (x1c + int(w * 0.26), y1c - roof_h + 6),
                      (x2c - int(w * 0.22), y1c - 1), (170, 190, 200), -1)
    # 车轮（黑色圆 + 灰毂）
    r = max(4, int(h * 0.19))
    wy = y2c - int(h * 0.10)
    for wx in (x1c + int(w * 0.22), x2c - int(w * 0.22)):
        if 0 <= wx < W:
            cv2.circle(img, (wx, min(H - 1, wy)), r, (25, 25, 28), -1)
            cv2.circle(img, (wx, min(H - 1, wy)), max(2, r // 2), (140, 140, 145), -1)
    # 车灯（前白后红）
    ly = y1c + int(h * 0.30)
    if facing == 'right':
        cv2.rectangle(img, (max(0, x2c - 10), ly), (x2c - 2, ly + int(h * 0.16)), (240, 245, 250), -1)
        cv2.rectangle(img, (x1c + 2, ly), (x1c + 10, ly + int(h * 0.16)), (40, 40, 200), -1)
    else:
        cv2.rectangle(img, (x1c + 2, ly), (x1c + 10, ly + int(h * 0.16)), (240, 245, 250), -1)
        cv2.rectangle(img, (max(0, x2c - 10), ly), (x2c - 2, ly + int(h * 0.16)), (40, 40, 200), -1)
    # 轮眉线
    cv2.line(img, (x1c, y2c - int(h * 0.22)), (x2c, y2c - int(h * 0.22)),
             tuple(max(0, int(c * 0.6)) for c in body), 2)


# 背景
bg = np.zeros((H, W, 3), dtype=np.uint8)
bg[:int(Y_HORIZON)] = (150, 158, 165)
bg[int(Y_HORIZON):] = (72, 74, 78)
cv2.line(bg, (0, int(Y_HORIZON)), (W, int(Y_HORIZON)), (115, 120, 125), 2)
for lane_x_top, lane_x_bot in ((320, 180), (640, 640), (960, 1100)):
    for k in range(14):
        t0, t1 = k / 14.0, k / 14.0 + 0.045
        y0 = int(Y_HORIZON + (H - Y_HORIZON) * t0 ** 1.6)
        y1 = int(Y_HORIZON + (H - Y_HORIZON) * t1 ** 1.6)
        x0 = int(lane_x_top + (lane_x_bot - lane_x_top) * t0 ** 1.6)
        x1 = int(lane_x_top + (lane_x_bot - lane_x_top) * t1 ** 1.6)
        if y1 > y0:
            cv2.line(bg, (x0, y0), (x1, y1), (220, 224, 226), 3)
# 远处建筑剪影（给 YOLO 一点上下文）
cv2.rectangle(bg, (60, int(Y_HORIZON) - 60), (200, int(Y_HORIZON)), (110, 112, 118), -1)
cv2.rectangle(bg, (900, int(Y_HORIZON) - 40), (1050, int(Y_HORIZON)), (118, 120, 126), -1)

CARS = [
    ("fast", 90.0, 430, (52, 52, 200), 168, 86),
    ("slow", 30.0, 505, (70, 170, 70), 150, 76),
]

out_path = os.path.join(OUT_DIR, "synth_traffic_v2.mp4")
writer = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
for name, kmh, y, color, cw, ch in CARS:
    info.append(f"  {name}: 真值 {kmh} km/h y={y} -> {kmh_to_px(kmh,y):.0f} px/s")

for f in range(N):
    frame = bg.copy()
    t = f / FPS
    for name, kmh, y, color, cw, ch in CARS:
        pxps = kmh_to_px(kmh, y)
        x = (120 + pxps * t) % (W + 500) - 250
        draw_car(frame, x, y - ch // 2, cw, ch, color, 'right')
    cv2.putText(frame, f"GT fast=90 slow=30 km/h  t={t:.1f}s", (12, 26),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    writer.write(frame)
writer.release()

info.append("")
info.append(f"输出: {out_path}  ({os.path.getsize(out_path)/1024/1024:.2f} MB)")

# 立刻用 YOLO 验证能被识别
import base64
import sys
sys.path.insert(0, r"E:\output\1\api")
os.chdir(r"E:\output\1\api")
try:
    from image_recognizer import multi_model_detect
    cap = cv2.VideoCapture(out_path)
    for pos in (40, 100, 160):
        cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
        ok, fr = cap.read()
        if not ok:
            continue
        tmp = rf"E:\output\_synth_chk_{pos}.jpg"
        cv2.imwrite(tmp, fr)
        r = multi_model_detect(tmp, conf_threshold=0.25)
        dets = r.get("all_detections", []) if r.get("success") else []
        veh = [d for d in dets if d.get("class_name") in ("car", "truck", "bus", "motorcycle")]
        info.append(f"YOLO 帧{pos}: 总 {len(dets)} 车辆 {len(veh)}  " +
                    " ".join(f"{d.get('class_name')}({d.get('confidence'):.2f})" for d in veh[:3]))
    cap.release()
except Exception as e:
    info.append(f"YOLO 验证失败: {type(e).__name__}: {e}")

io.open(r"E:\output\_synth_video.md", "w", encoding="utf-8").write("\n".join(info) + "\n")
print("OK")
