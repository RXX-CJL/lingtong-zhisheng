"""Score the classifiers against REAL CARLA lens crops with verified ground truth.

This is the closest available proxy for the demo footage: same renderer, same
light geometry, states machine-verified (not human-guessed).
"""
import glob
import json
import os
import re
import sys
from collections import Counter

import cv2
import numpy as np

sys.path.insert(0, r"E:\output\1\api")
SRC = r"E:\output\_tl_carla2"


def expand(img, frac=0.25):
    h, w = img.shape[:2]
    py, px = int(h * frac), int(w * frac)
    return cv2.copyMakeBorder(img, py, py, px, px, cv2.BORDER_REPLICATE)


def main():
    import traffic_light_classifier as tlc
    if not tlc.is_available():
        print("CNN unavailable")
        return 1

    pat = re.compile(r"^(red|green|yellow)_(\d+)m_(\d+)x(\d+)\.png$")
    rows = []
    for f in sorted(glob.glob(os.path.join(SRC, "*.png"))):
        m = pat.match(os.path.basename(f))
        if not m:
            continue
        truth, dist, cw, ch = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
        img = cv2.imread(f, cv2.IMREAD_COLOR)
        if img is None or img.size == 0:
            continue
        cnn, conf = tlc.classify_traffic_light(expand(img))
        hsv = tlc.hsv_fallback_state(img)
        rows.append({"truth": truth, "dist": dist, "size": "%sx%s" % (cw, ch),
                     "cnn": cnn, "conf": conf, "hsv": hsv, "file": os.path.basename(f)})

    print("%-8s %-5s %-9s %-9s %-7s %-9s %s"
          % ("truth", "dist", "size", "CNN", "conf", "HSV", "verdict"))
    for r in rows:
        v = []
        v.append("CNN ok" if r["cnn"] == r["truth"] else "CNN MISS(%s)" % r["cnn"])
        v.append("HSV ok" if r["hsv"] == r["truth"] else "HSV MISS(%s)" % r["hsv"])
        print("%-8s %-5d %-9s %-9s %-7.3f %-9s %s"
              % (r["truth"], r["dist"], r["size"], r["cnn"], r["conf"], r["hsv"], "  ".join(v)))

    n = len(rows)
    ok_cnn = sum(1 for r in rows if r["cnn"] == r["truth"])
    ok_hsv = sum(1 for r in rows if r["hsv"] == r["truth"])
    print("\n" + "=" * 74)
    print("REAL CARLA LENS CROPS (states machine-verified): n=%d" % n)
    print("=" * 74)
    print("  CNN4 : %d/%d = %.1f%%" % (ok_cnn, n, 100 * ok_cnn / max(1, n)))
    print("  HSV  : %d/%d = %.1f%%" % (ok_hsv, n, 100 * ok_hsv / max(1, n)))

    print("\nper state:")
    for st in ("red", "green", "yellow"):
        sub = [r for r in rows if r["truth"] == st]
        if not sub:
            continue
        c = sum(1 for r in sub if r["cnn"] == st)
        h = sum(1 for r in sub if r["hsv"] == st)
        print("   %-7s n=%d  CNN %d/%d   HSV %d/%d" % (st, len(sub), c, len(sub), h, len(sub)))

    print("\nCNN confusion:", dict(Counter((r["truth"], r["cnn"]) for r in rows)))
    print("HSV confusion:", dict(Counter((r["truth"], r["hsv"]) for r in rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
