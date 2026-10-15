"""严谨评估红绿灯分类器：多折交叉验证 + 误检拒识测试

目的：判断模型是"真学到了颜色"还是"过拟合到尺寸/形状"
方法：
  1. 5 折交叉验证（每折重新训练），看平均准确率
  2. 用不含红绿灯的画面裁剪（限速牌等）测试"是否会被误判成红黄绿"
  3. 输出混淆矩阵，看哪类最容易错
"""

import collections
import glob
import os
import random
import sys
import time

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

sys.path.insert(0, r"E:\output\_scripts")
from _train_tl_classifier import (CLASSES, IMG, TLColorNet, augment,  # noqa: E402
                                  preprocess, to_tensor)

ROOT = r"E:\output\_tl_dataset"
DEV = "cuda" if torch.cuda.is_available() else "cpu"
SEED = 42


def load_items():
    items = []
    for ci, cls in enumerate(CLASSES):
        for p in glob.glob(os.path.join(ROOT, cls, "*.png")):
            items.append((p, ci))
    return items


def train_fold(tr_items, epochs=60, seed=0):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    net = TLColorNet(len(CLASSES)).to(DEV)
    opt = torch.optim.Adam(net.parameters(), lr=1e-3, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs)
    crit = nn.CrossEntropyLoss()

    class DS(torch.utils.data.Dataset):
        def __len__(self): return len(tr_items)
        def __getitem__(self, i):
            p, y = tr_items[i]
            im = preprocess(p)
            if im is None:
                im = np.zeros((IMG, IMG, 3), np.float32)
            im = augment(im)
            return to_tensor(im), y

    dl = torch.utils.data.DataLoader(DS(), batch_size=16, shuffle=True, num_workers=0)
    for ep in range(epochs):
        net.train()
        for x, y in dl:
            x, y = x.to(DEV), y.to(DEV)
            opt.zero_grad(); loss = crit(net(x), y); loss.backward(); opt.step()
        sched.step()
    net.eval()
    return net


def predict(net, path):
    im = preprocess(path)
    if im is None:
        return None, 0.0
    x = to_tensor(im).unsqueeze(0).to(DEV)
    with torch.no_grad():
        p = torch.softmax(net(x), 1)[0]
    i = int(p.argmax())
    return CLASSES[i], float(p[i])


items = load_items()
by_cls = collections.defaultdict(list)
for p, y in items:
    by_cls[y].append(p)
print("=" * 78)
print("数据分布: " + "  ".join(f"{CLASSES[k]}={len(v)}" for k, v in sorted(by_cls.items())))
print("=" * 78)

# ---------------- 5 折交叉验证（分层） ----------------
print("\n【5 折分层交叉验证】")
random.seed(SEED)
folds = [[] for _ in range(5)]
for ci, ps in by_cls.items():
    ps = ps[:]
    random.shuffle(ps)
    for i, p in enumerate(ps):
        folds[i % 5].append((p, ci))

accs, cm = [], np.zeros((len(CLASSES), len(CLASSES)), dtype=int)
t0 = time.time()
for k in range(5):
    va = folds[k]
    tr = [it for j, f in enumerate(folds) if j != k for it in f]
    net = train_fold(tr, epochs=60, seed=SEED + k)
    correct = 0
    for p, y in va:
        pred, conf = predict(net, p)
        pi = CLASSES.index(pred) if pred in CLASSES else -1
        if pi == y:
            correct += 1
        if pi >= 0:
            cm[y][pi] += 1
    acc = correct / max(1, len(va))
    accs.append(acc)
    print(f"  折{k+1}: 验证 {len(va)} 张  准确率 {acc:.3f}")
print(f"  平均准确率: {np.mean(accs):.3f} ± {np.std(accs):.3f}   (耗时 {time.time()-t0:.0f}s)")

print("\n【混淆矩阵】(行=真实, 列=预测)")
print("        " + "".join(f"{c:>9}" for c in CLASSES))
for i, c in enumerate(CLASSES):
    print(f"  {c:6s}" + "".join(f"{cm[i][j]:>9}" for j in range(len(CLASSES))))

# ---------------- 全量训练 + 误检拒识测试 ----------------
print("\n【全量训练 + 误检拒识测试】")
net = train_fold(items, epochs=80, seed=SEED)

# 构造"非红绿灯"测试集：从画面中随机裁不含红绿灯的区域
FAIL = []
VIDEOS = [
    r"E:\output\1\test_assets\traffic_videos\ea1ca6cbb27653af24ebe585d56f0ffd.mp4",
    r"E:\output\1\test_assets\traffic_videos\701c5154f47975564a8039bb03bd3340.mp4",
]
rng = random.Random(7)
neg_conf = []
for vp in VIDEOS:
    cap = cv2.VideoCapture(vp)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    for fi in range(0, total, max(1, total // 10)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
        ok, frame = cap.read()
        if not ok:
            continue
        H, W = frame.shape[:2]
        # 上半部分随机裁 40x80 区域（多半是天空/建筑/路牌，非红绿灯）
        for _ in range(6):
            w = rng.randint(30, 60); h = rng.randint(40, 90)
            x = rng.randint(0, max(1, W - w)); y = rng.randint(0, max(1, int(H * 0.5) - h))
            crop = frame[y:y+h, x:x+w]
            if crop.size == 0:
                continue
            im = cv2.resize(crop, (IMG, IMG))
            im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            x_t = torch.from_numpy(im.transpose(2, 0, 1).copy()).unsqueeze(0).to(DEV)
            with torch.no_grad():
                p = torch.softmax(net(x_t), 1)[0]
            neg_conf.append(float(p.max()))
    cap.release()

neg_conf = np.array(neg_conf)
print(f"  非红绿灯随机裁剪 {len(neg_conf)} 张：")
if len(neg_conf):
    print(f"    高置信(>=0.9)被判为红黄绿: {(neg_conf>=0.9).sum()} 张 ({(neg_conf>=0.9).mean()*100:.1f}%)")
    print(f"    >=0.7: {(neg_conf>=0.7).sum()}   >=0.5: {(neg_conf>=0.5).sum()}")
    print(f"    置信度中位 {np.median(neg_conf):.3f}")
print("=" * 78)
print("判读：交叉验证准确率高 + 非红绿灯拒识率高 -> 模型可信，可接入")
print("      交叉验证低 或 非红绿灯大量被误判 -> 模型过拟合，需更多/更干净数据")
