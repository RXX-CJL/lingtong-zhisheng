"""针对用户的质疑，用"用户自己的画面"核对灯的实际颜色。

对用户机位画面里每一处信号灯：裁出原图 + 并排贴出"该处实测的像素平均色"，
让用户一眼看出我测的到底是什么颜色。
"""
import os
import sys

import cv2
import numpy as np

SRC = r"E:\output\_camera_verify\reference_1080.png"
OUT = r"E:\output\_tl_glow_eval\user_signal_truecolours.png"

# 用户画面里检出的信号灯候选（位置来自 confirm_1080 的黄色/绿色高饱和紧凑斑块）
SPOTS = [
    (897, 232, "A"),
    (1196, 256, "B"),
    (784, 251, "C"),
    (225, 334, "D"),
    (1163, 144, "E"),
    (1011, 140, "F"),
]


def name_of(b, g, r):
    px = np.uint8([[[int(b), int(g), int(r)]]])
    h, s, v = cv2.cvtColor(px, cv2.COLOR_BGR2HSV)[0, 0]
    hue = int(h) * 2
    if s < 40:
        return "grey/white s=%d" % s
    if hue < 15 or hue >= 345:
        return "RED hue=%d" % hue
    if hue < 45:
        return "ORANGE hue=%d" % hue
    if hue < 70:
        return "YELLOW hue=%d" % hue
    if hue < 100:
        return "YELLOW-GREEN hue=%d" % hue
    if hue < 150:
        return "GREEN hue=%d" % hue
    if hue < 200:
        return "CYAN hue=%d" % hue
    if hue < 260:
        return "BLUE hue=%d" % hue
    return "PURPLE hue=%d" % hue


def main():
    img = cv2.imread(SRC)
    if img is None:
        print("missing", SRC)
        return 1
    H, W = img.shape[:2]
    tiles = []
    print("用户画面 reference_1080.png —— 每处信号灯的实测颜色\n")
    print("%-4s %-14s %-22s %s" % ("spot", "at", "BGR", "判定"))
    for x, y, tag in SPOTS:
        half = 46
        x0, y0 = max(0, x - half), max(0, y - half)
        crop = img[y0:y0 + 2 * half, x0:x0 + 2 * half].copy()
        if crop.shape[0] != 2 * half or crop.shape[1] != 2 * half:
            c = np.zeros((2 * half, 2 * half, 3), np.uint8)
            c[:crop.shape[0], :crop.shape[1]] = crop
            crop = c
        # 该处最亮 25% 像素的平均色 = 灯珠颜色
        g_ = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        sel = g_ >= np.percentile(g_, 75)
        b, gg, r = [float(crop[:, :, i][sel].mean()) for i in range(3)]
        nm = name_of(b, gg, r)
        print("%-4s (%4d,%4d)   (%6.1f,%6.1f,%6.1f)  %s" % (tag, x, y, b, gg, r, nm))

        big = cv2.resize(crop, (200, 200), interpolation=cv2.INTER_NEAREST)
        cv2.drawMarker(big, (100, 100), (255, 0, 255), cv2.MARKER_CROSS, 24, 2)
        canvas = np.zeros((268, 200, 3), np.uint8)
        canvas[:200] = big
        canvas[204:238] = (int(b), int(gg), int(r))       # 实测色的纯色块
        cv2.putText(canvas, "spot %s" % tag, (4, 252), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(canvas, nm[:30], (4, 264), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (200, 200, 200), 1, cv2.LINE_AA)
        tiles.append(canvas)

    sheet = np.hstack(tiles)
    cv2.imwrite(OUT, sheet)
    print("\nwrote %s" % OUT)
    print("（每格：上面是原图裁切，下面是该处实测像素的平均色块）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
