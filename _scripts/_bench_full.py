"""Full-dataset benchmark: CNN4 (25% expanded, as deployed) vs HSV, over
E:\\output\\_tl_dataset (378 files: red 54 / green 48 / yellow 15 / none 260).

The 260 "none" samples matter most: they are exactly where HSV previously
"hard-guessed" a colour, which is why HSV was disabled. Measuring that rate is
the decisive test of whether re-enabling HSV is safe.
"""
import glob
import os
import sys
import time
from collections import Counter

import cv2
import numpy as np

sys.path.insert(0, r"E:\output\1\api")
ROOT = r"E:\output\_tl_dataset"


def expand(img, frac=0.25):
    h, w = img.shape[:2]
    py, px = int(h * frac), int(w * frac)
    return cv2.copyMakeBorder(img, py, py, px, px, cv2.BORDER_REPLICATE)


def main():
    import traffic_light_classifier as tlc
    if not tlc.is_available():
        print("CNN unavailable")
        return 1

    truth_map = {"red": "red", "green": "green", "yellow": "yellow", "none": "none"}
    recs = []
    t0 = time.time()
    for cls, want in truth_map.items():
        for f in sorted(glob.glob(os.path.join(ROOT, cls, "*.png"))):
            img = cv2.imread(f, cv2.IMREAD_COLOR)
            if img is None or img.size == 0:
                continue
            cnn, conf = tlc.classify_traffic_light(expand(img))
            hsv = tlc.hsv_fallback_state(img)
            hsve = tlc.hsv_fallback_state(expand(img))
            recs.append({"truth": want, "cnn": cnn, "conf": conf, "hsv": hsv,
                         "hsv_exp": hsve, "file": os.path.basename(f),
                         "w": img.shape[1], "h": img.shape[0]})
    dt = time.time() - t0
    print("benchmarked %d samples in %.1f s (%.1f ms each, both classifiers)\n"
          % (len(recs), dt, 1000 * dt / max(1, len(recs))))

    def summarise(key, name):
        pos = [r for r in recs if r["truth"] in ("red", "green", "yellow")]
        neg = [r for r in recs if r["truth"] == "none"]
        ok = sum(1 for r in pos if r[key] == r["truth"])
        fp = sum(1 for r in neg if r[key] in ("red", "green", "yellow"))
        okn = sum(1 for r in neg if r[key] in ("none", "unknown"))
        # per class
        per = {}
        for c in ("red", "green", "yellow"):
            sub = [r for r in pos if r["truth"] == c]
            per[c] = "%d/%d" % (sum(1 for r in sub if r[key] == c), len(sub))
        print("%-26s colour %3d/%-3d = %5.1f%%   reject %3d/%-3d = %5.1f%%   FALSE-POSITIVE(colour on none) %3d (%.1f%%)"
              % (name, ok, len(pos), 100 * ok / max(1, len(pos)), okn, len(neg),
                 100 * okn / max(1, len(neg)), fp, 100 * fp / max(1, len(neg))))
        print("%-26s   red %-8s green %-8s yellow %-8s" % ("", per["red"], per["green"], per["yellow"]))
        return {"ok": ok, "pos": len(pos), "fp": fp, "neg": len(neg)}

    print("=" * 122)
    a = summarise("cnn", "CNN4 (25% expanded)")
    b = summarise("hsv", "HSV (raw crop)")
    c = summarise("hsv_exp", "HSV (25% expanded)")

    print("\nDANGEROUS-DIRECTION ERRORS on the colour set:")
    for key, name in (("cnn", "CNN4"), ("hsv", "HSV")):
        r2g = [r for r in recs if r["truth"] == "red" and r[key] == "green"]
        g2r = [r for r in recs if r["truth"] == "green" and r[key] == "red"]
        y2n = [r for r in recs if r["truth"] == "yellow" and r[key] == "none"]
        print("   %-6s red->green %-3d  green->red %-3d  yellow->none %d"
              % (name, len(r2g), len(g2r), len(y2n)))

    print("\nHSV false positives on 'none' samples -- sample of what it hard-guesses:")
    fps = [r for r in recs if r["truth"] == "none" and r["hsv"] in ("red", "green", "yellow")]
    cnt = Counter(r["hsv"] for r in fps)
    print("   total %d  ->  %s" % (len(fps), dict(cnt)))
    for r in fps[:12]:
        print("      %-30s %dx%-4d hsv=%s" % (r["file"][:30], r["w"], r["h"], r["hsv"]))

    print("\nCNN confusion (truth -> pred) on 'none':")
    print("  ", dict(Counter(r["cnn"] for r in recs if r["truth"] == "none")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
