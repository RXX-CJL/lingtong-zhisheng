"""诊断 _channel_ratio_state 为何与 CNN 冲突：统计它在各真值下的输出分布。"""
import glob
import os
import sys
from collections import Counter

import cv2
import numpy as np

sys.path.insert(0, r"E:\output\1\api")
import traffic_light_classifier as tlc  # noqa: E402
ROOT = r"E:\output\_tl_dataset"

print("%-8s %-9s %-28s %-8s %-8s %s" %
      ("truth", "ratio判定", "发光区核心 BGR", "G/B", "B/R", "n"))
for cls in ("red", "green", "yellow", "none"):
    files = sorted(glob.glob(os.path.join(ROOT, cls, "*.png")))
    per = Counter()
    samples = []
    for f in files:
        img = cv2.imread(f, cv2.IMREAD_COLOR)
        if img is None or img.size == 0:
            continue
        gl = tlc.find_glow_region(img)
        if gl is None:
            per["(no_glow)"] += 1
            continue
        st = tlc._channel_ratio_state(img, gl)
        per[st] += 1
        core = img[gl["mask"]]
        cb, cg, cr = [float(core[:, i].mean()) for i in range(3)]
        samples.append((cb, cg, cr))
    if samples:
        m = np.median(np.array(samples), axis=0)
        gb = m[1] / max(m[0], 1e-6)
        br = m[0] / max(m[2], 1e-6)
        print("%-8s %-9s (%6.1f,%6.1f,%6.1f)          %-8.2f %-8.2f %s"
              % (cls, dict(per), m[0], m[1], m[2], gb, br, len(samples)))
    else:
        print("%-8s %-9s -" % (cls, dict(per)))
print()
print("阈值: _G_REL_STRONG=%.2f  (G/B>=此值 -> green)" % tlc._G_REL_STRONG)
print("红/黄靠 G/B>=0.80 判黄，否则 B/R>=1.6 判红")
