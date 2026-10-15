"""投影验证 v2 —— 自己用 numpy 构造相机矩阵（绕开 get_inverse_matrix 的约定问题）

v1 的失败：
  车在相机正前方 12m，但用 get_inverse_matrix() 算出的相机系 X=48.94（应≈12）
  -> 该矩阵的行/列约定与我的用法不符，且 4 种屏幕坐标约定全部落空

v2 做法（完全可控）：
  ① 从相机 transform 读取 loc + rotation（yaw/pitch/roll）
  ② 用 numpy 自己构造旋转矩阵 R（CARLA 左手系：yaw 绕 Z、pitch 绕 Y、roll 绕 X）
  ③ 相机系坐标 = R^T · (P - cam_loc)
  ④ 屏幕坐标 = 中心 + f · (y/x, -z/x)
  ⑤ 打印 + 画标记到帧上，人工核对
  ⑥ 若仍不对，直接把 6 种轴组合都算出来打印，找出落在中心的那个
"""

import io
import math
import os
import queue
import sys

import numpy as np

import carla

OUT = r"E:\output\_proj_validate"
os.makedirs(OUT, exist_ok=True)
out = []

client = carla.Client("127.0.0.1", 2000)
client.set_timeout(30.0)
world = client.get_world()
m = world.get_map()
bp = world.get_blueprint_library()
world.set_weather(carla.WeatherParameters.ClearNoon)

st = world.get_settings()
st.synchronous_mode = True
st.fixed_delta_seconds = 0.05
world.apply_settings(st)

# ---- 找灯 + 路段 ----
tls = list(world.get_actors().filter("traffic.traffic_light*"))
picked = None
for tl in tls:
    lbs = tl.get_light_boxes()
    if not lbs:
        continue
    lamp = sorted(lbs, key=lambda b: b.extent.x * b.extent.y * b.extent.z)[0]
    for sp in m.get_spawn_points():
        w = m.get_waypoint(sp.location)
        if w.is_junction:
            continue
        if 20 <= sp.location.distance(lamp.location) <= 45:
            picked = (tl, lamp.location, sp)
            break
    if picked:
        break

tl, lamp_loc, car_sp = picked
out.append(f"红绿灯 id={tl.id} 灯珠=({lamp_loc.x:.1f},{lamp_loc.y:.1f},{lamp_loc.z:.1f})")
out.append(f"车 spawn=({car_sp.location.x:.1f},{car_sp.location.y:.1f}) yaw={car_sp.rotation.yaw:.1f}")

car = world.spawn_actor(bp.filter("vehicle.*")[0], car_sp)
car.set_autopilot(False)
for _ in range(5):
    world.tick()
car_loc = car.get_location()

# ---- 相机：车后方 12m，正对车 ----
cyaw = math.radians(car_sp.rotation.yaw)
back = 12.0
cam_loc = carla.Location(x=car_loc.x - math.cos(cyaw) * back,
                        y=car_loc.y - math.sin(cyaw) * back,
                        z=car_loc.z + 2.0)
look_yaw = math.degrees(math.atan2(car_loc.y - cam_loc.y, car_loc.x - cam_loc.x))
cam_rot = carla.Rotation(pitch=0.0, yaw=look_yaw, roll=0.0)

RES = (1280, 720)
FOV = 70.0
cam_bp = bp.find("sensor.camera.rgb")
cam_bp.set_attribute("image_size_x", str(RES[0]))
cam_bp.set_attribute("image_size_y", str(RES[1]))
cam_bp.set_attribute("fov", str(FOV))
cam = world.spawn_actor(cam_bp, carla.Transform(cam_loc, cam_rot))
for _ in range(5):
    world.tick()
cam_tf = cam.get_transform()

world.get_spectator().set_transform(carla.Transform(cam_loc, cam_rot))

import cv2

q = queue.Queue()
cam.listen(q.put)
for _ in range(5):
    world.tick()
frame = None
try:
    img = q.get(timeout=10.0)
    frame = np.frombuffer(img.raw_data, dtype=np.uint8).reshape(
        (img.height, img.width, 4))[:, :, :3].copy()
except queue.Empty:
    pass

out.append(f"相机 transform loc=({cam_tf.location.x:.2f},{cam_tf.location.y:.2f},"
           f"{cam_tf.location.z:.2f}) rot=({cam_tf.rotation.pitch:.2f},"
           f"{cam_tf.rotation.yaw:.2f},{cam_tf.rotation.roll:.2f})")


# ---- 自己构造旋转矩阵 ----
def rot_matrix(pitch_deg, yaw_deg, roll_deg):
    """CARLA 左手系：R = Rz(yaw) · Ry(pitch) · Rx(roll)"""
    p, y, r = map(math.radians, (pitch_deg, yaw_deg, roll_deg))
    cz, sz = math.cos(y), math.sin(y)
    cy_, sy_ = math.cos(p), math.sin(p)
    cx, sx = math.cos(r), math.sin(r)
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    Ry = np.array([[cy_, 0, sy_], [0, 1, 0], [-sy_, 0, cy_]])
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    return Rz @ Ry @ Rx


