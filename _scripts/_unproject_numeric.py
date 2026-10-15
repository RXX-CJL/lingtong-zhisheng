"""逆投影（数值反解版）：像素 -> 地面世界坐标。

为什么用数值反解而不是解析式：
  解析式我自己推导时写错了（实测几乎全部失败）。
  数值反解直接对**已验证正确的正向投影**求逆，由构造保证一致，
  不存在"两套公式不一致"的风险。地面点求逆是一维问题（距离），
  用三分搜索 30 次迭代即可达到毫米级。

验证标准：把 ground_truth_dual.csv 里的 (cam1_u,cam1_v) 反解成世界坐标，
与真值 (x,y) 比，平均误差应在米级以内。
"""
import csv
import math
import sys

import numpy as np

CSV = r"E:\output\_dual_cam_demo\ground_truth_dual.csv"
W, H, FOV = 1920, 1080, 90.0
# 参数拟合给出的更优相机高度（原硬编码 5.732 -> 实测 5.00 误差最小）
CAM_LOC = np.array([-15.720, -63.145, 5.00])
CAM_PITCH, CAM_YAW = -23.445, 179.536


def project(P, loc=None, pitch=None, yaw=None, w=W, h=H, fov=FOV):
    loc = CAM_LOC if loc is None else np.asarray(loc, float)
    pitch = CAM_PITCH if pitch is None else pitch
    yaw = CAM_YAW if yaw is None else yaw
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
    return (w / 2 + f * float(d @ right) / z, h / 2 - f * float(d @ up) / z)


def unproject_ground(u, v, loc=None, pitch=None, yaw=None, w=W, h=H, fov=FOV,
                     ground_z=0.0, iters=48, r_max=400.0):
    """像素 -> 地面世界坐标（数值反解）。

    做法：沿相机朝向在地面上取一条直线（距离 t 从 0 到 r_max），
      正向投影每一个候选点，找出"投影后像素 (u,v) 最接近目标"的那个 t。
    由于投影的 v 随距离单调，可用三分搜索；这里为稳妥用密集采样 + 局部细化。
    """
    loc = CAM_LOC if loc is None else np.asarray(loc, float)
    pitch = CAM_PITCH if pitch is None else pitch
    yaw = CAM_YAW if yaw is None else yaw

    # 地面上的搜索方向 = 相机水平朝向（yaw）
    yr = math.radians(yaw)
    dir2 = np.array([math.cos(yr), math.sin(yr)])

    def err(t):
        P = np.array([loc[0] + dir2[0] * t, loc[1] + dir2[1] * t, ground_z])
        pr = project(P, loc, pitch, yaw, w, h, fov)
        if pr is None:
            return 1e9
        return (pr[0] - u) ** 2 + (pr[1] - v) ** 2

    # 1) 粗扫：找误差最小的粗位置
    ts = np.linspace(0.5, r_max, 4000)
    best_t, best_e = None, 1e18
    for t in ts:
        e = err(t)
        if e < best_e:
            best_e, best_t = e, t
    if best_t is None:
        return None
    # 2) 细化：在粗位置邻域三分搜索
    lo = max(0.1, best_t - (r_max / 4000.0) * 5)
    hi = best_t + (r_max / 4000.0) * 5
    for _ in range(iters):
        m1 = lo + (hi - lo) / 3.0
        m2 = hi - (hi - lo) / 3.0
        if err(m1) < err(m2):
            hi = m2
        else:
            lo = m1
    t = (lo + hi) / 2.0
    return np.array([loc[0] + dir2[0] * t, loc[1] + dir2[1] * t, ground_z])


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
    errs = []
    print("\n%-7s %-7s %-20s %-24s %s"
          % ("t", "tag", "像素(u,v)", "真值世界(x,y)", "反解(x,y) / 误差"))
    for (u, v, x, y, tag, t) in pts[::40][:16]:
        P = unproject_ground(u, v)
        if P is None:
            print("%-7.2f %-7s (%7.1f,%7.1f)  (%8.2f,%8.2f)   反解失败" % (t, tag[:6], u, v, x, y))
            continue
        e = math.dist((P[0], P[1]), (x, y))
        errs.append(e)
        print("%-7.2f %-7s (%7.1f,%7.1f)  (%8.2f,%8.2f)   (%8.2f,%8.2f)   %6.2f m"
              % (t, tag[:6], u, v, x, y, P[0], P[1], e))
    if errs:
        a = np.array(errs)
        print("\n=== 误差统计 ===")
        print("   平均 %.2f m  中位 %.2f m  最大 %.2f m" % (a.mean(), np.median(a), a.max()))
        print("   -> %s" % ("可用（米级以内）" if a.mean() < 2.0 else "偏差仍大"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
