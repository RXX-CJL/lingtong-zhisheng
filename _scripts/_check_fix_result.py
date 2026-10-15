"""修复后验证：红灯是不是真的红了？

读图已改为正确方式（raw_data 是 BGRA，取前三通道即 BGR，不再多反转）。
同帧测两个对象：
  (1) 橙色路障 —— 保色对照基准（真值橙，应 R 最大）
  (2) 红绿灯点亮镜片 —— Red/Green 差分锁定
"""
import math
import os
import sys
import time

import numpy as np
import carla
import cv2

OUT = r"E:\output\_verify_fix"
os.makedirs(OUT, exist_ok=True)
W, H, FOV = 1920, 1080, 90.0
CAM_LOC = np.array([-19.720, -63.145, 5.732])
CAM_PITCH, CAM_YAW = -23.445, 179.536
KNOWN_MAST = (-46.17, -73.56)
KNOWN_STOP = (-25.61, -64.76)


def grab(image):
    """★ 正确读法：BGRA -> 取前三通道 = BGR"""
    return np.frombuffer(image.raw_data, np.uint8).reshape(H, W, 4)[:, :, :3].copy()


def find_light(world):
    best = None
    for a in world.get_actors().filter("traffic.traffic_light*"):
        L = a.get_transform().location
        dm = math.dist((L.x, L.y), KNOWN_MAST)
        ds = 1e9
        try:
            for wp in a.get_stop_waypoints():
                sl = wp.transform.location
                ds = min(ds, math.dist((sl.x, sl.y), KNOWN_STOP))
        except Exception:
            pass
        sc = ds * 2.0 + dm * 0.5
        if best is None or sc < best[0]:
            best = (sc, a)
    return best[1] if best else None


def proj(p):
    p_, y_ = math.radians(CAM_PITCH), math.radians(CAM_YAW)
    cp, sp, cy, sy = math.cos(p_), math.sin(p_), math.cos(y_), math.sin(y_)
    f = W / (2 * math.tan(math.radians(FOV) / 2))
    d = np.asarray(p, float) - CAM_LOC
    z = float(d @ np.array([cp * cy, cp * sy, -sp]))
    if z <= 1e-6:
        return None
    return (W / 2 + f * float(d @ np.array([-sy, cy, 0.0])) / z,
            H / 2 - f * float(d @ np.array([-sp * cy, -sp * sy, cp])) / z, z)


def render(world):
    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(W))
    bp.set_attribute("image_size_y", str(H))
    bp.set_attribute("fov", str(FOV))
    cam = world.spawn_actor(bp, carla.Transform(
        carla.Location(x=float(CAM_LOC[0]), y=float(CAM_LOC[1]), z=float(CAM_LOC[2])),
        carla.Rotation(pitch=CAM_PITCH, yaw=CAM_YAW, roll=0.0)))
    got = []
    cam.listen(lambda im: got.append(im))
    for _ in range(6):
        world.tick()
        time.sleep(0.04)
    time.sleep(0.5)
    cam.stop()
    cam.destroy()
    return grab(got[-1])


