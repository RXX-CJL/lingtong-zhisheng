"""Diagnose the site search: count how many (approach, camera) pairs pass each
constraint stage, and show the closest misses with raw numbers.
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
    client.set_timeout(30.0)
    world = client.get_world()
    m = world.get_map()

    cells = {}
    for p in m.get_crosswalks():
        cells.setdefault((round(p.x / 5.0), round(p.y / 5.0)), []).append((p.x, p.y))
    bands = []
    for c, pts in cells.items():
        xs = [q[0] for q in pts]
        ys = [q[1] for q in pts]
        bands.append(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, max(xs) - min(xs), max(ys) - min(ys), len(pts)))

    print("crosswalk grid cells:", len(bands))
    print("\nsample cells (cx, cy, w, h, npts):")
    for b in sorted(bands, key=lambda t: -t[4])[:15]:
        print("   (%8.1f,%8.1f)  w=%5.1f h=%5.1f  n=%d" % b)

    # per light: nearest lamp head to each stop waypoint + nearest crosswalk band
    print("\n%-6s %-5s %-5s %-26s %-9s %-26s %-9s %s"
          % ("light", "road", "lane", "stop", "head_dist", "crosswalk band", "cw_along", "head_world"))
    n_head_bad = n_cw_bad = n_ok = 0
    for a in world.get_actors().filter("traffic.traffic_light*"):
        boxes = a.get_light_boxes()
        heads = []
        for b in boxes:
            if max(b.extent.x, b.extent.y) > 2.0:
                continue
            heads.append((np.array([b.location.x, b.location.y, b.location.z]),
                          np.array([b.extent.x, b.extent.y, b.extent.z])))
        try:
            stopwps = a.get_stop_waypoints()
        except Exception:
            stopwps = []
        for wp in stopwps:
            stp = np.array([wp.transform.location.x, wp.transform.location.y])
            chain = []
            cur = wp
            for _ in range(9):
                chain.append(np.array([cur.transform.location.x, cur.transform.location.y]))
                nx = cur.previous(4.0)
                if not nx:
                    break
                cur = nx[0]
            d = chain[0] - chain[-1]
            nn = np.linalg.norm(d)
            if nn < 1e-6:
                continue
            d = d / nn
            best = None
            for wl, ext in heads:
                dd = float(np.linalg.norm(wl[:2] - stp))
                if best is None or dd < best[0]:
                    best = (dd, wl, ext)
            if best is None:
                n_head_bad += 1
                continue
            hd, sig, ext = best
            cw = None
            for b in bands:
                dv = np.array([b[0], b[1]]) - stp
                along = float(dv.dot(d))
                perp = float(np.linalg.norm(dv - along * d))
                if 0.5 < along < 22.0 and perp < 14.0:
                    if cw is None or along < cw[0]:
                        cw = (along, b)
            if cw is None:
                n_cw_bad += 1
                print("%-6d %-5d %-5d (%8.1f,%8.1f) %-9.1f %-26s %-9s head=(%.1f,%.1f,%.2f) ext=(%.2f,%.2f,%.2f)"
                      % (a.id, wp.road_id, wp.lane_id, stp[0], stp[1], hd, "NONE within 22m", "-",
                         sig[0], sig[1], sig[2], ext[0], ext[1], ext[2]))
                continue
            n_ok += 1
            print("%-6d %-5d %-5d (%8.1f,%8.1f) %-9.1f (%8.1f,%8.1f) w=%4.1f h=%4.1f %-9.1f head=(%.1f,%.1f,%.2f) ext=(%.2f,%.2f,%.2f)"
                  % (a.id, wp.road_id, wp.lane_id, stp[0], stp[1], hd,
                     cw[1][0], cw[1][1], cw[1][2], cw[1][3], cw[0],
                     sig[0], sig[1], sig[2], ext[0], ext[1], ext[2]))

    print("\nsummary: approaches with cw+head=%d, no-head=%d, no-cw=%d" % (n_ok, n_head_bad, n_cw_bad))

    # ---- vertical-angle feasibility for one concrete case
    print("\nVERTICAL FEASIBILITY for light 9 (westbound, y=-63.15), camera at y=-63.15:")
    stp = np.array([-25.61, -64.76])
    sig = np.array([-166.28, -100.99, 4.56])
    cw = np.array([-31.21, -72.07, 0.0])
    for back in (12.0, 18.0, 25.0, 35.0, 50.0):
        camxy = stp - np.array([-1.0, 0.0]) * back
        for z in (8.0,):
            yaw = math.degrees(math.atan2(stp[1] - camxy[1], stp[0] - camxy[0]))
            # required pitch range to fit ALL points for the best pitch
            bestfit = None
            for pitch10 in range(-350, -30):
                pitch = pitch10 / 10.0
                cam = Cam([camxy[0], camxy[1], z], pitch, yaw)
                rs = [cam.project(p) for p in (np.array([stp[0], stp[1], 0.15]), cw, sig)]
                if any(r is None for r in rs):
                    continue
                vs = [r[1] for r in rs]
                us = [r[0] for r in rs]
                if all(4 <= v < H - 4 for v in vs) and all(4 <= u < W - 4 for u in us):
                    span = max(vs) - min(vs)
                    if bestfit is None or span < bestfit[0]:
                        bestfit = (span, pitch, [round(v, 0) for v in vs], [round(u, 0) for u in us])
            print("   back=%4.1f m  ->  %s" % (back, ("pitch=%.1f v=%s u=%s span=%.0f" % (bestfit[1], bestfit[2], bestfit[3], bestfit[0])) if bestfit else "IMPOSSIBLE to fit all three"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
