"""Build a montage of real traffic-light crops with brightness stats, so the
colour-judging problem can be seen rather than guessed.

Reads E:\\output\\_tl_crops2 (real video crops) and labels each tile with
size / labelled state / mean V / max V / saturated-pixel count.
"""
import glob
import os
import sys

import cv2
import numpy as np

SRC = r"E:\output\_tl_crops2"
OUT = r"E:\output\_tl_glow_eval"
os.makedirs(OUT, exist_ok=True)

TILE = 160
PAD = 26


def stats(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    H, S, V = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    return {
        "h": img.shape[0], "w": img.shape[1],
        "v_mean": float(V.mean()), "v_max": int(V.max()),
        "s_mean": float(S.mean()),
        "bright": int(((S > 90) & (V > 150)).sum()),
        "dark": int(V.mean() < 60),
    }


def main():
    files = sorted(glob.glob(os.path.join(SRC, "*.png")))
    print("%-46s %-9s %-7s %-6s %-6s %-8s %s" %
          ("file", "state", "size", "Vmean", "Vmax", "bright", "dark?"))
    tiles = []
    for f in files:
        img = cv2.imread(f, cv2.IMREAD_COLOR)
        if img is None:
            continue
        name = os.path.basename(f)
        st = name.rsplit("_", 2)[-2] if name.count("_") >= 2 else "?"
        s = stats(img)
        print("%-46s %-9s %-7s %-6.1f %-6d %-8d %s"
              % (name[:46], st, "%dx%d" % (s["w"], s["h"]), s["v_mean"], s["v_max"],
                 s["bright"], "DARK" if s["dark"] else ""))
        # resize preserving aspect to TILE
        h, w = img.shape[:2]
        sc = min(TILE / max(1, w), TILE / max(1, h))
        rs = cv2.resize(img, (max(1, int(w * sc)), max(1, int(h * sc))),
                        interpolation=cv2.INTER_NEAREST)
        canvas = np.zeros((TILE + PAD, TILE, 3), np.uint8)
        y0 = PAD + (TILE - rs.shape[0]) // 2
        x0 = (TILE - rs.shape[1]) // 2
        canvas[y0:y0 + rs.shape[0], x0:x0 + rs.shape[1]] = rs
        col = {"red": (0, 0, 255), "green": (0, 255, 0), "yellow": (0, 255, 255)}.get(st, (180, 180, 180))
        cv2.putText(canvas, "%s %dx%d" % (st[:3], w, h), (2, 16), cv2.FONT_HERSHEY_SIMPLEX,
                    0.42, col, 1, cv2.LINE_AA)
        cv2.putText(canvas, "V%.0f/%d b%d" % (s["v_mean"], s["v_max"], s["bright"]),
                    (2, TILE + PAD - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 200, 200), 1, cv2.LINE_AA)
        tiles.append(canvas)

    if tiles:
        cols = 7
        while len(tiles) % cols:
            tiles.append(np.zeros_like(tiles[0]))
        rows = [np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]
        sheet = np.vstack(rows)
        cv2.imwrite(os.path.join(OUT, "real_crops_montage.png"), sheet)
        print("\nwrote %s  (%dx%d)" % (os.path.join(OUT, "real_crops_montage.png"),
                                       sheet.shape[1], sheet.shape[0]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