def nm(b, g, r, hue, sat):
    if sat < 45:
        return "grey"
    if hue < 20 or hue >= 340:
        return "RED"
    if hue < 45:
        return "orange"
    if hue < 70:
        return "yellow"
    if hue < 100:
        return "yellow-green"
    if hue < 150:
        return "GREEN"
    if hue < 200:
        return "cyan"
    if hue < 260:
        return "blue"
    return "purple"


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(60.0)
    world = client.get_world()
    if len(world.get_actors().filter("traffic.traffic_light*")) == 0:
        world = client.load_world("Town10HD_Opt")
        time.sleep(3)
    tl = find_light(world)
    tls = list(world.get_actors().filter("traffic.traffic_light*"))
    print("灯=%d 目标灯 id=%d" % (len(tls), tl.id))

    s = world.get_settings()
    s.synchronous_mode = True
    s.fixed_delta_seconds = 0.05
    world.apply_settings(s)

    bl = world.get_blueprint_library()
    anchors = []
    for dy in (-3.0, 3.0):
        px, py = -29.7, -63.145 + dy
        r = proj([px, py, 1.0])
        if r is None or not (0 <= r[0] < W and 0 <= r[1] < H):
            print("  路障预检不在画面内 dy=%.1f" % dy)
            continue
        bp = bl.filter("static.prop.streetbarrier")[0]
        a = world.spawn_actor(bp, carla.Transform(
            carla.Location(x=px, y=py, z=0.3), carla.Rotation(pitch=0, yaw=90, roll=0)))
        anchors.append((dy, (int(r[0]), int(r[1])), a))
        print("  路障 dy=%+.1f 投影=(%d,%d)" % (dy, r[0], r[1]))

    imgs = {}
    for tag, st in (("Red", carla.TrafficLightState.Red),
                    ("Green", carla.TrafficLightState.Green),
                    ("Yellow", carla.TrafficLightState.Yellow)):
        for t in tls:
            t.freeze(True)
            t.set_state(st)
        for _ in range(6):
            world.tick()
            time.sleep(0.04)
        imgs[tag] = render(world)
        cv2.imwrite(os.path.join(OUT, "fixed_%s.png" % tag.lower()), imgs[tag])

    print("\n=== (1) 保色对照：橙色路障（真值=橙，应 R 最大）===")
    for dy, (x, y), a in anchors:
        m = imgs["Red"][max(0, y - 22):y + 22, max(0, x - 22):x + 22]
        hsv = cv2.cvtColor(m, cv2.COLOR_BGR2HSV)
        sc = hsv[:, :, 1].astype(np.int32) * hsv[:, :, 2].astype(np.int32)
        yy, xx = np.unravel_index(int(np.argmax(sc)), sc.shape)
        b, g, r = [int(m[yy, xx, k]) for k in range(3)]
        hh = cv2.cvtColor(np.uint8([[[b, g, r]]]), cv2.COLOR_BGR2HSV)[0, 0]
        print("  dy=%+.1f @(%d,%d) BGR=(%3d,%3d,%3d) hue=%-3d sat=%-3d -> %s"
              % (dy, x, y, b, g, r, int(hh[0]) * 2, int(hh[1]),
                 nm(b, g, r, int(hh[0]) * 2, int(hh[1]))))

    print("\n=== (2) 红绿灯：Red/Green 差分锁定变化区 ===")
    d = cv2.absdiff(imgs["Red"], imgs["Green"]).max(axis=2)
    mm = cv2.morphologyEx((d > 25).astype(np.uint8) * 255, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    nc, lab, st, ce = cv2.connectedComponentsWithStats(mm, 8)
    blobs = sorted([(int(st[i, cv2.CC_STAT_AREA]), int(ce[i][0]), int(ce[i][1]))
                    for i in range(1, nc)], reverse=True)[:5]
    for a_, cx, cy in blobs:
        sel = None
        for i in range(1, nc):
            if int(ce[i][0]) == cx and int(ce[i][1]) == cy and int(st[i, cv2.CC_STAT_AREA]) == a_:
                sel = (lab == i)
                break
        if sel is None:
            continue
        print("  a=%-5d @(%4d,%4d)" % (a_, cx, cy))
        for tag in ("Red", "Green", "Yellow"):
            b, g, r = [float(imgs[tag][:, :, k][sel].mean()) for k in range(3)]
            hh = cv2.cvtColor(np.uint8([[[int(b), int(g), int(r)]]]), cv2.COLOR_BGR2HSV)[0, 0]
            print("     %-7s BGR=(%5.1f,%5.1f,%5.1f) h=%-3d %s"
                  % (tag, b, g, r, int(hh[0]) * 2,
                     nm(b, g, r, int(hh[0]) * 2, int(hh[1]))))

    for _, _, a in anchors:
        try:
            a.destroy()
        except Exception:
            pass
    for t in tls:
        t.freeze(False)
    s.synchronous_mode = False
    s.fixed_delta_seconds = None
    world.apply_settings(s)
    print("\n产出:", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
