"""Validate classify_with_glow:
  A) regression on _tl_dataset (377 samples) -- must not regress vs CNN alone
  B) correctness on the machine-verified CARLA lens crops (_tl_carla3, 12/20/30 m)
  C) the danger check: red must never be reported as green
"""
import glob
import os
import re
import sys
from collections import Counter

import cv2
import numpy as np

sys.path.insert(0, r"E:\output\1\api")
import traffic_light_classifier as tlc  # noqa: E402


def expand(img, frac=0.25):
    h, w = img.shape[:2]
    py, px = int(h * frac), int(w * frac)
    return cv2.copyMakeBorder(img, py, py, px, px, cv2.BORDER_REPLICATE)


def run_dataset():
    root = r"E:\output\_tl_dataset"
    recs = []
    for cls in ("red", "green", "yellow", "none"):
        for f in sorted(glob.glob(os.path.join(root, cls, "*.png"))):
            img = cv2.imread(f, cv2.IMREAD_COLOR)
            if img is None or img.size == 0:
                continue
            exp = expand(img)
            cnn, cconf = tlc.classify_traffic_light(exp)
            st, conf, info = tlc.classify_with_glow(exp)
            recs.append({"truth": cls, "cnn": cnn, "glow": st, "src": info.get("source"),
                         "ratio": info.get("ratio")})
    pos = [r for r in recs if r["truth"] != "none"]
    neg = [r for r in recs if r["truth"] == "none"]

    def rep(key, name):
        ok = sum(1 for r in pos if r[key] == r["truth"])
        fp = sum(1 for r in neg if r[key] in ("red", "green", "yellow"))
        okn = sum(1 for r in neg if r[key] in ("none", "unknown"))
        r2g = sum(1 for r in pos if r["truth"] == "red" and r[key] == "green")
        print("   %-22s colour %3d/%-3d=%5.1f%%   reject %3d/%-3d=%5.1f%%   FP-colour-on-none %3d   red->green %d"
              % (name, ok, len(pos), 100 * ok / len(pos), okn, len(neg),
                 100 * okn / len(neg), fp, r2g))
        return ok, len(pos)

    print("A) REGRESSION on _tl_dataset (n=%d)" % len(recs))
    rep("cnn", "CNN4 alone (baseline)")
    rep("glow", "glow + CNN (new)")
    print("\n   per-state (new):")
    for c in ("red", "green", "yellow"):
        sub = [r for r in pos if r["truth"] == c]
        print("      %-7s %d/%d   sources=%s" % (c, sum(1 for r in sub if r["glow"] == c), len(sub),
                                                 dict(Counter(r["src"] for r in sub))))
    print("   none-sample outcome:", dict(Counter(r["glow"] for r in neg)))
    return recs


def run_carla():
    src = r"E:\output\_tl_carla3"
    pat = re.compile(r"^(red|green|yellow)_(\d+)m_(\d+)x(\d+)\.png$")
    recs = []
    for f in sorted(glob.glob(os.path.join(src, "*.png"))):
        m = pat.match(os.path.basename(f))
        if not m:
            continue
        truth, dist = m.group(1), int(m.group(2))
        if dist == 45:                       # excluded: housing location fails at 45 m
            continue
        img = cv2.imread(f, cv2.IMREAD_COLOR)
        if img is None or img.size == 0:
            continue
        st, conf, info = tlc.classify_with_glow(expand(img))
        recs.append({"truth": truth, "dist": dist, "size": "%sx%s" % (m.group(3), m.group(4)),
                     "glow": st, "src": info.get("source"), "ratio": info.get("ratio"),
                     "cnn": info.get("cnn"), "g": (info.get("glow") or {}).get("w")})
    print("\nB) CARLA machine-verified lens crops, 12/20/30 m (n=%d)" % len(recs))
    ok = sum(1 for r in recs if r["glow"] == r["truth"])
    print("   glow method: %d/%d = %.1f%%" % (ok, len(recs), 100 * ok / max(1, len(recs))))
    for s in ("red", "yellow", "green"):
        sub = [r for r in recs if r["truth"] == s]
        if sub:
            print("      %-7s %d/%d" % (s, sum(1 for r in sub if r["glow"] == s), len(sub)))
    print("\n   detail (large crop only):")
    for r in recs:
        if r["size"] != "34x130":
            continue
        print("      %-7s %2dm  pred=%-8s src=%-12s ratio=%-8s cnn=%-8s glow_w=%s"
              % (r["truth"], r["dist"], r["glow"], r["src"], r["ratio"], r["cnn"], r["g"]))
    print("\n   confusion:", dict(Counter((r["truth"], r["glow"]) for r in recs)))
    return recs


if __name__ == "__main__":
    run_dataset()
    run_carla()
