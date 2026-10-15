"""验证：用「相机高度+俯角+视场角」能反算出车辆在地面的真实位置吗？

物理模型（针孔相机 + 地面约束）：
  世界点 P 投影:  u = W/2 + f * (d·right)/(d·fwd)
                  v = H/2 - f * (d·up)/(d·fwd)
  已知相机位置 C、姿态 (pitch,yaw)、焦距 f，
  若 P 在地面 (z = z_ground)，可由像素 (u,v) **反解**出 P 的世界 (x,y)。

验证方法：读 ground_truth_dual.csv 里的真值
  （cam1_u, cam1_v 是像素坐标；(x,y) 是世界米制坐标）
  用逆投影把 (u,v) 还原成世界坐标，和真值比误差。
若误差在米级以内 -> 该模型可用于测速；若差得远 -> 需换方案。
"""
import csv
import math
import sys

import numpy as np

CSV = r"E:\output\_dual_cam_demo\ground_truth_dual.csv"
# 录制 CAM-1 的相机参数（_dual_cam_demo.py 里硬编码的，可信）
CAM_LOC = np.array([-15.720, -63.145, 5.732])
CAM_PITCH, CAM_YAW = -23.445, 179.536
W, H, FOV = 1920, 1080, 90.0
GROUND_Z = 0.0


def axes(pitch_deg, yaw_deg):
    p, y = math.radians(pitch_deg), math.radians(yaw_deg)
    cp, sp, cy, sy = math.cos(p), math.sin(p), math.cos(y), math.sin(y)
    fwd = np.array([cp * cy, cp * sy, -sp])
    right = np.array([-sy, cy, 0.0])
    up = np.array([-sp * cy, -sp * sy, cp])
    return fwd, right, up


def project(P, loc=None, pitch=None, yaw=None, w=W, h=H, fov=FOV):
    loc = CAM_LOC if loc is None else loc
    pitch = CAM_PITCH if pitch is None else pitch
    yaw = CAM_YAW if yaw is None else yaw
    fwd, right, up = axes(pitch, yaw)
    d = np.asarray(P, float) - loc
    z = float(d @ fwd)
    if z <= 1e-6:
        return None
    f = w / (2 * math.tan(math.radians(fov) / 2))
    return (w / 2 + f * float(d @ right) / z, h / 2 - f * float(d @ up) / z)


def unproject_to_ground(u, v, loc=None, pitch=None, yaw=None, w=W, h=H, fov=FOV,
                        ground_z=GROUND_Z):
    """像素 -> 地面世界坐标（射线与 z=ground_z 平面求交）"""
    loc = CAM_LOC if loc is None else loc
    pitch = CAM_PITCH if pitch is None else pitch
    yaw = CAM_YAW if yaw is None else yaw
    fwd, right, up = axes(pitch, yaw)
    f = w / (2 * math.tan(math.radians(fov) / 2))
    # 相机坐标系下的射线方向（归一化前）
    dir_cam = np.array([(u - w / 2) / f, -(v - h / 2) / f, 1.0])
    # 转到世界系：forward 分量 = z_cam
    d_world = dir_cam[0] * right + dir_cam[1] * up + dir_cam[2] * fwd
    if abs(d_world[2]) < 1e-9:
        return None
    t = (ground_z - loc[2]) / d_world[2]
    if t <= 0:
        return None
    return loc + t * d_world


def main():
    rows = list(csv.DictReader(open(CSV, encoding="utf-8")))
    print("ground truth 行数: %d" % len(rows))
    pts = []
    for r in rows:
        if not r.get("cam1_u") or not r.get("cam1_v"):
            continue
        if r.get("cam1_in") != "1":
            continue
        try:
            u, v = float(r["cam1_u"]), float(r["cam1_v"])
            x, y = float(r["x"]), float(r["y"])
        except ValueError:
            continue
        # 只要有意义的地面点（v 在画面内、不是极端值）
        if not (0 <= u < W and 0 <= v < H):
            continue
        pts.append((u, v, x, y, r["tag"], r["t_sec"]))
    print("可用样本: %d" % len(pts))

    print("\n%-8s %-7s %-16s %-24s %-24s %s"
          % ("t", "tag", "像素(u,v)", "真值世界(x,y)", "逆投影还原(x,y)", "误差(米)"))
    errs = []
    for (u, v, x, y, tag, t) in pts[:40]:
        P = unproject_to_ground(u, v)
        if P is None:
            print("%-8s %-7s (%7.1f,%7.1f)  (%8.2f,%8.2f)   逆投影失败"
                  % (t, tag[:6], u, v, x, y))
            continue
        e = math.dist((P[0], P[1]), (x, y))
        errs.append(e)
        print("%-8s %-7s (%7.1f,%7.1f)  (%8.2f,%8.2f)   (%8.2f,%8.2f)   %6.2f"
              % (t, tag[:6], u, v, x, y, P[0], P[1], e))

    if errs:
        a = np.array(errs)
        print("\n=== 误差统计（共 %d 个样本）===" % len(errs))
        print("   平均 %.2f m   中位 %.2f m   90分位 %.2f m   最大 %.2f m"
              % (a.mean(), np.median(a), np.percentile(a, 90), a.max()))
        if a.mean() < 2.0:
            print("   -> 模型可用（误差在米级以内）")
        else:
            print("   -> 模型偏差较大，需检查参数或改用标定方案")
    return 0


if __name__ == "__main__":
    sys.exit(main())
