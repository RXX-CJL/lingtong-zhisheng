# -*- coding: utf-8 -*-
"""查 CARLA 车辆蓝图里是否自带车牌材质/贴图，以及蓝图属性有哪些可调。"""
import carla

c = carla.Client("127.0.0.1", 2000); c.set_timeout(30.0)
w = c.get_world()
bl = w.get_blueprint_library()

bp = bl.find("vehicle.tesla.model3")
print("=== tesla.model3 蓝图可调属性 ===")
for a in bp:
    try:
        print("   %-28s = %r" % (a.id, a.recommended_values if a.recommended_values else ""))
    except Exception as exc:
        print("   (读取失败)", exc)

print("\n=== 所有蓝图里含 plate/license 的属性 ===")
found = set()
for b in bl:
    for a in b:
        low = a.id.lower()
        if "plate" in low or "license" in low:
            found.add((b.id, a.id))
print("  命中:", len(found))
for x in sorted(found)[:20]:
    print("   ", x)
