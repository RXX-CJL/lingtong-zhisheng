"""Re-run the ground-marker calibration with the CORRECTED projection matrix.

Markers are stacks of barriers at known ground distances along the view axis, so
even points below the frame edge are still measurable (their top is visible).
"""
import math
import os
import sys
import time

import numpy as np
import carla
import cv2

OUTDIR = r"E:\output\_camera_check"
os.makedirs(OUTDIR, exist_ok=True)
sys.path.insert(0, r"E:\output\_scripts")
from _spec_check import Proj, v3  # noqa: E402

W, H, FOV = 1280, 720, 90.0


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(25.0)
    world = client.get_world()
    spec = world.get_spectator().get_transform()
    pr = Proj(spec, W, H, FOV)

    print("spectator loc=(%.3f,%.3f,%.3f) pitch=%.3f yaw=%.3f" %
          (spec.location.x, spec.location.y, spec.location.z,
           spec.rotation.pitch, spec.rotation.yaw))
    print("forward =", np.round(pr.fwd, 4), "  (z must be NEGATIVE for a downward pitch)")

    cam = np.array(v3(spec.location))
    yaw = math.radians(spec.rotation.yaw)
    fwd_xy = np.array([math.cos(yaw), math.sin(yaw), 0.0])

    dists = [8.0, 12.0, 20.0, 32.0, 45.0]
    plan = []
    for d in dists:
        p = cam + fwd_xy * d
        p[2] = 0.0
        plan.append(("G%.0f" % d, [float(p[0]), float(p[1]), 0.0]))

    bp = world.get_blueprint_library().find("static.prop.streetbarrier")
    spawned = []
    for name, pt in plan:
        # stack barriers up to ~8 m so the marker is visible even when its base is below frame
        for dz in (0.0, 2.3, 4.6, 6.9):
            try:
                a = world.spawn_actor(bp, carla.Transform(
                    carla.Location(x=pt[0], y=pt[1], z=pt[2] + dz),
                    carla.Rotation(pitch=0, yaw=spec.rotation.yaw + 90, roll=0)))
                spawned.append(a)
            except Exception as e:
                print("spawn fail", name, dz, e)

    cbp = world.get_blueprint_library().find("sensor.camera.rgb")
    cbp.set_attribute("image_size_x", str(W))
    cbp.set_attribute("image_size_y", str(H))
    cbp.set_attribute("fov", str(FOV))
    ca = world.spawn_actor(cbp, spec)
    frames = []
    ca.listen(lambda im: frames.append(im))
    for _ in range(8):
        world.tick()
        time.sleep(0.05)
    time.sleep(0.7)
    ca.stop()
    ca.destroy()
    arr = np.frombuffer(frames[-1].raw_data, np.uint8).reshape(H, W, 4)[:, :, :3].copy()

    # blue mask (barriers are orange/white -> use "not road grey" via saturation)
    hsv = cv2.cvtColor(arr, cv2.COLOR_BGR2HSV)
    mask = ((hsv[:, :, 1] > 60) & (hsv[:, :, 2] > 90)).astype(np.uint8) * 255

    print("\n%-6s %-30s %-18s %-18s %s" % ("marker", "base world", "predicted(base)", "measured(centroid)", "err"))
    ov = arr.copy()
    for name, pt in plan:
        r = pr.project(pt)
        pred = (r["u"], r["v"]) if r else None
        base_v = pred[1] if pred else None
        if pred is None:
            print("%-6s (%7.2f,%7.2f,%5.2f) off-axis" % (name, pt[0], pt[1], pt[2]))
            continue
        if 0 <= pred[0] < W and 0 <= pred[1] < H:
            # measure near the predicted base
            x0, y0 = max(0, int(pred[0]) - 130), max(0, int(pred[1]) - 200)
            x1, y1 = min(W, int(pred[0]) + 130), min(H, int(pred[1]) + 60)
            sub = mask[y0:y1, x0:x1]
            n = int(sub.sum() // 255)
            if n > 40:
                ys, xs = np.nonzero(sub)
                mx, my = float(xs.mean()) + x0, float(ys.mean()) + y0
                # the stack spans base..base+8m, so its centroid sits above the base
                top = pr.project([pt[0], pt[1], 8.0])
                print("%-6s (%7.2f,%7.2f,%5.2f) base=(%5.0f,%5.0f) meas=(%5.0f,%5.0f) n=%-5d top=(%5.0f,%5.0f)"
                      % (name, pt[0], pt[1], pt[2], pred[0], pred[1], mx, my, n,
                         top["u"] if top else -1, top["v"] if top else -1))
                cv2.drawMarker(ov, (int(pred[0]), int(pred[1])), (0, 0, 255), cv2.MARKER_CROSS, 26, 2)
                cv2.drawMarker(ov, (int(mx), int(my)), (0, 255, 0), cv2.MARKER_TILTED_CROSS, 22, 2)
                cv2.putText(ov, name, (int(pred[0]) + 8, int(pred[1]) - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)
                if top and 0 <= top["v"] < H:
                    cv2.drawMarker(ov, (int(top["u"]), int(top["v"])), (255, 0, 0), cv2.MARKER_CROSS, 20, 2)
            else:
                print("%-6s (%7.2f,%7.2f,%5.2f) base=(%5.0f,%5.0f) NOT FOUND n=%d"
                      % (name, pt[0], pt[1], pt[2], pred[0], pred[1], n))
        else:
            print("%-6s (%7.2f,%7.2f,%5.2f) base pixel (%5.0f,%5.0f) OUT OF FRAME"
                  % (name, pt[0], pt[1], pt[2], pred[0], pred[1]))
    cv2.imwrite(os.path.join(OUTDIR, "calib3_corrected.png"), ov)

    # horizon check
    print("\nhorizon row (v where the view ray is horizontal) = %.0f" % (H / 2 + pr.f * math.tan(math.radians(spec.rotation.pitch))))
    print("nearest visible ground distance = %.1f m" % (spec.location.z / math.tan(math.radians(-spec.rotation.pitch + math.degrees(math.atan(1.0 / (pr.f / (W / 2)) * (H / 2)))))))

    for a in spawned:
        try:
            a.destroy()
        except Exception:
            pass
    print("cleaned %d actors -> calib3_corrected.png" % len(spawned))
    return 0


if __name__ == "__main__":
    sys.exit(main())
