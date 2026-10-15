"""闯红灯演示（选项1+3）：相机距路口 12m，等车到位后连续抓帧

用户的诉求链：
  "闯红灯" 演示视频 —— 车辆必须真实行驶（会停、会起步）
  机位要符合现实（真实监控高度）
  拍到"车冲过停止线"的关键动作

本脚本：
  ① 机位：路口【上游侧】(车流来向) 12m、高 6.5m、俯角 -18° —— 面向路口
     理由：车从远处驶来 -> 经过相机 -> 冲过停止线 -> 进路口，全过程可见
  ② 生成 8 辆车（autopilot，会遵守红绿灯）
  ③ 其中 1 辆设 ignore_lights_percentage=100（闯红灯）
  ④ 先跑 20 秒让车流铺开，然后**监测"是否有车接近路口(<35m)"**，
     一旦满足就连续抓帧 60 帧（3 秒 @20fps）
  ⑤ 记录每帧各车速度/位置，证明"守法车停下、违规车冲过"
"""

import io
import math
import os
import queue

import carla

OUT = r"E:\output\_demo_redlight2"
os.makedirs(OUT, exist_ok=True)
out = []

client = carla.Client("127.0.0.1", 2000)
client.set_timeout(30.0)
world = client.get_world()
m = world.get_map()
bp = world.get_blueprint_library()
world.set_weather(carla.WeatherParameters.ClearNoon)

TARGET_JID = 23
jsp = None
for sp in m.get_spawn_points():
    w = m.get_waypoint(sp.location)
    if w.is_junction and w.junction_id == TARGET_JID:
        jsp = sp
        break
jl = jsp.location
out.append(f"junction_id={TARGET_JID} 中心=({jl.x:.1f},{jl.y:.1f})")

# 进近方向
cands = []
for sp in m.get_spawn_points():
    w = m.get_waypoint(sp.location)
    if w.is_junction:
        continue
    d = sp.location.distance(jl)
    if d > 130:
        continue
    to_j = math.degrees(math.atan2(jl.y - sp.location.y, jl.x - sp.location.x))
    if abs((sp.rotation.yaw - to_j + 540) % 360 - 180) < 25:
        cands.append((d, sp, w))
cands.sort(key=lambda x: x[0])
approach_yaw = cands[0][1].rotation.yaw
yr = math.radians(approach_yaw)
out.append(f"进近 yaw={approach_yaw:.1f}  朝路口 spawn {len(cands)} 个")

# ---- 机位：路口【上游】12m，面向路口（车会朝相机开来）----
BACK = 12.0
HEIGHT = 6.5
PITCH = -18.0
cam_loc = carla.Location(x=jl.x - math.cos(yr) * BACK,
                        y=jl.y - math.sin(yr) * BACK,
                        z=jl.z + HEIGHT)
yaw_cam = math.degrees(math.atan2(jl.y - cam_loc.y, jl.x - cam_loc.x))
cam_rot = carla.Rotation(pitch=PITCH, yaw=yaw_cam, roll=0.0)
out.append(f"机位: ({cam_loc.x:.1f},{cam_loc.y:.1f},{cam_loc.z:.1f}) yaw={yaw_cam:.1f} "
           f"pitch={PITCH}  路口上游 {BACK}m（面向路口）")

spec = world.get_spectator()
spec.set_transform(carla.Transform(cam_loc, cam_rot))

st = world.get_settings()
st.synchronous_mode = True
st.fixed_delta_seconds = 0.05
world.apply_settings(st)

import cv2
import numpy as np

RES = (1920, 1080)
FOV = 70.0
cam_bp = bp.find("sensor.camera.rgb")
cam_bp.set_attribute("image_size_x", str(RES[0]))
cam_bp.set_attribute("image_size_y", str(RES[1]))
cam_bp.set_attribute("fov", str(FOV))
cam = world.spawn_actor(cam_bp, carla.Transform(cam_loc, cam_rot))
for _ in range(3):           # ⚠ 必须先 tick 再取 transform（本日踩坑）
    world.tick()
cam_tf = cam.get_transform()
out.append(f"相机实际: ({cam_tf.location.x:.2f},{cam_tf.location.y:.2f},"
           f"{cam_tf.location.z:.2f}) yaw={cam_tf.rotation.yaw:.2f}")
q = queue.Queue()
cam.listen(q.put)

f_px = RES[0] / (2.0 * math.tan(math.radians(FOV) / 2.0))


def proj(P):
    inv = cam_tf.get_inverse_matrix()
    d = (P[0] - cam_tf.location.x, P[1] - cam_tf.location.y, P[2] - cam_tf.location.z)
    vc = [sum(inv[i][j] * (d[0], d[1], d[2], 1.0)[j] for j in range(4)) for i in range(4)]
    if vc[0] <= 0.1:
        return None
    return (RES[0] / 2 + f_px * (vc[1] / vc[0]), RES[1] / 2 - f_px * (vc[2] / vc[0]))


