"""红绿灯判色根因量化：到底有多少"点亮"像素？在哪盏灯？

用户反馈："有一个红绿灯的侧面全是黄的，被误认为黄灯了"

拼图观察：ROI 里都是黄底灯箱 + 三个圆形灯头，CNN 判 yellow 是"看对了颜色、
看错了对象" —— 它识别的是**灯箱外壳**而不是**点亮的那盏灯**。

本脚本量化：
  ① 在红灯真值帧（CARLA 简单28s，我明确 set_state(Red)）上：
     - 算出黄/红/绿三类像素的绝对数量与占比
     - 找出最亮的连通域，看它落在灯箱的哪个位置（上/中/下）
  ② 判断"最亮区域颜色"是否比"整体主要颜色"更接近真实信号灯
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

VIDEO = r"E:\output\_carla_video3\carla_simple_28s.mp4"
# 真值：t=0 Green，t=4.05 Red  -> 取 t=6s（第 120 帧）应为红灯
RED_TRUE_FRAME = 120

from ultralytics import YOLO
model = YOLO(r"E:\output\1\yolov8n.pt") if os.path.exists(r"E:\output\1\yolov8n.pt") else None
if model is None:
    import glob
    ws = glob.glob(r"E:\output\1\**\yolov8n.pt", recursive=True)
    model = YOLO(ws[0]) if ws else None
out.append(f"YOLO 就绪: {model is not None}")

cap = cv2.VideoCapture(VIDEO)
cap.set(cv2.CAP_PROP_POS_FRAMES, RED_TRUE_FRAME)
ok, frame = cap.read()
cap.release()
out.append(f"取帧 {RED_TRUE_FRAME}（真值应为【红灯】）: {ok}  {frame.shape if ok else ''}")

if ok and model is not None:
    r = model.predict(frame, conf=0.25, imgsz=1280, verbose=False)[0]
    names = r.names
    n = 0
    for bx in r.boxes:
        if names[int(bx.cls)] != "traffic light":
            continue
        n += 1
        x1, y1, x2, y2 = [int(v) for v in bx.xyxy[0].tolist()]
        tx = (x1 + x2) // 2
        ty = (y1 + y2) // 2
        out.append("")
        out.append("=" * 74)
        out.append(f"灯框 #{n}: bbox=[{x1},{y1},{x2},{y2}]  尺寸 {x2-x1}x{y2-y1}  中心=({tx},{ty})")
        out.append("=" * 74)

        roi = frame[max(0, y1):min(frame.shape[0], y2), max(0, x1):min(frame.shape[1], x2)]
        if roi.size == 0:
            out.append("  ROI 为空")
            continue
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        masks = {
            "red": cv2.bitwise_or(cv2.inRange(hsv, (0, 70, 60), (10, 255, 255)),
                                  cv2.inRange(hsv, (170, 70, 60), (180, 255, 255))),
            "yellow": cv2.inRange(hsv, (15, 70, 70), (35, 255, 255)),
            "green": cv2.inRange(hsv, (40, 60, 60), (90, 255, 255)),
        }
        total = roi.shape[0] * roi.shape[1]
        out.append(f"  整体颜色占比（HSV，当前判色依据）:")
        for k, m in masks.items():
            c = int(cv2.countNonZero(m))
            out.append(f"     {k:7s} {c:>7} px  ({c/total*100:5.1f}%)")

        # --- 找"最亮"的连通域：点亮的那盏灯应该明显更亮 ---
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        _, bright = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        out.append(f"  亮度阈值分割（Otsu）: 亮像素 {int(cv2.countNonZero(bright))} "
                   f"({int(cv2.countNonZero(bright))/total*100:.1f}%)")

        # 连通域分析
        nlab, labels, stats, cents = cv2.connectedComponentsWithStats(bright, 8)
        comps = []
        for i in range(1, nlab):
            area = stats[i, cv2.CC_STAT_AREA]
            if area < 12:
                continue
            m = (labels == i)
            hsv_m = hsv[m]
            hue = hsv_m[:, 0].astype(float).mean()
            v = hsv_m[:, 2].astype(float).mean()
            cy = cents[i][1]
            # 按色相归类
            if hue < 11 or hue > 170:
                col = "red"
            elif 15 <= hue <= 35:
                col = "yellow"
            elif 40 <= hue <= 90:
                col = "green"
            else:
                col = f"hue{hue:.0f}"
            comps.append((area, col, round(v, 0), round(cy, 1), round(hue, 1)))
        comps.sort(reverse=True)
        out.append(f"  亮区连通域（按面积排序，最多 6 个）:")
        out.append(f"     {'面积':>6} {'颜色':8} {'亮度V':>6} {'y位置':>6} {'色相H':>6}")
        for a, col, v, cy, hue in comps[:6]:
            pos = "上" if cy < roi.shape[0] / 3 else ("中" if cy < roi.shape[0] * 2 / 3 else "下")
            out.append(f"     {a:>6} {col:8} {v:>6} {cy:>6} ({pos})  {hue:>6}")

        if comps:
            biggest = comps[0]
            out.append("")
            out.append(f"  ⭐ 最大亮区颜色 = {biggest[1]}  (面积 {biggest[0]}, 亮度 {biggest[2]}, "
                       f"位置 y={biggest[3]})")
            out.append(f"     真值 = 红灯")
            verdict = "✅ 与真值一致" if biggest[1] == "red" else "❌ 与真值不符"
            out.append(f"     判定: {verdict}")
            # 保存该 ROI 便于人工看
            cv2.imwrite(os.path.join(OUT, f"roi_{n}_hsv.png"), roi)
            cv2.imwrite(os.path.join(OUT, f"roi_{n}_bright.png"), bright)

out.append("")
out.append("=" * 74)
out.append("结论")
out.append("=" * 74)
out.append("  若「整体颜色占比」偏向 yellow、而「最大亮区颜色」为 red，")
out.append("  则证明：**当前判色看的是灯箱外壳，应该改成看点亮的那盏灯**。")

io.open(r"E:\output\_tl_rootcause.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
