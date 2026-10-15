"""为「双摄方案」定位灯头特写机位。

目标：找到控制本进口道（road 7 lane 1/2）的信号灯头，并找出一个
**能正面看到点亮灯珠**的机位（近摄相机的安装位置）。

方法：
  1. 列出 light 9 的所有灯箱（两种坐标解释都给）
  2. 把 light 9 钉成 Red
  3. 在候选位置网格上渲染，直接看哪个位置能看到**红色发光区域**
     —— 以像素为准，不猜灯面朝向
"""
import json
import math
import os
import sys
import time

import numpy as np
import carla
import cv2

OUT = r"E:\output\_dual_cam"
os.makedirs(OUT, exist_ok=True)
W, H, FOV = 1280, 720, 60.0
LIGHT_ID = 9


def lit_blobs(arr, colour="red"):
    hsv = cv2.cvtColor(arr, cv2.COLOR_BGR2HSV)
    if colour == "red":
        m = (((hsv[:, :, 0] < 10) | (hsv[:, :, 0] > 170)) &
             (hsv[:, :, 1] > 100) & (hsv[:, :, 2] > 110))
    else:
        m = ((hsv[:, :, 0] > 40) & (hsv[:, :, 0] < 100) &
             (hsv[:, :, 1] > 80) & (hsv[:, :, 2] > 110))
    mm = cv2.morphologyEx(m.astype(np.uint8) * 255, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    n, lab, stats, cent = cv2.connectedComponentsWithStats(mm, 8)
    best = None
    for i in range(1, n):
        a = int(stats[i, cv2.CC_STAT_AREA])
        if a < 8:
            continue
        if best is None or a > best[0]:
            best = (a, cent[i], stats[i])
    return best


def render(world, loc, rot):
    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(W))
    bp.set_attribute("image_size_y", str(H))
    bp.set_attribute("fov", str(FOV))
    cam = world.spawn_actor(bp, carla.Transform(loc, rot))
    got = []
    cam.listen(lambda im: got.append(im))
    for _ in range(5):
        world.tick()
        time.sleep(0.04)
    time.sleep(0.45)
    cam.stop()
    cam.destroy()
    return np.frombuffer(got[-1].raw_data, np.uint8).reshape(H, W, 4)[:, :, :3].copy()


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(25.0)
    world = client.get_world()
    tl = None
    for a in world.get_actors().filter("traffic.traffic_light*"):
        if a.id == LIGHT_ID:
            tl = a
    atf = tl.get_transform()
    print("light %d actor loc=(%.2f,%.2f,%.2f) yaw=%.1f" %
          (tl.id, atf.location.x, atf.location.y, atf.location.z, atf.rotation.yaw))

    boxes = tl.get_light_boxes()
    print("\n灯箱（两种坐标解释）:")
    cands = []
    for i, b in enumerate(boxes):
        raw = np.array([b.location.x, b.location.y, b.location.z])
        tr = atf.location + atf.transform(b.location)
        trv = np.array([tr.x, tr.y, tr.z])
        ext = np.array([b.extent.x, b.extent.y, b.extent.z])
        thin = int(np.argmin(ext))
        axis = "XYZ"[thin]
        print("  #%d extent=(%.2f,%.2f,%.2f) 最薄轴=%s" % (i, ext[0], ext[1], ext[2], axis))
        print("      raw        =(%8.2f,%8.2f,%6.2f)" % tuple(raw))
        print("      transformed=(%8.2f,%8.2f,%6.2f)" % tuple(trv))
        cands.append(("raw#%d" % i, raw))
        cands.append(("tr#%d" % i, trv))

    # 钉红
    tl.freeze(True)
    tl.set_state(carla.TrafficLightState.Red)
    for _ in range(6):
        world.tick()
        time.sleep(0.06)
    print("\nlight state =", tl.get_state())

    # 在每个候选位置周围 8 个方向 × 2 个距离放相机，看哪个能看到红珠
    print("\n搜索能正面看到红珠的机位（area=红色发光区像素数）:")
    hits = []
    for name, wp in cands:
        if wp[2] < 2.0:            # 太低的灯箱（行人灯/倒计时）
            continue
        for dist in (6.0, 10.0, 15.0):
            for ang in range(0, 360, 45):
                r = math.radians(ang)
                loc = carla.Location(x=float(wp[0] + math.cos(r) * dist),
                                     y=float(wp[1] + math.sin(r) * dist),
                                     z=float(wp[2] + 0.5))
                yaw = math.degrees(math.atan2(wp[1] - loc.y, wp[0] - loc.x))
                rot = carla.Rotation(pitch=-4.0, yaw=yaw, roll=0.0)
                arr = render(world, loc, rot)
                b = lit_blobs(arr, "red")
                if b and b[0] >= 20:
                    a_, c, st = b
                    hits.append({"box": name, "world": [round(float(v), 2) for v in wp],
                                 "cam": [round(loc.x, 2), round(loc.y, 2), round(loc.z, 2)],
                                 "yaw": round(yaw, 1), "dist": dist, "ang": ang,
                                 "red_area": a_, "px": [int(c[0]), int(c[1])],
                                 "size": [int(st[cv2.CC_STAT_WIDTH]), int(st[cv2.CC_STAT_HEIGHT])],
                                 "frame": os.path.join(OUT, "probe_%s_d%.0f_a%d.png" % (name, dist, ang))})
                    cv2.imwrite(hits[-1]["frame"], arr)
                    print("   %-8s 灯头(%7.1f,%7.1f,%5.2f) 相机(%7.1f,%7.1f,%5.2f) d=%4.0f ang=%3d -> 红区 %-5d px 尺寸 %dx%d"
                          % (name, wp[0], wp[1], wp[2], loc.x, loc.y, loc.z, dist, ang, a_,
                             hits[-1]["size"][0], hits[-1]["size"][1]))
    hits.sort(key=lambda d: -d["red_area"])
    with open(os.path.join(OUT, "probe_hits.json"), "w", encoding="utf-8") as f:
        json.dump(hits, f, ensure_ascii=False, indent=2)
    print("\n共 %d 个机位能看到红珠；最佳 5 个:" % len(hits))
    for h in hits[:5]:
        print("   %-8s cam=%s d=%.0f yaw=%.1f 红区=%d 尺寸=%s"
              % (h["box"], h["cam"], h["dist"], h["yaw"], h["red_area"], h["size"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
