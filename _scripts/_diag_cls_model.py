"""诊断分类模型：探查原始输出结构，寻找绕过 ultralytics.yolo 兼容问题的方法"""

import glob
import os
import sys

API = r"E:\output\1\api"
sys.path.insert(0, API)
os.chdir(API)

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from ultralytics import YOLO  # noqa: E402

CLS = glob.glob(r"E:\output\_models_dl\traffic_light_color*\**\weights\best.pt", recursive=True)[0]
VIDEO = r"E:\output\1\test_assets\traffic_videos\ea1ca6cbb27653af24ebe585d56f0ffd.mp4"

m = YOLO(CLS, task="classify")
print("模型对象类型:", type(m).__name__)
print("model.task:", getattr(m.model, "task", "?"))
print("names:", m.names)

cap = cv2.VideoCapture(VIDEO)
cap.set(cv2.CAP_PROP_POS_FRAMES, 123)
ok, frame = cap.read()
cap.release()

m_coco = YOLO(r"E:\output\1\zhitong\training\models\yolov8s.pt")
r = m_coco.predict(frame, imgsz=1280, conf=0.25, verbose=False, device=0)[0]
crops = []
for b in (r.boxes or []):
    cls = r.names.get(int(b.cls[0])) if isinstance(r.names, dict) else r.names[int(b.cls[0])]
    if "traffic light" in str(cls).lower():
        bb = [int(v) for v in b.xyxy[0].tolist()]
        c = frame[max(0, bb[1]):bb[3], max(0, bb[0]):bb[2]]
        if c.size:
            crops.append(c)
print(f"取到 {len(crops)} 个红绿灯裁剪")

print()
print("=" * 74)
print("方式 1：predict 原始返回值结构")
print("=" * 74)
rr = m.predict(crops[0], imgsz=64, verbose=False, device=0)[0]
print("  返回类型:", type(rr).__name__)
print("  可用属性:", [a for a in dir(rr) if not a.startswith('_')][:25])
print("  probs:", rr.probs)
print("  boxes:", getattr(rr, "boxes", None))

print()
print("=" * 74)
print("方式 2：直接对 tensor 前向（绕过 predict）")
print("=" * 74)
try:
    import torch
    net = m.model
    net.eval()
    x = cv2.resize(crops[0], (64, 64))
    x = cv2.cvtColor(x, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    t = torch.from_numpy(x).permute(2, 0, 1).unsqueeze(0)
    dev = next(net.parameters()).device
    t = t.to(dev)
    with torch.no_grad():
        out = net(t)
    o = out[0] if isinstance(out, (list, tuple)) else out
    if hasattr(o, "shape") and o.dim() == 2:
        probs = torch.softmax(o, dim=1)[0]
        idx = int(probs.argmax())
        print(f"  logits shape: {tuple(o.shape)}")
        print(f"  预测: {m.names[idx]}  置信度={float(probs[idx]):.4f}")
        print(f"  全部概率: {{" + ", ".join(f"{m.names[i]}={float(p):.3f}" for i, p in enumerate(probs)) + "}")
    else:
        print("  输出结构异常:", type(o), getattr(o, 'shape', None))
except Exception as e:
    print(f"  前向失败: {type(e).__name__}: {str(e)[:200]}")

print()
print("=" * 74)
print("方式 3：对全部裁剪批量前向（验证可用性）")
print("=" * 74)
try:
    import torch
    net = m.model
    net.eval()
    dev = next(net.parameters()).device
    for i, c in enumerate(crops):
        x = cv2.resize(c, (64, 64))
        x = cv2.cvtColor(x, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        t = torch.from_numpy(x).permute(2, 0, 1).unsqueeze(0).to(dev)
        with torch.no_grad():
            o = net(t)
        o = o[0] if isinstance(o, (list, tuple)) else o
        probs = torch.softmax(o, dim=1)[0]
        idx = int(probs.argmax())
        print(f"  裁剪#{i+1} {c.shape[1]}x{c.shape[0]}: {m.names[idx]} ({float(probs[idx]):.3f})")
except Exception as e:
    print(f"  失败: {type(e).__name__}: {str(e)[:200]}")
