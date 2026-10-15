"""CARLA 机位调优：多配置抓帧对比

目的：找出"能同时看到多辆车 + 俯拍监控感"的最佳机位。
上一版问题：pitch=-55°（太陡）+ back=18m -> 视野窄，且推进 6 秒后车都开走了。

本版策略：
  · 不再"推进 6 秒"，改为**推进 2 秒后立即抓**（车还在路口附近）
  · 生成更多车（12 辆）覆盖路口周边
  · 测试 3 组机位参数，每组抓 2 帧（不同时刻）
输出到 E:\\output\\_carla_frames\\tune\\ 便于逐一对比。
"""

import io
import math
import os
import queue

import carla

OUT_DIR = r"E:\output\_carla_frames\tune"
os.makedirs(OUT_DIR, exist_ok=True)
out = []

client = carla.Client("127.0.0.1", 2000)
client.set_timeout(30.0)
world = client.get_world()
bp_lib = world.get_blueprint_library()
m = world.get_map()
world.set_weather(carla.WeatherParameters.ClearNoon)

st = world.get_settings()
st.synchronous_mode = True
st.fixed_delta_seconds = 0.05
world.apply_settings(st)

# ---- 找路口 ----
spawn_points = m.get_spawn_points()
junction_sp = None
for sp in spawn_points:
    if m.get_waypoint(sp.location).is_junction:
        junction_sp = sp
        break
wp = m.get_waypoint(junction_sp.location)
jl = wp.transform.location
out.append(f"路口: ({jl.x:.1f}, {jl.y:.1f})")

# ---- 生成 12 辆车（路口周边最近的 spawn point）----
near = sorted(spawn_points, key=lambda p: p.location.distance(jl))[:16]
veh_bps = [b for b in bp_lib.filter("vehicle.*")
           if not any(k in b.id for k in ("bike", "harley", "crossbike", "kawasaki"))]
tm = client.get_trafficmanager(8000)
tm.set_synchronous_mode(True)
spawned = []
for i, sp in enumerate(near):
    if len(spawned) >= 12:
        break
    try:
        v = world.spawn_actor(veh_bps[i % len(veh_bps)], sp)
        v.set_autopilot(True, tm.get_port())
        spawned.append(v)
    except Exception:
        continue
out.append(f"生成 {len(spawned)} 辆车（autopilot）")

# 只推进 2 秒（让车动起来但仍在路口附近）
for _ in range(40):
    world.tick()
out.append("推进 2 秒")

# ---- 统计各车与路口的距离（判断谁在视野内）----
out.append("")
out.append("车辆位置（距路口距离）:")
for v in spawned:
    loc = v.get_location()
    d = math.sqrt((loc.x - jl.x) ** 2 + (loc.y - jl.y) ** 2)
    vel = v.get_velocity()
    kmh = 3.6 * math.sqrt(vel.x ** 2 + vel.y ** 2 + vel.z ** 2)
    out.append(f"   {v.type_id:26s} 距路口 {d:6.1f}m  {kmh:5.1f} km/h  "
               f"({loc.x:7.1f},{loc.y:7.1f})")

# ---- 3 组机位 ----
CONFIGS = [
    ("A_back30_pitch40", 30.0, -40.0, 20.0),   # 后退远、俯角缓 -> 视野宽
    ("B_back40_pitch35", 40.0, -35.0, 26.0),   # 更远更缓 -> 最宽
    ("C_back22_pitch50", 22.0, -50.0, 22.0),   # 近一点、陡一点 -> 特写感
]

cam_bp = bp_lib.find("sensor.camera.rgb")
cam_bp.set_attribute("image_size_x", "3840")
cam_bp.set_attribute("image_size_y", "2160")
cam_bp.set_attribute("fov", "70")
try:
    cam_bp.set_attribute("enable_postprocess_effects", "True")
except Exception:
    pass

cameras = []
for name, back, pitch, alt in CONFIGS:
    loc = carla.Location(x=jl.x - back, y=jl.y, z=jl.z + alt)
    rot = carla.Rotation(pitch=pitch, yaw=0.0, roll=0.0)
    cam = world.spawn_actor(cam_bp, carla.Transform(loc, rot))
    q = queue.Queue()
    cam.listen(q.put)
    cameras.append((name, cam, q, loc, rot))

out.append("")
out.append("=" * 76)
out.append("抓帧（每组 2 帧，间隔 2 秒仿真）")
out.append("=" * 76)

results = {}
for round_i in range(2):
    if round_i > 0:
        for _ in range(40):      # 再推进 2 秒
            world.tick()
    world.tick()
    for name, cam, q, loc, rot in cameras:
        try:
            img = q.get(timeout=20.0)
            p = os.path.join(OUT_DIR, f"{name}_r{round_i}.png")
            img.save_to_disk(p)
            results.setdefault(name, []).append(p)
            out.append(f"  {name} r{round_i}: ✅ {img.width}x{img.height} "
                       f"{os.path.getsize(p)/1024/1024:.1f}MB")
        except queue.Empty:
            out.append(f"  {name} r{round_i}: ❌ 超时")
        except Exception as e:
            out.append(f"  {name} r{round_i}: ❌ {type(e).__name__}: {str(e)[:80]}")

# ---- 抓完后立刻用 YOLO 数一下每组能看到几辆车 ----
out.append("")
out.append("=" * 76)
out.append("YOLO 快速统计（每组能检出几辆车 —— 这是选机位的硬指标）")
out.append("=" * 76)
import sys
sys.path.insert(0, r"E:\output\1\api")
os.chdir(r"E:\output\1\api")
import cv2
try:
    from image_recognizer import multi_model_detect
    for name, paths in results.items():
        for p in paths:
            img = cv2.imread(p)
            small = cv2.resize(img, (1280, int(img.shape[0] * 1280 / img.shape[1])),
                               interpolation=cv2.INTER_AREA)
            sp = p.replace(".png", "_1280.jpg")
            cv2.imwrite(sp, small, [cv2.IMWRITE_JPEG_QUALITY, 92])
            r = multi_model_detect(sp, conf_threshold=0.25)
            dets = r.get("all_detections", []) if r.get("success") else []
            veh = [d for d in dets if d.get("class_name") in
                   ("car", "truck", "bus", "motorcycle")]
            out.append(f"  {os.path.basename(p):28s} 车辆 {len(veh)} 辆  "
                       f"总检测 {len(dets)}  "
                       + " ".join(f"{d.get('class_name')}({d.get('confidence'):.2f})" for d in veh[:4]))
except Exception as e:
    out.append(f"  YOLO 统计失败: {type(e).__name__}: {str(e)[:150]}")

# ---- 清理 ----
for name, cam, q, loc, rot in cameras:
    try:
        cam.stop()
        cam.destroy()
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

io.open(r"E:\output\_carla_tune.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
