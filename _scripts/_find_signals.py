"""Find LIT traffic signals by colour in a rendered frame.

Renders the given camera, detects red / yellow / green compact blobs, and labels
them. This is evidence-based: it does not rely on any box-coordinate assumption.
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

CAMS = {
    "B_light10_road22": ([-45.2, -28.5, 6.0], -6.0, -89.7),
    "A_light17_road6": ([-81.4, -52.9, 6.0], -6.0, -22.1),
}


def render(world, loc, pitch, yaw):
    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(W))
    bp.set_attribute("image_size_y", str(H))
    bp.set_attribute("fov", str(FOV))
    tf = carla.Transform(carla.Location(*loc), carla.Rotation(pitch=pitch, yaw=yaw, roll=0.0))
    a = world.spawn_actor(bp, tf)
    got = []
    a.listen(lambda im: got.append(im))
    for _ in range(6):
        world.tick()
        time.sleep(0.05)
    time.sleep(0.6)
    a.stop()
    a.destroy()
    return np.frombuffer(got[-1].raw_data, np.uint8).reshape(H, W, 4)[:, :, :3].copy()


def find_signals(arr, tag, tiles):
    hsv = cv2.cvtColor(arr, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[:, :, 0].astype(int), hsv[:, :, 1].astype(int), hsv[:, :, 2].astype(int)
    masks = {
        "RED": (((h < 8) | (h > 172)) & (s > 130) & (v > 120)).astype(np.uint8),
        "YELLOW": ((h > 18) & (h < 34) & (s > 130) & (v > 150)).astype(np.uint8),
        "GREEN": ((h > 45) & (h < 90) & (s > 110) & (v > 110)).astype(np.uint8),
    }
    out = []
    ov = arr.copy()
    for name, m in masks.items():
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8))
        n, lab, stats, cent = cv2.connectedComponentsWithStats(m, 8)
        for i in range(1, n):
            a_ = stats[i, cv2.CC_STAT_AREA]
            w_ = stats[i, cv2.CC_STAT_WIDTH]
            h_ = stats[i, cv2.CC_STAT_HEIGHT]
            if a_ < 8 or a_ > 900:
                continue
            if max(w_, h_) / max(1, min(w_, h_)) > 5:      # too line-like
                continue
            cx, cy = cent[i]
            if cy > H * 0.75:
                continue
            bgr = arr[int(cy), int(cx)]
            out.append((name, a_, cx, cy, w_, h_, tuple(int(x) for x in bgr)))
            col = {"RED": (0, 0, 255), "YELLOW": (0, 255, 255), "GREEN": (0, 255, 0)}[name]
            cv2.circle(ov, (int(cx), int(cy)), max(8, max(w_, h_)), col, 2)
            cv2.putText(ov, "%s a=%d" % (name[0], a_), (int(cx) + 10, int(cy) - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, col, 2, cv2.LINE_AA)
            x0, y0 = max(0, int(cx) - 40), max(0, int(cy) - 40)
            tiles.append(cv2.resize(arr[y0:y0 + 80, x0:x0 + 80].copy(), (110, 110)))
    cv2.imwrite(os.path.join(OUTDIR, "signals_%s.png" % tag), ov)
    return out


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(20.0)
    world = client.get_world()
    st = {a.id: str(a.get_state()) for a in world.get_actors().filter("traffic.traffic_light*")}
    print("light states now:", {k: st[k] for k in sorted(st)})

    for tag, (loc, pitch, yaw) in CAMS.items():
        arr = render(world, loc, pitch, yaw)
        tiles = []
        found = find_signals(arr, tag, tiles)
        print("\n%s  camera=%s pitch=%.1f yaw=%.1f -> %d signal-coloured blobs"
              % (tag, loc, pitch, yaw, len(found)))
        for f in sorted(found, key=lambda t: -t[1])[:10]:
            print("   %-6s area=%-4d at (%4.0f,%4.0f) size=%2dx%-2d  BGR=%s"
                  % (f[0], f[1], f[2], f[3], f[4], f[5], f[6]))
        if tiles:
            while len(tiles) % 8:
                tiles.append(np.zeros((110, 110, 3), np.uint8))
            rows = [np.hstack(tiles[i:i + 8]) for i in range(0, min(len(tiles), 24), 8)]
            cv2.imwrite(os.path.join(OUTDIR, "signals_%s_crops.png" % tag), np.vstack(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
