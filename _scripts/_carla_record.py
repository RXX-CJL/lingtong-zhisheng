"""CARLA 场景录制 —— 2K / 40 秒 / 含三种违规场景

目的（务必记住）：
  产出一段【车速真值已知 + 违规意图已知】的视频，用于
  ① 测速精度验证（真值 vs 项目实测）
  ② 误报检查（对照组正常车是否被误判）
  ③ 漏报检查（3 种违规是否被检出）

违规制造方式（可靠优先，不用不可靠的改灯时序）：
  · 违规停车：脚本车停在车道内 35 秒不动（autopilot 关闭）
      -> 这是**真违停**：车确实停在不该停的地方
  · 压线行驶：脚本车用 manual control 持续骑在车道线上行驶
      -> 画面里是真压线
  · 闯红灯：**红灯期间**脚本车保持前进通过路口
      -> 用 get_state() 实时判断是否红灯，只在红灯时给油门

对照组：12 辆车 autopilot 正常行驶（用来测误报）
"""

import csv
import io
import math
import os
import queue

import carla

OUT_DIR = r"E:\output\_carla_video"
os.makedirs(OUT_DIR, exist_ok=True)
VIDEO_PATH = os.path.join(OUT_DIR, "carla_scene_2k.mp4")
CSV_PATH = os.path.join(OUT_DIR, "ground_truth.csv")

FPS = 20
DURATION = 40
N_FRAMES = FPS * DURATION
RES = (2560, 1440)

out = []
client = carla.Client("127.0.0.1", 2000)
client.set_timeout(30.0)
world = client.get_world()
bp_lib = world.get_blueprint_library()
m = world.get_map()
world.set_weather(carla.WeatherParameters.ClearNoon)

st = world.get_settings()
st.synchronous_mode = True
st.fixed_delta_seconds = 1.0 / FPS
st.no_rendering_mode = False
world.apply_settings(st)
out.append(f"同步模式 @ {FPS}fps  dt={1.0/FPS:.4f}s  目标 {N_FRAMES} 帧")

# ---- 路口 ----
spawn_points = m.get_spawn_points()
junction_sp = next(sp for sp in spawn_points
                   if m.get_waypoint(sp.location).is_junction)
jl = m.get_waypoint(junction_sp.location).transform.location
out.append(f"路口: ({jl.x:.1f}, {jl.y:.1f})")

# ---- 对照组：12 辆车 autopilot ----
near = sorted(spawn_points, key=lambda p: p.location.distance(jl))[:18]
veh_bps = [b for b in bp_lib.filter("vehicle.*")
           if not any(k in b.id for k in ("bike", "harley", "crossbike", "kawasaki"))]
tm = client.get_trafficmanager(8000)
tm.set_synchronous_mode(True)
tm.set_global_distance_to_leading_vehicle(3.0)

normal = []
used = set()
for sp in near:
    if len(normal) >= 12:
        break
    key = (round(sp.location.x, 1), round(sp.location.y, 1))
    if key in used:
        continue
    used.add(key)
    try:
        v = world.spawn_actor(veh_bps[len(normal) % len(veh_bps)], sp)
        v.set_autopilot(True, tm.get_port())
        normal.append(v)
    except Exception:
        continue
out.append(f"对照组: {len(normal)} 辆车（autopilot）")

# ---- 违规车 C：违停（停 35 秒不动）----
parked = None
for sp in near[len(normal):]:
    key = (round(sp.location.x, 1), round(sp.location.y, 1))
    if key in used:
        continue
    try:
        parked = world.spawn_actor(bp_lib.filter("vehicle.dodge.charger_2020")[0], sp)
        parked.set_autopilot(False)
        parked.apply_control(carla.VehicleControl(throttle=0.0, brake=1.0, hand_brake=True))
        out.append(f"违规车C（违停）: id={parked.id} 位置=({sp.location.x:.1f},{sp.location.y:.1f})")
        break
    except Exception:
        continue

# ---- 违规车 B：压线（手动持续偏转）----
lane_veh = None
for sp in near[len(normal) + 1:]:
    try:
        lane_veh = world.spawn_actor(bp_lib.filter("vehicle.audi.tt")[0], sp)
        lane_veh.set_autopilot(False)
        out.append(f"违规车B（压线）: id={lane_veh.id}")
        break
    except Exception:
        continue

# ---- 违规车 A：闯红灯（红灯时保持前进）----
red_veh = None
for sp in near[len(normal) + 2:]:
    try:
        red_veh = world.spawn_actor(bp_lib.filter("vehicle.nissan.patrol")[0], sp)
        red_veh.set_autopilot(False)
        out.append(f"违规车A（闯红灯）: id={red_veh.id}")
        break
    except Exception:
        continue

# 推进 2 秒让车流启动
for _ in range(FPS * 2):
    world.tick()

# ---- 相机（B 配置）----
cam_bp = bp_lib.find("sensor.camera.rgb")
cam_bp.set_attribute("image_size_x", str(RES[0]))
cam_bp.set_attribute("image_size_y", str(RES[1]))
cam_bp.set_attribute("fov", "70")
cam_loc = carla.Location(x=jl.x - 40.0, y=jl.y, z=jl.z + 26.0)
cam = world.spawn_actor(cam_bp, carla.Transform(cam_loc, carla.Rotation(pitch=-35.0)))
q = queue.Queue()
cam.listen(q.put)
out.append(f"相机 {RES[0]}x{RES[1]} 位置=({cam_loc.x:.1f},{cam_loc.y:.1f},{cam_loc.z:.1f}) pitch=-35")

