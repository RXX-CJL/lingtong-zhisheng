"""CARLA 场景录制 v2 —— 车辆在【视野内】持续行驶

v1 的问题（实测发现）：
  让 12 辆车 autopilot 自由行驶 -> 它们开出了视野；
  留在画面里的多是怠速/停车的车 -> 实测 px/s 只有 0.13~1.39，
  而真值有 6.5~26.6 km/h -> 差 10~100 倍，根本没有有效速度样本，
  导致「标定准不准」这个问题无法判定。

v2 的修正：
  ① 车辆**在视野内的道路上持续移动**（用固定速度沿路段往返）
  ② 每帧记录**【是否在画面内】+【像素 bbox】**（用已验证的投影公式）
  ③ 真值 CSV 增加 in_view / px_bbox 列 -> 只比对视野内的样本

投影公式已独立验证：库函数与我的实现完全一致（y=720 处 ppm=23.1）。
"""

import csv
import io
import math
import os
import queue

import carla

OUT_DIR = r"E:\output\_carla_video2"
os.makedirs(OUT_DIR, exist_ok=True)
VIDEO = os.path.join(OUT_DIR, "carla_loop_2k.mp4")
CSV_PATH = os.path.join(OUT_DIR, "ground_truth.csv")

FPS = 20
DURATION = 30
N = FPS * DURATION
W, H, FOV = 2560, 1440, 70.0
CAM_H, CAM_PITCH = 26.0, -35.0

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
out.append(f"同步 {FPS}fps  {N} 帧  画面 {W}x{H}")

# ---- 相机 ----
sp_all = m.get_spawn_points()
jsp = next(s for s in sp_all if m.get_waypoint(s.location).is_junction)
jl = m.get_waypoint(jsp.location).transform.location
cam_bp = bp.find("sensor.camera.rgb")
cam_bp.set_attribute("image_size_x", str(W))
cam_bp.set_attribute("image_size_y", str(H))
cam_bp.set_attribute("fov", str(FOV))
cam_transform = carla.Transform(
    carla.Location(x=jl.x - 40.0, y=jl.y, z=jl.z + CAM_H),
    carla.Rotation(pitch=CAM_PITCH))
cam = world.spawn_actor(cam_bp, cam_transform)
cam_tf = cam.get_transform()
out.append(f"路口 ({jl.x:.1f},{jl.y:.1f})  相机 z={jl.z+CAM_H:.1f} pitch={CAM_PITCH}")

# ---- 投影（公式已验证）----
f_px = W / (2.0 * math.tan(math.radians(FOV) / 2.0))


def project(loc):
    inv = cam_tf.get_inverse_matrix()
    p = inv @ loc
    if p[0] <= 1e-3:
        return None
    u = W / 2.0 + f_px * (p[1] / p[0])
    v = H / 2.0 - f_px * (p[2] / p[0])
    return (u, v)


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
                    us.append(pr[0])
                    vs.append(pr[1])
    if not us:
        return None
    return (min(us), min(vs), max(us), max(vs))


# ---- 选一条"穿过视野"的路段：沿 x 轴的路，从 x=-100 到 x=-20 ----
# 用路口附近的 waypoint 找一条直线
wp0 = m.get_waypoint(jl)
road_wps = []
cur = wp0
for _ in range(60):
    nxt = cur.next(6.0)
    if not nxt:
        break
    cur = nxt[0]
    road_wps.append(cur)
out.append(f"沿路采样点 {len(road_wps)} 个")
if len(road_wps) >= 8:
    s0 = road_wps[0].transform.location
    s1 = road_wps[-1].transform.location
    out.append(f"  起点 ({s0.x:.1f},{s0.y:.1f}) -> 终点 ({s1.x:.1f},{s1.y:.1f})")

# ---- 生成车辆：沿该路段起点放，手动控制往返 ----
veh_bps = [b for b in bp.filter("vehicle.*")
           if not any(k in b.id for k in ("bike", "harley", "crossbike", "kawasaki"))]
vehs = []
for i in range(4):
    if i >= len(road_wps):
        break
    wpt = road_wps[min(i * 2, len(road_wps) - 1)]
    tf = wpt.transform
    tf.location.z += 0.6
    try:
        v = world.spawn_actor(veh_bps[i % len(veh_bps)], tf)
        v.set_autopilot(False)
        vehs.append({"veh": v, "dir": 1 if i % 2 == 0 else -1,
                     "speed": [0.30, 0.20, 0.40, 0.25][i % 4]})
    except Exception as e:
        out.append(f"  生成 {i} 失败: {str(e)[:50]}")
