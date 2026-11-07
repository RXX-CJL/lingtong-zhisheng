# -*- coding: utf-8 -*-
"""实测 speeding vs obey 的真实速度（修正 spawn 与 TM 用法）。"""
import carla, math, time, sys
c = carla.Client('127.0.0.1', 2000); c.set_timeout(30.0)
w = c.get_world()
bl = w.get_blueprint_library()
m = w.get_map()

def spawn(bp_id, x, y):
    wp = m.get_waypoint(carla.Location(x=x, y=y, z=0.3), project_to_road=True)
    tf = wp.transform
    tf.location.z += 0.3
    a = w.try_spawn_actor(bl.find(bp_id), tf)
    return a

print('=== 找可用生成点 ===')
ok_pts = []
for wp in m.generate_waypoints(30.0):
    if wp.lane_type != carla.LaneType.Driving: continue
    tf = wp.transform; tf.location.z += 0.3
    a = w.try_spawn_actor(bl.find('vehicle.tesla.model3'), tf)
    if a is not None:
        ok_pts.append((tf.location.x, tf.location.y, tf.rotation.yaw))
        a.destroy()
        if len(ok_pts) >= 2: break
print('可用点:', ok_pts)
if len(ok_pts) < 2:
    print('FAIL 找不到两个可用点'); sys.exit(1)

A = spawn('vehicle.tesla.model3', ok_pts[0][0], ok_pts[0][1])
B = spawn('vehicle.audi.a2', ok_pts[1][0], ok_pts[1][1])
print('A=%s B=%s' % (A.id if A else None, B.id if B else None))
if A is None or B is None: sys.exit(1)
w.wait_for_tick(3.0)

tm = c.get_trafficmanager(8000)
tm.set_synchronous_mode(False)
A.set_autopilot(True, 8000)
B.set_autopilot(True, 8000)
tm.vehicle_percentage_speed_difference(A, -40.0)
tm.vehicle_percentage_speed_difference(B, 0.0)
w.wait_for_tick(3.0)

print('%5s %12s %12s %10s' % ('t', 'A超速km/h', 'B守法km/h', '差'))
for i in range(1, 11):
    time.sleep(2.0)
    try:
        va = A.get_velocity(); vb = B.get_velocity()
        sa = 3.6*math.sqrt(va.x**2+va.y**2+va.z**2)
        sb = 3.6*math.sqrt(vb.x**2+vb.y**2+vb.z**2)
        print('%5.0fs %12.1f %12.1f %10.1f' % (i*2, sa, sb, sa-sb))
    except Exception as e:
        print('读取失败', e); break
for a in (A, B):
    try: a.destroy()
    except: pass
w.wait_for_tick(2.0)
print('actors=', len(w.get_actors()))