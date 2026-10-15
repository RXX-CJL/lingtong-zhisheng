"""Authoritative light <-> lane mapping by walking backwards from each light's
stop waypoints, plus the real geometry of each signal head (mast arm, lamp boxes,
world positions) near junction 23.

Writes E:\\output\\_camera_check\\lights_map.json
"""
import json
import math
import os
import sys

import numpy as np
import carla

sys.path.insert(0, r"E:\output\_scripts")
from _spec_check import Proj, v3  # noqa: E402

OUT = r"E:\output\_camera_check\lights_map.json"
JX, JY = -67.0, -68.7


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(20.0)
    world = client.get_world()
    m = world.get_map()
    tf = world.get_spectator().get_transform()
    pr = Proj(tf, 1280, 720, 90.0)
    cam = np.array(v3(tf.location))

    print("=" * 96)
    print("TRAFFIC LIGHTS near junction 23 (%.1f, %.1f) -- who controls which lane" % (JX, JY))
    print("=" * 96)

    out = []
    for actor in world.get_actors().filter("traffic.traffic_light*"):
        atf = actor.get_transform()
        loc = np.array(v3(atf.location))
        if np.linalg.norm(loc[:2] - np.array([JX, JY])) > 90:
            continue
        try:
            state = str(actor.get_state())
        except Exception:
            state = "?"
        bb = actor.bounding_box
        print("\nLIGHT id=%d  actor_loc=(%.2f,%.2f,%.2f) yaw=%.1f  state=%s"
              % (actor.id, loc[0], loc[1], loc[2], atf.rotation.yaw, state))
        print("   bbox extent=(%.2f,%.2f,%.2f) centre=(%.2f,%.2f,%.2f)"
              % (bb.extent.x, bb.extent.y, bb.extent.z, bb.location.x, bb.location.y, bb.location.z))
        try:
            el = actor.get_elapsed_time()
            print("   elapsed_time=%.2f  (state change timer)" % el)
        except Exception:
            pass

        # lamp boxes: small ones = lamps, big one = housing/arm
        boxes = actor.get_light_boxes()
        lamps = []
        for i, b in enumerate(boxes):
            wl = atf.location + atf.transform(b.location)
            vol = b.extent.x * b.extent.y * b.extent.z
            p = pr.project(v3(wl))
            lamps.append({"i": i, "world": v3(wl), "extent": v3(b.extent), "vol": vol,
                          "pixel": ([round(p["u"], 1), round(p["v"], 1)] if p else None),
                          "in_frame": bool(p and p["in_frame"])})
        lamps.sort(key=lambda d: d["vol"])
        print("   light boxes (%d), smallest first:" % len(lamps))
        for L in lamps[:8]:
            print("     #%d ext=(%.2f,%.2f,%.2f) world=(%8.2f,%8.2f,%5.2f) px=%s %s"
                  % (L["i"], L["extent"][0], L["extent"][1], L["extent"][2],
                     L["world"][0], L["world"][1], L["world"][2],
                     ("(%5.0f,%5.0f)" % tuple(L["pixel"])) if L["pixel"] else "off",
                     "IN" if L["in_frame"] else "out"))

        # controlled lanes: walk back from stop waypoints
        lanes = []
        try:
            wps = actor.get_stop_waypoints()
        except Exception:
            wps = []
        for wp in wps:
            chain = []
            cur = wp
            for _ in range(12):
                wl = cur.transform.location
                chain.append([round(wl.x, 1), round(wl.y, 1), int(cur.road_id), int(cur.lane_id)])
                nxt = cur.previous(4.0)
                if not nxt:
                    break
                cur = nxt[0]
            lanes.append({"stop": [round(wp.transform.location.x, 1), round(wp.transform.location.y, 1)],
                          "road": int(wp.road_id), "lane": int(wp.lane_id),
                          "approach_chain": chain})
            print("   controls stop=(%.1f,%.1f) road=%d lane=%d" %
                  (wp.transform.location.x, wp.transform.location.y, wp.road_id, wp.lane_id))
            print("     approach runs back through: %s" % chain[:6])
            # heading of the approach = direction from last chain point to stop
            if len(chain) >= 2:
                dx = chain[0][0] - chain[-1][0]
                dy = chain[0][1] - chain[-1][1]
                print("     approach heading = (%.2f, %.2f)  yaw=%.1f deg"
                      % (dx, dy, math.degrees(math.atan2(dy, dx))))

        # apparent geometry from the spectator
        p_actor = pr.project(v3(atf.location) + np.array([0, 0, 6.0]))
        print("   from spectator: actor x=%.1f  y=%.1f  dist=%.1f m  apparent housing width=%.1f px"
              % (loc[0], loc[1], np.linalg.norm(loc - cam),
                 (pr.f / np.linalg.norm(loc - cam)) * 0.6))
        out.append({"id": actor.id, "state": state, "actor_loc": v3(atf.location),
                    "yaw": float(atf.rotation.yaw), "extent": v3(bb.extent), "lamps": lamps,
                    "lanes": lanes})

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("\nwrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
