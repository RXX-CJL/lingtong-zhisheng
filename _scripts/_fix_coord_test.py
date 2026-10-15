"""修正坐标后重测：直接在**画面里那两盏灯**上取样，判定红灯颜色。

坐标推导（纯几何，已自洽）：
  * 画面里两个亮灯的水平间距 133.8 px，深度 43 m，像素焦距 960 -> 实际间距 13.8 m
  * 本路口两盏灯间距正好 13.8 m（y: -64.26 -> -68.06）
  * 所以这两盏灯在深度 ~43 m 处，世界 x ≈ -58.6
检测方法：用 Red/Green 帧的**差分**锁定"随状态变化的像素"，只在那里面取最亮及均值。
"""
import math
import os
import sys
import time

import numpy as np
import carla
import cv2

OUT = r"E:\output\_fix_coord"
os.makedirs(OUT, exist_ok=True)
W, H, FOV = 1920, 1080, 90.0
CAM_LOC = (-15.720, -63.145, 5.732)
CAM_PITCH, CAM_YAW = -23.445, 179.536
# 画面里两盏灯的大致位置（前几轮观测）
LAMP_PX = [(1006, 140), (1139, 140)]


def render(world):
    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(W))
    bp.set_attribute("image_size_y", str(H))
    bp.set_attribute("fov", str(FOV))
    cam = world.spawn_actor(bp, carla.Transform(
        carla.Location(*CAM_LOC), carla.Rotation(pitch=CAM_PITCH, yaw=CAM_YAW, roll=0.0)))
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
        return "grey"
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
    s = world.get_settings()
    s.synchronous_mode = True
    s.fixed_delta_seconds = 0.05
    world.apply_settings(s)

    # 把场景里**所有**灯都钉成同一状态，保证画面里被观测的灯一定处于该状态
    tls = list(world.get_actors().filter("traffic.traffic_light*"))
    print("场景红绿灯 %d 个，全部同步钉死" % len(tls))

    imgs = {}
    for nm, st in (("red", carla.TrafficLightState.Red),
                   ("green", carla.TrafficLightState.Green),
                   ("yellow", carla.TrafficLightState.Yellow)):
        for t in tls:
            t.freeze(True)
            t.set_state(st)
        for _ in range(6):
            world.tick()
            time.sleep(0.04)
        imgs[nm] = render(world)
        cv2.imwrite(os.path.join(OUT, "all_%s.png" % nm), imgs[nm])
        print("  已渲染 %s 态" % nm)

    print("\n=== 差分锁定「随状态变化」的像素（在灯附近窗口内）===")
    for (cx, cy) in LAMP_PX:
        hw, hh = 22, 30
        x0, y0 = cx - hw, cy - hh
        x1, y1 = cx + hw, cy + hh
        win_r = imgs["red"][y0:y1, x0:x1]
        win_g = imgs["green"][y0:y1, x0:x1]
        win_y = imgs["yellow"][y0:y1, x0:x1]
        d = cv2.absdiff(win_r, win_g).max(axis=2)
        n = int((d > 20).sum())
        print("\n灯@(%d,%d) 窗口 %dx%d，红/绿差>20 的像素=%d" % (cx, cy, 2 * hw, 2 * hh, n))
        for nm, win in (("RED", win_r), ("GREEN", win_g), ("YELLOW", win_y)):
            g = cv2.cvtColor(win, cv2.COLOR_BGR2GRAY)
            yy, xx = np.unravel_index(int(np.argmax(g)), g.shape)
            b, gg, r = [int(win[yy, xx, k]) for k in range(3)]
            hsv = cv2.cvtColor(np.uint8([[[b, gg, r]]]), cv2.COLOR_BGR2HSV)[0, 0]
            hue, sat, val = int(hsv[0]) * 2, int(hsv[1]), int(hsv[2])
            print("   %-7s 最亮像素 BGR=(%3d,%3d,%3d) hue=%-3d sat=%-3d V=%-3d -> %s"
                  % (nm, b, gg, r, hue, sat, val, name(hue, sat)))
        if n > 0:
            sel = d > 20
            for nm, win in (("RED", win_r), ("GREEN", win_g)):
                mb, mg, mr = [float(win[:, :, k][sel].mean()) for k in range(3)]
                hsv = cv2.cvtColor(np.uint8([[[int(mb), int(mg), int(mr)]]]), cv2.COLOR_BGR2HSV)[0, 0]
                print("   [变化区均色] %-7s BGR=(%6.1f,%6.1f,%6.1f) hue=%-3d sat=%-3d -> %s"
                      % (nm, mb, mg, mr, int(hsv[0]) * 2, int(hsv[1]),
                         name(int(hsv[0]) * 2, int(hsv[1]))))

    # 全图：三态两两差分，列出所有显著变化区及其颜色
    print("\n=== 全图变化区（red vs green，>25）===")
    d = cv2.absdiff(imgs["red"], imgs["green"]).max(axis=2)
    mm = cv2.morphologyEx((d > 25).astype(np.uint8) * 255, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    nc, lab, st, ce = cv2.connectedComponentsWithStats(mm, 8)
    blobs = sorted([(int(st[i, cv2.CC_STAT_AREA]), int(ce[i][0]), int(ce[i][1])) for i in range(1, nc)],
                   reverse=True)[:8]
    for a, cx, cy in blobs:
        sel = (lab == 0)
        for i in range(1, nc):
            if int(ce[i][0]) == cx and int(ce[i][1]) == cy and int(st[i, cv2.CC_STAT_AREA]) == a:
                sel = (lab == i)
                break
        rb, rg, rr = [float(imgs["red"][:, :, k][sel].mean()) for k in range(3)]
        gb, gg, gr = [float(imgs["green"][:, :, k][sel].mean()) for k in range(3)]
        def hn(b_, g_, r_):
            hsv = cv2.cvtColor(np.uint8([[[int(b_), int(g_), int(r_)]]]), cv2.COLOR_BGR2HSV)[0, 0]
            return int(hsv[0]) * 2, int(hsv[1])
        hR, sR = hn(rb, rg, rr)
        hG, sG = hn(gb, gg, gr)
        print("   a=%-5d @(%4d,%4d)  RED态 BGR=(%5.1f,%5.1f,%5.1f) h=%-3d s=%-3d %-10s | GREEN态 BGR=(%5.1f,%5.1f,%5.1f) h=%-3d s=%-3d %s"
              % (a, cx, cy, rb, rg, rr, hR, sR, name(hR, sR), gb, gg, gr, hG, sG, name(hG, sG)))

    for t in tls:
        t.freeze(False)
    s.synchronous_mode = False
    s.fixed_delta_seconds = None
    world.apply_settings(s)
    print("\n产出:", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
