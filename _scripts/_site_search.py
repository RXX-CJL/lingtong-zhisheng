"""Map-wide search for a junction/approach where ONE camera can satisfy:
  * the controlling signal head is >= 25 px wide on screen (YOLO-usable)
  * its stop line is visible
  * the crosswalk band just past the stop line is visible
  * the junction centre is visible

Pure geometry using the VERIFIED projection formula; no rendering.
Writes E:\\output\\_camera_check\\site_search.json and prints the best sites.
"""
import json
import math
import os
import sys

import numpy as np
import carla

sys.path.insert(0, r"E:\output\_scripts")
from _spec_check import rot_matrix  # noqa: E402

W, H, FOV = 1280, 720, 90.0
OUT = r"E:\output\_camera_check\site_search.json"


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

    def in_frame(self, p, m=4.0):
        r = self.project(p)
        return r if (r and m <= r[0] < self.w - m and m <= r[1] < self.h - m) else None


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(30.0)
    world = client.get_world()
    m = world.get_map()

    # ---- crosswalk bands: cluster map crosswalk vertices onto a 5 m grid
    cells = {}
    for p in m.get_crosswalks():
        cells.setdefault((round(p.x / 5.0), round(p.y / 5.0)), []).append((p.x, p.y))
    bands = []
    for c, pts in cells.items():
        xs = [q[0] for q in pts]
        ys = [q[1] for q in pts]
        bands.append({"c": ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2),
                      "w": max(xs) - min(xs), "h": max(ys) - min(ys), "n": len(pts)})

    lights = []
    for a in world.get_actors().filter("traffic.traffic_light*"):
        boxes = a.get_light_boxes()
        atf = a.get_transform()
        heads = []
        for b in boxes:
            wl = np.array([b.location.x, b.location.y, b.location.z])   # box locs are world coords
            if max(b.extent.x, b.extent.y) > 2.0:
                continue                       # skip the mast arm box
            heads.append((wl, np.array([b.extent.x, b.extent.y, b.extent.z])))
        stops = []
        try:
            for wp in a.get_stop_waypoints():
                wl = wp.transform.location
                chain = []
                cur = wp
                for _ in range(9):
                    chain.append(np.array([cur.transform.location.x, cur.transform.location.y]))
                    nx = cur.previous(4.0)
                    if not nx:
                        break
                    cur = nx[0]
                head = chain[0] - chain[-1]           # approach direction (unit-ish)
                n = np.linalg.norm(head)
                if n < 1e-6:
                    continue
                stops.append({"stop": np.array([wl.x, wl.y]), "dir": head / n,
                              "road": int(wp.road_id), "lane": int(wp.lane_id),
                              "back": chain[-1]})
        except Exception:
            pass
        if stops and heads:
            lights.append({"id": a.id, "heads": heads, "stops": stops})

    print("map=%s  crosswalk cells=%d  lights with heads=%d" % (m.name, len(bands), len(lights)))

    results = []
    for L in lights:
        for st in L["stops"]:
            stp, d = st["stop"], st["dir"]
            # signal head that serves this approach: the one nearest the stop point
            best = None
            for wl, ext in L["heads"]:
                dist = np.linalg.norm(wl[:2] - stp)
                if best is None or dist < best[0]:
                    best = (dist, wl, ext)
            if best is None:
                continue
            head_dist, sig, ext = best
            if head_dist > 60:
                continue
            # crosswalk band just past the stop line, within 25 m
            cw = None
            for b in bands:
                dv = np.array(b["c"]) - stp
                along = float(dv.dot(d))
                perp = float(np.linalg.norm(dv - along * d))
                if 0.5 < along < 22.0 and perp < 14.0:
                    if cw is None or along < cw[0]:
                        cw = (along, np.array([b["c"][0], b["c"][1], 0.0]), b["w"], b["h"])
            if cw is None:
                continue
            junc = stp + d * 14.0            # approximate junction centre 14 m past the stop line

            for back in (10.0, 14.0, 18.0, 22.0, 26.0, 30.0, 36.0, 42.0, 50.0):
                cam_xy = stp - d * back
                for z in (6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0):
                    for pitch in range(-8, -33, -1):
                        yaw = math.degrees(math.atan2(stp[1] - cam_xy[1], stp[0] - cam_xy[0]))
                        cam = Cam([cam_xy[0], cam_xy[1], z], pitch, yaw)
                        ps = cam.in_frame(np.array([stp[0], stp[1], 0.15]))
                        pc = cam.in_frame(cw[1])
                        pj = cam.in_frame(np.array([junc[0], junc[1], 0.0]))
                        ph = cam.in_frame(sig)
                        if not (ps and pc and pj and ph):
                            continue
                        sig_w = 0.6 * cam.f / ph[2]          # housing ~0.6 m wide
                        if sig_w < 25.0:
                            continue
                        vs = sorted([ps[1], pc[1], pj[1]])
                        spread = vs[-1] - vs[0]
                        results.append({
                            "light": L["id"], "road": st["road"], "lane": st["lane"],
                            "cam": [round(cam_xy[0], 1), round(cam_xy[1], 1), z],
                            "pitch": pitch, "yaw": round(yaw, 1), "back": back,
                            "sig_w": round(sig_w, 1), "spread": round(spread, 1),
                            "px": {"STOP": [round(ps[0], 1), round(ps[1], 1)],
                                   "CW": [round(pc[0], 1), round(pc[1], 1)],
                                   "JUNC": [round(pj[0], 1), round(pj[1], 1)],
                                   "SIG": [round(ph[0], 1), round(ph[1], 1)]},
                            "stop": [round(stp[0], 1), round(stp[1], 1)],
                            "sig_world": [round(float(sig[0]), 1), round(float(sig[1]), 1), round(float(sig[2]), 2)],
                            "cw_world": [round(float(cw[1][0]), 1), round(float(cw[1][1]), 1)],
                            "score": round(sig_w * 2 + spread * 0.6, 1)})

    results.sort(key=lambda r: -r["score"])
    print("\n%d viable placements across the whole map. Best 15:" % len(results))
    print("  %-6s %-5s %-4s %-22s %-6s %-5s %-8s %-7s %-8s %s"
          % ("light", "road", "lane", "camera(x,y,z)", "pitch", "yaw", "sig_px", "spread", "back", "score"))
    for r in results[:15]:
        print("  %-6d %-5d %-4d (%8.1f,%8.1f,%-4.1f) %-6d %-5.1f %-8.1f %-7.1f %-8.1f %s"
              % (r["light"], r["road"], r["lane"], r["cam"][0], r["cam"][1], r["cam"][2],
                 r["pitch"], r["yaw"], r["sig_w"], r["spread"], r["back"], r["score"]))

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(results[:400], f, ensure_ascii=False, indent=2)
    print("\nwrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
