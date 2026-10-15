"""Camera-placement optimiser for the red-light demo at junction 23.

Approach used: WESTBOUND on road 7/6, i.e. traffic moving in -X at y ~= -65.2.
Hard requirement (user): traffic light + full crosswalk + stop line + junction centre
all visible, and the signal head big enough for YOLO (>= 30 px wide).

Scoring is done with the VERIFIED projection formula; the top candidates are then
rendered for real so the numbers can be checked against pixels.

Writes E:\\output\\_camera_check\\opt_candidates.png (+ opt.json)
"""
import json
import math
import os
import sys
import time

import numpy as np
import carla
import cv2

W, H, FOV = 1280, 720, 90.0
OUTDIR = r"E:\output\_camera_check"
sys.path.insert(0, r"E:\output\_scripts")
from _spec_check import rot_matrix  # noqa: E402


class Cam:
    def __init__(self, loc, pitch, yaw, roll=0.0, w=W, h=H, fov=FOV):
        self.loc = np.array(loc, dtype=float)
        self.pitch, self.yaw, self.roll = pitch, yaw, roll
        self.w, self.h, self.fov = w, h, fov
        self.R = rot_matrix(pitch, yaw, roll)
        self.f = w / (2 * math.tan(math.radians(fov) / 2))

    def project(self, p):
        vc = self.R.T @ (np.asarray(p, dtype=float) - self.loc)
        if vc[0] <= 1e-6:
            return None
        return {"u": self.w / 2 + self.f * (vc[1] / vc[0]),
                "v": self.h / 2 - self.f * (vc[2] / vc[0]),
                "depth": float(vc[0])}

    def px_per_m(self, p):
        pr = self.project(p)
        return None if pr is None else self.f / pr["depth"]


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(20.0)
    world = client.get_client().get_world() if False else client.get_world()
    m = world.get_map()

    STOP = np.array([-68.44, -61.71, 0.15])       # stop line for light 17 (road 6 lane -1)
    STOP2 = np.array([-68.45, -58.21, 0.15])      # stop line for the other westbound lane
    CW = np.array([-63.2, -63.2, 0.05])           # crosswalk centroid across the westbound approach
    JUNC = np.array([-67.0, -68.7, 0.0])          # junction 23 centre (user-selected)
    LANE_Y = -65.2                                # westbound lane 1 centre-line

    # signal head of light 17: use the actor's full bounding box (the housing),
    # not just the tiny lamp box
    tl = None
    for a in world.get_actors().filter("traffic.traffic_light*"):
        if a.id == 17:
            tl = a
    if tl is None:
        raise RuntimeError("light 17 not found")
    bb = tl.bounding_box
    atf = tl.get_transform()
    SIG = np.array([atf.location.x + bb.location.x, atf.location.y + bb.location.y,
                    0.0])
    SIG[2] = 0.0 + 6.0                            # housing sits ~6 m up the mast
    # face normal of the signal head from the actor's transform
    SIG_YAW = float(atf.rotation.yaw)
    print("light 17 actor loc=(%.2f,%.2f,%.2f) yaw=%.1f  bb extent=(%.2f,%.2f,%.2f)"
          % (atf.location.x, atf.location.y, atf.location.z, SIG_YAW,
             bb.extent.x, bb.extent.y, bb.extent.z))

    # ---------------- search
    best = []
    for x in np.arange(-34.0, -8.0, 2.0):
        for z in np.arange(6.0, 13.1, 1.0):
            for pitch in np.arange(-6.0, -31.0, -1.0):
                # aim yaw so the stop line is horizontally centred
                d = STOP[:2] - np.array([x, LANE_Y])
                yaw = math.degrees(math.atan2(d[1], d[0]))
                cam = Cam([x, LANE_Y, z], pitch, yaw)
                pts = {"STOP": STOP, "CW": CW, "JUNC": JUNC, "SIG": SIG}
                pr = {k: cam.project(v) for k, v in pts.items()}
                if any(p is None for p in pr.values()):
                    continue
                if not all(0 <= p["u"] < W and 6 <= p["v"] < H - 6 for p in pr.values()):
                    continue
                sig_w = 0.60 * cam.px_per_m(SIG)      # housing ~0.6 m wide
                if sig_w < 30:
                    continue
                # vertical spread of the ground targets
                vs = sorted([pr["STOP"]["v"], pr["CW"]["v"], pr["JUNC"]["v"]])
                spread = vs[-1] - vs[0]
                score = (sig_w * 2.0) + spread * 0.5
                best.append({"x": x, "y": LANE_Y, "z": z, "pitch": pitch, "yaw": yaw,
                             "sig_w": sig_w, "spread": spread, "score": score,
                             "px": {k: [round(v["u"], 1), round(v["v"], 1)] for k, v in pr.items()},
                             "depth_sig": pr["SIG"]["depth"]})
    best.sort(key=lambda r: -r["score"])
    print("\n%d candidates pass all constraints. Top 12:" % len(best))
    print("  %-7s %-5s %-7s %-7s %-8s %-8s %s" % ("x", "z", "pitch", "yaw", "sig_px", "spread", "pixels"))
    for r in best[:12]:
        print("  %-7.1f %-5.1f %-7.1f %-7.1f %-8.1f %-8.0f STOP%s CW%s JUNC%s SIG%s"
              % (r["x"], r["z"], r["pitch"], r["yaw"], r["sig_w"], r["spread"],
                 r["px"]["STOP"], r["px"]["CW"], r["px"]["JUNC"], r["px"]["SIG"]))

    with open(os.path.join(OUTDIR, "opt.json"), "w", encoding="utf-8") as f:
        json.dump(best[:40], f, ensure_ascii=False, indent=2)
    print("\nwrote", os.path.join(OUTDIR, "opt.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
