# -*- coding: utf-8 -*-
"""用当前机位拍摄跑动车辆，验证能否拍到超速画面。"""
import carla, math, time, os
import numpy as np, cv2
c = carla.Client('127.0.0.1', 2000); c.set_timeout(60.0)
w = c.get_world(); bl = w.get_blueprint_library(); m = w.get_map()
sp = w.get_spectator().get_transform()
print('机位:', (round(sp.location.x,1), round(sp.location.y,1), round(sp.location.z,1)), 'yaw', round(sp.rotation.yaw,1))

# 车从远处朝相机方向开过来
start = (280.0, -240.0)
wp = m.get_waypoint(carla.Location(x=start[0], y=start[1], z=0.3), project_to_road=True)
print('车起点 waypoint:', (round(wp.transform.location.x,1), round(wp.transform.location.y,1)), 'yaw', round(wp.transform.rotation.yaw,1))
tf = wp.transform; tf.location.z += 0.3
car = w.try_spawn_actor(bl.find('vehicle.tesla.model3'), tf)
print('车:', car.id if car else None)
if car is None: raise SystemExit(1)
w.wait_for_tick(3.0)
car.set_autopilot(True, 8000)
tm = c.get_trafficmanager(8000)
tm.vehicle_percentage_speed_difference(car, -60.0)
w.wait_for_tick(2.0)

outdir = r'E:\output\_scripts\_live'
bp = bl.find('sensor.camera.rgb')
bp.set_attribute('image_size_x','1280'); bp.set_attribute('image_size_y','720'); bp.set_attribute('fov','90')
cam = w.try_spawn_actor(bp, sp)
g = []
cam.listen(lambda img: g.append(np.frombuffer(img.raw_data,np.uint8).reshape(img.height,img.width,4)[:,:,:3].copy()))

print('%5s %10s %12s %s' % ('t', 'km/h', '离相机m', 'saved'))
saved = 0
for i in range(14):
    w.wait_for_tick(2.0); time.sleep(1.2)
    v = car.get_velocity(); s = 3.6*math.sqrt(v.x**2+v.y**2+v.z**2)
    d = car.get_location().distance(sp.location)
    tag = ''
    if i in (3, 6, 9, 12) and g:
        p = os.path.join(outdir, 'run_t%02d.png' % i)
        cv2.imwrite(p, g[-1]); saved += 1; tag = 'yes'
    print('%5ds %10.1f %12.1f %s' % ((i+1), s, d, tag))
cam.stop(); cam.destroy()
try: car.destroy()
except: pass
w.wait_for_tick(2.0)
print('saved', saved, 'frames')