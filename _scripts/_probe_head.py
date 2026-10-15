"""Find the CARLA signal head's lit lens by probing camera positions around it.

The lamp's box geometry says the face normal is the thinnest axis (+-X local).
Rather than trust that, probe 8 directions x 2 distances, render each, and report
which renders contain a RED lit region -- and where.
"""
import json
import math
import os
import sys
import time

import numpy as np
import carla
import cv2

OUT = r"E:\output\_tl_carla"
os.makedirs(OUT, exist_ok=True)
HEAD = np.array([-59.7, -60.8, 5.15])          # believed lamp position
W, H, FOV = 1280, 720, 60.0


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(25.0)
    world = client.get_world()

    tl = None
    for a in world.get_actors().filter("traffic.traffic_light*"):
        if a.id == 17:
            tl = a
    if tl is None:
        print("light 17 not found")
        return 1
    tl.freeze(True)
    tl.set_state(carla.TrafficLightState.Red)
    # let the forced state actually take effect before rendering
    for _ in range(4):
        world.tick()
        time.sleep(0.05)
    print("light 17 state after forcing + ticks:", tl.get_state())

    results = []
    for dist in (14.0, 24.0):
        for ang in range(0, 360, 45):
            r = math.radians(ang)
            cam_xy = HEAD[:2] + np.array([math.cos(r), math.sin(r)]) * dist
            yaw = math.degrees(math.atan2(HEAD[1] - cam_xy[1], HEAD[0] - cam_xy[0]))
            bp = world.get_blueprint_library().find("sensor.camera.rgb")
            bp.set_attribute("image_size_x", str(W))
            bp.set_attribute("image_size_y", str(H))
            bp.set_attribute("fov", str(FOV))
            ca = world.spawn_actor(bp, carla.Transform(
                carla.Location(x=float(cam_xy[0]), y=float(cam_xy[1]), z=5.6),
                carla.Rotation(pitch=-3.0, yaw=yaw, roll=0.0)))
            got = []
            ca.listen(lambda im: got.append(im))
            for _ in range(4):
                world.tick()
                time.sleep(0.04)
            time.sleep(0.4)
            ca.stop()
            ca.destroy()
            arr = np.frombuffer(got[-1].raw_data, np.uint8).reshape(H, W, 4)[:, :, :3].copy()
            hsv = cv2.cvtColor(arr, cv2.COLOR_BGR2HSV)
            red = (((hsv[:, :, 0] < 10) | (hsv[:, :, 0] > 170)) &
                   (hsv[:, :, 1] > 120) & (hsv[:, :, 2] > 120)).astype(np.uint8)
            n, lab, stats, cent = cv2.connectedComponentsWithStats(red, 8)
            best = None
            for i in range(1, n):
                a_ = int(stats[i, cv2.CC_STAT_AREA])
                if best is None or a_ > best[0]:
                    best = (a_, cent[i], stats[i])
            rec = {"dist": dist, "angle": ang, "cam": [round(float(cam_xy[0]), 2), round(float(cam_xy[1]), 2)],
                   "yaw": round(yaw, 1)}
            if best and best[0] >= 6:
                a_, c, st = best
                rec.update({"red_area": a_, "cx": float(c[0]), "cy": float(c[1]),
                            "w": int(st[cv2.CC_STAT_WIDTH]), "h": int(st[cv2.CC_STAT_HEIGHT])})
                # crop generously around the lens and save
                x0, y0 = int(max(0, c[0] - 60)), int(max(0, c[1] - 100))
                crop = arr[y0:y0 + 200, x0:x0 + 120]
                if crop.size:
                    cv2.imwrite(os.path.join(OUT, "probe_d%02.0f_a%03d_red.png" % (dist, ang)), crop)
                print("   d=%4.0f ang=%3d -> RED area=%-5d at (%5.1f,%5.1f) %dx%d"
                      % (dist, ang, a_, c[0], c[1], st[cv2.CC_STAT_WIDTH], st[cv2.CC_STAT_HEIGHT]))
            else:
                rec["red_area"] = 0
                print("   d=%4.0f ang=%3d -> no red region" % (dist, ang))
            results.append(rec)
            cv2.imwrite(os.path.join(OUT, "probe_d%02.0f_a%03d.png" % (dist, ang)), arr)

    tl.freeze(False)
    with open(os.path.join(OUT, "probe.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\nwrote probes ->", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
