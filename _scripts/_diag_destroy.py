# -*- coding: utf-8 -*-
r"""诊断：CARLA 里 actor.destroy() 之后 get_actor 的可见性时序。"""
import time

import carla

client = carla.Client("127.0.0.1", 2000)
client.set_timeout(10.0)
world = client.get_world()
anchor = world.get_map().get_spawn_points()[0]
bp = world.get_blueprint_library().find("vehicle.tesla.model3")
tf = carla.Transform(carla.Location(x=anchor.location.x, y=anchor.location.y, z=anchor.location.z + 2.0))

actor = world.try_spawn_actor(bp, tf)
if actor is None:
    print("SPAWN_FAILED")
    raise SystemExit(2)
actor_id = actor.id
print("SPAWNED", actor_id)
world.wait_for_tick(2.0)
print("GET_AFTER_TICK", world.get_actor(actor_id) is not None)

try:
    actor.destroy()
    print("DESTROY_OK")
except Exception as exc:
    print("DESTROY_ERR", exc)

print("GET_IMMEDIATE", world.get_actor(actor_id) is not None)
world.wait_for_tick(2.0)
print("GET_AFTER_TICK2", world.get_actor(actor_id) is not None)
time.sleep(0.5)
print("GET_AFTER_SLEEP", world.get_actor(actor_id) is not None)
ids = [a.id for a in world.get_actors()]
print("IN_ACTOR_LIST", actor_id in ids, "vehicle_count", len(world.get_actors().filter("vehicle.*")))
