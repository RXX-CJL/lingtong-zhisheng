# -*- coding: utf-8 -*-
import cv2, os
p = r'E:\output\1\carla\仿真输出\超速.mp4'
out = r'E:\output\_scripts\_speedframes'
os.makedirs(out, exist_ok=True)
cap = cv2.VideoCapture(p)
n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
for tag, idx in (('a_0', 0), ('b_300', 300), ('c_600', 600), ('d_890', min(890, n-1))):
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ok, fr = cap.read()
    if ok:
        f = os.path.join(out, tag + '.png')
        cv2.imwrite(f, fr)
        print('saved', f, fr.shape)
cap.release()