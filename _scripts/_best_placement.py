"""Pick the best camera placement for a red-light demo, using the MEASURED signal
head sizes, for every approach whose controlling light is within 120 m.

Constraint set (user's hard criteria):
  * signal head (real lamp box) visible, at least 20 px in its largest dimension
  * stop line visible
  * crosswalk band just past the stop line visible
  * junction centre visible
Also reports the on-screen size of the head so colour-judging feasibility is explicit.
"""
import json
import math
import os
import sys

import numpy as np
import carla

W, H, FOV = 1280, 720, 90.0
OUT = r"E:\output\_camera_check\best_placements.json"

# CARLA pitch is negative when looking down; with this Ry the forward vector is
# (cos p cos y, cos p sin y, -sin p) -- verified against rendered markers.
def _Ry(p):
    c, s = math.cos(p), math.sin(p)
    return np.array([[c, 0, -s], [0, 1, 0], [s, 0, c]])


def rot_matrix(pitch_deg, yaw_deg, roll_deg=0.0):
    p, y, r = map(math.radians, (pitch_deg, yaw_deg, roll_deg))
    cz, sz = math.cos(y), math.sin(y)
    cx, sx = math.cos(r), math.sin(r)
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    return Rz @ _Ry(p) @ Rx


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

    # crosswalk bands (5 m grid)
    cells = {}
    for p in m.get_crosswalks():
        cells.setdefault((round(p.x / 5.0), round(p.y / 5.0)), []).append((p.x, p.y))
    bands = [((min(x for x, y in v) + max(x for x, y in v)) / 2,
              (min(y for x, y in v) + max(y for x, y in v)) / 2)
             for v in cells.values()]

    results = []
    for a in world.get_actors().filter("traffic.traffic_light*"):
        boxes = a.get_light_boxes()
        heads = []
        for b in boxes:
            if max(b.extent.x, b.extent.y) > 2.0:
                continue
            ext = np.array([b.extent.x, b.extent.y, b.extent.z])
            heads.append((np.array([b.location.x, b.location.y, b.location.z]), ext))
        if not heads:
            continue
        heads.sort(key=lambda t: -t[1][2])          # tallest = vehicle head
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
            if len(chain) < 2:
                continue
            d = chain[0] - chain[-1]
            d = d / max(np.linalg.norm(d), 1e-9)
            # signal head serving this approach = nearest head to the stop point
            head, ext = min(heads, key=lambda t: float(np.linalg.norm(t[0][:2] - stp)))
            # nearest crosswalk band beyond the stop line
            cw = None
            for c in bands:
                dv = np.array(c) - stp
                along = float(dv.dot(d))
                perp = float(np.linalg.norm(dv - along * d))
                if 0.5 < along < 25.0 and perp < 15.0 and (cw is None or along < cw[0]):
                    cw = (along, c)
            if cw is None:
                continue
            for back in np.arange(8.0, 61.0, 2.0):
                camxy = stp - d * back
                for z in (6.0, 7.0, 8.0, 9.0, 10.0):
                    for pitch in np.arange(-5.0, -34.0, -0.5):
                        yaw = math.degrees(math.atan2(stp[1] - camxy[1], stp[0] - camxy[0]))
                        cam = Cam([camxy[0], camxy[1], z], pitch, yaw)
                        rs = cam.project(np.array([stp[0], stp[1], 0.2]))
                        rc = cam.project(np.array([cw[1][0], cw[1][1], 0.0]))
                        rh = cam.project(head)
                        if rs is None or rc is None or rh is None:
                            continue
                        margin = 8.0
                        if not all(margin <= r[0] < W - margin and margin <= r[1] < H - margin
                                   for r in (rs, rc, rh)):
                            continue
                        ppm = cam.f / rh[2]
                        w_px = 2 * ext[0] * ppm
                        h_px = 2 * ext[2] * ppm
                        if max(w_px, h_px) < 20.0:
                            continue
                        # junction centre: 15 m past the stop line along the approach
                        jc = stp + d * 15.0
                        rj = cam.project(np.array([jc[0], jc[1], 0.0]))
                        if rj is None or not (margin <= rj[0] < W - margin and margin <= rj[1] < H - margin):
                            continue
                        ground_span = max(rs[1], rc[1], rj[1]) - min(rs[1], rc[1], rj[1])
                        results.append({
                            "light": a.id, "road": int(wp.road_id), "lane": int(wp.lane_id),
                            "cam": [round(float(camxy[0]), 1), round(float(camxy[1]), 1), z],
                            "pitch": float(pitch), "yaw": round(yaw, 1), "back": float(back),
                            "head_px": [round(w_px, 1), round(h_px, 1)],
                            "head_depth": round(rh[2], 1),
                            "stop": [round(float(stp[0]), 1), round(float(stp[1]), 1)],
                            "cw": [round(float(cw[1][0]), 1), round(float(cw[1][1]), 1)],
                            "head_world": [round(float(x), 2) for x in head],
                            "px": {"STOP": [round(rs[0]), round(rs[1])],
                                   "CW": [round(rc[0]), round(rc[1])],
                                   "HEAD": [round(rh[0]), round(rh[1])],
                                   "JUNC": [round(rj[0]), round(rj[1])]},
                            "ground_span": round(float(ground_span), 1),
                            "score": round(max(w_px, h_px) * 1.0 + ground_span * 0.4, 1),
                        })
    results.sort(key=lambda r: -r["score"])
    print("%d viable placements.\n" % len(results))
    print("  %-5s %-4s %-7s %-22s %-7s %-6s %-5s %-14s %-9s %s"
          % ("light", "road", "lane", "camera", "pitch", "yaw", "back", "head px", "gnd span", "targets px"))
    for r in results[:14]:
        print("  %-5d %-4d %-7d (%7.1f,%7.1f,%-4.1f) %-7.1f %-6.1f %-5.0f %-14s %-9.0f S%s C%s H%s J%s"
              % (r["light"], r["road"], r["lane"], r["cam"][0], r["cam"][1], r["cam"][2],
                 r["pitch"], r["yaw"], r["back"], "%sx%s" % tuple(r["head_px"]), r["ground_span"],
                 r["px"]["STOP"], r["px"]["CW"], r["px"]["HEAD"], r["px"]["JUNC"]))

    # the two approaches that matter at the junction the user picked
    print("\nBEST per light near the user's junction (light 9 westbound / light 10 road22 / light 17 road6):")
    for lid in (9, 10, 17):
        sub = [r for r in results if r["light"] == lid]
        if sub:
            r = sub[0]
            print("   light %-3d -> cam=(%.1f,%.1f,%.1f) pitch=%.1f yaw=%.1f back=%.0f m  head %sx%s px at %.0f m"
                  % (lid, r["cam"][0], r["cam"][1], r["cam"][2], r["pitch"], r["yaw"], r["back"],
                     r["head_px"][0], r["head_px"][1], r["head_depth"]))
        else:
            print("   light %-3d -> NO viable placement" % lid)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(results[:200], f, ensure_ascii=False, indent=2)
    print("\nwrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
