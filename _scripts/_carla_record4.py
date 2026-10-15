"""CARLA 演示视频 v4 —— 相机放到能看见【红绿灯灯面】的方位

背景（本次调查结论）：
  · CARLA 红绿灯**确实会发光变色**（用户判断正确，罗盘图 +Y 方向可见绿灯发光）
  · 我此前录的两个视频里，相机都在灯的**背面/侧面** -> 画面里只有黄色外壳
    -> CNN 判 yellow 是**对的**，问题在机位
  · 因此本版把相机放到 +Y 侧（罗盘图证明该方向能看到灯面）

本版同时保留此前验证过的要素：
  · 相机 7m 高、俯角 -22°（贴近真实路口监控，用户要求"参考真实摄像头高度角度"）
  · 28 秒（车需要时间开进画面，实测 15 秒太短）
  · 2 辆车：A 绿灯通过、B 红灯通过（闯红灯）
  · 红灯用 set_state 确定置红（已验证：同步模式下保持）
  · 同步 20fps；真值 CSV 记录速度 + 世界坐标 + 像素 bbox
"""

import csv
import io
import math
import os
import queue

import carla

OUT = r"E:\output\_carla_video4"
os.makedirs(OUT, exist_ok=True)
VIDEO = os.path.join(OUT, "carla_tl_face_28s.mp4")
CSV_P = os.path.join(OUT, "ground_truth.csv")

FPS, DUR = 20, 28
N = FPS * DUR
W, H, FOV = 2560, 1440, 70.0
CAM_H, CAM_PITCH = 7.0, -22.0
# 关键：相机放在路口 +Y 侧（罗盘图证明该方向能看到灯面）
CAM_OFF_X, CAM_OFF_Y = -18.0, 26.0
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
out.append(f"同步 {FPS}fps  {N} 帧  相机 {CAM_H}m / pitch {CAM_PITCH}°")

sps = m.get_spawn_points()
jsp = next(s for s in sps if m.get_waypoint(s.location).is_junction)
jw = m.get_waypoint(jsp.location)
jl = jw.transform.location
out.append(f"路口 ({jl.x:.1f},{jl.y:.1f})")

# ---- 相机：+Y 侧，朝向路口 ----
cam_loc = carla.Location(x=jl.x + CAM_OFF_X, y=jl.y + CAM_OFF_Y, z=jl.z + CAM_H)
dx = jl.x - cam_loc.x
dy = jl.y - cam_loc.y
yaw = math.degrees(math.atan2(dy, dx))
cam_rot = carla.Rotation(pitch=CAM_PITCH, yaw=yaw, roll=0.0)
cam_bp = bp.find("sensor.camera.rgb")
cam_bp.set_attribute("image_size_x", str(W))
cam_bp.set_attribute("image_size_y", str(H))
cam_bp.set_attribute("fov", str(FOV))
cam = world.spawn_actor(cam_bp, carla.Transform(cam_loc, cam_rot))
cam_tf = cam.get_transform()
out.append(f"相机=({cam_loc.x:.1f},{cam_loc.y:.1f},{cam_loc.z:.1f})  yaw={yaw:.1f}（朝向路口）")

f_px = W / (2.0 * math.tan(math.radians(FOV) / 2.0))


def _to_cam(loc):
    """世界 -> 相机坐标（注意 get_inverse_matrix 返回 Python list，不能用 @）"""
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
                wl = carla.Location(x=sx * b.extent.x, y=sy * b.extent.y,
                                    z=sz * b.extent.z) + b.location
                wl = t.location + t.transform(wl)          # 正确的"局部->世界"
                pr = project(wl)
                if pr:
                    us.append(pr[0]); vs.append(pr[1])
    return (min(us), min(vs), max(us), max(vs)) if us else None


