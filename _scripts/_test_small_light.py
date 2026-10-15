"""Test the classifier on CARLA-realistic SMALL light crops.

The user's camera puts the signal head at 43 m -> about 12 x 47 px at 1080p.
Render a synthetic crop at that size for red / green / yellow and put it through
the deployed path (25% expanded ROI). If CNN4 cannot see a 12 px light, the
colour step fails no matter what the classifier is.
"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, r"E:\output\1\api")
OUT = r"E:\output\_tl_glow_eval"
os.makedirs(OUT, exist_ok=True)

# CARLA-ish lamp colours (BGR) for the LIT lens, on a dark grey housing
LIT = {"red": (40, 40, 245), "yellow": (40, 225, 245), "green": (60, 230, 60)}
DIM = {"red": (28, 28, 78), "yellow": (30, 74, 80), "green": (34, 76, 36)}


def make_crop(state, w, h):
    """A vertical 3-lens housing of size w x h with one lens lit."""
    img = np.full((h, w, 3), 58, np.uint8)          # grey housing
    img = cv2.rectangle(img, (0, 0), (w - 1, h - 1), (42, 42, 42), 1)
    third = h // 3
    order = ["red", "yellow", "green"]
    for i, s in enumerate(order):
        y0 = i * third
        y1 = y0 + third
        cx = w // 2
        ry = max(1, min(third, w) // 2 - 1)
        col = LIT[s] if s == state else DIM[s]
        cv2.circle(img, (cx, (y0 + y1) // 2), ry, col, -1, cv2.LINE_AA)
    return img


def expand(img, frac=0.25):
    h, w = img.shape[:2]
    py, px = int(h * frac), int(w * frac)
    return cv2.copyMakeBorder(img, py, py, px, px, cv2.BORDER_REPLICATE)


def main():
    import traffic_light_classifier as tlc
    if not tlc.is_available():
        print("CNN unavailable")
        return 1

    print("CARLA-realistic small light heads through the DEPLOYED path (25% expanded)\n")
    print("%-8s %-8s %-9s %-8s %-9s %-8s %s"
          % ("truth", "size", "CNN", "conf", "HSV(raw)", "HSV(exp)", "verdict"))
    tiles = []
    for w, h in ((12, 47), (20, 78), (34, 130), (64, 250)):
        for state in ("red", "yellow", "green"):
            img = make_crop(state, w, h)
            cnn, conf = tlc.classify_traffic_light(expand(img))
            hsv = tlc.hsv_fallback_state(img)
            hsve = tlc.hsv_fallback_state(expand(img))
            ok_cnn = "OK" if cnn == state else ("MISS->%s" % cnn)
            ok_hsv = "OK" if hsv == state else ("MISS->%s" % hsv)
            print("%-8s %-8s %-9s %-8.3f %-8s %-9s CNN:%s  HSV:%s"
                  % (state, "%dx%d" % (w, h), cnn, conf, hsv, hsve, ok_cnn, ok_hsv))
            big = cv2.resize(img, (max(60, w * 3), max(150, h * 3)), interpolation=cv2.INTER_NEAREST)
            canvas = np.zeros((190, 130, 3), np.uint8)
            sc = min(120 / big.shape[1], 150 / big.shape[0])
            rs = cv2.resize(big, (max(1, int(big.shape[1] * sc)), max(1, int(big.shape[0] * sc))),
                            interpolation=cv2.INTER_NEAREST)
            y0 = (150 - rs.shape[0]) // 2
            x0 = (130 - rs.shape[1]) // 2
            canvas[y0:y0 + rs.shape[0], x0:x0 + rs.shape[1]] = rs
            col = {"red": (0, 0, 255), "green": (0, 255, 0), "yellow": (0, 255, 255)}[state]
            cv2.putText(canvas, "%s %dx%d" % (state[:3], w, h), (2, 164),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.40, col, 1, cv2.LINE_AA)
            cv2.putText(canvas, "CNN %s" % cnn[:3], (2, 176),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.40,
                        (0, 255, 0) if cnn == state else (0, 0, 255), 1, cv2.LINE_AA)
            cv2.putText(canvas, "HSV %s" % hsv[:3], (2, 187),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.40,
                        (0, 255, 0) if hsv == state else (0, 0, 255), 1, cv2.LINE_AA)
            tiles.append(canvas)

    if tiles:
        cols = 6
        while len(tiles) % cols:
            tiles.append(np.zeros_like(tiles[0]))
        rows = [np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]
        sheet = np.vstack(rows)
        cv2.imwrite(os.path.join(OUT, "small_light_test.png"), sheet)
        print("\nwrote small_light_test.png (%dx%d)" % (sheet.shape[1], sheet.shape[0]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
