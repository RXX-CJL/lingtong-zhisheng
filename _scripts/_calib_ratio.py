"""Calibrate the channel-ratio rule on the ONLY trustworthy ground truth:
machine-verified CARLA lens crops (_tl_carla3, 12/20/30 m).

Measures, INSIDE the glow region found by find_glow_region (not a percentile
guess), the channel ratios for each state, and searches for a separating rule.
"""
import glob
import os
import re
import sys

import cv2
import numpy as np

sys.path.insert(0, r"E:\output\1\api")
import traffic_light_classifier as tlc  # noqa: E402

SRC = r"E:\output\_tl_carla3"


def main():
    pat = re.compile(r"^(red|green|yellow)_(\d+)m_(\d+)x(\d+)\.png$")
    rows = []
    for f in sorted(glob.glob(os.path.join(SRC, "*.png"))):
        m = pat.match(os.path.basename(f))
        if not m:
            continue
        truth, dist, cw, ch = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
        if dist == 45:
            continue
        img = cv2.imread(f, cv2.IMREAD_COLOR)
        if img is None or img.size == 0:
            continue
        g = tlc.find_glow_region(img)
        if g is None:
            rows.append({"truth": truth, "dist": dist, "size": "%sx%s" % (cw, ch),
                         "glow": None})
            continue
        core = img[g["mask"]]
        cb, cg, cr = [float(core[:, i].mean()) for i in range(3)]
        bgm = ~g["mask"]
        if int(bgm.sum()) >= 12:
            sh = img[bgm]
            sb, sg, sr = [float(sh[:, i].mean()) for i in range(3)]
        else:
            sb = sg = sr = float("nan")
        rows.append({
            "truth": truth, "dist": dist, "size": "%sx%s" % (cw, ch),
            "area": g["area"], "gw": g["w"], "gh": g["h"],
            "cb": cb, "cg": cg, "cr": cr,
            "sb": sb, "sg": sg, "sr": sr,
            "g_over_b": cg / max(cb, 1e-6),
            "r_over_b": cr / max(cb, 1e-6),
            "r_over_g": cr / max(cg, 1e-6),
            "dr": cr - sr, "dg": cg - sg, "db": cb - sb,
        })

    print("%-7s %-5s %-9s %-5s %-22s %-7s %-7s %-7s %-7s %-7s"
          % ("truth", "dist", "size", "area", "glow core BGR", "G/B", "R/B", "R/G", "dR", "dG"))
    for r in sorted(rows, key=lambda x: (x["truth"], x["dist"], x["size"])):
        if r.get("glow") is None and "cb" not in r:
            print("%-7s %-5d %-9s  no glow region found" % (r["truth"], r["dist"], r["size"]))
            continue
        print("%-7s %-5d %-9s %-5d (%6.1f,%6.1f,%6.1f) %-7.2f %-7.2f %-7.2f %-7.1f %-7.1f"
              % (r["truth"], r["dist"], r["size"], r["area"], r["cb"], r["cg"], r["cr"],
                 r["g_over_b"], r["r_over_b"], r["r_over_g"], r["dr"], r["dg"]))

    # how separable is each feature?
    print("\nfeature ranges per state (min..max):")
    for feat in ("g_over_b", "r_over_b", "r_over_g", "dr", "dg", "db"):
        print("   %-9s" % feat, end="")
        for st in ("red", "yellow", "green"):
            vals = [r[feat] for r in rows if r.get("truth") == st and feat in r]
            if vals:
                print("  %s[%.2f..%.2f]" % (st[:1].upper(), min(vals), max(vals)), end="")
        print()

    # try simple rules
    print("\ncandidate rules (accuracy on this set):")
    usable = [r for r in rows if "cb" in r]
    n = len(usable)
    rules = {
        "G/B >= 1.20 -> green else yellow": lambda r: "green" if r["g_over_b"] >= 1.20 else "yellow",
        "G/B >= 1.45 -> green else yellow": lambda r: "green" if r["g_over_b"] >= 1.45 else "yellow",
        "R/G >= 1.30 -> red ; G/B>=1.20 -> green ; else yellow":
            lambda r: "red" if r["r_over_g"] >= 1.30 else ("green" if r["g_over_b"] >= 1.20 else "yellow"),
        "R/B >= 1.50 -> red ; G/B>=1.20 -> green ; else yellow":
            lambda r: "red" if r["r_over_b"] >= 1.50 else ("green" if r["g_over_b"] >= 1.20 else "yellow"),
    }
    for name, fn in rules.items():
        ok = sum(1 for r in usable if fn(r) == r["truth"])
        print("   %-58s %3d/%-3d = %5.1f%%" % (name, ok, n, 100 * ok / n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
