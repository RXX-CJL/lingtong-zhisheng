"""用色域阈值直接回答：这批渲染图里到底有没有「明亮的红」「明亮的绿」？

对 A_default 的红态图与绿态图，分别统计：
  * 亮红像素（R 明显高于 G/B 且够亮）
  * 亮绿像素（G 明显高于 R/B 且够亮）
  * 亮青/蓝像素
并把命中的位置画到图上、裁图放大，供肉眼核对。
"""
import os
import sys

import numpy as np
import cv2

D = r"E:\output\_lightup2"
OUT = r"E:\output\_lightup2"


def masks(img):
    b, g, r = [img[:, :, i].astype(np.int16) for i in range(3)]
    v = np.maximum(np.maximum(b, g), r)
    bright = v > 110
    red = ((r > g + 25) & (r > b + 25) & bright)
    grn = ((g > r + 25) & (g > b + 15) & bright)
    cyan = ((b > r + 30) & (g > r + 20) & bright)
    return {"red": red, "green": grn, "cyan": cyan}, v


def main():
    tiles = []
    for state in ("red", "green"):
        p = os.path.join(D, "A_default_%s.png" % state)
        img = cv2.imread(p)
        if img is None:
            print("缺图", p)
            continue
        m, v = masks(img)
        print("\n=== A_default %s ===" % state.upper())
        vis = img.copy()
        for name, mk in m.items():
            n = int(mk.sum())
            print("  亮%s像素: %-6d" % (name, n), end="")
            if n > 0:
                ys, xs = np.nonzero(mk)
                print("  bbox x %d..%d y %d..%d" % (xs.min(), xs.max(), ys.min(), ys.max()), end="")
                # 最大的几个连通块
                mm = cv2.morphologyEx(mk.astype(np.uint8) * 255, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
                nc, lab, st, ce = cv2.connectedComponentsWithStats(mm, 8)
                blobs = sorted([(int(st[i, cv2.CC_STAT_AREA]), int(ce[i][0]), int(ce[i][1]))
                                for i in range(1, nc)], reverse=True)[:4]
                for a, cx, cy in blobs:
                    b_, g_, r_ = [int(img[cy, cx, k]) for k in range(3)]
                    print("\n      blob area=%-4d @(%4d,%4d) BGR=(%3d,%3d,%3d)" % (a, cx, cy, b_, g_, r_), end="")
                    # 裁图
                    hw = 26
                    x0, y0 = max(0, cx - hw), max(0, cy - hw)
                    x1, y1 = min(img.shape[1], cx + hw), min(img.shape[0], cy + hw)
                    c = img[y0:y1, x0:x1]
                    if c.size:
                        z = cv2.resize(c, (180, 180), interpolation=cv2.INTER_NEAREST)
                        cv2.putText(z, "%s %s" % (state[:3].upper(), name[:4]), (3, 15),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)
                        cv2.putText(z, "(%d,%d)" % (cx, cy), (3, 174), cv2.FONT_HERSHEY_SIMPLEX,
                                    0.42, (255, 255, 255), 1, cv2.LINE_AA)
                        tiles.append(z)
                        cv2.rectangle(vis, (x0, y0), (x1, y1), (0, 255, 255), 2)
        # 用颜色叠加显示掩膜分布
        ov = img.copy()
        ov[m["red"]] = (0, 0, 255)
        ov[m["green"]] = (0, 255, 0)
        ov[m["cyan"]] = (255, 255, 0)
        cv2.imwrite(os.path.join(OUT, "mask_%s.png" % state), ov)
        print()
        print("   掩膜叠加图: %s" % os.path.join(OUT, "mask_%s.png" % state))
    if tiles:
        while len(tiles) % 5:
            tiles.append(np.zeros((180, 180, 3), np.uint8))
        sheet = np.vstack([np.hstack(tiles[i:i + 5]) for i in range(0, len(tiles), 5)])
        p = os.path.join(OUT, "colour_blobs.png")
        cv2.imwrite(p, sheet)
        print("\n★ 彩色块裁图:", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
