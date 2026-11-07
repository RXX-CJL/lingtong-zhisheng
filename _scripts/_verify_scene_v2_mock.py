# -*- coding: utf-8 -*-
r"""场景 v2 序列化层 mock 验收：用真实 carla 值类型 + 假 world，不需要 CARLA 服务端。

用法：py -3.12 E:\output\_scripts\_verify_scene_v2_mock.py
"""
import importlib.util
import json
import sys
from pathlib import Path

import tkinter as tk

TARGET = (Path(__file__).resolve().parents[1] / "1" / "carla" / "CARLA_0.9.16"
          / "PythonAPI" / "examples" / "carla_creator_workshop.py")
spec = importlib.util.spec_from_file_location("carla_creator_workshop", TARGET)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
Workshop = module.CarlaCreatorWorkshop
carla = module.carla

PASS = 0
FAIL = 0
FAILED = []


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
    else:
        FAIL += 1
        FAILED.append(name)
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(detail) if detail else ""))


class FakeActor:
    def __init__(self, actor_id, type_id, transform):
        self.id = actor_id
        self.type_id = type_id
        self._transform = transform
        self.is_alive = True
        self.autopilot = None
        self.destroyed = False

    def get_transform(self):
        return self._transform

    def set_transform(self, t):
        self._transform = t

    def get_location(self):
        return self._transform.location

    def set_autopilot(self, flag, port=None):
        self.autopilot = flag

    def destroy(self):
        self.destroyed = True
        self.is_alive = False


class FakeLight:
    def __init__(self, actor_id, opendrive_id, group, dur=(20.0, 3.0, 25.0)):
        self.id = actor_id
        self._od = opendrive_id
        self._group = group
        self.green, self.yellow, self.red = dur
        self.state = carla.TrafficLightState.Green

    def get_opendrive_id(self):
        return self._od

    def get_group_traffic_lights(self):
        return self._group

    def get_green_time(self):
        return self.green

    def get_yellow_time(self):
        return self.yellow

    def get_red_time(self):
        return self.red

    def set_green_time(self, v):
        self.green = v

    def set_yellow_time(self, v):
        self.yellow = v

    def set_red_time(self, v):
        self.red = v

    def set_state(self, s):
        self.state = s

    def get_state(self):
        return self.state

    def reset_group(self):
        pass


class FakeActorList(list):
    def filter(self, pattern):
        base = pattern.rstrip("*")
        return FakeActorList([a for a in self if str(a.type_id).startswith(base)])


class FakeMap:
    def __init__(self, name="Carla/Maps/Town10HD_Opt"):
        self.name = name

    def get_spawn_points(self):
        return []


class FakeWorld:
    def __init__(self):
        self.actors = FakeActorList()
        self.weather = carla.WeatherParameters()
        self._map = FakeMap()

    def get_map(self):
        return self._map

    def get_actors(self):
        return self.actors

    def get_actor(self, actor_id):
        for a in self.actors:
            if a.id == actor_id:
                return a
        return None

    def get_weather(self):
        return self.weather

    def set_weather(self, w):
        self.weather = w

    def spawn_actor(self, bp, transform):
        raise RuntimeError("not needed")


root = tk.Tk()
root.withdraw()
app = Workshop(root)
root.update()

world = FakeWorld()
app.world = world
app.connected = True

# ---------- 1. transform 往返精度 ----------
t = carla.Transform(carla.Location(x=12.3456789, y=-7.654321, z=0.123456),
                    carla.Rotation(pitch=-3.25, yaw=137.75, roll=1.5))
back = app._dict_to_transform(app._transform_to_dict(t))
check("transform roundtrip x", abs(back.location.x - t.location.x) < 1e-9, back.location.x)
check("transform roundtrip yaw", abs(back.rotation.yaw - t.rotation.yaw) < 1e-9, back.rotation.yaw)
check("transform roundtrip roll", abs(back.rotation.roll - t.rotation.roll) < 1e-9, back.rotation.roll)

# ---------- 2. weather 全字段 ----------
names = app._weather_field_names()
check("weather field list >= 14", len(names) >= 14, len(names))
# 0.9.16 实测：WeatherParameters 有 14 个数值字段，没有 reflection_intensity
for field in ("cloudiness", "sun_azimuth_angle", "sun_altitude_angle",
              "precipitation", "precipitation_deposits", "wind_intensity", "fog_density",
              "fog_distance", "fog_falloff", "wetness", "scattering_intensity",
              "mie_scattering_scale", "rayleigh_scattering_scale", "dust_storm"):
    check("weather field present: " + field, field in names, None)
