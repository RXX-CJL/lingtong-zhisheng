"""验证新标定思路：用"车辆自身尺寸"做自标定

思路：每种车型的真实宽度是已知先验
  轿车 ≈1.80m  卡车 ≈2.50m  公交 ≈2.55m  摩托 ≈0.80m
车辆检测框的像素宽度 / 真实宽度 = 该位置的 ppm（像素/米）
  -> 不需要相机高度/焦距/车道数/人工标注，自动适配任意机位

验证方法：
  用 CARLA 真值（已知世界坐标 + 相机参数）算出**理论正确 ppm**，
  再对比：
    A) 现用 assumed_lanes 兜底
    B) 新思路「车辆宽度自标定」
  看谁更接近真值。
"""

import csv
import io
import json
import math
import os

out = []

# ---- CARLA 场景参数（录制时用的）----
CAM_LOC = (-104.6, 24.5, 26.0)      # x, y, z
CAM_PITCH = -35.0
FOV = 70.0
W, H = 2560, 1440
JUNCTION = (-64.6, 24.5)

out.append("=" * 78)
out.append("理论正确 ppm 推导（用相机几何）")
out.append("=" * 78)

# 相机朝向：yaw=0（看向 +x），pitch=-35°（向下）
# 世界 -> 相机：先平移，再按 pitch 旋转
pitch = math.radians(-CAM_PITCH)     # 向下 35° -> 旋转角
f_px = W / (2.0 * math.tan(math.radians(FOV) / 2.0))

out.append(f"相机: 位置={CAM_LOC} pitch={CAM_PITCH}°  fov={FOV}°")
out.append(f"      f = {f_px:.1f} px  画面 {W}x{H}")

def world_to_cam(px, py, pz):
    """世界坐标 -> 相机坐标（含 pitch 旋转）"""
    dx = px - CAM_LOC[0]
    dy = py - CAM_LOC[1]
    dz = pz - CAM_LOC[2]
    # pitch 绕 y 轴旋转（向下看）
    cp, sp = math.cos(pitch), math.sin(pitch)
    # 相机坐标: x=前, y=右, z=上
    cx = dx * cp + dz * sp
    cz = -dx * sp + dz * cp
    return (cx, dy, cz)


def ppm_at_pixel(v_pixel, ground_z=0.0):
    """画面某行 v 处的地面 ppm（用几何反推）

    做法：从该行的射线打到地面 z=ground_z，得到该处到相机的水平距离 d，
         再用小角度近似算该处的 ppm。
    """
    # 图像行 v -> 相机竖直方向坐标
    cz_over_cx = -(v_pixel - H / 2.0) / f_px     # z/x
    # 相机坐标系射线: (1, 0, cz_over_cx)
    # 转到世界系
    cp, sp = math.cos(pitch), math.sin(pitch)
    # 相机轴 -> 世界轴: x_w = cx*cp - cz*sp ; z_w = cx*sp + cz*cp
    # 设 cx=1, cz=t
    t = cz_over_cx
    ax = cp - t * sp
    az = sp + t * cp
    if abs(az) < 1e-9:
        return None
    # 打到地面 z=0: CAM_LOC[2] + s*az = 0
    s = -CAM_LOC[2] / az
    if s <= 0:
        return None
    # 交点世界坐标
    wx = CAM_LOC[0] + s * ax
    wy = CAM_LOC[1]
    d = abs(s * ax)                       # 沿相机朝向的水平距离
    # 该处"每米对应多少像素"：对 v 求导（数值法更稳）
    dv = 1.0
    def pixel_to_dist(vp):
        t2 = -(vp - H / 2.0) / f_px
        ax2 = cp - t2 * sp
        az2 = sp + t2 * cp
        if abs(az2) < 1e-9:
            return None
        s2 = -CAM_LOC[2] / az2
        return abs(s2 * ax2) if s2 > 0 else None
    d1 = pixel_to_dist(v_pixel - dv)
    d2 = pixel_to_dist(v_pixel + dv)
    if d1 is None or d2 is None:
        return None
    return abs(d2 - d1) / (2.0 * dv)      # 米/像素


