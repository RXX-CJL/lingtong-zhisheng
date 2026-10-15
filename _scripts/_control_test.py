"""一锤定音：同一帧里放「确定的红物体 + 确定的绿物体 + 红绿灯(钉红)」，三者同时测量。

三种可能的结果与含义：
  * 红物体红、绿物体绿、**红绿灯蓝**   -> 红绿灯资产/材质问题（不是渲染管线）
  * 红物体**蓝**、绿物体绿             -> 渲染管线/相机通道问题
  * 三者都正常                        -> 之前测法有误（看到的是灯箱）

红/绿对照物用 CARLA 自带的可着色道具：`static.prop.streetbarrier`（橙）、
以及用**车辆蓝本**（车身有固定颜色）——这里优先用`vehicle.*`里已知红/绿车漆的型号，
并且**先用地面平面法把它们的投影位置算出来**，保证取样点正确。
"""
import math
import os
import sys
import time

import numpy as np
import carla
import cv2

OUT = r"E:\output\_control"
os.makedirs(OUT, exist_ok=True)
W, H, FOV = 1920, 1080, 90.0
CAM_LOC = np.array([-15.720, -63.145, 5.732])
CAM_PITCH, CAM_YAW = -23.445, 179.536
KNOWN_MAST = (-46.17, -73.56)
KNOWN_STOP = (-25.61, -64.76)


def proj(p):
    p_, y_ = math.radians(CAM_PITCH), math.radians(CAM_YAW)
    cp, sp, cy, sy = math.cos(p_), math.sin(p_), math.cos(y_), math.sin(y_)
    fwd = np.array([cp * cy, cp * sy, -sp])
    right = np.array([-sy, cy, 0.0])
    up = np.array([sp * cy, sp * sy, cp])
    d = np.asarray(p, float) - CAM_LOC
    z = float(d @ fwd)
    if z <= 1e-6:
        return None
    f = W / (2 * math.tan(math.radians(FOV) / 2))
    return (W / 2 + f * float(d @ right) / z, H / 2 - f * float(d @ up) / z, z)


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


