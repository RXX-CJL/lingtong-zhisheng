"""决定性测试：CAM-2 特写里"单独一颗点亮的灯珠"喂判色器，能否判出颜色？

思路：CAM-2 视图里灯头是 32x96 的竖条，内部有 3 颗镜片。
把灯头竖条按上/中/下三等分，分别裁出来喂 CNN4，看哪一颗被判出颜色、判成什么。
真值：Red 态应点亮最上面那颗；Green 态最下面那颗；Yellow 态中间那颗。
"""
import os
import sys

import numpy as np
import cv2

sys.path.insert(0, r"E:\output\1\api")
from traffic_light_classifier import (classify_traffic_light, classify_with_glow,
                                      find_glow_region)  # noqa: E402

D = r"E:\output\_cam2_diag"
OUT = r"E:\output\_cam2_diag"


def lum(img, x0, y0, x1, y1):
    roi = img[y0:y1, x0:x1]
    if roi.size == 0:
        return None
    b, g, r = [float(roi[:, :, i].mean()) for i in range(3)]
    hsv = cv2.cvtColor(np.uint8([[[int(b), int(g), int(r)]]]), cv2.COLOR_BGR2HSV)[0, 0]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    return {"bgr": (b, g, r), "hue": int(hsv[0]) * 2, "sat": int(hsv[1]),
            "v": float(gray.mean()), "peak": int(gray.max())}


def nm(hue, sat):
    if sat < 45:
        return "grey"
    if hue < 20 or hue >= 340:
        return "RED"
    if hue < 45:
        return "orange"
    if hue < 70:
        return "yellow"
    if hue < 100:
        return "yellow-green"
    if hue < 150:
        return "GREEN"
    if hue < 200:
        return "cyan"
    if hue < 260:
        return "blue"
    return "purple"


def main():
    # 灯头竖条位置（从上一轮扫描得到）：两处 32x96 的块，中心 (961,351) 与 (638,350)
    HEADS = [(961, 351), (638, 350)]
    print("真值：Red 态点亮最上镜片 / Green 态最下 / Yellow 态中间\n")
    tiles = []
    for tag, truth in (("red", "RED"), ("green", "GREEN"), ("yellow", "YELLOW")):
        p = os.path.join(D, "cam2_%s.png" % tag)
        img = cv2.imread(p)
        if img is None:
            print("缺图", p)
            continue
        print("=== %s (真值 %s) ===" % (tag.upper(), truth))
        for hi, (cx, cy) in enumerate(HEADS):
            # 灯头竖条：以中心为基准，宽 32 高 96 -> 三颗镜片各 32 高
            hw, hh = 18, 50
            x0, y0 = cx - hw, cy - hh
            x1, y1 = cx + hw, cy + hh
            print("  灯头#%d 竖条 (%d,%d)-(%d,%d):" % (hi, x0, y0, x1, y1))
            third = (y1 - y0) // 3
            for k, lens in enumerate(("UPPER", "MIDDLE", "LOWER")):
                ly0 = y0 + k * third
                ly1 = ly0 + third
                st = lum(img, x0, ly0, x1, ly1)
                if st is None:
                    continue
                # 喂判色器：给一个包含该镜片及少量上下文的裁图
                pad = 4
                crop = img[max(0, ly0 - pad):ly1 + pad, max(0, x0 - pad):x1 + pad]
                cnn, conf = classify_traffic_light(crop)
                gl = find_glow_region(crop)
                hit = "✅" if (cnn == truth.lower() or
                              (truth == "RED" and cnn == "red")) else ""
                print("     %-6s V=%-6.1f BGR=(%5.1f,%5.1f,%5.1f) h=%-3d %-11s | CNN4=%-8s %.2f %s"
                      % (lens, st["v"], st["bgr"][0], st["bgr"][1], st["bgr"][2],
                         st["hue"], nm(st["hue"], st["sat"]), cnn, conf, hit))
                z = cv2.resize(crop, (120, 200), interpolation=cv2.INTER_NEAREST)
                cv2.putText(z, "%s %s" % (tag[:3].upper(), lens[:1]), (3, 14),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 255), 1, cv2.LINE_AA)
                cv2.putText(z, cnn[:5], (3, 192), cv2.FONT_HERSHEY_SIMPLEX, 0.42,
                            (0, 255, 0), 1, cv2.LINE_AA)
                tiles.append(z)
        print()
    if tiles:
        while len(tiles) % 6:
            tiles.append(np.zeros((200, 120, 3), np.uint8))
        sheet = np.vstack([np.hstack(tiles[i:i + 6]) for i in range(0, len(tiles), 6)])
        p = os.path.join(OUT, "cam2_lens_rows.png")
        cv2.imwrite(p, sheet)
        print("灯珠裁图（每行=一个灯态，三列=上/中/下镜片）:", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
