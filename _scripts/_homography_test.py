"""单应矩阵方案：像素 <-> 地面世界坐标（支持横向/纵向）。

原理：
  地面 z=0 平面上的点 (X,Y) 与像素 (u,v) 之间是 3x3 单应变换 H：
      [u,v,1]^T ~ H @ [X,Y,1]^T
  反向用它就能把像素换成米制坐标。

  关键：**H 不需要人工标点** —— 只要知道相机高度/俯角/偏航角/视场角，
  就能用已验证的正向投影算出 4 个已知地面点对应的像素，从而解出 H。
  这正好满足"前端输入相机参数即可测速"的需求。

验证：用 ground_truth_dual.csv 的 (u,v) <-> (x,y) 真值对，算反解误差。
"""
import csv
import math
import sys

import cv2
import numpy as np

CSV = r"E:\output\_dual_cam_demo\ground_truth_dual.csv"
W, H, FOV = 1920, 1080, 90.0


def project(P, loc, pitch, yaw, w=W, h=H, fov=FOV):
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


def homography_from_camera(loc, pitch, yaw, w=W, h=H, fov=FOV,
                           span=120.0, lateral=40.0):
    """由相机参数构造「像素 -> 地面米制」的单应矩阵。

    做法：以相机正下方地面点为参考，取地面上 4 个已知点（覆盖前方 span 米、
    左右 lateral 米），正向投影得到它们的像素，再用 cv2.getPerspectiveTransform
    求出「米制 -> 像素」的 H，其逆即「像素 -> 米制」。
    """
    loc = np.asarray(loc, float)
    # 相机朝向的水平单位向量
    yr = math.radians(yaw)
    dir2 = np.array([math.cos(yr), math.sin(yr)])
    perp2 = np.array([-dir2[1], dir2[0]])
    base = loc[:2]

    # 4 个地面点：近前左/近前右/远前右/远前左
    pts_world = []
    for (t, s) in ((5.0, -lateral), (5.0, lateral), (span, lateral), (span, -lateral)):
        pts_world.append(base + dir2 * t + perp2 * s)
    pts_img = []
    for pw in pts_world:
        pr = project([pw[0], pw[1], 0.0], loc, pitch, yaw, w, h, fov)
        if pr is None:
            return None, None
        pts_img.append(pr)
    src = np.array(pts_world, dtype=np.float32)     # 米制
    dst = np.array(pts_img, dtype=np.float32)       # 像素
    Hm = cv2.getPerspectiveTransform(src, dst)      # 米 -> 像素
    Hinv = np.linalg.inv(Hm)                        # 像素 -> 米
    return Hinv, Hm


def pixel_to_world(Hinv, u, v):
    p = Hinv @ np.array([u, v, 1.0])
    if abs(p[2]) < 1e-12:
        return None
    return np.array([p[0] / p[2], p[1] / p[2]])


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
    print("样本: %d" % len(pts))

    # 用参数扫描找最优相机高度（其余参数沿用已确认值）
    print("\n=== 参数扫描：相机高度 z 对反解误差的影响 ===")
    results = []
    for z in (4.6, 4.8, 5.0, 5.2, 5.4, 5.732):
        loc = [-15.720, -63.145, z]
        Hinv, _ = homography_from_camera(loc, -23.445, 179.536)
        if Hinv is None:
            continue
        es = []
        for (u, v, x, y, tag, t) in pts:
            P = pixel_to_world(Hinv, u, v)
            if P is None:
                continue
            es.append(math.dist((P[0], P[1]), (x, y)))
        if es:
            a = np.array(es)
            results.append((a.mean(), z, a))
            print("   z=%.3f m -> 平均误差 %6.2f m  中位 %6.2f m  90分位 %6.2f m"
                  % (z, a.mean(), np.median(a), np.percentile(a, 90)))

    if not results:
        print("全部失败")
        return 1
    best = min(results, key=lambda r: r[0])
    print("\n最优相机高度 z=%.3f m（平均误差 %.2f m）" % (best[1], best[0]))

    loc = [-15.720, -63.145, best[1]]
    Hinv, _ = homography_from_camera(loc, -23.445, 179.536)
    print("\n%-7s %-7s %-20s %-24s %s"
          % ("t", "tag", "像素(u,v)", "真值世界(x,y)", "反解(x,y) / 误差"))
    for (u, v, x, y, tag, t) in pts[::60][:12]:
        P = pixel_to_world(Hinv, u, v)
        if P is None:
            continue
        print("%-7.2f %-7s (%7.1f,%7.1f)  (%8.2f,%8.2f)   (%8.2f,%8.2f)   %6.2f m"
              % (t, tag[:6], u, v, x, y, P[0], P[1], math.dist((P[0], P[1]), (x, y))))

    a = best[2]
    print("\n=== 结论 ===")
    print("   平均 %.2f m / 中位 %.2f m / 90分位 %.2f m"
          % (a.mean(), np.median(a), np.percentile(a, 90)))
    if a.mean() < 2.0:
        print("   -> 单应矩阵方案可用，可接入测速")
    else:
        print("   -> 仍偏大，需进一步排查（可能真值像素含 bbox 中心而非接地点）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
