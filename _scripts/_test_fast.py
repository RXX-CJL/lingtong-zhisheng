# -*- coding: utf-8 -*-
"""验证：薄雾 + 近处来车，能否拍到清晰的超速画面。"""
import carla, math, time, os
import numpy as np, cv2
c = carla.Client('127.0.0.1', 2000); c.set_timeout(60.0)
w = c.get_world(); bl = w.get_blueprint_library(); m = w.get_map()
sp = w.get_spectator().get_transform()

# 1) 调薄雾
wt = w.get_weather()
wt.fog_density = 2.0
wt.fog_distance = 300.0
wt.fog_falloff = 1.0
wt.cloudiness = 15.0
w.set_weather(wt)
w.wait_for_tick(2.0)
print('雾已调薄: density=2.0 distance=300')

# 2) 找相机正前方 40~80m 的可用点（避开红灯）
yaw = math.radians(sp.rotation.yaw)
def at(d):
    x = sp.location.x + math.cos(yaw)*d
    y = sp.location.y + math.sin(yaw)*d
    return m.get_waypoint(carla.Location(x=x, y=y, z=sp.location.z), project_to_road=True)

pt = at(60.0)
print('60m 处: 路%s 车道%s' % (pt.road_id, pt.lane_id))
tf = pt.transform; tf.location.z += 0.3
car = w.try_spawn_actor(bl.find('vehicle.tesla.model3'), tf)
print('车:', car.id if car else None)
if car is None: raise SystemExit(1)
w.wait_for_tick(3.0)

# 3) 关 autopilot，用 apply_control 直驱（避免红灯停）
car.set_autopilot(False)
print('已关 autopilot，改用手动油门')

outdir = r'E:\output\_scripts\_live'
bp = bl.find('sensor.camera.rgb')
bp.set_attribute('image_size_x','1280'); bp.set_attribute('image_size_y','720'); bp.set_attribute('fov','90')
cam = w.try_spawn_actor(bp, sp)
g = []
cam.listen(lambda img: g.append(np.frombuffer(img.raw_data,np.uint8).reshape(img.height,img.width,4)[:,:,:3].copy()))

print('%5s %10s %12s %s' % ('t', 'km/h', '离相机m', 'shot'))
for i in range(16):
    car.apply_control(carla.VehicleControl(throttle=0.85, steer=0.0, brake=0.0))
    w.wait_for_tick(2.0); time.sleep(0.9)
    v = car.get_velocity(); s = 3.6*math.sqrt(v.x**2+v.y**2+v.z**2)
    d = car.get_location().distance(sp.location)
    tag = ''
    if i in (2, 5, 8, 11) and g:
        cv2.imwrite(os.path.join(outdir, 'fast_t%02d.png' % i), g[-1]); tag='yes'
    print('%5ds %10.1f %12.1f %s' % (i+1, s, d, tag))
    if d > 200: break
cam.stop(); cam.destroy()
try: car.destroy()
except: pass
w.wait_for_tick(2.0)