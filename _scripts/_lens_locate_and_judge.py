"""自动定位灯珠 + 判色器实测 + 出图（红/绿两态对照）。

不再手填坐标：在信号灯头区域里按"彩色度(饱和)"找最像灯珠的亮块，
把它裁出来 → 喂项目判色器 → 同时把裁图拼成图给人核对。
"""
import os
import sys

import numpy as np
import cv2

sys.path.insert(0, r"E:\output\1\api")
from traffic_light_classifier import (classify_traffic_light, find_glow_region,
                                      classify_with_glow)  # noqa: E402

D = r"E:\output\_lightup2"
OUT = r"E:\output\_lightup2"
# 信号灯头大致的搜索窗（从变体图里目测的大范围）
SEARCH = [(1335, 180, 60, 130),    # (cx, cy, half_w, half_h)
          (1007, 150, 60, 130)]


def find_lens(img, cx, cy, hw, hh):
    """在搜索窗里找"最彩色且较亮"的紧凑块 = 灯珠。返回 (x0,y0,x1,y1,info)"""
    x0, y0 = max(0, cx - hw), max(0, cy - hh)
    x1, y1 = min(img.shape[1], cx + hw), min(img.shape[0], cy + hh)
    roi = img[y0:y1, x0:x1]
    if roi.size == 0:
        return None
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    s = hsv[:, :, 1].astype(np.int16)
    v = hsv[:, :, 2].astype(np.int16)
    # 彩色度评分：饱和 × 亮度
    score = (s.astype(np.float32) * v.astype(np.float32))
    m = ((s > 60) & (v > 90)).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    n, lab, st, ce = cv2.connectedComponentsWithStats(m, 8)
    best = None
    for i in range(1, n):
        a = int(st[i, cv2.CC_STAT_AREA])
        if a < 6:
            continue
        bw, bh = int(st[i, cv2.CC_STAT_WIDTH]), int(st[i, cv2.CC_STAT_HEIGHT])
        if max(bw, bh) / max(1, min(bw, bh)) > 4:
            continue
        mx = float(score[lab == i].mean())
        if best is None or mx > best[0]:
            best = (mx, i, ce[i], st[i])
    if best is None:
        return None
    _, i, c, stt = best
    bx, by = int(c[0]), int(c[1])
    bw, bh = int(stt[cv2.CC_STAT_WIDTH]), int(stt[cv2.CC_STAT_HEIGHT])
    # 裁一个包含灯珠及上下文的框
    pad = max(10, int(max(bw, bh) * 0.9))
    lx0, ly0 = max(0, bx - pad), max(0, by - pad)
    lx1, ly1 = min(roi.shape[1], bx + bw + pad), min(roi.shape[0], by + bh + pad)
    lens = roi[ly0:ly1, lx0:lx1]
    b, g, r = [int(roi[by, bx, k]) for k in range(3)]
    hv = cv2.cvtColor(np.uint8([[[b, g, r]]]), cv2.COLOR_BGR2HSV)[0, 0]
    return {"gx": x0 + bx, "gy": y0 + by, "size": (bw, bh), "bgr": (b, g, r),
            "hue": int(hv[0]) * 2, "sat": int(hv[1]), "crop": lens,
            "rect": (x0 + lx0, y0 + ly0, x0 + lx1, y0 + ly1)}


def main():
    rows = []
    tiles = []
    for state in ("red", "green"):
        p = os.path.join(D, "A_default_%s.png" % state)
        img = cv2.imread(p)
        if img is None:
            print("缺图", p)
            continue
        vis = img.copy()
        print("\n=== A_default %s ===" % state.upper())
        for (cx, cy, hw, hh) in SEARCH:
            L = find_lens(img, cx, cy, hw, hh)
            if L is None:
                print("  窗(%d,%d): 未找到彩色灯珠" % (cx, cy))
                continue
            cnn, conf = classify_traffic_light(L["crop"])
            st2, c2, info = classify_with_glow(L["crop"])
            print("  窗(%d,%d) 灯珠@(%d,%d) %dx%d BGR=%s hue=%d sat=%d"
                  % (cx, cy, L["gx"], L["gy"], L["size"][0], L["size"][1],
                     L["bgr"], L["hue"], L["sat"]))
            print("      CNN4=%-8s %.3f   glow=%-8s (%s)   裁图 %dx%d"
                  % (cnn, conf, st2, info.get("source"),
                     L["crop"].shape[1], L["crop"].shape[0]))
            rows.append((state, cx, cy, L["bgr"], L["hue"], cnn, round(conf, 3), st2))
            # 画到总图上
            x0, y0, x1, y1 = L["rect"]
            cv2.rectangle(vis, (x0, y0), (x1, y1), (0, 255, 255), 2)
            cv2.circle(vis, (L["gx"], L["gy"]), 6, (0, 0, 255), 2)
            z = cv2.resize(L["crop"], (200, 200), interpolation=cv2.INTER_NEAREST)
            lab = "%s %s" % (state.upper(), cnn)
            cv2.putText(z, lab, (3, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                        (0, 0, 255) if state == "red" else (0, 255, 0), 1, cv2.LINE_AA)
            cv2.putText(z, "hue=%d sat=%d" % (L["hue"], L["sat"]), (3, 194),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 255), 1, cv2.LINE_AA)
            tiles.append(z)
        cv2.imwrite(os.path.join(OUT, "located_%s.png" % state), vis)

    if tiles:
        while len(tiles) % 4:
            tiles.append(np.zeros((200, 200, 3), np.uint8))
        sheet = np.vstack([np.hstack(tiles[i:i + 4]) for i in range(0, len(tiles), 4)])
        pth = os.path.join(OUT, "lens_crops_and_verdict.png")
        cv2.imwrite(pth, sheet)
        print("\n★ 灯珠裁图 + 判色结果:", pth)
    print("\n汇总:")
    for r in rows:
        print("   %-6s 灯珠 BGR=%-16s hue=%-4d CNN=%-8s %.3f  glow=%s"
              % (r[0], str(r[3]), r[4], r[5], r[6], r[7]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
