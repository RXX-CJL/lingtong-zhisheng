# -*- coding: utf-8 -*-
r"""离线状态机测试：用 mock world 跑完 摆车 -> 拖动 -> 松手 -> 拾取 -> 撤销 -> 删除。

不需要启动 CARLA 服务端。用法：py -3.12 E:\output\_scripts\_verify_workshop_drag_flow.py
"""
import importlib.util
import sys
import types
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


class Var:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class FakeActor:
    next_id = 100

    def __init__(self, blueprint_id, transform):
        self.id = FakeActor.next_id
        FakeActor.next_id += 1
        self.type_id = blueprint_id
        self._transform = carla.Transform(
            carla.Location(x=transform.location.x, y=transform.location.y, z=transform.location.z),
            carla.Rotation(pitch=transform.rotation.pitch, yaw=transform.rotation.yaw, roll=transform.rotation.roll))
        self.autopilot = False
        self.destroyed = False
        self.bounding_box = carla.BoundingBox(carla.Location(x=0.0, y=0.0, z=0.0),
                                              carla.Vector3D(x=2.0, y=1.0, z=0.75))

    def get_transform(self):
        t = self._transform
        return carla.Transform(carla.Location(x=t.location.x, y=t.location.y, z=t.location.z),
                               carla.Rotation(pitch=t.rotation.pitch, yaw=t.rotation.yaw, roll=t.rotation.roll))

    def set_transform(self, transform):
        self._transform = carla.Transform(
            carla.Location(x=transform.location.x, y=transform.location.y, z=transform.location.z),
            carla.Rotation(pitch=transform.rotation.pitch, yaw=transform.rotation.yaw, roll=transform.rotation.roll))

    def get_location(self):
        t = self._transform
        return carla.Location(x=t.location.x, y=t.location.y, z=t.location.z)

    def set_target_velocity(self, velocity):
        self.velocity = velocity

    def disable_constant_velocity(self):
        pass

    def set_autopilot(self, enabled, tm_port=8000):
        self.autopilot = enabled

    def destroy(self):
        self.destroyed = True


class FakeActors:
    def __init__(self, actors):
        self._actors = actors

    def filter(self, pattern):
        return [a for a in self._actors if not a.destroyed]


class FakeMap:
    def get_waypoint(self, location, project_to_road=True):
        return types.SimpleNamespace(transform=carla.Transform(
            carla.Location(x=location.x, y=location.y, z=0.0), carla.Rotation(yaw=90.0)))


class FakeWorld:
    def __init__(self, camera_transform):
        self.actors = []
        self._camera_transform = camera_transform

    def get_spectator(self):
        return types.SimpleNamespace(get_transform=lambda: self._camera_transform)

    def get_actors(self):
        return FakeActors(self.actors)

    def get_actor(self, actor_id):
        for actor in self.actors:
            if actor.id == actor_id and not actor.destroyed:
                return actor
        return None

    def get_blueprint_library(self):
        return types.SimpleNamespace(find=lambda blueprint_id: types.SimpleNamespace(id=blueprint_id))

    def try_spawn_actor(self, blueprint, transform):
        actor = FakeActor(blueprint.id, transform)
        self.actors.append(actor)
        return actor

    def ground_projection(self, location, distance):
        return carla.Location(x=location.x, y=location.y, z=0.0)

    def project_point(self, *args):
        return None

    def get_map(self):
        return FakeMap()


def make_app(camera_transform):
    app = object.__new__(Workshop)
    app.connected = True
    app.camera = None
    app.world = FakeWorld(camera_transform)
    app.preview_frame_size = (1920, 1080)
    app.preview_scale = 1.0
    app.preview_offset = (0.0, 0.0)
    app.place_on_click_var = Var(True)
    app.drag_vehicle_var = Var(True)
    app.snap_lane_var = Var(False)
    app.restore_autopilot_var = Var(False)
    app.vehicle_var = Var("vehicle.tesla.model3")
    app.owned_vehicle_ids = []
    app.owned_prop_ids = []
    app.vehicle_modes = {}
    app.autopilot_ids = set()
    app.drag_state = None
    app.selected_vehicle_id = None
    app.undo_stack = []
    app.speed_rows = []
    app.speed_combo = {"values": []}
    app.messages = []
    app.set_status = lambda text: app.messages.append(text)
    return app


