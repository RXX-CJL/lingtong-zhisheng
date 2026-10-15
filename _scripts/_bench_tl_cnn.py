"""Benchmark the CURRENT CNN4 classifier on the real-video crops that carry
ground-truth labels in their filenames.

This gives the honest baseline the new paradigm must beat -- earlier sessions
quoted "0.997 cross-validation", which is training-set CV, not real-footage accuracy.
"""
import glob
import os
import sys
import time
from collections import Counter

import cv2
import numpy as np

sys.path.insert(0, r"E:\output\1\api")


def main():
    import traffic_light_classifier as tlc
    print("model available:", tlc.is_available())
    print("model path     :", tlc._MODEL_PATH, "exists:", os.path.exists(tlc._MODEL_PATH))
    if not tlc.is_available():
        print("CNN unavailable -- cannot benchmark")
        return 1
    print("classes        :", tlc._classes)

    files = sorted(glob.glob(r"E:\output\_tl_crops2\*.png"))
    rows = []
    t0 = time.time()
    for f in files:
        img = cv2.imread(f, cv2.IMREAD_COLOR)
        if img is None:
            continue
        name = os.path.basename(f)
        truth = name.rsplit("_", 2)[-2]
        state, conf = tlc.classify_traffic_light(img)
        hsv_state = tlc.hsv_fallback_state(img)
        rows.append({"file": name, "truth": truth, "cnn": state, "conf": round(conf, 3),
                     "hsv": hsv_state, "size": "%dx%d" % (img.shape[1], img.shape[0])})
    dt = time.time() - t0

    print("\n%-34s %-8s %-9s %-7s %-9s %s" % ("file", "truth", "CNN", "conf", "HSV", "size"))
    for r in rows:
        flag = "" if r["cnn"] == r["truth"] else "   <-- MISMATCH"
        print("%-34s %-8s %-9s %-7.3f %-9s %-8s%s"
              % (r["file"][:34], r["truth"], r["cnn"], r["conf"], r["hsv"], r["size"], flag))

    # only the three real colour classes are meaningful; unknown/none are "reject" cases
    colour = [r for r in rows if r["truth"] in ("red", "green", "yellow")]
    reject = [r for r in rows if r["truth"] in ("unknown", "none")]
    cnn_ok = sum(1 for r in colour if r["cnn"] == r["truth"])
    hsv_ok = sum(1 for r in colour if r["hsv"] == r["truth"])
    cnn_rej = sum(1 for r in reject if r["cnn"] in ("unknown", "none"))
    hsv_rej = sum(1 for r in reject if r["hsv"] in ("unknown", "none"))

    print("\n" + "=" * 78)
    print("REAL-FOOTAGE BASELINE  (%d crops, %.2f s total, %.1f ms/crop)"
          % (len(rows), dt, 1000 * dt / max(1, len(rows))))
    print("=" * 78)
    print("colour crops (red/green/yellow) : n=%d   CNN correct %d (%.1f%%)   HSV correct %d (%.1f%%)"
          % (len(colour), cnn_ok, 100 * cnn_ok / max(1, len(colour)),
             hsv_ok, 100 * hsv_ok / max(1, len(colour))))
    print("reject crops (unknown/none)     : n=%d   CNN rejected %d (%.1f%%)  HSV rejected %d (%.1f%%)"
          % (len(reject), cnn_rej, 100 * cnn_rej / max(1, len(reject)),
             hsv_rej, 100 * hsv_rej / max(1, len(reject))))

    # dangerous direction: truth red but reported green
    danger = [r for r in rows if r["truth"] == "red" and r["cnn"] == "green"]
    print("\nDANGEROUS (truth=red, CNN=green): %d" % len(danger))
    for r in danger:
        print("   ", r["file"], "conf=%.3f" % r["conf"])

    # confusion
    print("\nCNN confusion (truth -> pred):")
    cm = Counter((r["truth"], r["cnn"]) for r in rows)
    for (a, b), n in sorted(cm.items()):
        print("   %-8s -> %-9s %d" % (a, b, n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
