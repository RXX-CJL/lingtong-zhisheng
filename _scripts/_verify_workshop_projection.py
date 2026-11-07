# -*- coding: utf-8 -*-
r"""离线校验 carla_creator_workshop 的相机反投影 / 拾取 / 地面求交（不启动 CARLA 服务端）。

用法：py -3.12 E:\output\_scripts\_verify_workshop_projection.py
"""
import importlib.util
import math
import sys
import types
from pathlib import Path

import numpy as np

TARGET = (Path(__file__).resolve().parents[1] / "1" / "carla" / "CARLA_0.9.16"
          / "PythonAPI" / "examples" / "carla_creator_workshop.py")

if not TARGET.is_file():
    print("FAIL 找不到目标文件:", TARGET)
    sys.exit(2)

spec = importlib.util.spec_from_file_location("carla_creator_workshop", TARGET)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
Workshop = module.CarlaCreatorWorkshop
carla = module.carla
cv2 = module.cv2

PASS = 0
FAIL = 0


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"[PASS] {name} {detail}")
    else:
        FAIL += 1
        print(f"[FAIL] {name} {detail}")


def fake_world(transform):
    return types.SimpleNamespace(
        get_spectator=lambda: types.SimpleNamespace(get_transform=lambda: transform),
        ground_projection=lambda location, distance: None,
        project_point=lambda *args: None,
    )


def make(transform, size=(1920, 1080), fov=None):
    obj = object.__new__(Workshop)
    obj.connected = True
    obj.world = fake_world(transform)
    obj.preview_frame_size = size
    if fov is None:
        obj.camera = None
    else:
        obj.camera = types.SimpleNamespace(get_transform=lambda: transform, attributes={"fov": str(fov)})
    return obj


def tf(pitch, yaw, x=0.0, y=0.0, z=0.0):
    return carla.Transform(carla.Location(x=x, y=y, z=z), carla.Rotation(pitch=pitch, yaw=yaw, roll=0.0))


# T1 中心像素 → 正前方
body = make(tf(0.0, 0.0))
origin, direction = body._ray_from_pixel(959.5, 539.5)
check("T1 中心像素方向=+X", np.allclose(direction, [1.0, 0.0, 0.0], atol=1e-9), f"dir={direction.round(6)}")

# T2 右边缘 → 水平半角 = fov/2
origin, right_edge = body._ray_from_pixel(1919.5, 539.5)
ratio = right_edge[1] / right_edge[0]
check("T2 右边缘=tan(45°)", abs(ratio - 1.0) < 1e-6, f"ratio={ratio:.6f}")

# T3 上边缘 → 垂直半角 = tan(fov/2)*(H/W)
origin, top_edge = body._ray_from_pixel(959.5, 0.0)
expect = 1.0 * 1080.0 / 1920.0
check("T3 上边缘垂直半角", abs(top_edge[2] / top_edge[0] - expect) < 1e-3, f"ratio={top_edge[2] / top_edge[0]:.6f} expect={expect:.6f}")

# T4 往返：像素 → 射线 → 世界点 → 像素
transform = tf(-23.445, 179.536, -15.720, -63.145, 5.732)
body = make(transform)
basis = body._camera_basis(transform)
origin_np = body._np_location(transform.location)
max_err = 0.0
for u, v in [(0, 0), (959.5, 539.5), (1919.5, 1079.5), (300, 800), (1500, 200)]:
    _, d = body._ray_from_pixel(u, v)
    point = origin_np + d * 40.0
    uv = body._world_to_pixel(point, origin_np, basis, 90.0, 1920, 1080)
    if uv is None:
        max_err = 9e9
        break
    max_err = max(max_err, abs(uv[0] - u), abs(uv[1] - v))
check("T4 像素->世界往返", max_err < 0.05, f"max_err={max_err:.4f}px")

# T5 真实机位的中心射线俯仰
_, center = body._ray_from_pixel(959.5, 539.5)
check("T5 真实机位俯角", abs(math.degrees(math.asin(center[2])) - (-23.445)) < 0.01, f"pitch={math.degrees(math.asin(center[2])):.3f}°")

# T6 fov 从相机属性读取（非 90 时半角跟着变）
body_110 = make(tf(0.0, 0.0), fov=110.0)
_, dir_110 = body_110._ray_from_pixel(1919.5, 539.5)
check("T6 fov=110 生效", abs(dir_110[1] / dir_110[0] - math.tan(math.radians(55.0))) < 1e-6,
      f"ratio={dir_110[1] / dir_110[0]:.6f} expect={math.tan(math.radians(55.0)):.6f}")

# T7 bbox 8 顶点投影 + 凸包命中
actor_tf = carla.Transform(carla.Location(x=10.0, y=0.0, z=0.0), carla.Rotation(yaw=0.0))
bbox = carla.BoundingBox(carla.Location(x=0.0, y=0.0, z=0.0), carla.Vector3D(x=2.0, y=1.0, z=1.0))
vertices = list(bbox.get_world_vertices(actor_tf))
body = make(tf(0.0, 0.0))
basis = body._camera_basis(body.world.get_spectator().get_transform())
origin_np = body._np_location(body.world.get_spectator().get_transform().location)
screen = [body._world_to_pixel(body._np_location(v), origin_np, basis, 90.0, 1920, 1080) for v in vertices]
hull = cv2.convexHull(np.array(screen, dtype=np.float32))
hit = cv2.pointPolygonTest(hull, (959.5, 539.5), False) >= 0
miss = cv2.pointPolygonTest(hull, (300.0, 200.0), False) >= 0
check("T7 车体中心命中/远处不命中", hit and not miss, f"命中={hit} 误命中={miss}")

# T8 射线→地面 解析解（真实机位，相机高 5.732m）
transform = tf(-23.445, 179.536, -15.720, -63.145, 5.732)
body = make(transform)
origin, d = body._ray_from_pixel(959.5, 770.0)
point = body._ground_point_from_ray(origin, d)
expect_dist = 5.732 / math.tan(math.radians(23.445 + 0.0))
check("T8 地面落点存在", point is not None, "" if point is None else f"x={point.x:.2f} y={point.y:.2f} z={point.z:.2f}")
if point is not None:
    horizontal = math.hypot(point.x - transform.location.x, point.y - transform.location.y)
    check("T8b 落点距离合理(5~30m)", 5.0 < horizontal < 30.0, f"水平距离={horizontal:.2f}m")

# T9 视角太平 → 无地面落点
body = make(tf(0.0, 0.0))
origin, d = body._ray_from_pixel(959.5, 539.5)
check("T9 水平视角拒绝落点", body._ground_point_from_ray(origin, d) is None, "")

# T10 画面坐标映射：缩放 + 居中偏移
body = make(tf(0.0, 0.0), size=(1920, 1080))
body.preview_scale = 0.5
body.preview_offset = (10.0, 20.0)
uv = body._pixel_to_image(types.SimpleNamespace(x=10 + 500 * 0.5, y=20 + 300 * 0.5))
check("T10 Label→原图坐标", uv is not None and abs(uv[0] - 500) < 1e-6 and abs(uv[1] - 300) < 1e-6, f"uv={uv}")
out = body._pixel_to_image(types.SimpleNamespace(x=5, y=5))
check("T10b 画面外返回 None", out is None, f"uv={out}")

print()
print(f"结果：PASS={PASS} FAIL={FAIL}")
sys.exit(0 if FAIL == 0 else 1)



