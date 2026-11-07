# -*- coding: utf-8 -*-
"""Town04 高速段：拍 6 个候选机位供选择。"""
import carla, math, time, os
import numpy as np

c = carla.Client('127.0.0.1', 2000); c.set_timeout(60.0)
w = c.get_world(); m = w.get_map(); bl = w.get_blueprint_library()
print('地图:', w.get_map().name)

# 直段 起点(193.7,-367.9) -> 终点(341.0,-168.7)，长约 247m，方向 yaw 约 0.4（正东偏北）
P0 = (193.7, -367.9, 0.4)
P1 = (341.0, -168.7, 0.4)
mid = ((P0[0]+P1[0])/2, (P0[1]+P1[1])/2)
yaw_road = math.degrees(math.atan2(P1[1]-P0[1], P1[0]-P0[0]))
print('直段中点: (%.1f, %.1f)，道路方向 %.1f°' % (mid[0], mid[1], yaw_road))

outdir = r'E:\output\_scripts\_t04cams'
os.makedirs(outdir, exist_ok=True)

# 6 个候选机位
CAMS = [
    ('A_high_front', (mid[0]-60, mid[1]-30, 45), (-28, yaw_road+8)),
    ('B_high_side',  (mid[0]-20, mid[1]-70, 50), (-25, yaw_road+45)),
    ('C_mid_front',  (mid[0]-90, mid[1]-40, 18), (-12, yaw_road+5)),
    ('D_low_front',  (mid[0]-110, mid[1]-55, 6),  (-6,  yaw_road+10)),
    ('E_high_behind',(mid[0]+40, mid[1]+30, 42), (-26, yaw_road-170)),
    ('F_wide',       (mid[0]-140, mid[1]-110, 70), (-24, yaw_road+30)),
]

bp = bl.find('sensor.camera.rgb')
bp.set_attribute('image_size_x', '1280'); bp.set_attribute('image_size_y', '720'); bp.set_attribute('fov', '90')

frames = {}
for name, loc, (pitch, yaw) in CAMS:
    tf = carla.Transform(carla.Location(*loc), carla.Rotation(pitch=pitch, yaw=yaw, roll=0))
    cam = w.try_spawn_actor(bp, tf)
    if cam is None:
        print(name, '相机生成失败'); continue
    got = []
    cam.listen(lambda img, g=got: g.append(np.frombuffer(img.raw_data, np.uint8).reshape(img.height, img.width, 4)[:, :, :3].copy()))
    w.wait_for_tick(3.0); time.sleep(1.0)
    if got:
        import cv2
        p = os.path.join(outdir, name + '.png')
        cv2.imwrite(p, got[-1])
        print('saved', p)
    cam.stop(); cam.destroy()
    w.wait_for_tick(1.0)
print('done')