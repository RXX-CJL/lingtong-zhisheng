"""4 类模型在真实视频上的最终验证：HSV vs CNN4 对比 + 误检拒识实际效果"""

import collections
import glob
import os
import sys

API = r"E:\output\1\api"
sys.path.insert(0, API)
sys.path.insert(0, r"E:\output\_scripts")
os.chdir(API)

import cv2  # noqa: E402
import torch  # noqa: E402
from ultralytics import YOLO  # noqa: E402

from _train_tl_classifier import TLColorNet, IMG, preprocess, to_tensor  # noqa: E402

VIDEOS = [
    ("v1", r"E:\output\1\test_assets\traffic_videos\ea1ca6cbb27653af24ebe585d56f0ffd.mp4"),
    ("v2", r"E:\output\1\test_assets\traffic_videos\701c5154f47975564a8039bb03bd3340.mp4"),
]
COCO = r"E:\output\1\zhitong\training\models\yolov8s.pt"
CKPT = r"E:\output\_tl_color_cls\tl_color_cnn4.pt"
DEV = "cuda" if torch.cuda.is_available() else "cpu"

ck = torch.load(CKPT, map_location=DEV, weights_only=False)
CLS4 = ck["classes"]
net = TLColorNet(len(CLS4)).to(DEV)
net.load_state_dict(ck["model_state"])
net.eval()
print(f"4类模型: {CLS4}  交叉验证准确率 {ck['cv_acc']:.3f}")

m = YOLO(COCO)


def hsv_state(roi):
    if roi.size == 0 or roi.shape[0] < 4 or roi.shape[1] < 4:
        return "unknown"
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
    return best if (total > 0 and counts[best] >= max(6, int(total * 0.02))) else "unknown"


def cnn4(roi):
    if roi.size == 0 or roi.shape[0] < 8 or roi.shape[1] < 8:
        return "none", 0.0
    im = cv2.resize(roi, (IMG, IMG), interpolation=cv2.INTER_AREA)
    im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB).astype("float32") / 255.0
    x = torch.from_numpy(im.transpose(2, 0, 1).copy()).unsqueeze(0).to(DEV)
    with torch.no_grad():
        p = torch.softmax(net(x), 1)[0]
    i = int(p.argmax())
    return CLS4[i], float(p[i])


st_hsv, st_cnn = collections.Counter(), collections.Counter()
n = 0
print()
print(f"{'视频':>4} {'帧':>5} | {'HSV':>26} | {'CNN4':>30}")
print("-" * 78)
for tag, vp in VIDEOS:
    cap = cv2.VideoCapture(vp)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    for fi in range(0, total, max(1, total // 25)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
        ok, frame = cap.read()
        if not ok:
            continue
        r = m.predict(frame, imgsz=1280, conf=0.25, verbose=False, device=0)[0]
        hs_list, cn_list = [], []
        for b in (r.boxes or []):
            cls = r.names.get(int(b.cls[0])) if isinstance(r.names, dict) else r.names[int(b.cls[0])]
            if "traffic light" not in str(cls).lower():
                continue
            x1, y1, x2, y2 = [int(v) for v in b.xyxy[0].tolist()]
            H, W = frame.shape[:2]
            w, h = x2 - x1, y2 - y1
            if w < 8 or h < 8:
                continue
            px, py = int(w * 0.25), int(h * 0.25)
            roi = frame[max(0, y1 - py):min(H, y2 + py), max(0, x1 - px):min(W, x2 + px)]
            s1 = hsv_state(roi)
            s2, c2 = cnn4(roi)
            st_hsv[s1] += 1
            st_cnn[s2] += 1
            n += 1
            hs_list.append(s1)
            cn_list.append(f"{s2}{'' if s2=='none' else f'({c2:.2f})'}")
        if hs_list or cn_list:
            print(f"{tag:>4} {fi:>5} | {str(hs_list)[:26]:>26} | {str(cn_list)[:30]:>30}")
    cap.release()

print()
print("=" * 78)
print(f"总检出 {n}")
print(f"  HSV : {dict(st_hsv)}")
print(f"  CNN4: {dict(st_cnn)}")
real_cnn = sum(v for k, v in st_cnn.items() if k != "none")
print()
print(f"  CNN4 判定为'非红绿灯'的数量: {st_cnn.get('none', 0)}  ({st_cnn.get('none',0)/max(1,n)*100:.1f}%)")
print(f"  CNN4 判定为红/黄/绿的数量  : {real_cnn}  ({real_cnn/max(1,n)*100:.1f}%)")
print(f"  HSV  无法判定的数量        : {st_hsv.get('unknown', 0)}  ({st_hsv.get('unknown',0)/max(1,n)*100:.1f}%)")
print("=" * 78)
