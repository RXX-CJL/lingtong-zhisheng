# -*- coding: utf-8 -*-
"""迎车视角：车从远处朝相机开过来（用正确的车道与朝向）。"""
import carla, math, time, os
import numpy as np, cv2
c = carla.Client('127.0.0.1', 2000); c.set_timeout(60.0)
w = c.get_world(); bl = w.get_blueprint_library(); m = w.get_map()
sp = w.get_spectator().get_transform()
yaw = math.radians(sp.rotation.yaw)
print('相机: (%.1f, %.1f, %.1f) yaw=%.1f' % (sp.location.x, sp.location.y, sp.location.z, sp.rotation.yaw))

# 检查前方路径上有什么挡住
print('=== 前方 20~120m 的 actor（排除地面/道路）===')
for a in w.get_actors():
    try:
        d = a.get_location().distance(sp.location)
    except: continue
    if not (15 < d < 130): continue
    if 'vehicle' not in a.type_id and 'walker' not in a.type_id: continue
    print('  %.0fm %s id=%d' % (d, a.type_id, a.id))

print('=== 前方路径上最近的静止车辆（可能要避让的）===')
veh = [(round(a.get_location().distance(sp.location),1), a.id, a.type_id) for a in w.get_actors().filter('vehicle.*')]
veh.sort()
for d, i, t in veh[:5]:
    print('  %.0fm %s id=%d' % (d, t, i))