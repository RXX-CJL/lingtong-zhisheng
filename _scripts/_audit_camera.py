"""Precise on-screen measurement of the USER'S current camera:
for every traffic light, compute the apparent pixel size of its real signal heads
(the lamp boxes), which lane each serves, and where it lands in frame.

This answers: "can the current camera see a red light big enough to judge colour?"
"""
import json
import math
import os
import sys

import numpy as np
import carla

sys.path.insert(0, r"E:\output\_scripts")
from _spec_check import Proj, v3  # noqa: E402

OUT = r"E:\output\_camera_check\current_camera_audit.json"


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(20.0)
    world = client.get_world()
    m = world.get_map()
    tf = world.get_spectator().get_transform()
    pr = Proj(tf, 1280, 720, 90.0)
    cam = np.array(v3(tf.location))

    print("=" * 100)
    print("USER CAMERA AUDIT   loc=(%.2f,%.2f,%.2f) pitch=%.2f yaw=%.2f  fov=90  1280x720"
          % (cam[0], cam[1], cam[2], tf.rotation.pitch, tf.rotation.yaw))
    print("=" * 100)

    rows = []
    for a in world.get_actors().filter("traffic.traffic_light*"):
        try:
            state = str(a.get_state())
        except Exception:
            state = "?"
        boxes = a.get_light_boxes()
        heads = []
        for b in boxes:
            if max(b.extent.x, b.extent.y) > 2.0:
                continue                              # mast arm
            wl = np.array([b.location.x, b.location.y, b.location.z])   # world coords
            ext = np.array([b.extent.x, b.extent.y, b.extent.z])
            heads.append((wl, ext))
        if not heads:
            continue
        # the main vehicle head = tallest box (z extent) among the small ones
        heads.sort(key=lambda t: -t[1][2])
        main_head, ext = heads[0]
        p = pr.project(main_head)
        if p is None:
            continue
        depth = p["depth"]
        ppm = pr.f / depth
        w_px = 2 * ext[0] * ppm
        h_px = 2 * ext[2] * ppm
        lanes = []
        try:
            for wp in a.get_stop_waypoints():
                lanes.append("road%d/lane%d" % (wp.road_id, wp.lane_id))
        except Exception:
            pass
        rows.append({"id": a.id, "state": state, "head": [round(float(x), 2) for x in main_head],
                     "ext_m": [round(float(x), 3) for x in ext],
                     "pixel": [round(p["u"], 1), round(p["v"], 1)],
                     "depth": round(depth, 1), "w_px": round(w_px, 1), "h_px": round(h_px, 1),
                     "in_frame": bool(p["in_frame"]), "lanes": lanes, "n_heads": len(heads)})

    rows.sort(key=lambda r: r["depth"])
    print("\n%-4s %-6s %-9s %-24s %-16s %-7s %-7s %s"
          % ("id", "state", "depth", "head world", "pixel", "w_px", "h_px", "serves"))
    for r in rows[:16]:
        print("%-4d %-6s %-9.1f (%8.2f,%8.2f,%5.2f)  (%5.0f,%5.0f) %-7.1f %-7.1f %s %s"
              % (r["id"], r["state"], r["depth"], r["head"][0], r["head"][1], r["head"][2],
                 r["pixel"][0], r["pixel"][1], r["w_px"], r["h_px"],
                 ",".join(r["lanes"][:2]), "IN" if r["in_frame"] else "out"))

    in_frame = [r for r in rows if r["in_frame"]]
    print("\nIN-FRAME traffic lights: %d" % len(in_frame))
    for r in in_frame:
        print("   id=%-3d state=%-6s depth=%6.1fm  head on screen %.1f x %.1f px  serves %s"
              % (r["id"], r["state"], r["depth"], r["w_px"], r["h_px"], ",".join(r["lanes"])))

    # how big WOULD the head be if the camera were 20 m from it?
    print("\nReference: apparent head size vs distance (head = 0.40 m wide, 1.18 m tall, f=640):")
    for d in (10, 15, 20, 25, 30, 40, 60, 80):
        print("   %3d m -> %6.1f x %6.1f px" % (d, 0.40 * 640.0 / d * 2, 1.18 * 640.0 / d))

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"cam": v3(tf.location), "rows": rows}, f, ensure_ascii=False, indent=2)
    print("\nwrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