check("weather field count is 14", len(names) == 14, names)
check("no bogus reflection_intensity", "reflection_intensity" not in names)

world.weather.cloudiness = 88.5
world.weather.sun_azimuth_angle = 311.0
world.weather.wetness = 0.42
wdata = app._weather_to_dict()
check("weather dict records cloudiness", abs(wdata["cloudiness"] - 88.5) < 1e-9, wdata["cloudiness"])
check("weather dict records azimuth", abs(wdata["sun_azimuth_angle"] - 311.0) < 1e-9,
      wdata["sun_azimuth_angle"])
check("weather dict records wetness", abs(wdata["wetness"] - 0.42) < 1e-6, wdata["wetness"])
check("weather dict json-serializable", isinstance(json.dumps(wdata), str))

# 回填：按 hasattr 容错，未知键忽略
app._apply_scene_weather({"cloudiness": 12.0, "unknown_future_field": 9.9,
                          "sun_azimuth_angle": 45.0})
check("weather apply known field", abs(world.weather.cloudiness - 12.0) < 1e-9,
      world.weather.cloudiness)
check("weather apply ignores unknown field", True)
app._apply_scene_weather({})
check("weather apply empty dict safe", True)
app._apply_scene_weather("not a dict")
check("weather apply non-dict safe", True)

# ---------- 3. 车辆字段完整性 ----------
world.actors = FakeActorList()
v1 = FakeActor(101, "vehicle.tesla.model3",
               carla.Transform(carla.Location(1, 2, 3), carla.Rotation(yaw=10)))
v2 = FakeActor(102, "vehicle.audi.a2",
               carla.Transform(carla.Location(4, 5, 6), carla.Rotation(yaw=20)))
world.actors.extend([v1, v2])
app.owned_vehicle_ids = [101, 102]
app.autopilot_ids = {101}
app.vehicle_modes = {101: "obey", 102: "run_light"}
app.target_speed_by_vehicle = {101: 33.0}
app.ignore_lights_by_vehicle = {102: 100.0}
app.selected_vehicle_id = 102
app.owned_prop_ids = []
app.global_diff_var.set("-15")
app.fps_var.set("30")

scene = app._scene_to_dict()
check("scene format v2", scene["format"] == module.SCENE_FORMAT_V2, scene["format"])
check("scene vehicles = 2", len(scene["vehicles"]) == 2, len(scene["vehicles"]))
veh = {item["blueprint"]: item for item in scene["vehicles"]}
check("vehicle autopilot recorded", veh["vehicle.tesla.model3"]["autopilot"] is True)
check("vehicle autopilot false recorded", veh["vehicle.audi.a2"]["autopilot"] is False)
check("vehicle behavior_mode recorded", veh["vehicle.audi.a2"]["behavior_mode"] == "run_light")
check("vehicle target_speed recorded", veh["vehicle.tesla.model3"]["target_speed_kmh"] == 33.0)
check("vehicle ignore_lights recorded", veh["vehicle.audi.a2"]["ignore_lights_percent"] == 100.0)
check("vehicle ignore_lights None when unknown",
      veh["vehicle.tesla.model3"]["ignore_lights_percent"] is None)
check("scene has props key", "props" in scene and scene["props"] == [])
check("scene has traffic_lights key", "traffic_lights" in scene)
check("scene has camera key", "camera" in scene)
check("scene has hidden_environment_objects key", "hidden_environment_objects" in scene)
check("hidden env default {}", scene["hidden_environment_objects"] == {})
check("scene has session", isinstance(scene.get("session"), dict))
check("session selected vehicle id", scene["session"]["selected_vehicle_id"] == 102)
check("session selected vehicle index", scene["session"]["selected_vehicle_index"] == 1,
      scene["session"]["selected_vehicle_index"])
check("session global diff", scene["session"]["global_speed_diff_percent"] == "-15")
check("session fps", scene["session"]["record_fps"] == "30")
check("scene json-serializable", isinstance(json.dumps(scene, ensure_ascii=False), str))

# ---------- 4. 道具 ----------
prop = FakeActor(201, "static.prop.constructioncone",
                 carla.Transform(carla.Location(9, 9, 0.2), carla.Rotation(yaw=0)))
world.actors.append(prop)
app.owned_prop_ids = [201]
scene = app._scene_to_dict()
check("props recorded", len(scene["props"]) == 1, scene["props"])
check("prop blueprint recorded", scene["props"][0]["blueprint"] == "static.prop.constructioncone")

