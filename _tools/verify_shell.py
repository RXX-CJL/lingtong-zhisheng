# -*- coding: utf-8 -*-
import cv2, numpy as np
f = r"E:\output\1\api\output\event_videos\20261101\evt_10550_6_3934e4_frame_89.jpg"
img = cv2.imread(f)
x1,y1,x2,y2 = 988,110,1028,182
crop = img[y1:y2, x1:x2]
h = y2 - y1

print("=== 验证「灯壳是黄色」这个前提 ===")
# 1) 灯壳 = 每段里除最亮点之外的背景像素
for name, a, b in [("上段", y1, y1+h//3), ("中段", y1+h//3, y1+2*h//3), ("下段", y1+2*h//3, y2)]:
    seg = img[a:b, x1:x2].reshape(-1,3).astype(int)
    lum = seg.sum(axis=1)
    order = np.argsort(lum)
    # 最暗 40% 视为灯壳/背景（不亮的灯位 + 壳体）
    shell = seg[order[:max(1,int(len(seg)*0.4))]]
    B,G,R = shell[:,0].mean(), shell[:,1].mean(), shell[:,2].mean()
    print("  %s 壳体/暗部均值  R=%3.0f G=%3.0f B=%3.0f  R-B=%3.0f" % (name, R,G,B, R-B))

print()
print("=== 关键：红色灯芯 vs 黄色灯壳 在色相上分不分得开 ===")
flat = crop.reshape(-1,3).astype(int)
hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV).reshape(-1,3)
lum = flat.sum(axis=1)
top = np.argsort(lum)[-max(1,len(flat)//10):]
hues = hsv[top][:,0]
print("  最亮 10%% 像素的色相(H, 0-180)：中位=%.0f  范围=[%.0f, %.0f]" % (np.median(hues), hues.min(), hues.max()))
print("  参考：OpenCV 中 红≈0/180  橙≈15  黄≈30  绿≈60")
print("  → 今回最亮像素色相落在 %.0f 附近，属于%s" % (np.median(hues),
      "红-橙交界（红黄难分）" if 5 <= np.median(hues) <= 25 else "其他"))
