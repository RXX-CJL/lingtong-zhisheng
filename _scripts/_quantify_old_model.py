"""量化 ground_plane_ppm 与真值的偏差（决定是修它还是换单应矩阵）。"""
import csv
import math
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, r"E:\output\1\api")
from speed_calibration import ground_plane_ppm  # noqa: E402

CSV = r"E:\output\_dual_cam_demo\ground_truth_dual.csv"
W, H, FOV = 1920, 1080, 90.0
# 实测最优相机高度
CAM_H = 5.0
CAM_PITCH = -23.445


def main():
    rows = list(csv.DictReader(open(CSV, encoding="utf-8")))
    # 按 track 收轨迹
    traj = defaultdict(list)
    for r in rows:
        if not r.get("cam1_u") or r.get("cam1_in") != "1":
            continue
        try:
            traj[r["tag"]].append((float(r["t_sec"]), float(r["cam1_u"]),
                                   float(r["cam1_v"]), float(r["x"]), float(r["y"])))
        except ValueError:
            continue
    print("轨迹条数: %s" % {k: len(v) for k, v in traj.items()})

    print("\n=== 真值像素比例（相邻帧: 像素位移 / 米制位移）vs 两模型给出值 ===")
    print("%-9s %-9s %-8s %-8s %-12s %-12s %s"
          % ("tag", "t", "像素Δ", "米Δ", "真值ppm", "旧模型ppm", "比值(旧/真)"))
    ratios = []
    for tag, pts in traj.items():
        pts.sort()
        for i in range(1, len(pts), 8):
            (t0, u0, v0, x0, y0) = pts[i - 1]
            (t1, u1, v1, x1, y1) = pts[i]
            dpix = math.dist((u0, v0), (u1, v1))
            dmet = math.dist((x0, y0), (x1, y1))
            if dmet < 1e-6:
                continue
            true_ppm = dpix / dmet
            old = ground_plane_ppm(v1, H, W, CAM_H, CAM_PITCH, FOV)
            if old:
                ratios.append((tag, t1, dpix, dmet, true_ppm, old, old / true_ppm))
    for r in ratios[:14]:
        print("%-9s %-9.2f %-8.1f %-8.2f %-12.1f %-12.1f %.2f"
              % (r[0][:8], r[1], r[2], r[3], r[4], r[5], r[6]))
    if ratios:
        a = np.array([r[6] for r in ratios])
        print("\n   比值(旧模型/真值) 平均 %.2f  中位 %.2f  范围 %.2f~%.2f"
              % (a.mean(), np.median(a), a.min(), a.max()))
        print("   -> %s" % ("旧模型系统性偏差明显，应改用单应矩阵"
                            if abs(a.mean() - 1.0) > 0.15 else "旧模型基本可用"))

    print("\n=== 同一帧内横向 vs 纵向的 ppm 差异（证明需要 2D 模型）===")
    for tag, pts in traj.items():
        pts.sort()
        for i in range(1, len(pts), 20):
            (t0, u0, v0, x0, y0) = pts[i - 1]
            (t1, u1, v1, x1, y1) = pts[i]
            dx_m, dy_m = abs(x1 - x0), abs(y1 - y0)
            du_p, dv_p = abs(u1 - u0), abs(v1 - v0)
            if dx_m > 0.5 and dy_m > 0.1:
                print("   %-9s t=%.2f  x向 %.1f px/%.2f m = %.1f px/m | y向 %.1f px/%.2f m = %.1f px/m"
                      % (tag[:8], t1, du_p, dx_m, du_p / dx_m, dv_p, dy_m, dv_p / dy_m))
                break
    return 0


if __name__ == "__main__":
    sys.exit(main())
