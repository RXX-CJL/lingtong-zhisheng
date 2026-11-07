# -*- coding: utf-8 -*-
"""清理测试残留：销毁本工具测试产生的车辆与相机，恢复到 23 actor。"""
import carla
c = carla.Client("127.0.0.1", 2000); c.set_timeout(20.0)
w = c.get_world()
print("清理前:", len(w.get_actors()))
for x in list(w.get_actors().filter("vehicle.*")):
    print("  销毁 vehicle id=%s %s" % (x.id, x.type_id)); x.destroy()
for x in list(w.get_actors().filter("sensor.camera.*")):
    print("  销毁 camera id=%s" % x.id); x.destroy()
for x in list(w.get_actors().filter("static.prop.*")):
    print("  销毁 prop id=%s" % x.id); x.destroy()
w.wait_for_tick(2.0)
a = w.get_actors()
print("清理后:", len(a), "| vehicle:", len(a.filter("vehicle.*")),
      "| camera:", len(a.filter("sensor.camera.*")))
lights = list(a.filter("traffic.traffic_light*"))
bad = [l.get_opendrive_id() for l in lights
       if abs(l.get_green_time()-10.0) > 0.01 or abs(l.get_red_time()-2.0) > 0.01]
print("红绿灯 %d 盏，配时异常: %s" % (len(lights), bad or "无"))
