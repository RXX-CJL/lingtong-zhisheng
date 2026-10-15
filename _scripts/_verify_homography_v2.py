"""验证修正后的 ground_plane_homography（已改为复用已验证的 3D 投影）。"""
import csv
import math
import sys

import numpy as np

sys.path.insert(0, r"E:\output\1\api")
import speed_calibration as SC  # noqa: E402

CSV = r"E:\output\_dual_cam_demo\ground_truth_dual.csv"
CAM_X, CAM_Y, CAM_H = -15.720, -63.145, 5.0
PITCH, YAW = -23.445, 179.536
W, H, FOV = 1920, 1080, 90.0


def world_to_local(x, y):
    yr = math.radians(YAW)
    dx, dy = x - CAM_X, y - CAM_Y
    return (dx * math.cos(yr) + dy * math.sin(yr),
            dx * (-math.sin(yr)) + dy * math.cos(yr))


def main():
    hg = SC.ground_plane_homography(CAM_H, PITCH, FOV, W, H, yaw_deg=YAW,
                                    cam_world_x=CAM_X, cam_world_y=CAM_Y)
    if not hg:
        print("构造失败")
        return 1
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

    print("%-7s %-7s %-20s %-24s %-24s %s"
          % ("t", "tag", "像素(u,v)", "真值(局部x,y)", "反解(局部x,y)", "误差"))
    errs = []
    for (u, v, x, y, tag, t) in pts[::60][:14]:
        P = SC.pixel_to_ground_m(hg["Hinv"], u, v)
        if P is None:
            print("%-7.2f %-7s (%7.1f,%7.1f)  反解失败" % (t, tag[:6], u, v))
            continue
        Xt, Yt = world_to_local(x, y)
        e = math.dist(P, (Xt, Yt))
        errs.append(e)
        print("%-7.2f %-7s (%7.1f,%7.1f)  (%8.2f,%8.2f)     (%8.2f,%8.2f)     %6.2f m"
              % (t, tag[:6], u, v, Xt, Yt, P[0], P[1], e))

    if errs:
        a = np.array(errs)
        print("\n=== 误差统计（共 %d） ===" % len(errs))
        print("   平均 %.2f m  中位 %.2f m  90分位 %.2f m  最大 %.2f m"
              % (a.mean(), np.median(a), np.percentile(a, 90), a.max()))
        print("   -> %s" % ("✅ 通过（目标 <2m）" if a.mean() < 2.0 else "❌ 未通过"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
