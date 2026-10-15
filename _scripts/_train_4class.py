"""生成负样本（非红绿灯）并训练 4 类模型（green/red/yellow/none）

负样本来源：从视频中随机裁剪，但**排除所有已检出的红绿灯框附近区域**
（否则会把真红绿灯当负样本，毒化训练）

输出：
  E:\\output\\_tl_dataset\\none\\*.png   （负样本）
  E:\\output\\_tl_color_cls\\tl_color_cnn4.pt （4 类权重）
"""

import glob
import os
import random
import sys

API = r"E:\output\1\api"
sys.path.insert(0, API)
os.chdir(API)

import cv2  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402
import torch.nn as nn  # noqa: E402
import torch.nn.functional as F  # noqa: E402
from ultralytics import YOLO  # noqa: E402

ROOT = r"E:\output\_tl_dataset"
NEG_DIR = os.path.join(ROOT, "none")
OUT_DIR = r"E:\output\_tl_color_cls"
os.makedirs(NEG_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)

CLASSES4 = ["green", "red", "yellow", "none"]
COCO = r"E:\output\1\zhitong\training\models\yolov8s.pt"
VIDEOS = [
    r"E:\output\1\test_assets\traffic_videos\ea1ca6cbb27653af24ebe585d56f0ffd.mp4",
    r"E:\output\1\test_assets\traffic_videos\701c5154f47975564a8039bb03bd3340.mp4",
]
IMG = 64
DEV = "cuda" if torch.cuda.is_available() else "cpu"
TARGET_NEG = 260
SEED = 42

# ------------------------------------------------------------------ 生成负样本
rng = random.Random(SEED)
np.random.seed(SEED)
m = YOLO(COCO)
saved = 0
print("生成负样本（排除已检出红绿灯区域）...")
for vp in VIDEOS:
    if saved >= TARGET_NEG:
        break
    tag = "v1" if "ea1ca6" in vp else "v2"
    cap = cv2.VideoCapture(vp)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    for fi in range(0, total, max(1, total // 30)):
        if saved >= TARGET_NEG:
            break
        cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
        ok, frame = cap.read()
        if not ok:
            continue
        H, W = frame.shape[:2]
        # 已检出红绿灯的框（含扩边），用于排除
        r = m.predict(frame, imgsz=1280, conf=0.25, verbose=False, device=0)[0]
        avoid = []
        for b in (r.boxes or []):
            cls = r.names.get(int(b.cls[0])) if isinstance(r.names, dict) else r.names[int(b.cls[0])]
            if "traffic light" in str(cls).lower():
                x1, y1, x2, y2 = [float(v) for v in b.xyxy[0].tolist()]
                px, py = (x2 - x1) * 0.6, (y2 - y1) * 0.6
                avoid.append((x1 - px, y1 - py, x2 + px, y2 + py))

        def overlaps(bx):
            for ax1, ay1, ax2, ay2 in avoid:
                if not (bx[2] < ax1 or bx[0] > ax2 or bx[3] < ay1 or bx[1] > ay2):
                    return True
            return False

        tries = 0
        while tries < 40 and saved < TARGET_NEG:
            tries += 1
            w = rng.randint(24, 70)
            h = rng.randint(30, 90)
            x = rng.randint(0, max(1, W - w))
            y = rng.randint(0, max(1, H - h))
            box = (x, y, x + w, y + h)
            if overlaps(box):
                continue
            crop = frame[y:y + h, x:x + w]
            if crop.size == 0:
                continue
            # 排除几乎纯色的区域（天空/墙面，缺乏信息量）
            if crop.reshape(-1, 3).std(axis=0).mean() < 12:
                continue
            big = cv2.resize(crop, None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST)
            cv2.imwrite(os.path.join(NEG_DIR, f"neg_{tag}_f{fi:04d}_{saved:04d}.png"), big)
            saved += 1
    cap.release()
print(f"  已生成 {saved} 张负样本 -> {NEG_DIR}")

# ------------------------------------------------------------------ 训练 4 类
from _train_tl_classifier import TLColorNet, augment, preprocess, to_tensor  # noqa: E402

items = []
for ci, cls in enumerate(CLASSES4):
    for p in glob.glob(os.path.join(ROOT, cls, "*.png")):
        items.append((p, ci))
from collections import Counter  # noqa: E402
dist = Counter(c for _, c in items)
print()
print("4 类数据分布: " + "  ".join(f"{CLASSES4[k]}={v}" for k, v in sorted(dist.items())))

random.seed(SEED)
by_cls = {}
for p, y in items:
    by_cls.setdefault(y, []).append(p)


def train(items_tr, epochs=80, seed=SEED):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    net = TLColorNet(len(CLASSES4)).to(DEV)
    opt = torch.optim.Adam(net.parameters(), lr=1e-3, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs)
    crit = nn.CrossEntropyLoss()

    class DS(torch.utils.data.Dataset):
        def __len__(self): return len(items_tr)
        def __getitem__(self, i):
            p, y = items_tr[i]
            im = preprocess(p)
            if im is None:
                im = np.zeros((IMG, IMG, 3), np.float32)
            return to_tensor(augment(im)), y

    dl = torch.utils.data.DataLoader(DS(), batch_size=16, shuffle=True, num_workers=0)
    for ep in range(epochs):
        net.train()
        for x, y in dl:
            x, y = x.to(DEV), y.to(DEV)
            opt.zero_grad(); F.cross_entropy(net(x), y).backward(); opt.step()
        sched.step()
    net.eval()
    return net


# 分层 5 折（含 none 类）
random.seed(SEED)
folds = [[] for _ in range(5)]
for ci, ps in by_cls.items():
    ps = ps[:]; random.shuffle(ps)
    for i, p in enumerate(ps):
        folds[i % 5].append((p, ci))

print("\n【5 折交叉验证（4 类）】")
accs = []
cm = np.zeros((4, 4), dtype=int)
for k in range(5):
    va = folds[k]
    tr = [it for j, f in enumerate(folds) if j != k for it in f]
    net = train(tr, epochs=70, seed=SEED + k)
    corr = 0
    for p, y in va:
        im = preprocess(p)
        if im is None:
            continue
        x = to_tensor(im).unsqueeze(0).to(DEV)
        with torch.no_grad():
            pi = int(torch.softmax(net(x), 1)[0].argmax())
        if pi == y:
            corr += 1
        cm[y][pi] += 1
    a = corr / max(1, len(va))
    accs.append(a)
    print(f"  折{k+1}: {len(va):>3} 张  准确率 {a:.3f}")
print(f"  平均: {np.mean(accs):.3f} ± {np.std(accs):.3f}")
print("\n【混淆矩阵】(行=真实, 列=预测)")
print("        " + "".join(f"{c:>9}" for c in CLASSES4))
for i, c in enumerate(CLASSES4):
    print(f"  {c:6s}" + "".join(f"{cm[i][j]:>9}" for j in range(4)))

# 全量训练并保存
net = train(items, epochs=90, seed=SEED)
ck = {"model_state": net.state_dict(), "classes": CLASSES4, "img_size": IMG,
      "arch": "TLColorNet-4class", "cv_acc": float(np.mean(accs)),
      "trained_at": __import__("time").strftime("%Y-%m-%d %H:%M:%S")}
path = os.path.join(OUT_DIR, "tl_color_cnn4.pt")
torch.save(ck, path)
print(f"\n4 类权重已保存: {path}  ({os.path.getsize(path)/1024:.0f} KB)")
print(f"5 折平均准确率: {np.mean(accs):.3f}")
