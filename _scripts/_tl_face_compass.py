"""一次确定灯面朝向：沿 ±X / ±Y 四个方向各拍一张，用图判定哪边是灯面

前 4 次失败的根因（本次已用几何数据定位）：
  · 灯箱 ext=(0.201, 0.484, 0.704) -> x 很薄、y 很宽
  · 灯箱 yaw=-90
  => 灯面的法线是 ±X 方向
  · 而我一直把相机放在 ±Y（用杆 yaw 算的 cos/sin）-> 永远在侧面

本脚本对每个方向拍一张，并把 4 张拼成一张"方向罗盘图"，
这样一眼就能看出哪边是灯面。
"""

import io
import math
import os
import queue

import carla

OUT = r"E:\output\_tl_review"
os.makedirs(OUT, exist_ok=True)
out = []

client = carla.Client("127.0.0.1", 2000)
client.set_timeout(30.0)
world = client.get_world()
bp = world.get_blueprint_library()

st = world.get_settings()
st.synchronous_mode = True
st.fixed_delta_seconds = 0.05
world.apply_settings(st)

tl = list(world.get_actors().filter("traffic.traffic_light*"))[0]
lbs = tl.get_light_boxes()
# 用体量最小的 box 作为信号灯珠（经验规律）
lamp = sorted(lbs, key=lambda b: b.extent.x * b.extent.y * b.extent.z)[0]
out.append(f"灯 id={tl.id}  选用灯珠=({lamp.location.x:.2f},{lamp.location.y:.2f},"
           f"{lamp.location.z:.2f})  ext=({lamp.extent.x:.3f},{lamp.extent.y:.3f},{lamp.extent.z:.3f})")

# 强制置红（这样若拍到灯面，应看到红光）
tl.set_state(carla.TrafficLightState.Red)

cam_bp = bp.find("sensor.camera.rgb")
cam_bp.set_attribute("image_size_x", "640")
cam_bp.set_attribute("image_size_y", "640")
cam_bp.set_attribute("fov", "50")

import cv2
import numpy as np

DIRS = [
    ("+X", (1, 0), 0.0),
    ("-X", (-1, 0), 180.0),
    ("+Y", (0, 1), 90.0),
    ("-Y", (0, -1), -90.0),
]
DIST = 7.0

tiles = []
results = []
for name, (ux, uy), look_yaw in DIRS:
    cam_loc = carla.Location(x=lamp.location.x + ux * DIST,
                             y=lamp.location.y + uy * DIST,
                             z=lamp.location.z)
    cam_rot = carla.Rotation(pitch=0.0, yaw=look_yaw, roll=0.0)
    try:
        cam = world.spawn_actor(cam_bp, carla.Transform(cam_loc, cam_rot))
    except Exception as e:
        out.append(f"  {name}: 相机生成失败 {str(e)[:60]}")
        continue
    q = queue.Queue()
    cam.listen(q.put)
    frame = None
    for _ in range(10):
        world.tick()
    try:
        img = q.get(timeout=12.0)
        frame = np.frombuffer(img.raw_data, dtype=np.uint8).reshape(
            (img.height, img.width, 4))[:, :, :3].copy()
    except queue.Empty:
        pass
    try:
        cam.stop(); cam.destroy()
    except Exception:
        pass

    if frame is None:
        out.append(f"  {name}: 取帧失败")
        continue

    # 量化：高饱和 + 高亮像素（= 发光灯珠特征）
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    m = ((hsv[:, :, 1] > 100) & (hsv[:, :, 2] > 140)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, stats, cents = cv2.connectedComponentsWithStats(m, 8)
    blobs = []
    for i in range(1, n):
        a = stats[i, cv2.CC_STAT_AREA]
        if a < 15:
            continue
        mm = (lab == i)
        hh = float(np.median(hsv[:, :, 0][mm]))
        blobs.append((int(a), round(hh, 1), int(cents[i][0]), int(cents[i][1])))
    blobs.sort(reverse=True)
    red_blobs = [b for b in blobs if b[1] < 12 or b[1] > 168]
    results.append({"dir": name, "n_blob": len(blobs), "red": len(red_blobs),
                    "top": blobs[:3]})
    out.append(f"  {name}: 高饱和亮区 {len(blobs)} 个，其中红色 {len(red_blobs)} 个  "
               f"top3={blobs[:3]}")

    t = frame.copy()
    cv2.putText(t, f"{name} red={len(red_blobs)}", (6, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    tiles.append(t)

if tiles:
    grid = np.hstack(tiles)
    p = os.path.join(OUT, "tl_face_compass.png")
    cv2.imwrite(p, grid)
    out.append("")
    out.append(f"四方向罗盘图: {p}  {grid.shape[1]}x{grid.shape[0]}")

out.append("")
out.append("=" * 74)
out.append("判定：哪个方向看到了『红色发光灯珠』，那个方向就是灯面")
out.append("=" * 74)
best = None
for r in results:
    out.append(f"  {r['dir']:3s}  红色发光区 {r['red']} 个")
    if r["red"] > 0 and (best is None or r["red"] > best["red"]):
        best = r
if best:
    out.append("")
    out.append(f"  ✅ 灯面朝向 = {best['dir']}（看到 {best['red']} 个红色发光区）")
    out.append(f"     以后架监控相机应放在灯珠的 {best['dir']} 方向")
else:
    out.append("")
    out.append("  ⚠ 四个方向都没看到红色发光区 —— 可能置红未生效，或相机高度不对")

st.synchronous_mode = False
st.fixed_delta_seconds = None
world.apply_settings(st)

io.open(r"E:\output\_tl_face_compass.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
