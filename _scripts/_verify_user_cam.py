"""Verify the USER'S camera as-is (T-junction reading): at 1280x720 and 1920x1080,
render the spectator view and locate every LIT signal by pixel evidence, then
report apparent size (the number that decides whether colour judging can work).

Light-box locations are searched over BOTH interpretations, and the one that
matches real pixels is reported.
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


def render(world, tf, w, h):
    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(w))
    bp.set_attribute("image_size_y", str(h))
    bp.set_attribute("fov", str(FOV))
    a = world.spawn_actor(bp, tf)
    got = []
    a.listen(lambda im: got.append(im))
    for _ in range(6):
        world.tick()
        time.sleep(0.05)
    time.sleep(0.7)
    a.stop()
    a.destroy()
    return np.frombuffer(got[-1].raw_data, np.uint8).reshape(h, w, 4)[:, :, :3].copy()


def lit_blobs(arr, w, h):
    hsv = cv2.cvtColor(arr, cv2.COLOR_BGR2HSV)
    H_, S_, V_ = hsv[:, :, 0].astype(int), hsv[:, :, 1].astype(int), hsv[:, :, 2].astype(int)
    masks = {
        "RED": (((H_ < 10) | (H_ > 170)) & (S_ > 90) & (V_ > 110)),
        "YEL": ((H_ > 16) & (H_ < 36) & (S_ > 90) & (V_ > 140)),
        "GRN": ((H_ > 40) & (H_ < 100) & (S_ > 70) & (V_ > 120)),
    }
    out = []
    for name, m in masks.items():
        mm = m.astype(np.uint8) * 255
        mm = cv2.morphologyEx(mm, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        n, lab, stats, cent = cv2.connectedComponentsWithStats(mm, 8)
        for i in range(1, n):
            a_ = int(stats[i, cv2.CC_STAT_AREA])
            w_ = int(stats[i, cv2.CC_STAT_WIDTH])
            h_ = int(stats[i, cv2.CC_STAT_HEIGHT])
            if a_ < 12 or a_ > 4000:
                continue
            ar = max(w_, h_) / max(1, min(w_, h_))
            if ar > 6:
                continue
            cx, cy = cent[i]
            out.append({"colour": name, "area": a_, "x": float(cx), "y": float(cy),
                        "w": w_, "h": h_, "ar": round(ar, 2),
                        "bgr": [int(v) for v in arr[int(cy), int(cx)]]})
    out.sort(key=lambda d: -d["area"])
    return out


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(25.0)
    world = client.get_world()
    spec = world.get_spectator().get_transform()
    print("spectator loc=(%.3f,%.3f,%.3f) rot=(%.2f,%.2f,%.2f)"
          % (spec.location.x, spec.location.y, spec.location.z,
             spec.rotation.pitch, spec.rotation.yaw, spec.rotation.roll))

    states_before = {a.id: str(a.get_state()) for a in world.get_actors().filter("traffic.traffic_light*")}
    print("states:", {k: states_before[k] for k in sorted(states_before)})

    for (w, h) in ((1280, 720), (1920, 1080)):
        cam = Cam([spec.location.x, spec.location.y, spec.location.z],
                  spec.rotation.pitch, spec.rotation.yaw, w, h)
        tf = carla.Transform(spec.location, spec.rotation)
        arr = render(world, tf, w, h)
        bl = lit_blobs(arr, w, h)
        ov = arr.copy()
        for b in bl:
            col = {"RED": (0, 0, 255), "YEL": (0, 255, 255), "GRN": (0, 255, 0)}[b["colour"]]
            cv2.circle(ov, (int(b["x"]), int(b["y"])), max(9, max(b["w"], b["h"])), col, 2)
            cv2.putText(ov, "%s a=%d %dx%d" % (b["colour"][0], b["area"], b["w"], b["h"]),
                        (int(b["x"]) + 10, int(b["y"]) - 10), cv2.FONT_HERSHEY_SIMPLEX,
                        0.55 * w / 1280 + 0.2, col, 2, cv2.LINE_AA)
        cv2.imwrite(os.path.join(OUTDIR, "verify_%dx%d.png" % (w, h)), ov)
        print("\n=== %dx%d  f=%.1f px  -> %d lit-signal-candidate blobs ===" % (w, h, cam.f, len(bl)))
        for b in bl[:14]:
            print("   %-3s area=%-5d at (%5.0f,%5.0f)  %3dx%-3d ar=%-4s BGR=%s"
                  % (b["colour"], b["area"], b["x"], b["y"], b["w"], b["h"], b["ar"], b["bgr"]))

    # lamp geometry under both interpretations, at 1920x1080
    cam = Cam([spec.location.x, spec.location.y, spec.location.z],
              spec.rotation.pitch, spec.rotation.yaw, 1920, 1080)
    print("\nLamp projections at 1920x1080 (both interpretations):")
    print("  %-4s %-5s %-11s %-26s %-15s %s" % ("id", "state", "interp", "world", "pixel", "size px"))
    for tl in world.get_actors().filter("traffic.traffic_light*"):
        atf = tl.get_transform()
        try:
            st = str(tl.get_state())
        except Exception:
            st = "?"
        for b in tl.get_light_boxes():
            if max(b.extent.x, b.extent.y) > 2.0:
                continue
            cands = {
                "transformed": atf.location + atf.transform(b.location),
                "raw": carla.Location(x=b.location.x, y=b.location.y, z=b.location.z),
            }
            for nm, wl in cands.items():
                r = cam.project([wl.x, wl.y, wl.z])
                if r is None or not (0 <= r[0] < 1920 and 0 <= r[1] < 1080):
                    continue
                ppm = cam.f / r[2]
                print("  %-4d %-5s %-11s (%8.2f,%8.2f,%6.2f) (%6.0f,%5.0f) %.1f x %.1f  d=%.1f"
                      % (tl.id, st, nm, wl.x, wl.y, wl.z, r[0], r[1],
                         2 * b.extent.x * ppm, 2 * b.extent.z * ppm, r[2]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
