"""在演示视频上评测多个判色模型 —— 走**模块自身的判色函数**（与部署一致）。

关键：不要自己重写预处理。直接改 TL_COLOR_MODEL 环境变量后 reload 模块，
调用 traffic_light_classifier.classify_traffic_light()，这才是部署路径。
"""
import importlib
import os
import subprocess
import sys
from collections import Counter

import cv2
import numpy as np

sys.path.insert(0, r"E:\output\1\api")

VID = r"E:\output\_dual_cam_demo\dual_cam_demo_lossless.mkv"
MODELS = [
    ("CNN4_orig", r"E:\output\_tl_color_cls\tl_color_cnn4.pt"),
    ("CNN5_v1", r"E:\output\_tl_color_cls\tl_color_cnn5_carla.pt"),
    ("CNN6_v2", r"E:\output\_tl_color_cls\tl_color_cnn6_carla.pt"),
]
FRAMES = [(30, "Red"), (90, "Red"), (150, "Red"), (210, "Red"), (250, "Red"), (290, "Red"),
          (310, "Green"), (350, "Green"), (380, "Green"), (410, "Yellow"), (440, "Yellow"),
          (470, "Yellow"), (510, "Red")]


def run_one(name, path):
    os.environ["TL_COLOR_MODEL"] = path
    # 清掉已缓存模块，确保按新环境变量加载
    for k in list(sys.modules):
        if k in ("traffic_light_classifier", "realtime_detector"):
            del sys.modules[k]
    import traffic_light_classifier as T
    importlib.reload(T)
    from realtime_detector import RealtimeViolationDetector
    det = RealtimeViolationDetector()

    cap = cv2.VideoCapture(VID)
    pw = int(1920 * 0.26)
    ph = int(pw * 720 / 1280)
    x0, y0 = 1920 - pw - 18, 1080 - ph - 18
    ok_n = 0
    per = {}
    lines = []
    for f, truth in FRAMES:
        cap.set(cv2.CAP_PROP_POS_FRAMES, f)
        ok, fr = cap.read()
        if not ok:
            continue
        pip = fr[y0:y0 + ph, x0:x0 + pw]
        dets = det._yolo_detect(pip)
        tls = [d for d in dets if (d.get("class_name") or "").lower()
               in ("traffic light", "traffic_light")]
        votes = Counter()
        for d in tls:
            a, b, c2, dd = [int(v) for v in d["bbox"][:4]]
            roi = pip[max(0, b):min(ph, dd), max(0, a):min(pw, c2)]
            if roi.size == 0:
                continue
            st, conf = T.classify_traffic_light(roi)
            votes["%s" % st] += 1
        real = {k: v for k, v in votes.items() if k not in ("none", "unknown")}
        pred = max(real, key=real.get) if real else "none"
        hit = (pred == truth.lower())
        ok_n += 1 if hit else 0
        per.setdefault(truth, [0, 0])
        per[truth][1] += 1
        per[truth][0] += 1 if hit else 0
        lines.append("   帧 %-4d 真值 %-6s 投票 %-40s -> %-8s %s"
                     % (f, truth, str(dict(votes)), pred, "OK" if hit else "X"))
    cap.release()
    del det
    return ok_n, len(FRAMES), per, lines


def main():
    print("模型路径由 TL_COLOR_MODEL 环境变量控制（模块已支持）\n")
    results = {}
    for name, path in MODELS:
        print("=" * 78)
        print("=== %s : %s" % (name, os.path.basename(path)))
        print("=" * 78)
        a, b, per, lines = run_one(name, path)
        for l in lines:
            print(l)
        print("   合计 %d/%d = %.0f%%" % (a, b, 100.0 * a / max(1, b)))
        for t, (x, y) in sorted(per.items()):
            print("      %-7s %d/%d" % (t, x, y))
        print()
        results[name] = (a, b, per)

    print("=" * 78)
    print("%-12s %-12s %s" % ("模型", "总准确率", "分态"))
    for name, (a, b, per) in results.items():
        print("%-12s %-12s %s" % (name, "%d/%d=%.0f%%" % (a, b, 100.0 * a / max(1, b)),
                                  "  ".join("%s %d/%d" % (t, x, y) for t, (x, y) in sorted(per.items()))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
