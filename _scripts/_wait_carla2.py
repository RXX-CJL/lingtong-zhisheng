# -*- coding: utf-8 -*-
import sys, time
import carla
for i in range(1, 41):
    try:
        c = carla.Client('127.0.0.1', 2000)
        c.set_timeout(8.0)
        w = c.get_world()
        print('READY 第%d次 地图=%s' % (i, w.get_map().name))
        sys.exit(0)
    except Exception as exc:
        print('第%d次未就绪: %s' % (i, str(exc)[:60]))
        time.sleep(8)
print('超时')
sys.exit(1)