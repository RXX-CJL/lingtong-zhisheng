"""Visualise the lens-centred CARLA crops next to the deployed expansion, with
per-crop channel stats, so the failure is visible rather than inferred.
"""
import glob
import os
import re
import sys

import cv2
import numpy as np

SRC = r"E:\output\_tl_glow_eval"
OUT = r"E:\output\_tl_glow_eval\carla_centred_montage.png"
TILE = 300


def main():
    files = sorted(glob.glob(os.path.join(SRC, "eval_*.png")))
    tiles = []
    for f in files:
        img = cv2.imread(f, cv2.IMREAD_COLOR)
        if img is None:
            continue
        name = os.path.basename(f)[5:-4]
        b, g, r = [float(img[:, :, i].mean()) for i in range(3)]
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        # brightest 10% of pixels: what colour are they?
        v = hsv[:, :, 2]
        thr = np.percentile(v, 90)
        sel = v >= thr
        bb, gg, rr = [float(img[:, :, i][sel].mean()) for i in range(3)]
        h, w = img.shape[:2]
        sc = min(TILE / max(1, w), TILE / max(1, h), 6.0)
        rs = cv2.resize(img, (max(1, int(w * sc)), max(1, int(h * sc))), interpolation=cv2.INTER_NEAREST)
        canvas = np.zeros((TILE + 64, TILE, 3), np.uint8)
        y0 = 40 + (TILE - rs.shape[0]) // 2
        x0 = (TILE - rs.shape[1]) // 2
        if y0 >= 40 and x0 >= 0 and y0 + rs.shape[0] <= TILE + 64 and x0 + rs.shape[1] <= TILE:
            canvas[y0:y0 + rs.shape[0], x0:x0 + rs.shape[1]] = rs
        truth = name.split("_")[0]
        col = {"red": (0, 0, 255), "green": (0, 255, 0), "yellow": (0, 255, 255)}.get(truth, (200, 200, 200))
        cv2.putText(canvas, "%s %s" % (truth[:3], name.split("_")[-1]), (4, 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, col, 1, cv2.LINE_AA)
        cv2.putText(canvas, "all B%.0f G%.0f R%.0f" % (b, g, r), (4, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, (200, 200, 200), 1, cv2.LINE_AA)
        cv2.putText(canvas, "top10%% B%.0f G%.0f R%.0f" % (bb, gg, rr), (4, TILE + 44),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(canvas, "%dx%d" % (w, h), (4, TILE + 58),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, (160, 160, 160), 1, cv2.LINE_AA)
        tiles.append(canvas)
    if not tiles:
        print("no crops found in", SRC)
        return 1
    cols = 4
    while len(tiles) % cols:
        tiles.append(np.zeros_like(tiles[0]))
    rows = [np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]
    sheet = np.vstack(rows)
    cv2.imwrite(OUT, sheet)
    print("wrote %s (%dx%d), %d crops" % (OUT, sheet.shape[1], sheet.shape[0], len(files)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
