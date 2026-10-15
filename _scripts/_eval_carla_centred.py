"""Corrected evaluation: use the 135-degree capture series (where the lit lens is
visible), centre the crop on the lens position recorded in manifest.json, and
score CNN4 / HSV / the new glow method on identical inputs.
"""
import json
import os
import sys
from collections import Counter

import cv2
import numpy as np

sys.path.insert(0, r"E:\output\1\api")
sys.path.insert(0, r"E:\output\_scripts")
from _glow_proto import find_glow, classify_glow, crop_at  # noqa: E402

SRC = r"E:\output\_tl_carla2"
OUT = r"E:\output\_tl_glow_eval"


def main():
    import traffic_light_classifier as tlc
    man = json.load(open(os.path.join(SRC, "manifest.json"), encoding="utf-8"))
    entries = [m for m in man if m.get("found")]
    print("captures with a located lens: %d" % len(entries))

    rows = []
    print("\n%-8s %-5s %-9s %-9s %-9s %-9s %-9s %s"
          % ("truth", "dist", "lens px", "CNN", "HSV", "GLOW", "glow size", "ring BGR / hue / sat"))
    for e in entries:
        truth, dist = e["state"].lower(), e["dist"]
        full = os.path.join(SRC, "%s_%02.0fm_full.png" % (truth, dist))
        arr = cv2.imread(full, cv2.IMREAD_COLOR)
        if arr is None:
            print("  missing", full)
            continue
        cx, cy = e["lens"]
        lw, lh = e["lens_px"]
        # a box with the same 25% padding convention the pipeline uses:
        # box = lens extent * 2.6, then expand 25% for the CNN
        bw, bh = max(12, int(lw * 2.6)), max(40, int(lh * 2.6))
        crop = crop_at(arr, cx, cy, bw, bh)
        if crop.shape[0] != bh or crop.shape[1] != bw:
            continue
        exp = cv2.copyMakeBorder(crop, int(bh * .25), int(bh * .25),
                                 int(bw * .25), int(bw * .25), cv2.BORDER_REPLICATE)
        cnn, conf = tlc.classify_traffic_light(exp)
        hsv = tlc.hsv_fallback_state(crop)
        st, info = classify_glow(crop)
        rows.append({"truth": truth, "dist": dist, "cnn": cnn, "hsv": hsv, "glow": st})
        ring = ("%s h%.0f s%.0f" % (info["ring_bgr"], info["hue"], info["sat"])) if info else "-"
        gsz = ("%dx%d" % (info["glow"]["w"], info["glow"]["h"])) if info else "-"
        print("%-8s %-5d %-9s %-9s %-9s %-9s %-9s %s"
              % (truth, dist, "%dx%d" % (lw, lh), cnn, hsv, st, gsz, ring))
        cv2.imwrite(os.path.join(OUT, "eval_%s_%02dm.png" % (truth, dist)), crop)
        cv2.imwrite(os.path.join(OUT, "eval_%s_%02dm_exp.png" % (truth, dist)), exp)

    n = len(rows)
    print("\n" + "=" * 88)
    print("REAL CARLA LENS, lens-centred crops + machine-verified states   n=%d" % n)
    print("=" * 88)
    for key, name in (("cnn", "CNN4 (deployed)"), ("hsv", "HSV (disabled)"), ("glow", "GLOW (new)")):
        ok = sum(1 for r in rows if r[key] == r["truth"])
        print("   %-18s %3d/%-3d = %5.1f%%" % (name, ok, n, 100 * ok / max(1, n)))
    print("\nper state:")
    for s in ("red", "green", "yellow"):
        sub = [r for r in rows if r["truth"] == s]
        if not sub:
            continue
        print("   %-7s n=%d  CNN %d  HSV %d  GLOW %d"
              % (s, len(sub), sum(1 for r in sub if r["cnn"] == s),
                 sum(1 for r in sub if r["hsv"] == s), sum(1 for r in sub if r["glow"] == s)))
    print("\nconfusions:")
    for key in ("cnn", "hsv", "glow"):
        print("   %-6s %s" % (key, dict(Counter((r["truth"], r[key]) for r in rows))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
