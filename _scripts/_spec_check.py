"""Projection analysis for the user-tuned CARLA spectator.

Read-only: opens CARLA, reads the spectator transform, projects the scene
targets (traffic-light bulbs / crosswalks / stop line / junction centre) through
the VERIFIED projection formula, and writes JSON + prints a report.

Run in the CARLA-side interpreter:
  C:\\Users\\ROG\\AppData\\Local\\Programs\\Python\\Python312\\python.exe
"""
import json
import math
import sys

import numpy as np
import carla

W, H = 1280, 720          # spectator default image size
FOV = 90.0                # spectator default fov (attributes.get('fov') returns None)
OUT = r"E:\output\_scripts\_spec_check.json"

# ---------------------------------------------------------------- projection
def rot_matrix(pitch_deg, yaw_deg, roll_deg):
    """CARLA left-handed: R = Rz(yaw) @ Ry(pitch) @ Rx(roll).

    NOTE (fixed 2026-10-04): CARLA pitch is NEGATIVE when looking DOWN.
    The forward direction must be (cos p cos y, cos p sin y, -sin p), which
    requires -sin(p) in Ry. The handoff version used +sin(p), giving a forward
    vector that pointed UP for a downward pitch (z=+0.398 at pitch=-23.4 deg).
    Proof it was wrong: calibrated ground markers at 40/60 m matched an image
    row that the buggy matrix misplaced by ~600 px.
    """
    p, y, r = map(math.radians, (pitch_deg, yaw_deg, roll_deg))
    cz, sz = math.cos(y), math.sin(y)
    cp, sp = math.cos(p), math.sin(p)
    cx, sx = math.cos(r), math.sin(r)
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    Ry = np.array([[cp, 0, -sp], [0, 1, 0], [sp, 0, cp]])
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    return Rz @ Ry @ Rx


class Proj:
    def __init__(self, tf, w=W, h=H, fov=FOV):
        self.cam = np.array([tf.location.x, tf.location.y, tf.location.z])
        self.fwd = np.array([
            math.cos(math.radians(tf.rotation.yaw)) * math.cos(math.radians(tf.rotation.pitch)),
            math.sin(math.radians(tf.rotation.yaw)) * math.cos(math.radians(tf.rotation.pitch)),
            math.sin(math.radians(tf.rotation.pitch)),
        ])
        self.R = rot_matrix(tf.rotation.pitch, tf.rotation.yaw, tf.rotation.roll)
        self.w, self.h = w, h
        self.f = w / (2 * math.tan(math.radians(fov) / 2))

    def project(self, p):
        vc = self.R.T @ (np.asarray(p, dtype=float) - self.cam)
        if vc[0] <= 1e-6:
            return None
        u = self.w / 2 + self.f * (vc[1] / vc[0])
        v = self.h / 2 - self.f * (vc[2] / vc[0])
        return {"u": float(u), "v": float(v), "depth": float(vc[0]),
                "in_frame": bool(0 <= u < self.w and 0 <= v < self.h)}

    def angle_to(self, p):
        d = np.asarray(p, dtype=float) - self.cam
        n = np.linalg.norm(d)
        if n < 1e-9:
            return 0.0
        return float(math.degrees(math.acos(max(-1.0, min(1.0, float(d.dot(self.fwd)) / n)))))


def v3(v):
    return [float(v.x), float(v.y), float(v.z)]


# ---------------------------------------------------------------- geometry
def crosswalk_polys(points, tol=0.35):
    """Group closed loops of crosswalk vertices into per-crosswalk polygons."""
    remaining = list(points)
    polys = []
    while remaining:
        seed = remaining.pop(0)
        chain = [seed]
        changed = True
        while changed:
            changed = False
            for i, c in enumerate(remaining):
                if abs(c.x - chain[-1].x) < tol and abs(c.y - chain[-1].y) < tol \
                        and abs(c.z - chain[-1].z) < tol:
                    chain.append(remaining.pop(i))
                    changed = True
                    break
        polys.append(chain)
    return polys


