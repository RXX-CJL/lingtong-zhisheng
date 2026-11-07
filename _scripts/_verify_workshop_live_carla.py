# -*- coding: utf-8 -*-
r"""真实 CARLA 三级验证：点击摆车 / 拖动 / 松手落地 / 拾取 / 撤销 / 删除 + 三个投射 API 实测。

需要先启动 CARLA（127.0.0.1:2000）。用法：
    py -3.12 E:\output\_scripts\_verify_workshop_live_carla.py
证据写入 E:\output\_carla_batch2_live_verify.json
"""
import importlib.util
import json
import math
import sys
import time
import tkinter as tk
import types
from pathlib import Path

TARGET = (Path(__file__).resolve().parents[1] / "1" / "carla" / "CARLA_0.9.16"
          / "PythonAPI" / "examples" / "carla_creator_workshop.py")
RESULT_PATH = Path(__file__).resolve().parents[1] / "_carla_batch2_live_verify.json"

spec = importlib.util.spec_from_file_location("carla_creator_workshop", TARGET)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
Workshop = module.CarlaCreatorWorkshop
carla = module.carla

PASS = 0
FAIL = 0
EVIDENCE = {}


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
    else:
        FAIL += 1
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(detail) if detail else ""))
    EVIDENCE.setdefault("checks", []).append({"name": name, "ok": bool(ok), "detail": str(detail)})


def wait_for_carla(timeout=180.0):
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(10.0)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            world = client.get_world()
            return client, world
        except Exception:
            time.sleep(3.0)
    return None, None


print("waiting for CARLA at 127.0.0.1:2000 ...")
client, world = wait_for_carla()
if world is None:
    print("FAIL carla not reachable")
    sys.exit(2)

map_name = world.get_map().name.rsplit("/", 1)[-1]
print("connected:", map_name, "server", client.get_server_version())
EVIDENCE["map"] = map_name
EVIDENCE["server"] = client.get_server_version()

# ---------- 三个投射 API 的真实行为（本轮未确证项） ----------
anchor = world.get_map().get_spawn_points()[0]
base_z = float(anchor.location.z)
anchor_ground = Workshop._as_location(world.ground_projection(
    carla.Location(x=anchor.location.x, y=anchor.location.y, z=base_z + 5.0), 100.0))
road_z = float(anchor_ground.z) if anchor_ground is not None else base_z
EVIDENCE["road_z"] = road_z
EVIDENCE["spawn_point_z"] = base_z
probe_origin = carla.Location(x=anchor.location.x, y=anchor.location.y, z=base_z + 5.0)
try:
    hit = world.project_point(probe_origin, carla.Vector3D(x=0.0, y=0.0, z=-1.0), 100.0)
    EVIDENCE["project_point"] = {"type": type(hit).__name__, "repr": str(hit)[:200]}
    check("project_point usable", Workshop._as_location(hit) is not None, type(hit).__name__)
except Exception as exc:
    EVIDENCE["project_point"] = {"error": str(exc)}
    check("project_point callable", False, exc)

try:
    ground = world.ground_projection(carla.Location(x=anchor.location.x, y=anchor.location.y, z=base_z + 5.0), 100.0)
    EVIDENCE["ground_projection"] = {"type": type(ground).__name__, "repr": str(ground)[:200]}
    check("ground_projection usable", Workshop._as_location(ground) is not None, type(ground).__name__)
    resolved = Workshop._as_location(ground)
    if resolved is not None:
        check("ground_projection near spawn", abs(float(resolved.z) - base_z) < 5.0,
              "ground_z=%.3f spawn_z=%.3f" % (float(resolved.z), base_z))
except Exception as exc:
    EVIDENCE["ground_projection"] = {"error": str(exc)}
    check("ground_projection callable", False, exc)

try:
    actors = world.cast_ray(carla.Location(x=anchor.location.x, y=anchor.location.y, z=base_z + 25.0),
                            carla.Location(x=anchor.location.x, y=anchor.location.y, z=base_z - 1.0))
    EVIDENCE["cast_ray"] = {"type": type(actors).__name__, "length": len(actors) if hasattr(actors, "__len__") else None,
                            "first_item_type": type(actors[0]).__name__ if actors else None}
    check("cast_ray returns list", isinstance(actors, list), type(actors).__name__)
except Exception as exc:
    EVIDENCE["cast_ray"] = {"error": str(exc)}
    check("cast_ray callable", False, exc)

# ---------- 启动工坊（隐藏窗口，不跑 Tk 事件循环，避免覆盖我们固定的坐标映射） ----------
root = tk.Tk()
root.withdraw()
app = Workshop(root)
app.client = client
app.world = world
app.connected = True
app.place_on_click_var.set(True)
app._refresh_blueprints()
app._read_weather()
app.start_camera()
time.sleep(1.5)

camera = app.camera
check("preview camera spawned", camera is not None)
check("camera frame received", app.latest_rgb is not None, None if app.latest_rgb is None else app.latest_rgb.shape)

width, height = int(app.camera_width), int(app.camera_height)
app.preview_frame_size = (width, height)
app.preview_scale = 1.0
app.preview_offset = (0.0, 0.0)

# 把相机放到第一条生成点正上方，垂直向下俯视
cam_tf = carla.Transform(carla.Location(x=anchor.location.x, y=anchor.location.y, z=base_z + 25.0),
                         carla.Rotation(pitch=-90.0, yaw=0.0))
