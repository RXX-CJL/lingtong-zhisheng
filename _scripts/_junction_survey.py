"""扫描 CARLA 地图，找出【有斑马线】的路口，供用户挑选

背景（用户要求）：
  "carla里面路口和国内标准路口标线有所区别，所以关于视频的录取需要我监督，
   现在我们需要确定路口是否有适合演示的斑马线，所以需要你帮我找适合的路口
   并截图给我看，让我选择"

做法：
  ① 遍历地图上所有路口（waypoint.is_junction）
  ② 用 OpenDRIVE 的 crosswalk 数据判断哪个路口有斑马线
  ③ 对有斑马线的路口，架一台俯拍相机截图
  ④ 输出候选清单 + 每张截图，供用户选择
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

out.append(f"地图: {m.name}")

# ---- ① 拿所有斑马线（OpenDRIVE crosswalk）----
try:
    cws = m.get_crosswalks()
    out.append(f"地图斑马线（crosswalk）总数: {len(cws)}")
except Exception as e:
    out.append(f"get_crosswalks 不可用: {e}")
    cws = []

# 把斑马线按位置聚类成"过街口"，每 4 个点位一组（CARLA 返回的是一串点）
cw_centers = []
for cw in cws:
    cw_centers.append((cw.x, cw.y))
out.append(f"斑马线顶点数: {len(cw_centers)}")

# ---- ② 找所有路口 ----
spawn_points = m.get_spawn_points()
junction_wps = {}
for sp in spawn_points:
    wp = m.get_waypoint(sp.location)
    if wp.is_junction and wp.junction_id is not None:
        jid = wp.junction_id
        if jid not in junction_wps:
            junction_wps[jid] = (wp, sp.location)
out.append(f"包含 spawn point 的路口数: {len(junction_wps)}")

# 对每个路口，统计附近有多少斑马线顶点（半径 60m）
out.append("")
out.append("=" * 88)
out.append("路口 -> 斑马线数量（半径 60m 内的 crosswalk 顶点数）")
out.append("=" * 88)

cand = []
for jid, (wp, loc) in junction_wps.items():
    n = 0
    for (x, y) in cw_centers:
        if math.hypot(x - loc.x, y - loc.y) < 60.0:
            n += 1
    cand.append({"jid": jid, "loc": loc, "n_cw": n, "wp": wp})

cand.sort(key=lambda c: -c["n_cw"])
for c in cand[:20]:
    out.append(f"  junction_id={c['jid']:>4}  位置=({c['loc'].x:8.1f},{c['loc'].y:8.1f})  "
               f"斑马线顶点={c['n_cw']:>4}")

# 只保留有斑马线的
with_cw = [c for c in cand if c["n_cw"] >= 8]
out.append("")
out.append(f"有斑马线的路口（顶点>=8）: {len(with_cw)} 个")

# ---- ③ 对前 6 个候选路口截图 ----
cam_bp = bp.find("sensor.camera.rgb")
cam_bp.set_attribute("image_size_x", "1280")
cam_bp.set_attribute("image_size_y", "720")
cam_bp.set_attribute("fov", "70")

import cv2
import numpy as np

st = world.get_settings()
st.synchronous_mode = True
st.fixed_delta_seconds = 0.05
world.apply_settings(st)

shots = []
for i, c in enumerate(with_cw[:6]):
    loc = c["loc"]
    # 俯拍：路口上方 22m，向后 26m，俯角 40°
    cam_loc = carla.Location(x=loc.x - 26.0, y=loc.y, z=loc.z + 22.0)
    yaw = math.degrees(math.atan2(loc.y - cam_loc.y, loc.x - cam_loc.x))
    cam_rot = carla.Rotation(pitch=-40.0, yaw=yaw, roll=0.0)
    try:
        cam = world.spawn_actor(cam_bp, carla.Transform(cam_loc, cam_rot))
    except Exception as e:
        out.append(f"  候选{i+1} 相机失败: {str(e)[:60]}")
        continue
    q = queue.Queue()
    cam.listen(q.put)
    frame = None
    for _ in range(6):
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
        out.append(f"  候选{i+1} 取帧失败")
        continue
    p = os.path.join(OUT, f"junction_{i+1}_jid{c['jid']}.png")
    cv2.imwrite(p, frame)
    shots.append({"idx": i + 1, "jid": c["jid"], "loc": loc, "n_cw": c["n_cw"], "path": p})
    out.append(f"  候选{i+1}: junction_id={c['jid']} 位置=({loc.x:.1f},{loc.y:.1f}) "
               f"斑马线顶点={c['n_cw']}  -> {os.path.basename(p)}")

st.synchronous_mode = False
st.fixed_delta_seconds = None
world.apply_settings(st)

out.append("")
out.append("=" * 88)
out.append("截图清单（请打开查看并挑选）")
out.append("=" * 88)
for s in shots:
    out.append(f"  候选{s['idx']}  junction_id={s['jid']}  斑马线顶点={s['n_cw']}  {s['path']}")

io.open(r"E:\output\_junction_survey.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
