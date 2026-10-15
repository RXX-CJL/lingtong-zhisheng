"""Clean reference frame of the user's camera at 1920x1080 (no overlay) + a marked
version showing the four required targets, using the CORRECTED projection.
Also reports the demo-approach data needed by the recorder.
"""
import json
import math
import os
import sys
import time

import numpy as np
import carla
import cv2

OUTDIR = r"E:\output\_camera_verify"
os.makedirs(OUTDIR, exist_ok=True)
sys.path.insert(0, r"E:\output\_scripts")
from _spec_check import Proj  # noqa: E402

W, H, FOV = 1920, 1080, 90.0


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(25.0)
    world = client.get_world()
    m = world.get_map()
    spec = world.get_spectator().get_transform()
    pr = Proj(spec, W, H, FOV)

    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(W))
    bp.set_attribute("image_size_y", str(H))
    bp.set_attribute("fov", str(FOV))
    ca = world.spawn_actor(bp, spec)
    frames = []
    ca.listen(lambda im: frames.append(im))
    for _ in range(6):
        world.tick()
        time.sleep(0.05)
    time.sleep(0.7)
    ca.stop()
    ca.destroy()
    arr = np.frombuffer(frames[-1].raw_data, np.uint8).reshape(H, W, 4)[:, :, :3].copy()
    cv2.imwrite(os.path.join(OUTDIR, "reference_1080.png"), arr)

    marks = arr.copy()
    # the four required targets, hard-coded from verified junction data
    targets = [
        ("CW_far",   [-63.2, -63.2, 0.05],  (0, 255, 0)),
        ("CW_near",  [-31.2, -72.1, 0.05],  (0, 180, 0)),
        ("STOP_L9",  [-25.61, -64.76, 0.15], (0, 255, 255)),
        ("STOP_L9b", [-25.60, -68.26, 0.15], (0, 255, 255)),
        ("JUNCTION", [-29.09, -64.80, 0.0],  (255, 128, 0)),
        ("TL9_head", [-45.7, -64.3, 5.15],   (255, 0, 255)),
    ]
    print("targets with the CORRECTED projection (%dx%d):" % (W, H))
    for name, pt, col in targets:
        r = pr.project(pt)
        if r is None:
            print("   %-9s off-axis" % name)
            continue
        inside = 0 <= r["u"] < W and 0 <= r["v"] < H
        print("   %-9s world=(%8.2f,%8.2f,%6.2f) -> (%6.1f,%6.1f) depth=%.1f m  %s"
              % (name, pt[0], pt[1], pt[2], r["u"], r["v"], r["depth"], "IN" if inside else "OUT"))
        if inside:
            cv2.drawMarker(marks, (int(r["u"]), int(r["v"])), col, cv2.MARKER_CROSS, 28, 3)
            cv2.putText(marks, name, (int(r["u"]) + 10, int(r["v"]) - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, col, 2, cv2.LINE_AA)
    cv2.imwrite(os.path.join(OUTDIR, "reference_1080_marked.png"), marks)

    # demo approach data: the lane the camera watches (road 7 lane 1) and its light
    print("\ndemo approach (road 7 lane 1 -- the lane whose stop line is in frame):")
    wp = m.get_waypoint(carla.Location(x=-15.0, y=-64.7, z=2.0),
                        project_to_road=True, lane_type=carla.LaneType.Driving)
    if wp:
        ch = []
        cur = wp
        for _ in range(8):
            ch.append((round(cur.transform.location.x, 1), round(cur.transform.location.y, 1),
                       round(cur.transform.rotation.yaw, 1)))
            nx = cur.next(6.0)
            if not nx:
                break
            cur = nx[0]
        print("   road=%d lane=%d  heading yaw=%.1f" % (wp.road_id, wp.lane_id, wp.transform.rotation.yaw))
        print("   forward chain:", ch)
        print("   right lane:", (wp.get_right_lane().lane_id if wp.get_right_lane() else None),
              " left lane:", (wp.get_left_lane().lane_id if wp.get_left_lane() else None))
    for tl in world.get_actors().filter("traffic.traffic_light*"):
        if tl.id != 9:
            continue
        print("   light 9 state=%s  freeze=%s" % (tl.get_state(), tl.is_frozen()))
        print("   green=%.1f yellow=%.1f red=%.1f"
              % (tl.get_green_time(), tl.get_yellow_time(), tl.get_red_time()))

    print("\nwrote reference_1080.png / reference_1080_marked.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