world.get_spectator().set_transform(cam_tf)
camera.set_transform(cam_tf)
time.sleep(1.5)
EVIDENCE["camera_at"] = {"x": cam_tf.location.x, "y": cam_tf.location.y, "z": cam_tf.location.z}


def event_at(x, y):
    return types.SimpleNamespace(x=x, y=y, widget=app.preview)


def settle():
    """异步世界：等一帧让客户端缓存里的 actor 位姿更新。"""
    try:
        world.wait_for_tick(2.0)
    except Exception:
        pass


center_u, center_v = width / 2.0 - 0.5, height / 2.0 - 0.5

# ---------- 点击空地摆车 ----------
before_ids = set(app.owned_vehicle_ids)
app._on_preview_press(event_at(center_u, center_v))
new_ids = [i for i in app.owned_vehicle_ids if i not in before_ids]
check("click spawns one vehicle", len(new_ids) == 1, new_ids)
actor = world.get_actor(new_ids[0]) if new_ids else None
check("spawned actor exists in world", actor is not None)
settle()
spawned_loc = actor.get_location() if actor else None
if spawned_loc:
    horizontal = math.hypot(spawned_loc.x - anchor.location.x, spawned_loc.y - anchor.location.y)
    EVIDENCE["spawn"] = {"id": actor.id, "type": actor.type_id, "x": spawned_loc.x, "y": spawned_loc.y,
                         "z": spawned_loc.z, "offset_from_anchor_m": horizontal}
    check("spawn lands on clicked ground (<=3m)", horizontal < 3.0, "offset=%.2fm" % horizontal)
    check("spawn height near road", abs(spawned_loc.z - road_z) < 2.0,
          "z=%.2f road_z=%.2f" % (spawned_loc.z, road_z))

# ---------- 拖动 ----------
app.drag_state["last_time"] = 0.0
drag_pixel = (center_u + 200.0, center_v)
app._on_preview_drag(event_at(*drag_pixel))
settle()
moved_loc = actor.get_location() if actor else None
if moved_loc and spawned_loc:
    moved_m = math.hypot(moved_loc.x - spawned_loc.x, moved_loc.y - spawned_loc.y)
    EVIDENCE["drag"] = {"before": [spawned_loc.x, spawned_loc.y], "after": [moved_loc.x, moved_loc.y],
                        "moved_m": moved_m}
    check("drag moves vehicle (>1m)", moved_m > 1.0, "moved=%.2fm" % moved_m)

# ---------- 松手落地 ----------
before_release = actor.get_location() if actor else None
app._on_preview_release(event_at(*drag_pixel))
settle()
landed = actor.get_location() if actor else None
check("drag state cleared", app.drag_state is None)
if landed:
    EVIDENCE["release"] = {"z": landed.z, "road_z": road_z}
    check("release snaps to ground", abs(landed.z - road_z) < 2.0, "z=%.2f road_z=%.2f" % (landed.z, road_z))
    check("autopilot disabled after release", actor.id not in app.autopilot_ids)

# ---------- 再拾取（用真实反投影算出车所在像素） ----------
transform, fov = app._camera_pose()
settle()
basis = app._camera_basis(transform)
origin_np = app._np_location(transform.location)
pixel = app._world_to_pixel(app._np_location(actor.get_location()), origin_np, basis, fov, width, height)
check("vehicle projects into view", pixel is not None, pixel)
if pixel:
    app._on_preview_press(event_at(pixel[0], pixel[1]))
    picked = app.drag_state["actor_id"] if app.drag_state else None
    EVIDENCE["pick"] = {"pixel": [pixel[0], pixel[1]], "picked_id": picked, "expected_id": actor.id}
    check("press on vehicle picks it", picked == actor.id, "picked=%s expected=%s" % (picked, actor.id))
    app._on_preview_release(event_at(pixel[0], pixel[1]))

# ---------- 撤销 ----------
app.undo_last_placement()
settle()
check("undo move keeps vehicle", world.get_actors().find(actor.id) is not None)
app.undo_last_placement()
settle()
gone = world.get_actors().find(actor.id) is None
EVIDENCE["undo"] = {"actor_removed_after_second_undo": gone}
check("undo spawn removes vehicle", gone)

# ---------- 删除选中 ----------
before_ids = set(app.owned_vehicle_ids)
app._on_preview_press(event_at(center_u, center_v))
victim_id = [i for i in app.owned_vehicle_ids if i not in before_ids]
victim = world.get_actor(victim_id[0]) if victim_id else None
app._on_preview_release(event_at(center_u, center_v))
app.delete_selected_vehicle()
settle()
check("delete removes selected vehicle", victim is not None and world.get_actors().find(victim_id[0]) is None,
      victim_id[0] if victim_id else None)

# ---------- 收尾 ----------
app.remove_own_vehicles(confirm=False)
app.stop_camera()
EVIDENCE["cleanup_owned_vehicles"] = len(app.owned_vehicle_ids)
check("cleanup removes test vehicles", len(app.owned_vehicle_ids) == 0)
root.destroy()

EVIDENCE["result"] = {"pass": PASS, "fail": FAIL}
RESULT_PATH.write_text(json.dumps(EVIDENCE, ensure_ascii=False, indent=2), encoding="utf-8")
print()
print("RESULT PASS=%d FAIL=%d  evidence=%s" % (PASS, FAIL, RESULT_PATH))
sys.exit(0 if FAIL == 0 else 1)
