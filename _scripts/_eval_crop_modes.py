"""最后一块拼图：修正"灯珠在框内占比太小"的问题，再评测。

发现：真实视频里灯珠**填满** YOLO 框；CARLA 里灯珠只占框内一小块。
而模型（含重训）都是在"灯珠填满框"的样本上学的 -> CARLA 上判色不稳。

修正方案（推理侧，不动模型）：
  1. 用 YOLO 框裁出灯头
  2. 在框内按亮度定位**最亮点**（= 被点亮的灯珠）
  3. 以它为中心裁一个固定小窗（灯珠尺度）
  4. 把这个小窗**放大到填满** 64x64 再喂模型
"""
import importlib
import os
import sys
from collections import Counter

import cv2
import numpy as np

sys.path.insert(0, r"E:\output\1\api")
VID = r"E:\output\_dual_cam_demo\dual_cam_demo_lossless.mkv"
FRAMES = [(30, "Red"), (90, "Red"), (150, "Red"), (210, "Red"), (250, "Red"), (290, "Red"),
          (310, "Green"), (350, "Green"), (380, "Green"), (410, "Yellow"), (440, "Yellow"),
          (470, "Yellow"), (510, "Red"), (515, "Red")]
MODELS = [
    ("CNN4_orig", r"E:\output\_tl_color_cls\tl_color_cnn4.pt"),
    ("CNN5_v1", r"E:\output\_tl_color_cls\tl_color_cnn5_carla.pt"),
    ("CNN6_v2", r"E:\output\_tl_color_cls\tl_color_cnn6_carla.pt"),
]


def tight_crop(roi, mode, scale=3):
    """把 YOLO 框内"被点亮的灯珠"裁出来并放大到填满。

    mode:
      'raw'    -> 原样（现状）
      'peakN'  -> 以最亮点为中心裁 N 像素窗，再放大
      'upper'  -> 取框上部 1/3（红灯位）
      'lit'    -> 按三片亮度选被点亮那片，裁该片
    """
    if mode == "raw":
        return roi
    h, w = roi.shape[:2]
    if mode == "upper":
        return roi[0:max(4, h // 3), :]
    if mode == "lit":
        third = max(3, h // 3)
        g = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY).astype(np.float32)
        best, bi = -1, 0
        for k in range(3):
            seg = g[k * third:(k + 1) * third] if k < 2 else g[2 * third:]
            if seg.size == 0:
                continue
            m = float(seg.mean())
            if m > best:
                best, bi = m, k
        y0 = bi * third
        y1 = y0 + third if bi < 2 else h
        return roi[y0:y1, :]
    if mode.startswith("peak"):
        n = int(mode[4:])
        g = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        yy, xx = np.unravel_index(int(np.argmax(g)), g.shape)
        r = n // 2
        a0, b0 = max(0, xx - r), max(0, yy - r)
        a1, b1 = min(w, a0 + n), min(h, b0 + n)
        c = roi[b0:b1, a0:a1]
        return c if c.size else roi
    return roi


def run_one(name, path, modes):
    os.environ["TL_COLOR_MODEL"] = path
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
    fr_cache = []
    for f, truth in FRAMES:
        cap.set(cv2.CAP_PROP_POS_FRAMES, f)
        ok, fr = cap.read()
        if not ok:
            continue
        pip = fr[y0:y0 + ph, x0:x0 + pw]
        dets = det._yolo_detect(pip)
        tls = [d for d in dets if (d.get("class_name") or "").lower()
               in ("traffic light", "traffic_light")]
        rois = []
        for d in tls:
            a, b, c2, dd = [int(v) for v in d["bbox"][:4]]
            r = pip[max(0, b):min(ph, dd), max(0, a):min(pw, c2)]
            if r.size:
                rois.append(r)
        fr_cache.append((f, truth, rois))
    cap.release()
    del det

    out = {}
    for mode in modes:
        ok_n = 0
        per = {}
        for f, truth, rois in fr_cache:
            votes = Counter()
            for r in rois:
                c = tight_crop(r, mode)
                if c.size == 0 or min(c.shape[:2]) < 3:
                    continue
                st, conf = T.classify_traffic_light(c)
                votes[st] += 1
            real = {k: v for k, v in votes.items() if k not in ("none", "unknown")}
            pred = max(real, key=real.get) if real else "none"
            hit = (pred == truth.lower())
            ok_n += 1 if hit else 0
            per.setdefault(truth, [0, 0])
            per[truth][1] += 1
            per[truth][0] += 1 if hit else 0
        out[mode] = (ok_n, len(fr_cache), per)
    return out


def main():
    modes = ["raw", "lit", "peak9", "peak13", "peak17", "upper"]
    all_res = {}
    for name, path in MODELS:
        print("=" * 80)
        print("%s" % name)
        print("=" * 80)
        res = run_one(name, path, modes)
        for m, (a, b, per) in res.items():
            txt = "  ".join("%s %d/%d" % (t, x, y) for t, (x, y) in sorted(per.items()))
            print("   %-8s %2d/%2d = %3.0f%%   %s" % (m, a, b, 100.0 * a / max(1, b), txt))
        all_res[name] = res
        print()

    print("=" * 80)
    print("总表（行=模型, 列=裁图方式 -> 准确率）")
    print("%-12s %s" % ("模型", "".join("%-10s" % m for m in modes)))
    for name, res in all_res.items():
        print("%-12s %s" % (name, "".join(
            "%-10s" % ("%d/%d" % (res[m][0], res[m][1])) for m in modes)))
    print()
    print("各方式下 红灯 判对情况（闯红灯判定最关键）:")
    print("%-12s %s" % ("模型", "".join("%-10s" % m for m in modes)))
    for name, res in all_res.items():
        row = ""
        for m in modes:
            per = res[m][2]
            r = per.get("Red", [0, 0])
            row += "%-10s" % ("%d/%d" % (r[0], r[1]))
        print("%-12s %s" % (name, row))
    return 0


if __name__ == "__main__":
    sys.exit(main())
