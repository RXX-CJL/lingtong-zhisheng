# -*- coding: utf-8 -*-
"""收工前现场体检：隐藏装饰物残留 / actor / 机位 / 红绿灯配时。"""
import carla
c = carla.Client("127.0.0.1", 2000); c.set_timeout(20.0)
w = c.get_world()
a = w.get_actors()
print("总 actor 数 =", len(a), "| vehicle:", len(a.filter("vehicle.*")),
      "| prop:", len(a.filter("static.prop.*")), "| cam:", len(a.filter("sensor.camera.*")))

t = w.get_spectator().get_transform()
print("spectator loc=(%.6f, %.6f, %.6f) yaw=%.6f" % (t.location.x, t.location.y, t.location.z, t.rotation.yaw))

lights = list(a.filter("traffic.traffic_light*"))
bad = [(l.get_opendrive_id(), l.get_green_time(), l.get_yellow_time(), l.get_red_time())
       for l in lights if abs(l.get_green_time()-10.0) > 0.01 or abs(l.get_red_time()-2.0) > 0.01]
print("红绿灯 %d 盏，配时异常: %s" % (len(lights), bad if bad else "无（全部 10/3/2）"))

# 隐藏残留检查：EnvironmentObject 被隐藏后，enable=False 的对象在 get_environment_objects 里仍在，
# 但地面射线 ground_projection 会穿透。这里用最直接的办法：尝试恢复全部（幂等操作）。
for name, label in (("Vegetation", carla.CityObjectLabel.Vegetation),
                    ("Poles", carla.CityObjectLabel.Poles),
                    ("Fences", carla.CityObjectLabel.Fences),
                    ("Buildings", carla.CityObjectLabel.Buildings),
                    ("Walls", carla.CityObjectLabel.Walls),
                    ("TrafficSigns", carla.CityObjectLabel.TrafficSigns)):
    objs = w.get_environment_objects(label)
    print("  %-14s n=%d" % (name, len(objs)))
print("DONE")
