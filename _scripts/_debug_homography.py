"""逐步定位：正向投影对不对？单应矩阵构造对不对？

用 ground_truth 的一个已知点做端到端检验：
  世界点 -> (局部系 X,Y) -> 正向投影应命中真值像素
  若正向对，再看单应矩阵的正/反向是否自洽。
"""
import csv
import math
import sys

import numpy as np

sys.path.insert(0, r"E:\output\1\api")
import speed_calibration as SC  # noqa: E402

CSV = r"E:\output\_dual_cam_demo\ground_truth_dual.csv"
CAM = np.array([-15.720, -63.145, 5.0])
YAW = 179.536
PITCH = -23.445
W, H, FOV = 1920, 1080, 90.0


def world_to_local(x, y):
    yr = math.radians(YAW)
    d = np.array([x - CAM[0], y - CAM[1]])
    fwd2 = np.array([math.cos(yr), math.sin(yr)])
    right2 = np.array([-math.sin(yr), math.cos(yr)])
    return float(d @ fwd2), float(d @ right2)


def proj_ref(X, Y):
    """按 _verify_homography_func 里那份「已验证」的针孔模型正向投影"""
    f = W / (2 * math.tan(math.radians(FOV) / 2))
    P = np.array([X, Y, -CAM[2]])
    # 验证用简化基（与早期通过的 _homography_test.py 等价：相机在原点上方、朝向 +X 下方 pitch）
    p = math.radians(PITCH)
    cp, sp = math.cos(p), math.sin(p)
    fwd = np.array([cp, 0.0, sp])
    up = np.array([-sp, 0.0, cp])
    right = np.array([0.0, 1.0, 0.0])
    z = float(P @ fwd)
    if z <= 1e-6:
        return None
    return (W / 2 + f * float(P @ right) / z,
            H / 2 - f * float(P @ up) / z)


def main():
    rows = list(csv.DictReader(open(CSV, encoding="utf-8")))
    print("=== 1) 先用「参照模型」正向投影 5 个真值点，确认模型本身对 ===")
    print("%-7s %-7s %-22s %-24s %s"
          % ("t", "tag", "真值(局部X,Y)", "参照模型投影", "真值像素"))
    n = 0
    for r in rows:
        if not r.get("cam1_u") or r.get("cam1_in") != "1":
            continue
        try:
            u, v = float(r["cam1_u"]), float(r["cam1_v"])
            x, y = float(r["x"]), float(r["y"])
            t = float(r["t_sec"])
        except ValueError:
            continue
        X, Y = world_to_local(x, y)
        pr = proj_ref(X, Y)
        if pr:
            e = math.dist(pr, (u, v))
            print("%-7.2f %-7s (%8.2f,%8.2f)   (%7.1f,%7.1f)   (%7.1f,%7.1f)  误差 %6.1f px"
                  % (t, r["tag"][:6], X, Y, pr[0], pr[1], u, v, e))
        n += 1
        if n >= 6:
            break

    print("\n=== 2) 看 speed_calibration 内部 4 个构造点投影到哪里 ===")
    f = W / (2 * math.tan(math.radians(FOV) / 2))
    p = math.radians(PITCH)
    cp, sp = math.cos(p), math.sin(p)
    fwd = np.array([cp, 0.0, sp])
    up = np.array([-sp, 0.0, cp])
    right = np.array([0.0, 1.0, 0.0])
    down = np.array([0.0, 0.0, -1.0])
    print("   fwd=%s up=%s down=%s" % (fwd.round(3), up.round(3), down.round(3)))
    for (X, Y) in [(5.0, -40.0), (5.0, 40.0), (140.0, 40.0), (140.0, -40.0)]:
        P = X * fwd + Y * right + CAM[2] * down
        z = float(P @ fwd)
        if z <= 1e-6:
            print("   (%6.1f,%6.1f) -> 相机后方 z=%.2f" % (X, Y, z))
            continue
        u = W / 2 + f * float(P @ right) / z
        v = H / 2 - f * float(P @ up) / z
        print("   (%6.1f,%6.1f) -> 像素 (%8.1f,%8.1f)  z=%.2f" % (X, Y, u, v, z))

    print("\n=== 3) 单应矩阵自洽性：像素->米->像素 应回到原点 ===")
    hg = SC.ground_plane_homography(CAM[2], PITCH, FOV, W, H, yaw_deg=YAW)
    if hg:
        Hinv, Hm = hg["Hinv"], hg["Hm"]
        for (uu, vv) in [(960, 540), (960, 900), (1200, 700), (700, 400)]:
            q = Hinv @ np.array([uu, vv, 1.0])
            if abs(q[2]) < 1e-12:
                continue
            XY = q[:2] / q[2]
            back = Hm @ np.array([XY[0], XY[1], 1.0])
            bu, bv = back[:2] / back[2]
            print("   像素(%4d,%4d) -> 米(%8.2f,%8.2f) -> 像素(%8.1f,%8.1f)  往返误差 %.3f px"
                  % (uu, vv, XY[0], XY[1], bu, bv, math.dist((uu, vv), (bu, bv))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
