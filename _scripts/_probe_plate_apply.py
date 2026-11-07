# -*- coding: utf-8 -*-
"""实测：能否用 apply_color_texture_to_object 给整辆车贴一张车牌图（验证可行性边界）。"""
import time
import carla
from PIL import Image, ImageDraw

c = carla.Client("127.0.0.1", 2000); c.set_timeout(60.0)
w = c.get_world()

# 1) 车
bp = w.get_blueprint_library().find("vehicle.tesla.model3")
wp = w.get_map().get_waypoint(carla.Location(x=109.93, y=-9.33, z=0.3), project_to_road=True)
tf = wp.transform; tf.location.z += 0.3
actor = w.try_spawn_actor(bp, tf)
if actor is None:
    print("生成失败"); raise SystemExit(1)
w.wait_for_tick(2.0); time.sleep(0.8)
print("车 id=%d" % actor.id)

# 2) 车在当前世界里的对象名（用于 apply）
names_before = set(w.get_names_of_all_objects())
print("对象名里含 Tesla 的:", [n for n in names_before if "Tesla" in n or "tesla" in n])

# 3) 造一张小图（先只验小尺寸是否被接受，避免 2048x2048 卡死）
W = H = 64
img = Image.new("RGB", (W, H), (0, 0, 255))
d = ImageDraw.Draw(img)
d.rectangle([2, 2, W-3, H-3], outline=(255, 255, 255), width=2)

print("\n=== 应用贴图（Diffuse）到整辆车 ===")
t0 = time.time()
tex = carla.TextureColor(W, H)
for x in range(W):
    for y in range(H):
        r, g, b = img.getpixel((x, y))
        tex.set(x, y, carla.Color(int(r), int(g), int(b), 255))
print("  TextureColor 填充耗时 %.2fs" % (time.time() - t0))

target = [n for n in w.get_names_of_all_objects() if "TeslaM3" in n]
print("  目标对象名候选:", target[:3])
ok = False
for name in target[:1]:
    try:
        w.apply_color_texture_to_object(name, carla.MaterialParameter.Diffuse, tex)
        w.wait_for_tick(2.0)
        ok = True
        print("  apply 调用成功: %s" % name)
    except Exception as exc:
        print("  apply 失败:", type(exc).__name__, str(exc)[:200])

actor.destroy()
w.wait_for_tick(2.0)
print("\n结果：调用%s。注意：这只证明 API 可调用，不等于车牌可用（缺 UV）" % ("成功" if ok else "失败"))
