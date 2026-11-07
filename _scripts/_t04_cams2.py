# -*- coding: utf-8 -*-
"""在 road45（521m 长路）和 road39（高速环线）上拍候选机位。"""
import carla, math, time, os
import numpy as np, cv2
c = carla.Client('127.0.0.1', 2000); c.set_timeout(60.0)
w = c.get_world(); m = w.get_map(); bl = w.get_blueprint_library()

def road_pts(rid):
    out = []
    for wp in m.generate_waypoints(10.0):
        if wp.lane_type != carla.LaneType.Driving: continue
        if wp.road_id != rid: continue
        t = wp.transform
        out.append((t.location.x, t.location.y, t.location.z, t.rotation.yaw))
    return out

outdir = r'E:\output\_scripts\_t04cams2'
os.makedirs(outdir, exist_ok=True)
bp = bl.find('sensor.camera.rgb')
bp.set_attribute('image_size_x','1280'); bp.set_attribute('image_size_y','720'); bp.set_attribute('fov','90')

def shoot(tag, loc, pitch, yaw):
    tf = carla.Transform(carla.Location(*loc), carla.Rotation(pitch=pitch, yaw=yaw, roll=0))
    cam = w.try_spawn_actor(bp, tf)
    if cam is None: print(tag,'失败'); return
    got = []
    cam.listen(lambda img,g=got: g.append(np.frombuffer(img.raw_data,np.uint8).reshape(img.height,img.width,4)[:,:,:3].copy()))
    w.wait_for_tick(3.0); time.sleep(0.8)
    if got:
        p = os.path.join(outdir, tag + '.png'); cv2.imwrite(p, got[-1]); print('saved', tag)
    cam.stop(); cam.destroy(); w.wait_for_tick(1.0)

for rid, nm in ((45,'r45'), (39,'r39')):
    p = road_pts(rid)
    if not p: print(nm,'无点'); continue
    xs=[a[0] for a in p]; ys=[a[1] for a in p]; zs=[a[2] for a in p]
    cx, cy = sum(xs)/len(xs), sum(ys)/len(ys)
    zmax = max(zs)
    print('%s: n=%d 中心(%.0f,%.0f) 高度%.1f~%.1f' % (nm, len(p), cx, cy, min(zs), zmax))
    shoot(nm+'_1_high',  (cx, cy-90, zmax+55), -32, 0)
    shoot(nm+'_2_side',  (cx-90, cy-40, zmax+45), -28, 35)
    shoot(nm+'_3_closer',(cx, cy-70, zmax+30), -25, 0)
print('done')