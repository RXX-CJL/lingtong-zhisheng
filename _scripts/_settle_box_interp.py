"""Settle the light-box coordinate question EMPIRICALLY: render candidate-B camera,
crop around both interpretations of each lamp, and report which crop contains a
bright saturated lamp.
"""
import math
import os
import sys
import time

import numpy as np
import carla
import cv2

OUTDIR = r"E:\output\_camera_check"
sys.path.insert(0, r"E:\output\_scripts")
from _spec_check import rot_matrix  # noqa: E402

W, H, FOV = 1280, 720, 90.0
CAND = {"cam": [-45.2, -28.5, 6.0], "pitch": -6.0, "yaw": -89.7}


class Cam:
    def __init__(self, loc, pitch, yaw, w=W, h=H, fov=FOV):
        self.loc = np.asarray(loc, float)
        self.R = rot_matrix(pitch, yaw, 0.0)
        self.w, self.h = w, h
        self.f = w / (2 * math.tan(math.radians(fov) / 2))

    def project(self, p):
        vc = self.R.T @ (np.asarray(p, float) - self.loc)
        if vc[0] <= 1e-6:
            return None
        return (self.w / 2 + self.f * (vc[1] / vc[0]),
                self.h / 2 - self.f * (vc[2] / vc[0]), float(vc[0]))


def classify(crop_hsv, crop_bgr):
    sat = crop_hsv[:, :, 1]
    val = crop_hsv[:, :, 2]
    m = (sat > 110) & (val > 130)
    n = int(m.sum())
    if n < 4:
        return n, "none", (0, 0, 0)
    b, g, r = [float(crop_bgr[:, :, i][m].mean()) for i in range(3)]
    hue = float(crop_hsv[:, :, 0][m].mean()) * 2.0
    if r > g + 25 and r > b + 25:
        c = "RED"
    elif g > r + 20 and g > b + 20:
        c = "GREEN"
    elif r > 150 and g > 130 and b < 120:
        c = "YELLOW"
    else:
        c = "other"
    return n, c, (round(r), round(g), round(b))


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(20.0)
    world = client.get_world()
    cam = Cam(CAND["cam"], CAND["pitch"], CAND["yaw"])

    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(W))
    bp.set_attribute("image_size_y", str(H))
    bp.set_attribute("fov", str(FOV))
    tf = carla.Transform(carla.Location(*CAND["cam"]),
                         carla.Rotation(pitch=CAND["pitch"], yaw=CAND["yaw"], roll=0.0))
    a = world.spawn_actor(bp, tf)
    got = []
    a.listen(lambda im: got.append(im))
    for _ in range(6):
        world.tick()
        time.sleep(0.05)
    time.sleep(0.6)
    a.stop()
    a.destroy()
    arr = np.frombuffer(got[-1].raw_data, np.uint8).reshape(H, W, 4)[:, :, :3].copy()
    hsv = cv2.cvtColor(arr, cv2.COLOR_BGR2HSV)

    tiles = []
    print("%-4s %-5s %-9s %-24s %-12s %-6s %-8s %s"
          % ("id", "state", "interp", "world", "pixel", "npx", "colour", "meanBGR"))
    for tl in world.get_actors().filter("traffic.traffic_light*"):
        if tl.id not in (10, 17, 9):
            continue
        try:
            st = str(tl.get_state())
        except Exception:
            st = "?"
        atf = tl.get_transform()
        for i, b in enumerate(tl.get_light_boxes()):
            if max(b.extent.x, b.extent.y) > 2.0:
                continue
            raw = np.array([b.location.x, b.location.y, b.location.z])
            interps = {
                "transformed": atf.location + atf.transform(b.location),
                "raw": carla.Location(x=float(raw[0]), y=float(raw[1]), z=float(raw[2])),
            }
            for name, wl in interps.items():
                r = cam.project([wl.x, wl.y, wl.z])
                if r is None:
                    continue
                u, v = int(round(r[0])), int(round(r[1]))
                if not (0 <= u < W and 0 <= v < H):
                    continue
                x0, y0 = max(0, u - 26), max(0, v - 26)
                x1, y1 = min(W, u + 26), min(H, v + 26)
                n, col, bgr = classify(hsv[y0:y1, x0:x1], arr[y0:y1, x0:x1])
                print("%-4d %-5s %-9s (%7.1f,%7.1f,%5.2f) (%4d,%4d) %-6d %-8s %s"
                      % (tl.id, st, name, wl.x, wl.y, wl.z, u, v, n, col, bgr))
                tile = arr[y0:y1, x0:x1].copy()
                ccol = {"RED": (0, 0, 255), "GREEN": (0, 255, 0), "YELLOW": (0, 255, 255)}.get(col, (255, 0, 255))
                cv2.drawMarker(tile, (u - x0, v - y0), ccol, cv2.MARKER_CROSS, 18, 2)
                cv2.putText(tile, "%d%s" % (tl.id, name[0]), (2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, ccol, 1)
                tiles.append(cv2.resize(tile, (104, 104)))

    if tiles:
        while len(tiles) % 8:
            tiles.append(np.zeros((104, 104, 3), np.uint8))
        rows = [np.hstack(tiles[i:i + 8]) for i in range(0, len(tiles), 8)]
        cv2.imwrite(os.path.join(OUTDIR, "interp_crops.png"), np.vstack(rows))
        print("\nwrote interp_crops.png  (%d tiles)" % len(tiles))
    return 0


if __name__ == "__main__":
    sys.exit(main())