R = rot_matrix(cam_tf.rotation.pitch, cam_tf.rotation.yaw, cam_tf.rotation.roll)
out.append("")
out.append("自建旋转矩阵 R:")
for row in R:
    out.append(f"   {[round(x, 4) for x in row]}")

f_px = RES[0] / (2.0 * math.tan(math.radians(FOV) / 2.0))
out.append(f"f = {f_px:.1f} px")


def to_cam_np(P):
    """世界 -> 相机系（用自建 R 的转置）"""
    d = np.array([P[0] - cam_tf.location.x,
                  P[1] - cam_tf.location.y,
                  P[2] - cam_tf.location.z])
    return R.T @ d


out.append("")
out.append("=" * 80)
out.append("投影（自建矩阵）")
out.append("=" * 80)
vis = frame.copy() if frame is not None else None

targets = [
    ("车（应画面中心）", (car_loc.x, car_loc.y, car_loc.z + 0.8), (0, 0, 255), "CAR"),
    ("红绿灯珠", (lamp_loc.x, lamp_loc.y, lamp_loc.z), (0, 255, 255), "TL"),
]
for name, P, col, tag in targets:
    vc = to_cam_np(P)
    out.append(f"  {name}: 相机系=({vc[0]:8.2f},{vc[1]:8.2f},{vc[2]:8.2f})")
    if vc[0] <= 0.1:
        out.append("     -> 在相机后方")
        continue
    u = RES[0] / 2 + f_px * (vc[1] / vc[0])
    v_ = RES[1] / 2 - f_px * (vc[2] / vc[0])
    inside = 0 <= u <= RES[0] and 0 <= v_ <= RES[1]
    d_center = math.hypot(u - RES[0] / 2, v_ - RES[1] / 2)
    out.append(f"     -> 像素=({u:7.1f},{v_:7.1f})  画面内={inside}  距中心={d_center:.1f}")
    if vis is not None and inside:
        cv2.drawMarker(vis, (int(u), int(v_)), col, cv2.MARKER_CROSS, 40, 4)
        cv2.putText(vis, tag, (int(u) + 12, int(v_) - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, col, 2)

if vis is not None:
    p = os.path.join(OUT, "validate2_marked.png")
    cv2.imwrite(p, vis)
    out.append("")
    out.append(f"标记图: {os.path.basename(p)}")

# ---- 若车没落在中心，枚举轴组合 ----
vc_car = to_cam_np((car_loc.x, car_loc.y, car_loc.z + 0.8))
out.append("")
out.append("=" * 80)
out.append("轴组合枚举（找哪个让车落在画面中心 640,360）")
out.append("=" * 80)
out.append(f"  车相机系 = ({vc_car[0]:.2f},{vc_car[1]:.2f},{vc_car[2]:.2f})")
out.append("  期望: 深度≈12，横向≈0，纵向≈-1.2")
u0, v0 = RES[0] / 2, RES[1] / 2
best = None
for di, dname in ((0, "x"), (1, "y"), (2, "z")):
    for hi, hname in ((0, "x"), (1, "y"), (2, "z")):
        if hi == di:
            continue
        for vi, vname in ((0, "x"), (1, "y"), (2, "z")):
            if vi in (di, hi):
                continue
            for sgn_h in (1, -1):
                for sgn_v in (1, -1):
                    depth = vc_car[di]
                    if depth <= 0.1:
                        continue
                    u = u0 + sgn_h * f_px * vc_car[hi] / depth
                    v_ = v0 + sgn_v * f_px * vc_car[vi] / depth
                    dcen = math.hypot(u - u0, v_ - v0)
                    ok = 0 <= u <= RES[0] and 0 <= v_ <= RES[1]
                    if ok and (best is None or dcen < best[0]):
                        best = (dcen, f"深度={dname} 横={'-' if sgn_h<0 else '+'}{hname} "
                                      f"纵={'-' if sgn_v<0 else '+'}{vname}", u, v_)

if best:
    out.append(f"  ✅ 最佳约定: {best[1]}  -> 像素=({best[2]:.1f},{best[3]:.1f}) "
               f"距中心 {best[0]:.1f}")
else:
    out.append("  ❌ 没有任何轴组合把车投到画面内 —— 说明 R 构造或取帧时机有误")

try:
    cam.stop(); cam.destroy()
except Exception:
    pass
try:
    car.destroy()
except Exception:
    pass
st.synchronous_mode = False
st.fixed_delta_seconds = None
world.apply_settings(st)

io.open(r"E:\output\_proj_validate2.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
