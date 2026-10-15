"""CARLA 相机投影：自己实现针孔模型 + **实测验证**

背景：CARLA 0.9.16 的 ServerSideSensor 没有 project()，需自行实现。
但"自己实现"必须先证明它对 —— 否则后续真值全不可信。

验证手段（用相机自己的画面做交叉验证）：
  1. 在相机视野内放车，用公式算出像素框
  2. 把该像素框画到**真实渲染帧**上
  3. 人工/程序检查框是否套住车辆
  另加方向性检验：把车放在相机右侧，看是否投影到画面右半。

坐标约定（CARLA，左手系）：
  x = 前（镜头朝向）、y = 右、z = 上
  u = W/2 + f * (y/x)
  v = H/2 - f * (z/x)      （图像 y 向下为正）
"""

import io
import math
import queue

import carla

out = []
client = carla.Client("127.0.0.1", 2000)
client.set_timeout(30.0)
world = client.get_world()
bp_lib = world.get_blueprint_library()
m = world.get_map()

W, H, FOV = 1280, 720, 70.0
f_px = W / (2.0 * math.tan(math.radians(FOV) / 2.0))
out.append(f"相机 {W}x{H}  fov={FOV}  ->  f = {f_px:.2f} px")


def project_point(cam_tf, loc, f):
    """世界坐标 -> 像素（返回 (u, v, depth)；depth<=0 表示在相机后方）"""
    inv = cam_tf.get_inverse_matrix()
    p = inv @ loc
    if p[0] <= 1e-3:
        return (None, None, p[0])
    u = W / 2.0 + f * (p[1] / p[0])
    v = H / 2.0 - f * (p[2] / p[0])
    return (u, v, p[0])


def veh_pixel_bbox(veh, cam_tf, f):
    """车辆 3D bbox 8 角点 -> 像素外接矩形"""
    bb = veh.bounding_box
    tf = veh.get_transform()
    us, vs = [], []
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                local = carla.Location(x=sx * bb.extent.x,
                                       y=sy * bb.extent.y,
                                       z=sz * bb.extent.z) + bb.location
                wl = tf.transform(local)
                u, v, d = project_point(cam_tf, wl, f)
                if u is not None:
                    us.append(u)
                    vs.append(v)
    if not us:
        return None
    return (min(us), min(vs), max(us), max(vs))


# ---- 建场景 ----
sp = next(s for s in m.get_spawn_points()
          if m.get_waypoint(s.location).is_junction)
jl = m.get_waypoint(sp.location).transform.location

cam_bp = bp_lib.find("sensor.camera.rgb")
cam_bp.set_attribute("image_size_x", str(W))
cam_bp.set_attribute("image_size_y", str(H))
cam_bp.set_attribute("fov", str(FOV))
cam_loc = carla.Location(x=jl.x - 40.0, y=jl.y, z=jl.z + 26.0)
cam_rot = carla.Rotation(pitch=-35.0)
cam = world.spawn_actor(cam_bp, carla.Transform(cam_loc, cam_rot))
cam_tf = cam.get_transform()
out.append(f"相机位置=({cam_loc.x:.1f},{cam_loc.y:.1f},{cam_loc.z:.1f}) pitch={cam_rot.pitch}")

st = world.get_settings()
st.synchronous_mode = True
st.fixed_delta_seconds = 0.05
world.apply_settings(st)

# 在路口附近放几辆车
near = sorted(m.get_spawn_points(), key=lambda p: p.location.distance(jl))[:8]
vehs = []
for i, s in enumerate(near):
    try:
        v = world.spawn_actor(bp_lib.filter("vehicle.audi.a2")[0], s)
        vehs.append(v)
    except Exception:
        pass
for _ in range(20):
    world.tick()
out.append(f"生成 {len(vehs)} 辆车")

# ---- 投影 + 画框到真实帧 ----
q = queue.Queue()
cam.listen(q.put)
world.tick()
img = q.get(timeout=20.0)

import cv2
import numpy as np

arr = np.frombuffer(img.raw_data, dtype=np.uint8).reshape((img.height, img.width, 4))[:, :, :3].copy()

out.append("")
out.append("=" * 74)
out.append("投影结果（画框到真实渲染帧上人工核对）")
out.append("=" * 74)
n_drawn = 0
for v in vehs:
    bb = veh_pixel_bbox(v, cam_tf, f_px)
    loc = v.get_location()
    if bb is None:
        out.append(f"  id={v.id} 在相机后方/不可投影  世界=({loc.x:.1f},{loc.y:.1f})")
        continue
    u1, v1, u2, v2 = [int(round(x)) for x in bb]
    inside = (u2 > 0 and u1 < W and v2 > 0 and v1 < H)
    out.append(f"  id={v.id} 像素框=[{u1},{v1},{u2},{v2}] 尺寸={u2-u1}x{v2-v1}  "
               f"在画面内={inside}")
    if inside:
        cv2.rectangle(arr, (max(0, u1), max(0, v1)), (min(W, u2), min(H, v2)),
                      (0, 255, 0), 3)
        n_drawn += 1

p = r"E:\output\_screens\carla_projection_check.jpg"
cv2.imwrite(p, arr, [cv2.IMWRITE_JPEG_QUALITY, 92])
out.append("")
out.append(f"已在真实帧上画 {n_drawn} 个投影框 -> {p}")

# ---- 方向性检验：车在相机右侧应投影到右半 ----
out.append("")
out.append("=" * 74)
out.append("方向性检验（证明 u/v 符号没搞反）")
out.append("=" * 74)
# 取一辆确实在画面内的车，人为向右/向上偏移，看像素是否同步偏移
tests = [v for v in vehs if veh_pixel_bbox(v, cam_tf, f_px) is not None]
if tests:
    v = tests[0]
    base = v.get_location()
    for name, dy, dz in (("原位置", 0.0, 0.0), ("向右+5m", 5.0, 0.0), ("向上+5m", 0.0, 5.0)):
        pt = carla.Location(x=base.x, y=base.y + dy, z=base.z + dz)
        u, vv, d = project_point(cam_tf, pt, f_px)
        out.append(f"  {name:10s} 世界y={pt.y:8.2f} z={pt.z:7.2f} -> 像素=({u:.0f}, {vv:.0f})"
                   if u is not None else f"  {name:10s} 不可投影")
    out.append("")
    out.append("  说明: '向右+5m' 的 u 应**增大**；'向上+5m' 的 v 应**减小**。")

# ---- 清理 ----
try:
    cam.stop()
    cam.destroy()
except Exception:
    pass
for v in vehs:
    try:
        v.destroy()
    except Exception:
        pass
st.synchronous_mode = False
st.fixed_delta_seconds = None
world.apply_settings(st)
out.append("")
out.append("已清理")

io.open(r"E:\output\_carla_projection.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
