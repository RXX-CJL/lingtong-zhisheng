"""Confirmation frame for the user's CURRENT camera pose, at 1920x1080, with every
required target projected and labelled. Also reports the exact pose and the
apparent size of the lights that control this road.

Writes E:\\output\\_camera_verify\\confirm_1080.png (+ .json)
"""
import json
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
from _spec_check import rot_matrix  # noqa: E402

FOV = 90.0
W, H = 1920, 1080


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


def build_targets(world, m):
    """Targets: stop lines + crosswalk bands + lit-signal blobs + junction centre."""
    t = []
    for a in world.get_actors().filter("traffic.traffic_light*"):
        try:
            st = str(a.get_state())
        except Exception:
            st = "?"
        try:
            for wp in a.get_stop_waypoints():
                wl = wp.transform.location
                t.append(("STOP_L%d_%s" % (a.id, st[:1]), [wl.x, wl.y, 0.15], (0, 255, 255)))
        except Exception:
            pass
    # crosswalk bands: cluster raw vertices at 6 m
    cells = {}
    for p in m.get_crosswalks():
        cells.setdefault((round(p.x / 6.0), round(p.y / 6.0)), []).append((p.x, p.y))
    for k, v in cells.items():
        cx = (min(q[0] for q in v) + max(q[0] for q in v)) / 2
        cy = (min(q[1] for q in v) + max(q[1] for q in v)) / 2
        t.append(("CW", [cx, cy, 0.05], (0, 255, 0)))
    return t


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(25.0)
    world = client.get_world()
    m = world.get_map()
    spec = world.get_spectator().get_transform()

    cam = Cam([spec.location.x, spec.location.y, spec.location.z],
              spec.rotation.pitch, spec.rotation.yaw)
    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(W))
    bp.set_attribute("image_size_y", str(H))
    bp.set_attribute("fov", str(FOV))
    a = world.spawn_actor(bp, carla.Transform(spec.location, spec.rotation))
    got = []
    a.listen(lambda im: got.append(im))
    for _ in range(6):
        world.tick()
        time.sleep(0.05)
    time.sleep(0.7)
    a.stop()
    a.destroy()
    arr = np.frombuffer(got[-1].raw_data, np.uint8).reshape(H, W, 4)[:, :, :3].copy()

    ov = arr.copy()
    info = {"pose": {"loc": [spec.location.x, spec.location.y, spec.location.z],
                     "rot": [spec.rotation.pitch, spec.rotation.yaw, spec.rotation.roll],
                     "f_px": cam.f, "size": [W, H], "fov": FOV},
            "targets": []}
    nm_in = {}
    for name, pt, col in build_targets(world, m):
        r = cam.project(pt)
        if r is None:
            continue
        inside = 0 <= r[0] < W and 0 <= r[1] < H
        info["targets"].append({"name": name, "world": pt,
                                "pixel": [round(r[0], 1), round(r[1], 1)],
                                "depth": round(r[2], 1), "in": bool(inside)})
        if inside:
            key = name.split("_")[0]
            nm_in[key] = nm_in.get(key, 0) + 1
            cv2.drawMarker(ov, (int(r[0]), int(r[1])), col, cv2.MARKER_CROSS, 24, 2)
            if name.startswith(("STOP", "CW")) and nm_in[key] <= 8:
                cv2.putText(ov, name, (int(r[0]) + 8, int(r[1]) - 8), cv2.FONT_HERSHEY_SIMPLEX,
                            0.6, col, 2, cv2.LINE_AA)
    cv2.imwrite(os.path.join(OUTDIR, "confirm_1080.png"), ov)

    print("POSE  loc=(%.3f,%.3f,%.3f)  pitch=%.3f yaw=%.3f roll=%.3f  f=%.1fpx  %dx%d"
          % (spec.location.x, spec.location.y, spec.location.z,
             spec.rotation.pitch, spec.rotation.yaw, spec.rotation.roll, cam.f, W, H))
    print("\nin-frame targets: %s" % nm_in)

    # apparent size of the lights controlling the road the camera looks down (road 6 / 7)
    print("\nApparent size of signal heads for lights that stop road 6 / road 7 traffic:")
    for tl in world.get_actors().filter("traffic.traffic_light*"):
        roads = set()
        try:
            for wp in tl.get_stop_waypoints():
                roads.add(wp.road_id)
        except Exception:
            pass
        if not (roads & {6, 7}):
            continue
        atf = tl.get_transform()
        try:
            st = str(tl.get_state())
        except Exception:
            st = "?"
        for i, b in enumerate(tl.get_light_boxes()):
            if max(b.extent.x, b.extent.y) > 2.0:
                continue
            wl = atf.location + atf.transform(b.location)
            r = cam.project([wl.x, wl.y, wl.z])
            if not r:
                continue
            ppm = cam.f / r[2]
            print("   light %-3d %-6s box#%d -> px=(%5.0f,%5.0f) size %5.1f x %-5.1f px  depth %5.1f m  %s"
                  % (tl.id, st, i, r[0], r[1], 2 * b.extent.x * ppm, 2 * b.extent.z * ppm,
                     r[2], "IN FRAME" if (0 <= r[0] < W and 0 <= r[1] < H) else "off"))

    # the closest vehicle lane stop line -> how far is the demo stop line?
    print("\nStop lines for road 6 / road 7 (demo approach):")
    for tl in world.get_actors().filter("traffic.traffic_light*"):
        try:
            wps = tl.get_stop_waypoints()
        except Exception:
            continue
        for wp in wps:
            if wp.road_id not in (6, 7):
                continue
            wl = wp.transform.location
            d = math.dist([wl.x, wl.y, wl.z], [spec.location.x, spec.location.y, spec.location.z])
            r = cam.project([wl.x, wl.y, wl.z])
            print("   light %-3d road %d lane %-3d stop=(%.1f,%.1f)  dist=%.1f m  pixel=%s"
                  % (tl.id, wp.road_id, wp.lane_id, wl.x, wl.y, d,
                     ("(%.0f,%.0f) %s" % (r[0], r[1], "IN" if (0 <= r[0] < W and 0 <= r[1] < H) else "BELOW")) if r else "off"))

    with open(os.path.join(OUTDIR, "confirm_1080.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    print("\nwrote confirm_1080.png / confirm_1080.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