# ---------- 5. 红绿灯 ----------
light_a = FakeLight(301, "TLS_4", [])
light_b = FakeLight(302, "TLS_4", [])
light_a._group = [light_a, light_b]
light_b._group = [light_a, light_b]
world.actors.extend([light_a, light_b])
app.tl_actors = [light_a, light_b]
app.tl_group_ids = [301, 302]
app.tl_durations = {"Green": 12.0, "Yellow": 2.0, "Red": 15.0}
app.tl_phase = "Yellow"
app.tl_running = True
app.tl_combo["values"] = ["a", "b"]
app.tl_combo.current(0)
tl_data = app._traffic_lights_to_dict()
check("tl opendrive id", tl_data["opendrive_id"] == "TLS_4", tl_data["opendrive_id"])
check("tl group ids", tl_data["group_actor_ids"] == [301, 302], tl_data["group_actor_ids"])
check("tl durations", tl_data["durations"] == {"Green": 12.0, "Yellow": 2.0, "Red": 15.0},
      tl_data["durations"])
check("tl phase", tl_data["phase"] == "Yellow", tl_data["phase"])
check("tl running", tl_data["running"] is True)

# 恢复：秒数回填到界面变量
app.green_var.set("99")
app.yellow_var.set("99")
app.red_var.set("99")
app.tl_running = False
app._restore_traffic_lights({"opendrive_id": "TLS_4", "group_actor_ids": [301, 302],
                             "durations": {"Green": 12.0, "Yellow": 2.0, "Red": 15.0},
                             "phase": "Green", "running": False})
check("tl durations restored to UI vars", app.green_var.get() == "12"
      and app.yellow_var.get() == "2" and app.red_var.get() == "15",
      (app.green_var.get(), app.yellow_var.get(), app.red_var.get()))
check("tl not restarted when running=False", app.tl_running is False)

# ---------- 6. hidden_environment_objects：超 int64 的 id 必须原样 ----------
BIG = 16740775638937321093
check("big id exceeds int64", BIG > 2 ** 63 - 1, BIG)
app.hidden_env_ids = {"Buildings": [BIG, 12345], "Vegetation": []}
hidden = app._hidden_env_to_dict()
check("hidden env key preserved", "Buildings" in hidden, list(hidden))
check("hidden env big id exact", hidden["Buildings"][0] == BIG, hidden["Buildings"][0])
check("hidden env ids are python int",
      all(type(x) is int for x in hidden["Buildings"]), [type(x) for x in hidden["Buildings"]])
text = json.dumps({"hidden_environment_objects": hidden}, ensure_ascii=False)
reloaded = json.loads(text)["hidden_environment_objects"]["Buildings"][0]
check("hidden env big id survives JSON", reloaded == BIG, reloaded)
del app.hidden_env_ids
check("hidden env absent attr -> {}", app._hidden_env_to_dict() == {},
      app._hidden_env_to_dict())

# ---------- 7. 相机 ----------
class FakeSpectator:
    def __init__(self):
        self.t = carla.Transform(carla.Location(-11, 22, 33),
                                 carla.Rotation(pitch=-12.5, yaw=203.25, roll=0))
        self.set_calls = []

    def get_transform(self):
        return self.t

    def set_transform(self, t):
        self.t = t
        self.set_calls.append(t)


spec_actor = FakeSpectator()


class WorldWithSpectator(FakeWorld):
    def get_spectator(self):
        return spec_actor


app.world = WorldWithSpectator()
cam = app._camera_to_dict()
check("camera fov recorded", cam["fov"] == 90.0, cam["fov"])
check("camera size recorded", cam["image_size_x"] == 960 and cam["image_size_y"] == 540,
      (cam["image_size_x"], cam["image_size_y"]))
check("camera transform recorded", cam["transform"] is not None)
check("camera yaw recorded", abs(cam["transform"]["rotation"]["yaw"] - 203.25) < 1e-9,
      cam["transform"]["rotation"]["yaw"])

app.camera = None
spec_actor.set_calls.clear()
app._restore_camera(cam)
check("camera restore sets spectator", len(spec_actor.set_calls) == 1, len(spec_actor.set_calls))
check("camera restore yaw exact",
      abs(spec_actor.t.rotation.yaw - 203.25) < 1e-6, spec_actor.t.rotation.yaw)
app._restore_camera({})
check("camera restore empty dict safe", True)
app._restore_camera(None)
check("camera restore None safe", True)

