# -*- coding: utf-8 -*-
"""Town04：把速度稳定在 80 附近 —— 调速度差让稳态落在 80。"""
import carla, math, time
c = carla.Client('127.0.0.1', 2000); c.set_timeout(60.0)
w = c.get_world(); m = w.get_map(); bl = w.get_blueprint_library()
tm = c.get_trafficmanager(8000)

start = (193.7, -367.9)

def run(diff, secs=16):
    wp = m.get_waypoint(carla.Location(x=start[0], y=start[1], z=0.3), project_to_road=True)
    tf = wp.transform; tf.location.z += 0.3
    A = w.try_spawn_actor(bl.find('vehicle.tesla.model3'), tf)
    if A is None: return None
    w.wait_for_tick(3.0)
    A.set_autopilot(True, 8000)
    tm.vehicle_percentage_speed_difference(A, diff)
    vals = []
    for i in range(secs):
        time.sleep(1.0)
        v = A.get_velocity(); vals.append(3.6*math.sqrt(v.x**2+v.y**2+v.z**2))
    A.destroy(); w.wait_for_tick(2.0)
    return vals

for diff in (-30.0, -40.0, -50.0):
    vals = run(diff)
    if not vals: print('diff=%s 失败' % diff); continue
    # 取中间 10 秒（跳过起步加速）
    mid = vals[4:14]
    print('diff=%+5.0f%%  峰值%.1f  中段均值%.1f  中段波动[%.1f..%.1f]' % (
        diff, max(vals), sum(mid)/len(mid), min(mid), max(mid)))