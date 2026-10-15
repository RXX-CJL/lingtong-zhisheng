"""Isolate WHY CNN4 scores 37.5% on the reviewed crops.

Hypothesis: the deployed pipeline feeds the CNN a 25%-expanded ROI, so a raw crop
is out-of-distribution. Test CNN4 on raw crops vs expanded crops (10/25/40%).
Also test HSV on the same two inputs.
"""
import glob
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, r"E:\output\1\api")


def expand(img, frac):
    h, w = img.shape[:2]
    py, px = int(h * frac), int(w * frac)
    return cv2.copyMakeBorder(img, py, py, px, px, cv2.BORDER_REPLICATE)


def main():
    import traffic_light_classifier as tlc
    if not tlc.is_available():
        print("CNN unavailable")
        return 1

    files = sorted(glob.glob(r"E:\output\_tl_crops2\*.png"))
    rows = []
    for f in files:
        img = cv2.imread(f, cv2.IMREAD_COLOR)
        if img is None:
            continue
        name = os.path.basename(f)
        truth = name.rsplit("_", 2)[-2]
        rec = {"file": name[:40], "truth": truth}
        for frac in (0.0, 0.10, 0.25, 0.40):
            st, cf = tlc.classify_traffic_light(expand(img, frac) if frac else img)
            rec["cnn_%.2f" % frac] = st
            rec["conf_%.2f" % frac] = round(cf, 3)
        rec["hsv"] = tlc.hsv_fallback_state(img)
        rows.append(rec)

    colour = [r for r in rows if r["truth"] in ("red", "green", "yellow")]
    reject = [r for r in rows if r["truth"] in ("unknown", "none")]

    print("%-40s %-8s %-9s %-9s %-9s %-9s %s"
          % ("file", "truth", "cnn_raw", "cnn_10%", "cnn_25%", "cnn_40%", "hsv"))
    for r in rows:
        print("%-40s %-8s %-9s %-9s %-9s %-9s %s"
              % (r["file"], r["truth"], r["cnn_0.00"], r["cnn_0.10"],
                 r["cnn_0.25"], r["cnn_0.40"], r["hsv"]))

    print("\n" + "=" * 84)
    print("%-22s %-12s %-12s %-12s %-12s %s"
          % ("input", "colour_acc", "reject_acc", "red->green", "red->none", "green->red"))
    print("=" * 84)
    for frac in (0.0, 0.10, 0.25, 0.40):
        key = "cnn_%.2f" % frac
        ok = sum(1 for r in colour if r[key] == r["truth"])
        rj = sum(1 for r in reject if r[key] in ("unknown", "none"))
        r2g = sum(1 for r in colour if r["truth"] == "red" and r[key] == "green")
        r2n = sum(1 for r in colour if r["truth"] == "red" and r[key] == "none")
        g2r = sum(1 for r in colour if r["truth"] == "green" and r[key] == "red")
        print("%-22s %-12s %-12s %-12d %-12d %d"
              % ("CNN expand %.0f%%" % (frac * 100),
                 "%d/%d=%.0f%%" % (ok, len(colour), 100 * ok / max(1, len(colour))),
                 "%d/%d=%.0f%%" % (rj, len(reject), 100 * rj / max(1, len(reject))),
                 r2g, r2n, g2r))
    ok = sum(1 for r in colour if r["hsv"] == r["truth"])
    rj = sum(1 for r in reject if r["hsv"] in ("unknown", "none"))
    r2g = sum(1 for r in colour if r["truth"] == "red" and r["hsv"] == "green")
    r2n = sum(1 for r in colour if r["truth"] == "red" and r["hsv"] == "none")
    g2r = sum(1 for r in colour if r["truth"] == "green" and r["hsv"] == "red")
    print("%-22s %-12s %-12s %-12d %-12d %d"
          % ("HSV (raw crop)", "%d/%d=%.0f%%" % (ok, len(colour), 100 * ok / max(1, len(colour))),
             "%d/%d=%.0f%%" % (rj, len(reject), 100 * rj / max(1, len(reject))), r2g, r2n, g2r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
