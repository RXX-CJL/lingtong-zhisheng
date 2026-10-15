"""扫描"发光区定位 -> 裁切尺度"对 CNN4 的影响，数据驱动找最优。

在 _tl_dataset 377 张上扫：以发光区中心为中心，按不同边长裁切后喂 CNN4，
看判色/拒识。边长用"相对镜片尺寸的倍数"和"绝对像素"两种表达都试。
"""
import glob
import os
import sys
from collections import Counter

import cv2
import numpy as np

sys.path.insert(0, r"E:\output\1\api")
import traffic_light_classifier as tlc  # noqa: E402
ROOT = r"E:\output\_tl_dataset"


def expand(img, frac=0.25):
    h, w = img.shape[:2]
    py, px = int(h * frac), int(w * frac)
    return cv2.copyMakeBorder(img, py, py, px, px, cv2.BORDER_REPLICATE)


def crop_fixed(img, cx, cy, side):
    h, w = img.shape[:2]
    half = side / 2.0
    x0, y0 = int(round(cx - half)), int(round(cy - half))
    x1, y1 = int(round(cx + half)), int(round(cy + half))
    px0, py0 = max(0, -x0), max(0, -y0)
    px1, py1 = max(0, x1 - w), max(0, y1 - h)
    x0c, y0c, x1c, y1c = max(0, x0), max(0, y0), min(w, x1), min(h, y1)
    if x1c - x0c < 4 or y1c - y0c < 4:
        return None
    sub = img[y0c:y1c, x0c:x1c]
    if px0 or py0 or px1 or py1:
        sub = cv2.copyMakeBorder(sub, py0, py1, px0, px1, cv2.BORDER_REPLICATE)
    return sub


def main():
    recs = []
    for cls in ("red", "green", "yellow", "none"):
        for f in sorted(glob.glob(os.path.join(ROOT, cls, "*.png"))):
            img = cv2.imread(f, cv2.IMREAD_COLOR)
            if img is None or img.size == 0:
                continue
            recs.append({"truth": cls, "img": img})
    pos = [r for r in recs if r["truth"] != "none"]
    neg = [r for r in recs if r["truth"] == "none"]
    print("样本 %d（判色 %d / none %d）\n" % (len(recs), len(pos), len(neg)))

    print("%-26s %-16s %-16s %s" % ("裁切策略", "判色", "拒识", "FP"))
    for label, fn in [
        ("基线：整图+25%扩边", lambda r: expand(r["img"])),
        ("整图不扩边", lambda r: r["img"]),
        ("定位中心 边长=min(w,h)", lambda r: _c(r, "min")),
        ("定位中心 边长=0.8*min(w,h)", lambda r: _c(r, "min08")),
        ("定位中心 边长=镜片*2.5", lambda r: _c(r, "lens25")),
        ("定位中心 边长=镜片*4", lambda r: _c(r, "lens40")),
        ("定位中心 固定32px", lambda r: _c(r, 32)),
        ("定位中心 固定48px", lambda r: _c(r, 48)),
        ("定位中心 固定64px", lambda r: _c(r, 64)),
    ]:
        ok = fp = rej = 0
        for r in pos:
            im = fn(r)
            if im is None:
                continue
            st, _ = tlc.classify_traffic_light(im)
            if st == r["truth"]:
                ok += 1
        for r in neg:
            im = fn(r)
            if im is None:
                rej += 1
                continue
            st, _ = tlc.classify_traffic_light(im)
            if st in ("none", "unknown"):
                rej += 1
            elif st in ("red", "green", "yellow"):
                fp += 1
        print("%-26s %-16s %-16s %d"
              % (label, "%d/%d=%.0f%%" % (ok, len(pos), 100.0 * ok / len(pos)),
                 "%d/%d=%.0f%%" % (rej, len(neg), 100.0 * rej / len(neg)), fp))
    return 0


def _c(r, mode):
    img = r["img"]
    h, w = img.shape[:2]
    gl = tlc.find_glow_region(expand(img))
    if gl is None:
        return None
    cx, cy = gl["cx"], gl["cy"]
    if mode == "min":
        side = min(w, h) * 1.25
    elif mode == "min08":
        side = min(w, h)
    elif mode == "lens25":
        side = max(gl["w"], gl["h"]) * 2.5
    elif mode == "lens40":
        side = max(gl["w"], gl["h"]) * 4.0
    else:
        side = float(mode)
    return crop_fixed(expand(img), cx, cy, side)


if __name__ == "__main__":
    sys.exit(main())