# ---- 记录红绿灯在画面中的位置与状态（复核判色用）----
tl_rows = []
for tl in world.get_actors().filter("traffic.traffic_light*"):
    lbs = tl.get_light_boxes()
    if not lbs:
        continue
    lamp = sorted(lbs, key=lambda b: b.extent.x * b.extent.y * b.extent.z)[0]
    pr = project(lamp.location)
    tl_rows.append({
        "id": tl.id,
        "loc": (round(lamp.location.x, 2), round(lamp.location.y, 2), round(lamp.location.z, 2)),
        "px": (round(pr[0]), round(pr[1])) if pr else None,
        "in_view": bool(pr and 0 <= pr[0] <= W and 0 <= pr[1] <= H),
    })
n_iv = sum(1 for r in tl_rows if r["in_view"])
out.append(f"红绿灯 {len(tl_rows)} 个，其中**在画面内** {n_iv} 个")
for r in tl_rows:
    if r["in_view"]:
        out.append(f"   id={r['id']} 世界={r['loc']} 像素={r['px']}")

# ---- 车辆 ----
vbp = bp.filter("vehicle.audi.a2")[0]
same_road = sorted([(s.location.distance(jl), s) for s in sps
                    if not m.get_waypoint(s.location).is_junction], key=lambda x: x[0])
vA = vB = None
try:
    vA = world.spawn_actor(vbp, same_road[0][1])
    out.append(f"车A（正常）id={vA.id}")
except Exception as e:
    out.append(f"车A 失败: {str(e)[:50]}")
try:
    vB = world.spawn_actor(vbp, same_road[min(1, len(same_road) - 1)][1])
    out.append(f"车B（闯红灯）id={vB.id}")
except Exception as e:
    out.append(f"车B 失败: {str(e)[:50]}")

for _ in range(10):
    world.tick()

# 最近的灯置红
near_tl, best = None, 1e9
for tl in world.get_actors().filter("traffic.traffic_light*"):
    d = tl.get_location().distance(jl)
    if d < best:
        best, near_tl = d, tl
if near_tl:
    near_tl.set_state(carla.TrafficLightState.Green)
    for _ in range(10):
        world.tick()
    out.append(f"最近灯 id={near_tl.id}（距路口 {best:.1f}m）初始置为 Green")

# ---- 录制 ----
q = queue.Queue()
cam.listen(q.put)

import cv2
import numpy as np

writer = cv2.VideoWriter(VIDEO, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
rows = []
tl_hist = []


def hold(veh, kmh):
    try:
        veh.enable_constant_velocity(carla.Vector3D(x=kmh / 3.6, y=0.0, z=0.0))
    except Exception:
        veh.apply_control(carla.VehicleControl(throttle=0.5))


for fi in range(N):
    if near_tl:
        stv = carla.TrafficLightState.Green if fi < FPS * 4 else carla.TrafficLightState.Red
        near_tl.set_state(stv)
        tl_hist.append((round(fi / FPS, 2), str(near_tl.get_state()).split(".")[-1]))
    if vA:
        hold(vA, NORMAL_KMH)
    if vB:
        hold(vB, RED_KMH)

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

    if (fi + 1) % (FPS * 7) == 0:
        nv = sum(1 for r in rows[-2 * FPS * 7:] if r[6] == 1)
        out.append(f"  {fi+1}/{N} 帧  近 7 秒视野内样本 {nv}")

writer.release()
try:
    if vA: vA.disable_constant_velocity()
    if vB: vB.disable_constant_velocity()
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
if tl_hist:
    ch = [tl_hist[0]]
    for i in range(1, len(tl_hist)):
        if tl_hist[i][1] != tl_hist[i - 1][1]:
            ch.append(tl_hist[i])
    out.append("  红绿灯状态变化:")
    for t, s in ch[:8]:
        out.append(f"    t={t:6.2f}s -> {s}")
out.append("")
out.append("  有效样本（视野内 + >5km/h）:")
for tag in ("normal", "red_runner"):
    vv = [r for r in rows if r[1] == tag and r[6] == 1 and r[3] > 5]
    if vv:
        sp = [r[3] for r in vv]
        out.append(f"    {tag:12s} {len(vv):>4} 样本  avg={sum(sp)/len(sp):5.1f} "
                   f"max={max(sp):5.1f} km/h")

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

io.open(r"E:\output\_carla_record4.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
