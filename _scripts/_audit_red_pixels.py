"""回查：旧视频里的"红色像素"到底是不是红绿灯？

上一会话说"我从未拍到过可判读的红色灯珠，那些红像素可能是背景噪声"。
本脚本逐帧找出旧视频里所有"亮红"块，统计它们的：
  * 屏幕位置分布（如果集中在灯头位置 -> 可能是灯；如果散布 -> 噪声）
  * 是否跨帧稳定（灯会持续亮；噪声是偶发）
  * 出现的时间段（如果能对上红灯相位 -> 可能是灯）
"""
import os
import sys
from collections import Counter, defaultdict

import numpy as np
import cv2

OLD = r"E:\output\_carla_video4\carla_tl_face_28s.mp4"
NEW = r"E:\output\_dual_cam_demo\dual_cam_demo_lossless.mkv"


def red_blobs(img, vmin=150, smin=120, rmin=90):
    b, g, r = [img[:, :, i].astype(np.int16) for i in range(3)]
    m = ((r > g + 30) & (r > b + 30) & (r > rmin) & (np.maximum(np.maximum(b, g), r) > vmin)).astype(np.uint8)
    m = cv2.morphologyEx(m * 255, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    nc, lab, st, ce = cv2.connectedComponentsWithStats(m, 8)
    out = []
    for i in range(1, nc):
        a = int(st[i, cv2.CC_STAT_AREA])
        if a < 8:
            continue
        cx, cy = int(ce[i][0]), int(ce[i][1])
        pb, pg, pr = [int(img[cy, cx, k]) for k in range(3)]
        out.append((a, cx, cy, pb, pg, pr))
    return out


def scan(path, tag, step=4):
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        print("打不开", path)
        return
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w, h = int(cap.get(3)), int(cap.get(4))
    fps = cap.get(cv2.CAP_PROP_FPS) or 20.0
    print("\n" + "=" * 78)
    print("%s  %dx%d  %d 帧  %.1f fps" % (tag, w, h, n, fps))
    print("=" * 78)
    allb = []
    per_frame = {}
    for f in range(0, n, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, f)
        ok, img = cap.read()
        if not ok:
            continue
        bl = red_blobs(img)
        if bl:
            per_frame[f] = bl
            allb.extend([(f,) + x for x in bl])
    cap.release()
    print("抽帧 %d 帧（每 %d 帧一抽），含亮红块的帧 %d 个，共 %d 块"
          % (len(range(0, n, step)), step, len(per_frame), len(allb)))
    if not allb:
        print("  ✗ 整段视频没有亮红块")
        return
    # 位置分布：把画面分 8x8 网格统计
    gw, gh = 8, 8
    grid = Counter()
    for (f, a, cx, cy, b, g, r) in allb:
        grid[(cx // (w // gw), cy // (h // gh))] += 1
    print("\n  亮红块的位置分布（8x8 网格，值=出现次数）:")
    for gy in range(gh):
        row = "   "
        for gx in range(gw):
            row += "%5d" % grid.get((gx, gy), 0)
        print(row)
    # 跨帧稳定性：同一位置附近是否反复出现
    print("\n  出现最频繁的 8 个位置（聚类半径 20px）:")
    clusters = []
    for (f, a, cx, cy, b, g, r) in allb:
        hit = None
        for c in clusters:
            if abs(c["x"] - cx) < 20 and abs(c["y"] - cy) < 20:
                hit = c
                break
        if hit:
            hit["n"] += 1
            hit["frames"].append(f)
            hit["bgr"].append((b, g, r))
        else:
            clusters.append({"x": cx, "y": cy, "n": 1, "frames": [f], "bgr": [(b, g, r)]})
    clusters.sort(key=lambda c: -c["n"])
    for c in clusters[:8]:
        mb, mg, mr = [float(np.mean([p[k] for p in c["bgr"]])) for k in range(3)]
        span = (min(c["frames"]), max(c["frames"]))
        print("    (%4d,%4d) 出现 %-4d 帧  帧区间 %s  BGR均值=(%.0f,%.0f,%.0f)"
              % (c["x"], c["y"], c["n"], span, mb, mg, mr))
    tot = sum(c["n"] for c in clusters)
    print("\n  判定: ", end="")
    if clusters and clusters[0]["n"] >= 5:
        print("存在跨帧稳定出现的红块 @(%d,%d)，出现 %d 次 -> 可能是真实红光源"
              % (clusters[0]["x"], clusters[0]["y"], clusters[0]["n"]))
    else:
        print("红块零散、无跨帧稳定位置 -> 更像背景噪声（红车/红招牌/红砖）")


if __name__ == "__main__":
    scan(OLD, "旧视频 _carla_video4（上一会话）", step=4)
    scan(NEW, "本次录制 dual_cam", step=4)