# ---------- 8. session 回填 ----------
app.selected_vehicle_id = None
app.global_diff_var.set("0")
app.fps_var.set("20")
app.target_speed_var.set("30")
app.owned_vehicle_ids = [701, 702, 703]   # 模拟重新生成后的新 id
app._apply_scene_session({"selected_vehicle_index": 1, "selected_vehicle_id": 102,
                          "global_speed_diff_percent": "-30",
                          "target_speed_kmh": "55", "record_fps": "10",
                          "ignore_lights_percent": "100"})
check("session selected restored by index (id changed)", app.selected_vehicle_id == 702,
      app.selected_vehicle_id)
check("session diff restored", app.global_diff_var.get() == "-30", app.global_diff_var.get())
check("session speed restored", app.target_speed_var.get() == "55", app.target_speed_var.get())
check("session fps restored", app.fps_var.get() == "10", app.fps_var.get())
check("session ignore lights restored", app.ignore_lights_var.get() == "100",
      app.ignore_lights_var.get())
app.selected_vehicle_id = None
app._apply_scene_session({"selected_vehicle_index": 99, "selected_vehicle_id": 99999})
check("session drops out-of-range index and unknown id", app.selected_vehicle_id is None,
      app.selected_vehicle_id)
# 只有旧 id、没有索引的存档：能匹配就恢复
app.selected_vehicle_id = None
app._apply_scene_session({"selected_vehicle_id": 703})
check("session legacy id fallback works", app.selected_vehicle_id == 703,
      app.selected_vehicle_id)
app._apply_scene_session(None)
check("session None safe", True)

# ---------- 9. v1 兼容：_apply_vehicle_item 不看 autopilot 字段时的默认 ----------
# 注意：第 7 节把 app.world 换成了 WorldWithSpectator，这里必须换回来，否则 _live_actor 找不到 actor
app.world = world
world.actors = FakeActorList()
v3 = FakeActor(401, "vehicle.tesla.model3", carla.Transform(carla.Location(), carla.Rotation()))
world.actors.append(v3)
app.owned_vehicle_ids = [401]
app.autopilot_ids = set()
app.vehicle_modes = {}
app.auto_var.set(True)
v1_item = {"blueprint": "vehicle.tesla.model3",
           "transform": app._transform_to_dict(v3.get_transform())}
app._apply_vehicle_item(401, v1_item, module.SCENE_FORMAT_V1)
check("v1 item uses auto_var for autopilot", v3.autopilot is True and 401 in app.autopilot_ids,
      (v3.autopilot, 401 in app.autopilot_ids))

v4 = FakeActor(402, "vehicle.tesla.model3", carla.Transform(carla.Location(), carla.Rotation()))
world.actors.append(v4)
app.owned_vehicle_ids = [402]
app.autopilot_ids = set()
app.auto_var.set(False)
v1_item2 = dict(v1_item)
app._apply_vehicle_item(402, v1_item2, module.SCENE_FORMAT_V1)
check("v1 item honors auto_var False", v4.autopilot is not True and 402 not in app.autopilot_ids,
      (v4.autopilot, 402 in app.autopilot_ids))

# v2 明确 autopilot=False 时不开启
v5 = FakeActor(403, "vehicle.tesla.model3", carla.Transform(carla.Location(), carla.Rotation()))
world.actors.append(v5)
app.owned_vehicle_ids = [403]
app.autopilot_ids = set()
app.auto_var.set(True)  # 全局开关不该影响 v2 的显式值
app._apply_vehicle_item(403, {"blueprint": "vehicle.tesla.model3",
                              "transform": app._transform_to_dict(v5.get_transform()),
                              "autopilot": False, "behavior_mode": None,
                              "target_speed_kmh": None, "ignore_lights_percent": None},
                        module.SCENE_FORMAT_V2)
check("v2 explicit autopilot False wins over auto_var", 403 not in app.autopilot_ids,
      403 in app.autopilot_ids)
check("v2 explicit autopilot False set on actor", v5.autopilot is False, v5.autopilot)

# ---------- 10. 原子写：覆盖写 + 无 tmp 残留 ----------
tmp = Path(__file__).resolve().parent / "_tmp_scene_v2_mock"
import shutil
shutil.rmtree(tmp, ignore_errors=True)
target_path = tmp / "nested" / "scene.json"
app._write_json_atomic(target_path, {"a": 1})
app._write_json_atomic(target_path, {"a": 2})
check("atomic overwrite works", json.loads(target_path.read_text(encoding="utf-8"))["a"] == 2)
check("atomic created parent dir", target_path.parent.is_dir())
check("atomic no tmp file", [p.name for p in target_path.parent.iterdir()] == ["scene.json"],
      [p.name for p in target_path.parent.iterdir()])

