"""Render the spectator view with ALL candidate reference features labelled,
so the projection can be visually cross-checked, and dump the feature table.

Writes:
  E:\\output\\_camera_check\\overlay_all.png
  E:\\output\\_scripts\\_features.json
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
os.makedirs(OUTDIR, exist_ok=True)
sys.path.insert(0, r"E:\output\_scripts")
from _spec_check import Proj, v3, crosswalk_polys  # noqa: E402


def convex_hull_center(pts):
    """Cheap centre = mean of the min/max box, robust for a 4-vertex loop."""
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return [(min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0, 0.0]


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(20.0)
    world = client.get_world()
    m = world.get_map()
    tf = world.get_spectator().get_transform()
    pr = Proj(tf, W, H, FOV)

    # ---- frame
    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(W))
    bp.set_attribute("image_size_y", str(H))
    bp.set_attribute("fov", str(FOV))
    bp.set_attribute("enable_postprocess_effects", "False")
    cam = world.spawn_actor(bp, tf)
    frames = []
    cam.listen(lambda img: frames.append(img))
    for _ in range(6):
        world.tick()
        time.sleep(0.05)
    time.sleep(0.6)
    cam.stop()
    cam.destroy()
    arr = np.frombuffer(frames[-1].raw_data, dtype=np.uint8).reshape(H, W, 4)[:, :, :3]

    feats = []

    # ---- crosswalk polygons (grouped, then box-centre)
    polys = crosswalk_polys(m.get_crosswalks())
    # merge polys that belong to the same crosswalk (centres within 4m) is overkill;
    # instead aggregate raw points into 4m grid clusters
    clusters = {}
    for p in m.get_crosswalks():
        key = (round(p.x / 6.0), round(p.y / 6.0))
        clusters.setdefault(key, []).append([p.x, p.y, p.z])
    # merge neighbouring keys of the same crosswalk
    keys = list(clusters)
    merged = []
    used = set()
    for k in keys:
        if k in used:
            continue
        grp = list(clusters[k])
        used.add(k)
        for k2 in keys:
            if k2 in used:
                continue
            if abs(k2[0] - k[0]) <= 1 and abs(k2[1] - k[1]) <= 1:
                grp += clusters[k2]
                used.add(k2)
        merged.append(grp)
    for i, grp in enumerate(merged):
        c = convex_hull_center(grp)
        p = pr.project(c)
        d = float(np.linalg.norm(np.array(c) - pr.cam))
        feats.append({"kind": "CW%d" % i, "world": c, "pixel": p, "dist": d,
                      "n_pts": len(grp),
                      "span": [max(q[0] for q in grp) - min(q[0] for q in grp),
                               max(q[1] for q in grp) - min(q[1] for q in grp)]})

    # ---- stop lines
    for actor in world.get_actors().filter("traffic.traffic_light*"):
        try:
            wps = actor.get_stop_waypoints()
        except Exception:
            wps = []
        for wp in wps:
            wl = v3(wp.transform.location)
            p = pr.project(wl)
            d = float(np.linalg.norm(np.array(wl) - pr.cam))
            if d < 200:
                feats.append({"kind": "STOP%d" % actor.id, "world": wl, "pixel": p, "dist": d})

    # ---- traffic light bulbs
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
                best = (vol, v3(wl))
        if best is None:
            continue
        wl = best[1]
        p = pr.project(wl)
        d = float(np.linalg.norm(np.array(wl) - pr.cam))
        if d < 350:
            feats.append({"kind": "TL%d" % actor.id, "world": wl, "pixel": p, "dist": d})

    # ---- draw
    ov = arr.copy()
    colors = {"CW": (0, 255, 0), "STOP": (0, 200, 255), "TL": (255, 0, 255)}
    rows = []
    for f in sorted(feats, key=lambda x: x["dist"]):
        px = f["pixel"]
        if px is None:
            rows.append((f["kind"], f["world"], None, f["dist"]))
            continue
        u, v = int(round(px["u"])), int(round(px["v"]))
        inframe = 0 <= u < W and 0 <= v < H
        key = "TL" if f["kind"].startswith("TL") else ("STOP" if f["kind"].startswith("STOP") else "CW")
        c = colors[key]
        if inframe:
            cv2.drawMarker(ov, (u, v), c, cv2.MARKER_CROSS, 22, 2)
            cv2.putText(ov, "%s %.0fm" % (f["kind"], f["dist"]), (u + 7, v - 7),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, c, 2, cv2.LINE_AA)
        else:
            # clamp label to the nearest edge so off-frame targets are still visible
            cu = min(max(u, 2), W - 120)
            cv2v = min(max(v, 16), H - 6)
            cv2.drawMarker(ov, (cu, cv2v), c, cv2.MARKER_TILTED_CROSS, 16, 2)
            cv2.putText(ov, "%s %.0fm" % (f["kind"], f["dist"]), (cu + 4, cv2v - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, c, 1, cv2.LINE_AA)
        rows.append((f["kind"], f["world"], (u, v), f["dist"], inframe))

    cv2.imwrite(os.path.join(OUTDIR, "overlay_all.png"), ov)

    print("%-8s %-30s %-18s %8s  %s" % ("kind", "world", "pixel", "dist", "in_frame"))
    for r in rows:
        if len(r) == 4:
            print("%-8s (%8.2f,%8.2f,%5.2f)  %-18s %8.1f  no" % (r[0], r[1][0], r[1][1], r[1][2], "off-axis", r[3]))
        else:
            print("%-8s (%8.2f,%8.2f,%5.2f)  %-18s %8.1f  %s"
                  % (r[0], r[1][0], r[1][1], r[1][2], "(%4d,%4d)" % r[2], r[3], "YES" if r[4] else "no"))

    with open(r"E:\output\_scripts\_features.json", "w", encoding="utf-8") as fh:
        json.dump({"spectator": {"location": v3(tf.location),
                                 "rotation": [tf.rotation.pitch, tf.rotation.yaw, tf.rotation.roll]},
                   "features": feats}, fh, ensure_ascii=False, indent=2)
    print("\nwrote", os.path.join(OUTDIR, "overlay_all.png"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
