"""红绿灯颜色分类器训练（照 CSDN 博客架构：2 层卷积 + 2 层全连接 + log_softmax）

数据：E:\\output\\_tl_dataset\\{red,yellow,green}
  - unknown 目录不参与训练（含误检样本）
  - 小样本（~117 张）-> 强数据增强 + 分层划分

参考博客的超参思路：
  输入 60x32x3，conv1(3->6,5x5) -> maxpool -> conv2(6->16,5x5) -> maxpool
  -> fc1(960->120) -> fc2(120->84) -> fc3(84->3) -> log_softmax
本实现做了必要改进：
  - 输入 64x64（原图信息更多）
  - 加 BatchNorm（小样本收敛更稳）
  - 加数据增强（翻转/亮度/对比度/轻微旋转）
  - 用 CrossEntropyLoss（等价于 log_softmax + NLL）
"""

import glob
import json
import os
import random
import sys
import time

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

ROOT = r"E:\output\_tl_dataset"
OUT_DIR = r"E:\output\_tl_color_cls"
os.makedirs(OUT_DIR, exist_ok=True)
CLASSES = ["green", "red", "yellow"]     # 与下载模型一致的顺序
IMG = 64
SEED = 42
EPOCHS = 80
BATCH = 16
LR = 1e-3

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
DEV = "cuda" if torch.cuda.is_available() else "cpu"


# ---------------------------------------------------------------- 数据
def load_items():
    items = []
    for ci, cls in enumerate(CLASSES):
        for p in glob.glob(os.path.join(ROOT, cls, "*.png")):
            items.append((p, ci))
    random.shuffle(items)
    return items


def preprocess(path, size=IMG):
    im = cv2.imread(path)
    if im is None:
        return None
    im = cv2.resize(im, (size, size), interpolation=cv2.INTER_AREA)
    im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    return im


def augment(im):
    # 水平翻转
    if random.random() < 0.5:
        im = im[:, ::-1, :]
    # 亮度 / 对比度
    if random.random() < 0.7:
        a = 1.0 + random.uniform(-0.25, 0.25)      # 对比度
        b = random.uniform(-0.12, 0.12)            # 亮度
        im = np.clip(im * a + b, 0, 1)
    # 轻微旋转 / 平移
    if random.random() < 0.5:
        ang = random.uniform(-12, 12)
        tx, ty = random.uniform(-0.08, 0.08), random.uniform(-0.08, 0.08)
        M = cv2.getRotationMatrix2D((IMG / 2, IMG / 2), ang, 1.0)
        M[0, 2] += tx * IMG
        M[1, 2] += ty * IMG
        im = cv2.warpAffine(im, M, (IMG, IMG), borderMode=cv2.BORDER_REPLICATE)
    return im


def to_tensor(arr):
    return torch.from_numpy(arr.transpose(2, 0, 1).copy()).float()


class DS(torch.utils.data.Dataset):
    def __init__(self, items, train=True):
        self.items = items
        self.train = train

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        p, y = self.items[i]
        im = preprocess(p)
        if im is None:
            im = np.zeros((IMG, IMG, 3), np.float32)
        if self.train:
            im = augment(im)
        return to_tensor(im), y


# ---------------------------------------------------------------- 模型
class TLColorNet(nn.Module):
    """博客架构 + BatchNorm 改进"""

    def __init__(self, n_cls=3):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 16, 5, padding=2)
        self.bn1 = nn.BatchNorm2d(16)
        self.conv2 = nn.Conv2d(16, 32, 5, padding=2)
        self.bn2 = nn.BatchNorm2d(32)
        self.conv3 = nn.Conv2d(32, 64, 3, padding=1)
        self.bn3 = nn.BatchNorm2d(64)
        self.pool = nn.MaxPool2d(2, 2)
        self.drop = nn.Dropout(0.35)
        self.fc1 = nn.Linear(64 * 8 * 8, 128)
        self.fc2 = nn.Linear(128, 64)
        self.fc3 = nn.Linear(64, n_cls)

    def forward(self, x):
        x = self.pool(F.relu(self.bn1(self.conv1(x))))     # 64->32
        x = self.pool(F.relu(self.bn2(self.conv2(x))))     # 32->16
        x = self.pool(F.relu(self.bn3(self.conv3(x))))     # 16->8
        x = x.view(x.size(0), -1)
        x = self.drop(F.relu(self.fc1(x)))
        x = F.relu(self.fc2(x))
        return self.fc3(x)          # 返回 logits，配 CrossEntropyLoss


