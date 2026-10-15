"""诊断：ground_plane_homography 为何构造失败（逐步打印）。"""
import math
import sys

import numpy as np

sys.path.insert(0, r"E:\output\1\api")

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
print("fwd=%s" % fwd.round(4))
print("right=%s" % right.round(4))
print("up=%s" % up.round(4))
print("f=%.1f  loc=%s" % (f, loc.round(3)))


def project(P):
    d = np.asarray(P, float) - loc
    z = float(d @ fwd)
    if z <= 1e-6:
        return None
    return (W / 2 + f * float(d @ right) / z, H / 2 - f * float(d @ up) / z, z)


dir2 = np.array([cy, sy])
perp2 = np.array([-sy, cy])
base = loc[:2]
print("\ndir2(前进方向)=%s  perp2(右)=%s" % (dir2.round(4), perp2.round(4)))

lat, spn = 40.0, 120.0
for it in range(6):
    near = max(2.0, spn * 0.05)
    print("\n--- 迭代%d: near=%.1f span=%.1f lat=%.1f ---" % (it, near, spn, lat))
    ok_all = True
    for (t, s) in ((near, -lat), (near, lat), (spn, lat), (spn, -lat)):
        pw = base + dir2 * t + perp2 * s
        pr = project([pw[0], pw[1], 0.0])
        if pr is None:
            print("   (t=%.1f,s=%+.1f) -> 投影失败（相机后方）" % (t, s))
            ok_all = False
            continue
        u, v, z = pr
        inside = (-W * 1.5 <= u <= W * 1.5) and (-H * 1.5 <= v <= H * 1.5)
        print("   (t=%6.1f,s=%+6.1f) -> 像素(%9.1f,%9.1f) z=%7.2f  %s"
              % (t, s, u, v, z, "OK" if inside else "超出范围"))
        if not inside:
            ok_all = False
    if ok_all:
        print("   -> 本轮全部合格")
        break
    lat *= 0.7
    spn *= 0.85
    if lat < 0.5 or spn < 8.0:
        print("   -> 收缩到底仍不合格")
        break
return_code = 0
sys.exit(return_code)
