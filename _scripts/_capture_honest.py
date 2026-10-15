"""Capture HONEST red/yellow/green lens crops: locate the signal head by finding
the lamp BOX (cyan housing) rather than by colour, then centre the crop on the
right lens for the state (red = top lens, yellow = middle, green = bottom).

The previous attempt picked a red umbrella because it located the "lens" by
searching for red pixels.
"""
import json
import math
import os
import sys
import time

import numpy as np
import carla
import cv2

OUT = r"E:\output\_tl_carla3"
os.makedirs(OUT, exist_ok=True)
W, H, FOV = 1920, 1080, 60.0
HEAD = np.array([-59.7, -60.8, 5.15])
CAM_DIR = 135.0


def find_housing(arr):
    """Find the traffic-light housing: it is a strongly BLUE/CYAN vertical blob."""
    hsv = cv2.cvtColor(arr, cv2.COLOR_BGR2HSV)
    m = ((hsv[:, :, 0] > 90) & (hsv[:, :, 0] < 125) & (hsv[:, :, 1] > 110) & (hsv[:, :, 2] > 80))
    mm = cv2.morphologyEx(m.astype(np.uint8) * 255, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, lab, stats, cent = cv2.connectedComponentsWithStats(mm, 8)
    best = None
    for i in range(1, n):
        a = int(stats[i, cv2.CC_STAT_AREA])
        h_ = int(stats[i, cv2.CC_STAT_HEIGHT])
        w_ = int(stats[i, cv2.CC_STAT_WIDTH])
        if h_ < 10 or w_ < 4:
            continue
        if a > 200000:
            continue
        if best is None or a > best[0]:
            best = (a, cent[i], stats[i])
    return best


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
    for want in ("Red", "Green", "Yellow"):
        tl.freeze(True)
        tl.set_state(getattr(carla.TrafficLightState, want))
        for _ in range(5):
            world.tick()
            time.sleep(0.05)
        actual = str(tl.get_state())
        print("\nforced %-6s -> actual %-6s %s" % (want, actual, "OK" if actual == want else "MISMATCH"))
        if actual != want:
            continue
        for dist in (12.0, 20.0, 30.0, 45.0):
            r = math.radians(CAM_DIR)
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
            time.sleep(0.45)
            ca.stop()
            ca.destroy()
            arr = np.frombuffer(got[-1].raw_data, np.uint8).reshape(H, W, 4)[:, :, :3].copy()
            hs = find_housing(arr)
            if hs is None:
                print("   dist=%4.0f m  housing NOT FOUND" % dist)
                manifest.append({"state": want, "dist": dist, "found": False})
                continue
            a_, c, st = hs
            hx, hy = float(c[0]), float(c[1])
            hw, hh = int(st[cv2.CC_STAT_WIDTH]), int(st[cv2.CC_STAT_HEIGHT])
            # red = top lens, yellow = middle, green = bottom
            off = {"Red": -0.30, "Yellow": 0.0, "Green": 0.30}[want]
            ly = hy + off * hh
            print("   dist=%4.0f m  housing %dx%d at (%.0f,%.0f) -> %s lens y=%.0f"
                  % (dist, hw, hh, hx, hy, want, ly))
            for (cw, ch) in ((64, 250), (34, 130), (20, 78), (12, 47)):
                x0 = max(0, min(W - cw, int(hx - cw // 2)))
                y0 = max(0, min(H - ch, int(ly - ch // 2)))
                crop = arr[y0:y0 + ch, x0:x0 + cw]
                if crop.shape[0] == ch and crop.shape[1] == cw:
                    cv2.imwrite(os.path.join(OUT, "%s_%02.0fm_%dx%d.png" % (want.lower(), dist, cw, ch)), crop)
            cv2.imwrite(os.path.join(OUT, "%s_%02.0fm_full.png" % (want.lower(), dist)), arr)
            manifest.append({"state": want, "dist": dist, "found": True,
                             "housing": [hx, hy], "housing_px": [hw, hh], "lens_y": ly})
    tl.freeze(False)
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    ok = sum(1 for m in manifest if m.get("found"))
    print("\ncaptures with housing located: %d/%d -> %s" % (ok, len(manifest), OUT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
