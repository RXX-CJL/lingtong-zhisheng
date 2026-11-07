# -*- coding: utf-8 -*-
"""生成一辆车，再查它的材质对象名里有没有车牌相关。"""
import time
import carla

c = carla.Client("127.0.0.1", 2000); c.set_timeout(30.0)
w = c.get_world()

def names_snapshot():
    return set(w.get_names_of_all_objects())

before = names_snapshot()
print("生成前对象数:", len(before))

bp = w.get_blueprint_library().find("vehicle.tesla.model3")
wp = w.get_map().get_waypoint(carla.Location(x=109.93, y=-9.33, z=0.3), project_to_road=True)
tf = wp.transform; tf.location.z += 0.3
actor = w.try_spawn_actor(bp, tf)
if actor is None:
    print("生成失败"); raise SystemExit(1)
print("已生成 id=%d" % actor.id)
w.wait_for_tick(2.0); time.sleep(1.0)

after = names_snapshot()
new = sorted(after - before)
print("新增对象数:", len(new))
print("\n=== 新增对象中含 plate/Plate/License 的 ===")
hits = [n for n in new if any(k in n for k in ("Plate", "plate", "License", "license"))]
print("  命中:", len(hits))
for n in hits[:30]:
    print("   ", n)

print("\n=== 新增对象里含 tesla 的（前 25 个）===")
tl = [n for n in new if "tesla" in n.lower()]
print("  共", len(tl))
for n in tl[:25]:
    print("   ", n)

actor.destroy()
w.wait_for_tick(2.0)
print("\n已销毁测试车，对象数回到:", len(w.get_names_of_all_objects()))
