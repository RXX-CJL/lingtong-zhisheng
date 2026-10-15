"""Capture REAL CARLA signal-lens crops with VERIFIED ground-truth states.

Camera sits on the lens-facing side (probed: ~135 deg), so the lit lens is visible.
For each state: force it, tick, ASSERT the state took effect, then render and crop.
"""
import json
import math
import os
import sys
import time

import numpy as np
import carla
import cv2

OUT = r"E:\output\_tl_carla2"
os.makedirs(OUT, exist_ok=True)
HEAD = np.array([-59.7, -60.8, 5.15])
W, H, FOV = 1920, 1080, 60.0

# camera direction: on the SE side, looking back at the lens
CAM_DIR = 135.0


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
    ok_states = 0
    for want in ("Red", "Green", "Yellow"):
        tl.freeze(True)
        tl.set_state(getattr(carla.TrafficLightState, want))
        for _ in range(5):
            world.tick()
            time.sleep(0.05)
        got_state = str(tl.get_state())
        verified = (got_state == want)
        ok_states += int(verified)
        print("forced %-6s -> actual %-6s  %s" % (want, got_state, "OK" if verified else "STILL WRONG"))
        if not verified:
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
            cv2.imwrite(os.path.join(OUT, "%s_%02.0fm_full.png" % (want.lower(), dist)), arr)

            # locate the lit lens inside the render to crop it exactly
            hsv = cv2.cvtColor(arr, cv2.COLOR_BGR2HSV)
            if want == "Red":
                m = (((hsv[:, :, 0] < 10) | (hsv[:, :, 0] > 170)) & (hsv[:, :, 1] > 120) & (hsv[:, :, 2] > 120))
            elif want == "Green":
                m = ((hsv[:, :, 0] > 40) & (hsv[:, :, 0] < 100) & (hsv[:, :, 1] > 90) & (hsv[:, :, 2] > 120))
            else:
                m = ((hsv[:, :, 0] > 15) & (hsv[:, :, 0] < 38) & (hsv[:, :, 1] > 120) & (hsv[:, :, 2] > 150))
            mm = m.astype(np.uint8)
            n, lab, stats, cent = cv2.connectedComponentsWithStats(mm, 8)
            best = None
            for i in range(1, n):
                a = int(stats[i, cv2.CC_STAT_AREA])
                if best is None or a > best[0]:
                    best = (a, cent[i], stats[i])
            if not best or best[0] < 6:
                print("   dist=%4.0f m  -> lit lens NOT FOUND in render" % dist)
                manifest.append({"state": want, "dist": dist, "found": False})
                continue
            a, c, st = best
            cx, cy = int(c[0]), int(c[1])
            lw, lh = int(st[cv2.CC_STAT_WIDTH]), int(st[cv2.CC_STAT_HEIGHT])
            print("   dist=%4.0f m  lens area=%-4d at (%4d,%4d) %dx%d" % (dist, a, cx, cy, lw, lh))
            for (cw, ch) in ((64, 250), (34, 130), (20, 78), (12, 47)):
                x0 = max(0, min(W - cw, cx - cw // 2))
                y0 = max(0, min(H - ch, cy - ch // 2))
                crop = arr[y0:y0 + ch, x0:x0 + cw]
                if crop.shape[0] == ch and crop.shape[1] == cw:
                    cv2.imwrite(os.path.join(OUT, "%s_%02.0fm_%dx%d.png" % (want.lower(), dist, cw, ch)), crop)
            manifest.append({"state": want, "dist": dist, "found": True, "lens": [cx, cy],
                             "lens_px": [lw, lh], "area": a})
    tl.freeze(False)
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print("\nverified states: %d/3   captures with lens found: %d/%d"
          % (ok_states, sum(1 for m in manifest if m.get("found")), len(manifest)))
    print("wrote ->", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
