"""最小无歧义实验：确认三件事
  1. 渲染管线是否保色（用"已知颜色的发光体"验证）
  2. CARLA 红绿灯在 Red 态下，点亮的那颗镜片渲染成什么颜色
  3. 用**纯几何**（投影）锁定镜片位置，不靠亮度/饱和度猜

做法：用 light_boxes 的 raw 世界坐标投影到画面，得到三颗镜片的像素位置，
再在每颗镜片的小窗口里取"该窗口内最亮像素"，逐一对比 Red / Green 两态。
"""
import math
import os
import sys
import time

import numpy as np
import carla
import cv2

OUT = r"E:\output\_minimal"
os.makedirs(OUT, exist_ok=True)
KNOWN_MAST = (-46.17, -73.56)
KNOWN_STOP = (-25.61, -64.76)
W, H, FOV = 1920, 1080, 90.0
CAM_LOC = np.array([-15.720, -63.145, 5.732])
CAM_PITCH, CAM_YAW = -23.445, 179.536


def proj(p, w=W, h=H, fov=FOV):
    p_, y_ = math.radians(CAM_PITCH), math.radians(CAM_YAW)
    cp, sp, cy, sy = math.cos(p_), math.sin(p_), math.cos(y_), math.sin(y_)
    fwd = np.array([cp * cy, cp * sy, -sp])
    right = np.array([-sy, cy, 0.0])
    up = np.array([sp * cy, sp * sy, cp])
    d = np.asarray(p, float) - CAM_LOC
    z = float(d @ fwd)
    if z <= 1e-6:
        return None
    f = w / (2 * math.tan(math.radians(fov) / 2))
    return (w / 2 + f * float(d @ right) / z, h / 2 - f * float(d @ up) / z, z)


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


def render(world, cam_tf):
    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(W))
    bp.set_attribute("image_size_y", str(H))
    bp.set_attribute("fov", str(FOV))
    cam = world.spawn_actor(bp, cam_tf)
    got = []
    cam.listen(lambda im: got.append(im))
    for _ in range(6):
        world.tick()
        time.sleep(0.04)
    time.sleep(0.5)
    cam.stop()
    cam.destroy()
    return np.frombuffer(got[-1].raw_data, np.uint8).reshape(H, W, 4)[:, :, :3].copy()


def name(hue, sat):
    if sat < 40:
        return "灰白"
    if hue < 20 or hue >= 340:
        return "红"
    if hue < 50:
        return "橙/棕"
    if hue < 70:
        return "黄"
    if hue < 100:
        return "黄绿"
    if hue < 150:
        return "绿"
    if hue < 200:
        return "青"
    if hue < 260:
        return "蓝"
    return "紫/品红"


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(60.0)
    world = client.get_world()
    tl = find_light(world)
    print("地图=%s  目标灯 id=%d" % (world.get_map().name, tl.id))

    # 3) 纯几何锁定镜片：把 light_boxes 的 raw 坐标投影到画面
    atf = tl.get_transform()
    print("\n灯箱原始坐标投影到用户机位画面（用于纯几何定位）:")
    heads = []
    for i, b in enumerate(tl.get_light_boxes()):
        if max(b.extent.x, b.extent.y) > 2.0:
            continue
        raw = np.array([b.location.x, b.location.y, b.location.z])
        ext = np.array([b.extent.x, b.extent.y, b.extent.z])
        r = proj(raw)
        if r is None:
            continue
        px, py, d = r
        inside = 0 <= px < W and 0 <= py < H
        print("   #%d world=(%8.2f,%8.2f,%6.2f) ext=(%.2f,%.2f,%.2f) -> px=(%6.1f,%6.1f) d=%5.1fm %s"
              % (i, raw[0], raw[1], raw[2], ext[0], ext[1], ext[2], px, py, d,
                 "IN" if inside else "OUT"))
        if inside:
            heads.append((i, raw, (int(px), int(py)), d, ext))

    if not heads:
        print("没有灯箱落在画面内")
        return 1

    s = world.get_settings()
    s.synchronous_mode = True
    s.fixed_delta_seconds = 0.05
    world.apply_settings(s)

    # 1)+2) 两态渲染
    imgs = {}
    for nm, st in (("red", carla.TrafficLightState.Red),
                   ("green", carla.TrafficLightState.Green)):
        tl.freeze(True)
        tl.set_state(st)
        for _ in range(6):
            world.tick()
            time.sleep(0.04)
        imgs[nm] = render(world, carla.Transform(
            carla.Location(x=float(CAM_LOC[0]), y=float(CAM_LOC[1]), z=float(CAM_LOC[2])),
            carla.Rotation(pitch=CAM_PITCH, yaw=CAM_YAW, roll=0.0)))
        cv2.imwrite(os.path.join(OUT, "%s.png" % nm), imgs[nm])

    # 在每颗镜片的投影位置附近取最亮像素（不猜，纯几何）
    print("\n各灯箱投影位置附近的最亮像素（真值：Red 态应有一颗亮红灯）:")
    print("   %-6s %-14s %-34s %-34s" % ("box", "投影px", "RED 态最亮像素", "GREEN 态最亮像素"))
    for i, raw, (px, py), d, ext in heads:
        hw = max(8, int(30 * 6.0 / d) + 6)
        hh = max(10, int(45 * 6.0 / d) + 8)
        out = []
        for nm in ("red", "green"):
            img = imgs[nm]
            x0, y0 = max(0, px - hw), max(0, py - hh)
            x1, y1 = min(W, px + hw), min(H, py + hh)
            roi = img[y0:y1, x0:x1]
            if roi.size == 0:
                out.append("窗口越界")
                continue
            g = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            yy, xx = np.unravel_index(int(np.argmax(g)), g.shape)
            b, gg, r = [int(roi[yy, xx, k]) for k in range(3)]
            hsv = cv2.cvtColor(np.uint8([[[b, gg, r]]]), cv2.COLOR_BGR2HSV)[0, 0]
            hue, sat, val = int(hsv[0]) * 2, int(hsv[1]), int(hsv[2])
            out.append("BGR=(%3d,%3d,%3d) hue=%3d sat=%-3d V=%-3d %s"
                       % (b, gg, r, hue, sat, val, name(hue, sat)))
        print("   #%-5d (%5d,%5d)  %-34s %-34s" % (i, px, py, out[0], out[1]))

    tl.freeze(False)
    s.synchronous_mode = False
    s.fixed_delta_seconds = None
    world.apply_settings(s)
    print("\n产出:", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
