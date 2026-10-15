"""确认"红灯渲染成淡蓝"是普遍问题还是个例。

对视野内的多盏灯，分别钉 Red / Green / Yellow，量其**被点亮镜片**的像素颜色。
（"点亮的镜片"用该灯头区域内饱和度最高的紧凑块定位。）
"""
import math
import os
import sys
import time

import numpy as np
import carla
import cv2

OUT = r"E:\output\_lightup2"
os.makedirs(OUT, exist_ok=True)
W, H, FOV = 1920, 1080, 90.0
CAM1 = carla.Location(x=-15.720, y=-63.145, z=5.732)
ROT1 = carla.Rotation(pitch=-23.445, yaw=179.536, roll=0.0)


def render(world):
    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(W))
    bp.set_attribute("image_size_y", str(H))
    bp.set_attribute("fov", str(FOV))
    cam = world.spawn_actor(bp, carla.Transform(CAM1, ROT1))
    got = []
    cam.listen(lambda im: got.append(im))
    for _ in range(5):
        world.tick()
        time.sleep(0.04)
    time.sleep(0.45)
    cam.stop()
    cam.destroy()
    return np.frombuffer(got[-1].raw_data, np.uint8).reshape(H, W, 4)[:, :, :3].copy()


def lit_lens(img, cx, cy, hw=26, hh=70):
    """在灯头区域找"最彩色的紧凑块"= 点亮的镜片。返回其 BGR"""
    x0, y0 = max(0, cx - hw), max(0, cy - hh)
    x1, y1 = min(W, cx + hw), min(H, cy + hh)
    roi = img[y0:y1, x0:x1]
    if roi.size == 0:
        return None
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    s = hsv[:, :, 1].astype(np.int16)
    v = hsv[:, :, 2].astype(np.int16)
    m = ((s > 60) & (v > 80)).astype(np.uint8)
    n, lab, st, ce = cv2.connectedComponentsWithStats(m, 8)
    best = None
    for i in range(1, n):
        a = int(st[i, cv2.CC_STAT_AREA])
        if a < 5:
            continue
        sc = float((s[lab == i].astype(np.float32) * v[lab == i].astype(np.float32)).mean())
        if best is None or sc > best[0]:
            best = (sc, i, ce[i])
    if best is None:
        return None
    _, i, c = best
    px = int(c[0]) + x0
    py = int(c[1]) + y0
    b, g, r = [int(img[py, px, k]) for k in range(3)]
    hsvp = cv2.cvtColor(np.uint8([[[b, g, r]]]), cv2.COLOR_BGR2HSV)[0, 0]
    return {"bgr": (b, g, r), "hue": int(hsvp[0]) * 2, "sat": int(hsvp[1]),
            "xy": (px, py), "area": int(st[best[1], cv2.CC_STAT_AREA])}


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(60.0)
    world = client.get_world()
    if len(world.get_actors().filter("traffic.traffic_light*")) == 0:
        world = client.load_world("Town10HD_Opt")
        time.sleep(3)
    tls = sorted(world.get_actors().filter("traffic.traffic_light*"), key=lambda a: a.id)
    print("场景红绿灯数:", len(tls))

    s = world.get_settings()
    s.synchronous_mode = True
    s.fixed_delta_seconds = 0.05
    world.apply_settings(s)

    # 先渲染一帧找出画面里的灯头位置
    base = render(world)
    # 用青色掩膜找灯箱（housing 是青蓝色）
    b, g, r = [base[:, :, i].astype(np.int16) for i in range(3)]
    m = ((b > r + 30) & (g > r + 20) & (b > 110)).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, lab, st, ce = cv2.connectedComponentsWithStats(m, 8)
    heads = []
    for i in range(1, n):
        a = int(st[i, cv2.CC_STAT_AREA])
        w_, h_ = int(st[i, cv2.CC_STAT_WIDTH]), int(st[i, cv2.CC_STAT_HEIGHT])
        if a < 150 or h_ < 25 or h_ <= w_:
            continue
        heads.append((a, int(ce[i][0]), int(ce[i][1]), w_, h_))
    heads.sort(key=lambda t: -t[0])
    print("画面里检出的灯头（青蓝色竖向块）: %d 个" % len(heads))
    for a, cx, cy, w_, h_ in heads[:8]:
        print("   area=%-5d (%4d,%4d) %2dx%-3d" % (a, cx, cy, w_, h_))
    if not heads:
        print("没检出灯头，放弃")
        return 1

    # 挑最靠中间的 3 个灯头做测试
    heads.sort(key=lambda t: abs(t[1] - W // 2))
    targets = heads[:3]

    print("\n对每盏灯三态测量（点亮镜片的像素颜色）:")
    print("%-8s %-30s %-30s %s" % ("灯头@", "Red", "Green", "Yellow"))
    rows = []
    for a, cx, cy, w_, h_ in targets:
        res = {}
        for name, stt in (("Red", carla.TrafficLightState.Red),
                          ("Green", carla.TrafficLightState.Green),
                          ("Yellow", carla.TrafficLightState.Yellow)):
            # 把**所有**灯都设成同一状态（画面里多盏灯，无法逐一对应，只做整体观察）
            for t in tls:
                t.freeze(True)
                t.set_state(stt)
            for _ in range(5):
                world.tick()
                time.sleep(0.04)
            img = render(world)
            cv2.imwrite(os.path.join(OUT, "all_%s.png" % name.lower()), img)
            L = lit_lens(img, cx, cy, hw=max(12, w_ // 2 + 6), hh=max(30, h_ // 2 + 20))
            res[name] = L
        def fmt(L):
            if L is None:
                return "无彩色块"
            return "BGR=%-16s hue=%-4d sat=%-3d" % (str(L["bgr"]), L["hue"], L["sat"])
        print("%-8s %-30s %-30s %s" % ("(%d,%d)" % (cx, cy), fmt(res["Red"]),
                                       fmt(res["Green"]), fmt(res["Yellow"])))
        rows.append((cx, cy, res))

    # 出图：三态各裁同一灯头
    tiles = []
    for name in ("red", "green", "yellow"):
        p = os.path.join(OUT, "all_%s.png" % name)
        im = cv2.imread(p) if os.path.exists(p) else None
        if im is None:
            continue
        cx, cy, w_, h_ = targets[0][1], targets[0][2], targets[0][3], targets[0][4]
        hw, hh = max(20, w_ // 2 + 16), max(45, h_ // 2 + 30)
        c = im[max(0, cy - hh):cy + hh, max(0, cx - hw):cx + hw]
        if c.size == 0:
            continue
        z = cv2.resize(c, (170, 400), interpolation=cv2.INTER_NEAREST)
        cv2.putText(z, name.upper(), (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2, cv2.LINE_AA)
        tiles.append(z)
    if tiles:
        p = os.path.join(OUT, "three_states_same_lamp.png")
        cv2.imwrite(p, np.hstack(tiles))
        print("\n★ 同一灯头三态对照:", p)

    for t in tls:
        t.freeze(False)
    s.synchronous_mode = False
    s.fixed_delta_seconds = None
    world.apply_settings(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
