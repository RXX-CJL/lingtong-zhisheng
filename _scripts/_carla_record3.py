"""CARLA 简单场景录制 v3 —— 用户要求的"单车、低机位、明显违规"

用户反馈（原话要点）：
  · "视频似乎没有什么动作（没有体现明显的违规现象，却检测出频繁的抓拍）"
  · "时间不用太长，车辆不用太多，只需要一辆车没有违规，另一辆有闯红灯"
  · "摄像机角度不用那么高，可以参考现实中真实的交通摄像头高度和角度"

本场景设计：
  · 相机 7m 高、俯角 -22°、距路口 18m  ← 贴近真实路口监控
  · 2 辆车：A 正常通过（绿灯）、B 闯红灯（红灯时通过）
  · 红灯用 set_state 确定置红（已验证稳定）
  · 15 秒 / 20fps = 300 帧
  · 恒定速度控制器（精确控速 -> 真值可靠）
  · 真值 CSV 记录：速度 + 世界坐标 + 像素 bbox（投影公式已验证）
"""

import csv
import io
import math
import os
import queue

import carla

OUT = r"E:\output\_carla_video3"
os.makedirs(OUT, exist_ok=True)
VIDEO = os.path.join(OUT, "carla_simple_28s.mp4")
CSV_P = os.path.join(OUT, "ground_truth.csv")

FPS, DUR = 20, 28      # 2026-10-04: 15 -> 28 秒（车需要时间开进画面）
N = FPS * DUR
W, H, FOV = 2560, 1440, 70.0
CAM_H, CAM_PITCH, CAM_BACK = 7.0, -22.0, 18.0
NORMAL_KMH, RED_KMH = 30.0, 35.0

out = []
client = carla.Client("127.0.0.1", 2000)
client.set_timeout(30.0)
world = client.get_world()
bp = world.get_blueprint_library()
m = world.get_map()
world.set_weather(carla.WeatherParameters.ClearNoon)

st = world.get_settings()
st.synchronous_mode = True
st.fixed_delta_seconds = 1.0 / FPS
world.apply_settings(st)
out.append(f"同步 {FPS}fps  {N} 帧  相机 {CAM_H}m / pitch {CAM_PITCH}° / 距路口 {CAM_BACK}m")

# ---- 找路口与进入路口的车道 ----
sps = m.get_spawn_points()
jsp = next(s for s in sps if m.get_waypoint(s.location).is_junction)
jw = m.get_waypoint(jsp.location)
jl = jw.transform.location
out.append(f"路口 ({jl.x:.1f},{jl.y:.1f})  road_id={jw.road_id} lane={jw.lane_id}")

# 找同一条路上、路口之前的 spawn point（用于放置两辆车，使其朝路口行驶）
same_road = []
for s in sps:
    w = m.get_waypoint(s.location)
    if w.road_id == jw.road_id and not w.is_junction:
        d = s.location.distance(jl)
        same_road.append((d, s))
same_road.sort(key=lambda x: x[0])
out.append(f"同路非路口 spawn: {len(same_road)} 个，最近 {same_road[0][0]:.1f}m" if same_road else "无")

if len(same_road) < 2:
    out.append("⚠ 同路点不足，放宽为任意非路口点")
    same_road = sorted([(s.location.distance(jl), s) for s in sps
                        if not m.get_waypoint(s.location).is_junction],
                       key=lambda x: x[0])

# ---- 相机 ----
cam_bp = bp.find("sensor.camera.rgb")
cam_bp.set_attribute("image_size_x", str(W))
cam_bp.set_attribute("image_size_y", str(H))
cam_bp.set_attribute("fov", str(FOV))
cam_tf_obj = carla.Transform(
    carla.Location(x=jl.x - CAM_BACK, y=jl.y, z=jl.z + CAM_H),
    carla.Rotation(pitch=CAM_PITCH))
cam = world.spawn_actor(cam_bp, cam_tf_obj)
cam_tf = cam.get_transform()
out.append(f"相机位 ({cam_tf_obj.location.x:.1f},{cam_tf_obj.location.y:.1f},{cam_tf_obj.location.z:.1f})")

f_px = W / (2.0 * math.tan(math.radians(FOV) / 2.0))


def _to_cam(loc):
    """世界坐标 -> 相机坐标系

    注意（2026-10-04 踩坑）：CARLA 的 `get_inverse_matrix()` 返回的是
    **Python list**，不是矩阵对象，因此 `inv @ loc` 会抛
        TypeError: unsupported operand type(s) for @: 'list' and 'Location'
    必须手动做 4x4 矩阵乘。这是 v2/v3 CSV 全空的真因。
    """
    inv = cam_tf.get_inverse_matrix()
    v = (loc.x, loc.y, loc.z, 1.0)
    return tuple(sum(inv[i][j] * v[j] for j in range(4)) for i in range(4))


def project(loc):
    p = _to_cam(loc)
    if p[0] <= 1e-3:
        return None
    return (W / 2.0 + f_px * (p[1] / p[0]), H / 2.0 - f_px * (p[2] / p[0]))


def veh_bbox(veh):
    b = veh.bounding_box
    t = veh.get_transform()
    us, vs = [], []
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                wl = t.transform(carla.Location(x=sx * b.extent.x, y=sy * b.extent.y,
                                                z=sz * b.extent.z) + b.location)
                pr = project(wl)
                if pr:
                    us.append(pr[0]); vs.append(pr[1])
    return (min(us), min(vs), max(us), max(vs)) if us else None


