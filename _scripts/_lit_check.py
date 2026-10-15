"""Consolidated evidence: render the three candidate camera views in ONE pass
(same light cycle), detect signal-coloured compact blobs in each, crop them, and
build a contact sheet. Answers "which candidate actually shows a lit signal".
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
CAMS = [
    ("A_light17", [-81.4, -52.9, 6.0], -6.0, -22.1),
    ("B_light10", [-45.2, -28.5, 6.0], -6.0, -89.7),
    ("C_light9", [-11.6, -64.6, 6.0], -6.0, -179.4),
]


def render(world, loc, pitch, yaw):
    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(W))
    bp.set_attribute("image_size_y", str(H))
    bp.set_attribute("fov", str(FOV))
    tf = carla.Transform(carla.Location(*loc), carla.Rotation(pitch=pitch, yaw=yaw, roll=0.0))
    a = world.spawn_actor(bp, tf)
    got = []
    a.listen(lambda im: got.append(im))
    for _ in range(4):
        world.tick()
        time.sleep(0.04)
    time.sleep(0.5)
    a.stop()
    a.destroy()
    return np.frombuffer(got[-1].raw_data, np.uint8).reshape(H, W, 4)[:, :, :3].copy()


def blobs(arr):
    hsv = cv2.cvtColor(arr, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[:, :, 0].astype(int), hsv[:, :, 1].astype(int), hsv[:, :, 2].astype(int)
    masks = {
        "RED": (((h < 8) | (h > 172)) & (s > 120) & (v > 130)),
        "YEL": ((h > 18) & (h < 34) & (s > 120) & (v > 150)),
        "GRN": ((h > 45) & (h < 95) & (s > 100) & (v > 120)),
    }
    out = []
    for name, m in masks.items():
        mm = (m.astype(np.uint8)) * 255
        mm = cv2.morphologyEx(mm, cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8))
        n, lab, stats, cent = cv2.connectedComponentsWithStats(mm, 8)
        for i in range(1, n):
            a_ = int(stats[i, cv2.CC_STAT_AREA])
            w_ = int(stats[i, cv2.CC_STAT_WIDTH])
            h_ = int(stats[i, cv2.CC_STAT_HEIGHT])
            if a_ < 6 or a_ > 1200:
                continue
            if max(w_, h_) / max(1, min(w_, h_)) > 4:
                continue
            cx, cy = cent[i]
            if cy > H * 0.72:
                continue
            out.append({"colour": name, "area": a_, "x": float(cx), "y": float(cy),
                        "w": w_, "h": h_, "bgr": [int(x) for x in arr[int(cy), int(cx)]]})
    out.sort(key=lambda d: -d["area"])
    return out


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(20.0)
    world = client.get_world()
    states = {a.id: str(a.get_state()) for a in world.get_actors().filter("traffic.traffic_light*")}
    print("light states at start:", {k: states[k] for k in sorted(states)})
    print("distinct states:", sorted(set(states.values())))

    tiles_top, tiles_crop = [], []
    for tag, loc, pitch, yaw in CAMS:
        arr = render(world, loc, pitch, yaw)
        bl = blobs(arr)
        ov = arr.copy()
        for b in bl:
            col = {"RED": (0, 0, 255), "YEL": (0, 255, 255), "GRN": (0, 255, 0)}[b["colour"]]
            cv2.circle(ov, (int(b["x"]), int(b["y"])), max(8, max(b["w"], b["h"])), col, 2)
            cv2.putText(ov, "%s%d" % (b["colour"], b["area"]), (int(b["x"]) + 9, int(b["y"]) - 9),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 2, cv2.LINE_AA)
        cv2.putText(ov, tag, (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.imwrite(os.path.join(OUTDIR, "lit_%s.png" % tag), ov)
        tiles_top.append(cv2.resize(ov, (W // 2, H // 2)))
        print("\n%s -> %d compact signal-coloured blobs (upper 72%% of frame)" % (tag, len(bl)))
        for b in bl[:8]:
            print("   %-3s area=%-4d at (%4.0f,%4.0f) %2dx%-2d BGR=%s"
                  % (b["colour"], b["area"], b["x"], b["y"], b["w"], b["h"], b["bgr"]))
            x0, y0 = max(0, int(b["x"]) - 36), max(0, int(b["y"]) - 36)
            tiles_crop.append(cv2.resize(arr[y0:y0 + 72, x0:x0 + 72].copy(), (96, 96)))

    while len(tiles_top) % 2:
        tiles_top.append(np.zeros_like(tiles_top[0]))
    sheet = np.vstack([np.hstack(tiles_top[0:2]),
                       np.hstack(tiles_top[2:4]) if len(tiles_top) >= 4 else np.hstack(tiles_top[2:4])])
    cv2.imwrite(os.path.join(OUTDIR, "lit_sheet.png"), sheet)
    if tiles_crop:
        while len(tiles_crop) % 8:
            tiles_crop.append(np.zeros((96, 96, 3), np.uint8))
        rows = [np.hstack(tiles_crop[i:i + 8]) for i in range(0, min(len(tiles_crop), 32), 8)]
        cv2.imwrite(os.path.join(OUTDIR, "lit_crops.png"), np.vstack(rows))
    print("\nwrote lit_sheet.png + lit_crops.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
