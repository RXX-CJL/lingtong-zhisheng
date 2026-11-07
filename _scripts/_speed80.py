# -*- coding: utf-8 -*-
"""实测：如何让 autopilot 车稳定跑到 80 km/h。对比三种设置。"""
import carla, math, time, sys
c = carla.Client('127.0.0.1', 2000); c.set_timeout(30.0)
w = c.get_world(); bl = w.get_blueprint_library(); m = w.get_map()

# 找两个不同车道的点
pts = []
for wp in m.generate_waypoints(30.0):
    if wp.lane_type != carla.LaneType.Driving: continue
    tf = wp.transform; tf.location.z += 0.3
    a = w.try_spawn_actor(bl.find('vehicle.tesla.model3'), tf)
    if a is not None:
        pts.append((tf.location.x, tf.location.y, wp.lane_id, wp.lane_width))
        a.destroy()
    if len(pts) >= 6: break
print('可用点:', [(round(p[0],1), round(p[1],1), p[2]) for p in pts])

# 取同向不同车道两点
p0 = pts[0]
other = next((p for p in pts if p[2] != p0[2] and (p[2]*p0[2]) > 0), None)
print('选定: 主=%s 副=%s' % ((round(p0[0],1),round(p0[1],1),p0[2]), None if not other else (round(other[0],1),round(other[1],1),other[2])))

def spawn(bp_id, x, y):
    wp = m.get_waypoint(carla.Location(x=x,y=y,z=0.3), project_to_road=True)
    tf = wp.transform; tf.location.z += 0.3
    return w.try_spawn_actor(bl.find(bp_id), tf)

A = spawn('vehicle.tesla.model3', p0[0], p0[1])
print('A=%s' % (A.id if A else None))
if A is None: sys.exit(1)
w.wait_for_tick(3.0)

tm = c.get_trafficmanager(8000)
A.set_autopilot(True, 8000)

def kmh(a):
    v = a.get_velocity(); return 3.6*math.sqrt(v.x**2+v.y**2+v.z**2)

print('=== 方案1: set_desired_speed(80/3.6) ===')
tm.set_desired_speed(A, 80/3.6)
for i in range(4):
    time.sleep(2.0); print('   t=%ds %.1f km/h' % ((i+1)*2, kmh(A)))

print('=== 方案2: 速度差 -80%（比限速快80%） ===')
tm.vehicle_percentage_speed_difference(A, -80.0)
for i in range(4):
    time.sleep(2.0); print('   t=%ds %.1f km/h' % ((i+1)*2, kmh(A)))

print('=== 方案3: 两者叠加 ===')
tm.set_desired_speed(A, 80/3.6)
tm.vehicle_percentage_speed_difference(A, -10.0)
for i in range(4):
    time.sleep(2.0); print('   t=%ds %.1f km/h' % ((i+1)*2, kmh(A)))

try: A.destroy()
except: pass
w.wait_for_tick(2.0)
print('actors=', len(w.get_actors()))