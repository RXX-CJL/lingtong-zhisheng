# -*- coding: utf-8 -*-
import cv2, os
os.chdir(r"E:\output\1\api")
OUT = r"E:\output\_uicheck"
SRC = r"E:\output\1\carla\仿真输出\超速.mp4"
cap = cv2.VideoCapture(SRC)
ROI = (988,110,1028,182)
x1,y1,x2,y2 = ROI
for fi in [0, 300, 390, 600]:
    cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
    ok, fr = cap.read()
    if not ok: continue
    crop = fr[y1:y2, x1:x2]
    big = cv2.resize(crop, None, fx=8, fy=8, interpolation=cv2.INTER_NEAREST)
    p = os.path.join(OUT, "src_roi0_f%d.png" % fi)
    cv2.imwrite(p, big)
    print("写出", p, crop.shape)
cap.release()

# 对比：event 帧的同一 ROI 均值
ev = cv2.imread(r"E:\output\1\api\output\event_videos\20261101\evt_10550_6_3934e4_frame_89.jpg")
c2 = ev[y1:y2, x1:x2]
import numpy as np
print("event 帧 ROI0 均值 BGR =", c2.reshape(-1,3).mean(axis=0).round(1))
