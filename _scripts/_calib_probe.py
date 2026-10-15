"""DECISIVE projection calibration.

Spawns 5 conspicuous cubes at world points computed from the spectator transform
(60m straight ahead, plus 4 offsets at +-15m laterally / +-18m along), projects them
with the VERIFIED formula, then measures their ACTUAL centroid in the rendered frame.

If formula == measurement, the projection is sound and any "off" reading is my
misreading of the scene. If not, the numbers say exactly by how much.

Writes  E:\\output\\_camera_check\\calib_marked.png  and prints a table.
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
from _spec_check import Proj, v3  # noqa: E402


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(20.0)
    world = client.get_world()
    tf = world.get_spectator().get_transform()
    pr = Proj(tf, W, H, FOV)

    cam = np.array(v3(tf.location))
    fwd = np.array(pr.fwd)
    right = np.array([math.cos(math.radians(tf.rotation.yaw) + math.pi / 2),
                      math.sin(math.radians(tf.rotation.yaw) + math.pi / 2), 0.0])

    # known world offsets from the camera
    plan = [
        ("A_fwd60", fwd * 60.0 + np.array([0, 0, 1.0]), (0, 0, 255)),
        ("B_fwd35", fwd * 35.0 + np.array([0, 0, 1.0]), (0, 255, 0)),
        ("C_right15", fwd * 45.0 + right * 15.0 + np.array([0, 0, 1.0]), (255, 0, 0)),
        ("D_left15", fwd * 45.0 - right * 15.0 + np.array([0, 0, 1.0]), (0, 255, 255)),
        ("E_fwd75", fwd * 75.0 + np.array([0, 0, 1.0]), (255, 0, 255)),
    ]

    bp = world.get_blueprint_library().find("static.prop.streetbarrier")
    spawned = []
    cubes = []
    for name, pt, color in plan:
        loc = carla.Location(x=float(pt[0]), y=float(pt[1]), z=float(pt[2]))
        # stack three barriers to make a tall, unmistakable marker
        for dz in (0.0, 2.5, 5.0):
            try:
                a = world.spawn_actor(bp, carla.Transform(
                    carla.Location(x=loc.x, y=loc.y, z=loc.z + dz),
                    carla.Rotation(pitch=0, yaw=tf.rotation.yaw + 90, roll=0)))
                spawned.append(a)
            except Exception as e:
                print("spawn failed for", name, "dz", dz, e)
        cubes.append((name, [loc.x, loc.y, loc.z], color))

    # camera
    cbp = world.get_blueprint_library().find("sensor.camera.rgb")
    cbp.set_attribute("image_size_x", str(W))
    cbp.set_attribute("image_size_y", str(H))
    cbp.set_attribute("fov", str(FOV))
    cam_actor = world.spawn_actor(cbp, tf)
    frames = []
    cam_actor.listen(lambda img: frames.append(img))
    for _ in range(8):
        world.tick()
        time.sleep(0.05)
    time.sleep(0.8)
    cam_actor.stop()
    cam_actor.destroy()
    arr = np.frombuffer(frames[-1].raw_data, dtype=np.uint8).reshape(H, W, 4)[:, :, :3]
    print("frame %dx%d" % (frames[-1].width, frames[-1].height))

    marks = arr.copy()
    print("\n%-10s %-30s %-16s %-16s %s" % ("marker", "world", "predicted px", "measured px", "error"))
    results = []
    for name, wpt, color in cubes:
        p = pr.project(wpt)
        pred = (p["u"], p["v"]) if p else None
        mask = np.zeros((H, W), np.uint8)
        # the barrier's real colour is orange/white; instead search for saturated pixels
        hsv = cv2.cvtColor(arr, cv2.COLOR_BGR2HSV)
        sat = hsv[:, :, 1]
        val = hsv[:, :, 2]
        mask[(sat > 90) & (val > 90)] = 255
        if pred:
            u, v = int(pred[0]), int(pred[1])
            x0, y0 = max(0, u - 140), max(0, v - 140)
            x1, y1 = min(W, u + 140), min(H, v + 140)
            sub = mask[y0:y1, x0:x1]
            n = int(sub.sum() // 255)
            if n > 30:
                ys, xs = np.nonzero(sub)
                meas = (float(xs.mean()) + x0, float(ys.mean()) + y0)
                err = math.hypot(meas[0] - pred[0], meas[1] - pred[1])
                print("%-10s (%7.2f,%7.2f,%5.2f)  (%6.0f,%6.0f)  (%6.0f,%6.0f)  %6.1f px  n=%d"
                      % (name, wpt[0], wpt[1], wpt[2], pred[0], pred[1], meas[0], meas[1], err, n))
                results.append({"name": name, "world": wpt, "pred": list(pred), "meas": list(meas),
                                "err_px": err, "n_px": n})
                cv2.drawMarker(marks, (u, v), (0, 0, 255), cv2.MARKER_CROSS, 30, 2)
                cv2.putText(marks, "%s P" % name, (u + 8, v - 8), cv2.FONT_HERSHEY_SIMPLEX,
                            0.6, (0, 0, 255), 2, cv2.LINE_AA)
                cv2.drawMarker(marks, (int(meas[0]), int(meas[1])), (0, 255, 0), cv2.MARKER_TILTED_CROSS, 24, 2)
            else:
                print("%-10s (%7.2f,%7.2f,%5.2f)  (%6.0f,%6.0f)  NOT FOUND in window n=%d"
                      % (name, wpt[0], wpt[1], wpt[2], pred[0], pred[1], n))
                cv2.drawMarker(marks, (u, v), (255, 255, 0), cv2.MARKER_CROSS, 30, 2)
        else:
            print("%-10s (%7.2f,%7.2f,%5.2f)  off-axis" % (name, wpt[0], wpt[1], wpt[2]))

    cv2.imwrite(os.path.join(OUTDIR, "calib_marked.png"), marks)
    with open(os.path.join(OUTDIR, "calib.json"), "w", encoding="utf-8") as f:
        json.dump({"spectator": {"location": v3(tf.location),
                                 "rotation": [tf.rotation.pitch, tf.rotation.yaw, tf.rotation.roll]},
                   "results": results}, f, ensure_ascii=False, indent=2)

    for a in spawned:
        try:
            a.destroy()
        except Exception:
            pass
    print("\ncleaned %d actors -> %s" % (len(spawned), os.path.join(OUTDIR, "calib_marked.png")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
