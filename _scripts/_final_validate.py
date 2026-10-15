"""最终验证：修改后
  ① 生产路径（YOLO 框原样喂 CNN4）应为 100% 判色 / 100% 拒识
  ② classify_with_glow（发光区校验 + CNN）应不劣于 ①
  ③ CARLA 真值裁图上给出对照
  ④ 危险方向（红→绿、黄→红）必须为 0
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


def old_style_expand(img, frac=0.25):
    h, w = img.shape[:2]
    py, px = int(h * frac), int(w * frac)
    return cv2.copyMakeBorder(img, py, py, px, px, cv2.BORDER_REPLICATE)


def main():
    recs = []
    for cls in ("red", "green", "yellow", "none"):
        for f in sorted(glob.glob(os.path.join(ROOT, cls, "*.png"))):
            img = cv2.imread(f, cv2.IMREAD_COLOR)
            if img is None or img.size == 0:
                continue
            recs.append({"truth": cls, "img": img,
                         "raw": cls == "none" and "none" or cls})
    pos = [r for r in recs if r["truth"] != "none"]
    neg = [r for r in recs if r["truth"] == "none"]

    def score(fn, name):
        ok = rej = fp = 0
        r2g = y2r = 0
        for r in pos:
            st, conf, info = fn(r["img"])
            if st == r["truth"]:
                ok += 1
            if r["truth"] == "red" and st == "green":
                r2g += 1
            if r["truth"] == "yellow" and st == "red":
                y2r += 1
        for r in neg:
            st, conf, info = fn(r["img"])
            if st in ("none", "unknown"):
                rej += 1
            else:
                fp += 1
        print("   %-38s 判色 %3d/%-3d=%5.1f pct   拒识 %3d/%-3d=%5.1f pct   FP %d   红→绿 %d   黄→红 %d"
              % (name, ok, len(pos), 100.0 * ok / len(pos),
                 rej, len(neg), 100.0 * rej / len(neg), fp, r2g, y2r))

    print("① 生产路径（现在已改为：YOLO 框原样，不扩边）")
    score(lambda im: (tlc.classify_traffic_light(im)[0], tlc.classify_traffic_light(im)[1], {}),
          "CNN4 对原样框")
    print("\n② 发光区校验 + CNN（classify_with_glow）")
    score(lambda im: tlc.classify_with_glow(im), "classify_with_glow")
    print("\n③ 对照：旧行为（扩边 25%）—— 仅用于对比，已废弃")
    score(lambda im: (tlc.classify_traffic_light(old_style_expand(im))[0],
                      tlc.classify_traffic_light(old_style_expand(im))[1], {}),
          "CNN4 对扩边 25% 框（旧）")

    # 分状态 + 来源
    print("\nclassify_with_glow 分状态:")
    for c in ("red", "green", "yellow"):
        sub = [r for r in pos if r["truth"] == c]
        ok = sum(1 for r in sub if tlc.classify_with_glow(r["img"])[0] == c)
        src = Counter(tlc.classify_with_glow(r["img"])[2].get("source") for r in sub)
        print("   %-7s %3d/%-3d   来源=%s" % (c, ok, len(sub), dict(src)))
    print("   none 判定分布:", dict(Counter(tlc.classify_with_glow(r["img"])[0] for r in neg)))

    # CARLA 真值裁图
    print("\n④ CARLA 机器校验真值裁图（红/黄/绿 × 12/20/30m，n=36）")
    src_dir = r"E:\output\_tl_carla3"
    import re
    pat = re.compile(r"^(red|green|yellow)_(\d+)m_(\d+)x(\d+)\.png$")
    crows = []
    for f in sorted(glob.glob(os.path.join(src_dir, "*.png"))):
        m = pat.match(os.path.basename(f))
        if not m or int(m.group(2)) == 45:
            continue
        img = cv2.imread(f)
        if img is None or img.size == 0:
            continue
        st, conf, info = tlc.classify_with_glow(img)
        crows.append((m.group(1), st, info.get("source")))
    n = len(crows)
    ok = sum(1 for t, s, _ in crows if t == s)
    print("   classify_with_glow: %d/%d = %.1f pct" % (ok, n, 100.0 * ok / n))
    for c in ("red", "yellow", "green"):
        sub = [r for r in crows if r[0] == c]
        print("      %-7s %d/%d   来源=%s" % (c, sum(1 for r in sub if r[1] == c), len(sub),
                                              dict(Counter(r[2] for r in sub))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
