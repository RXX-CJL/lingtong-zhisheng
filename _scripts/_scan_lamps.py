"""Locate LIT signal lamps directly in the rendered frame (colour + compactness +
proximity to a grey housing), and report their true on-screen size.

This bypasses the light-box coordinate question entirely.
"""
import math
import os
import sys
import time

import numpy as np
import carla
import cv2

OUTDIR = r"E:\output\_camera_verify"
os.makedirs(OUTDIR, exist_ok=True)
sys.path.insert(0, r"E:\output\_scripts")
from _spec_check import Proj  # noqa: E402

W, H, FOV = 1920, 1080, 90.0


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(25.0)
    world = client.get_world()
    spec = world.get_spectator().get_transform()

    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(W))
    bp.set_attribute("image_size_y", str(H))
    bp.set_attribute("fov", str(FOV))
    ca = world.spawn_actor(bp, spec)
    frames = []
    ca.listen(lambda im: frames.append(im))
    for _ in range(6):
        world.tick()
        time.sleep(0.05)
    time.sleep(0.7)
    ca.stop()
    ca.destroy()
    arr = np.frombuffer(frames[-1].raw_data, np.uint8).reshape(H, W, 4)[:, :, :3].copy()
    cv2.imwrite(os.path.join(OUTDIR, "lit_scan_frame.png"), arr)

    hsv = cv2.cvtColor(arr, cv2.COLOR_BGR2HSV)
    Hh, S, V = hsv[:, :, 0].astype(np.int16), hsv[:, :, 1].astype(np.int16), hsv[:, :, 2].astype(np.int16)

    # a lit lamp: strongly coloured AND brighter than its immediate surroundings
    grey = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
    local = cv2.blur(grey.astype(np.float32), (31, 31))
    bright = grey.astype(np.float32) > (local + 12)

    masks = {
        "RED": (((Hh < 10) | (Hh > 170)) & (S > 100) & (V > 120)),
        "YELLOW": ((Hh > 16) & (Hh < 38) & (S > 100) & (V > 150)),
        "GREEN": ((Hh > 40) & (Hh < 100) & (S > 80) & (V > 130)),
    }
    found = []
    for name, m in masks.items():
        mm = (m & bright).astype(np.uint8) * 255
        mm = cv2.morphologyEx(mm, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        n, lab, stats, cent = cv2.connectedComponentsWithStats(mm, 8)
        for i in range(1, n):
            a_ = int(stats[i, cv2.CC_STAT_AREA])
            w_ = int(stats[i, cv2.CC_STAT_WIDTH])
            h_ = int(stats[i, cv2.CC_STAT_HEIGHT])
            if a_ < 10:
                continue
            ar = max(w_, h_) / max(1, min(w_, h_))
            if ar > 4.0:
                continue
            cx, cy = cent[i]
            # a lamp is surrounded by a dark grey housing: check ring darkness
            x0, y0 = int(max(0, cx - 22)), int(max(0, cy - 22))
            x1, y1 = int(min(W, cx + 22)), int(min(H, cy + 22))
            patch = grey[y0:y1, x0:x1]
            ring = float(patch.mean())
            found.append({"colour": name, "area": a_, "x": float(cx), "y": float(cy),
                          "w": w_, "h": h_, "ar": round(ar, 2), "ring_grey": round(ring, 1),
                          "bgr": [int(v) for v in arr[int(cy), int(cx)]]})
    found.sort(key=lambda d: -d["area"])
    print("spectator loc=(%.2f,%.2f,%.2f) pitch=%.2f yaw=%.2f"
          % (spec.location.x, spec.location.y, spec.location.z,
             spec.rotation.pitch, spec.rotation.yaw))
    print("\nlit-lamp candidates (coloured + locally bright, compact):")
    print("  %-7s %-6s %-16s %-10s %-8s %s" % ("colour", "area", "centre", "size", "aspect", "ring grey"))
    for f in found[:20]:
        print("  %-7s %-6d (%6.0f,%5.0f) %4dx%-4d %-8s %.1f  BGR=%s"
              % (f["colour"], f["area"], f["x"], f["y"], f["w"], f["h"], f["ar"], f["ring_grey"], f["bgr"]))

    ov = arr.copy()
    for f in found[:20]:
        col = {"RED": (0, 0, 255), "YELLOW": (0, 255, 255), "GREEN": (0, 255, 0)}[f["colour"]]
        cv2.rectangle(ov, (int(f["x"] - f["w"] / 2) - 6, int(f["y"] - f["h"] / 2) - 6),
                      (int(f["x"] + f["w"] / 2) + 6, int(f["y"] + f["h"] / 2) + 6), col, 2)
        cv2.putText(ov, "%s %dx%d" % (f["colour"][0], f["w"], f["h"]),
                    (int(f["x"]) + 10, int(f["y"]) - 10), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, col, 2, cv2.LINE_AA)
    cv2.imwrite(os.path.join(OUTDIR, "lit_scan_marked.png"), ov)
    print("\nwrote lit_scan_frame.png / lit_scan_marked.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
