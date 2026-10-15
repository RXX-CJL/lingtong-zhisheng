"""Map the junction neighbourhood the spectator sits in: which traffic lights
actually control this junction, their stop lines, bulb world positions and
apparent pixel size from the spectator.

Read-only apart from one camera spawn for a reference frame.
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
from _spec_check import Proj, v3  # noqa: E402


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(20.0)
    world = client.get_world()
    m = world.get_map()
    tf = world.get_spectator().get_transform()
    pr = Proj(tf, W, H, FOV)
    cam = np.array(v3(tf.location))

    # ---------- 1. junction extents around the camera
    print("=" * 90)
    print("SPECTATOR loc=(%.2f,%.2f,%.2f) yaw=%.1f pitch=%.1f" % (cam[0], cam[1], cam[2],
                                                                  tf.rotation.yaw, tf.rotation.pitch))
    print("=" * 90)

    junc_pts = []
    for dx in range(-90, 91, 4):
        for dy in range(-90, 91, 4):
            probe = carla.Location(x=float(cam[0] + dx), y=float(cam[1] + dy), z=2.0)
            wp = m.get_waypoint(probe, project_to_road=True, lane_type=carla.LaneType.Driving)
            if wp is not None and wp.is_junction:
                junc_pts.append((float(wp.transform.location.x), float(wp.transform.location.y),
                                 int(wp.road_id), int(wp.lane_id)))
    # grid-sample collisions mean identical waypoints repeat; dedupe
    uniq = {}
    for x, y, r, l in junc_pts:
        uniq[(round(x, 1), round(y, 1))] = (x, y, r, l)
    pts = list(uniq.values())
    if pts:
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        print("\n[1] JUNCTION containing the camera")
        print("    extent x: %.1f .. %.1f  (%.1f m)" % (min(xs), max(xs), max(xs) - min(xs)))
        print("    extent y: %.1f .. %.1f  (%.1f m)" % (min(ys), max(ys), max(ys) - min(ys)))
        print("    centre  : (%.1f, %.1f)   cam distance to centre %.1f m"
              % ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2,
                 math.hypot((min(xs) + max(xs)) / 2 - cam[0], (min(ys) + max(ys)) / 2 - cam[1])))
        print("    lanes involved: %s" % sorted({(p[2], p[3]) for p in pts}))
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        pc = pr.project([cx, cy, 0.0])
        print("    centre pixel = %s" % (("(%.0f,%.0f)" % (pc["u"], pc["v"])) if pc else "off-axis"))
    else:
        print("\n[1] camera is NOT inside a junction")

    # ---------- 2. traffic lights near the camera, with control relationship
    print("\n[2] TRAFFIC LIGHTS within 120 m  (bulb = smallest light box, world coords)")
    lights = []
    for actor in world.get_actors().filter("traffic.traffic_light*"):
        try:
            boxes = actor.get_light_boxes()
        except Exception:
            boxes = []
        atf = actor.get_transform()
        best = None
        for b in boxes:
            wl = atf.location + atf.transform(b.location)
            vol = b.extent.x * b.extent.y * b.extent.z
            if best is None or vol < best[0]:
                best = (vol, wl, b.extent)
        if best is None:
            continue
        wl = v3(best[1])
        d = float(np.linalg.norm(np.array(wl) - cam))
        if d > 120:
            continue
        p = pr.project(wl)
        try:
            state = str(actor.get_state())
        except Exception:
            state = "?"
        stops = []
        try:
            for wp in actor.get_stop_waypoints():
                stops.append({"world": v3(wp.transform.location), "road": int(wp.road_id),
                              "lane": int(wp.lane_id),
                              "dist": float(np.linalg.norm(np.array(v3(wp.transform.location)) - cam))})
        except Exception:
            pass
        lights.append({"id": actor.id, "bulb": wl, "dist": d, "state": state,
                       "pixel": p, "n_boxes": len(boxes), "extent": v3(best[2]), "stops": stops,
                       "yaw": float(atf.rotation.yaw), "loc": v3(atf.location)})
    lights.sort(key=lambda x: x["dist"])
    for L in lights:
        p = L["pixel"]
        pxs = ("(%5.0f,%5.0f)" % (p["u"], p["v"])) if p else "off-axis"
        inf = "YES" if (p and p["in_frame"]) else "no "
        print("    id=%-3d state=%-6s dist=%6.1fm  bulb=(%8.2f,%8.2f,%5.2f)  px=%s %s  boxes=%d ext=(%.2f,%.2f,%.2f)"
              % (L["id"], L["state"], L["dist"], L["bulb"][0], L["bulb"][1], L["bulb"][2], pxs, inf,
                 L["n_boxes"], L["extent"][0], L["extent"][1], L["extent"][2]))
        for s in L["stops"]:
            print("          stop waypoint (%.2f,%.2f) road=%d lane=%d  dist=%.1f"
                  % (s["world"][0], s["world"][1], s["road"], s["lane"], s["dist"]))

    # ---------- 3. apparent size of the nearest signal head
    print("\n[3] APPARENT SIZE on screen (fov=90, 1280x720) if a camera sat at the spectator")
    for L in lights[:6]:
        st = L["stops"][0] if L["stops"] else None
        if not st:
            continue
        # signal head sits above the stop line, ~1m offset toward the junction + 4.5m up
        pt = L["bulb"]
        p = pr.project(pt)
        if not p or not p["in_frame"]:
            continue
        # physical extent of the smallest box -> pixels
        ext = L["extent"]
        w_m = max(ext[0], ext[1]) * 2.0
        h_m = ext[2] * 2.0
        depth = p["depth"]
        px_w = pr.f * w_m / depth
        px_h = pr.f * h_m / depth
        print("    light id=%-3d depth=%6.1fm  physical %.2fx%.2f m -> on screen %.1f x %.1f px"
              % (L["id"], depth, w_m, h_m, px_w, px_h))

    with open(os.path.join(OUTDIR, "junction_map.json"), "w", encoding="utf-8") as f:
        json.dump({"cam": v3(tf.location),
                   "junction_pts": pts, "lights": lights}, f, ensure_ascii=False, indent=2)
    print("\nwrote", os.path.join(OUTDIR, "junction_map.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
