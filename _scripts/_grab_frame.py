"""Grab ONE frame through the user's spectator transform + overlay projected
reference points, and run an FOV sensitivity analysis.

Writes:
  E:\\output\\_camera_check\\frame_raw.png        raw 1280x720 frame
  E:\\output\\_camera_check\\frame_marks.png      frame + projected markers
  E:\\output\\_camera_check\\contact_sheet.png    3x3 crops around key targets
"""
import math
import os
import sys
import time

import numpy as np
import carla
import cv2

W, H = 1280, 720
FOV = 90.0
OUTDIR = r"E:\output\_camera_check"
os.makedirs(OUTDIR, exist_ok=True)

sys.path.insert(0, r"E:\output\_scripts")
from _spec_check import Proj, rot_matrix, v3, crosswalk_polys, poly_center  # noqa: E402


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(20.0)
    world = client.get_world()
    m = world.get_map()
    spec = world.get_spectator()
    tf = spec.get_transform()

    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(W))
    bp.set_attribute("image_size_y", str(H))
    bp.set_attribute("fov", str(FOV))
    cam = world.spawn_actor(bp, tf)
    frames = []
    cam.listen(lambda img: frames.append(img))
    for _ in range(6):
        world.tick()
        time.sleep(0.05)
    time.sleep(0.6)
    cam.stop()
    cam.destroy()
    if not frames:
        raise RuntimeError("no frame captured")
    img = frames[-1]
    arr = np.frombuffer(img.raw_data, dtype=np.uint8).reshape(img.height, img.width, 4)[:, :, :3]
    arr = arr.copy()
    cv2.imwrite(os.path.join(OUTDIR, "frame_raw.png"), arr)
    print("frame captured: %dx%d  frame_number=%d" % (img.width, img.height, img.frame))

    pr = Proj(tf, W, H, FOV)

    # ---- collect reference targets
    targets = []
    # junction centre
    junction = None
    for dist in range(0, 240, 2):
        probe = np.array(v3(tf.location)) + pr.fwd * dist
        wp = m.get_waypoint(carla.Location(x=float(probe[0]), y=float(probe[1]), z=float(probe[2])),
                            project_to_road=True, lane_type=carla.LaneType.Driving)
        if wp is not None and wp.is_junction:
            junction = wp
            break
    if junction is not None:
        targets.append(("JUNCTION", v3(junction.transform.location), (0, 0, 255)))

    # stop line nearest to junction
    stops = []
    for actor in world.get_actors().filter("traffic.traffic_light*"):
        try:
            for wp in actor.get_stop_waypoints():
                wl = v3(wp.transform.location)
                d = float(np.linalg.norm(np.array(wl) - pr.cam))
                stops.append((d, actor.id, wl))
        except Exception:
            pass
    stops.sort()
    for d, lid, wl in stops[:2]:
        targets.append(("STOPLINE_L%d" % lid, wl, (0, 255, 255)))

    # nearest 4 crosswalk polygons
    polys = crosswalk_polys(m.get_crosswalks())
    cw = []
    for poly in polys:
        c = poly_center(poly)
        cw.append((float(np.linalg.norm(np.array(c) - pr.cam)), c, len(poly)))
    cw.sort()
    for d, c, n in cw[:4]:
        targets.append(("CROSSWALK", c, (0, 255, 0)))

    # nearest 5 traffic-light bulbs
    bulbs = []
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
                best = (vol, wl)
        if best is None:
            continue
        wl = v3(best[1])
        bulbs.append((float(np.linalg.norm(np.array(wl) - pr.cam)), actor.id, wl))
    bulbs.sort()
    for d, aid, wl in bulbs[:5]:
        targets.append(("TL%d" % aid, wl, (255, 0, 255)))

    marks = arr.copy()
    rows = []
    for name, world_pt, color in targets:
        p = pr.project(world_pt)
        if p is None:
            rows.append((name, world_pt, None, None))
            continue
        u, v = p["u"], p["v"]
        inframe = -80 < u < W + 80 and -80 < v < H + 80
        if inframe:
            cv2.drawMarker(marks, (int(u), int(v)), color, cv2.MARKER_CROSS, 26, 2)
            cv2.putText(marks, "%s d=%.0f" % (name, np.linalg.norm(np.array(world_pt) - pr.cam)),
                        (int(u) + 8, int(v) - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)
        rows.append((name, world_pt, (u, v), p["in_frame"]))

    cv2.imwrite(os.path.join(OUTDIR, "frame_marks.png"), marks)

    # ---- contact sheet: 320x180 crops centred on each in-frame target
    tiles = []
    for name, world_pt, color in targets:
        p = pr.project(world_pt)
        if p is None or not p["in_frame"]:
            tile = np.full((180, 320, 3), 40, np.uint8)
            cv2.putText(tile, "%s OFF" % name, (8, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)
        else:
            u, v = int(p["u"]), int(p["v"])
            x0, y0 = max(0, u - 160), max(0, v - 90)
            x1, y1 = min(W, x0 + 320), min(H, y0 + 180)
            tile = marks[y0:y1, x0:x1].copy()
            cv2.drawMarker(tile, (u - x0, v - y0), color, cv2.MARKER_CROSS, 30, 2)
            cv2.putText(tile, "%s (%d,%d)" % (name, u, v), (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2, cv2.LINE_AA)
        if tile.shape[0] != 180 or tile.shape[1] != 320:
            tile = cv2.resize(tile, (320, 180))
        tiles.append(tile)
    while len(tiles) % 3:
        tiles.append(np.full((180, 320, 3), 40, np.uint8))
    sheet_rows = [np.hstack(tiles[i:i + 3]) for i in range(0, len(tiles), 3)]
    sheet = np.vstack(sheet_rows) if sheet_rows else marks
    cv2.imwrite(os.path.join(OUTDIR, "contact_sheet.png"), sheet)

    print("\n%-16s %-30s %-18s %s" % ("target", "world", "pixel", "in_frame"))
    for name, wp_, px, inf in rows:
        print("%-16s (%8.2f,%8.2f,%5.2f)  %-18s %s"
              % (name, wp_[0], wp_[1], wp_[2],
                 ("(%6.0f,%5.0f)" % px) if px else "-- off-axis --",
                 "YES" if inf else "no"))

    # ---- FOV sensitivity
    print("\nFOV sensitivity (u,v) for the same targets:")
    for fov in (50.0, 70.0, 90.0, 110.0):
        p2 = Proj(tf, W, H, fov)
        line = []
        for name in ("JUNCTION", "STOPLINE_L17", "CROSSWALK"):
            for nm, wp_, _, _ in rows:
                if nm == name:
                    q = p2.project(wp_)
                    line.append("%s=%s" % (name[:4], ("(%.0f,%.0f)" % (q["u"], q["v"])) if q else "off"))
                    break
        print("  fov=%5.1f  %s" % (fov, "  ".join(line)))

    print("\nwrote", OUTDIR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