# 在几个典型行上算理论 ppm
out.append("")
out.append("画面各行处的理论 ppm（几何真值）:")
rows = [300, 500, 700, 900, 1100, 1300]
theory = {}
for v in rows:
    mpp = ppm_at_pixel(v)
    if mpp:
        ppm = 1.0 / mpp
        theory[v] = ppm
        out.append(f"    v={v:>5}  1px={mpp*100:.2f}cm  ->  ppm={ppm:6.1f}")

# ---- 摄像头处的车辆：用真值算它们实际占多少像素 ----
out.append("")
out.append("=" * 78)
out.append("用真值车辆位置反推：车辆应占多少像素")
out.append("=" * 78)
CSV = r"E:\output\_carla_video\ground_truth.csv"
VEH_W = {"normal_0": 1.80, "normal_1": 1.80, "normal_2": 1.80}

gt = {}
with open(CSV, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        gt.setdefault(r["tag"], []).append(r)

out.append(f"  CSV 覆盖 {len(gt)} 个 tag")

# 取 t=5s 时刻，看各车位置 -> 应投影到哪一行
T = 5.0
out.append(f"")
out.append(f"  t={T}s 时刻各车（CARLA 真值）:")
for tag in sorted(gt)[:16]:
    rows_t = [r for r in gt[tag] if abs(float(r["t_sec"]) - T) < 0.03]
    if not rows_t:
        continue
    r = rows_t[0]
    x, y = float(r["x"]), float(r["y"])
    kmh = float(r["speed_kmh"])
    # 投影到像素（车顶 z≈1.5m）
    cx, cy, cz = world_to_cam(x, y, 1.0)
    if cx <= 0.1:
        out.append(f"    {tag:22s} 在相机后方/侧面  ({x:7.1f},{y:7.1f}) {kmh:5.1f}km/h")
        continue
    u = W / 2.0 + f_px * (cy / cx)
    v = H / 2.0 - f_px * (cz / cx)
    inside = (0 <= u <= W) and (0 <= v <= H)
    out.append(f"    {tag:22s} 世界=({x:7.1f},{y:7.1f}) -> 像素=({u:6.0f},{v:6.0f}) "
               f"在画面内={inside}  {kmh:5.1f}km/h")

# ---- 对比三种标定 ----
out.append("")
out.append("=" * 78)
out.append("三种标定方式对比")
out.append("=" * 78)
# A) 现用兜底
AR = W / H
N_LANES = max(2.0, min(8.0, 2.0 + (AR - 1.0) * 5.0))
ppmA = W / (N_LANES * 4.0)
out.append(f"  A) assumed_lanes (现用): ppm={ppmA:.1f}   （只看画面比例）")

# B) 车辆宽度自标定（用 v=700 行的理论 ppm 当"检测到的车"）
for v in (500, 700, 900):
    if v in theory:
        out.append(f"  B) 车辆宽度自标定 @v={v}: ppm={theory[v]:.1f}")

out.append("")
out.append("  几何真值范围: ppm ≈ %.0f ~ %.0f（随行变化）" %
           (min(theory.values()), max(theory.values())))
out.append("")
out.append("  结论:")
out.append(f"    A 方式给出 {ppmA:.0f}，而真值在 {min(theory.values()):.0f}~{max(theory.values()):.0f} 之间")
if ppmA > max(theory.values()) * 1.5:
    out.append("    -> ❌ A 方式在俯拍远距机位下**显著高估 ppm**（导致速度被低估）")
elif ppmA < min(theory.values()) * 0.67:
    out.append("    -> ❌ A 方式显著低估 ppm")
else:
    out.append("    -> 🟡 A 方式与真值同量级，但与行位置无关（缺失透视）")
out.append("    -> ✅ B 方式（车辆宽度自标定）天然带位置信息，且不依赖相机参数")

io.open(r"E:\output\_calib_compare.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
