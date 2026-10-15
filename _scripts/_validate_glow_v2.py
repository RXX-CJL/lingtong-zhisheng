"""验证发光区判色 v2（同上一轮失败的那两个测试集，直接对比）。

  A) _tl_carla3  36 张机器校验真值的 CARLA 灯珠裁图（红/黄/绿 × 12/20/30m）
  B) _tl_dataset 377 张真实视频样本（red54/green48/yellow15/none260）
     —— 重点看是否把 CNN4 的 93.2% / 99.6% 拖坏

判色三条底线：
  * 红不能被判成绿（最危险方向）
  * 拒识率不能掉（宁可 unknown，不可误导）
  * 整体不能比 CNN4 单用更差
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


def run_carla():
    src = r"E:\output\_tl_carla3"
    pat = re.compile(r"^(red|green|yellow)_(\d+)m_(\d+)x(\d+)\.png$")
    rows = []
    for f in sorted(glob.glob(os.path.join(src, "*.png"))):
        m = pat.match(os.path.basename(f))
        if not m:
            continue
        truth, dist = m.group(1), int(m.group(2))
        if dist == 45:
            continue
        img = cv2.imread(f)
        if img is None or img.size == 0:
            continue
        cnn, cc = tlc.classify_traffic_light(expand(img))
        st, conf, info = tlc.classify_with_glow(img)
        rows.append({"truth": truth, "dist": dist, "size": "%sx%s" % (m.group(3), m.group(4)),
                     "cnn": cnn, "glow": st, "src": info.get("source"),
                     "ratio": info.get("ratio"), "cropped": info.get("cropped")})
    n = len(rows)
    ok_cnn = sum(1 for r in rows if r["cnn"] == r["truth"])
    ok_g = sum(1 for r in rows if r["glow"] == r["truth"])
    print("A) CARLA 机器校验真值裁图  n=%d（真值全是红/黄/绿）" % n)
    print("   CNN4 单用（整框+25pct）   : %3d/%d = %5.1f pct" % (ok_cnn, n, 100.0 * ok_cnn / n))
    print("   glow v2（定位+裁紧+CNN）  : %3d/%d = %5.1f pct" % (ok_g, n, 100.0 * ok_g / n))
    print("   分状态:")
    for s in ("red", "yellow", "green"):
        sub = [r for r in rows if r["truth"] == s]
        if sub:
            print("      %-7s CNN %d/%d    GLOW %d/%d"
                  % (s, sum(1 for r in sub if r["cnn"] == s), len(sub),
                     sum(1 for r in sub if r["glow"] == s), len(sub)))
    print("   来源分布:", dict(Counter(r["src"] for r in rows)))
    red = [r for r in rows if r["truth"] == "red"]
    print("   危险方向 red->green: CNN %d  GLOW %d"
          % (sum(1 for r in red if r["cnn"] == "green"),
             sum(1 for r in red if r["glow"] == "green")))
    print("   混淆:", dict(Counter((r["truth"], r["glow"]) for r in rows)))
    return rows


def run_dataset():
    root = r"E:\output\_tl_dataset"
    recs = []
    for cls in ("red", "green", "yellow", "none"):
        for f in sorted(glob.glob(os.path.join(root, cls, "*.png"))):
            img = cv2.imread(f, cv2.IMREAD_COLOR)
            if img is None or img.size == 0:
                continue
            cnn, _ = tlc.classify_traffic_light(expand(img))
            st, conf, info = tlc.classify_with_glow(expand(img))
            recs.append({"truth": cls, "cnn": cnn, "glow": st, "src": info.get("source")})
    pos = [r for r in recs if r["truth"] != "none"]
    neg = [r for r in recs if r["truth"] == "none"]

    def rep(key, name):
        ok = sum(1 for r in pos if r[key] == r["truth"])
        fp = sum(1 for r in neg if r[key] in ("red", "green", "yellow"))
        okn = sum(1 for r in neg if r[key] in ("none", "unknown"))
        r2g = sum(1 for r in pos if r["truth"] == "red" and r[key] == "green")
        print("   %-24s colour %3d/%-3d=%5.1f pct   reject %3d/%-3d=%5.1f pct   FP %3d   red2green %d"
              % (name, ok, len(pos), 100.0 * ok / len(pos), okn, len(neg),
                 100.0 * okn / len(neg), fp, r2g))

    print("\nB) 真实视频数据集 _tl_dataset  n=%d（red54 green48 yellow15 none260）" % len(recs))
    rep("cnn", "CNN4 单用（基线）")
    rep("glow", "发光区 v2（新）")
    print("   分状态（新）:")
    for c in ("red", "green", "yellow"):
        sub = [r for r in pos if r["truth"] == c]
        print("      %-7s %d/%d  来源=%s"
              % (c, sum(1 for r in sub if r["glow"] == c), len(sub),
                 dict(Counter(r["src"] for r in sub))))
    print("   none 样本判定分布:", dict(Counter(r["glow"] for r in neg)))
    return recs


if __name__ == "__main__":
    run_carla()
    run_dataset()
