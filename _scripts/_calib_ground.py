"""Ground-level projection calibration: markers at known ground distances along the
view axis, predicted by the formula and measured in the rendered frame.

Writes E:\\output\\_camera_check\\calib2_marked.png + calib2.json
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
    yaw = math.radians(tf.rotation.yaw)
    fwd_xy = np.array([math.cos(yaw), math.sin(yaw), 0.0])

    dists = [12.0, 25.0, 40.0, 60.0]
    ground = []
    for d in dists:
        p = cam + fwd_xy * d
        p[2] = 0.6                      # just above the road
        ground.append(("G%.0f" % d, [float(p[0]), float(p[1]), float(p[2])]))

    bp = world.get_blueprint_library().find("static.prop.streetbarrier")
    spawned = []
    for name, pt in ground:
        for dz in (0.0, 2.2):
            try:
                a = world.spawn_actor(bp, carla.Transform(
                    carla.Location(x=pt[0], y=pt[1], z=pt[2] + dz),
                    carla.Rotation(pitch=0, yaw=tf.rotation.yaw + 90, roll=0)))
                spawned.append(a)
            except Exception as e:
                print("spawn fail", name, dz, e)

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

    hsv = cv2.cvtColor(arr, cv2.COLOR_BGR2HSV)
    mask = ((hsv[:, :, 1] > 90) & (hsv[:, :, 2] > 100)).astype(np.uint8) * 255

    marks = arr.copy()
    print("\n%-6s %-28s %-16s %-18s %s" % ("mk", "world", "predicted", "measured", "err"))
    out = []
    for name, pt in ground:
        p = pr.project(pt)
        if not p:
            print("%-6s %-28s off-axis" % (name, "(%7.2f,%7.2f,%5.2f)" % tuple(pt)))
            continue
        u, v = int(p["u"]), int(p["v"])
        rec = {"name": name, "world": pt, "pred": [p["u"], p["v"]]}
        if 0 <= u < W and 0 <= v < H - 4:
            x0, y0 = max(0, u - 120), max(0, v - 110)
            x1, y1 = min(W, u + 120), min(H, v + 40)
            sub = mask[y0:y1, x0:x1]
            n = int(sub.sum() // 255)
            if n > 40:
                ys, xs = np.nonzero(sub)
                mx, my = float(xs.mean()) + x0, float(ys.mean()) + y0
                err = math.hypot(mx - p["u"], my - p["v"])
                print("%-6s (%7.2f,%7.2f,%5.2f)  (%6.0f,%6.0f)  (%6.0f,%6.0f)  %6.1f px  n=%d"
                      % (name, pt[0], pt[1], pt[2], p["u"], p["v"], mx, my, err, n))
                rec.update({"meas": [mx, my], "err": err, "n": n})
                cv2.drawMarker(marks, (int(mx), int(my)), (0, 255, 0), cv2.MARKER_TILTED_CROSS, 26, 2)
            else:
                print("%-6s (%7.2f,%7.2f,%5.2f)  (%6.0f,%6.0f)  NOT FOUND n=%d"
                      % (name, pt[0], pt[1], pt[2], p["u"], p["v"], n))
                rec.update({"meas": None, "n": n})
        else:
            print("%-6s (%7.2f,%7.2f,%5.2f)  (%6.0f,%6.0f)  OUT OF FRAME"
                  % (name, pt[0], pt[1], pt[2], p["u"], p["v"]))
            rec.update({"meas": None, "n": None})
        out.append(rec)
        cv2.drawMarker(marks, (u, v), (0, 0, 255), cv2.MARKER_CROSS, 30, 2)
        cv2.putText(marks, name, (u + 8, v - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)

    cv2.imwrite(os.path.join(OUTDIR, "calib2_marked.png"), marks)
    with open(os.path.join(OUTDIR, "calib2.json"), "w", encoding="utf-8") as f:
        json.dump({"spectator": {"location": v3(tf.location),
                                 "rotation": [tf.rotation.pitch, tf.rotation.yaw, tf.rotation.roll]},
                   "markers": out}, f, ensure_ascii=False, indent=2)

    for a in spawned:
        try:
            a.destroy()
        except Exception:
            pass
    print("\ncleaned %d -> %s" % (len(spawned), os.path.join(OUTDIR, "calib2_marked.png")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
