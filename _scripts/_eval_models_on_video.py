"""在演示视频上评测多个判色模型（独立数据，非训练来源）。

真值：帧 0-299=Red，300-399=Green，400-499=Yellow，500+=Red（灯态是钉死的）
被测：CNN4(原) / CNN5(第一版重训) / CNN6(修正数据重训)
"""
import os
import sys
from collections import Counter

import cv2
import numpy as np

sys.path.insert(0, r"E:\output\1\api")
import traffic_light_classifier as T  # noqa: E402
from _train_tl_classifier import TLColorNet, preprocess, to_tensor  # noqa: E402
import torch  # noqa: E402

VID = r"E:\output\_dual_cam_demo\dual_cam_demo_lossless.mkv"
MODELS = [
    ("CNN4_orig", r"E:\output\_tl_color_cls\tl_color_cnn4.pt"),
    ("CNN5_v1", r"E:\output\_tl_color_cls\tl_color_cnn5_carla.pt"),
    ("CNN6_v2", r"E:\output\_tl_color_cls\tl_color_cnn6_carla.pt"),
]
CLASSES = ["green", "red", "yellow", "none"]
DEV = "cuda" if torch.cuda.is_available() else "cpu"
FRAMES = [(30, "Red"), (90, "Red"), (150, "Red"), (210, "Red"), (250, "Red"), (290, "Red"),
          (310, "Green"), (350, "Green"), (380, "Green"), (410, "Yellow"), (440, "Yellow"),
          (470, "Yellow"), (510, "Red")]


def get_boxes(img):
    """用项目真实链路（YOLO）拿红绿灯框"""
    return T  # placeholder


def main():
    # 先一次性把视频帧和框取出来（避免每模型重复跑 YOLO）
    sys.path.insert(0, r"E:\output\1\api")
    from realtime_detector import RealtimeViolationDetector
    det = RealtimeViolationDetector()
    cap = cv2.VideoCapture(VID)
    W, H = int(cap.get(3)), int(cap.get(4))
    pw = int(1920 * 0.26)
    ph = int(pw * 720 / 1280)
    x0, y0 = 1920 - pw - 18, 1080 - ph - 18
    print("CAM-2 画中画: x %d..%d y %d..%d (%dx%d)" % (x0, x0 + pw, y0, y0 + ph, pw, ph))

    cases = []
    for f, truth in FRAMES:
        cap.set(cv2.CAP_PROP_POS_FRAMES, f)
        ok, fr = cap.read()
        if not ok:
            continue
        pip = fr[y0:y0 + ph, x0:x0 + pw]
        dets = det._yolo_detect(pip)
        tls = [d for d in dets if (d.get("class_name") or "").lower()
               in ("traffic light", "traffic_light")]
        crops = []
        for d in tls:
            a, b, c2, dd = [int(v) for v in d["bbox"][:4]]
            roi = pip[max(0, b):min(ph, dd), max(0, a):min(pw, c2)]
            if roi.size and roi.shape[0] >= 4 and roi.shape[1] >= 4:
                crops.append(roi)
        cases.append((f, truth, crops))
    cap.release()
    print("取到 %d 帧，帧均框数 %.1f\n" % (len(cases), np.mean([len(c[2]) for c in cases])))

    summary = {}
    for name, path in MODELS:
        ck = torch.load(path, map_location=DEV, weights_only=False)
        net = TLColorNet(len(CLASSES)).to(DEV)
        net.load_state_dict(ck["model_state"])
        net.eval()
        print("=== %s ===" % name)
        ok_n = 0
        tot = 0
        per_truth = {}
        for f, truth, crops in cases:
            votes = Counter()
            for roi in crops:
                # 与部署一致的内部分辨率：先按模型输入方式处理
                im = cv2.resize(roi, (64, 64), interpolation=cv2.INTER_AREA)
                x = to_tensor(im.astype(np.float32)).unsqueeze(0).to(DEV)
                with torch.no_grad():
                    pi = int(torch.softmax(net(x), 1)[0].argmax())
                votes[CLASSES[pi]] += 1
            # 忽略 none 后取多数票
            real = {k: v for k, v in votes.items() if k != "none"}
            pred = max(real, key=real.get) if real else "none"
            hit = (pred == truth.lower())
            tot += 1
            ok_n += 1 if hit else 0
            per_truth.setdefault(truth, [0, 0])
            per_truth[truth][1] += 1
            per_truth[truth][0] += 1 if hit else 0
            print("   帧 %-4d 真值 %-6s 投票 %-34s -> %-7s %s"
                  % (f, truth, str(dict(votes)), pred, "OK" if hit else "X"))
        print("   合计 %d/%d = %.0f%%" % (ok_n, tot, 100.0 * ok_n / max(1, tot)))
        for t, (a, b) in sorted(per_truth.items()):
            print("      %-7s %d/%d" % (t, a, b))
        summary[name] = (ok_n, tot, per_truth)
        print()

    print("=" * 70)
    print("%-12s %-10s %s" % ("模型", "总准确率", "各态"))
    for name, (a, b, pt) in summary.items():
        det_txt = "  ".join("%s %d/%d" % (t, x, y) for t, (x, y) in sorted(pt.items()))
        print("%-12s %-10s %s" % (name, "%d/%d=%.0f%%" % (a, b, 100.0 * a / max(1, b)), det_txt))
    return 0


if __name__ == "__main__":
    sys.exit(main())
