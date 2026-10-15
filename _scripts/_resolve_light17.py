"""Resolve light-box coordinate semantics for LIGHT 17 (the light controlling the
lane the user's camera looks down) by rendering and testing BOTH interpretations
against the actual rendered signal housing.

Renders at 1920x1080 (the user's chosen recording resolution).
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
from _spec_check import rot_matrix  # noqa: E402

FOV = 90.0


class Cam:
    def __init__(self, loc, pitch, yaw, w, h, fov=FOV):
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
    client.set_timeout(25.0)
    world = client.get_world()
    spec = world.get_spectator().get_transform()
    print("spectator NOW loc=(%.3f,%.3f,%.3f) rot=(%.3f,%.3f,%.3f)"
          % (spec.location.x, spec.location.y, spec.location.z,
             spec.rotation.pitch, spec.rotation.yaw, spec.rotation.roll))

    W, H = 1920, 1080
    cam = Cam([spec.location.x, spec.location.y, spec.location.z],
              spec.rotation.pitch, spec.rotation.yaw, W, H)
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
    cv2.imwrite(os.path.join(OUTDIR, "resolve_frame_1080.png"), arr)

    ov = arr.copy()
    print("\nlight 17 -- every box, both interpretations (1920x1080):")
    print("  %-4s %-11s %-26s %-15s %-9s %s" % ("box", "interp", "world", "pixel", "size px", "depth"))
    for tl in world.get_actors().filter("traffic.traffic_light*"):
        if tl.id != 17:
            continue
        atf = tl.get_transform()
        try:
            st = str(tl.get_state())
        except Exception:
            st = "?"
        print("  actor loc=(%.2f,%.2f,%.2f) yaw=%.1f state=%s"
              % (atf.location.x, atf.location.y, atf.location.z, atf.rotation.yaw, st))
        for i, b in enumerate(tl.get_light_boxes()):
            cands = {
                "transformed": (atf.location + atf.transform(b.location), (0, 255, 255)),
                "raw": (carla.Location(x=b.location.x, y=b.location.y, z=b.location.z), (255, 0, 255)),
            }
            for nm, (wl, col) in cands.items():
                r = cam.project([wl.x, wl.y, wl.z])
                if r is None:
                    print("  #%d %-11s off-axis" % (i, nm))
                    continue
                inside = 0 <= r[0] < W and 0 <= r[1] < H
                ppm = cam.f / r[2]
                sw, sh = 2 * b.extent.x * ppm, 2 * b.extent.z * ppm
                print("  #%d %-11s (%8.2f,%8.2f,%6.2f) (%6.0f,%5.0f) %5.1fx%-5.1f d=%.1f %s"
                      % (i, nm, wl.x, wl.y, wl.z, r[0], r[1], sw, sh, r[2], "IN" if inside else "out"))
                if inside:
                    cv2.drawMarker(ov, (int(r[0]), int(r[1])), col, cv2.MARKER_CROSS, 26, 3)
                    cv2.putText(ov, "%s#%d" % (nm[0].upper(), i), (int(r[0]) + 10, int(r[1]) - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, col, 2, cv2.LINE_AA)
    cv2.imwrite(os.path.join(OUTDIR, "resolve_marks_1080.png"), ov)

    # also mark the crosswalk and stop line for road 6 (light 17's approach)
    print("\nreference markers:")
    for nm, pt, col in (("STOP17", [-68.44, -61.71, 0.15], (0, 255, 255)),
                        ("CW_L63", [-63.2, -63.2, 0.05], (0, 255, 0)),
                        ("JUNC23", [-67.0, -68.7, 0.0], (255, 128, 0))):
        r = cam.project(pt)
        if r:
            print("  %-8s -> (%6.0f,%5.0f) %s" % (nm, r[0], r[1],
                                                  "IN" if (0 <= r[0] < W and 0 <= r[1] < H) else "OUT"))
            if 0 <= r[0] < W and 0 <= r[1] < H:
                cv2.drawMarker(ov, (int(r[0]), int(r[1])), col, cv2.MARKER_CROSS, 30, 3)
                cv2.putText(ov, nm, (int(r[0]) + 10, int(r[1]) + 24), cv2.FONT_HERSHEY_SIMPLEX,
                            0.8, col, 2, cv2.LINE_AA)
    cv2.imwrite(os.path.join(OUTDIR, "resolve_marks_1080.png"), ov)
    print("\nwrote resolve_frame_1080.png / resolve_marks_1080.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
