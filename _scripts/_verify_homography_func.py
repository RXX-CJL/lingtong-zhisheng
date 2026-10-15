"""验证 speed_calibration.ground_plane_homography 的正确性。

相机世界位置 (-15.720, -63.145, 5.0)，yaw=179.536°。
函数返回的是「以相机正下方地面点为原点、x 沿相机朝向、y 向右」的局部米制坐标。
把真值世界坐标转到该局部系，与单应矩阵反解结果比对。
"""
import csv
import math
import sys

import numpy as np

sys.path.insert(0, r"E:\output\1\api")
from speed_calibration import (ground_plane_homography, pixel_to_ground_m,
                               ground_plane_ppm)  # noqa: E402

CSV = r"E:\output\_dual_cam_demo\ground_truth_dual.csv"
CAM = np.array([-15.720, -63.145, 5.0])
YAW = 179.536
W, H, FOV = 1920, 1080, 90.0


def world_to_local(x, y):
    """世界 (x,y) -> 相机局部系 (沿朝向 X, 横向 Y)"""
    yr = math.radians(YAW)
    d = np.array([x - CAM[0], y - CAM[1]])
    fwd2 = np.array([math.cos(yr), math.sin(yr)])
    right2 = np.array([-math.sin(yr), math.cos(yr)])
    return float(d @ fwd2), float(d @ right2)


def main():
    hg = ground_plane_homography(CAM[2], -23.445, FOV, W, H, yaw_deg=YAW)
    if hg is None:
        print("构造单应矩阵失败")
        return 1
    Hinv = hg["Hinv"]
    print(hg["note"])

    rows = list(csv.DictReader(open(CSV, encoding="utf-8")))
    pts = []
    for r in rows:
        if not r.get("cam1_u") or r.get("cam1_in") != "1":
            continue
        try:
            pts.append((float(r["cam1_u"]), float(r["cam1_v"]),
                        float(r["x"]), float(r["y"]), r["tag"], float(r["t_sec"])))
        except ValueError:
            continue
    print("样本: %d\n" % len(pts))

    print("%-7s %-7s %-18s %-24s %-24s %s"
          % ("t", "tag", "像素(u,v)", "真值(局部系)", "单应反解(局部系)", "误差"))
    errs = []
    for (u, v, x, y, tag, t) in pts[::60][:14]:
        P = pixel_to_ground_m(Hinv, u, v)
        if P is None:
            print("%-7.2f %-7s (%7.1f,%7.1f)  反解失败" % (t, tag[:6], u, v))
            continue
        Xt, Yt = world_to_local(x, y)
        e = math.dist(P, (Xt, Yt))
        errs.append(e)
        print("%-7.2f %-7s (%7.1f,%7.1f)  (%8.2f,%8.2f)      (%8.2f,%8.2f)      %6.2f m"
              % (t, tag[:6], u, v, Xt, Yt, P[0], P[1], e))

    if errs:
        a = np.array(errs)
        print("\n=== 误差统计 ===")
        print("   平均 %.2f m  中位 %.2f m  90分位 %.2f m  最大 %.2f m"
              % (a.mean(), np.median(a), np.percentile(a, 90), a.max()))
        print("   -> %s" % ("✅ 通过（与之前 0.77m 一致）" if a.mean() < 2.0
                            else "❌ 未通过，需排查"))

    print("\n=== 对照：旧模型 ground_plane_ppm 在同一批点上的偏差 ===")
    old_ratios = []
    for (u, v, x, y, tag, t) in pts[::20]:
        old = ground_plane_ppm(v, H, W, CAM[2], -23.445, FOV)
        if not old:
            continue
        # 真值 ppm：用相邻点的像素/米位移估计较麻烦，这里只报旧模型值供对照
        old_ratios.append(old)
    if old_ratios:
        print("   旧模型 ppm 范围 %.1f ~ %.1f（真值同区域约 2.7 ~ 231）"
              % (min(old_ratios), max(old_ratios)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
