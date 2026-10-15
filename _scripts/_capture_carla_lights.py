"""Capture REAL CARLA traffic-light crops at several distances, with the light
clamped to a known state, so the classifiers can be scored against CARLA ground
truth (the footage the demo will actually use).

Saves E:\\output\\_tl_carla\\<state>_<dist>m_w<W>h<H>.png plus a manifest.
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

# the westbound-approach light near junction 23 (controls road 6 / road 7)
POLE = np.array([-59.24, -51.50, 0.25])
# the lamp head we believe sits on that mast (raw box interpretation)
HEAD_RAW = np.array([-59.7, -60.8, 5.15])


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

    manifest = []
    for state in ("Red", "Green", "Yellow"):
        tl.freeze(True)
        tl.set_state(getattr(carla.TrafficLightState, state))
        print("light 17 forced to", tl.get_state())
        for dist in (12.0, 20.0, 30.0, 45.0):
            for (W, H) in ((1920, 1080),):
                # camera on the approach lane, looking at the mast
                cam_xy = np.array([POLE[0] + dist, POLE[1] - 3.0])
                yaw = math.degrees(math.atan2(HEAD_RAW[1] - cam_xy[1], HEAD_RAW[0] - cam_xy[0]))
                pitch = -4.0
                loc = carla.Location(x=float(cam_xy[0]), y=float(cam_xy[1]), z=6.0)
                rot = carla.Rotation(pitch=pitch, yaw=yaw, roll=0.0)
                bp = world.get_blueprint_library().find("sensor.camera.rgb")
                bp.set_attribute("image_size_x", str(W))
                bp.set_attribute("image_size_y", str(H))
                bp.set_attribute("fov", "60")
                ca = world.spawn_actor(bp, carla.Transform(loc, rot))
                got = []
                ca.listen(lambda im: got.append(im))
                for _ in range(6):
                    world.tick()
                    time.sleep(0.04)
                time.sleep(0.5)
                ca.stop()
                ca.destroy()
                arr = np.frombuffer(got[-1].raw_data, np.uint8).reshape(H, W, 4)[:, :, :3].copy()
                full = os.path.join(OUT, "%s_%02.0fm_full.png" % (state.lower(), dist))
                cv2.imwrite(full, arr)
                # crop the centre band where the head should be
                cx, cy = W // 2, int(H * 0.45)
                for (cw, ch) in ((64, 250), (34, 130), (20, 78), (12, 47)):
                    x0, y0 = max(0, cx - cw // 2), max(0, cy - ch // 2)
                    crop = arr[y0:y0 + ch, x0:x0 + cw]
                    if crop.shape[0] != ch or crop.shape[1] != cw:
                        continue
                    p = os.path.join(OUT, "%s_%02.0fm_%dx%d.png" % (state.lower(), dist, cw, ch))
                    cv2.imwrite(p, crop)
                manifest.append({"state": state, "dist": dist, "cam": [float(cam_xy[0]), float(cam_xy[1]), 6.0],
                                 "yaw": yaw, "full": full})
                print("   dist=%4.0f m cam=(%.1f,%.1f) yaw=%.1f -> %s" % (dist, cam_xy[0], cam_xy[1], yaw, os.path.basename(full)))
    tl.freeze(False)
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print("\nwrote", len(manifest), "captures ->", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