# ---- 生成 2 辆车 ----
vbp = bp.filter("vehicle.audi.a2")[0]
vA = vB = None
try:
    vA = world.spawn_actor(vbp, same_road[0][1])
    out.append(f"车A（正常）id={vA.id} @ 距路口 {same_road[0][0]:.1f}m")
except Exception as e:
    out.append(f"车A 生成失败: {str(e)[:60]}")
try:
    idx = min(1, len(same_road) - 1)
    vB = world.spawn_actor(vbp, same_road[idx][1])
    out.append(f"车B（闯红灯）id={vB.id} @ 距路口 {same_road[idx][0]:.1f}m")
except Exception as e:
    out.append(f"车B 生成失败: {str(e)[:60]}")

for _ in range(10):
    world.tick()

# ---- 红绿灯：置红（已验证稳定）----
near_tl = None
best = 1e9
for tl in world.get_actors().filter("traffic.traffic_light*"):
    d = tl.get_location().distance(jl)
    if d < best:
        best, near_tl = d, tl
if near_tl:
    near_tl.set_state(carla.TrafficLightState.Red)
    for _ in range(10):
        world.tick()
    out.append(f"已把最近红绿灯(id={near_tl.id}, 距路口 {best:.1f}m) 置为 "
               f"{str(near_tl.get_state()).split('.')[-1]}")

# ---- 录制 ----
q = queue.Queue()
cam.listen(q.put)

import cv2
import numpy as np

writer = cv2.VideoWriter(VIDEO, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
rows = []
tl_history = []


def hold_speed(veh, kmh):
    """恒定速度控制（精确控速，真值可靠）"""
    try:
        veh.enable_constant_velocity(carla.Vector3D(x=kmh / 3.6, y=0.0, z=0.0))
    except Exception:
        veh.apply_control(carla.VehicleControl(throttle=0.5))


for fi in range(N):
    # 前 4 秒绿灯放行 A；之后保持红灯，B 继续通过 -> 闯红灯
    if near_tl:
        if fi < FPS * 4:
            near_tl.set_state(carla.TrafficLightState.Green)
        else:
            near_tl.set_state(carla.TrafficLightState.Red)
        tl_history.append((round(fi / FPS, 2),
                           str(near_tl.get_state()).split(".")[-1]))

    if vA:
        hold_speed(vA, NORMAL_KMH)
    if vB:
        hold_speed(vB, RED_KMH)

    world.tick()

    try:
        img = q.get(timeout=20.0)
        arr = np.frombuffer(img.raw_data, dtype=np.uint8).reshape(
            (img.height, img.width, 4))[:, :, :3]
        writer.write(arr)
    except queue.Empty:
        out.append(f"  帧 {fi} 超时")
        continue

    ts = fi / FPS
    for tag, v in (("normal", vA), ("red_runner", vB)):
        if v is None:
            continue
        try:
            vel = v.get_velocity()
            kmh = 3.6 * math.sqrt(vel.x ** 2 + vel.y ** 2 + vel.z ** 2)
            loc = v.get_location()
            bb = veh_bbox(v)
            inv = 0
            bbs = ""
            if bb:
                u1, v1, u2, v2 = bb
                cu, cvv = (u1 + u2) / 2, (v1 + v2) / 2
                inv = int(0 <= cu <= W and 0 <= cvv <= H and u2 > 0 and u1 < W)
                bbs = f"{u1:.0f};{v1:.0f};{u2:.0f};{v2:.0f}"
            rows.append((round(ts, 3), tag, v.id, round(kmh, 2),
                         round(loc.x, 2), round(loc.y, 2), inv, bbs))
        except Exception:
            pass

    if (fi + 1) % (FPS * 3) == 0:
        n_in = sum(1 for r in rows[-2 * FPS * 3:] if r[6] == 1)
        out.append(f"  {fi+1}/{N} 帧  近 3 秒视野内样本 {n_in}")

writer.release()
try:
    if vA:
        vA.disable_constant_velocity()
    if vB:
        vB.disable_constant_velocity()
except Exception:
    pass

with open(CSV_P, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["t_sec", "tag", "carla_id", "speed_kmh", "x", "y", "in_view", "px_bbox"])
    w.writerows(rows)

out.append("")
out.append("=" * 74)
out.append("录制完成")
out.append("=" * 74)
out.append(f"  视频 {VIDEO}  ({os.path.getsize(VIDEO)/1024/1024:.1f} MB, {N} 帧)")
out.append(f"  真值 {CSV_P}  ({len(rows)} 行)")

# 红绿灯时间线
if tl_history:
    changes = [tl_history[0]]
    for i in range(1, len(tl_history)):
        if tl_history[i][1] != tl_history[i - 1][1]:
            changes.append(tl_history[i])
    out.append("")
    out.append("  红绿灯状态变化:")
    for t, s in changes[:8]:
        out.append(f"    t={t:5.2f}s -> {s}")

out.append("")
out.append("  有效样本（视野内 + 速度>5km/h）:")
for tag in ("normal", "red_runner"):
    vv = [r for r in rows if r[1] == tag and r[6] == 1 and r[3] > 5]
    if vv:
        sp = [r[3] for r in vv]
        out.append(f"    {tag:12s} {len(vv):>4} 样本  avg={sum(sp)/len(sp):5.1f} "
                   f"max={max(sp):5.1f} km/h")

# 清理
try:
    cam.stop(); cam.destroy()
except Exception:
    pass
for v in (vA, vB):
    if v:
        try:
            v.destroy()
        except Exception:
            pass
st.synchronous_mode = False
st.fixed_delta_seconds = None
world.apply_settings(st)
out.append("")
out.append("已清理")

io.open(r"E:\output\_carla_record3.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
