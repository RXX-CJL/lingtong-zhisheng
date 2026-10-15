"""最小投影验证实验（用户要求：画面里必须能看到红绿灯）

背景：
  投影判断一直不可靠（"画面里 0 辆车"），但车辆数据是正常的。
  根因未确定 —— 可能是 CARLA 相机坐标轴约定与我假设的不同。
  不再靠推理，做**受控实验**：

实验设计：
  ① 在一条直路上放一辆车（位置已知）
  ② 相机架在该车【正前方 12m】、高 2m、正对该车（yaw 精确计算）
  ③ 在车的位置也放一个"标记"（用一辆显眼的车）
  ④ 抓帧 -> 人工看车是否在画面中心
  ⑤ 打印投影坐标 -> 与画面比对，逐个验证坐标轴约定

  同时：把相机架在能同时看到【车】和【红绿灯】的位置（用户要求）
"""

import io
import math
import os
import queue

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

# ---- ① 找一段直路 + 一个红绿灯（用户要求画面里要有红绿灯）----
# 找红绿灯，然后在它附近的路面上找一个 spawn point
tls = list(world.get_actors().filter("traffic.traffic_light*"))
out.append(f"世界红绿灯 {len(tls)} 个")

target_tl = None
tl_lamp_world = None
for tl in tls:
    lbs = tl.get_light_boxes()
    if not lbs:
        continue
    lamp = sorted(lbs, key=lambda b: b.extent.x * b.extent.y * b.extent.z)[0]
    # 找一个距离该灯 20~45m 的非路口 spawn point（放车用）
    for sp in m.get_spawn_points():
        w = m.get_waypoint(sp.location)
        if w.is_junction:
            continue
        d = sp.location.distance(lamp.location)
        if 20 <= d <= 45:
            target_tl = tl
            tl_lamp_world = lamp.location
            car_sp = sp
            break
    if target_tl:
        break

if target_tl is None:
    out.append("未找到合适的灯+路段组合")
