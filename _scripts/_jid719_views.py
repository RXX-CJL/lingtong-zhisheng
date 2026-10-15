"""junction 719 详细截图（用户选定候选 2，要求再看图确认）

用户要求：
  "2，先截个图给我看一下"
  "关于视频的录取需要我监督，现在我们需要确定路口是否有适合演示的斑马线"

本脚本对 junction_id=719 拍多角度图：
  ① 俯拍全景（看路口整体布局与斑马线）
  ② 中景（看斑马线 + 车道线 + 停止线）
  ③ 低角度（模拟真实监控机位，看标线细节）
同时输出该路口的结构化信息（road_id / lane 数 / 斑马线数量 / 红绿灯）
"""

import io
import math
import os
import queue

import carla

OUT = r"E:\output\_junction_survey"
os.makedirs(OUT, exist_ok=True)
out = []

client = carla.Client("127.0.0.1", 2000)
client.set_timeout(30.0)
world = client.get_world()
m = world.get_map()
bp = world.get_blueprint_library()
world.set_weather(carla.WeatherParameters.ClearNoon)

TARGET_JID = 719

# ---- 找该路口的中心 ----
jsp = None
for sp in m.get_spawn_points():
    wp = m.get_waypoint(sp.location)
    if wp.is_junction and wp.junction_id == TARGET_JID:
        jsp = sp
        break
if jsp is None:
    out.append(f"未找到 junction_id={TARGET_JID}")
else:
    jl = jsp.location
    out.append(f"junction_id={TARGET_JID}  位置=({jl.x:.1f},{jl.y:.1f},{jl.z:.1f})")

    # 结构化信息
    wp0 = m.get_waypoint(jl)
    out.append(f"  road_id={wp0.road_id}  lane_id={wp0.lane_id}")
    try:
        cws = m.get_crosswalks()
        near = [c for c in cws if math.hypot(c.x - jl.x, c.y - jl.y) < 60]
        out.append(f"  60m 内斑马线顶点: {len(near)}")
    except Exception:
        pass
    # 该路口涉及哪些车道
    lanes = set()
    for sp in m.get_spawn_points():
        w = m.get_waypoint(sp.location)
        if w.is_junction and w.junction_id == TARGET_JID:
            lanes.add((w.road_id, w.lane_id))
    out.append(f"  相关车道(road_id,lane_id): {sorted(lanes)}")

    # 红绿灯
    tls = [t for t in world.get_actors().filter("traffic.traffic_light*")
           if t.get_location().distance(jl) < 60]
    out.append(f"  60m 内红绿灯: {len(tls)} 个  ids={[t.id for t in tls]}")

    st = world.get_settings()
    st.synchronous_mode = True
    st.fixed_delta_seconds = 0.05
    world.apply_settings(st)

    import cv2
    import numpy as np

    cam_bp = bp.find("sensor.camera.rgb")
    cam_bp.set_attribute("image_size_x", "1920")
    cam_bp.set_attribute("image_size_y", "1080")
    cam_bp.set_attribute("fov", "70")

    # 三组机位
    VIEWS = [
        ("A_俯拍全景", (-30.0, 0.0, 24.0), -45.0),
        ("B_中景",     (-22.0, 0.0, 12.0), -32.0),
        ("C_低角度",   (-16.0, 0.0, 7.0),  -22.0),
    ]

    shots = []
    for name, (ox, oy, oz), pitch in VIEWS:
        cam_loc = carla.Location(x=jl.x + ox, y=jl.y + oy, z=jl.z + oz)
        yaw = math.degrees(math.atan2(jl.y - cam_loc.y, jl.x - cam_loc.x))
        try:
            cam = world.spawn_actor(cam_bp, carla.Transform(
                cam_loc, carla.Rotation(pitch=pitch, yaw=yaw, roll=0.0)))
        except Exception as e:
            out.append(f"  {name}: 相机失败 {str(e)[:50]}")
            continue
        q = queue.Queue()
        cam.listen(q.put)
        f = None
        for _ in range(6):
            world.tick()
        try:
            img = q.get(timeout=12.0)
            f = np.frombuffer(img.raw_data, dtype=np.uint8).reshape(
                (img.height, img.width, 4))[:, :, :3].copy()
        except queue.Empty:
            pass
        try:
            cam.stop(); cam.destroy()
        except Exception:
            pass
        if f is None:
            out.append(f"  {name}: 取帧失败")
            continue
        p = os.path.join(OUT, f"jid719_{name}.png")
        cv2.imwrite(p, f)
        shots.append((name, p))
        out.append(f"  {name}: 相机=({cam_loc.x:.1f},{cam_loc.y:.1f},{cam_loc.z:.1f}) "
                   f"pitch={pitch} -> {os.path.basename(p)}")

    st.synchronous_mode = False
    st.fixed_delta_seconds = None
    world.apply_settings(st)

    out.append("")
    out.append("截图:")
    for n, p in shots:
        out.append(f"  {n}: {p}")

io.open(r"E:\output\_jid719_views.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
