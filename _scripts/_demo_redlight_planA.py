"""按方案 A 架设机位（距路口 18m / 高 6.5m / 俯角 -22°），先抓帧给用户看

用户选择方案 A："我按距路口18m/高6.5m/俯角-22°架机位，先抓一帧给你看，你满意才录"

要点：
  · 机位方向必须【沿道路轴线】（否则拍到路口侧面，看不到停止线与路口中心）
  · 用进近道路的 waypoint 求出"车流朝向"，把相机放在车流【上游】18m 处
  · 相机看向路口中心，俯角 -22°
  · 生成车辆并推进到"有车在路口前"的时刻再抓帧（否则画面空）
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

# ---- ① 找路口中心 + 进近道路方向 ----
jsp = None
for sp in m.get_spawn_points():
    w = m.get_waypoint(sp.location)
    if w.is_junction and w.junction_id == TARGET_JID:
        jsp = sp
        break
jl = jsp.location
out.append(f"junction_id={TARGET_JID} 中心=({jl.x:.1f},{jl.y:.1f},{jl.z:.1f})")

# 找"驶向路口"的 spawn point（车辆朝向与指向路口的方向夹角小）
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
    if diff < 25:      # 朝向路口
        cands.append((d, sp, w))

cands.sort(key=lambda x: x[0])
out.append(f"朝向路口的 spawn point: {len(cands)} 个")
for d, sp, w in cands[:6]:
    out.append(f"   d={d:6.1f}m  yaw={sp.rotation.yaw:7.1f}  road={w.road_id} lane={w.lane_id} "
               f"loc=({sp.location.x:.1f},{sp.location.y:.1f})")

if not cands:
    out.append("⚠ 没有朝向路口的 spawn point，无法按道路轴线架机位")
    approach_yaw = None
else:
    # 用最近的进近点确定道路轴线方向（车流方向）
    d0, sp0, w0 = cands[0]
    approach_yaw = sp0.rotation.yaw
    out.append("")
    out.append(f"选定进近点: d={d0:.1f}m yaw={approach_yaw:.1f}  "
               f"loc=({sp0.location.x:.1f},{sp0.location.y:.1f})")

    # ---- ② 机位：沿车流方向【上游】18m，高 6.5m ----
    BACK = 18.0
    HEIGHT = 6.5
    PITCH = -22.0
    yr = math.radians(approach_yaw)
    # 车流前进方向 = (cos yaw, sin yaw)；相机放在路口【上游】= 往后退
    cam_loc = carla.Location(x=jl.x - math.cos(yr) * BACK,
                            y=jl.y - math.sin(yr) * BACK,
                            z=jl.z + HEIGHT)
    # 相机看向路口中心（水平 yaw 指向路口）
    yaw_cam = math.degrees(math.atan2(jl.y - cam_loc.y, jl.x - cam_loc.x))
    cam_rot = carla.Rotation(pitch=PITCH, yaw=yaw_cam, roll=0.0)
    out.append(f"机位: 位置=({cam_loc.x:.1f},{cam_loc.y:.1f},{cam_loc.z:.1f}) "
               f"yaw={yaw_cam:.1f} pitch={PITCH}")
    out.append(f"  距路口 {BACK}m  高 {HEIGHT}m  （车流方向 yaw={approach_yaw:.1f}）")

    # 把 CARLA 窗口也移到该机位（用户可实时看到）
    spec = world.get_spectator()
    spec.set_transform(carla.Transform(cam_loc, cam_rot))

    st = world.get_settings()
    st.synchronous_mode = True
    st.fixed_delta_seconds = 0.05
    world.apply_settings(st)

    import cv2
    import numpy as np

    RES = (1920, 1080)
    cam_bp = bp.find("sensor.camera.rgb")
    cam_bp.set_attribute("image_size_x", str(RES[0]))
    cam_bp.set_attribute("image_size_y", str(RES[1]))
    cam_bp.set_attribute("fov", "70")
    cam = world.spawn_actor(cam_bp, carla.Transform(cam_loc, cam_rot))
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

    # ---- ③ 生成车辆（都在进近方向上，会驶向路口）----
    tm = client.get_trafficmanager(8000)
    tm.set_synchronous_mode(True)
    tm.set_global_distance_to_leading_vehicle(3.0)

    veh_bps = [b for b in bp.filter("vehicle.*")
               if not any(k in b.id for k in ("bike", "harley", "crossbike",
                                              "kawasaki", "microlino", "carlacola"))]
    spawned = []
    idx = 0
    for d, sp, w in cands[:6]:
        try:
            v = world.spawn_actor(veh_bps[idx % len(veh_bps)], sp)
            v.set_autopilot(True, tm.get_port())
            spawned.append(v)
            idx += 1
        except Exception:
            continue
    out.append("")
    out.append(f"生成 {len(spawned)} 辆车（autopilot，全部朝向路口）")

    # 也放一辆"违规车"（无视红灯）
    violator = None
    if spawned:
        violator = spawned[-1]
        try:
            tm.ignore_lights_percentage(violator, 100.0)
            out.append(f"  违规车 id={violator.id} 设 ignore_lights_percentage=100")
        except Exception as e:
            out.append(f"  设置失败: {str(e)[:60]}")

    # ---- ④ 推进到"车接近路口"再抓帧 ----
    shots = []
    log = []
    for i in range(240):        # 12 秒
        world.tick()
        if i % 20 == 0:
            f = grab()
            if f is not None:
                p = os.path.join(OUT, f"A_view_t{i/20:04.1f}s.png")
                cv2.imwrite(p, f)
                shots.append((round(i / 20.0, 1), p))
            row = {"t": round(i / 20.0, 1)}
            for k, v in enumerate(spawned):
                try:
                    vel = v.get_velocity()
                    kmh = 3.6 * math.sqrt(vel.x**2 + vel.y**2 + vel.z**2)
                    row[f"v{k}"] = (round(kmh, 1), round(v.get_location().distance(jl), 1))
                except Exception:
                    pass
            log.append(row)

    out.append("")
    out.append(f"抓帧 {len(shots)} 张")
    out.append("")
    out.append("  时间 | 各车 (速度km/h, 距路口m)")
    for row in log:
        parts = [f"{k}=({v[0]},{v[1]})" for k, v in row.items() if k != "t"]
        out.append(f"   t={row['t']:>5}s | " + "  ".join(parts))

    # ---- ⑤ 估计车辆在画面里的可见性 ----
    out.append("")
    out.append("=" * 78)
    out.append("⑤ 车辆是否落在画面内（用投影估算）")
    out.append("=" * 78)
    f_px = RES[0] / (2.0 * math.tan(math.radians(70.0) / 2.0))
    cam_tf = cam.get_transform()

    def to_cam(P):
        inv = cam_tf.get_inverse_matrix()
        v = (P[0], P[1], P[2], 1.0)
        return tuple(sum(inv[i][j] * v[j] for j in range(4)) for i in range(4))

    def proj(P):
        p = to_cam(P)
        if p[0] <= 0.1:
            return None
        return (RES[0] / 2 + f_px * (p[1] / p[0]), RES[1] / 2 - f_px * (p[2] / p[0]))

    for k, v in enumerate(spawned):
        try:
            loc = v.get_location()
            pr = proj((loc.x, loc.y, loc.z + 0.8))
            if pr:
                inv = 0 <= pr[0] <= RES[0] and 0 <= pr[1] <= RES[1]
                out.append(f"   v{k} id={v.id:>3} 世界=({loc.x:7.1f},{loc.y:7.1f}) "
                           f"像素=({pr[0]:7.0f},{pr[1]:7.0f}) 在画面内={'✅' if inv else '❌'}")
            else:
                out.append(f"   v{k} id={v.id:>3} 在相机后方")
        except Exception:
            pass

    # 清理
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
    out.append("已清理（CARLA 窗口保持在方案 A 的机位）")

io.open(r"E:\output\_demo_redlight_planA.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
