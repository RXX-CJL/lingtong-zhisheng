"""Verify candidate-B camera: is light 10's own signal head actually on screen?

Renders candidate B once, crops each of light 10's lamp boxes (and the mast-arm
actor), and reports the local colour/saturation so "is the signal there" is
answered from pixels rather than from geometry alone.
"""
import json
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
CAND = {"name": "B", "cam": [-45.2, -28.5, 6.0], "pitch": -6.0, "yaw": -89.7}


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


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(20.0)
    world = client.get_world()

    print("current light states:")
    states = {}
    for a in world.get_actors().filter("traffic.traffic_light*"):
        try:
            states[a.id] = str(a.get_state())
        except Exception:
            states[a.id] = "?"
    for k in sorted(states):
        print("   id=%-3d %s" % (k, states[k]))

    cam = Cam(CAND["cam"], CAND["pitch"], CAND["yaw"])
    tf = carla.Transform(carla.Location(*CAND["cam"]),
                         carla.Rotation(pitch=CAND["pitch"], yaw=CAND["yaw"], roll=0.0))
    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(W))
    bp.set_attribute("image_size_y", str(H))
    bp.set_attribute("fov", str(FOV))
    actor = world.spawn_actor(bp, tf)
    got = []
    actor.listen(lambda img: got.append(img))
    for _ in range(6):
        world.tick()
        time.sleep(0.05)
    time.sleep(0.6)
    actor.stop()
    actor.destroy()
    arr = np.frombuffer(got[-1].raw_data, np.uint8).reshape(H, W, 4)[:, :, :3].copy()
    cv2.imwrite(os.path.join(OUTDIR, "verify_B_frame.png"), arr)
    hsv = cv2.cvtColor(arr, cv2.COLOR_BGR2HSV)

    # light 10 lamp boxes
    tl10 = None
    for a in world.get_actors().filter("traffic.traffic_light*"):
        if a.id == 10:
            tl10 = a
    print("\nverify: light 10 boxes (world coords), projected into candidate-B camera")
    tiles = []
    for i, b in enumerate(tl10.get_light_boxes()):
        wl = np.array([b.location.x, b.location.y, b.location.z])
        ext = np.array([b.extent.x, b.extent.y, b.extent.z])
        r = cam.project(wl)
        if not r:
            print("   #%d off-axis" % i)
            continue
        u, v = int(round(r[0])), int(round(r[1]))
        inside = 0 <= u < W and 0 <= v < H
        ppm = cam.f / r[2]
        wp_, hp_ = 2 * ext[0] * ppm, 2 * ext[2] * ppm
        print("   #%d world=(%.2f,%.2f,%.2f) ext=(%.2f,%.2f,%.2f) px=(%d,%d) %s size=%.1fx%.1f px depth=%.1fm"
              % (i, wl[0], wl[1], wl[2], ext[0], ext[1], ext[2], u, v,
                 "IN" if inside else "out", wp_, hp_, r[2]))
        x0, y0 = max(0, u - 60), max(0, v - 60)
        x1, y1 = min(W, u + 60), min(H, v + 60)
        tile = arr[y0:y1, x0:x1].copy()
        sub = hsv[y0:y1, x0:x1]
        sat = float(sub[:, :, 1].mean())
        val = float(sub[:, :, 2].mean())
        strong = int(((sub[:, :, 1] > 120) & (sub[:, :, 2] > 140)).sum())
        bgr = arr[max(0, v - 2):v + 3, max(0, u - 2):u + 3].reshape(-1, 3).mean(axis=0)
        print("        local HSV sat=%.0f val=%.0f  bright-saturated px=%d  centre BGR=(%.0f,%.0f,%.0f)"
              % (sat, val, strong, bgr[0], bgr[1], bgr[2]))
        cv2.drawMarker(tile, (u - x0, v - y0), (255, 0, 255), cv2.MARKER_CROSS, 20, 2)
        cv2.putText(tile, "#%d" % i, (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2, cv2.LINE_AA)
        tiles.append(cv2.resize(tile, (120, 120)))

    if tiles:
        while len(tiles) % 4:
            tiles.append(np.zeros((120, 120, 3), np.uint8))
        rows = [np.hstack(tiles[i:i + 4]) for i in range(0, len(tiles), 4)]
        cv2.imwrite(os.path.join(OUTDIR, "verify_B_crops.png"), np.vstack(rows))
        print("   wrote verify_B_crops.png")

    # where are the bright saturated signal-like blobs in the upper half?
    mask = ((hsv[:, :, 1] > 140) & (hsv[:, :, 2] > 150)).astype(np.uint8)
    mask[H // 2:, :] = 0
    n, lab, stats, cent = cv2.connectedComponentsWithStats(mask, 8)
    blobs = []
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] >= 6:
            blobs.append((stats[i, cv2.CC_STAT_AREA], cent[i][0], cent[i][1], stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]))
    blobs.sort(reverse=True)
    print("\nbright saturated blobs in the upper half (candidate for lit signals / signs):")
    for a_, cx, cy, w_, h_ in blobs[:12]:
        bgr = arr[int(cy), int(cx)]
        print("   area=%-5d centre=(%4.0f,%4.0f) size=%2dx%2d  BGR=(%3d,%3d,%3d)"
              % (a_, cx, cy, w_, h_, bgr[0], bgr[1], bgr[2]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
