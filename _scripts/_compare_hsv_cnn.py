"""HSV vs CNN 准确率对比（全量视频帧，这是决定是否替换的依据）"""

import collections
import glob
import os
import sys

API = r"E:\output\1\api"
sys.path.insert(0, API)
os.chdir(API)

import cv2  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402
import torch.nn.functional as F  # noqa: E402
from ultralytics import YOLO  # noqa: E402

sys.path.insert(0, r"E:\output\_scripts")
from _train_tl_classifier import TLColorNet, CLASSES, IMG, preprocess  # noqa: E402

VIDEOS = [
    ("v1", r"E:\output\1\test_assets\traffic_videos\ea1ca6cbb27653af24ebe585d56f0ffd.mp4"),
    ("v2", r"E:\output\1\test_assets\traffic_videos\701c5154f47975564a8039bb03bd3340.mp4"),
]
COCO = r"E:\output\1\zhitong\training\models\yolov8s.pt"
CKPT = r"E:\output\_tl_color_cls\tl_color_cnn.pt"
OUT = r"E:\output\_tl_compare"
os.makedirs(OUT, exist_ok=True)
DEV = "cuda" if torch.cuda.is_available() else "cpu"

ck = torch.load(CKPT, map_location=DEV, weights_only=False)
net = TLColorNet(len(ck["classes"])).to(DEV)
net.load_state_dict(ck["model_state"])
net.eval()
print(f"CNN 权重: 验证准确率 {ck['val_acc']:.3f}  类别 {ck['classes']}  训练于 {ck['trained_at']}")

m = YOLO(COCO)


def hsv_state(roi):
    if roi.size == 0 or roi.shape[0] < 4 or roi.shape[1] < 4:
        return "unknown", 0
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    masks = {
        "red": cv2.bitwise_or(cv2.inRange(hsv, (0, 70, 60), (10, 255, 255)),
                              cv2.inRange(hsv, (170, 70, 60), (180, 255, 255))),
        "yellow": cv2.inRange(hsv, (15, 70, 70), (35, 255, 255)),
        "green": cv2.inRange(hsv, (40, 60, 60), (90, 255, 255)),
    }
    counts = {k: int(cv2.countNonZero(v)) for k, v in masks.items()}
    total = roi.shape[0] * roi.shape[1]
    best = max(counts, key=counts.get)
    ok = total > 0 and counts[best] >= max(6, int(total * 0.02))
    return (best if ok else "unknown"), counts[best]


def cnn_state(roi):
    if roi.size == 0 or roi.shape[0] < 8 or roi.shape[1] < 8:
        return "unknown", 0.0
    im = cv2.resize(roi, (IMG, IMG), interpolation=cv2.INTER_AREA)
    im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    x = torch.from_numpy(im.transpose(2, 0, 1).copy()).unsqueeze(0).to(DEV)
    with torch.no_grad():
        prob = torch.softmax(net(x), 1)[0]
    i = int(prob.argmax())
    return CLASSES[i], float(prob[i])


stat_hsv, stat_cnn = collections.Counter(), collections.Counter()
conf_list = []
n = 0
disagree = []

for tag, vp in VIDEOS:
    cap = cv2.VideoCapture(vp)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = max(1, total // 50)
    for fi in range(0, total, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
        ok, frame = cap.read()
        if not ok:
            continue
        r = m.predict(frame, imgsz=1280, conf=0.25, verbose=False, device=0)[0]
        for j, b in enumerate(r.boxes or []):
            cls = r.names.get(int(b.cls[0])) if isinstance(r.names, dict) else r.names[int(b.cls[0])]
            if "traffic light" not in str(cls).lower():
                continue
            bb = [int(v) for v in b.xyxy[0].tolist()]
            x1, y1, x2, y2 = bb
            H, W = frame.shape[:2]
            w, h = x2 - x1, y2 - y1
            if w < 8 or h < 8:
                continue
            padx, pady = int(w * 0.25), int(h * 0.25)
            roi = frame[max(0, y1 - pady):min(H, y2 + pady),
                        max(0, x1 - padx):min(W, x2 + padx)]
            hs, hc = hsv_state(roi)
            cs, cc = cnn_state(roi)
            stat_hsv[hs] += 1
            stat_cnn[cs] += 1
            conf_list.append(cc)
            n += 1
            if hs != cs:
                disagree.append((tag, fi, j, hs, hc, cs, cc, w, h))
                if len(disagree) <= 12:
                    big = cv2.resize(roi, None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST)
                    cv2.imwrite(os.path.join(OUT, f"{tag}_f{fi}_{j}_hsv-{hs}_cnn-{cs}_{cc:.2f}.png"), big)
    cap.release()

print()
print("=" * 76)
print(f"总样本: {n}")
print(f"  HSV 判色分布: {dict(stat_hsv)}")
print(f"  CNN 判色分布: {dict(stat_cnn)}")
if conf_list:
    conf_list.sort()
    print(f"  CNN 置信度: 中位 {conf_list[len(conf_list)//2]:.3f}  "
          f"最低 {conf_list[0]:.3f}  最高 {conf_list[-1]:.3f}")
    low = sum(1 for c in conf_list if c < 0.6)
    print(f"  CNN 低置信(<0.6): {low}/{n}")
print()
print(f"两者不一致: {len(disagree)} 处  (对比图已存 {OUT})")
for d in disagree[:8]:
    print(f"  {d[0]} 帧{d[1]:4d} #{d[2]}: HSV={d[3]}({d[4]}px) vs CNN={d[5]}({d[6]:.2f})  {d[7]}x{d[8]}")
print("=" * 76)
print("判读要点：")
print("  - CNN 的 unknown 应远少于 HSV（HSV 遇背光/偏色即放弃）")
print("  - 不一致样本需人工看图仲裁（对比图已导出）")
