"""发光区定位 v2：**种子 + 生长**。在 CARLA 真值裁图上调参，
判据 = 定位中心与真实灯珠中心（最亮点）误差 < 灯珠半径。

真值：E:\\output\\_tl_carla3（红/黄/绿 × 12/20/30m × 4 种裁切，状态已回读校验）
"""
import glob
import math
import os
import re
import sys

import cv2
import numpy as np

SRC = r"E:\output\_tl_carla3"
OUT = r"E:\output\_tl_glow_eval"


def find_glow_v2(img, seed_pct=99.0, grow_ratio=0.78, min_area=4, use_local=True):
    """种子=ROI 内亮度峰值邻域；在其周围生长出"亮度 >= grow_ratio*峰值"的连通域。"""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    h, w = g.shape
    if h < 4 or w < 4:
        return None
    # 种子：峰值邻域（3x3 均值）最大处，降低单像素噪声
    seed_map = cv2.blur(g, (3, 3))
    if use_local:
        # 排除大范围同亮背景：要求高于本 ROI 的中位数
        med = float(np.median(g))
        if float(seed_map.max()) - med < 12:
            return None
    py, px = np.unravel_index(np.argmax(seed_map), g.shape)
    peak = float(seed_map[py, px])
    if peak < 60:
        return None
    thr = max(30.0, peak * grow_ratio)
    # 从种子做有界生长（限制在峰值附近，避免长到别的灯上）
    m = (g >= thr).astype(np.uint8)
    n, lab = cv2.connectedComponents(m, 8)
    sid = lab[py, px]
    if sid == 0:
        return None
    sel = (lab == sid)
    area = int(sel.sum())
    if area < min_area:
        # 放宽一次
        for r in (0.65, 0.5):
            m = (g >= peak * r).astype(np.uint8)
            n, lab = cv2.connectedComponents(m, 8)
            sid = lab[py, px]
            if sid == 0:
                continue
            sel = (lab == sid)
            area = int(sel.sum())
            if area >= min_area:
                break
        else:
            return None
    ys, xs = np.nonzero(sel)
    # 形态学合理性：包围盒不能过扁或过长
    bw = int(xs.max() - xs.min() + 1)
    bh = int(ys.max() - ys.min() + 1)
    if bw <= 0 or bh <= 0:
        return None
    ar = max(bw, bh) / max(1, min(bw, bh))
    if ar > 4.0 or bw > 0.9 * w and bh > 0.9 * h:
        return None
    cx, cy = float(xs.mean()), float(ys.mean())
    return {"cx": cx, "cy": cy, "w": bw, "h": bh, "area": area,
            "peak": peak, "thr": thr, "mask": sel, "seed": (int(px), int(py))}


def main():
    pat = re.compile(r"^(red|green|yellow)_(\d+)m_(\d+)x(\d+)\.png$")
    items = []
    for f in sorted(glob.glob(os.path.join(SRC, "*.png"))):
        m = pat.match(os.path.basename(f))
        if not m:
            continue
        truth, dist, cw, ch = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
        if dist == 45:
            continue
        img = cv2.imread(f)
        if img is None or img.size == 0:
            continue
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
        py, px = np.unravel_index(np.argmax(cv2.blur(g, (3, 3))), g.shape)
        items.append({"f": f, "img": img, "truth": truth, "dist": dist,
                      "size": (cw, ch), "peak_xy": (int(px), int(py)), "peak": float(g[py, px])})
    print("样本数 %d（红/黄/绿 × 12/20/30m × 4 裁切）\n" % len(items))

    print("%-10s %-10s %-9s %-9s %s" % ("grow", "min_area", "命中率", "平均偏差", "最大偏差"))
    best = None
    for grow in (0.92, 0.85, 0.78, 0.70, 0.60):
        for ma in (4, 8):
            ok = 0
            devs = []
            for it in items:
                gl = find_glow_v2(it["img"], grow_ratio=grow, min_area=ma)
                if gl is None:
                    continue
                d = math.hypot(gl["cx"] - it["peak_xy"][0], gl["cy"] - it["peak_xy"][1])
                # 判据：误差 < 灯珠半径（用生长区当半径近似）
                radius = max(gl["w"], gl["h"]) / 2.0
                devs.append(d)
                if d <= max(radius, 3.0):
                    ok += 1
            if devs:
                rate = 100.0 * ok / len(items)
                print("%-10.2f %-10d %-9s %-9.1f %.1f"
                      % (grow, ma, "%d/%d=%.0f%%" % (ok, len(items), rate),
                         sum(devs) / len(devs), max(devs)))
                if best is None or rate > best[0]:
                    best = (rate, grow, ma)

    if best is None:
        print("没有参数组合可用")
        return 1
    rate, grow, ma = best
    print("\n最佳: grow=%.2f min_area=%d  命中率 %.0f%%" % (grow, ma, rate))

    # 用最佳参数出诊断图
    tiles = []
    for it in items:
        if it["size"][0] != 34:
            continue
        gl = find_glow_v2(it["img"], grow_ratio=grow, min_area=ma)
        big = cv2.resize(it["img"], (34 * 4, 130 * 4), interpolation=cv2.INTER_NEAREST)
        cv2.drawMarker(big, (it["peak_xy"][0] * 4, it["peak_xy"][1] * 4), (0, 0, 255),
                       cv2.MARKER_CROSS, 22, 2)
        note = "MISS"
        if gl:
            cv2.drawMarker(big, (int(gl["cx"] * 4), int(gl["cy"] * 4)), (0, 255, 0),
                           cv2.MARKER_TILTED_CROSS, 22, 2)
            d = math.hypot(gl["cx"] - it["peak_xy"][0], gl["cy"] - it["peak_xy"][1])
            note = "d=%.0f" % d
        cv2.putText(big, "%s %dm %s" % (it["truth"][:3], it["dist"], note), (4, 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        tiles.append(big)
    cols = 5
    while len(tiles) % cols:
        tiles.append(np.zeros_like(tiles[0]))
    sheet = np.vstack([np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)])
    p = os.path.join(OUT, "glow_v2_diagnosis.png")
    cv2.imwrite(p, sheet)
    print("诊断图:", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
