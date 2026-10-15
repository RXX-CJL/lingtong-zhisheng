"""逐步复现 ground_plane_homography 的构造过程，找出失败点。"""
import math
import sys

import cv2
import numpy as np

CAM_X, CAM_Y, CAM_H = -15.720, -63.145, 5.0
PITCH, YAW = -23.445, 179.536
W, H, FOV = 1920, 1080, 90.0

loc = np.array([CAM_X, CAM_Y, CAM_H], float)
p, y = math.radians(PITCH), math.radians(YAW)
cp, sp, cy, sy = math.cos(p), math.sin(p), math.cos(y), math.sin(y)
fwd = np.array([cp * cy, cp * sy, -sp])
right = np.array([-sy, cy, 0.0])
up = np.array([-sp * cy, -sp * sy, cp])
f = W / (2 * math.tan(math.radians(FOV) / 2))
dir2 = np.array([cy, sy])
perp2 = np.array([-sy, cy])
print("f=%.1f  dir2=%s  perp2=%s" % (f, dir2.round(4), perp2.round(4)))


def unproject(u, v):
    d = ((u - W / 2.0) / f) * right + ((H / 2.0 - v) / f) * up + fwd
    if abs(d[2]) < 1e-9:
        return None, d, None
    t = (0.0 - loc[2]) / d[2]
    if t <= 0:
        return None, d, t
    return loc + t * d, d, t


px_pts = [(0.0, float(H - 1)), (float(W - 1), float(H - 1)),
          (0.0, float(H) * 0.55), (float(W - 1), float(H) * 0.55)]
local_pts = []
print("\n%-14s %-12s %-10s %-26s %s" % ("像素", "射线dz", "t", "世界点", "局部(x,y)"))
for (u, v) in px_pts:
    P, d, t = unproject(u, v)
    if P is None:
        print("(%7.1f,%7.1f)  dz=%.4f  t=%s  -> 反投影失败" % (u, v, d[2], t))
        continue
    dx, dy = P[0] - loc[0], P[1] - loc[1]
    lx = float(dx * dir2[0] + dy * dir2[1])
    ly = float(dx * perp2[0] + dy * perp2[1])
    local_pts.append((lx, ly))
    print("(%7.1f,%7.1f)  dz=%+.4f  t=%8.2f  (%9.2f,%9.2f,%5.2f)  (%8.2f,%8.2f)"
          % (u, v, d[2], t, P[0], P[1], P[2], lx, ly))

if len(local_pts) == 4:
    print("\n局部点集: %s" % [(round(a, 2), round(b, 2)) for a, b in local_pts])
    print("  是否有 x<=0 的点: %s" % any(a <= 0 for a, b in local_pts))
    print("  去重后个数: %d" % len(set((round(a, 2), round(b, 2)) for a, b in local_pts)))
    Hm = cv2.getPerspectiveTransform(np.array(local_pts, np.float32),
                                     np.array(px_pts, np.float32))
    print("  Hm det=%.6g" % float(np.linalg.det(Hm)))
    Hinv = np.linalg.inv(Hm)
    # 往返自检
    rng = np.random.RandomState(0)
    worst = 0.0
    for _ in range(20):
        uu = float(rng.uniform(0, W)); vv = float(rng.uniform(H * 0.5, H))
        q = Hinv @ np.array([uu, vv, 1.0])
        XY = q[:2] / q[2]
        bk = Hm @ np.array([XY[0], XY[1], 1.0])
        e = math.dist((uu, vv), (bk[0] / bk[2], bk[1] / bk[2]))
        worst = max(worst, e)
    print("  往返自检最大误差: %.6f px" % worst)
    # 解析 vs 单应
    devs = []
    for (uu, vv) in ((W / 2, H * 0.8), (W * 0.3, H * 0.9), (W * 0.7, H * 0.7)):
        P, d, t = unproject(uu, vv)
        if P is None:
            continue
        dx, dy = P[0] - loc[0], P[1] - loc[1]
        ref = (float(dx * dir2[0] + dy * dir2[1]), float(dx * perp2[0] + dy * perp2[1]))
        q = Hinv @ np.array([uu, vv, 1.0])
        got = (q[0] / q[2], q[1] / q[2])
        devs.append(math.dist(ref, got))
        print("   像素(%7.1f,%7.1f) 解析(%.2f,%.2f) 单应(%.2f,%.2f) 差 %.3f"
              % (uu, vv, ref[0], ref[1], got[0], got[1], math.dist(ref, got)))
    print("  解析vs单应 最大差: %.3f m" % (max(devs) if devs else -1))
