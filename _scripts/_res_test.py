"""对照实验：只改渲染分辨率/相机参数，看红灯颜色是否变化。

旧视频 = 2560x1440（用户说红灯是红的）
本次   = 1920x1080（红灯呈青蓝）
先测分辨率，再测旧记录里提到的相机高度/俯角。
"""
import math
import os
import sys
import time

import numpy as np
import carla
import cv2

OUT = r"E:\output\_res_test"
os.makedirs(OUT, exist_ok=True)
KNOWN_MAST = (-46.17, -73.56)
KNOWN_STOP = (-25.61, -64.76)
# 两盏灯在画面里的位置，按比例换算到不同分辨率
LAMP_1920 = [(1006, 140), (1139, 140)]


def find_light(world):
    best = None
    for a in world.get_actors().filter("traffic.traffic_light*"):
        L = a.get_transform().location
        dm = math.dist((L.x, L.y), KNOWN_MAST)
        ds = 1e9
        try:
            for wp in a.get_stop_waypoints():
                sl = wp.transform.location
                ds = min(ds, math.dist((sl.x, sl.y), KNOWN_STOP))
        except Exception:
            pass
        sc = ds * 2.0 + dm * 0.5
        if best is None or sc < best[0]:
            best = (sc, a)
    return best[1] if best else None


def render(world, cam_tf, w, h, fov, extra=None):
    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(w))
    bp.set_attribute("image_size_y", str(h))
    bp.set_attribute("fov", str(fov))
    for k, v in (extra or {}).items():
        try:
            bp.set_attribute(k, str(v))
        except Exception:
            pass
    cam = world.spawn_actor(bp, cam_tf)
    got = []
    cam.listen(lambda im: got.append(im))
    for _ in range(6):
        world.tick()
        time.sleep(0.04)
    time.sleep(0.5)
    cam.stop()
    cam.destroy()
    return np.frombuffer(got[-1].raw_data, np.uint8).reshape(h, w, 4)[:, :, :3].copy()


def probe(img, w, h, lamps_1920):
    """在按比例换算后的灯位置取最亮像素"""
    sx, sy = w / 1920.0, h / 1080.0
    out = []
    for (cx, cy) in lamps_1920:
        X, Y = int(cx * sx), int(cy * sy)
        hw, hh = 24, 34
        roi = img[max(0, Y - hh):Y + hh, max(0, X - hw):X + hw]
        if roi.size == 0:
            out.append(None)
            continue
        g = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        yy, xx = np.unravel_index(int(np.argmax(g)), g.shape)
        b, gg, r = [int(roi[yy, xx, k]) for k in range(3)]
        hsv = cv2.cvtColor(np.uint8([[[b, gg, r]]]), cv2.COLOR_BGR2HSV)[0, 0]
        out.append((b, gg, r, int(hsv[0]) * 2, int(hsv[1]), int(g[yy, xx])))
    return out


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(60.0)
    world = client.get_world()
    tl = find_light(world)
    tls = list(world.get_actors().filter("traffic.traffic_light*"))
    print("地图=%s 灯=%d 目标灯 id=%d" % (world.get_map().name, len(tls), tl.id))

    s = world.get_settings()
    s.synchronous_mode = True
    s.fixed_delta_seconds = 0.05
    world.apply_settings(s)

    CASES = [
        ("A_1920x1080_z5.732_p-23.445", 1920, 1080, 90.0,
         carla.Location(x=-15.720, y=-63.145, z=5.732),
         carla.Rotation(pitch=-23.445, yaw=179.536, roll=0.0), {}),
        ("B_2560x1440_z5.732_p-23.445", 2560, 1440, 90.0,
         carla.Location(x=-15.720, y=-63.145, z=5.732),
         carla.Rotation(pitch=-23.445, yaw=179.536, roll=0.0), {}),
        ("C_2560x1440_z7_p-22(旧记录)", 2560, 1440, 90.0,
         carla.Location(x=-82.6, y=50.5, z=7.0),
         carla.Rotation(pitch=-22.0, yaw=-55.3, roll=0.0), {}),
    ]

    print("\n%-34s %-32s %-32s" % ("case", "RED 态灯珠", "GREEN 态灯珠"))
    for label, w, h, fov, loc, rot, extra in CASES:
        res = {}
        for nm, st in (("red", carla.TrafficLightState.Red),
                       ("green", carla.TrafficLightState.Green)):
            for t in tls:
                t.freeze(True)
                t.set_state(st)
            for _ in range(6):
                world.tick()
                time.sleep(0.04)
            img = render(world, carla.Transform(loc, rot), w, h, fov, extra)
            cv2.imwrite(os.path.join(OUT, "%s_%s.png" % (label, nm)), img)
            res[nm] = probe(img, w, h, LAMP_1920)
        def fmt(lst):
            parts = []
            for x in lst:
                if x is None:
                    parts.append("[-]")
                else:
                    parts.append("BGR=(%3d,%3d,%3d)h%-3d" % x[:4])
            return " ".join(parts)
        print("%-34s %-32s %-32s" % (label, fmt(res["red"]), fmt(res["green"])))

    for t in tls:
        t.freeze(False)
    s.synchronous_mode = False
    s.fixed_delta_seconds = None
    world.apply_settings(s)
    print("\n产出:", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
