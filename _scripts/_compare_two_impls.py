"""对撞实验：把「之前成功的实现」与「speed_calibration 里的新实现」
放在同一脚本里，用**同一批真值点**比较，让差异自己暴露。

成功实现：_homography_test.py 的 homography_from_camera（世界坐标 + 相机的
          已验证 3D 投影函数）
新实现  ：speed_calibration.ground_plane_homography（局部米制系 + 独立针孔式）
"""
import csv
import math
import sys

import cv2
import numpy as np

sys.path.insert(0, r"E:\output\1\api")
import speed_calibration as SC  # noqa: E402

CSV = r"E:\output\_dual_cam_demo\ground_truth_dual.csv"
W, H, FOV = 1920, 1080, 90.0
LOC = np.array([-15.720, -63.145, 5.0])
PITCH, YAW = -23.445, 179.536


# ---------- 实现 A：之前成功的版本 ----------
def project_verified(P, loc, pitch, yaw, w=W, h=H, fov=FOV):
    p, y = math.radians(pitch), math.radians(yaw)
    cp, sp, cy, sy = math.cos(p), math.sin(p), math.cos(y), math.sin(y)
    fwd = np.array([cp * cy, cp * sy, -sp])
    right = np.array([-sy, cy, 0.0])
    up = np.array([-sp * cy, -sp * sy, cp])
    d = np.asarray(P, float) - np.asarray(loc, float)
    z = float(d @ fwd)
    if z <= 1e-6:
        return None
    f = w / (2 * math.tan(math.radians(fov) / 2))
    return (w / 2 + f * float(d @ right) / z, h / 2 - f * float(d @ up) / z)


def homography_A(loc, pitch, yaw, span=120.0, lateral=40.0):
    loc = np.asarray(loc, float)
    yr = math.radians(yaw)
    dir2 = np.array([math.cos(yr), math.sin(yr)])
    perp2 = np.array([-dir2[1], dir2[0]])
    base = loc[:2]
    pts_world = [base + dir2 * t + perp2 * s
                 for (t, s) in ((5.0, -lateral), (5.0, lateral), (span, lateral), (span, -lateral))]
    pts_img = [project_verified([p[0], p[1], 0.0], loc, pitch, yaw) for p in pts_world]
    if any(p is None for p in pts_img):
        return None, None
    Hm = cv2.getPerspectiveTransform(np.array(pts_world, np.float32),
                                     np.array(pts_img, np.float32))
    return np.linalg.inv(Hm), Hm


def px2world_A(Hinv, u, v):
    q = Hinv @ np.array([u, v, 1.0])
    return (q[0] / q[2], q[1] / q[2]) if abs(q[2]) > 1e-12 else None


# ---------- 实现 B：speed_calibration 新版本 ----------
def world_to_local(x, y):
    yr = math.radians(YAW)
    d = np.array([x - LOC[0], y - LOC[1]])
    return (float(d @ np.array([math.cos(yr), math.sin(yr)])),
            float(d @ np.array([-math.sin(yr), math.cos(yr)])))


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

    hA = homography_A(LOC, PITCH, YAW)
    hgB = SC.ground_plane_homography(LOC[2], PITCH, FOV, W, H, yaw_deg=YAW)
    print("实现A 矩阵构造:", "成功" if hA[0] is not None else "失败")
    print("实现B 矩阵构造:", "成功" if hgB else "失败")
    if hgB:
        print("   B:", hgB["note"])

    print("\n%-7s %-7s %-20s %-24s %-24s %s"
          % ("t", "tag", "像素(u,v)", "真值世界(x,y)", "A反解(世界)", "A误差"))
    eA = []
    for (u, v, x, y, tag, t) in pts[::80][:8]:
        P = px2world_A(hA[0], u, v) if hA[0] is not None else None
        if P is None:
            continue
        e = math.dist(P, (x, y))
        eA.append(e)
        print("%-7.2f %-7s (%7.1f,%7.1f)  (%8.2f,%8.2f)   (%8.2f,%8.2f)   %6.2f m"
              % (t, tag[:6], u, v, x, y, P[0], P[1], e))
    if eA:
        a = np.array(eA)
        print("   A 平均误差 %.2f m" % a.mean())

    print("\n%-7s %-7s %-20s %-24s %-24s %s"
          % ("t", "tag", "像素(u,v)", "真值(局部X,Y)", "B反解(局部X,Y)", "B误差"))
    eB = []
    if hgB:
        for (u, v, x, y, tag, t) in pts[::80][:8]:
            P = SC.pixel_to_ground_m(hgB["Hinv"], u, v)
            if P is None:
                continue
            Xt, Yt = world_to_local(x, y)
            e = math.dist(P, (Xt, Yt))
            eB.append(e)
            print("%-7.2f %-7s (%7.1f,%7.1f)  (%8.2f,%8.2f)     (%8.2f,%8.2f)     %6.2f m"
                  % (t, tag[:6], u, v, Xt, Yt, P[0], P[1], e))
    if eB:
        a = np.array(eB)
        print("   B 平均误差 %.2f m" % a.mean())

    print("\n=== 关键对照：把 A 的结果也转到局部系，看两者是否一致 ===")
    if hA[0] is not None and hgB:
        for (u, v, x, y, tag, t) in pts[::150][:4]:
            PA = px2world_A(hA[0], u, v)
            PB = SC.pixel_to_ground_m(hgB["Hinv"], u, v)
            if PA is None or PB is None:
                continue
            XA, YA = world_to_local(PA[0], PA[1])
            print("   t=%-6.2f 像素(%6.1f,%6.1f)  A->局部(%8.2f,%8.2f)  B->局部(%8.2f,%8.2f)"
                  % (t, u, v, XA, YA, PB[0], PB[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
