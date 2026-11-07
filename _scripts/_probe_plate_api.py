# -*- coding: utf-8 -*-
"""实测 apply_color_texture_to_object 在本机 0.9.16 是否可用。"""
import carla

c = carla.Client("127.0.0.1", 2000); c.set_timeout(30.0)
w = c.get_world()

print("=== 1) API 存在性 ===")
print("  apply_color_texture_to_object:", hasattr(w, "apply_color_texture_to_object"))
print("  apply_texture_to_object:", hasattr(w, "apply_texture_to_object"))
print("  get_names_of_all_objects:", hasattr(w, "get_names_of_all_objects"))
print("  carla.TextureColor:", hasattr(carla, "TextureColor"))
print("  carla.MaterialParameter:", hasattr(carla, "MaterialParameter"))
if hasattr(carla, "MaterialParameter"):
    print("   枚举值:", [x for x in dir(carla.MaterialParameter) if not x.startswith("_")])

print("\n=== 2) 车辆相关对象名（找车牌材质）===")
names = w.get_names_of_all_objects()
print("  对象总数:", len(names))
for kw in ("Plate", "plate", "License", "license"):
    hit = [n for n in names if kw in n]
    print("  含 %-8r 的对象: %d 个" % (kw, len(hit)))
    for n in hit[:8]:
        print("      ", n)
