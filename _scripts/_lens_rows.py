"""逐颗镜片测量：CARLA 在 Red/Green/Yellow 三态下，点亮的到底是哪一颗镜片、什么颜色。

灯头内有 3 颗镜片（上=红位 / 中=黄位 / 下=绿位）。
在灯头投影位置的竖直方向上，按固定间距取 3 个采样窗，逐一测最亮像素。
"""
import math
import os
import sys
import time

import numpy as np
import carla
import cv2

OUT = r"E:\output\_lens_rows"
os.makedirs(OUT, exist_ok=True)
W, H, FOV = 1920, 1080, 90.0
CAM = carla.Location(x=-15.720, y=-63.145, z=5.732)
ROT = carla.Rotation(pitch=-23.445, yaw=179.536, roll=0.0)
KNOWN_MAST = (-46.17, -73.56)
KNOWN_STOP = (-25.61, -64.76)
# 两盏灯的水平位置（画面坐标）
LANE_X = [1006, 1139]
# 灯头内三颗镜片的竖直位置（画面坐标，上->下）
LENS_Y = [131, 157, 198]
LENS_NAME = ["UPPER(red slot)", "MIDDLE(yellow slot)", "LOWER(green slot)"]


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


def render(world):
    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(W))
    bp.set_attribute("image_size_y", str(H))
    bp.set_attribute("fov", str(FOV))
    cam = world.spawn_actor(bp, carla.Transform(CAM, ROT))
    got = []
    cam.listen(lambda im: got.append(im))
    for _ in range(6):
        world.tick()
        time.sleep(0.04)
    time.sleep(0.5)
    cam.stop()
    cam.destroy()
    return np.frombuffer(got[-1].raw_data, np.uint8).reshape(H, W, 4)[:, :, :3].copy()


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(60.0)
    world = client.get_world()
    if len(world.get_actors().filter("traffic.traffic_light*")) == 0:
        world = client.load_world("Town10HD_Opt")
        time.sleep(3)
    tls = list(world.get_actors().filter("traffic.traffic_light*"))
    print("地图=%s 灯=%d" % (world.get_map().name, len(tls)))

    s = world.get_settings()
    s.synchronous_mode = True
    s.fixed_delta_seconds = 0.05
    world.apply_settings(s)

    imgs = {}
    for nm, st in (("Red", carla.TrafficLightState.Red),
                   ("Green", carla.TrafficLightState.Green),
                   ("Yellow", carla.TrafficLightState.Yellow)):
        for t in tls:
            t.freeze(True)
            t.set_state(st)
        for _ in range(6):
            world.tick()
            time.sleep(0.04)
        imgs[nm] = render(world)
        cv2.imwrite(os.path.join(OUT, "state_%s.png" % nm.lower()), imgs[nm])

    def probe(img, cx, cy, hw=11, hh=9):
        roi = img[max(0, cy - hh):cy + hh, max(0, cx - hw):cx + hw]
        if roi.size == 0:
            return None
        b, g, r = [float(roi[:, :, k].mean()) for k in range(3)]
        hsv = cv2.cvtColor(np.uint8([[[int(b), int(g), int(r)]]]), cv2.COLOR_BGR2HSV)[0, 0]
        g2 = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        return (b, g, r, int(hsv[0]) * 2, int(hsv[1]), float(g2.mean()))

    print("\n每颗镜片的平均色（亮度=灰度均值，越大越亮 = 越可能被点亮）")
    for lane_i, cx in enumerate(LANE_X):
        print("\n--- 第 %d 盏灯 (画面 x=%d) ---" % (lane_i + 1, cx))
        print("   %-22s %-38s %-38s %s" % ("镜片", "Red 态", "Green 态", "Yellow 态"))
        for k, cy in enumerate(LENS_Y):
            cells = []
            for nm in ("Red", "Green", "Yellow"):
                p = probe(imgs[nm], cx, cy)
                if p is None:
                    cells.append("[-]")
                else:
                    cells.append("BGR=(%5.1f,%5.1f,%5.1f) h=%-3d V=%-5.1f"
                                 % (p[0], p[1], p[2], p[3], p[5]))
            print("   %-22s %-38s %-38s %s" % (LENS_NAME[k], cells[0], cells[1], cells[2]))

    for t in tls:
        t.freeze(False)
    s.synchronous_mode = False
    s.fixed_delta_seconds = None
    world.apply_settings(s)
    print("\n产出:", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
