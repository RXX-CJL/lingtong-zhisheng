"""FIXED light-box handling: world = actor.get_transform().transform(box.location)
(the documented pitfall -- box locations are actor-relative, NOT world coords).

Renders candidate-B camera and reports where each lamp REALLY is on screen.
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
    cv2.imwrite(os.path.join(OUTDIR, "fix_B_frame.png"), arr)

    print("%-4s %-6s %-30s %-16s %-8s %s" % ("id", "state", "lamp world (actor-relative FIXED)", "pixel", "size", "in"))
    rows = []
    for tl in world.get_actors().filter("traffic.traffic_light*"):
        try:
            st = str(tl.get_state())
        except Exception:
            st = "?"
        atf = tl.get_transform()
        for i, b in enumerate(tl.get_light_boxes()):
            if max(b.extent.x, b.extent.y) > 2.0:
                continue
            wl = atf.location + atf.transform(b.location)     # <-- the FIX
            ext = np.array([b.extent.x, b.extent.y, b.extent.z])
            r = cam.project([wl.x, wl.y, wl.z])
            if r is None:
                continue
            u, v = int(round(r[0])), int(round(r[1]))
            inside = 0 <= u < W and 0 <= v < H
            ppm = cam.f / r[2]
            rows.append({"id": tl.id, "state": st, "world": [round(wl.x, 2), round(wl.y, 2), round(wl.z, 2)],
                         "px": [u, v], "w": round(2 * ext[0] * ppm, 1), "h": round(2 * ext[2] * ppm, 1),
                         "in": inside, "depth": round(r[2], 1), "ext": [round(float(e), 2) for e in ext]})
    rows.sort(key=lambda d: (not d["in"], d["depth"]))
    for d in rows[:20]:
        print("%-4d %-6s (%8.2f,%8.2f,%6.2f)  (%5d,%4d)  %4.1fx%-4.1f %s d=%.1f"
              % (d["id"], d["state"], d["world"][0], d["world"][1], d["world"][2],
                 d["px"][0], d["px"][1], d["w"], d["h"], "IN" if d["in"] else "out", d["depth"]))

    # draw all in-frame lamps
    ov = arr.copy()
    for d in rows:
        if not d["in"]:
            continue
        col = {"Red": (0, 0, 255), "Yellow": (0, 255, 255), "Green": (0, 255, 0)}.get(d["state"], (255, 0, 255))
        cv2.drawMarker(ov, tuple(d["px"]), col, cv2.MARKER_CROSS, 22, 2)
        cv2.putText(ov, "%d %s" % (d["id"], d["state"][:3]), (d["px"][0] + 6, d["px"][1] - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 2, cv2.LINE_AA)
    cv2.imwrite(os.path.join(OUTDIR, "fix_B_marked.png"), ov)
    print("\nin-frame lamps: %d" % sum(1 for d in rows if d["in"]))
    print("wrote fix_B_marked.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
