"""Render preview frames for the top camera candidates + measure crosswalk coverage.

Shows the user what each candidate actually looks like, with the four required
targets marked. Also reports how much of the crosswalk's WIDTH fits in frame.

Writes E:\\output\\_camera_check\\preview_<name>.png and preview_sheet.png
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
os.makedirs(OUTDIR, exist_ok=True)
sys.path.insert(0, r"E:\output\_scripts")
from _spec_check import rot_matrix, v3, crosswalk_polys  # noqa: E402

W, H, FOV = 1280, 720, 90.0

CANDIDATES = [
    # name, camera loc, pitch, yaw, target dict
    {"name": "A_light17_road6_lane-2",
     "cam": [-81.4, -52.9, 6.0], "pitch": -6.0, "yaw": -22.1,
     "stop": [-68.4, -61.7], "cw": [-64.1, -54.4], "head": [-59.7, -60.8, 5.15],
     "junc": [-65.4, -66.3]},
    {"name": "B_light10_road22_lane1",
     "cam": [-45.2, -28.5, 6.0], "pitch": -6.0, "yaw": -89.7,
     "stop": [-45.1, -42.5], "cw": [-55.9, -46.7], "head": [-43.7, -50.6, 5.15],
     "junc": [-44.6, -57.5]},
    {"name": "C_light9_road7_lane1",
     "cam": [-11.6, -64.6, 6.0], "pitch": -6.0, "yaw": -179.4,
     "stop": [-25.6, -64.8], "cw": [-31.2, -72.1], "head": [-45.7, -64.3, 5.15],
     "junc": [-20.6, -64.8]},
]


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


def grab(world, tf):
    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(W))
    bp.set_attribute("image_size_y", str(H))
    bp.set_attribute("fov", str(FOV))
    cam = world.spawn_actor(bp, tf)
    got = []
    cam.listen(lambda img: got.append(img))
    for _ in range(6):
        world.tick()
        time.sleep(0.05)
    time.sleep(0.6)
    cam.stop()
    cam.destroy()
    return np.frombuffer(got[-1].raw_data, np.uint8).reshape(H, W, 4)[:, :, :3].copy()


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(20.0)
    world = client.get_world()
    m = world.get_map()

    # crosswalk polygons, grouped by proximity: use raw points clustered at 8 m
    pts = m.get_crosswalks()
    clusters = {}
    for p in pts:
        clusters.setdefault((round(p.x / 8.0), round(p.y / 8.0)), []).append(np.array([p.x, p.y]))

    sheet_tiles = []
    summary = []
    for cand in CANDIDATES:
        cam = Cam(cand["cam"], cand["pitch"], cand["yaw"])
        tf = carla.Transform(
            carla.Location(x=cand["cam"][0], y=cand["cam"][1], z=cand["cam"][2]),
            carla.Rotation(pitch=cand["pitch"], yaw=cand["yaw"], roll=0.0))
        arr = grab(world, tf)
        ov = arr.copy()
        marks = {}
        keymap = {"STOP": "stop", "CW": "cw", "HEAD": "head", "JUNC": "junc"}
        for key, color in (("STOP", (0, 255, 255)), ("CW", (0, 255, 0)),
                           ("HEAD", (255, 0, 255)), ("JUNC", (0, 128, 255))):
            wp_ = cand[keymap[key]]
            if len(wp_) == 2:
                wp_ = [wp_[0], wp_[1], 0.15 if key != "HEAD" else 5.15]
            r = cam.project(wp_)
            marks[key] = r
            if r and 0 <= r[0] < W and 0 <= r[1] < H:
                cv2.drawMarker(ov, (int(r[0]), int(r[1])), color, cv2.MARKER_CROSS, 26, 2)
                cv2.putText(ov, key, (int(r[0]) + 8, int(r[1]) - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)
        cv2.putText(ov, cand["name"], (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.imwrite(os.path.join(OUTDIR, "preview_%s.png" % cand["name"]), ov)
        sheet_tiles.append(cv2.resize(ov, (W // 2, H // 2)))

        # crosswalk width coverage: all raw points within 40 m of the target crosswalk centre
        cw_c = np.array(cand["cw"])
        near = [p for p in pts if np.linalg.norm(np.array([p.x, p.y]) - cw_c) < 12.0]
        if near:
            us = []
            for p in near:
                r = cam.project([p.x, p.y, p.z])
                if r:
                    us.append(r[0])
            if us:
                inside = sum(1 for u in us if 0 <= u < W)
                summary.append("%s: crosswalk points near target = %d, in frame horizontally %d (%.0f%%), u range %.0f..%.0f"
                               % (cand["name"], len(near), inside, 100.0 * inside / len(near), min(us), max(us)))
            else:
                summary.append("%s: crosswalk points all off-axis" % cand["name"])

    sheet = np.vstack([np.hstack(sheet_tiles[0:2]),
                       np.hstack(sheet_tiles[2:4]) if len(sheet_tiles) >= 4 else np.hstack([sheet_tiles[2], np.zeros_like(sheet_tiles[2])])])
    cv2.imwrite(os.path.join(OUTDIR, "preview_sheet.png"), sheet)

    print("\n".join(summary))
    print("\nwrote preview_sheet.png + %d preview_*.png" % len(CANDIDATES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
