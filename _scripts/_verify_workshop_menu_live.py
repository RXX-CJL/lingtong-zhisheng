# -*- coding: utf-8 -*-
r"""真实 CARLA 验证：选中黄框 + 右键菜单背后的朝向编辑方法。

用法：py -3.12 E:\output\_scripts\_verify_workshop_menu_live.py（需 CARLA 已启动）
"""
import importlib.util
import sys
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

PASS = 0
FAIL = 0


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
    else:
        FAIL += 1
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(detail) if detail else ""))


client = carla.Client("127.0.0.1", 2000)
client.set_timeout(10.0)
world = client.get_world()
anchor = world.get_map().get_spawn_points()[0]

root = tk.Tk()
root.withdraw()
app = Workshop(root)
app.client = client
app.world = world
app.connected = True
app._refresh_blueprints()
app.start_camera()
time.sleep(1.5)

cam_tf = carla.Transform(carla.Location(x=anchor.location.x, y=anchor.location.y, z=anchor.location.z + 25.0),
                         carla.Rotation(pitch=-90.0, yaw=0.0))
world.get_spectator().set_transform(cam_tf)
app.camera.set_transform(cam_tf)
time.sleep(1.8)

bp = world.get_blueprint_library().find("vehicle.tesla.model3")
actor = world.try_spawn_actor(bp, carla.Transform(
    carla.Location(x=anchor.location.x, y=anchor.location.y, z=anchor.location.z + 1.0),
    carla.Rotation(yaw=0.0)))
check("vehicle spawned", actor is not None)
if actor is None:
    app.stop_camera(); root.destroy(); sys.exit(2)
world.wait_for_tick(2.0)
app.owned_vehicle_ids.append(actor.id)
app.selected_vehicle_id = actor.id

# 1) 选中黄框
frame = app.latest_rgb
check("camera frame available", frame is not None, None if frame is None else frame.shape)
if frame is not None:
    original = frame.copy()
    drawn = app._draw_selection(frame.copy())
    changed = int((drawn != original).any(axis=2).sum())
    check("selection box drawn", changed > 50, "changed_pixels=%d" % changed)

# 2) 朝向 +90（菜单项调用的同一方法）
before = float(actor.get_transform().rotation.yaw)
app._set_vehicle_yaw(actor.id, delta=90.0)
world.wait_for_tick(2.0)
after = float(actor.get_transform().rotation.yaw)
check("yaw +90 on server", abs(((after - before) % 360.0) - 90.0) < 1.0, "before=%.1f after=%.1f" % (before, after))

# 3) 朝向绝对值（输入角度菜单）
app._set_vehicle_yaw(actor.id, absolute=37.0)
world.wait_for_tick(2.0)
check("yaw absolute on server", abs(float(actor.get_transform().rotation.yaw) - 37.0) < 1.0,
      actor.get_transform().rotation.yaw)

# 4) 对齐车道
app._align_vehicle_to_lane(actor.id)
world.wait_for_tick(2.0)
waypoint = world.get_map().get_waypoint(actor.get_location(), project_to_road=True)
lane_yaw = float(waypoint.transform.rotation.yaw) if waypoint is not None else None
check("align to lane", lane_yaw is not None and abs(float(actor.get_transform().rotation.yaw) - lane_yaw) < 1.0,
      "vehicle=%.1f lane=%s" % (float(actor.get_transform().rotation.yaw), lane_yaw))

# 5) 删除菜单背后的方法（只测方法存在性，避免真删）
check("delete by id method exists", hasattr(app, "_delete_vehicle_by_id"))

# 清理
try:
    actor.destroy()
except Exception:
    pass
world.wait_for_tick(2.0)
app.owned_vehicle_ids = []
app.selected_vehicle_id = None
app.stop_camera()
root.destroy()

print()
print("RESULT PASS=%d FAIL=%d" % (PASS, FAIL))
sys.exit(0 if FAIL == 0 else 1)
