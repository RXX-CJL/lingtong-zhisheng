"""确认 CNN4 的最优输入尺度，并检查"扩边 25%"为何有害。

关键假设：CNN4 原本就是按"YOLO 框原样"训练的，部署时加的 25% 扩边
把背景像素带进来，导致 1 例假阳性 + 少数漏判。
"""
import glob
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, r"E:\output\1\api")
import traffic_light_classifier as tlc  # noqa: E402
ROOT = r"E:\output\_tl_dataset"


def expand(img, frac):
    h, w = img.shape[:2]
    py, px = int(h * frac), int(w * frac)
    if py == 0 and px == 0:
        return img
    return cv2.copyMakeBorder(img, py, py, px, px, cv2.BORDER_REPLICATE)


def shrink(img, frac):
    """裁掉四周 frac 比例（模拟"框比物体大"）。"""
    h, w = img.shape[:2]
    py, px = int(h * frac), int(w * frac)
    if h - 2 * py < 8 or w - 2 * px < 8:
        return img
    return img[py:h - py, px:w - px]


def main():
    recs = []
    for cls in ("red", "green", "yellow", "none"):
        for f in sorted(glob.glob(os.path.join(ROOT, cls, "*.png"))):
            img = cv2.imread(f, cv2.IMREAD_COLOR)
            if img is None or img.size == 0:
                continue
            recs.append({"truth": cls, "img": img})
    pos = [r for r in recs if r["truth"] != "none"]
    neg = [r for r in recs if r["truth"] == "none"]

    print("%-22s %-15s %-15s %-6s %s" % ("输入处理", "判色", "拒识", "FP", "说明"))
    variants = [
        ("原样（不处理）", lambda im: im, "★推荐"),
        ("再扩边 10%", lambda im: expand(im, 0.10), ""),
        ("再扩边 25%（当前部署）", lambda im: expand(im, 0.25), "← 生产代码用的"),
        ("再扩边 40%", lambda im: expand(im, 0.40), ""),
        ("内裁 10%", lambda im: shrink(im, 0.10), ""),
        ("内裁 20%", lambda im: shrink(im, 0.20), ""),
    ]
    for label, fn, note in variants:
        ok = rej = fp = 0
        for r in pos:
            st, _ = tlc.classify_traffic_light(fn(r["img"]))
            if st == r["truth"]:
                ok += 1
        for r in neg:
            st, _ = tlc.classify_traffic_light(fn(r["img"]))
            if st in ("none", "unknown"):
                rej += 1
            else:
                fp += 1
        print("%-22s %-15s %-15s %-6d %s"
              % (label, "%d/%d=%.0f%%" % (ok, len(pos), 100.0 * ok / len(pos)),
                 "%d/%d=%.0f%%" % (rej, len(neg), 100.0 * rej / len(neg)), fp, note))

    # 找出"原样对、扩边错"的那些样本，看长什么样
    print("\n原样判对、扩边 25% 判错的样本:")
    bad = []
    for r in recs:
        a, _ = tlc.classify_traffic_light(r["img"])
        b, _ = tlc.classify_traffic_light(expand(r["img"], 0.25))
        if a == r["truth"] and b != r["truth"]:
            bad.append((r, a, b))
    print("   共 %d 例" % len(bad))
    for r, a, b in bad[:10]:
        h, w = r["img"].shape[:2]
        print("      truth=%-7s 原样=%-8s 扩边=%-8s  尺寸=%dx%d" % (r["truth"], a, b, w, h))
    if bad:
        tiles = []
        for r, a, b in bad[:8]:
            im = r["img"]
            h, w = im.shape[:2]
            sc = min(200.0 / w, 200.0 / h, 4.0)
            t = cv2.resize(im, (max(1, int(w * sc)), max(1, int(h * sc))), interpolation=cv2.INTER_NEAREST)
            c = np.zeros((230, 210, 3), np.uint8)
            y0 = (200 - t.shape[0]) // 2
            x0 = (210 - t.shape[1]) // 2
            c[y0:y0 + t.shape[0], x0:x0 + t.shape[1]] = t
            cv2.putText(c, "T:%s A:%s" % (r["truth"][:3], a[:3]), (2, 215),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 0), 1, cv2.LINE_AA)
            cv2.putText(c, "EXP:%s" % b[:3], (2, 227), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 255), 1, cv2.LINE_AA)
            tiles.append(c)
        while len(tiles) % 4:
            tiles.append(np.zeros_like(tiles[0]))
        p = r"E:\output\_tl_glow_eval\expand_hurts_cases.png"
        cv2.imwrite(p, np.vstack([np.hstack(tiles[i:i + 4]) for i in range(0, len(tiles), 4)]))
        print("   证据图:", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
