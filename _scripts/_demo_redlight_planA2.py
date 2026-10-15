"""方案 A 修正版：实时寻找"车辆进入画面"的时刻再抓帧

上一版问题：
  车辆 spawn 在距路口 48~67m 处，而相机架在距路口 18m
  -> 车在相机【后方】-> 画面里没有车
  （原因：CARLA 的 spawn point 都在远离路口的直路段上）

修正思路：
  不再"先架机位再看有没有车"，改为**边跑边用投影判断车辆是否入画**，
  一旦有车进入画面就抓帧并记录，这样拿到的一定是"有车且在路口附近"的画面。
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

# ---- 进近方向（朝向路口的 spawn point）----
cands = []
for sp in m.get_spawn_points():
    w = m.get_waypoint(sp.location)
    if w.is_junction:
        continue
    d = sp.location.distance(jl)
    if d > 120:
        continue
    to_j = math.degrees(math.atan2(jl.y - sp.location.y, jl.x - sp.location.x))
    diff = abs((sp.rotation.yaw - to_j + 540) % 360 - 180)
    if diff < 25:
        cands.append((d, sp, w))
cands.sort(key=lambda x: x[0])
approach_yaw = cands[0][1].rotation.yaw
out.append(f"进近方向 yaw={approach_yaw:.1f}（{len(cands)} 个朝路口点）")

# ---- 机位（2026-10-04 修正方向）----
# 上一版错误：把相机放在"路口 - 34m*车流方向"处，即路口【上游】，
#   而车流也是从上游驶来 -> 相机背对来车 -> 画面里 0 辆车。
# 正确做法：相机放在路口【下游】（车流已通过的一侧），面向来车，
#   这样才能拍到"车从远处驶来 -> 通过路口"的完整过程。
BACK = 20.0
HEIGHT = 6.5
PITCH = -18.0
yr = math.radians(approach_yaw)
# 下游 = 沿车流前进方向再往前 BACK 米
cam_loc = carla.Location(x=jl.x + math.cos(yr) * BACK,
                        y=jl.y + math.sin(yr) * BACK,
                        z=jl.z + HEIGHT)
# 相机看向【来车方向】（即与车流方向相反）
look_x = jl.x - math.cos(yr) * 60.0
look_y = jl.y - math.sin(yr) * 60.0
yaw_cam = math.degrees(math.atan2(look_y - cam_loc.y, look_x - cam_loc.x))
cam_rot = carla.Rotation(pitch=PITCH, yaw=yaw_cam, roll=0.0)
out.append(f"机位: ({cam_loc.x:.1f},{cam_loc.y:.1f},{cam_loc.z:.1f}) yaw={yaw_cam:.1f} "
           f"pitch={PITCH}  路口下游 {BACK}m（面向来车）")

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
# ⚠ 关键（2026-10-04 踩坑）：同步模式下 spawn 后必须【先 tick】再取 transform，
#   否则 get_transform() 返回单位矩阵（loc=0,0,0），导致所有投影失效 ——
#   这正是此前"画面里 0 辆车"的真因（不是机位问题）。
for _ in range(3):
    world.tick()
cam_tf = cam.get_transform()
out.append(f"相机实际 transform: ({cam_tf.location.x:.2f},{cam_tf.location.y:.2f},"
           f"{cam_tf.location.z:.2f}) yaw={cam_tf.rotation.yaw:.2f} "
           f"(期望 {cam_loc.x:.2f},{cam_loc.y:.2f},{cam_loc.z:.2f})")
q = queue.Queue()
cam.listen(q.put)

f_px = RES[0] / (2.0 * math.tan(math.radians(FOV) / 2.0))


def to_cam(P):
    inv = cam_tf.get_inverse_matrix()
    v = (P[0], P[1], P[2], 1.0)
    return tuple(sum(inv[i][j] * v[j] for j in range(4)) for i in range(4))


def proj(P):
    p = to_cam(P)
    if p[0] <= 0.1:
        return None
    return (RES[0] / 2 + f_px * (p[1] / p[0]), RES[1] / 2 - f_px * (p[2] / p[0]))


def n_in_view(vehicles):
    n = 0
    for v in vehicles:
        try:
            loc = v.get_location()
            pr = proj((loc.x, loc.y, loc.z + 0.8))
            if pr and 0 <= pr[0] <= RES[0] and 0 <= pr[1] <= RES[1]:
                n += 1
        except Exception:
            pass
    return n


# ---- 生成车辆 ----
tm = client.get_trafficmanager(8000)
tm.set_synchronous_mode(True)
tm.set_global_distance_to_leading_vehicle(3.0)
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
out.append(f"生成 {len(spawned)} 辆车")
violator = spawned[-1] if spawned else None
if violator:
    try:
        tm.ignore_lights_percentage(violator, 100.0)
        out.append(f"违规车 id={violator.id}")
    except Exception:
        pass

# ---- 边跑边找"画面内有车"的时刻 ----
out.append("")
out.append("=" * 80)
out.append("运行 + 实时投影判断车辆是否入画")
out.append("=" * 80)

best = []
for i in range(600):        # 30 秒
    world.tick()
    if i % 10 == 0:
        n = n_in_view(spawned)
        try:
            img = q.get(timeout=2.0)
            frame = np.frombuffer(img.raw_data, dtype=np.uint8).reshape(
                (img.height, img.width, 4))[:, :, :3].copy()
        except queue.Empty:
            frame = None
        if i % 40 == 0:
            out.append(f"  t={i/20:5.1f}s  画面内车辆={n}")
        if n >= 1 and frame is not None and len(best) < 8:
            p = os.path.join(OUT, f"A2_t{i/20:05.1f}s_n{n}.png")
            cv2.imwrite(p, frame)
            # 记录当时各车状态
            st_list = []
            for k, v in enumerate(spawned):
                try:
                    vel = v.get_velocity()
                    kmh = 3.6 * math.sqrt(vel.x**2 + vel.y**2 + vel.z**2)
                    pr = proj((v.get_location().x, v.get_location().y,
                               v.get_location().z + 0.8))
                    inv = bool(pr and 0 <= pr[0] <= RES[0] and 0 <= pr[1] <= RES[1])
                    st_list.append((k, round(kmh, 1), round(v.get_location().distance(jl), 1), inv))
                except Exception:
                    pass
            best.append({"t": round(i / 20.0, 1), "n": n, "path": p, "st": st_list})

out.append("")
out.append("=" * 80)
out.append(f"抓到 {len(best)} 张『画面内有车』的帧")
out.append("=" * 80)
for b in best:
    out.append(f"  t={b['t']:>5}s  画面内 {b['n']} 辆  -> {os.path.basename(b['path'])}")
    for k, kmh, d, inv in b["st"]:
        out.append(f"      v{k}  {kmh:>5.1f} km/h  距路口 {d:>5.1f}m  {'在画面内✅' if inv else ''}")

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

io.open(r"E:\output\_demo_redlight_planA2.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
