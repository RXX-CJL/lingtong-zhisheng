"""重训判色器：让它在 **CARLA 渲染** 的红绿灯上也能判对。

背景（本轮查明）：
  * CNN4 用**真实视频**训练（黑/深色灯箱、小灯珠），
    而 CARLA 渲染的灯箱是**青蓝色**、灯珠占比大 -> 分布外，拒识率极高。
    （输入呈现方式扫描：最好的也只有 33%）
  * 颜色本身没问题（读图通道 bug 已修）：红灯相位实测 15000+ 个真红像素。

做法：
  1. 采集 CARLA 三态下的**灯珠裁图**，用**真值**打标签（我们钉死的灯态就是真值）
  2. 在 CNN4 基础上微调（冻结前几层，小学习率），保留真实世界能力
  3. 按 5 折/留出法报准确率，并单独报"红灯召回"（最关键的指标）
"""
import glob
import os
import random
import sys
import time

import numpy as np
import cv2
import torch
import torch.nn as nn
import torch.nn.functional as F

sys.path.insert(0, r"E:\output\1\api")
from _train_tl_classifier import TLColorNet, augment, preprocess, to_tensor  # noqa: E402

SRC = r"E:\output\_retrain_carla2"
OUT = r"E:\output\_tl_color_cls"
os.makedirs(OUT, exist_ok=True)
CLASSES = ["green", "red", "yellow", "none"]
IMG = 64
DEV = "cuda" if torch.cuda.is_available() else "cpu"
SEED = 42
BASE = os.path.join(OUT, "tl_color_cnn4.pt")


def load_crops():
    items = []
    for ci, cls in enumerate(CLASSES):
        for p in glob.glob(os.path.join(SRC, cls, "*.png")):
            items.append((p, ci))
        n = len(glob.glob(os.path.join(SRC, cls, "*.png")))
        print("  %-8s %d 张" % (cls, n))
    return items


def train_on(items_tr, init_state, epochs=60, lr=3e-4, freeze_until=2, seed=SEED):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    net = TLColorNet(len(CLASSES)).to(DEV)
    net.load_state_dict(init_state)
    # 冻结前若干层（保留真实世界的低层特征）
    layers = list(net.children())
    frozen = 0
    for i, mod in enumerate(layers):
        if i < freeze_until:
            for p in mod.parameters():
                p.requires_grad = False
            frozen += 1
    opt = torch.optim.Adam([p for p in net.parameters() if p.requires_grad],
                           lr=lr, weight_decay=1e-4)

    class DS(torch.utils.data.Dataset):
        def __len__(self):
            return len(items_tr)

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
    net.eval()
    return net, frozen


def evaluate(net, items):
    cm = np.zeros((4, 4), dtype=int)
    for p, y in items:
        im = preprocess(p)
        if im is None:
            continue
        x = to_tensor(im).unsqueeze(0).to(DEV)
        with torch.no_grad():
            pi = int(torch.softmax(net(x), 1)[0].argmax())
        cm[y][pi] += 1
    return cm


def baseline_eval(state, items):
    net = TLColorNet(len(CLASSES)).to(DEV)
    net.load_state_dict(state)
    net.eval()
    return evaluate(net, items), net


def main():
    print("CARLA 判色数据集:")
    items = load_crops()
    if not items:
        print("没有数据，先跑采集脚本")
        return 1
    from collections import Counter
    dist = Counter(c for _, c in items)
    print("  合计 %d 张，分布 %s" % (len(items), {CLASSES[k]: v for k, v in sorted(dist.items())}))

    ck = torch.load(BASE, map_location=DEV, weights_only=False)
    base_state = ck["model_state"]

    print("\n【基线】原 CNN4 在 CARLA 数据上的表现:")
    cm0, _ = baseline_eval(base_state, items)
    acc0 = np.trace(cm0) / max(1, cm0.sum())
    print("  准确率 %.3f" % acc0)
    print("         " + "".join("%9s" % c for c in CLASSES))
    for i, c in enumerate(CLASSES):
        print("  %-6s" % c + "".join("%9d" % cm0[i][j] for j in range(4)))
    red_recall0 = cm0[1][1] / max(1, cm0[1].sum())
    print("  红灯召回 = %.3f" % red_recall0)

    # 留出法：每类按 75/25 分
    random.seed(SEED)
    by = {}
    for p, y in items:
        by.setdefault(y, []).append(p)
    tr, va = [], []
    for y, ps in by.items():
        ps = ps[:]; random.shuffle(ps)
        k = max(1, int(len(ps) * 0.75))
        tr += [(p, y) for p in ps[:k]]
        va += [(p, y) for p in ps[k:]]
    print("\n训练集 %d / 验证集 %d" % (len(tr), len(va)))

    best = None
    for ep, lr_, fu in ((60, 3e-4, 2), (80, 1e-4, 1), (100, 3e-4, 0)):
        net, frozen = train_on(tr, base_state, epochs=ep, lr=lr_, freeze_until=fu)
        cmv = evaluate(net, va)
        a = np.trace(cmv) / max(1, cmv.sum())
        rr = cmv[1][1] / max(1, cmv[1].sum())
        print("  epochs=%-4d lr=%-7.0e freeze=%d -> 验证准确率 %.3f  红灯召回 %.3f"
              % (ep, lr_, fu, a, rr))
        if best is None or (rr, a) > (best[0], best[1]):
            best = (rr, a, ep, lr_, fu)

    print("\n最优配置: 红灯召回=%.3f 准确率=%.3f (epochs=%d lr=%.0e freeze=%d)"
          % (best[0], best[1], best[2], best[3], best[4]))

    # 用最优配置在**全量**数据上训练并保存
    net, frozen = train_on(items, base_state, epochs=best[2], lr=best[3],
                           freeze_until=best[4])
    cmf = evaluate(net, items)
    acc = np.trace(cmf) / max(1, cmf.sum())
    print("\n【最终】全量数据表现: 准确率 %.3f" % acc)
    print("         " + "".join("%9s" % c for c in CLASSES))
    for i, c in enumerate(CLASSES):
        print("  %-6s" % c + "".join("%9d" % cmf[i][j] for j in range(4)))
    print("  红灯召回 = %.3f" % (cmf[1][1] / max(1, cmf[1].sum())))

    out = os.path.join(OUT, "tl_color_cnn6_carla.pt")
    torch.save({"model_state": net.state_dict(), "classes": CLASSES, "img_size": IMG,
                "arch": "TLColorNet-4class", "cv_acc": float(best[1]),
                "trained_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "note": "在 CNN4 基础上用 CARLA 渲染的灯珠裁图微调；真值=钉死的灯态"},
               out)
    print("\n新权重: %s (%.0f KB)" % (out, os.path.getsize(out) / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
