"""新录视频的颜色验证：红灯到底是不是红的？

对红灯相位内的若干帧，扫描"亮且红"的像素，并与"亮且绿"对照。
判据（对比修复前同一脚本的结论）：
  * 修复前：红态帧"亮红像素≈1"、"亮蓝像素 1266"、最亮 200 像素 BGR=(255,168,91) 蓝主导
  * 修复后：应出现明亮的**红**像素（R 主导），且不再是蓝主导
同时把灯珠区域裁图存盘，便于人工核对。
"""
import os
import sys

import numpy as np
import cv2

VID = r"E:\output\_dual_cam_demo\dual_cam_demo_lossless.mkv"
OUT = r"E:\output\_newvideo_check"
os.makedirs(OUT, exist_ok=True)


def scan(img, tag):
    b, g, r = [img[:, :, i].astype(np.int16) for i in range(3)]
    v = np.maximum(np.maximum(b, g), r)
    red = (r > g + 40) & (r > b + 40) & (r > 120)
    grn = (g > r + 40) & (g > b + 40) & (g > 120)
    blu = (b > r + 40) & (b > g + 40) & (b > 120)
    sel = img.reshape(-1, 3)[np.argsort(v.flatten())[-200:]]
    return {"tag": tag, "red": int(red.sum()), "green": int(grn.sum()),
            "blue": int(blu.sum()),
            "top200": tuple(round(float(x), 0) for x in sel.mean(axis=0)),
            "mean": tuple(round(float(img[:, :, i].mean()), 1) for i in range(3))}


def main():
    cap = cv2.VideoCapture(VID)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print("视频 %dx%d  %d 帧" % (cap.get(3), cap.get(4), n))
    print("真值相位: 帧 0-299=Red(15s)  300-399=Green  400-499=Yellow  500+=Red\n")

    rows = []
    tiles = []
    for f in (0, 60, 150, 200, 290, 350, 420, 510):
        cap.set(cv2.CAP_PROP_POS_FRAMES, f)
        ok, img = cap.read()
        if not ok:
            continue
        truth = "Red" if f < 300 or f >= 500 else ("Green" if f < 400 else "Yellow")
        st = scan(img, f)
        rows.append((f, truth, st))
        print("帧 %-4d 真值=%-6s 亮红=%-6d 亮绿=%-6d 亮蓝=%-6d 最亮200均值BGR=%s"
              % (f, truth, st["red"], st["green"], st["blue"], st["top200"]))
        # 红灯相：把最红的块裁出来看
        if truth == "Red":
            b, g, r = [img[:, :, i].astype(np.int16) for i in range(3)]
            m = ((r > g + 40) & (r > b + 40) & (r > 120)).astype(np.uint8) * 255
            m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
            nc, lab, s_, ce = cv2.connectedComponentsWithStats(m, 8)
            blobs = sorted([(int(s_[i, cv2.CC_STAT_AREA]), int(ce[i][0]), int(ce[i][1]))
                            for i in range(1, nc)], reverse=True)[:3]
            for ai, (a_, cx, cy) in enumerate(blobs):
                hw = 22
                c = img[max(0, cy - hw):cy + hw, max(0, cx - hw):cx + hw]
                if c.size == 0:
                    continue
                z = cv2.resize(c, (180, 180), interpolation=cv2.INTER_NEAREST)
                pb, pg, pr = [int(img[cy, cx, k]) for k in range(3)]
                cv2.putText(z, "f%d a=%d" % (f, a_), (3, 15), cv2.FONT_HERSHEY_SIMPLEX,
                            0.45, (0, 255, 255), 1, cv2.LINE_AA)
                cv2.putText(z, "BGR(%d,%d,%d)" % (pb, pg, pr), (3, 172),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)
                tiles.append(z)
    cap.release()

    print("\n" + "=" * 76)
    print("★ 结论对照")
    print("=" * 76)
    redf = [r for r in rows if r[1] == "Red"]
    grnf = [r for r in rows if r[1] == "Green"]
    if redf:
        rr = max(x[2]["red"] for x in redf)
        print("红灯相位内 最多亮红像素 = %d" % rr)
        print("  （修复前同一脚本测到的是 1 —— 基本为零）")
        tb = redf[0][2]["top200"]
        dom = "R 主导 -> 红" if tb[2] > tb[0] and tb[2] > tb[1] else (
            "B 主导 -> 偏蓝（未修好）" if tb[0] > tb[2] else "G 主导")
        print("  红灯相位 最亮200像素均值 BGR=%s  -> %s" % (tb, dom))
    if grnf:
        print("绿灯相位内 亮绿像素 = %d" % max(x[2]["green"] for x in grnf))

    if tiles:
        while len(tiles) % 4:
            tiles.append(np.zeros((180, 180, 3), np.uint8))
        sheet = np.vstack([np.hstack(tiles[i:i + 4]) for i in range(0, len(tiles), 4)])
        p = os.path.join(OUT, "red_blobs_new_video.png")
        cv2.imwrite(p, sheet)
        print("\n红灯块裁图: %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
