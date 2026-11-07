# -*- coding: utf-8 -*-
"""探查 Town04 高速环线：找能跑 80km/h 的直路段。"""
import carla, math
c = carla.Client('127.0.0.1', 2000); c.set_timeout(60.0)
print('可用地图:', [m for m in c.get_available_maps()][:6])
print()
print('=== 切到 Town04 ===')
w = c.load_world('Town04')
print('当前地图:', w.get_map().name)
m = w.get_map()