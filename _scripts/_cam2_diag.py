"""CAM-2 特写诊断：灯珠在特写里到底有多大、什么颜色。

不经过画中画缩放，直接按脚本里的 CAM2_POS 单独渲染，扫描点亮的灯珠。
"""
import math
import os
import sys
import time

import numpy as np
import carla
import cv2

OUT = r"E:\output\_cam2_diag"
os.makedirs(OUT, exist_ok=True)
W, H, FOV = 1280, 720, 60.0
CAM2_POS = (-32.74, -64.26, 5.15)
CAM2_PITCH, CAM2_YAW = 0.0, 180.0
KNOWN_STOP = (-25.61, -64.76)


def grab(image):
    """正确读法：BGRA -> 前三通道即 BGR"""
    return np.frombuffer(image.raw_data, np.uint8).reshape(H, W, 4)[:, :, :3].copy()


def find_light(world):
    best = None
    for a in world.get_actors().filter("traffic.traffic_light*"):
        d = 1e9
        try:
            for wp in a.get_stop_waypoints():
                sl = wp.transform.location
                d = min(d, math.dist((sl.x, sl.y), KNOWN_STOP))
        except Exception:
            pass
        if best is None or d < best[0]:
            best = (d, a)
    return best[1] if best else None


def lit_lens(img, cx, cy, hw=90, hh=200):
    """在灯头区域找最亮且最彩色的紧凑块 = 点亮的灯珠"""
    x0, y0 = max(0, cx - hw), max(0, cy - hh)
    x1, y1 = min(W, cx + hw), min(H, cy + hh)
    roi = img[y0:y1, x0:x1]
    if roi.size == 0:
        return None
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    sc = hsv[:, :, 1].astype(np.int32) * hsv[:, :, 2].astype(np.int32)
    thr = max(3000, int(sc.max() * 0.5))
    m = (sc > thr).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    nc, lab, st, ce = cv2.connectedComponentsWithStats(m, 8)
    best = None
    for i in range(1, nc):
        a = int(st[i, cv2.CC_STAT_AREA])
        if a < 4:
            continue
        if best is None or a > best[0]:
            best = (a, i, int(ce[i][0]), int(ce[i][1]),
                    int(st[i, cv2.CC_STAT_WIDTH]), int(st[i, cv2.CC_STAT_HEIGHT]))
    if best is None:
        return None
    a, i, bx, by, bw, bh = best
    gx, gy = x0 + bx, y0 + by
    b, g, r = [int(img[gy, gx, k]) for k in range(3)]
    hh2 = cv2.cvtColor(np.uint8([[[b, g, r]]]), cv2.COLOR_BGR2HSV)[0, 0]
    return {"area": a, "xy": (gx, gy), "size": (bw, bh), "bgr": (b, g, r),
            "hue": int(hh2[0]) * 2, "sat": int(hh2[1]),
            "bbox": (x0 + bx - bw, y0 + by - bh, x0 + bx + bw, y0 + by + bh)}


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(60.0)
    world = client.get_world()
    if len(world.get_actors().filter("traffic.traffic_light*")) == 0:
        world = client.load_world("Town10HD_Opt")
        time.sleep(3)
    tl = find_light(world)
    tls = list(world.get_actors().filter("traffic.traffic_light*"))
    print("目标灯 id=%d" % tl.id)

    s = world.get_settings()
    s.synchronous_mode = True
    s.fixed_delta_seconds = 0.05
    world.apply_settings(s)

    # 相机到灯头的距离（列出灯箱坐标）
    print("\n灯箱坐标（用于判断 CAM-2 到灯的距离）：")
    for i, b in enumerate(tl.get_light_boxes()):
        if max(b.extent.x, b.extent.y) > 2.0:
            continue
        raw = (b.location.x, b.location.y, b.location.z)
        d = math.dist(raw, CAM2_POS)
        print("   #%d (%8.2f,%8.2f,%6.2f) ext=(%.2f,%.2f,%.2f) 距 CAM-2 %.1f m"
              % (i, raw[0], raw[1], raw[2], b.extent.x, b.extent.y, b.extent.z, d))

    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(W))
    bp.set_attribute("image_size_y", str(H))
    bp.set_attribute("fov", str(FOV))

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
        # 每次新建相机（stop() 之后不能复用同一 actor 的 listen）
        cam = world.spawn_actor(bp, carla.Transform(
            carla.Location(*CAM2_POS), carla.Rotation(pitch=CAM2_PITCH, yaw=CAM2_YAW, roll=0.0)))
        got = []
        cam.listen(lambda im: got.append(im))
        for _ in range(5):
            world.tick()
            time.sleep(0.05)
        time.sleep(0.4)
        cam.stop()
        cam.destroy()
        imgs[tag] = grab(got[-1])
        cv2.imwrite(os.path.join(OUT, "cam2_%s.png" % tag.lower()), imgs[tag])

    print("\n=== CAM-2 特写里点亮的灯珠 ===")
    for tag in ("Red", "Green", "Yellow"):
        img = imgs[tag]
        # 全图找最亮彩色块
        res = []
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        sc = hsv[:, :, 1].astype(np.int32) * hsv[:, :, 2].astype(np.int32)
        m = (sc > max(4000, int(sc.max() * 0.4))).astype(np.uint8) * 255
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        nc, lab, st, ce = cv2.connectedComponentsWithStats(m, 8)
        for i in range(1, nc):
            a = int(st[i, cv2.CC_STAT_AREA])
            if a < 6:
                continue
            bx, by = int(ce[i][0]), int(ce[i][1])
            b, g, r = [int(img[by, bx, k]) for k in range(3)]
            hh = cv2.cvtColor(np.uint8([[[b, g, r]]]), cv2.COLOR_BGR2HSV)[0, 0]
            res.append((a, bx, by, int(st[i, cv2.CC_STAT_WIDTH]), int(st[i, cv2.CC_STAT_HEIGHT]),
                        b, g, r, int(hh[0]) * 2))
        res.sort(reverse=True)
        print("  %-7s 最亮彩色块:" % tag)
        for a, bx, by, bw, bh, b, g, r, hue in res[:5]:
            nm = ("红" if (hue < 20 or hue >= 340) else "橙" if hue < 45 else
                  "黄" if hue < 70 else "绿" if 70 <= hue < 150 else
                  "青" if hue < 200 else "蓝" if hue < 260 else "紫")
            print("     area=%-5d @(%4d,%4d) %3dx%-3d BGR=(%3d,%3d,%3d) hue=%-3d -> %s"
                  % (a, bx, by, bw, bh, b, g, r, hue, nm))

    for t in tls:
        t.freeze(False)
    s.synchronous_mode = False
    s.fixed_delta_seconds = None
    world.apply_settings(s)
    print("\n产出:", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
