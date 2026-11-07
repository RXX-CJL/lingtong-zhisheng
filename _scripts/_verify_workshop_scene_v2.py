# -*- coding: utf-8 -*-
r"""场景 v2 真实 CARLA round-trip 验收（连 127.0.0.1:2000，Town10HD_Opt）。

用法：py -3.12 E:\output\_scripts\_verify_workshop_scene_v2.py

约束：不改 spectator 最终机位（测试中临时设过，finally 原样恢复）；不 load_world；
本次测试生成的所有 actor 在 finally 里 destroy。
"""
import importlib.util
import json
import sys
import tempfile
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
FAILED_NAMES = []


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
    else:
        FAIL += 1
        FAILED_NAMES.append(name)
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(detail) if detail else ""))


def dist(a, b):
    return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2) ** 0.5


def yaw_delta(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


tmpdir = Path(tempfile.mkdtemp(prefix="workshop_scene_v2_"))
SAVE_PATH = str(tmpdir / "scene_v2.json")
V1_PATH = str(tmpdir / "scene_v1.json")
state = {"load_path": SAVE_PATH}
dialog_log = []
HAS_TRAFFIC_LIGHTS = False

# 全部无对话框：monkeypatch 文件选择与提示框
module.filedialog.asksaveasfilename = lambda **kw: (dialog_log.append(("save", kw)),
                                                    SAVE_PATH)[1]
module.filedialog.askopenfilename = lambda **kw: (dialog_log.append(("open", kw)),
                                                  state["load_path"])[1]
module.messagebox.askyesno = lambda *a, **kw: (dialog_log.append(("askyesno", a)), True)[1]
module.messagebox.showwarning = lambda *a, **kw: dialog_log.append(("warn", a))
module.messagebox.showerror = lambda *a, **kw: dialog_log.append(("error", a))
module.messagebox.showinfo = lambda *a, **kw: dialog_log.append(("info", a))

root = tk.Tk()
root.withdraw()
app = Workshop(root)
root.update()

app.connect()
check("connect", app.connected, app.status_var.get())
check("map is Town10HD_Opt", "Town10HD_Opt" in app.world.get_map().name, app.world.get_map().name)

world = app.world
spectator = world.get_spectator()
world.wait_for_tick(1.0)
ORIGINAL_SPECTATOR = spectator.get_transform()
ORIGINAL_WEATHER = world.get_weather()
INITIAL_ACTOR_IDS = {actor.id for actor in world.get_actors()}
extra_actors = []


def tl_durations_snapshot():
    """{light_id: (green, yellow, red)}；set_*_time 是永久改写，靠这个验证是否被还原。"""
    snap = {}
    for light in world.get_actors().filter("traffic.traffic_light*"):
        try:
            snap[light.id] = (round(light.get_green_time(), 3),
                              round(light.get_yellow_time(), 3),
                              round(light.get_red_time(), 3))
        except Exception:
            continue
    return snap


BASELINE_TL = tl_durations_snapshot()
print("BASELINE tl durations: %s (n=%d)" % (sorted(set(BASELINE_TL.values())), len(BASELINE_TL)))


def destroy_test_actors():
    """销毁本工具记账的 actor + 任何临时探测 actor。"""
    for actor_id in list(app.owned_vehicle_ids) + list(app.owned_prop_ids):
        actor = app._live_actor(actor_id)
        if actor is not None:
            try:
                actor.destroy()
            except Exception:
                pass
    for actor in extra_actors:
        try:
            if actor.is_alive:
                actor.destroy()
        except Exception:
            pass
    extra_actors.clear()
    app.owned_vehicle_ids.clear()
    app.owned_prop_ids.clear()
    app.autopilot_ids.clear()
    app.vehicle_modes.clear()
    app.target_speed_by_vehicle.clear()
    app.ignore_lights_by_vehicle.clear()
    app.selected_vehicle_id = None


def spawn_car(bp, point):
    actor = world.try_spawn_actor(bp, point)
    if actor is None:
        return None
    app.owned_vehicle_ids.append(actor.id)
    return actor


try:
    # ---------- 1. 摆 3 辆车（不同 behavior_mode）+ 1 个 static.prop ----------
    spawn_points = world.get_map().get_spawn_points()
    check("spawn points available", len(spawn_points) >= 16, len(spawn_points))

    model3 = None
    for bp in world.get_blueprint_library().filter("vehicle.*"):
        if bp.id == "vehicle.tesla.model3":
            model3 = bp
            break
    if model3 is None:
        model3 = list(world.get_blueprint_library().filter("vehicle.*"))[0]

    plans = [("obey", 0, 40.0), ("parked", 4, None), ("run_light", 8, None)]
    expected = []
    for mode, index, speed in plans:
        actor = spawn_car(model3, spawn_points[index])
        if actor is None:
            continue
        expected.append({"mode": mode, "bp": actor.type_id, "id": actor.id})
    check("3 vehicles spawned", len(expected) == 3, len(expected))
    # 新 actor 要先被 get_actors() 感知，否则 set_vehicle_behavior 里的 _live_actor 会返回 None
    for _ in range(3):
        world.wait_for_tick(1.0)
    # 按生成顺序逐车设行为（此时 3 辆都在 get_actors() 里了）
    for (mode, index, speed), actor_id in zip(plans, list(app.owned_vehicle_ids)):
        app.set_vehicle_behavior(actor_id, mode)
        if speed is not None:
            app.target_speed_by_vehicle[actor_id] = speed
    check("behavior modes recorded in app",
          sorted(str(m) for m in app.vehicle_modes.values()) == sorted(["obey", "parked", "run_light"]),
          app.vehicle_modes)
    app._wait_one_tick()

    prop_bp = None
    for candidate in ("static.prop.constructioncone", "static.prop.streetbarrier",
                      "static.prop.trafficcone01"):
        try:
            prop_bp = world.get_blueprint_library().find(candidate)
            break
        except Exception:
            prop_bp = None
    prop_actor = None
    if prop_bp is not None:
        base = spawn_points[14].location
        prop_actor = world.try_spawn_actor(prop_bp, carla.Transform(
            carla.Location(x=base.x, y=base.y, z=base.z + 0.15), carla.Rotation(yaw=0.0)))
        if prop_actor is not None:
            app.owned_prop_ids.append(prop_actor.id)
    check("1 static.prop spawned", prop_actor is not None, prop_bp.id if prop_bp else "no blueprint")
    app._wait_one_tick()

    # ---------- 2. 红绿灯配时 12/2/15（宽容口径：本图无灯则 SKIP） ----------
    probe_lights = list(world.get_actors().filter("traffic.traffic_light*"))
    print("READONLY traffic.traffic_light* count = %d" % len(probe_lights))
    for light in probe_lights[:3]:
        try:
            print("  sample: id=%s opendrive=%s group=%d" % (
                light.id, light.get_opendrive_id(), len(light.get_group_traffic_lights())))
        except Exception as exc:
            print("  sample read failed:", exc)
    HAS_TRAFFIC_LIGHTS = len(probe_lights) > 0
    if not HAS_TRAFFIC_LIGHTS:
        print("SKIP 本图无红绿灯 actor，配时恢复未在实机验证")
    tl_group = []
    tl_oD_id = None
    if HAS_TRAFFIC_LIGHTS:
        app.scan_traffic_lights()
        check("traffic lights scanned", len(app.tl_actors) > 0, len(app.tl_actors))
        app.green_var.set("12")
        app.yellow_var.set("2")
        app.red_var.set("15")
        app.start_custom_timing()
        check("custom timing running", bool(app.tl_running), app.tl_durations)
        tl_group = list(app.tl_group_ids)
        tl_anchor = app._selected_tl()
        tl_oD_id = str(tl_anchor.get_opendrive_id()) if tl_anchor is not None else None
        check("tl opendrive id captured", bool(tl_oD_id), tl_oD_id)

    # ---------- 3. 非默认天气 + 手动一次 spectator 机位 ----------
    weather = world.get_weather()
    weather.cloudiness = 77.0
    weather.precipitation = 33.0
    weather.fog_density = 21.0
    weather.sun_azimuth_angle = 202.0
    weather.sun_altitude_angle = 17.0
    weather.wetness = 44.0
    world.set_weather(weather)
    app._read_weather()
    check("weather applied", abs(world.get_weather().cloudiness - 77.0) < 1e-3,
          world.get_weather().cloudiness)

    first_actor = app._live_actor(app.owned_vehicle_ids[0])
    base = first_actor.get_transform().location
    TEST_CAMERA = carla.Transform(
        carla.Location(x=base.x - 14.0, y=base.y - 8.0, z=base.z + 9.0),
        carla.Rotation(pitch=-21.0, yaw=123.5, roll=0.0))
    spectator.set_transform(TEST_CAMERA)
    if app.camera is not None:
        app.camera.set_transform(TEST_CAMERA)
    # 异步世界下 spectator 的读回有传输延迟，轮询到目标值或超时
    moved_yaw = None
    for _ in range(20):
        world.wait_for_tick(1.0)
        moved_yaw = spectator.get_transform().rotation.yaw
        if yaw_delta(moved_yaw, 123.5) < 0.01:
            break
    check("spectator moved", moved_yaw is not None and yaw_delta(moved_yaw, 123.5) < 0.01,
          moved_yaw)

    app.selected_vehicle_id = app.owned_vehicle_ids[1]
    app.global_diff_var.set("-12")
    app.fps_var.set("15")

    # 归位：行为模式（obey/run_light）会让车自己开走，保存时的位置就会漂移，
    # 加载时那些位置既可能被占用也可能互相碰撞。归位到生成点 + 归零速度，位置断言才有确定基准。
    for (mode, index, speed), actor_id in zip(plans, list(app.owned_vehicle_ids)):
        actor = app._live_actor(actor_id)
        if actor is None:
            continue
        try:
            actor.set_target_velocity(carla.Vector3D(0, 0, 0))
            actor.set_transform(spawn_points[index])
        except Exception as exc:
            print("reset vehicle failed:", actor_id, exc)
    if app.camera is not None:
        app.camera.set_transform(TEST_CAMERA)
    world.wait_for_tick(1.0)
    world.wait_for_tick(1.0)
    print("RESET vehicles back to spawn points before save")

    # ---------- 4. save_scene（无对话框路径） ----------
    app.save_scene()
    check("save dialog called", any(kind == "save" for kind, _ in dialog_log))
    saved_file = Path(SAVE_PATH)
    check("saved file exists", saved_file.is_file(), SAVE_PATH)
    check("no .tmp leftover after save", not saved_file.with_name(saved_file.name + ".tmp").exists())

    data = json.loads(saved_file.read_text(encoding="utf-8"))
    # 留一份真实产物给交付报告核对字段
    evidence = Path(__file__).resolve().parent / "_scene_v2_roundtrip_sample.json"
    try:
        evidence.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print("SCENE SAMPLE saved to", evidence)
    except Exception as exc:
        print("scene sample dump failed:", exc)
    check("format is v2", data.get("format") == "carla_creator_workshop_scene_v2", data.get("format"))
    check("vehicles recorded = 3", len(data.get("vehicles", [])) == 3,
          len(data.get("vehicles", [])))
    check("props recorded = 1", len(data.get("props", [])) == 1, len(data.get("props", [])))
    weather_fields = data.get("weather", {})
    check("weather fields > 4", len(weather_fields) >= 10, len(weather_fields))
    for key in ("sun_azimuth_angle", "sun_altitude_angle", "wetness", "fog_falloff"):
        check("weather field " + key, key in weather_fields, weather_fields.get(key))
    check("weather fields == 14 (0.9.16 real fields)",
          len(weather_fields) == 14, len(weather_fields))
    modes = sorted(str(item.get("behavior_mode")) for item in data["vehicles"])
    check("behavior modes recorded", modes == sorted(["obey", "parked", "run_light"]), modes)
    check("autopilot flags recorded",
          all(isinstance(item.get("autopilot"), bool) for item in data["vehicles"]),
          [item.get("autopilot") for item in data["vehicles"]])
    check("target_speed recorded", any(item.get("target_speed_kmh") == 40.0
                                       for item in data["vehicles"]),
          [item.get("target_speed_kmh") for item in data["vehicles"]])
    check("ignore_lights_percent key present",
          all("ignore_lights_percent" in item for item in data["vehicles"]))
    cam = data.get("camera") or {}
    check("camera recorded", isinstance(cam.get("transform"), dict), cam)
    check("camera yaw recorded", cam.get("transform") is not None
          and yaw_delta(cam["transform"]["rotation"]["yaw"], 123.5) < 0.01,
          (cam.get("transform") or {}).get("rotation"))
    check("camera fov/size recorded", cam.get("fov") == 90.0 and cam.get("image_size_x") == 960,
          (cam.get("fov"), cam.get("image_size_x"), cam.get("image_size_y")))
    tl_data = data.get("traffic_lights") or {}
    check("traffic_lights key present in v2", "traffic_lights" in data, list(data.keys()))
    if HAS_TRAFFIC_LIGHTS:
        check("tl running recorded", bool(tl_data.get("running")), tl_data.get("running"))
        durations = tl_data.get("durations") or {}
        check("tl durations 12/2/15",
              abs(durations.get("Green", 0) - 12.0) < 1e-6
              and abs(durations.get("Yellow", 0) - 2.0) < 1e-6
              and abs(durations.get("Red", 0) - 15.0) < 1e-6, durations)
        check("tl group recorded",
              sorted(tl_data.get("group_actor_ids") or []) == sorted(tl_group),
              tl_data.get("group_actor_ids"))
        check("tl opendrive id recorded", str(tl_data.get("opendrive_id")) == tl_oD_id,
              tl_data.get("opendrive_id"))
    else:
        print("SKIP 红绿灯字段断言（本图无灯）")
    check("hidden_environment_objects empty dict",
          data.get("hidden_environment_objects") == {}, data.get("hidden_environment_objects"))
    session = data.get("session") or {}
    check("session global diff", session.get("global_speed_diff_percent") == "-12", session)
    check("session fps", session.get("record_fps") == "15", session.get("record_fps"))
    check("session resolution", session.get("camera_resolution") == "960x540",
          session.get("camera_resolution"))

    # 销毁前记录期望值
    expected_state = []
    for item in expected:
        actor = app._live_actor(item["id"])
        if actor is None:
            print("DIAG expected actor missing:", item["id"])
            continue
        t = actor.get_transform()
        expected_state.append({"mode": item["mode"], "bp": item["bp"],
                               "location": (t.location.x, t.location.y, t.location.z),
                               "yaw": t.rotation.yaw})
    check("expected states captured", len(expected_state) == 3, len(expected_state))
    prop_transform = prop_actor.get_transform() if prop_actor is not None else None

    # ---------- 5. 销毁全部 actor 后 load_scene ----------
    app.stop_custom_timing(silent=True)
    destroy_test_actors()
    root.update()
    world.wait_for_tick(1.0)
    check("all owned actors destroyed", not app.owned_vehicle_ids and not app.owned_prop_ids)
    leftover = [actor.id for actor in world.get_actors() if actor.id not in INITIAL_ACTOR_IDS]
    check("cleanup destroyed every actor we created", leftover == [], leftover)

    dialog_log.clear()
    app.load_scene()
    check("load dialog called", any(kind == "open" for kind, _ in dialog_log))
    check("load reported no error dialog", not any(kind == "error" for kind, _ in dialog_log),
          [a[0] for k, a in dialog_log if k == "error"])

    # 实测：try_spawn_actor 返回后立刻 get_transform 拿到的是 (0,0,0)，必须等一帧才是真实位姿。
    # 但等太多帧 autopilot（obey）车会被 TM 开走。折中：等 2 帧再量（TM 2 帧位移 < 0.05m）。
    world.wait_for_tick(1.0)
    world.wait_for_tick(1.0)
    snapshot_now = []
    for actor_id in list(app.owned_vehicle_ids):
        actor = app._live_actor(actor_id)
        if actor is None:
            continue
        t = actor.get_transform()
        snapshot_now.append({"id": actor_id, "bp": actor.type_id,
                             "location": (t.location.x, t.location.y, t.location.z),
                             "yaw": t.rotation.yaw,
                             "mode": app.vehicle_modes.get(actor_id),
                             "autopilot": actor_id in app.autopilot_ids})

    check("vehicle count restored", len(app.owned_vehicle_ids) == 3,
          (app.owned_vehicle_ids, app.status_var.get()))
    check("prop count restored", len(app.owned_prop_ids) == 1, app.owned_prop_ids)
    if len(app.owned_vehicle_ids) != 3:
        print("DIAG owned=", app.owned_vehicle_ids, "props=", app.owned_prop_ids)
        print("DIAG status=", app.status_var.get())
        print("DIAG warn dialogs=", [a[0] for k, a in dialog_log if k == "warn"])
        print("DIAG loaded json vehicles=", [v.get("blueprint") for v in data.get("vehicles", [])])
        live = {a.id: a.type_id for a in world.get_actors()}
        print("DIAG live actors=", live)

    restored = snapshot_now
    check("restored blueprints match",
          sorted(r["bp"] for r in restored) == sorted(e["bp"] for e in expected_state),
          [r["bp"] for r in restored])
    check("restored behavior modes match",
          sorted(str(r["mode"]) for r in restored) == sorted(str(e["mode"]) for e in expected_state),
          [r["mode"] for r in restored])

    # 实测：x/y 完全一致（差 0.000），只有 z 差 0.12~0.34m —— 这是车生成后悬挂落到路面的物理沉降，
    # 不是还原精度损失。位置精度按水平面（x/y）判定，z 单列并按物理沉降容差判。
    max_err = 0.0
    max_z = 0.0
    max_yaw = 0.0
    for exp in (expected_state if restored else []):
        match = min(restored, key=lambda r: (r["location"][0] - exp["location"][0]) ** 2
                    + (r["location"][1] - exp["location"][1]) ** 2)
        err = ((match["location"][0] - exp["location"][0]) ** 2
               + (match["location"][1] - exp["location"][1]) ** 2) ** 0.5
        dz = abs(match["location"][2] - exp["location"][2])
        max_err = max(max_err, err)
        max_z = max(max_z, dz)
        max_yaw = max(max_yaw, yaw_delta(match["yaw"], exp["yaw"]))
        print("  PER-VEH mode=%s xy_err=%.5f dz=%.5f dyaw=%.4f exp=(%.3f,%.3f,%.3f) got=(%.3f,%.3f,%.3f)"
              % (exp["mode"], err, dz, yaw_delta(match["yaw"], exp["yaw"]),
                 exp["location"][0], exp["location"][1], exp["location"][2],
                 match["location"][0], match["location"][1], match["location"][2]))
    check("transform error (x/y) < 0.05m", max_err < 0.05, round(max_err, 5))
    check("z drift within suspension drop (< 0.6m)", max_z < 0.6, round(max_z, 5))
    check("yaw error < 0.5deg", max_yaw < 0.5, round(max_yaw, 4))

    prop_restored = app._live_actor(app.owned_prop_ids[0]) if app.owned_prop_ids else None
    check("prop restored same blueprint",
          prop_restored is not None and prop_restored.type_id == (prop_bp.id if prop_bp else None),
          prop_restored.type_id if prop_restored is not None else "missing")
    if prop_restored is not None and prop_transform is not None:
        perr = dist(prop_restored.get_transform().location, prop_transform.location)
        check("prop transform error < 0.05m", perr < 0.05, round(perr, 5))

    weather_now = world.get_weather()
    check("weather cloudiness restored", abs(weather_now.cloudiness - 77.0) < 1e-3,
          weather_now.cloudiness)
    check("weather azimuth restored", abs(weather_now.sun_azimuth_angle - 202.0) < 1e-3,
          weather_now.sun_azimuth_angle)
    check("weather wetness restored", abs(weather_now.wetness - 44.0) < 1e-3, weather_now.wetness)

    spectator_now = spectator.get_transform()
    check("spectator yaw restored", yaw_delta(spectator_now.rotation.yaw, 123.5) < 0.5,
          spectator_now.rotation.yaw)
    check("spectator location restored", dist(spectator_now.location, TEST_CAMERA.location) < 0.05,
          round(dist(spectator_now.location, TEST_CAMERA.location), 4))

    if HAS_TRAFFIC_LIGHTS:
        check("custom timing restored", bool(app.tl_running), app.tl_running)
        tl_now = app._live_actor(tl_group[0]) if tl_group else None
        if tl_now is not None:
            check("tl green secs restored", abs(tl_now.get_green_time() - 12.0) < 1e-3,
                  tl_now.get_green_time())
            check("tl yellow secs restored", abs(tl_now.get_yellow_time() - 2.0) < 1e-3,
                  tl_now.get_yellow_time())
            check("tl red secs restored", abs(tl_now.get_red_time() - 15.0) < 1e-3,
                  tl_now.get_red_time())
        else:
            check("tl actor found after load", False, "group anchor missing")
    else:
        print("SKIP 红绿灯配时恢复断言（本图无灯），load_scene 未报错即视为通过")
    check("session selected vehicle restored (by index)", app.selected_vehicle_id in app.owned_vehicle_ids,
          app.selected_vehicle_id)
    check("session selected is the 2nd vehicle",
          app.selected_vehicle_id == app.owned_vehicle_ids[1], app.owned_vehicle_ids)
    check("session global diff restored", app.global_diff_var.get() == "-12",
          app.global_diff_var.get())
    check("session fps restored", app.fps_var.get() == "15", app.fps_var.get())
    app.stop_custom_timing(silent=True)

    # ---------- 6. 自动存档：直接调用路径写真实 last_session.json ----------
    auto_path = module.AUTO_SAVE_PATH
    app.auto_save_var.set("")
    saved_ok = app.run_auto_save()
    check("auto save returned True", saved_ok is True, app.auto_save_var.get())
    check("auto save file exists", auto_path.is_file(), str(auto_path))
    check("auto save real path under 场景快照",
          auto_path.name == "last_session.json" and auto_path.parent.name == "场景快照",
          str(auto_path))
    check("auto save left no .tmp",
          not auto_path.with_name(auto_path.name + ".tmp").exists(),
          [p.name for p in auto_path.parent.iterdir()])
    auto_json = json.loads(auto_path.read_text(encoding="utf-8"))
    check("auto save format v2", auto_json.get("format") == module.SCENE_FORMAT_V2,
          auto_json.get("format"))
    check("auto save flagged", auto_json.get("auto_save") is True, auto_json.get("auto_save"))
    check("auto save status text updated", "已写入" in app.auto_save_var.get(),
          app.auto_save_var.get())

    # 自动存档必须能被 load_scene 正常读回
    destroy_test_actors()
    root.update()
    world.wait_for_tick(1.0)
    state["load_path"] = str(auto_path)
    dialog_log.clear()
    app.load_scene()
    app._wait_one_tick()
    check("auto save reloadable by load_scene",
          not any(kind == "error" for kind, _ in dialog_log)
          and len(app.owned_vehicle_ids) == 3,
          ([a[0] for k, a in dialog_log if k == "error"], app.owned_vehicle_ids))
    app.stop_custom_timing(silent=True)
    state["load_path"] = SAVE_PATH

    # stop_custom_timing 必须把同组灯的绿/黄/红秒数写回原值（set_*_time 是永久改写）
    restored_tl = tl_durations_snapshot()
    check("stop_custom_timing restored tl durations to baseline",
          restored_tl == BASELINE_TL,
          {k: (BASELINE_TL.get(k), v) for k, v in restored_tl.items() if BASELINE_TL.get(k) != v})

    # 录制中不写坏文件
    check("auto save skipped while recording",
          app._auto_save_allowed() is True, app.recording)
    app.recording = True
    before = auto_path.read_text(encoding="utf-8")
    skipped = app.run_auto_save()
    after = auto_path.read_text(encoding="utf-8")
    app.recording = False
    check("auto save skips while recording", skipped is False and before == after,
          app.auto_save_var.get())

    # ---------- 6b. K2 回归：恢复后的手动驱动车必须朝车头方向走 ----------
    # 自动存档重载后 actor id 已变，必须按当前存活车重算
    manual_ids = [actor_id for actor_id in app.owned_vehicle_ids
                  if actor_id not in app.autopilot_ids
                  and app.vehicle_modes.get(actor_id) in ("run_light", "reverse", "lane_cross")]
    check("has manual-driven vehicle to verify K2", len(manual_ids) > 0,
          [(i, app.vehicle_modes.get(i)) for i in app.owned_vehicle_ids])
    if manual_ids:
        actor = app._live_actor(manual_ids[0])
        # 加载时刚下过油门，先让它跑起来再取起点，否则 2 帧内位移接近 0 会误判成"没动"
        app._drive_forward(actor, 8.0)
        for _ in range(10):
            world.wait_for_tick(1.0)
        start = actor.get_transform().location
        forward = actor.get_transform().get_forward_vector()
        app._drive_forward(actor, 8.0)
        for _ in range(40):
            world.wait_for_tick(1.0)
        end = actor.get_transform().location
        moved = carla.Vector3D(end.x - start.x, end.y - start.y, end.z - start.z)
        length = (moved.x ** 2 + moved.y ** 2 + moved.z ** 2) ** 0.5
        dot = ((moved.x * forward.x + moved.y * forward.y) / length) if length > 1e-6 else 0.0
        check("manual drive moves forward (K2: no reversed constant_velocity)",
              length > 0.3 and dot > 0.8,
              "moved=%.2fm dot=%.3f start=(%.2f,%.2f,%.2f) end=(%.2f,%.2f,%.2f) fwd=(%.2f,%.2f) mode=%s"
              % (length, dot, start.x, start.y, start.z, end.x, end.y, end.z,
                 forward.x, forward.y, app.vehicle_modes.get(manual_ids[0])))

    # ---------- 7. v1 向后兼容 ----------
    destroy_test_actors()
    root.update()
    world.wait_for_tick(1.0)

    v1_point = spawn_points[2]
    v1_data = {
        "format": "carla_creator_workshop_scene_v1",
        "map": world.get_map().name.rsplit("/", 1)[-1],
        "weather": {"cloudiness": 10.0, "precipitation": 0.0, "fog_density": 0.0,
                    "sun_altitude_angle": 45.0},
        "vehicles": [{"blueprint": model3.id,
                      "transform": {"location": {"x": v1_point.location.x,
                                                 "y": v1_point.location.y,
                                                 "z": v1_point.location.z},
                                    "rotation": {"pitch": 0.0, "yaw": v1_point.rotation.yaw,
                                                 "roll": 0.0}}}],
        "saved_at": "2026-10-23 00:00:00",
    }
    Path(V1_PATH).write_text(json.dumps(v1_data, ensure_ascii=False, indent=2), encoding="utf-8")
    state["load_path"] = V1_PATH
    dialog_log.clear()
    v1_error = None
    try:
        app.load_scene()
    except Exception as exc:
        v1_error = exc
    app._wait_one_tick()
    check("v1 load did not raise", v1_error is None, v1_error)
    check("v1 load spawned 1 vehicle", len(app.owned_vehicle_ids) == 1,
          (app.owned_vehicle_ids, app.status_var.get(),
           [a[0] for k, a in dialog_log if k in ("warn", "error")]))
    if len(app.owned_vehicle_ids) != 1:
        print("DIAG v1 dialogs=", dialog_log)
        print("DIAG v1 status=", app.status_var.get())
        print("DIAG v1 json=", json.dumps(v1_data, ensure_ascii=False)[:400])
    check("v1 load no error dialog", not any(kind == "error" for kind, _ in dialog_log),
          [a[0] for k, a in dialog_log if k == "error"])
    check("v1 weather applied", abs(world.get_weather().cloudiness - 10.0) < 1e-3,
          world.get_weather().cloudiness)
finally:
    try:
        app.stop_custom_timing(silent=True)
    except Exception:
        pass
    # 收尾硬断言：15 盏灯必须全部回到地图原值（set_*_time 永久改写，必须验到）
    try:
        world.wait_for_tick(1.0)
        final_tl = tl_durations_snapshot()
        drift = {k: (BASELINE_TL.get(k), v) for k, v in final_tl.items()
                 if BASELINE_TL.get(k) != v}
        extra_lights = set(final_tl) - set(BASELINE_TL)
        check("FINAL all traffic lights back to baseline durations (%d lights)" % len(final_tl),
              not drift and not extra_lights and len(final_tl) == len(BASELINE_TL),
              {"drift": drift, "new": extra_lights,
               "baseline": sorted(set(BASELINE_TL.values())),
               "now": sorted(set(final_tl.values()))})
        check("FINAL traffic light count unchanged", len(final_tl) == len(BASELINE_TL),
              (len(BASELINE_TL), len(final_tl)))
    except Exception as exc:
        check("FINAL traffic light baseline check", False, exc)
    try:
        destroy_test_actors()
    except Exception:
        pass
    try:
        world.set_weather(ORIGINAL_WEATHER)
    except Exception:
        pass
    # 机位必须原样还给用户：设完等帧校验，不一致就重试
    restored_ok = False
    for attempt in range(5):
        try:
            spectator.set_transform(ORIGINAL_SPECTATOR)
            if app.camera is not None:
                app.camera.set_transform(ORIGINAL_SPECTATOR)
            world.wait_for_tick(1.0)
            now = spectator.get_transform()
            if (yaw_delta(now.rotation.yaw, ORIGINAL_SPECTATOR.rotation.yaw) < 0.01
                    and dist(now.location, ORIGINAL_SPECTATOR.location) < 0.01):
                restored_ok = True
                break
        except Exception as exc:
            print("spectator restore attempt %d failed: %s" % (attempt, exc))
    final = spectator.get_transform()
    print("SPECTATOR RESTORE ok=%s | target yaw=%.2f loc=(%.3f, %.3f, %.3f) | now yaw=%.2f loc=(%.3f, %.3f, %.3f)"
          % (restored_ok, ORIGINAL_SPECTATOR.rotation.yaw, ORIGINAL_SPECTATOR.location.x,
             ORIGINAL_SPECTATOR.location.y, ORIGINAL_SPECTATOR.location.z,
             final.rotation.yaw, final.location.x, final.location.y, final.location.z))
    if not restored_ok:
        print("!! WARNING: spectator NOT restored — 需要人工确认机位 !!" + chr(10) +
              "TARGET_JSON " + json.dumps(module.CarlaCreatorWorkshop._transform_to_dict(ORIGINAL_SPECTATOR)))
    try:
        root.update()
        app.close()
    except Exception:
        pass

print()
if not HAS_TRAFFIC_LIGHTS:
    print("NOTE 本图无红绿灯 actor，配时恢复未在实机验证（SKIP，不计 FAIL）")
print("RESULT PASS=%d FAIL=%d" % (PASS, FAIL))
if FAILED_NAMES:
    print("FAILED: " + ", ".join(FAILED_NAMES))
sys.exit(0 if FAIL == 0 else 1)
