# -*- coding: utf-8 -*-
import cv2, os, numpy as np
os.chdir(r"E:\output\1\api")
SRC = r"E:\output\1\carla\仿真输出\超速.mp4"
print("源:", SRC, "存在:", os.path.exists(SRC))

cap = cv2.VideoCapture(SRC)
fps = cap.get(cv2.CAP_PROP_FPS) or 20
total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
print("fps=%.1f total=%d 时长=%.1fs" % (fps, total, total/fps))

ROI = (988,110,1028,182)   # 判决主灯
x1,y1,x2,y2 = ROI

def classify(r,g,b):
    # 归一化差值判断
    if r > 120 and g < r*0.55 and b < 120: return "RED"
    if g > 110 and g > r*0.75 and b < 130: return "GREEN"
    if r > 130 and g > r*0.62 and b < 110: return "YELLOW/AMBER"
    return "dim/off"

print("\n=== ROI0 逐秒采样（每 0.5s）===")
step = max(1, int(fps*0.5))
rows = []
for fi in range(0, total, step):
    cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
    ok, frame = cap.read()
    if not ok: break
    crop = frame[y1:y2, x1:x2]
    if crop.size == 0: continue
    flat = crop.reshape(-1,3).astype(int)
    lum = flat.sum(axis=1)
    idx = np.argsort(lum)[-max(1,len(lum)//12):]
    top = flat[idx]
    b,g,r = top[:,0].mean(), top[:,1].mean(), top[:,2].mean()
    c = classify(r,g,b)
    rows.append((fi, fi/fps, r, g, b, c))

for fi, t, r, g, b, c in rows:
    print("  帧%5d t=%5.1fs  R=%3.0f G=%3.0f B=%3.0f  -> %s" % (fi, t, r, g, b, c))

from collections import Counter
print("\n分布:", dict(Counter(x[5] for x in rows)))
cap.release()