def measure(img, pt, half=10, label=""):
    r = proj(pt)
    if r is None:
        return None
    x, y = int(r[0]), int(r[1])
    if not (0 <= x < W and 0 <= y < H):
        return None
    roi = img[max(0, y - half):y + half, max(0, x - half):x + half]
    if roi.size == 0:
        return None
    # 区域内"最饱和"的像素 = 物体本色（避开背景）
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    s = hsv[:, :, 1].astype(np.int16)
    v = hsv[:, :, 2].astype(np.int16)
    score = s.astype(np.int32) * v.astype(np.int32)
    yy, xx = np.unravel_index(int(np.argmax(score)), score.shape)
    b, g, rr = [int(roi[yy, xx, k]) for k in range(3)]
    hh = cv2.cvtColor(np.uint8([[[b, g, rr]]]), cv2.COLOR_BGR2HSV)[0, 0]
    return {"xy": (x, y), "bgr": (b, g, rr), "hue": int(hh[0]) * 2,
            "sat": int(hh[1]), "val": int(hh[2])}


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(60.0)
    world = client.get_world()
    if len(world.get_actors().filter("traffic.traffic_light*")) == 0:
        world = client.load_world("Town10HD_Opt")
        time.sleep(3)
    tl = find_light(world)
    tls = list(world.get_actors().filter("traffic.traffic_light*"))
    print("地图=%s 灯=%d 目标灯 id=%d" % (world.get_map().name, len(tls), tl.id))

    s = world.get_settings()
    s.synchronous_mode = True
    s.fixed_delta_seconds = 0.05
    world.apply_settings(s)

    bl = world.get_blueprint_library()
    spawns = []
    # 相机 yaw≈180 -> 朝向 -X；可见地面带约在 2.3~13.5 m（已用基准物标定）。
    # 所以物体放在距相机约 6 m 处：x≈-25.7，左右各偏 3 m。
    cands = [("red", "vehicle.tesla.model3", np.array([-25.7, -66.0, 0.3])),
             ("green", "vehicle.audi.a2", np.array([-25.7, -60.3, 0.3]))]
    for tag, bp_id, pos in cands:
        r = proj([pos[0], pos[1], 1.2])
        print("  预检 %-6s 投影 = %s" % (tag, "无" if r is None else "(%.0f,%.0f) d=%.1f" % r))
        if r is None or not (0 <= r[0] < W and 0 <= r[1] < H):
            print("      -> 不在画面内，跳过")
            continue
        try:
            bp = bl.filter(bp_id)[0]
            a = world.spawn_actor(bp, carla.Transform(
                carla.Location(x=float(pos[0]), y=float(pos[1]), z=float(pos[2])),
                carla.Rotation(pitch=0, yaw=90.0, roll=0)))
            spawns.append((tag, a, pos))
            print("     已放置 %-6s %-22s at (%.1f,%.1f)" % (tag, bp_id, pos[0], pos[1]))
        except Exception as e:
            print("     放置失败", tag, e)

    # 钉红
    for t in tls:
        t.freeze(True)
        t.set_state(carla.TrafficLightState.Red)
    for _ in range(6):
        world.tick()
        time.sleep(0.04)

    img = render(world)
    cv2.imwrite(os.path.join(OUT, "control_red_state.png"), img)

    print("\n=== 同一帧内三者对照（真值：两个道具分别是红/绿车漆；红绿灯=Red）===")
    print("%-14s %-12s %-34s %s" % ("对象", "投影像素", "实测最饱和像素", "判定"))
    for tag, a, pos in spawns:
        top = a.get_transform().location
        m = measure(img, [top.x, top.y, top.z + 1.0], half=26)
        if m is None:
            print("%-14s 投影不在画面内" % tag)
            continue
        hue = m["hue"]
        nm = ("红" if (hue < 20 or hue >= 340) and m["sat"] >= 50 else
              "绿" if 100 <= hue < 150 and m["sat"] >= 50 else
              "青/蓝" if 180 <= hue < 260 and m["sat"] >= 50 else "灰/低饱和")
        print("%-14s (%5d,%5d)  BGR=(%3d,%3d,%3d) hue=%-3d sat=%-3d -> %s"
              % (tag, m["xy"][0], m["xy"][1], m["bgr"][0], m["bgr"][1], m["bgr"][2],
                 m["hue"], m["sat"], nm))

    # 红绿灯：用 Red/Green 差分锁定，再看绝对色
    for t in tls:
        t.set_state(carla.TrafficLightState.Green)
    for _ in range(6):
        world.tick()
        time.sleep(0.04)
    img_g = render(world)
    cv2.imwrite(os.path.join(OUT, "control_green_state.png"), img_g)
    d = cv2.absdiff(img, img_g).max(axis=2)
    mm = cv2.morphologyEx((d > 25).astype(np.uint8) * 255, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    nc, lab, st, ce = cv2.connectedComponentsWithStats(mm, 8)
    blobs = sorted([(int(st[i, cv2.CC_STAT_AREA]), int(ce[i][0]), int(ce[i][1]))
                    for i in range(1, nc)], reverse=True)[:4]
    print("\n红绿灯（Red vs Green 差分锁定的变化区）:")
    for a, cx, cy in blobs:
        sel = None
        for i in range(1, nc):
            if int(ce[i][0]) == cx and int(ce[i][1]) == cy and int(st[i, cv2.CC_STAT_AREA]) == a:
                sel = (lab == i)
                break
        if sel is None:
            continue
        rb, rg, rr = [float(img[:, :, k][sel].mean()) for k in range(3)]
        gb, gg, gr = [float(img_g[:, :, k][sel].mean()) for k in range(3)]
        hR = cv2.cvtColor(np.uint8([[[int(rb), int(rg), int(rr)]]]), cv2.COLOR_BGR2HSV)[0, 0]
        hG = cv2.cvtColor(np.uint8([[[int(gb), int(gg), int(gr)]]]), cv2.COLOR_BGR2HSV)[0, 0]
        print("   a=%-5d @(%4d,%4d)  Red态 BGR=(%5.1f,%5.1f,%5.1f) hue=%-3d | Green态 BGR=(%5.1f,%5.1f,%5.1f) hue=%d"
              % (a, cx, cy, rb, rg, rr, int(hR[0]) * 2, gb, gg, gr, int(hG[0]) * 2))

    for _, a, _ in spawns:
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
