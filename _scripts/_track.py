# -*- coding: utf-8 -*-
"""一次性测量：按剧本 v2 的相机实际位置追踪三车在画面中的像素位置，验证速度差可见。"""
import sys, carla, time, math, queue, os
import numpy as np, cv2
sys.path.insert(0, r'E:\output\1\carla\CARLA_0.9.16\PythonAPI\carla')
from agents.navigation.global_route_planner import GlobalRoutePlanner

CAM_LOC = carla.Location(x=75.0, y=-95.0, z=40.0)
CAM_ROT = carla.Rotation(pitch=-24.0, yaw=105.0, roll=0.0)
W, H, FOV = 1280, 720, 80.0
OUT = r'E:\output\_scripts\_track'
os.makedirs(OUT, exist_ok=True)

def world_to_pixel(tf):
    fwd = tf.get_forward_vector()
    right = carla.Vector3D(math.cos(math.radians(tf.rotation.yaw + 90)),
                           math.sin(math.radians(tf.rotation.yaw + 90)), 0.0)
    up = carla.Vector3D(0, 0, 1)
    d = carla.Vector3D(tf.location.x, tf.location.y, tf.location.z)
    return fwd, right, up, d

c = carla.Client('127.0.0.1', 2000); c.set_timeout(30.0)
w = c.get_world(); m = w.get_map(); bp = w.get_blueprint_library()
cam_tf = carla.Transform(CAM_LOC, CAM_ROT)
fwd = cam_tf.get_forward_vector()
# 正交基
p = math.radians(CAM_ROT.pitch); y = math.radians(CAM_ROT.yaw)
f = np.array([math.cos(p)*math.cos(y), math.cos(p)*math.sin(y), math.sin(p)])
r = np.array([math.sin(y), -math.cos(y), 0.0])
u = np.cross(r, f)
fx = (W / 2) / math.tan(math.radians(FOV / 2))
actors = []
q = queue.Queue()
cam = None
try:
    tm = c.get_trafficmanager(8000)
    plan = [(42.9, 'vehicle.audi.a2', 0.0), (58.9, 'vehicle.mini.cooper_s', 0.0), (10.9, 'vehicle.tesla.model3', -40.0)]
    for x, name, pct in plan:
        a = w.try_spawn_actor(bp.find(name), carla.Transform(carla.Location(x=x, y=-57.4, z=0.6), carla.Rotation(yaw=0.0)))
        actors.append(a)
        if not a:
            print('spawn FAIL', name, flush=True); continue
        a.set_autopilot(True, 8000)
        tm.ignore_lights_percentage(a, 0.0)
        tm.vehicle_percentage_speed_difference(a, pct)
    cb = bp.find('sensor.camera.rgb')
    cb.set_attribute('image_size_x', str(W)); cb.set_attribute('image_size_y', str(H)); cb.set_attribute('fov', str(FOV))
    cam = w.spawn_actor(cb, cam_tf)
    cam.listen(lambda img: q.put(img))
    t0 = time.time(); shot = False
    while time.time() - t0 < 12:
        try:
            img = q.get(timeout=1.0)
        except queue.Empty:
            continue
        if not shot and time.time() - t0 > 8:
            arr = np.frombuffer(img.raw_data, dtype=np.uint8).reshape(img.height, img.width, 4)
            frame = arr[:, :, :3].copy()
            for a in actors:
                if not a: continue
                L = a.get_transform().location
                d = np.array([L.x - CAM_LOC.x, L.y - CAM_LOC.y, L.z + 0.8 - CAM_LOC.z])
                z = float(np.dot(d, f))
                if z <= 0.5: continue
                px = float(np.dot(d, r)) * fx / z + W / 2
                py = -float(np.dot(d, u)) * fx / z + H / 2
                v = a.get_velocity(); sp = math.sqrt(v.x**2+v.y**2+v.z**2)*3.6
                print('%-22s km/h=%5.0f  pixel=(%6.0f,%6.0f)  dist=%5.1fm' % (a.type_id.split('.')[-1], sp, px, py, z), flush=True)
                if 0 <= px < W and 0 <= py < H:
                    cv2.circle(frame, (int(px), int(py)), 26, (0, 255, 255), 3)
                    cv2.putText(frame, '%.0f' % sp, (int(px)+28, int(py)), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,255,255), 2)
            cv2.imwrite(os.path.join(OUT, 'track.png'), frame)
            shot = True
            print('saved track.png', flush=True)
finally:
    if cam: cam.stop(); cam.destroy()
    for a in actors:
        if a: a.destroy()
    print('CLEANED', flush=True)