def main():
    items = load_items()
    from collections import Counter
    dist = Counter(c for _, c in items)
    print("=" * 74)
    print(f"样本总数: {len(items)}  " +
          "  ".join(f"{CLASSES[k]}={v}" for k, v in sorted(dist.items())))
    print(f"设备: {DEV}   输入: {IMG}x{IMG}   轮数: {EPOCHS}")
    print("=" * 74)

    # 分层划分 train/val（每类至少留 1 张验证）
    by_cls = {i: [] for i in range(len(CLASSES))}
    for p, y in items:
        by_cls[y].append(p)
    tr, va = [], []
    for ci, ps in by_cls.items():
        random.shuffle(ps)
        n_val = max(1, int(round(len(ps) * 0.2)))
        va += [(p, ci) for p in ps[:n_val]]
        tr += [(p, ci) for p in ps[n_val:]]
    print(f"训练 {len(tr)}  验证 {len(va)}")

    dl_tr = torch.utils.data.DataLoader(DS(tr, True), batch_size=BATCH,
                                        shuffle=True, num_workers=0)
    dl_va = torch.utils.data.DataLoader(DS(va, False), batch_size=BATCH,
                                        shuffle=False, num_workers=0)

    net = TLColorNet(len(CLASSES)).to(DEV)
    opt = torch.optim.Adam(net.parameters(), lr=LR, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOCHS)
    crit = nn.CrossEntropyLoss()

    best_acc, best_state, hist = 0.0, None, []
    t0 = time.time()
    for ep in range(1, EPOCHS + 1):
        net.train()
        tl, tn = 0.0, 0
        for x, y in dl_tr:
            x, y = x.to(DEV), y.to(DEV)
            opt.zero_grad()
            out = net(x)
            loss = crit(out, y)
            loss.backward()
            opt.step()
            tl += loss.item() * y.size(0)
            tn += y.size(0)
        sched.step()

        net.eval()
        correct = tot = 0
        with torch.no_grad():
            for x, y in dl_va:
                x, y = x.to(DEV), y.to(DEV)
                pred = net(x).argmax(1)
                correct += (pred == y).sum().item()
                tot += y.size(0)
        acc = correct / max(1, tot)
        hist.append({"epoch": ep, "loss": round(tl / max(1, tn), 4), "val_acc": round(acc, 4)})
        if acc >= best_acc:
            best_acc = acc
            best_state = {k: v.detach().cpu().clone() for k, v in net.state_dict().items()}
        if ep % 10 == 0 or ep == 1:
            print(f"  epoch {ep:3d}  loss={tl/max(1,tn):.4f}  val_acc={acc:.3f}  best={best_acc:.3f}")

    print(f"\n训练完成，耗时 {time.time()-t0:.1f}s   最佳验证准确率 {best_acc:.3f}")

    net.load_state_dict(best_state)
    ckpt = {
        "model_state": net.state_dict(),
        "classes": CLASSES,
        "img_size": IMG,
        "arch": "TLColorNet(conv5-16/conv5-32/conv3-64/fc128/fc64/fc3)",
        "val_acc": best_acc,
        "trained_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    ck_path = os.path.join(OUT_DIR, "tl_color_cnn.pt")
    torch.save(ckpt, ck_path)
    print(f"权重已保存: {ck_path}  ({os.path.getsize(ck_path)/1024:.0f} KB)")

    with open(os.path.join(OUT_DIR, "history.json"), "w", encoding="utf-8") as f:
        json.dump(hist, f, ensure_ascii=False, indent=1)

    # 验证集逐张结果（便于人工复核）
    net.eval()
    lines = ["file,true,pred,conf,ok"]
    with torch.no_grad():
        for p, y in va:
            im = preprocess(p)
            if im is None:
                continue
            x = to_tensor(im).unsqueeze(0).to(DEV)
            prob = torch.softmax(net(x), 1)[0]
            pi = int(prob.argmax())
            lines.append(f"{os.path.basename(p)},{CLASSES[y]},{CLASSES[pi]},"
                         f"{float(prob[pi]):.3f},{'1' if pi==y else '0'}")
    with open(os.path.join(OUT_DIR, "val_predictions.csv"), "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines) + "\n")
    print(f"验证集明细: {OUT_DIR}\\val_predictions.csv")


if __name__ == "__main__":
    main()
