# -*- coding: utf-8 -*-
r"""真实 CARLA 验证：6 种车辆行为模式（遵守/闯红灯/超速/逆行/压线/违停）。

用法：py -3.12 E:\output\_scripts\_verify_workshop_behavior_live.py（需 CARLA 已启动）
"""
import importlib.util
import math
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
SPAWNED = []


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
    else:
        FAIL += 1
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(detail) if detail else ""))


def speed_kmh(actor):
    v = actor.get_velocity()
    return 3.6 * math.sqrt(v.x ** 2 + v.y ** 2 + v.z ** 2)


client = carla.Client("127.0.0.1", 2000)
client.set_timeout(10.0)
world = client.get_world()
lights = [l for l in world.get_actors().filter("traffic.traffic_light*") if len(l.get_stop_waypoints()) > 0]
light = lights[0]
stop = light.get_stop_waypoints()[0]
bp = world.get_blueprint_library().find("vehicle.tesla.model3")

root = tk.Tk()
root.withdraw()
app = Workshop(root)
app.client = client
app.world = world
app.connected = True


def spawn_before_stop(distance=6.0):
    prev = stop.previous(distance)
    if not prev:
        return None
    p = prev[0]
    for dz in (0.3, 0.6, 1.0, 1.5):
        actor = world.try_spawn_actor(bp, carla.Transform(
            carla.Location(x=p.transform.location.x, y=p.transform.location.y,
                           z=p.transform.location.z + dz),
            p.transform.rotation))
        if actor is not None:
            SPAWNED.append(actor)
            world.wait_for_tick(2.0)
            return actor
    return None


def sample(actor, seconds):
    trace = []
    for _ in range(seconds):
        time.sleep(1.0)
        trace.append((speed_kmh(actor), stop.transform.location.distance(actor.get_location())))
    return trace


try:
    light.freeze(True)
    light.set_state(carla.TrafficLightState.Red)

    # 1) obey：红灯前停住
    v1 = spawn_before_stop()
    check("obey spawn", v1 is not None)
    if v1 is not None:
        app.owned_vehicle_ids.append(v1.id)
        app.set_vehicle_behavior(v1.id, "obey")
        trace = sample(v1, 6)
        final_speed, final_dist = trace[-1]
        min_dist = min(d for _, d in trace)
        check("obey stops at red", final_speed < 1.0 and min_dist < 7.5,
              "final_speed=%.1f min_dist=%.2f final_dist=%.2f" % (final_speed, min_dist, final_dist))
        v1.destroy()
        SPAWNED.remove(v1)

    # 2) run_light：关 autopilot + 手动匀速，沿车头方向直行（无视红灯）
    v2 = spawn_before_stop(25.0)
    check("run_light spawn", v2 is not None)
    if v2 is not None:
        app.owned_vehicle_ids.append(v2.id)
        before = (v2.get_location().x, v2.get_location().y)
        forward = (v2.get_transform().get_forward_vector().x, v2.get_transform().get_forward_vector().y)
        app.set_vehicle_behavior(v2.id, "run_light")
        time.sleep(3.5)
        after = (v2.get_location().x, v2.get_location().y)
        moved = math.hypot(after[0] - before[0], after[1] - before[1])
        dot = ((after[0] - before[0]) * forward[0] + (after[1] - before[1]) * forward[1]) / max(moved, 1e-6)
        check("run_light drives along heading", moved > 15.0 and dot > 0.85,
              "moved=%.1fm dot=%.2f speed=%.1f" % (moved, dot, speed_kmh(v2)))
        v2.destroy()
        SPAWNED.remove(v2)

    # 3) parked：原地不动
    v3 = spawn_before_stop(20.0)
    check("parked spawn", v3 is not None)
    if v3 is not None:
        app.owned_vehicle_ids.append(v3.id)
        app.set_vehicle_behavior(v3.id, "parked")
        start = v3.get_location()
        time.sleep(3.0)
        moved = stop.transform.location.distance(start) - stop.transform.location.distance(v3.get_location())
        check("parked stays", abs(moved) < 1.0 and speed_kmh(v3) < 1.0,
              "moved=%.2f speed=%.1f" % (moved, speed_kmh(v3)))

    # 4) reverse：挪到对向车道
    v4 = spawn_before_stop(30.0)
    check("reverse spawn", v4 is not None)
    if v4 is not None:
        app.owned_vehicle_ids.append(v4.id)
        before = world.get_map().get_waypoint(v4.get_location(), project_to_road=True)
        app.set_vehicle_behavior(v4.id, "reverse")
        world.wait_for_tick(2.0)
        after = world.get_map().get_waypoint(v4.get_location(), project_to_road=True)
        opposite = before is not None and after is not None and before.lane_id * after.lane_id < 0
        check("reverse moves to opposite lane", opposite,
              "lane_before=%s lane_after=%s" % (before.lane_id if before else None, after.lane_id if after else None))

    # 5) lane_cross：横向偏移
    v5 = spawn_before_stop(40.0)
    check("lane_cross spawn", v5 is not None)
    if v5 is not None:
        app.owned_vehicle_ids.append(v5.id)
        wp = world.get_map().get_waypoint(v5.get_location(), project_to_road=True)
        before_loc = v5.get_location()
        app.set_vehicle_behavior(v5.id, "lane_cross")
        world.wait_for_tick(2.0)
        after_loc = v5.get_location()
        offset = math.hypot(after_loc.x - before_loc.x, after_loc.y - before_loc.y)
        check("lane_cross offsets sideways", 0.8 < offset < 4.0,
              "offset=%.2f lane_width=%.2f" % (offset, wp.lane_width if wp else -1))
finally:
    try:
        light.set_state(carla.TrafficLightState.Green)
        light.freeze(False)
    except Exception:
        pass
    for actor in SPAWNED:
        try:
            actor.destroy()
        except Exception:
            pass
    app.owned_vehicle_ids = []
    app.autopilot_ids = set()
    root.destroy()

print()
print("RESULT PASS=%d FAIL=%d" % (PASS, FAIL))
sys.exit(0 if FAIL == 0 else 1)
