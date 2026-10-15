"""诊断专用模型失败原因：检查 checkpoint 元数据与实际推理行为"""

import glob
import os
import sys

API = r"E:\output\1\api"
sys.path.insert(0, API)
os.chdir(API)

import torch  # noqa: E402
from ultralytics import YOLO  # noqa: E402

DET = glob.glob(r"E:\output\_models_dl\traffic_light_detection*\**\weights\best.pt", recursive=True)[0]
CLS = glob.glob(r"E:\output\_models_dl\traffic_light_color*\**\weights\best.pt", recursive=True)[0]

for label, p in (("检测模型", DET), ("分类模型", CLS)):
    print("=" * 76)
    print(f"{label}: {p}")
    print("=" * 76)
    try:
        ck = torch.load(p, map_location="cpu", weights_only=False)
        print(f"  checkpoint 顶层键: {list(ck.keys()) if isinstance(ck, dict) else type(ck)}")
        for k in ("task", "date", "version", "train_args", "model", "ema"):
            if isinstance(ck, dict) and k in ck:
                v = ck[k]
                if k in ("model", "ema"):
                    print(f"  {k}: <{type(v).__name__}>  task={getattr(v, 'task', '?')}  yaml={getattr(getattr(v, 'yaml', None), 'get', lambda *a: '?')('task') if hasattr(getattr(v,'yaml',None),'get') else '?'}")
                elif k == "train_args":
                    ta = v if isinstance(v, dict) else {}
                    keep = {kk: ta.get(kk) for kk in ("data", "imgsz", "epochs", "model", "batch", "task") if kk in ta}
                    print(f"  train_args(节选): {keep}")
                else:
                    print(f"  {k}: {str(v)[:100]}")
    except Exception as e:
        print(f"  torch.load 失败: {type(e).__name__}: {str(e)[:150]}")
    print()

print("=" * 76)
print("用 task 参数显式加载并测试")
print("=" * 76)

# 分类模型：显式 task='classify'
print("--- 分类模型 (task='classify') ---")
try:
    m = YOLO(CLS, task="classify")
    print(f"  names: {m.names}")
    import cv2
    VIDEO = r"E:\output\1\test_assets\traffic_videos\ea1ca6cbb27653af24ebe585d56f0ffd.mp4"
    cap = cv2.VideoCapture(VIDEO)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 123)
    ok, frame = cap.read()
    cap.release()
    m_coco = YOLO(r"E:\output\1\zhitong\training\models\yolov8s.pt")
    r = m_coco.predict(frame, imgsz=1280, conf=0.25, verbose=False, device=0)[0]
    n = 0
    for b in (r.boxes or []):
        cls = r.names.get(int(b.cls[0])) if isinstance(r.names, dict) else r.names[int(b.cls[0])]
        if "traffic light" not in str(cls).lower():
            continue
        bb = [int(v) for v in b.xyxy[0].tolist()]
        crop = frame[max(0, bb[1]):bb[3], max(0, bb[0]):bb[2]]
        if crop.size == 0:
            continue
        n += 1
        for imgsz in (64, 128, 224):
            try:
                rr = m.predict(crop, imgsz=imgsz, verbose=False, device=0)[0]
                top1 = int(rr.probs.top1) if rr.probs is not None else -1
                conf = float(rr.probs.top1conf) if rr.probs is not None else 0
                name = m.names[top1] if top1 >= 0 else "None"
                print(f"    裁剪#{n} {crop.shape[1]}x{crop.shape[0]} imgsz={imgsz}: {name} ({conf:.3f})")
            except Exception as e:
                print(f"    裁剪#{n} imgsz={imgsz} 失败: {str(e)[:80]}")
except Exception as e:
    print(f"  加载失败: {type(e).__name__}: {str(e)[:200]}")

print()
print("--- 检测模型：不同 imgsz/conf ---")
try:
    md = YOLO(DET)
    print(f"  names: {md.names}  task={getattr(md, 'task', '?')}")
    import cv2
    VIDEO = r"E:\output\1\test_assets\traffic_videos\ea1ca6cbb27653af24ebe585d56f0ffd.mp4"
    cap = cv2.VideoCapture(VIDEO)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 123)
    ok, frame = cap.read()
    cap.release()
    for imgsz in (640, 960, 1280):
        for conf in (0.1, 0.25):
            r = md.predict(frame, imgsz=imgsz, conf=conf, verbose=False, device=0)[0]
            n = len(r.boxes) if r.boxes is not None else 0
            print(f"    imgsz={imgsz} conf={conf}: 检出 {n}")
except Exception as e:
    print(f"  失败: {type(e).__name__}: {str(e)[:200]}")