def event_at(x, y):
    return types.SimpleNamespace(x=x, y=y, widget=None)


# 俯视机位：10m 高、垂直向下，中心像素落在 (0,0) 地面
camera = carla.Transform(carla.Location(x=0.0, y=0.0, z=10.0), carla.Rotation(pitch=-90.0, yaw=0.0))
app = make_app(camera)
center = (959.5, 539.5)

app._on_preview_press(event_at(*center))
check("click empty spawns one vehicle", len(app.world.actors) == 1, app.messages[-1])
check("spawn recorded in undo stack", app.undo_stack and app.undo_stack[-1][0] == "spawn", app.undo_stack)
check("drag state armed after spawn", app.drag_state is not None)
actor = app.world.actors[0]
check("spawned at ground point z=0.2", abs(actor.get_location().z - 0.2) < 1e-6, actor.get_location().z)

# 拖动：绕过 40ms 节流
app.drag_state["last_time"] = 0.0
app._on_preview_drag(event_at(1200.0, 900.0))
moved = actor.get_location()
check("drag moved the vehicle", abs(moved.x) + abs(moved.y) > 0.5, (round(moved.x, 2), round(moved.y, 2)))

app._on_preview_release(event_at(1200.0, 900.0))
check("drag state cleared on release", app.drag_state is None)
landed = actor.get_location()
check("release snaps to ground height 0.1", abs(landed.z - 0.1) < 1e-6, landed.z)
check("autopilot stays off by default", actor.autopilot is False)

# 再拾取：把车当前位置投影回像素，应该能点中
basis = app._camera_basis(camera)
origin_np = app._np_location(camera.location)
pixel = app._world_to_pixel(app._np_location(landed), origin_np, basis, 90.0, 1920, 1080)
app._on_preview_press(event_at(pixel[0], pixel[1]))
check("press on vehicle picks it", app.drag_state is not None and app.drag_state["actor_id"] == actor.id,
      None if app.drag_state is None else app.drag_state["actor_id"])
check("pick records a move undo entry", app.undo_stack[-1][0] == "move", app.undo_stack[-1][0])
app._on_preview_release(event_at(pixel[0], pixel[1]))

# 朝向编辑（右键菜单调用的同一方法）
before_yaw = actor.get_transform().rotation.yaw
app._set_vehicle_yaw(actor.id, delta=90.0)
after_yaw = actor.get_transform().rotation.yaw
check("yaw +90 works", abs((after_yaw - before_yaw) - 90.0) < 1e-6, "%s -> %s" % (before_yaw, after_yaw))
app._set_vehicle_yaw(actor.id, absolute=15.0)
check("yaw absolute works", abs(actor.get_transform().rotation.yaw - 15.0) < 1e-6,
      actor.get_transform().rotation.yaw)
app.undo_last_placement()
restored = actor.get_location()
check("undo move restores position", abs(restored.x - landed.x) < 1e-6 and abs(restored.y - landed.y) < 1e-6,
      (round(restored.x, 2), round(restored.y, 2)))
app.undo_last_placement()
check("undo spawn removes vehicle", actor.destroyed and app.owned_vehicle_ids == [], app.owned_vehicle_ids)

# 删除选中车辆
app2 = make_app(camera)
app2._on_preview_press(event_at(*center))
target = app2.world.actors[0]
app2._on_preview_release(event_at(*center))
app2.delete_selected_vehicle()
check("delete selected destroys vehicle", target.destroyed and app2.owned_vehicle_ids == [], app2.messages[-1])

print()
print("RESULT PASS=%d FAIL=%d" % (PASS, FAIL))
sys.exit(0 if FAIL == 0 else 1)
