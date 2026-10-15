"""用【修正后】的投影，重做一锤定音的对照实验。

修正前的错误：Proj 的 up 向量写成 [sp*cy, sp*sy, cp]（应为负号），
导致所有物体都放到画面外、灯珠采样点错位。

本次：两个对照车放在 10 m / 14 m（这两个深度已验证在地面可见带内），
与红绿灯（钉红）同帧测量。
"""
import math
import os
import sys
import time

import numpy as np
import carla
import cv2

OUT = r"E:\output\_control2"
os.makedirs(OUT, exist_ok=True)
W, H, FOV = 1920, 1080, 90.0
CAM_LOC = np.array([-19.720, -63.145, 5.732])   # spectator 基准
CAM_PITCH, CAM_YAW = -23.445, 179.536
KNOWN_MAST = (-46.17, -73.56)
KNOWN_STOP = (-25.61, -64.76)


def proj(p):
    """修正版（up 用负号）"""
    p_, y_ = math.radians(CAM_PITCH), math.radians(CAM_YAW)
    cp, sp, cy, sy = math.cos(p_), math.sin(p_), math.cos(y_), math.sin(y_)
    f = W / (2 * math.tan(math.radians(FOV) / 2))
    d = np.asarray(p, float) - CAM_LOC
    z = float(d @ np.array([cp * cy, cp * sy, -sp]))
    if z <= 1e-6:
        return None
    return (W / 2 + f * float(d @ np.array([-sy, cy, 0.0])) / z,
            H / 2 - f * float(d @ np.array([-sp * cy, -sp * sy, cp])) / z, z)


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
    return np.frombuffer(got[-1].raw_data, np.uint8).reshape(H, W, 4)[:, :, :3].copy()


def measure_at(img, xy, half=18):
    x, y = xy
    roi = img[max(0, y - half):y + half, max(0, x - half):x + half]
    if roi.size == 0:
        return None
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    sc = hsv[:, :, 1].astype(np.int32) * hsv[:, :, 2].astype(np.int32)
    yy, xx = np.unravel_index(int(np.argmax(sc)), sc.shape)
    b, g, r = [int(roi[yy, xx, k]) for k in range(3)]
    hh = cv2.cvtColor(np.uint8([[[b, g, r]]]), cv2.COLOR_BGR2HSV)[0, 0]
    return (b, g, r, int(hh[0]) * 2, int(hh[1]))


def nm_of(b, g, r, hue, sat):
    if sat < 45:
        return "grey/low-sat"
    if hue < 20 or hue >= 340:
        return "RED"
    if hue < 50:
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
    spawns = []
    # 已验证：8m 以远在画面内。放 10m 与 14m，横向各偏 4m。
    plan = [("red", "vehicle.tesla.model3", (-29.7, -67.1)),
            ("green", "vehicle.audi.a2", (-33.7, -59.1))]
    for tag, bp_id, (px, py) in plan:
        r = proj([px, py, 0.9])
        print("  预检 %-6s -> %s" % (tag, "无" if r is None else "(%.0f,%.0f) d=%.1f" % r))
        if r is None or not (0 <= r[0] < W and 0 <= r[1] < H):
            print("     不在画面内")
            continue
        bp = bl.filter(bp_id)[0]
        a = world.spawn_actor(bp, carla.Transform(
            carla.Location(x=px, y=py, z=0.3), carla.Rotation(pitch=0, yaw=90.0, roll=0)))
        spawns.append((tag, a, (px, py), (int(r[0]), int(r[1]))))

    for t in tls:
        t.freeze(True)
        t.set_state(carla.TrafficLightState.Red)
    for _ in range(6):
        world.tick()
        time.sleep(0.04)
    img_r = render(world)
    cv2.imwrite(os.path.join(OUT, "red_state.png"), img_r)

    for t in tls:
        t.set_state(carla.TrafficLightState.Green)
    for _ in range(6):
        world.tick()
        time.sleep(0.04)
    img_g = render(world)
    cv2.imwrite(os.path.join(OUT, "green_state.png"), img_g)

    print("\n=== 同帧对照（修正投影后）===")
    print("%-8s %-12s %-34s %s" % ("对象", "投影像素", "实测最饱和像素", "判定"))
    for tag, a, pos, xy in spawns:
        m = measure_at(img_r, xy)
        if m is None:
            print("%-8s 采样失败" % tag)
            continue
        print("%-8s (%5d,%5d)  BGR=(%3d,%3d,%3d) hue=%-3d sat=%-3d -> %s"
              % (tag, xy[0], xy[1], m[0], m[1], m[2], m[3], m[4], nm_of(*m)))

    d = cv2.absdiff(img_r, img_g).max(axis=2)
    mm = cv2.morphologyEx((d > 25).astype(np.uint8) * 255, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    nc, lab, st, ce = cv2.connectedComponentsWithStats(mm, 8)
    blobs = sorted([(int(st[i, cv2.CC_STAT_AREA]), int(ce[i][0]), int(ce[i][1]))
                    for i in range(1, nc)], reverse=True)[:4]
    print("\n红绿灯（Red/Green 差分锁定）:")
    for aa, cx, cy in blobs:
        sel = None
        for i in range(1, nc):
            if int(ce[i][0]) == cx and int(ce[i][1]) == cy and int(st[i, cv2.CC_STAT_AREA]) == aa:
                sel = (lab == i)
                break
        if sel is None:
            continue
        rb, rg, rr = [float(img_r[:, :, k][sel].mean()) for k in range(3)]
        gb, gg, gr = [float(img_g[:, :, k][sel].mean()) for k in range(3)]
        hR = cv2.cvtColor(np.uint8([[[int(rb), int(rg), int(rr)]]]), cv2.COLOR_BGR2HSV)[0, 0]
        hG = cv2.cvtColor(np.uint8([[[int(gb), int(gg), int(gr)]]]), cv2.COLOR_BGR2HSV)[0, 0]
        print("   a=%-5d @(%4d,%4d)  Red BGR=(%5.1f,%5.1f,%5.1f) hue=%-3d %-10s | Green BGR=(%5.1f,%5.1f,%5.1f) hue=%-3d %s"
              % (aa, cx, cy, rb, rg, rr, int(hR[0]) * 2, nm_of(rb, rg, rr, int(hR[0]) * 2, int(hR[1])),
                 gb, gg, gr, int(hG[0]) * 2, nm_of(gb, gg, gr, int(hG[0]) * 2, int(hG[1]))))

    for _, a, _, _ in spawns:
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
