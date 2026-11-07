# -*- coding: utf-8 -*-
"""Town04 实测：找直路段并测试最高速度。"""
import carla, math, time
c = carla.Client('127.0.0.1', 2000); c.set_timeout(60.0)
w = c.get_world(); print('地图:', w.get_map().name)
m = w.get_map(); bl = w.get_blueprint_library()

print('=== 采样车道点，找长直路段 ===')
pts = []
for wp in m.generate_waypoints(20.0):
    if wp.lane_type != carla.LaneType.Driving: continue
    pts.append((wp.transform.location.x, wp.transform.location.y, wp.transform.rotation.yaw, wp.lane_id))
print('车道点总数:', len(pts))

# 找一段连续同 yaw 的直路
best = None
for i in range(len(pts)-6):
    seg = pts[i:i+7]
    yaws = [p[2] for p in seg]
    if max(yaws)-min(yaws) < 3.0:
        d = math.dist((seg[0][0],seg[0][1]), (seg[-1][0],seg[-1][1]))
        if best is None or d > best[0]:
            best = (d, seg[0], seg[-1])
if best:
    print('最长直段: %.1f m, 起点(%.1f,%.1f) 终点(%.1f,%.1f) yaw=%.1f' % (best[0], best[1][0],best[1][1], best[2][0],best[2][1], best[1][2]))
else:
    print('未找到直段'); raise SystemExit(1)

print()
print('=== 在直段起点生成车，测最高速度 ===')
wp = m.get_waypoint(carla.Location(x=best[1][0], y=best[1][1], z=0.3), project_to_road=True)
tf = wp.transform; tf.location.z += 0.3
A = w.try_spawn_actor(bl.find('vehicle.tesla.model3'), tf)
if A is None: print('生成失败'); raise SystemExit(1)
print('车 id=%d' % A.id)
w.wait_for_tick(3.0)

tm = c.get_trafficmanager(8000)
A.set_autopilot(True, 8000)
tm.vehicle_percentage_speed_difference(A, -80.0)
print('%5s %10s' % ('t', 'km/h'))
mx = 0
for i in range(12):
    time.sleep(2.0)
    v = A.get_velocity(); s = 3.6*math.sqrt(v.x**2+v.y**2+v.z**2)
    mx = max(mx, s)
    print('%5ds %10.1f' % ((i+1)*2, s))
print('最高速度: %.1f km/h' % mx)
A.destroy(); w.wait_for_tick(2.0)