"""扫描：CAM-2 裁图要怎样"呈现"才能让 CNN4 判对？

模型在真实视频上训练（黑/深色灯箱、小灯珠）。CARLA 渲染的灯箱是青蓝色、灯珠占比大，
属于分布外输入。本脚本试多种呈现方式，找能让模型判对的输入形式：
  1. 裁图尺寸（填满 vs 留白）
  2. 是否包含灯箱上下文
  3. 是否只裁点亮的那颗镜片
  4. 尺寸缩放（模拟真实视频里灯珠只有 10~30 px 的样子）
"""
import os
import sys
from itertools import product

import numpy as np
import cv2

sys.path.insert(0, r"E:\output\1\api")
from traffic_light_classifier import classify_traffic_light  # noqa: E402

D = r"E:\output\_cam2_diag"
OUT = r"E:\output\_cam2_sweep"
os.makedirs(OUT, exist_ok=True)
# 灯头竖条中心（上一轮定位）
HEADS = [(961, 351), (638, 350)]
# 三颗镜片：上/中/下
LENS = ["UPPER", "MIDDLE", "LOWER"]
TRUTH = {"red": "red", "green": "green", "yellow": "yellow"}


def crop_lens(img, cx, cy, which, hw=18, hh=50, pad=0):
    """裁第 which 颗镜片（0上 1中 2下），pad 为额外上下文"""
    y0, y1 = cy - hh, cy + hh
    third = (y1 - y0) // 3
    ly0 = y0 + which * third
    ly1 = ly0 + third
    return img[max(0, ly0 - pad):ly1 + pad, max(0, cx - hw - pad):cx + hw + pad]


def variants(img, cx, cy, which):
    """生成多种呈现方式"""
    out = {}
    base = crop_lens(img, cx, cy, which, pad=3)
    if base.size == 0:
        return out
    out["tight"] = base
    # 带更多上下文（含部分灯箱）
    out["ctx+12"] = crop_lens(img, cx, cy, which, pad=12)
    # 整条灯头（三颗镜片全在）
    out["whole_head"] = img[max(0, cy - 50):cy + 50, max(0, cx - 18):cx + 18]
    # 缩放到不同尺寸（模拟真实视频里灯珠的像素规模）
    for target in (12, 20, 28, 40, 64):
        h, w = base.shape[:2]
        sc = target / max(h, w)
        nw, nh = max(4, int(w * sc)), max(4, int(h * sc))
        small = cv2.resize(base, (nw, nh), interpolation=cv2.INTER_AREA)
        out["down%d" % target] = small
        # 再放大回 64 并加黑底（模拟"远处小灯"在框内的样子）
        canvas = np.zeros((64, 64, 3), np.uint8)
        y0 = (64 - nh) // 2
        x0 = (64 - nw) // 2
        canvas[y0:y0 + nh, x0:x0 + nw] = small
        out["pad64_%d" % target] = canvas
    return out


def main():
    rows = []
    for tag in ("red", "green", "yellow"):
        img = cv2.imread(os.path.join(D, "cam2_%s.png" % tag))
        if img is None:
            print("缺图 cam2_%s.png" % tag)
            continue
        truth = TRUTH[tag]
        print("\n=== %s（真值 %s）===" % (tag.upper(), truth))
        for (cx, cy) in HEADS:
            for which in (0, 1, 2):
                for name, crop in variants(img, cx, cy, which).items():
                    if crop.size == 0 or min(crop.shape[:2]) < 4:
                        continue
                    st, conf = classify_traffic_light(crop)
                    ok = (st == truth)
                    rows.append((tag, "head(%d,%d)" % (cx, cy), LENS[which], name,
                                 st, round(conf, 3), ok))
    # 汇总
    print("\n" + "=" * 88)
    print("%-7s %-16s %-7s %-12s %-10s %-7s %s" %
          ("真值", "灯头", "镜片", "呈现方式", "CNN4", "conf", "对?"))
    print("=" * 88)
    for r in rows:
        print("%-7s %-16s %-7s %-12s %-10s %-7s %s" %
              (r[0], r[1], r[2], r[3], r[4], r[5], "OK" if r[6] else ""))
    hit = {}
    for r in rows:
        k = r[3]
        hit.setdefault(k, [0, 0])
        hit[k][1] += 1
        if r[6]:
            hit[k][0] += 1
    print("\n按呈现方式统计命中率:")
    for k, (h, n) in sorted(hit.items(), key=lambda x: -x[1][0] / max(1, x[1][1])):
        print("   %-12s %2d/%2d = %.0f%%" % (k, h, n, 100.0 * h / max(1, n)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