def poly_center(poly):
    xs = [p.x for p in poly]
    ys = [p.y for p in poly]
    zs = [p.z for p in poly]
    return [sum(xs) / len(xs), sum(ys) / len(ys), sum(zs) / len(zs)]


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(20.0)
    world = client.get_world()
    m = world.get_map()
    spec = world.get_spectator()
    tf = spec.get_transform()
    pr = Proj(tf)

    report = {
        "map": m.name,
        "spectator": {
            "location": v3(tf.location),
            "rotation": [float(tf.rotation.pitch), float(tf.rotation.yaw), float(tf.rotation.roll)],
        },
        "image": {"w": W, "h": H, "fov": FOV, "f_px": pr.f},
        "forward": [float(x) for x in pr.fwd],
    }

    print("=" * 78)
    print("SPECTATOR  loc=(%.2f, %.2f, %.2f)  pitch=%.2f  yaw=%.2f  roll=%.2f"
          % (tf.location.x, tf.location.y, tf.location.z,
             tf.rotation.pitch, tf.rotation.yaw, tf.rotation.roll))
    print("image %dx%d  fov=%.1f  f=%.1f px" % (W, H, FOV, pr.f))
    print("=" * 78)

    # ---------------- 1. traffic lights: real bulb world positions
    lights = []
    for actor in world.get_actors().filter("traffic.traffic_light*"):
        try:
            boxes = actor.get_light_boxes()
        except Exception:
            boxes = []
        atf = actor.get_transform()
        best = None
        for b in boxes:
            world_loc = atf.location + atf.transform(b.location)
            ext = b.extent
            vol = ext.x * ext.y * ext.z
            if best is None or vol < best[0]:
                best = (vol, world_loc, ext)
        if best is None:
            continue
        # stop line / trigger of this light, if available
        stop = None
        try:
            for wp in actor.get_stop_waypoints():
                stop = v3(wp.transform.location)
                break
        except Exception:
            pass
        _, wl, ext = best
        p = pr.project(v3(wl))
        lights.append({
            "id": actor.id,
            "bulb_world": v3(wl),
            "extent": v3(ext),
            "n_boxes": len(boxes),
            "stop_waypoint": stop,
            "pixel": p,
            "angle_deg": pr.angle_to(v3(wl)),
            "distance": float(np.linalg.norm(np.array(v3(wl)) - pr.cam)),
        })
    lights.sort(key=lambda d: d["angle_deg"])
    in_frame_lights = [d for d in lights if d["pixel"] and d["pixel"]["in_frame"]]
    report["traffic_lights"] = lights
    report["traffic_lights_in_frame"] = len(in_frame_lights)

    print("\n[1] TRAFFIC LIGHTS  (total %d, in-frame %d)" % (len(lights), len(in_frame_lights)))
    print("    %-5s %-26s %-16s %6s %6s %8s" % ("id", "bulb world", "pixel(u,v)", "dist", "ang", "in?"))
    for d in lights[:12]:
        px = d["pixel"]
        pxs = ("(%6.0f,%5.0f)" % (px["u"], px["v"])) if px else "-- off-axis --"
        print("    %-5d (%-8.2f,%8.2f,%5.2f) %-16s %6.1f %6.1f %8s"
              % (d["id"], d["bulb_world"][0], d["bulb_world"][1], d["bulb_world"][2],
                 pxs, d["distance"], d["angle_deg"], "YES" if (px and px["in_frame"]) else "no"))

    # ---------------- 2. crosswalks
    try:
        cw_points = m.get_crosswalks()
    except Exception as e:
        cw_points = []
        print("    get_crosswalks failed:", e)
    polys = crosswalk_polys(cw_points)
    cws = []
    for poly in polys:
        c = poly_center(poly)
        p = pr.project(c)
        cws.append({
            "n_verts": len(poly),
            "center": c,
            "pixel": p,
            "angle_deg": pr.angle_to(c),
            "distance": float(np.linalg.norm(np.array(c) - pr.cam)),
            "bbox_world": {
                "x": [min(q.x for q in poly), max(q.x for q in poly)],
                "y": [min(q.y for q in poly), max(q.y for q in poly)],
            },
        })
    cws.sort(key=lambda d: d["angle_deg"])
    in_frame_cw = [d for d in cws if d["pixel"] and d["pixel"]["in_frame"]]
    report["crosswalks"] = cws
    report["crosswalks_in_frame"] = len(in_frame_cw)

    print("\n[2] CROSSWALKS  (total %d, in-frame %d)" % (len(cws), len(in_frame_cw)))
    for d in cws[:8]:
        px = d["pixel"]
        pxs = ("(%6.0f,%5.0f)" % (px["u"], px["v"])) if px else "-- off-axis --"
        print("    verts=%-3d center=(%8.2f,%8.2f,%5.2f) %-16s %6.1f %6.1f %8s"
              % (d["n_verts"], d["center"][0], d["center"][1], d["center"][2],
                 pxs, d["distance"], d["angle_deg"], "YES" if (px and px["in_frame"]) else "no"))

    # ---------------- 3. junction the spectator is aiming at
    junction = None
    for dist in range(0, 240, 2):
        probe = np.array(v3(tf.location)) + pr.fwd * dist
        wp = m.get_waypoint(carla.Location(x=float(probe[0]), y=float(probe[1]), z=float(probe[2])),
                            project_to_road=True, lane_type=carla.LaneType.Driving)
        if wp is not None and wp.is_junction:
            junction = wp
            break
    jinfo = None
    if junction is not None:
        jloc = junction.transform.location
        p = pr.project(v3(jloc))
        jinfo = {
            "probe_distance": dist,
            "location": v3(jloc),
            "pixel": p,
            "angle_deg": pr.angle_to(v3(jloc)),
            "distance": float(np.linalg.norm(np.array(v3(jloc)) - pr.cam)),
            "road_id": int(junction.road_id),
            "lane_id": int(junction.lane_id),
        }
        report["junction"] = jinfo
        px = p
        print("\n[3] JUNCTION (probe %dm along view axis)" % dist)
        print("    location=(%.2f, %.2f, %.2f)  pixel=(%s)  dist=%.1f  angle=%.1f"
              % (jloc.x, jloc.y, jloc.z,
                 ("%.0f,%.0f" % (px["u"], px["v"])) if px else "off-axis",
                 jinfo["distance"], jinfo["angle_deg"]))
        print("    lane road_id=%d lane_id=%d" % (jinfo["road_id"], jinfo["lane_id"]))
    else:
        print("\n[3] JUNCTION -- none found within 240m along the view axis")

    # ---------------- 4. stop lines of every traffic light within 120m
    print("\n[4] STOP LINES (get_stop_waypoints) within 160m, in-frame first")
    stops = []
    for actor in world.get_actors().filter("traffic.traffic_light*"):
        try:
            wps = actor.get_stop_waypoints()
        except Exception:
            wps = []
        for wp in wps:
            wl = wp.transform.location
            d = float(np.linalg.norm(np.array(v3(wl)) - pr.cam))
            if d > 160:
                continue
            p = pr.project(v3(wl))
            stops.append({"light_id": actor.id, "world": v3(wl), "pixel": p,
                          "angle_deg": pr.angle_to(v3(wl)), "distance": d})
    stops.sort(key=lambda s: (0 if (s["pixel"] and s["pixel"]["in_frame"]) else 1, s["angle_deg"]))
    report["stop_lines"] = stops
    for s in stops[:10]:
        px = s["pixel"]
        pxs = ("(%6.0f,%5.0f)" % (px["u"], px["v"])) if px else "-- off-axis --"
        print("    light=%-4d world=(%8.2f,%8.2f,%5.2f) %-16s %6.1f %6.1f %8s"
              % (s["light_id"], s["world"][0], s["world"][1], s["world"][2], pxs,
                 s["distance"], s["angle_deg"], "YES" if (px and px["in_frame"]) else "no"))
    report["stop_lines_in_frame"] = len([s for s in stops if s["pixel"] and s["pixel"]["in_frame"]])

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("\nwrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