# ---- 录制 ----
out.append("")
out.append("=" * 74)
out.append(f"开始录制 {N_FRAMES} 帧")
out.append("=" * 74)

import cv2
writer = cv2.VideoWriter(VIDEO_PATH, cv2.VideoWriter_fourcc(*"mp4v"), FPS, RES)
rows = []
viol_log = []
red_frames = 0
lane_phase = 0
frames_written = 0

import numpy as np

for fi in range(N_FRAMES):
    # --- 违规车 A：闯红灯（红灯期间保持前进）---
    if red_veh is not None:
        try:
            loc = red_veh.get_location()
            d_j = math.sqrt((loc.x - jl.x) ** 2 + (loc.y - jl.y) ** 2)
            # 找最近的灯状态
            tl_state = None
            for tl in world.get_actors().filter("traffic.traffic_light*"):
                if tl.get_location().distance(loc) < 60:
                    tl_state = str(tl.get_state()).split(".")[-1]
                    break
            if tl_state == "Red" and d_j < 45:
                red_frames += 1
                red_veh.apply_control(carla.VehicleControl(throttle=0.55, steer=0.0))
                if red_frames == 1:
                    viol_log.append((fi / FPS, "red_light_start", f"id={red_veh.id} d={d_j:.1f}m"))
            elif d_j > 60:
                red_veh.apply_control(carla.VehicleControl(throttle=0.4))
        except Exception:
            pass

    # --- 违规车 B：压线（周期性打方向，让车骑线）---
    if lane_veh is not None:
        try:
            t = fi / FPS
            steer = 0.10 * math.sin(t * 1.2)      # 缓慢左右摆，形成骑线
            lane_veh.apply_control(carla.VehicleControl(throttle=0.45, steer=steer))
            if fi % (FPS * 5) == 0:
                viol_log.append((fi / FPS, "lane_weave", f"id={lane_veh.id} steer={steer:.3f}"))
        except Exception:
            pass

    # --- 违规车 C：保持停止（每帧重申刹车）---
    if parked is not None:
        try:
            parked.apply_control(carla.VehicleControl(throttle=0.0, brake=1.0, hand_brake=True))
        except Exception:
            pass

    world.tick()

    # --- 取帧 ---
    try:
        img = q.get(timeout=20.0)
        arr = np.frombuffer(img.raw_data, dtype=np.uint8)
        arr = arr.reshape((img.height, img.width, 4))[:, :, :3]
        writer.write(arr)
        frames_written += 1
    except queue.Empty:
        out.append(f"  帧 {fi}: 取帧超时")
        continue

    # --- 记录真值 ---
    ts = fi / FPS
    for tag, veh in (("normal", None),):
        pass
    for i, v in enumerate(normal):
        try:
            vel = v.get_velocity()
            kmh = 3.6 * math.sqrt(vel.x ** 2 + vel.y ** 2 + vel.z ** 2)
            loc = v.get_location()
            rows.append((round(ts, 3), f"normal_{i}", v.id, v.type_id,
                         round(kmh, 2), round(loc.x, 2), round(loc.y, 2), "normal"))
        except Exception:
            pass
    for tag, v in (("violation_parking", parked), ("violation_lane", lane_veh),
                   ("violation_redlight", red_veh)):
        if v is None:
            continue
        try:
            vel = v.get_velocity()
            kmh = 3.6 * math.sqrt(vel.x ** 2 + vel.y ** 2 + vel.z ** 2)
            loc = v.get_location()
            rows.append((round(ts, 3), tag, v.id, v.type_id,
                         round(kmh, 2), round(loc.x, 2), round(loc.y, 2), tag))
        except Exception:
            pass

    if (fi + 1) % (FPS * 5) == 0:
        out.append(f"  已录 {fi+1}/{N_FRAMES} 帧 ({(fi+1)/FPS:.0f}s)  "
                   f"写入 {frames_written}  违章车A红灯帧={red_frames}")

writer.release()

# ---- 写 CSV ----
with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["t_sec", "tag", "carla_id", "type_id", "speed_kmh", "x", "y", "role"])
    w.writerows(rows)

out.append("")
out.append("=" * 74)
out.append("录制完成")
out.append("=" * 74)
out.append(f"  视频: {VIDEO_PATH}  ({os.path.getsize(VIDEO_PATH)/1024/1024:.1f} MB, "
           f"{frames_written} 帧)")
out.append(f"  真值CSV: {CSV_PATH}  ({len(rows)} 行)")
out.append(f"  未渲染轮数: {N_FRAMES - frames_written}")
out.append("")
out.append("违规意图时间线（作为判定真值）:")
for t, kind, detail in viol_log[:20]:
    out.append(f"  t={t:6.2f}s  {kind:18s} {detail}")
out.append("")
out.append(f"闯红灯场景: 车A 在红灯且距路口<45m 时保持前进，共 {red_frames} 帧 "
           f"({red_frames/FPS:.1f}s)")

# 统计真值速度范围
sp = [r[4] for r in rows if r[7] == "normal"]
if sp:
    out.append("")
    out.append(f"对照组真值速度: min={min(sp):.1f} max={max(sp):.1f} "
               f"avg={sum(sp)/len(sp):.1f} km/h （{len(sp)} 采样）")

# ---- 清理 ----
try:
    cam.stop()
    cam.destroy()
except Exception:
    pass
for v in normal + [x for x in (parked, lane_veh, red_veh) if x is not None]:
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

io.open(r"E:\output\_carla_record.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
