"""Measure the honest CARLA lens crops: per-state lens colour (hue, channel
dominance, saturation) and what the deployed classifiers say.
"""
import glob
import os
import re
import sys
from collections import Counter

import cv2
import numpy as np

sys.path.insert(0, r"E:\output\1\api")
SRC = r"E:\output\_tl_carla3"


def expand(img, frac=0.25):
    h, w = img.shape[:2]
    py, px = int(h * frac), int(w * frac)
    return cv2.copyMakeBorder(img, py, py, px, px, cv2.BORDER_REPLICATE)


def lens_stats(img):
    v = img.max(axis=2).astype(np.float32)
    sel = v >= np.percentile(v, 88)
    b, g, r = [float(img[:, :, i][sel].mean()) for i in range(3)]
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    return {"b": b, "g": g, "r": r,
            "hue": float(np.median(hsv[:, :, 0][sel])),
            "sat": float(hsv[:, :, 1][sel].mean()),
            "val": float(hsv[:, :, 2][sel].mean())}


def main():
    import traffic_light_classifier as tlc
    pat = re.compile(r"^(red|green|yellow)_(\d+)m_(\d+)x(\d+)\.png$")
    recs = []
    for f in sorted(glob.glob(os.path.join(SRC, "*.png"))):
        m = pat.match(os.path.basename(f))
        if not m:
            continue
        truth, dist, cw, ch = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
        img = cv2.imread(f, cv2.IMREAD_COLOR)
        if img is None or img.size == 0:
            continue
        s = lens_stats(img)
        cnn, conf = tlc.classify_traffic_light(expand(img))
        hsv = tlc.hsv_fallback_state(img)
        recs.append({"truth": truth, "dist": dist, "size": "%sx%s" % (cw, ch),
                     "cnn": cnn, "hsv": hsv, **s})

    print("%-8s %-5s %-9s %-24s %-6s %-6s %-6s %-9s %-9s %s"
          % ("truth", "dist", "size", "top12% BGR", "hue", "sat", "val", "CNN", "HSV", "max ch"))
    for r in recs:
        mx = max(("B", r["b"]), ("G", r["g"]), ("R", r["r"]), key=lambda t: t[1])[0]
        print("%-8s %-5d %-9s (%6.1f,%6.1f,%6.1f) %-6.0f %-6.0f %-6.0f %-9s %-9s %s"
              % (r["truth"], r["dist"], r["size"], r["b"], r["g"], r["r"],
                 r["hue"], r["sat"], r["val"], r["cnn"], r["hsv"], mx))

    n = len(recs)
    print("\n" + "=" * 100)
    print("HONEST CARLA LENS CROPS (housing-located, states verified)  n=%d" % n)
    print("=" * 100)
    okc = sum(1 for r in recs if r["cnn"] == r["truth"])
    okh = sum(1 for r in recs if r["hsv"] == r["truth"])
    print("   CNN4 : %d/%d = %.1f%%" % (okc, n, 100 * okc / max(1, n)))
    print("   HSV  : %d/%d = %.1f%%" % (okh, n, 100 * okh / max(1, n)))

    print("\nper-state median lens colour of the brightest 12%%:")
    for st in ("red", "yellow", "green"):
        sub = [r for r in recs if r["truth"] == st and r["size"] == "34x130"]
        if not sub:
            continue
        b = np.median([r["b"] for r in sub]); g = np.median([r["g"] for r in sub]); r_ = np.median([r["r"] for r in sub])
        hue = np.median([r["hue"] for r in sub]); sat = np.median([r["sat"] for r in sub])
        print("   %-7s BGR=(%6.1f,%6.1f,%6.1f)  hue=%5.0f  sat=%5.0f" % (st, b, g, r_, hue, sat))

    print("\nconfusions:")
    print("   CNN:", dict(Counter((r["truth"], r["cnn"]) for r in recs)))
    print("   HSV:", dict(Counter((r["truth"], r["hsv"]) for r in recs)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
