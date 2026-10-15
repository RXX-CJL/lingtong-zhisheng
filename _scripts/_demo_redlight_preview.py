"""读取用户手动调整的机位，并按该机位做一次闯红灯演示

用户要求：
  "我调整好了机位，你按照现在我调整的机位开始先演示一遍给我看，
   再决定要不要录下来"

做法：
  ① 读取 world.get_spectator() 的当前变换（= 用户调好的机位）
  ② 用完全相同的 transform 生成一台演示相机（这样相机拍到的 = 用户看到的）
  ③ 在该机位下跑一次闯红灯场景：
       - 若干守法车（autopilot，会在红灯前停下）
       - 一辆违规车（ignore_lights_percentage=100，红灯时冲过）
  ④ 抓若干帧保存，让用户Judge机位与场景
  ⑤ 同时输出各车速度/位置，证明"守法车真的停了，违规车真的闯了"
"""

import io
import math
import os
import queue

import carla

OUT = r"E:\output\_demo_redlight"
os.makedirs(OUT, exist_ok=True)
out = []

client = carla.Client("127.0.0.1", 2000)
client.set_timeout(30.0)
world = client.get_world()
m = world.get_map()
bp = world.get_blueprint_library()

# ---- ① 读取用户调好的机位 ----
spec = world.get_spectator()
user_tf = spec.get_transform()
out.append("=" * 84)
out.append("① 读取到你调整的机位")
out.append("=" * 84)
out.append(f"  位置 = ({user_tf.location.x:.2f}, {user_tf.location.y:.2f}, "
           f"{user_tf.location.z:.2f})")
out.append(f"  旋转 = pitch={user_tf.rotation.pitch:.2f}  yaw={user_tf.rotation.yaw:.2f}  "
           f"roll={user_tf.rotation.roll:.2f}")

# ---- ② 用同一 transform 生成演示相机 ----
RES = (1920, 1080)
FOV = 70.0
cam_bp = bp.find("sensor.camera.rgb")
cam_bp.set_attribute("image_size_x", str(RES[0]))
cam_bp.set_attribute("image_size_y", str(RES[1]))
cam_bp.set_attribute("fov", str(FOV))
cam = world.spawn_actor(cam_bp, user_tf)
out.append("")
out.append(f"② 已按该机位生成演示相机（{RES[0]}x{RES[1]} fov={FOV}）")

st = world.get_settings()
st.synchronous_mode = True
st.fixed_delta_seconds = 0.05
world.apply_settings(st)

import cv2
import numpy as np

q = queue.Queue()
cam.listen(q.put)


def grab():
    world.tick()
    try:
        img = q.get(timeout=12.0)
        return np.frombuffer(img.raw_data, dtype=np.uint8).reshape(
            (img.height, img.width, 4))[:, :, :3].copy()
    except queue.Empty:
        return None


# ---- 先抓一帧空场景，确认机位 ----
f0 = grab()
if f0 is not None:
    p0 = os.path.join(OUT, "view_00_empty.png")
    cv2.imwrite(p0, f0)
    out.append(f"   空场景一帧: {os.path.basename(p0)}")

# ---- ③ 找路口 + 生成车辆 ----
# 用机位视线方向推测用户在拍哪个路口：沿视线投射到地面
import math as _m
yaw_r = _m.radians(user_tf.rotation.yaw)
pitch_r = _m.radians(user_tf.rotation.pitch)
fwd = (carla.Vector3D(x=_m.cos(pitch_r) * _m.cos(yaw_r),
                      y=_m.cos(pitch_r) * _m.sin(yaw_r),
                      z=_m.sin(pitch_r)))
# 与 z=0 平面求交
z0 = user_tf.location.z
if abs(fwd.z) > 1e-6:
    t = -z0 / fwd.z
    hit = carla.Location(x=user_tf.location.x + fwd.x * t,
                         y=user_tf.location.y + fwd.y * t, z=0.0)
    out.append("")
    out.append(f"③ 机位视线与地面的交点 = ({hit.x:.1f}, {hit.y:.1f})")
else:
    hit = carla.Location(x=user_tf.location.x, y=user_tf.location.y, z=0)
    out.append("③ 视线接近水平，无法求交点")

# 找离交点最近的路口
best_j, bd = None, 1e9
for sp in m.get_spawn_points():
    w = m.get_waypoint(sp.location)
    if w.is_junction and w.junction_id is not None:
        d = sp.location.distance(hit)
        if d < bd:
            bd, best_j = d, (w.junction_id, sp.location)
