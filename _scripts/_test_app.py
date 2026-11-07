# -*- coding: utf-8 -*-
"""沿相机所在车道取点，让车朝相机开过来。"""
import carla, math, time, os
import numpy as np, cv2
c = carla.Client('127.0.0.1', 2000); c.set_timeout(60.0)
w = c.get_world(); bl = w.get_blueprint_library(); m = w.get_map()
sp = w.get_spectator().get_transform()

# 相机所在 waypoint，然后沿车道向后走 N 个 waypoint
wp0 = m.get_waypoint(sp.location, project_to_road=True)
print('相机所在: road=%s lane=%s' % (wp0.road_id, wp0.lane_id))

def walk(wp, n, forward=True):
    cur = wp
    for _ in range(n):
        nxt = cur.next(8.0) if forward else cur.previous(8.0)
        if not nxt: return None
        cur = nxt[0]
    return cur

# 沿车道往前 10 段（约 80m）
target = walk(wp0, 10, forward=True)
if target is None:
    print('向前走到头，改向后'); target = walk(wp0, 10, forward=False)
if target is None:
    print('失败'); raise SystemExit(1)
tp = target.transform.location
print('目标点: (%.1f, %.1f, %.1f) 距离 %.1fm 该处车道=%s' % (tp.x, tp.y, tp.z, tp.distance(sp.location), target.lane_id))

tf = target.transform; tf.location.z += 0.3
car = w.try_spawn_actor(bl.find('vehicle.tesla.model3'), tf)
print('车:', car.id if car else None)
if car is None: raise SystemExit(1)
w.wait_for_tick(3.0)

# 用 TM 让它沿车道开（不关 autopilot，避免跑偏）
car.set_autopilot(True, 8000)
tm = c.get_trafficmanager(8000)
tm.vehicle_percentage_speed_difference(car, -60.0)
tm.ignore_walkers_percentage(car, 100.0)
w.wait_for_tick(2.0)
print('已开启 autopilot + 超速60%')

outdir = r'E:\output\_scripts\_live'
bp = bl.find('sensor.camera.rgb')
bp.set_attribute('image_size_x','1280'); bp.set_attribute('image_size_y','720'); bp.set_attribute('fov','90')
cam = w.try_spawn_actor(bp, sp)
g = []
cam.listen(lambda img: g.append(np.frombuffer(img.raw_data,np.uint8).reshape(img.height,img.width,4)[:,:,:3].copy()))

print('%5s %10s %12s %s' % ('t','km/h','离相机m','shot'))
for i in range(18):
    w.wait_for_tick(2.0); time.sleep(0.8)
    v = car.get_velocity(); s = 3.6*math.sqrt(v.x**2+v.y**2+v.z**2)
    d = car.get_location().distance(sp.location)
    tag=''
    if i in (1,3,5,7) and g:
        cv2.imwrite(os.path.join(outdir,'app_t%02d.png'%i), g[-1]); tag='yes'
    print('%5ds %10.1f %12.1f %s' % (i+1, s, d, tag))
cam.stop(); cam.destroy()
try: car.destroy()
except: pass
w.wait_for_tick(2.0)