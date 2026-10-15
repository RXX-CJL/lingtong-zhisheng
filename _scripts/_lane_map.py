"""Local lane structure + authoritative light<->lane mapping at junction 23
(around (-67.0, -68.7)), which is what the spectator is aimed at.
"""
import json
import math
import os
import sys

import numpy as np
import carla

sys.path.insert(0, r"E:\output\_scripts")
from _spec_check import Proj, v3  # noqa: E402

OUT = r"E:\output\_camera_check\lane_map.json"


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(20.0)
    world = client.get_world()
    m = world.get_map()
    tf = world.get_spectator().get_transform()
    pr = Proj(tf, 1280, 720, 90.0)
    cam = np.array(v3(tf.location))

    JX, JY = -67.0, -68.7      # user-selected junction 23

    # ---------- 1. lane topology along the east-west road through the junction
    print("=" * 92)
    print("JUNCTION 23 at (%.1f, %.1f)   camera at (%.2f, %.2f, %.2f)"
          % (JX, JY, cam[0], cam[1], cam[2]))
    print("=" * 92)

    print("\n[1] WAYPOINTS along y = %.1f (the road the camera looks down)" % cam[1])
    print("     %-9s %-9s %-7s %-7s %-6s %s" % ("x", "y", "road", "lane", "junc", "pixel"))
    seen = set()
    for x in range(int(cam[0]) + 6, int(cam[0]) - 80, -3):
        for dy in (0.0, -3.5, 3.5, -7.0, 7.0):
            loc = carla.Location(x=float(x), y=cam[1] + dy, z=2.0)
            wp = m.get_waypoint(loc, project_to_road=True, lane_type=carla.LaneType.Driving)
            if wp is None:
                continue
            key = (wp.road_id, wp.lane_id, round(wp.transform.location.x / 3.0),
                   round(wp.transform.location.y / 3.0))
            if key in seen:
                continue
            seen.add(key)
            wl = wp.transform.location
            p = pr.project([wl.x, wl.y, wl.z])
            px = ("(%5.0f,%4.0f)" % (p["u"], p["v"])) if p else "off"
            print("     %-9.1f %-9.1f %-7d %-7d %-6s %s"
                  % (wl.x, wl.y, wp.road_id, wp.lane_id, "YES" if wp.is_junction else "-", px))

    # ---------- 2. traffic lights reachable FROM those waypoints
    print("\n[2] AUTHORITATIVE mapping: get_traffic_lights_from_waypoint()")
    rows = []
    checked = set()
    for x in range(int(cam[0]) + 40, int(cam[0]) - 140, -4):
        for dy in np.arange(-10.5, 10.6, 3.5):
            loc = carla.Location(x=float(x), y=cam[1] + float(dy), z=2.0)
            wp = m.get_waypoint(loc, project_to_road=True, lane_type=carla.LaneType.Driving)
            if wp is None:
                continue
            k = (wp.road_id, wp.lane_id)
            if k in checked:
                continue
            checked.add(k)
            try:
                tls = m.get_traffic_lights_from_waypoint(wp, distance=120.0)
            except TypeError:
                tls = m.get_traffic_lights_from_waypoint(wp)
            except Exception as e:
                tls = []
                print("     err", e)
            if not tls and not wp.is_junction:
                continue
            o = wp.get_left_lane()
            info = "road=%-4d lane=%-3d x=%7.1f y=%7.1f junc=%-3s n_lights=%d" % (
                wp.road_id, wp.lane_id, wp.transform.location.x, wp.transform.location.y,
                "YES" if wp.is_junction else "no", len(tls))
            print("     " + info)
            for t in tls:
                try:
                    st = str(t.get_state())
                except Exception:
                    st = "?"
                boxes = t.get_light_boxes()
                atf = t.get_transform()
                best = None
                for b in boxes:
                    wl = atf.location + atf.transform(b.location)
                    vol = b.extent.x * b.extent.y * b.extent.z
                    if best is None or vol < best[0]:
                        best = (vol, v3(wl))
                bulb = best[1] if best else None
                p = pr.project(bulb) if bulb else None
                print("        light id=%-3d state=%-6s bulb=(%8.2f,%8.2f,%5.2f) px=%s"
                      % (t.id, st, bulb[0], bulb[1], bulb[2],
                         ("(%5.0f,%4.0f) %s" % (p["u"], p["v"], "IN" if p["in_frame"] else "out")) if p else "off"))
                rows.append({"wp": [wp.road_id, wp.lane_id, wp.transform.location.x, wp.transform.location.y],
                             "light": t.id, "state": st, "bulb": bulb})

    # ---------- 3. how far is the junction edge from the camera along the view axis
    print("\n[3] JUNCTION EDGE along the camera view axis")
    for d in range(0, 120, 1):
        probe = cam + np.array([-1.0, 0.0, 0.0]) * d
        wp = m.get_waypoint(carla.Location(x=float(probe[0]), y=float(probe[1]), z=2.0),
                            project_to_road=True, lane_type=carla.LaneType.Driving)
        if wp is not None and wp.is_junction:
            print("     first junction waypoint at %.0f m ahead: (%.1f, %.1f) road=%d lane=%d"
                  % (d, wp.transform.location.x, wp.transform.location.y, wp.road_id, wp.lane_id))
            break
    else:
        print("     no junction waypoint within 120 m along the view axis")

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"cam": v3(tf.location), "mapping": rows}, f, ensure_ascii=False, indent=2)
    print("\nwrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
