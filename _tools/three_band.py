# -*- coding: utf-8 -*-
import cv2, numpy as np, os
# 关键判据：信号灯是"上中下三段哪个亮"，不依赖绝对色值
f = r"E:\output\1\api\output\event_videos\20261101\evt_10550_6_3934e4_frame_89.jpg"
img = cv2.imread(f)
x1,y1,x2,y2 = 988,110,1028,182     # ROI 0，高 72px
h = y2 - y1
thirds = [("上段(红位)", y1, y1+h//3), ("中段(黄位)", y1+h//3, y1+2*h//3), ("下段(绿位)", y1+2*h//3, y2)]

print("=== ROI0 三段亮度对比（判断哪个位置的灯在亮）===")
vals = []
for name, a, b in thirds:
    crop = img[a:b, x1:x2].reshape(-1,3).astype(int)
    lum = crop.sum(axis=1)
    top = crop[np.argsort(lum)[-max(1,len(lum)//5):]]   # 该段最亮 20%
    B,G,R = top[:,0].mean(), top[:,1].mean(), top[:,2].mean()
    bright = (R+G+B)/3
    vals.append((name, bright, R, G, B))
    print("  %-12s 亮度=%6.1f  R=%3.0f G=%3.0f B=%3.0f" % (name, bright, R, G, B))

vals.sort(key=lambda v: -v[1])
print("\n  → 最亮的是: %s  （其余两段亮度差 %.0f / %.0f）" % (
    vals[0][0], vals[0][1]-vals[1][1], vals[0][1]-vals[2][1]))
print("  → CARLA 信号灯自上而下 = 红 / 黄 / 绿")
print("  → 判定: %s" % ("红灯（上段亮）" if "上段" in vals[0][0] else
                        ("黄灯（中段亮）" if "中段" in vals[0][0] else "绿灯（下段亮）")))
