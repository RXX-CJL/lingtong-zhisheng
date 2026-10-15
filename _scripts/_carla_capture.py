"""CARLA 4K 抓帧 + 路口场景编排

目标（两步验证）：
  1. 4K (3840x2160) Epic 画质下能否成功抓帧
  2. 抓到的画面里"车看起来像车吗"（后续喂 YOLO 验证）

场景设计（俯拍路口监控视角）：
  · 找一个路口（is_junction 的 spawn point）
  · 路口附近生成 6 辆车（不同车道/朝向）
  · 相机架在路口上方，向下倾斜 55°，能够俯视整个路口
  · 分辨率 3840x2160，PNG 输出（无损，便于 YOLO 与人工核对）
"""

import io
import math
import os
import queue
import time

import carla

OUT_DIR = r"E:\output\_carla_frames"
os.makedirs(OUT_DIR, exist_ok=True)
out = []

client = carla.Client("127.0.0.1", 2000)
client.set_timeout(30.0)
world = client.get_world()
bp_lib = world.get_blueprint_library()
m = world.get_map()

# 天气：晴好（能见度高，演示好看）
world.set_weather(carla.WeatherParameters.ClearNoon)

# 同步模式（精确控制）
st = world.get_settings()
st.synchronous_mode = True
st.fixed_delta_seconds = 0.05
world.apply_settings(st)
out.append(f"同步模式 dt={st.fixed_delta_seconds}s")

# ---- 找路口 ----
spawn_points = m.get_spawn_points()
junction_sp = None
for sp in spawn_points:
    wp = m.get_waypoint(sp.location)
    if wp.is_junction:
        junction_sp = sp
        break
if junction_sp is None:
    junction_sp = spawn_points[0]
wp = m.get_waypoint(junction_sp.location)
jl = wp.transform.location
out.append(f"路口位置: ({jl.x:.1f}, {jl.y:.1f}, {jl.z:.1f})  is_junction={wp.is_junction}")

# ---- 在路口附近生成车辆 ----
# 取该路口周围若干 spawn point，按距离排序取近的
near = sorted(spawn_points, key=lambda p: p.location.distance(jl))[:10]
veh_bps = [b for b in bp_lib.filter("vehicle.*")
           if "bike" not in b.id and "harley" not in b.id and "crossbike" not in b.id]

spawned = []
tm = client.get_trafficmanager(8000)
tm.set_synchronous_mode(True)
for i, sp in enumerate(near):
    if len(spawned) >= 6:
        break
    bp = veh_bps[i % len(veh_bps)]
    try:
        v = world.spawn_actor(bp, sp)
        v.set_autopilot(True, tm.get_port())      # 让它们自己动起来
        spawned.append(v)
    except Exception:
        continue

out.append(f"已生成 {len(spawned)} 辆车（autopilot 开启，会自己行驶）")
for v in spawned:
    out.append(f"   {v.type_id}  id={v.id}")

# 推进让车辆进入路口、动起来
for _ in range(120):
    world.tick()
out.append("已推进 6 秒仿真（车辆开始行驶）")

# ---- 架相机（俯拍路口）----
cam_bp = bp_lib.find("sensor.camera.rgb")
RES = (3840, 2160)
cam_bp.set_attribute("image_size_x", str(RES[0]))
cam_bp.set_attribute("image_size_y", str(RES[1]))
cam_bp.set_attribute("fov", "70")
cam_bp.set_attribute("sensor_tick", "0.0")
try:
    cam_bp.set_attribute("enable_postprocess_effects", "True")
except Exception:
    pass

# 相机位置：路口上方 22m，向后偏 18m，向下俯 55°
alt = 22.0
back = 18.0
cam_loc = carla.Location(x=jl.x - back, y=jl.y, z=jl.z + alt)
cam_rot = carla.Rotation(pitch=-55.0, yaw=0.0, roll=0.0)

camera = world.spawn_actor(cam_bp, carla.Transform(cam_loc, cam_rot))
out.append(f"相机: {RES[0]}x{RES[1]}  fov=70  位置=({cam_loc.x:.1f},{cam_loc.y:.1f},{cam_loc.z:.1f})  "
           f"pitch={cam_rot.pitch}")

q = queue.Queue()
camera.listen(q.put)

# 抓帧
out.append("")
out.append("=" * 74)
out.append("抓帧尝试")
out.append("=" * 74)
ok = False
for attempt in range(6):
    try:
        world.tick()
        img = q.get(timeout=15.0)
        p = os.path.join(OUT_DIR, f"carla_junction_4k_{attempt}.png")
        img.save_to_disk(p)
        size_mb = os.path.getsize(p) / 1024 / 1024
        out.append(f"  尝试 {attempt+1}: ✅ 成功  {img.width}x{img.height}  "
                   f"{size_mb:.1f}MB  -> {os.path.basename(p)}")
        ok = True
        break
    except queue.Empty:
        out.append(f"  尝试 {attempt+1}: ❌ 15 秒内没拿到帧（可能显存不足/OOM）")
    except Exception as e:
        out.append(f"  尝试 {attempt+1}: ❌ {type(e).__name__}: {str(e)[:120]}")

out.append("")
out.append(f"4K 抓帧结论: {'✅ 可行' if ok else '❌ 不可行'}")

# ---- 如果 4K 失败，退回 2K 再试 ----
if not ok:
    out.append("")
    out.append("退回 2560x1440 重试...")
    try:
        camera.destroy()
    except Exception:
        pass
    cam_bp2 = bp_lib.find("sensor.camera.rgb")
    cam_bp2.set_attribute("image_size_x", "2560")
    cam_bp2.set_attribute("image_size_y", "1440")
    cam_bp2.set_attribute("fov", "70")
    camera = world.spawn_actor(cam_bp2, carla.Transform(cam_loc, cam_rot))
    q2 = queue.Queue()
    camera.listen(q2.put)
    for attempt in range(6):
        try:
            world.tick()
            img = q2.get(timeout=15.0)
            p = os.path.join(OUT_DIR, f"carla_junction_2k_{attempt}.png")
            img.save_to_disk(p)
            out.append(f"  尝试 {attempt+1}: ✅ {img.width}x{img.height}  "
                       f"{os.path.getsize(p)/1024/1024:.1f}MB")
            ok = True
            break
        except Exception as e:
            out.append(f"  尝试 {attempt+1}: ❌ {type(e).__name__}")

# ---- 记录车辆真值速度（后续测速验证用）----
out.append("")
out.append("车辆真值速度（CARLA API 读出，可作测速真值）:")
for v in spawned[:6]:
    vel = v.get_velocity()
    kmh = 3.6 * math.sqrt(vel.x ** 2 + vel.y ** 2 + vel.z ** 2)
    loc = v.get_location()
    out.append(f"   {v.type_id:28s} {kmh:6.2f} km/h  位置=({loc.x:7.1f},{loc.y:7.1f})")

# ---- 清理 ----
try:
    camera.stop()
    camera.destroy()
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
out.append("已清理相机与车辆，恢复异步模式")

io.open(r"E:\output\_carla_capture.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
