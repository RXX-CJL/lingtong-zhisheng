"""一致性检验：真值世界坐标 --正向投影--> 像素，与真值像素比。

这能区分两种故障：
  A) 正向投影命中真值像素  -> 相机参数对，是【逆投影公式】写错了
  B) 正向投影也命不中      -> 相机参数不对（机位/姿态/视场角与实际不符）
                          或 ground_truth 里的像素坐标本身有问题
"""
import csv
import math
import sys

import numpy as np

CSV = r"E:\output\_dual_cam_demo\ground_truth_dual.csv"
CAM_LOC = np.array([-15.720, -63.145, 5.732])
CAM_PITCH, CAM_YAW = -23.445, 179.536
W, H, FOV = 1920, 1080, 90.0


def project(P, loc, pitch, yaw, w=W, h=H, fov=FOV):
    p, y = math.radians(pitch), math.radians(yaw)
    cp, sp, cy, sy = math.cos(p), math.sin(p), math.cos(y), math.sin(y)
    fwd = np.array([cp * cy, cp * sy, -sp])
    right = np.array([-sy, cy, 0.0])
    up = np.array([-sp * cy, -sp * sy, cp])
    d = np.asarray(P, float) - loc
    z = float(d @ fwd)
    if z <= 1e-6:
        return None
    f = w / (2 * math.tan(math.radians(fov) / 2))
    return (w / 2 + f * float(d @ right) / z, h / 2 - f * float(d @ up) / z, z)


def main():
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
    print("可用样本: %d" % len(pts))

    print("\n=== A) 用【真值世界坐标】正向投影，看能否命中【真值像素】 ===")
    print("%-7s %-7s %-24s %-22s %s" % ("t", "tag", "真值世界(x,y,z=0)", "正向投影出的像素", "误差(px)"))
    errs = []
    for (u, v, x, y, tag, t) in pts[::40][:20]:
        pr = project([x, y, 0.0], CAM_LOC, CAM_PITCH, CAM_YAW)
        if pr is None:
            print("%-7.2f %-7s (%8.2f,%8.2f)   投影失败" % (t, tag[:6], x, y))
            continue
        e = math.dist((pr[0], pr[1]), (u, v))
        errs.append(e)
        print("%-7.2f %-7s (%8.2f,%8.2f)   (%7.1f,%7.1f) vs 真值(%7.1f,%7.1f)  %7.1f"
              % (t, tag[:6], x, y, pr[0], pr[1], u, v, e))
    if errs:
        a = np.array(errs)
        print("\n   像素误差: 平均 %.0f  中位 %.0f  最大 %.0f" % (a.mean(), np.median(a), a.max()))
        print("   判定: %s" % ("A) 参数基本对，问题在逆投影公式"
                              if a.mean() < 200 else
                              "B) 正向投影也对不上 -> 相机参数或真值像素有问题"))

    print("\n=== B) 换一组相机参数试探（看是不是机位记错了）===")
    best = None
    for dz in (4.0, 5.0, 5.732, 6.5, 7.0):
        for dp in (-22.0, -23.445, -25.0, -27.0, -30.0):
            for dx in (-19.72, -15.72):
                loc = np.array([dx, -63.145, dz])
                es = []
                for (u, v, x, y, tag, t) in pts[::20][:30]:
                    pr = project([x, y, 0.0], loc, dp, CAM_YAW)
                    if pr:
                        es.append(math.dist((pr[0], pr[1]), (u, v)))
                if len(es) >= 5:
                    m = float(np.mean(es))
                    if best is None or m < best[0]:
                        best = (m, dx, dz, dp, len(es))
    if best:
        print("   最优组合: 平均像素误差 %.0f  (相机 x=%.2f  z=%.2f  pitch=%.1f, %d 个样本)"
              % best)
    return 0


if __name__ == "__main__":
    sys.exit(main())
