"""Measure the REAL lit-lens colours across states, using the top-N% brightest
pixels (robust, no local-contrast filtering -- the previous glow finder wrongly
required the lens to be brighter than its surround and rejected the green lens).
"""
import glob
import os
import sys

import cv2
import numpy as np

SRC = r"E:\output\_tl_glow_eval"


def lens_colour(img, pct=10):
    """Mean BGR of the brightest pct% of pixels + plain BGR mean."""
    v = img.max(axis=2).astype(np.float32)
    thr = np.percentile(v, 100 - pct)
    sel = v >= thr
    b, g, r = [float(img[:, :, i][sel].mean()) for i in range(3)]
    ab, ag, ar = [float(img[:, :, i].mean()) for i in range(3)]
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h = float(np.median(hsv[:, :, 0][sel]))
    s = float(hsv[:, :, 1][sel].mean())
    return {"b": b, "g": g, "r": r, "ab": ab, "ag": ag, "ar": ar, "hue": h, "sat": s,
            "sel": int(sel.sum()), "total": int(v.size)}


def main():
    files = sorted(glob.glob(os.path.join(SRC, "eval_*.png")))
    print("%-16s %-18s %-24s %-7s %-7s %s"
          % ("crop", "bright-top10% BGR", "all-pixels BGR", "hue", "sat", "max channel"))
    for f in files:
        img = cv2.imread(f, cv2.IMREAD_COLOR)
        if img is None:
            continue
        name = os.path.basename(f)[5:-4]
        c = lens_colour(img)
        mx = max(("B", c["b"]), ("G", c["g"]), ("R", c["r"]), key=lambda t: t[1])[0]
        print("%-16s (%6.1f,%6.1f,%6.1f) (%6.1f,%6.1f,%6.1f) %-7.0f %-7.0f %s"
              % (name, c["b"], c["g"], c["r"], c["ab"], c["ag"], c["ar"], c["hue"], c["sat"], mx))

    # what does a simple max-channel rule give?
    print("\nsimple rule: max channel of the brightest 10%% -> colour")
    for f in files:
        img = cv2.imread(f, cv2.IMREAD_COLOR)
        if img is None:
            continue
        name = os.path.basename(f)[5:-4]
        truth = name.split("_")[0]
        c = lens_colour(img)
        if c["g"] >= c["b"] and c["g"] >= c["r"]:
            pred = "green"
        elif c["r"] >= c["g"] and c["r"] >= c["b"]:
            pred = "red"
        else:
            pred = "blue"
        print("   %-16s truth=%-7s pred=%-7s %s" % (name, truth, pred,
                                                    "OK" if pred == truth else "MISS"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