# ---------- 11. 红绿灯原始配时快照/还原（set_*_time 是永久改写） ----------
world.actors = FakeActorList()
la = FakeLight(901, "TLS_X", [], dur=(10.0, 3.0, 2.0))
lb = FakeLight(902, "TLS_X", [], dur=(10.0, 3.0, 2.0))
la._group = [la, lb]
lb._group = [la, lb]
world.actors.extend([la, lb])
app.world = world
app.tl_actors = [la, lb]
app.tl_combo["values"] = ["a", "b"]
app.tl_combo.current(0)
app.tl_group_ids = [901, 902]
app.tl_original_durations = {}
app.tl_durations = {"Green": 20.0, "Yellow": 3.0, "Red": 25.0}

check("tl original snapshot starts empty", app.tl_original_durations == {})

# 模拟 start_custom_timing 的关键步骤（不触发 on_tick/消息框）
app.tl_group_ids = [901, 902]
app._tl_snapshot_durations()
snap = dict(app.tl_original_durations)
check("snapshot captured 2 lights", len(snap) == 2, snap)
check("snapshot green original", snap.get(901, (None,))[0] == 10.0, snap.get(901))
check("snapshot yellow original", snap.get(901, (None, None))[1] == 3.0, snap.get(901))
check("snapshot red original", snap.get(901, (None, None, None))[2] == 2.0, snap.get(901))

# 二次快照不得覆盖（避免把改过的值当原值）
app._tl_snapshot_durations()
check("snapshot not overwritten on second call", app.tl_original_durations == snap,
      app.tl_original_durations)

# 改成 12/2/15
app.tl_durations = {"Green": 12.0, "Yellow": 2.0, "Red": 15.0}
app._tl_apply_phase("Green")
check("durations changed by apply_phase",
      (la.green, la.yellow, la.red) == (12.0, 2.0, 15.0), (la.green, la.yellow, la.red))
check("second light also changed",
      (lb.green, lb.yellow, lb.red) == (12.0, 2.0, 15.0), (lb.green, lb.yellow, lb.red))

# stop 收尾：写回原值
restored = app._tl_restore_durations()
check("restore wrote back 2 lights", restored == 2, restored)
check("light A restored to 10/3/2", (la.green, la.yellow, la.red) == (10.0, 3.0, 2.0),
      (la.green, la.yellow, la.red))
check("light B restored to 10/3/2", (lb.green, lb.yellow, lb.red) == (10.0, 3.0, 2.0),
      (lb.green, lb.yellow, lb.red))
check("snapshot cleared after restore", app.tl_original_durations == {}, app.tl_original_durations)

# 无快照时不得瞎写
before = (la.green, la.yellow, la.red)
again = app._tl_restore_durations()
check("restore with no snapshot returns 0", again == 0, again)
check("restore with no snapshot leaves lights untouched",
      (la.green, la.yellow, la.red) == before, (la.green, la.yellow, la.red))

# stop_custom_timing 端到端：真的会调写回
app.tl_group_ids = [901, 902]
app.tl_original_durations = {}
app._tl_snapshot_durations()
app.tl_durations = {"Green": 12.0, "Yellow": 2.0, "Red": 15.0}
app._tl_apply_phase("Green")
app.tl_running = False
app.tl_tick_id = None
app.stop_custom_timing(silent=True)
check("stop_custom_timing restored light A", (la.green, la.yellow, la.red) == (10.0, 3.0, 2.0),
      (la.green, la.yellow, la.red))
check("stop_custom_timing restored light B", (lb.green, lb.yellow, lb.red) == (10.0, 3.0, 2.0),
      (lb.green, lb.yellow, lb.red))

# 写回失败必须吞异常，不影响停止流程
class BadLight(FakeLight):
    def set_green_time(self, v):
        raise RuntimeError("boom")


bad = BadLight(903, "TLS_X", [], dur=(10.0, 3.0, 2.0))
world.actors.append(bad)
app.tl_group_ids = [903]
app.tl_original_durations = {}
app._tl_snapshot_durations()
app.tl_original_durations = {903: (10.0, 3.0, 2.0)}
try:
    n = app._tl_restore_durations()
    ok = True
except Exception as exc:
    ok = False
    n = exc
check("restore swallows write errors", ok and n == 0, n)

try:
    app.close()
    closed = True
except Exception as exc:
    closed = False
    print("close traceback:", exc)
check("close clean", closed)
shutil.rmtree(tmp, ignore_errors=True)

print()
print("RESULT PASS=%d FAIL=%d" % (PASS, FAIL))
if FAILED:
    print("FAILED: " + ", ".join(FAILED))
sys.exit(0 if FAIL == 0 else 1)