out.append(f"   最近路口: junction_id={best_j[0]}  距交点 {bd:.1f}m  "
           f"位置=({best_j[1].x:.1f},{best_j[1].y:.1f})")
jl = best_j[1]

# 生成车辆：守法车 + 1 辆违规车
tm = client.get_trafficmanager(8000)
tm.set_synchronous_mode(True)
tm.set_global_distance_to_leading_vehicle(3.0)

veh_bps = [b for b in bp.filter("vehicle.*")
           if not any(k in b.id for k in ("bike", "harley", "crossbike", "kawasaki",
                                          "microlino", "carlacola"))]

near = sorted([(s.location.distance(jl), s) for s in m.get_spawn_points()],
              key=lambda x: x[0])[:20]
lawful, violator = [], None
idx = 0
for d, s in near:
    w = m.get_waypoint(s.location)
    if w.is_junction:
        continue
    try:
        v = world.spawn_actor(veh_bps[idx % len(veh_bps)], s)
        v.set_autopilot(True, tm.get_port())
        idx += 1
        if violator is None and d < 60:
            violator = v
            # 关键：只让这一辆车无视红灯 -> 它会闯红灯，其余车会守法停下
            try:
                tm.ignore_lights_percentage(v, 100.0)
                out.append(f"   违规车 id={v.id} 已设 ignore_lights_percentage=100")
            except Exception as e:
                out.append(f"   设置违规车失败: {str(e)[:70]}")
        else:
            lawful.append(v)
        if len(lawful) >= 4 and violator is not None:
            break
    except Exception:
        continue

out.append(f"   已生成 {len(lawful)} 辆守法车 + "
           f"{1 if violator else 0} 辆违规车")

# ---- ④ 跑仿真并抓帧 ----
out.append("")
out.append("=" * 84)
out.append("④ 跑 20 秒仿真，记录行为并抓帧")
out.append("=" * 84)

shots = []
log = []
for i in range(400):        # 20s @20fps
    world.tick()
    # 窗口继续跟随用户机位（保持用户看到的画面）
    if i % 100 == 0:
        spec.set_transform(user_tf)
    if i % 40 == 0:         # 每 2 秒抓一帧
        f = grab()
        if f is not None:
            p = os.path.join(OUT, f"view_{i//40:02d}_t{i/20:.0f}s.png")
            cv2.imwrite(p, f)
            shots.append((i / 20.0, p))
        # 记录各车状态
        row = {"t": round(i / 20.0, 1)}
        allv = lawful + ([violator] if violator else [])
        for k, v in enumerate(allv):
            try:
                vel = v.get_velocity()
                kmh = 3.6 * math.sqrt(vel.x**2 + vel.y**2 + vel.z**2)
                loc = v.get_location()
                row[f"v{k}"] = (round(kmh, 1), round(loc.distance(jl), 1))
            except Exception:
                pass
        log.append(row)

out.append(f"   抓帧 {len(shots)} 张")
out.append("")
out.append("   时间 | 各车 (速度km/h, 距路口m)")
for row in log:
    parts = [f"{k}=({v[0]},{v[1]})" for k, v in row.items() if k != "t"]
    out.append(f"   t={row['t']:>5}s | " + "  ".join(parts))

# 判定：是否出现"有车停下 + 有车通过"
out.append("")
out.append("=" * 84)
out.append("⑤ 行为判定")
out.append("=" * 84)
allv = lawful + ([violator] if violator else [])
if log:
    for k, v in enumerate(allv):
        key = f"v{k}"
        vals = [row.get(key) for row in log if row.get(key)]
        if not vals:
            continue
        sp = [x[0] for x in vals]
        dd = [x[1] for x in vals]
        tag = "违规车" if v is violator else f"守法车{k}"
        out.append(f"  {tag:8} id={v.id:>3}  速度 {min(sp):>5.1f}~{max(sp):>5.1f} km/h  "
                   f"距路口 {min(dd):>5.1f}~{max(dd):>5.1f} m  "
                   f"{'有停车(速度曾<1)' if min(sp) < 1.0 else '未停车'}")

# 清理
try:
    cam.stop(); cam.destroy()
except Exception:
    pass
for v in allv:
    try:
        v.set_autopilot(False)
        v.destroy()
    except Exception:
        pass
st.synchronous_mode = False
st.fixed_delta_seconds = None
world.apply_settings(st)
out.append("")
out.append("已清理相机与车辆（CARLA 窗口保持在你调的机位）")

io.open(r"E:\output\_demo_redlight_preview.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