def grab():
    try:
        img = q.get(timeout=3.0)
        return np.frombuffer(img.raw_data, dtype=np.uint8).reshape(
            (img.height, img.width, 4))[:, :, :3].copy()
    except queue.Empty:
        return None


# ---- 生成车辆 ----
tm = client.get_trafficmanager(8000)
tm.set_synchronous_mode(True)
tm.set_global_distance_to_leading_vehicle(3.5)
veh_bps = [b for b in bp.filter("vehicle.*")
           if not any(k in b.id for k in ("bike", "harley", "crossbike",
                                          "kawasaki", "microlino", "carlacola"))]
spawned = []
idx = 0
for d, sp, w in cands[:8]:
    try:
        v = world.spawn_actor(veh_bps[idx % len(veh_bps)], sp)
        v.set_autopilot(True, tm.get_port())
        spawned.append(v)
        idx += 1
    except Exception:
        continue
violator = spawned[0] if spawned else None      # 用最靠近路口的那辆做违规车
if violator:
    try:
        tm.ignore_lights_percentage(violator, 100.0)
        out.append(f"违规车（闯红灯）id={violator.id}  其余 {len(spawned)-1} 辆守法")
    except Exception as e:
        out.append(f"设置违规车失败: {str(e)[:70]}")

# ---- 先跑 20 秒让车流铺开 ----
out.append("")
out.append("阶段 1：先跑 20 秒让车流接近路口")
for i in range(400):
    world.tick()
    if i % 100 == 0:
        near = sum(1 for v in spawned if v.get_location().distance(jl) < 40)
        out.append(f"  t={i/20:5.1f}s  距路口<40m 的车: {near}")

# ---- 阶段 2：监测并连续抓帧 ----
out.append("")
out.append("阶段 2：等「有车接近路口」，连续抓帧")
frames = []
rec = []
COND_M = 35.0
started = False
for i in range(600):
    world.tick()
    n_near = 0
    for v in spawned:
        try:
            if v.get_location().distance(jl) < COND_M:
                n_near += 1
        except Exception:
            pass
    if not started and n_near >= 2:
        started = True
        out.append(f"  触发抓帧: t={i/20:.1f}s  有 {n_near} 辆车在 {COND_M}m 内")
    if started:
        f = grab()
        if f is not None:
            p = os.path.join(OUT, f"seq_{len(frames):03d}_t{i/20:05.1f}s.png")
            cv2.imwrite(p, f)
            frames.append(p)
        row = {"t": round(i / 20.0, 1)}
        for k, v in enumerate(spawned):
            try:
                vel = v.get_velocity()
                kmh = 3.6 * math.sqrt(vel.x**2 + vel.y**2 + vel.z**2)
                loc = v.get_location()
                pr = proj((loc.x, loc.y, loc.z + 0.8))
                inv = bool(pr and 0 <= pr[0] <= RES[0] and 0 <= pr[1] <= RES[1])
                row[f"v{k}"] = (round(kmh, 1), round(loc.distance(jl), 1), inv)
            except Exception:
                pass
        rec.append(row)
        if len(frames) >= 80:
            break

out.append(f"  抓帧 {len(frames)} 张")
out.append("")
out.append("  时间 | 各车 (速度, 距路口, 在画面内)")
for row in rec[::4]:
    parts = []
    for k, v in row.items():
        if k == "t":
            continue
        parts.append(f"{k}=({v[0]},{v[1]},{'✅' if v[2] else '✗'})")
    out.append(f"   t={row['t']:>5}s | " + "  ".join(parts))

# 汇总行为
out.append("")
out.append("=" * 80)
out.append("行为汇总")
out.append("=" * 80)
for k, v in enumerate(spawned):
    vals = [r.get(f"v{k}") for r in rec if r.get(f"v{k}")]
    if not vals:
        continue
    sp = [x[0] for x in vals]
    dd = [x[1] for x in vals]
    tag = "★违规车" if v is violator else f" 守法车{k}"
    out.append(f"  {tag} id={v.id:>3}  速度 {min(sp):>5.1f}~{max(sp):>5.1f} km/h  "
               f"距路口 {min(dd):>5.1f}~{max(dd):>5.1f} m  "
               f"{'曾停车' if min(sp) < 1.0 else '未停车'}  "
               f"画面内 {sum(1 for x in vals if x[2])}/{len(vals)} 帧")

try:
    cam.stop(); cam.destroy()
except Exception:
    pass
for v in spawned:
    try:
        v.set_autopilot(False)
        v.destroy()
    except Exception:
        pass
st.synchronous_mode = False
st.fixed_delta_seconds = None
world.apply_settings(st)
out.append("")
out.append("已清理")

io.open(r"E:\output\_demo_redlight2.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
