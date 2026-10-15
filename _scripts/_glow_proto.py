"""Prototype: 'find the glow, judge on the halo' colour decision, and honest
evaluation.

Key measured fact: the lit lens CORE is blown out to white (low saturation), so
its hue is useless. The colour lives in the HALO around the core. So:
  1. find the compact bright region (the lit lens) inside the box
  2. take a ring around it
  3. decide the colour from that ring's channel ratios
  4. no glow found -> unknown  (never guess)

Also re-evaluates the existing classifiers with the lens ACTUALLY CENTRED, to
remove the framing confound from the previous run.
"""
import glob
import json
import math
import os
import re
import sys
from collections import Counter

import cv2
import numpy as np

sys.path.insert(0, r"E:\output\1\api")
SRC = r"E:\output\_tl_carla2"
OUT = r"E:\output\_tl_glow_eval"
os.makedirs(OUT, exist_ok=True)


# ----------------------------------------------------------------- glow finder
def find_glow(img):
    """Largest compact region that is bright both absolutely and vs its surround."""
    b, g, r = (img[:, :, i].astype(np.float32) for i in range(3))
    v = np.maximum(np.maximum(b, g), r)
    grey = (0.114 * b + 0.587 * g + 0.299 * r)
    local = cv2.blur(grey, (25, 25))
    mask = ((v > 150) & (grey > local + 12)).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    n, lab, stats, cent = cv2.connectedComponentsWithStats(mask, 8)
    best = None
    for i in range(1, n):
        a = int(stats[i, cv2.CC_STAT_AREA])
        if best is None or a > best[0]:
            best = (a, i, cent[i], stats[i])
    if best is None or best[0] < 6:
        return None
    a, i, c, st = best
    return {"area": a, "cx": float(c[0]), "cy": float(c[1]),
            "w": int(st[cv2.CC_STAT_WIDTH]), "h": int(st[cv2.CC_STAT_HEIGHT]),
            "mask": (lab == i)}


def _circ_hue(h):
    ang = h.astype(np.float32) * (2 * np.pi / 180.0)
    return float(np.degrees(np.arctan2(np.sin(ang).mean(), np.cos(ang).mean())) % 180)


def decide_from_ring(img, glow, ring=7):
    """Colour from an annulus around the glow core, plus the core itself."""
    h, w = img.shape[:2]
    m = glow["mask"].astype(np.uint8)
    kern = np.ones((2 * ring + 1, 2 * ring + 1), np.uint8)
    outer = cv2.dilate(m, kern) > 0
    ringm = outer & (~m.astype(bool))
    if ringm.sum() < 8:
        ringm = outer
    sel = img[ringm]
    if sel.size == 0:
        return None
    b, g, r = [float(sel[:, i].mean()) for i in range(3)]
    core = img[m > 0]
    cb, cg, cr = [float(core[:, i].mean()) for i in range(3)]
    # channel ratios (scale free)
    mx = max(b, g, r, 1e-6)
    rb, rg, rr = b / mx, g / mx, r / mx
    # hue of the ring, saturation weighted
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    hh = hsv[:, :, 0][ringm]
    ss = hsv[:, :, 1][ringm]
    hue = _circ_hue(hh)
    sat = float(ss.mean())
    return {"ring_bgr": [round(b, 1), round(g, 1), round(r, 1)],
            "core_bgr": [round(cb, 1), round(cg, 1), round(cr, 1)],
            "ratio": [round(rb, 3), round(rg, 3), round(rr, 3)],
            "hue": round(hue, 1), "sat": round(sat, 1),
            "core_sat": round(float(hsv[:, :, 1][m > 0].mean()), 1)}


def classify_glow(img, ring=7):
    """Return (state, info). state in red/green/yellow/unknown."""
    g = find_glow(img)
    if g is None:
        return "unknown", None
    info = decide_from_ring(img, g, ring)
    if info is None:
        return "unknown", None
    info["glow"] = {"area": g["area"], "cx": round(g["cx"], 1), "cy": round(g["cy"], 1),
                    "w": g["w"], "h": g["h"]}
    b, gg, r = info["ring_bgr"]
    # hue-based decision with channel-ratio cross-check
    hue, sat = info["hue"], info["sat"]
    in_red = (hue >= 165 or hue <= 12)
    in_yel = (12 < hue <= 40)
    in_grn = (40 < hue <= 100)
    # require the channel ordering to agree with the hue (guards against grey/white)
    if in_red and r >= gg and r >= b:
        return "red", info
    if in_grn and gg >= r and gg >= b:
        return "green", info
    if in_yel and r >= b and gg >= b:
        return "yellow", info
    # hue ambiguous: fall back to plain channel dominance on the ring
    if r > gg + 12 and r > b + 12:
        return "red", info
    if gg > r + 10 and gg > b + 10:
        return "green", info
    if r > b + 25 and gg > b + 25 and abs(r - gg) <= 25:
        return "yellow", info
    return "unknown", info


