"""补录真值：把 CARLA 车辆的世界坐标投影到**像素 bbox**

为什么需要这一步：
  原先的 ground_truth.csv 只有世界坐标 (x,y)，而检测器输出的是画面像素 bbox，
  两者**无法对应** -> 没法把"检测到的车"匹配到"CSV 里哪辆车" -> 无法比速度。

做法：用 CARLA 的 `camera.project()` 把每辆车 3D bbox 的 8 个角点投影到像素，
  取外接矩形作为像素 bbox。这样就能按"空间位置"匹配检测结果与真值。

本脚本逐个测试各 API 的可用性，避免假设。
"""

import io
import math

import carla

out = []
client = carla.Client("127.0.0.1", 2000)
client.set_timeout(30.0)
world = client.get_world()
bp_lib = world.get_blueprint_library()
m = world.get_map()

# ---- 搭一个最小场景：路口 + 相机 + 2 辆车 ----
sp = next(s for s in m.get_spawn_points()
          if m.get_waypoint(s.location).is_junction)
jl = m.get_waypoint(sp.location).transform.location
out.append(f"路口: ({jl.x:.1f},{jl.y:.1f})")

cam_bp = bp_lib.find("sensor.camera.rgb")
cam_bp.set_attribute("image_size_x", "1280")
cam_bp.set_attribute("image_size_y", "720")
cam_bp.set_attribute("fov", "70")
cam_loc = carla.Location(x=jl.x - 40.0, y=jl.y, z=jl.z + 26.0)
cam = world.spawn_actor(cam_bp, carla.Transform(cam_loc, carla.Rotation(pitch=-35.0)))
out.append(f"相机已建 id={cam.id}")

near = sorted(m.get_spawn_points(), key=lambda p: p.location.distance(jl))[:6]
vehs = []
for i, s in enumerate(near[:2]):
    try:
        v = world.spawn_actor(bp_lib.filter("vehicle.audi.a2")[0], s)
        vehs.append(v)
    except Exception as e:
        out.append(f"  生成失败: {str(e)[:60]}")
out.append(f"生成 {len(vehs)} 辆车")

st = world.get_settings()
st.synchronous_mode = True
st.fixed_delta_seconds = 0.05
world.apply_settings(st)
for _ in range(20):
    world.tick()

# ---- 测试 1: camera.project() ----
out.append("")
out.append("=" * 72)
out.append("测试 1: camera.project() —— 世界坐标 -> 像素")
out.append("=" * 72)
has_project = hasattr(cam, "project")
out.append(f"  camera 有 project 方法: {has_project}")
if has_project:
    for v in vehs:
        loc = v.get_location()
        loc.z += 1.0                     # 抬高到车体中部
        try:
            px = cam.project(loc)
            out.append(f"  id={v.id} 世界=({loc.x:.1f},{loc.y:.1f},{loc.z:.1f}) "
                       f"-> 像素=({px.x:.1f}, {px.y:.1f})")
        except Exception as e:
            out.append(f"  id={v.id} project 失败: {type(e).__name__}: {str(e)[:80]}")

# ---- 测试 2: 用 3D bbox 8 角点投影出像素外接框 ----
out.append("")
out.append("=" * 72)
out.append("测试 2: 3D bbox 8 角点 -> 像素外接矩形（真正要用的方法）")
out.append("=" * 72)
for v in vehs:
    try:
        bb = v.bounding_box                      # local space
        tf = v.get_transform()
        pts = []
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    local = carla.Location(x=sx * bb.extent.x,
                                           y=sy * bb.extent.y,
                                           z=sz * bb.extent.z)
                    wpt = tf.transform(local + bb.location)
                    p = cam.project(wpt)
                    pts.append((p.x, p.y))
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        # 过滤掉投影到相机后面的点（project 会返回异常大的值）
        valid = [(x, y) for x, y in pts if -5000 < x < 5000 and -5000 < y < 5000]
        if valid:
            vx = [p[0] for p in valid]
            vy = [p[1] for p in valid]
            out.append(f"  id={v.id} 像素bbox=[{min(vx):.0f},{min(vy):.0f},"
                       f"{max(vx):.0f},{max(vy):.0f}]  "
                       f"尺寸={max(vx)-min(vx):.0f}x{max(vy)-min(vy):.0f}  "
                       f"有效点 {len(valid)}/8")
        else:
            out.append(f"  id={v.id} 无有效投影点")
    except Exception as e:
        out.append(f"  id={v.id} 失败: {type(e).__name__}: {str(e)[:100]}")

# ---- 测试 3: 是否在画面内 ----
out.append("")
out.append("=" * 72)
out.append("测试 3: 车辆是否落在画面范围内（1280x720）")
out.append("=" * 72)
for v in vehs:
    loc = v.get_location()
    loc.z += 1.0
    try:
        p = cam.project(loc)
        inside = 0 <= p.x <= 1280 and 0 <= p.y <= 720
        out.append(f"  id={v.id} 像素=({p.x:.0f},{p.y:.0f})  在画面内={inside}")
    except Exception as e:
        out.append(f"  id={v.id} 失败: {str(e)[:60]}")

# ---- 清理 ----
try:
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

io.open(r"E:\output\_carla_project_test.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
