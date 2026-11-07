# -*- coding: utf-8 -*-
"""Town04：让车在长直路上跑起来，沿路拍机位（跟随车辆位置）。"""
import carla, math, time, os
import numpy as np, cv2
c = carla.Client('127.0.0.1', 2000); c.set_timeout(60.0)
w = c.get_world(); m = w.get_map(); bl = w.get_blueprint_library()

# 用之前验证过能跑 105km/h 的那个直段（193.7,-367.9 -> 341.0,-168.7）
A0 = (193.7, -367.9); A1 = (341.0, -168.7)
mid = ((A0[0]+A1[0])/2, (A0[1]+A1[1])/2)
yaw = math.degrees(math.atan2(A1[1]-A0[1], A1[0]-A0[0]))
print('直段 中点(%.0f,%.0f) 方向 %.1f°' % (mid[0], mid[1], yaw))

# 生成一辆车跑起来，确认这条路的真实外观
wp = m.get_waypoint(carla.Location(x=A0[0], y=A0[1], z=0.3), project_to_road=True)
tf = wp.transform; tf.location.z += 0.3
car = w.try_spawn_actor(bl.find('vehicle.tesla.model3'), tf)
print('车:', car.id if car else None)
if car:
    w.wait_for_tick(3.0)
    car.set_autopilot(True, 8000)
    tm = c.get_trafficmanager(8000); tm.vehicle_percentage_speed_difference(car, -60.0)
    w.wait_for_tick(3.0)

outdir = r'E:\output\_scripts\_t04cams3'
os.makedirs(outdir, exist_ok=True)
bp = bl.find('sensor.camera.rgb')
bp.set_attribute('image_size_x','1280'); bp.set_attribute('image_size_y','720'); bp.set_attribute('fov','90')

def shoot(tag, loc, pitch, yaw_):
    t = carla.Transform(carla.Location(*loc), carla.Rotation(pitch=pitch, yaw=yaw_, roll=0))
    cam = w.try_spawn_actor(bp, t)
    if cam is None: print(tag,'fail'); return
    g = []
    cam.listen(lambda img, G=g: G.append(np.frombuffer(img.raw_data,np.uint8).reshape(img.height,img.width,4)[:,:,:3].copy()))
    w.wait_for_tick(3.0); time.sleep(0.6)
    if g: cv2.imwrite(os.path.join(outdir, tag+'.png'), g[-1]); print('saved', tag)
    cam.stop(); cam.destroy(); w.wait_for_tick(1.0)

# 沿路取三个点做机位基准，相机放在道路侧后方高处
for i, frac in enumerate((0.25, 0.5, 0.75)):
    px = A0[0] + (A1[0]-A0[0])*frac
    py = A0[1] + (A1[1]-A0[1])*frac
    for j, (dz, back) in enumerate(((35, 55), (20, 35))):
        # 相机在道路垂直方向偏移（yaw+90）
        ry = math.radians(yaw + 90)
        cx = px + math.cos(ry)*back
        cy = py + math.sin(ry)*back
        shoot('P%d_%d' % (i+1, j+1), (cx, cy, dz), -22, yaw - 155)

if car:
    try: car.destroy()
    except: pass
w.wait_for_tick(2.0)
print('done')