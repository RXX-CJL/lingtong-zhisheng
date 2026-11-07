# -*- coding: utf-8 -*-
"""诊断：车为何停在远处 + 当前天气雾浓度。"""
import carla, math, time
c = carla.Client('127.0.0.1', 2000); c.set_timeout(60.0)
w = c.get_world()

wt = w.get_weather()
print('=== 当前天气 ===')
print('  cloudiness      =', wt.cloudiness)
print('  precipitation   =', wt.precipitation)
print('  fog_density     =', wt.fog_density)
print('  fog_distance    =', wt.fog_distance)
print('  fog_falloff     =', wt.fog_falloff)
print('  sun_altitude    =', wt.sun_altitude_angle)

print('=== 找相机前方路径上的路口/红绿灯 ===')
sp = w.get_spectator().get_transform()
m = w.get_map()
# 沿相机朝向采样前方 200m
import math as mm
yaw = mm.radians(sp.rotation.yaw)
for d in (30, 60, 100, 140, 173):
    x = sp.location.x + mm.cos(yaw)*d
    y = sp.location.y + mm.sin(yaw)*d
    wp = m.get_waypoint(carla.Location(x=x, y=y, z=sp.location.z), project_to_road=True)
    if wp:
        print('  %3dm 处: 路%.2f 车道%.2f z=%.1f 类型%s' % (d, wp.road_id, wp.lane_id, wp.transform.location.z, wp.lane_type))

print('=== 前方红绿灯 ===')
ls = list(w.get_actors().filter('traffic.traffic_light*'))
print('  红绿灯总数:', len(ls))
near = [(round(l.get_location().distance(sp.location),1), str(l.get_state())) for l in ls if l.get_location().distance(sp.location) < 220]
near.sort()
for d, st in near[:6]:
    print('   %.0fm  %s' % (d, st))