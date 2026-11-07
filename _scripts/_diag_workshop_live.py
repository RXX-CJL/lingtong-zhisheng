# -*- coding: utf-8 -*-
r"""诊断：CARLA 真实环境里的相机位姿、反投影射线、LabelledPoint 结构。

用法：py -3.12 E:\output\_scripts\_diag_workshop_live.py（需 CARLA 已启动）
"""
import importlib.util
import time
import tkinter as tk
from pathlib import Path

TARGET = (Path(__file__).resolve().parents[1] / "1" / "carla" / "CARLA_0.9.16"
          / "PythonAPI" / "examples" / "carla_creator_workshop.py")
spec = importlib.util.spec_from_file_location("carla_creator_workshop", TARGET)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
Workshop = module.CarlaCreatorWorkshop
carla = module.carla

client = carla.Client("127.0.0.1", 2000)
client.set_timeout(10.0)
world = client.get_world()
anchor = world.get_map().get_spawn_points()[0]
base_z = float(anchor.location.z)
print("ANCHOR", round(anchor.location.x, 2), round(anchor.location.y, 2), "z", round(base_z, 2))

root = tk.Tk()
root.withdraw()
app = Workshop(root)
app.client = client
app.world = world
app.connected = True
app._refresh_blueprints()
app.start_camera()
time.sleep(1.2)

cam_tf = carla.Transform(carla.Location(x=anchor.location.x, y=anchor.location.y, z=base_z + 25.0),
                         carla.Rotation(pitch=-90.0, yaw=0.0))
world.get_spectator().set_transform(cam_tf)
app.camera.set_transform(cam_tf)
time.sleep(1.2)

cam = app.camera.get_transform()
print("SET_TF", round(cam_tf.location.x, 2), round(cam_tf.location.y, 2), round(cam_tf.location.z, 2),
      "pitch", cam_tf.rotation.pitch)
print("CAM_TF", round(cam.location.x, 2), round(cam.location.y, 2), round(cam.location.z, 2),
      "pitch", round(cam.rotation.pitch, 3), "yaw", round(cam.rotation.yaw, 3))
spec_tf = world.get_spectator().get_transform()
print("SPEC_TF", round(spec_tf.location.x, 2), round(spec_tf.location.y, 2), round(spec_tf.location.z, 2),
      "pitch", round(spec_tf.rotation.pitch, 3))

app.preview_frame_size = (int(app.camera_width), int(app.camera_height))
app.preview_scale = 1.0
app.preview_offset = (0.0, 0.0)
u, v = app.preview_frame_size[0] / 2.0 - 0.5, app.preview_frame_size[1] / 2.0 - 0.5
origin, direction = app._ray_from_pixel(u, v)
print("RAY_ORIGIN", [round(float(x), 2) for x in origin])
print("RAY_DIR", [round(float(x), 4) for x in direction])
point = app._ground_point_from_ray(origin, direction)
print("GROUND_POINT", "None" if point is None else [round(float(point.x), 2), round(float(point.y), 2), round(float(point.z), 2)])

probe = carla.Location(x=cam.location.x, y=cam.location.y, z=cam.location.z)
gp = world.ground_projection(probe, 300.0)
print("GP_TYPE", type(gp).__name__)
print("GP_ATTRS", [a for a in dir(gp) if not a.startswith("_")])
for attr in ("location", "point", "label"):
    try:
        print("GP_" + attr.upper(), getattr(gp, attr))
    except Exception as exc:
        print("GP_" + attr.upper(), "ERR", exc)

pp = world.project_point(carla.Location(x=cam.location.x, y=cam.location.y, z=cam.location.z),
                         carla.Vector3D(x=0.0, y=0.0, z=-1.0), 100.0)
print("PP_TYPE", type(pp).__name__)
for attr in ("location", "point", "label"):
    try:
        print("PP_" + attr.upper(), getattr(pp, attr))
    except Exception as exc:
        print("PP_" + attr.upper(), "ERR", exc)

rays = world.cast_ray(carla.Location(x=cam.location.x, y=cam.location.y, z=cam.location.z),
                      carla.Location(x=cam.location.x, y=cam.location.y, z=base_z - 1.0))
print("RAY_HITS", len(rays))
for item in rays[:3]:
    print("  HIT", type(item).__name__, getattr(item, "label", "?"), getattr(item, "location", "?"))

# 直接测一次 set_transform 是否可用
bp = world.get_blueprint_library().find("vehicle.tesla.model3")
spawn_tf = carla.Transform(carla.Location(x=anchor.location.x, y=anchor.location.y, z=base_z + 1.0),
                           carla.Rotation(yaw=0.0))
actor = world.try_spawn_actor(bp, spawn_tf)
if actor is not None:
    before = actor.get_location()
    print("SPAWNED", actor.id, [round(before.x, 2), round(before.y, 2), round(before.z, 2)])
    target = carla.Transform(carla.Location(x=before.x + 5.0, y=before.y, z=before.z),
                             actor.get_transform().rotation)
    try:
        actor.set_transform(target)
        after = actor.get_location()
        print("MOVED", [round(after.x, 2), round(after.y, 2), round(after.z, 2)])
    except Exception as exc:
        print("SET_TRANSFORM_ERR", exc)
    actor.destroy()

app.stop_camera()
root.destroy()