else:
    out.append(f"选定红绿灯 id={target_tl.id}  灯珠世界=({tl_lamp_world.x:.1f},"
               f"{tl_lamp_world.y:.1f},{tl_lamp_world.z:.1f})")
    out.append(f"选车 spawn point=({car_sp.location.x:.1f},{car_sp.location.y:.1f}) "
               f"yaw={car_sp.rotation.yaw:.1f}")

    # ---- ② 放车 ----
    car_bp = bp.filter("vehicle.*")[0]
    car = world.spawn_actor(car_bp, car_sp)
    car.set_autopilot(False)
    for _ in range(5):
        world.tick()
    car_loc = car.get_location()
    out.append(f"车已放好 id={car.id}  实际位置=({car_loc.x:.2f},{car_loc.y:.2f},{car_loc.z:.2f})")

    # ---- ③ 相机：放在车的【正后方 12m】看向车（这样车应在画面中心）----
    # 用"车 -> 期望相机"的几何：相机在车的后方，朝向车
    # 车头方向 = car_sp.rotation.yaw；后方 = 反方向
    cyaw = math.radians(car_sp.rotation.yaw)
    back = 12.0
    cam_loc = carla.Location(x=car_loc.x - math.cos(cyaw) * back,
                            y=car_loc.y - math.sin(cyaw) * back,
                            z=car_loc.z + 2.0)
    look_yaw = math.degrees(math.atan2(car_loc.y - cam_loc.y, car_loc.x - cam_loc.x))
    cam_rot = carla.Rotation(pitch=0.0, yaw=look_yaw, roll=0.0)
    out.append(f"相机=({cam_loc.x:.2f},{cam_loc.y:.2f},{cam_loc.z:.2f}) yaw={look_yaw:.1f} "
               f"（车在正前方 {back}m）")

    spec = world.get_spectator()
    spec.set_transform(carla.Transform(cam_loc, cam_rot))

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
    out.append(f"相机实际 transform=({cam_tf.location.x:.2f},{cam_tf.location.y:.2f},"
               f"{cam_tf.location.z:.2f}) yaw={cam_tf.rotation.yaw:.2f}")

    import cv2
    import numpy as np

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

    if frame is None:
        out.append("取帧失败")
    else:
        p = os.path.join(OUT, "proj_validate.png")
        cv2.imwrite(p, frame)
        out.append(f"已抓帧: {os.path.basename(p)}")

        # ---- ⑤ 投影车辆 + 灯珠，并把标记画到帧上 ----
        f_px = RES[0] / (2.0 * math.tan(math.radians(FOV) / 2.0))
        inv = cam_tf.get_inverse_matrix()

        def project(P):
            d = (P[0] - cam_tf.location.x, P[1] - cam_tf.location.y,
                 P[2] - cam_tf.location.z)
            vc = [sum(inv[i][j] * (d[0], d[1], d[2], 1.0)[j] for j in range(4))
                  for i in range(4)]
            if vc[0] <= 0.1:
                return None, vc
            return (RES[0] / 2 + f_px * (vc[1] / vc[0]),
                    RES[1] / 2 - f_px * (vc[2] / vc[0])), vc

        vis = frame.copy()
        out.append("")
        out.append("=" * 78)
        out.append("投影验证（标记画到帧上）")
        out.append("=" * 78)
        targets = [
            ("车（应在画面中心）", (car_loc.x, car_loc.y, car_loc.z + 0.8), (0, 0, 255), 'CAR'),
            ("红绿灯珠", (tl_lamp_world.x, tl_lamp_world.y, tl_lamp_world.z), (0, 255, 255), 'TL'),
        ]
        for name, P, col, tag in targets:
            pr, vc = project(P)
            out.append(f"  {name}: 相机系=({vc[0]:7.2f},{vc[1]:7.2f},{vc[2]:7.2f})", )
            if pr is None:
                out.append("     -> 在相机后方，不可投影")
                continue
            u, v_ = pr
            inside = 0 <= u <= RES[0] and 0 <= v_ <= RES[1]
            out.append(f"     -> 像素=({u:7.1f},{v_:7.1f})  画面内={inside}")
            if inside:
                cv2.drawMarker(vis, (int(u), int(v_)), col, cv2.MARKER_CROSS, 40, 4)
                cv2.putText(vis, tag, (int(u) + 12, int(v_) - 12),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, col, 2)
        p2 = os.path.join(OUT, "proj_validate_marked.png")
        cv2.imwrite(p2, vis)
        out.append("")
        out.append(f"  标记图: {os.path.basename(p2)}")
        out.append("  （若 'CAR' 十字不在画面中心那辆车上，则坐标约定需要修正）")

        # ---- 补充：打印几种可能的坐标约定，便于比对 ----
        out.append("")
        out.append("=" * 78)
        out.append("坐标约定探测（同一辆车，用不同公式算像素，看哪个落在中心）")
        out.append("=" * 78)
        d = (car_loc.x - cam_tf.location.x, car_loc.y - cam_tf.location.y,
             car_loc.z - cam_tf.location.z)
        vc = [sum(inv[i][j] * (d[0], d[1], d[2], 1.0)[j] for j in range(4))
              for i in range(4)]
        cx, cy, cz = RES[0] / 2, RES[1] / 2, RES[0]  # 仅占位
        u0, v0 = RES[0] / 2, RES[1] / 2
        cands = [
            ("约定1 u=+y/f, v=-z/f", u0 + f_px * vc[1] / vc[0], v0 - f_px * vc[2] / vc[0]),
            ("约定2 u=-y/f, v=+z/f", u0 - f_px * vc[1] / vc[0], v0 + f_px * vc[2] / vc[0]),
            ("约定3 u=+z/f, v=-y/f", u0 + f_px * vc[2] / vc[0], v0 - f_px * vc[1] / vc[0]),
            ("约定4 u=-z/f, v=+y/f", u0 - f_px * vc[2] / vc[0], v0 + f_px * vc[1] / vc[0]),
        ]
        out.append(f"  相机系坐标 = ({vc[0]:.2f}, {vc[1]:.2f}, {vc[2]:.2f})   期望落在中心 ({u0:.0f},{v0:.0f})")
        for lab, u, v_ in cands:
            dist = math.hypot(u - u0, v_ - v0)
            ok = 0 <= u <= RES[0] and 0 <= v_ <= RES[1]
            out.append(f"    {lab:26s} -> ({u:8.1f},{v_:8.1f})  距中心 {dist:07.1f}  "
                       f"{'在画面内' if ok else '画面外'}")

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

io.open(r"E:\output\_proj_validate.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