def crop_at(img, cx, cy, cw, ch):
    H, W = img.shape[:2]
    x0 = max(0, min(W - cw, int(cx - cw // 2)))
    y0 = max(0, min(H - ch, int(cy - ch // 2)))
    return img[y0:y0 + ch, x0:x0 + cw]


def main():
    import traffic_light_classifier as tlc
    pat = re.compile(r"^(red|green|yellow)_(\d+)m_(\d+)x(\d+)\.png$")

    # regroup crops by their source capture so the lens can be centred once
    groups = {}
    for f in glob.glob(os.path.join(SRC, "*_full.png")):
        m = re.match(r"^(red|green|yellow)_(\d+)m_full\.png$", os.path.basename(f))
        if m:
            groups[(m.group(1), int(m.group(2)))] = f

    print("Re-evaluating with the lit lens CENTRED (removes the framing confound)\n")
    print("%-8s %-5s %-11s %-9s %-9s %-11s %-9s %s"
          % ("truth", "dist", "lens px", "CNN", "HSV", "GLOW(new)", "glow cfg", "glow ring BGR/hue"))
    rows = []
    for (truth, dist), full in sorted(groups.items()):
        arr = cv2.imread(full, cv2.IMREAD_COLOR)
        if arr is None:
            continue
        g = find_glow(arr)
        if g is None:
            print("%-8s %-5d  (no glow found in full frame)" % (truth, dist))
            continue
        cx, cy = g["cx"], g["cy"]
        lw, lh = g["w"], g["h"]
        # standard 25%-expanded box around the lens
        bw = max(12, int(lw * 2.6))
        bh = max(40, int(lh * 2.6))
        for (cw, ch) in ((bw, bh), (34, 130), (12, 47)):
            crop = crop_at(arr, cx, cy, cw, ch)
            if crop.shape[0] != ch or crop.shape[1] != cw:
                continue
            exp = cv2.copyMakeBorder(crop, int(ch * .25), int(ch * .25), int(cw * .25), int(cw * .25),
                                     cv2.BORDER_REPLICATE)
            cnn, conf = tlc.classify_traffic_light(exp)
            hsv = tlc.hsv_fallback_state(crop)
            st, info = classify_glow(crop)
            rows.append({"truth": truth, "dist": dist, "size": "%dx%d" % (cw, ch),
                         "cnn": cnn, "hsv": hsv, "glow": st, "info": info})
            if (cw, ch) == (bw, bh):
                ring = info["ring_bgr"] if info else None
                print("%-8s %-5d %-11s %-9s %-9s %-11s %-9s %s"
                      % (truth, dist, "%dx%d" % (lw, lh), cnn, hsv, st, "",
                         ("%s hue %.0f sat %.0f" % (ring, info["hue"], info["sat"])) if info else "-"))
                if info:
                    cv2.imwrite(os.path.join(OUT, "centred_%s_%02dm.png" % (truth, dist)), crop)

    n = len(rows)
    print("\n" + "=" * 96)
    print("ALL CROPS (lens re-centred), n=%d" % n)
    print("=" * 96)
    for key, name in (("cnn", "CNN4"), ("hsv", "HSV"), ("glow", "GLOW (new)")):
        ok = sum(1 for r in rows if r[key] == r["truth"])
        print("   %-12s %3d/%-3d = %5.1f%%" % (name, ok, n, 100 * ok / max(1, n)))

    print("\nGLOW method details (large crop only):")
    big = [r for r in rows if r["info"] and r["size"] == "%dx%d" % (
        max(12, int(r["info"]["glow"]["w"] * 2.6)), max(40, int(r["info"]["glow"]["h"] * 2.6)))]
    for r in big:
        i = r["info"]
        print("   truth=%-7s pred=%-8s core=%s ring=%s hue=%5.1f sat=%5.1f  glow=%dx%d"
              % (r["truth"], r["glow"], i["core_bgr"], i["ring_bgr"], i["hue"], i["sat"],
                 i["glow"]["w"], i["glow"]["h"]))

    print("\nconfusions (all crops):")
    for key in ("cnn", "hsv", "glow"):
        print("   %-6s %s" % (key, dict(Counter((r["truth"], r[key]) for r in rows))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