out.append(f"生成 {len(vehs)} 辆车（手动控制，沿路往返）")

# ---- 录制 ----
q = queue.Queue()
cam.listen(q.put)

import cv2
import numpy as np

writer = cv2.VideoWriter(VIDEO, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
rows = []
n_in_view = 0
n_moving = 0

for fi in range(N):
    # 控制：到达路段端点则掉头
    for it in vehs:
        v = it["veh"]
        try:
            loc = v.get_location()
            # 用与路段起终点的投影距离判断是否该掉头
            if len(road_wps) >= 8:
                a = road_wps[0].transform.location
                b = road_wps[-1].transform.location
                ax = (loc.x - a.x) * (b.x - a.x) + (loc.y - a.y) * (b.y - a.y)
                L2 = (b.x - a.x) ** 2 + (b.y - a.y) ** 2
                prog = ax / L2 if L2 > 1 else 0.5
                if prog > 0.92:
                    it["dir"] = -1
                elif prog < 0.08:
                    it["dir"] = 1
            # 简单控制：给固定油门 + 用 waypoint 方向把正车头
            v.apply_control(carla.VehicleControl(
                throttle=it["speed"] if it["dir"] > 0 else 0.0,
                brake=0.0 if it["dir"] > 0 else 0.35,
                reverse=(it["dir"] < 0),
                steer=0.0))
        except Exception:
            pass

    world.tick()

    try:
        img = q.get(timeout=20.0)
        arr = np.frombuffer(img.raw_data, dtype=np.uint8).reshape(
            (img.height, img.width, 4))[:, :, :3]
        writer.write(arr)
    except queue.Empty:
        out.append(f"  帧 {fi} 取帧超时")
        continue

    ts = fi / FPS
    for i, it in enumerate(vehs):
        v = it["veh"]
        try:
            vel = v.get_velocity()
            kmh = 3.6 * math.sqrt(vel.x ** 2 + vel.y ** 2 + vel.z ** 2)
            bb = veh_bbox(v)
            in_view = False
            bb_str = ""
            if bb:
                u1, v1, u2, v2 = bb
                in_view = (u2 > 0 and u1 < W and v2 > 0 and v1 < H)
                # 中心是否真的在画面内
                cu, cvv = (u1 + u2) / 2, (v1 + v2) / 2
                in_view = in_view and (0 <= cu <= W) and (0 <= cvv <= H)
                bb_str = f"{u1:.0f};{v1:.0f};{u2:.0f};{v2:.0f}"
            if in_view:
                n_in_view += 1
                if kmh > 5:
                    n_moving += 1
            rows.append((round(ts, 3), f"veh_{i}", v.id, v.type_id,
                         round(kmh, 2), round(v.get_location().x, 2),
                         round(v.get_location().y, 2), int(in_view), bb_str))
        except Exception:
            pass

    if (fi + 1) % (FPS * 5) == 0:
        out.append(f"  {fi+1}/{N} 帧  视野内样本 {n_in_view}  其中运动中(>5km/h) {n_moving}")

writer.release()

with open(CSV_PATH, "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["t_sec", "tag", "carla_id", "type_id", "speed_kmh",
                "x", "y", "in_view", "px_bbox"])
    w.writerows(rows)

out.append("")
out.append("=" * 74)
out.append("录制完成")
out.append("=" * 74)
out.append(f"  视频 {VIDEO}  ({os.path.getsize(VIDEO)/1024/1024:.1f} MB)")
out.append(f"  真值 {CSV_PATH}  ({len(rows)} 行)")
out.append(f"  视野内样本 {n_in_view}，其中运动中(>5km/h) {n_moving}")
out.append("")
out.append(f"  ⭐ 关键指标：运动中且在视野内的样本 = {n_moving}")
out.append("     （这是判定标定对错的**有效样本**；v1 这个数字接近于 0）")

# 统计各车速度
out.append("")
for i, it in enumerate(vehs):
    tag = f"veh_{i}"
    vv = [r[4] for r in rows if r[1] == tag and r[7] == 1]
    if vv:
        out.append(f"  {tag} 视野内 {len(vv)} 样本  avg={sum(vv)/len(vv):5.1f} "
                   f"max={max(vv):5.1f} km/h")

# 清理
try:
    cam.stop(); cam.destroy()
except Exception:
    pass
for it in vehs:
    try:
        it["veh"].destroy()
    except Exception:
        pass
st.synchronous_mode = False
st.fixed_delta_seconds = None
world.apply_settings(st)
out.append("")
out.append("已清理")

io.open(r"E:\output\_carla_record2.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
