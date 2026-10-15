"""Measure the GLOW region of each real crop: where is the brightest compact area,
what are its BGR/HSV values, and does the hue survive the blow-out?

This decides whether "find the glow then judge hue" is viable on real footage.
"""
import glob
import os
import sys

import cv2
import numpy as np

SRC = r"E:\output\_tl_crops2"
OUT = r"E:\output\_tl_glow_eval"
os.makedirs(OUT, exist_ok=True)


def glow_region(img):
    """Largest compact region of high-saturation OR very-bright pixels."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    H, S, V = hsv[:, :, 0], hsv[:, :, 1].astype(np.int16), hsv[:, :, 2].astype(np.int16)
    grey = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    local = cv2.blur(grey.astype(np.float32), (15, 15))
    brighter = grey.astype(np.float32) > (local + 10)
    mask = (((S > 110) & (V > 140)) | (V > 235)) & brighter
    mask = mask.astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    n, lab, stats, cent = cv2.connectedComponentsWithStats(mask, 8)
    best = None
    for i in range(1, n):
        a = int(stats[i, cv2.CC_STAT_AREA])
        if best is None or a > best[0]:
            best = (a, i, cent[i], stats[i])
    if best is None:
        return None
    a, i, c, st = best
    sel = lab == i
    bgr = img[sel].mean(axis=0)
    hh = H[sel].astype(np.float32)
    # circular mean for hue (red wraps)
    ang = hh * (2 * np.pi / 180.0)
    hm = float(np.degrees(np.arctan2(np.sin(ang).mean(), np.cos(ang).mean())) % 180)
    return {"area": a, "cx": float(c[0]), "cy": float(c[1]),
            "w": int(st[cv2.CC_STAT_WIDTH]), "h": int(st[cv2.CC_STAT_HEIGHT]),
            "bgr": [round(float(v), 1) for v in bgr], "hue": round(hm, 1),
            "sat": round(float(S[sel].mean()), 1), "val": round(float(V[sel].mean()), 1),
            "frac": round(a / float(img.shape[0] * img.shape[1]), 4)}


def main():
    files = sorted(glob.glob(os.path.join(SRC, "*.png")))
    print("%-34s %-8s %-9s %-22s %-6s %-6s %-6s %s" %
          ("file", "label", "glow_area", "glow BGR", "hue", "sat", "val", "frac"))
    tiles = []
    for f in files:
        img = cv2.imread(f, cv2.IMREAD_COLOR)
        if img is None:
            continue
        name = os.path.basename(f)
        label = name.rsplit("_", 2)[-2]
        g = glow_region(img)
        if g is None:
            print("%-34s %-8s %s" % (name[:34], label, "NO GLOW FOUND"))
            continue
        print("%-34s %-8s %-9d %-22s %-6.1f %-6.1f %-6.1f %s"
              % (name[:34], label, g["area"], str(g["bgr"]), g["hue"], g["sat"], g["val"], g["frac"]))
        # visual: crop around the glow at 4x
        x0 = int(max(0, g["cx"] - 30)); y0 = int(max(0, g["cy"] - 30))
        crop = img[y0:y0 + 60, x0:x0 + 60]
        if crop.size == 0:
            crop = img
        rs = cv2.resize(crop, (150, 150), interpolation=cv2.INTER_NEAREST)
        cv2.drawMarker(rs, (int((g["cx"] - x0) * 150 / max(1, crop.shape[1])),
                            int((g["cy"] - y0) * 150 / max(1, crop.shape[0]))),
                       (255, 0, 255), cv2.MARKER_CROSS, 16, 2)
        canvas = np.zeros((176, 150, 3), np.uint8)
        canvas[:150] = rs
        col = {"red": (0, 0, 255), "green": (0, 255, 0), "yellow": (0, 255, 255)}.get(label, (180, 180, 180))
        cv2.putText(canvas, "%s h%.0f" % (label[:3], g["hue"]), (2, 164),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, col, 1, cv2.LINE_AA)
        cv2.putText(canvas, "B%d G%d R%d" % tuple(int(v) for v in g["bgr"]), (2, 174),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.36, (200, 200, 200), 1, cv2.LINE_AA)
        tiles.append(canvas)
    if tiles:
        cols = 7
        while len(tiles) % cols:
            tiles.append(np.zeros_like(tiles[0]))
        rows = [np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]
        sheet = np.vstack(rows)
        cv2.imwrite(os.path.join(OUT, "glow_region_montage.png"), sheet)
        print("\nwrote glow_region_montage.png (%dx%d)" % (sheet.shape[1], sheet.shape[0]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
