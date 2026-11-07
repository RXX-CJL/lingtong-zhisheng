# -*- coding: utf-8 -*-
"""实测：重新跑一次 speeding vs obey，直接读 CARLA 里两车的真实速度差。"""
import carla, math, time, sys
c = carla.Client('127.0.0.1', 2000); c.set_timeout(30.0)
w = c.get_world()
bp = w.get_blueprint_library()
m = w.get_map()

def spawn(bp_id, loc):
    wp = m.get_waypoint(carla.Location(*loc), project_to_road=True)
    tf = wp.transform; tf.location.z += 0.3
    a = w.try_spawn_actor(bp.get_blueprint_library().find(bp_id) if hasattr(bp,'get_blueprint_library') else bp.find(bp_id), tf)
    return a

A = spawn('vehicle.tesla.model3', (109.93, -9.33, 0.3))
time.sleep(0.3)
B = spawn('vehicle.audi.a2', (102.0, -9.38, 0.3))
if A is None or B is None:
    print('spawn 失败', A, B); sys.exit(1)
print('spawned A=%d B=%d' % (A.id, B.id))
w.wait_for_tick(2.0)

tm = c.get_trafficmanager(8000)
A.set_autopilot(True, 8000)
B.set_autopilot(True, 8000)
tm.vehicle_percentage_speed_difference(A, -40.0)
tm.vehicle_percentage_speed_difference(B, 0.0)
w.wait_for_tick(2.0)

print('%5s %10s %10s %10s' % ('t', 'A(超速)km/h', 'B(守法)km/h', '差值'))
for i in range(1, 13):
    time.sleep(2.0)
    va = A.get_velocity(); vb = B.get_velocity()
    sa = 3.6*math.sqrt(va.x**2+va.y**2+va.z**2)
    sb = 3.6*math.sqrt(vb.x**2+vb.y**2+vb.z**2)
    print('%5.0fs %10.1f %10.1f %10.1f' % (i*2, sa, sb, sa-sb))
A.destroy(); B.destroy()
w.wait_for_tick(2.0)
print('done, actors=', len(w.get_actors()))