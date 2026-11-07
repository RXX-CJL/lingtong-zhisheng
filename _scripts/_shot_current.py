# -*- coding: utf-8 -*-
"""读当前 spectator 机位，并在此机位拍一张确认画面。"""
import carla, time, os
import numpy as np, cv2
c = carla.Client('127.0.0.1', 2000); c.set_timeout(60.0)
w = c.get_world(); bl = w.get_blueprint_library()
print('地图:', w.get_map().name)
sp = w.get_spectator().get_transform()
print('当前 spectator:')
print('  location = (%.4f, %.4f, %.4f)' % (sp.location.x, sp.location.y, sp.location.z))
print('  rotation = pitch %.2f  yaw %.2f  roll %.2f' % (sp.rotation.pitch, sp.rotation.yaw, sp.rotation.roll))

outdir = r'E:\output\_scripts\_live'
os.makedirs(outdir, exist_ok=True)
bp = bl.find('sensor.camera.rgb')
bp.set_attribute('image_size_x','1280'); bp.set_attribute('image_size_y','720'); bp.set_attribute('fov','90')
cam = w.try_spawn_actor(bp, sp)
if cam is None:
    print('相机生成失败'); raise SystemExit(1)
g = []
cam.listen(lambda img: g.append(np.frombuffer(img.raw_data,np.uint8).reshape(img.height,img.width,4)[:,:,:3].copy()))
w.wait_for_tick(3.0); time.sleep(1.0)
if g:
    p = os.path.join(outdir, 'current_view.png')
    cv2.imwrite(p, g[-1])
    print('saved', p)
cam.stop(); cam.destroy()
print('actors=', len(w.get_actors()))