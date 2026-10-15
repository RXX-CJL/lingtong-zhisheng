"""一刀切开：同一帧里放"已知纯红物体" + 真实红绿灯（钉红），比较两者渲染色。

判据：
  * 红物体 = 红 且 红绿灯 = 青蓝  -> 红绿灯资产/材质问题
  * 红物体 = 红 且 红绿灯 = 红     -> 本次渲染其实是好的（之前测法有误）
  * 红物体 = 青蓝                  -> 渲染管线问题（环境差异）
"""
import math
import os
import sys
import time

import numpy as np
import carla
import cv2

OUT = r"E:\output\_redtest"
os.makedirs(OUT, exist_ok=True)
W, H, FOV = 1280, 720, 90.0
KNOWN_MAST = (-46.17, -73.56)
KNOWN_STOP = (-25.61, -64.76)


def find_light(world):
    best = None
    for a in world.get_actors().filter("traffic.traffic_light*"):
        L = a.get_transform().location
        d_mast = math.dist((L.x, L.y), KNOWN_MAST)
        d_stop = 1e9
        try:
            for wp in a.get_stop_waypoints():
                sl = wp.transform.location
                d_stop = min(d_stop, math.dist((sl.x, sl.y), KNOWN_STOP))
        except Exception:
            pass
        sc = d_stop * 2.0 + d_mast * 0.5
        if best is None or sc < best[0]:
            best = (sc, a, d_mast, d_stop)
    return best


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


def top_colour(img, x0, y0, x1, y1):
    """区域内最亮像素的 BGR"""
    roi = img[y0:y1, x0:x1]
    if roi.size == 0:
        return None
    g = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    y, x = np.unravel_index(int(np.argmax(g)), g.shape)
    b, gg, r = [int(roi[y, x, k]) for k in range(3)]
    hsv = cv2.cvtColor(np.uint8([[[b, gg, r]]]), cv2.COLOR_BGR2HSV)[0, 0]
    return (b, gg, r, int(hsv[0]) * 2, int(hsv[1]), int(g[y, x]))


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(60.0)
    world = client.get_world()
    n_tl = len(world.get_actors().filter("traffic.traffic_light*"))
    print("地图=%s  红绿灯=%d" % (world.get_map().name, n_tl))
    if n_tl == 0:
        world = client.load_world("Town10HD_Opt")
        time.sleep(3)
        print("load_world 后 红绿灯=%d" % len(world.get_actors().filter("traffic.traffic_light*")))

    found = find_light(world)
    tl = found[1]
    print("目标灯 id=%d loc=(%.2f,%.2f,%.2f)" % (tl.id, tl.get_transform().location.x,
                                                 tl.get_transform().location.y,
                                                 tl.get_transform().location.z))

    s = world.get_settings()
    s.synchronous_mode = True
    s.fixed_delta_seconds = 0.05
    world.apply_settings(s)

    # 相机：用户机位；同时在相机正前方 8 m 放一个"纯红测试块"
    cam_loc = carla.Location(x=-15.720, y=-63.145, z=5.732)
    cam_rot = carla.Rotation(pitch=-10.0, yaw=179.536, roll=0.0)  # 稍微抬眼，保证测试块在画面里
    ctf = carla.Transform(cam_loc, cam_rot)

    # 用 vehicle.tesla.model3（车身红）作为"已知红物体"，放在相机正前 10 m
    bl = world.get_blueprint_library()
    red_props = []
    # 1) 纯红测试块：用 traffic cone / 静态道具不保证红色，改用 actor 的明确红色车
    bp_car = bl.filter("vehicle.tesla.model3")[0]
    fwd = np.array([math.cos(math.radians(cam_rot.yaw)), math.sin(math.radians(cam_rot.yaw)), 0.0])
    car_loc = np.array([cam_loc.x, cam_loc.y, cam_loc.z]) + fwd * 10.0
    try:
        car = world.spawn_actor(bp_car, carla.Transform(
            carla.Location(x=float(car_loc[0]), y=float(car_loc[1]), z=0.4),
            carla.Rotation(pitch=0, yaw=cam_rot.yaw + 90, roll=0)))
        red_props.append(("red_car_tesla", car))
        print("已放置红色特斯拉 at (%.1f,%.1f)" % (car_loc[0], car_loc[1]))
    except Exception as e:
        print("放置失败:", e)

    # 钉红
    tl.freeze(True)
    tl.set_state(carla.TrafficLightState.Red)
    for _ in range(6):
        world.tick()
        time.sleep(0.04)
    print("light state =", tl.get_state())

    img = render(world, ctf)
    cv2.imwrite(os.path.join(OUT, "redtest_red.png"), img)

    # 找红色特斯拉的位置（画面下半部最红的块）
    b, g, r = [img[:, :, i].astype(np.int16) for i in range(3)]
    redmask = ((r > g + 30) & (r > b + 30) & (r > 80)).astype(np.uint8)
    print("\n【已知红物体】全图 强红像素 = %d" % int(redmask.sum()))
    if redmask.sum() > 50:
        ys, xs = np.nonzero(redmask)
        print("   红色物体 bbox x %d..%d y %d..%d" % (xs.min(), xs.max(), ys.min(), ys.max()))
        sel = redmask.astype(bool)
        mb, mg, mr = [float(img[:, :, k][sel].mean()) for k in range(3)]
        hsv = cv2.cvtColor(np.uint8([[[int(mb), int(mg), int(mr)]]]), cv2.COLOR_BGR2HSV)[0, 0]
        print("   红物体均色 BGR=(%.1f,%.1f,%.1f) hue=%d sat=%d  <== 关键：它红不红"
              % (mb, mg, mr, int(hsv[0]) * 2, int(hsv[1])))
    else:
        print("   ⚠ 画面里没找到明显的红物体（可能被挡住/位置不对）")

    # 红绿灯：用绿态的帧做差找它
    tl.set_state(carla.TrafficLightState.Green)
    for _ in range(6):
        world.tick()
        time.sleep(0.04)
    img_g = render(world, ctf)
    cv2.imwrite(os.path.join(OUT, "redtest_green.png"), img_g)

    d = cv2.absdiff(img, img_g).max(axis=2)
    print("\n【红绿灯】红/绿帧差值 >25 的像素 = %d" % int((d > 25).sum()))
    if int((d > 25).sum()) > 0:
        sel = d > 25
        ys, xs = np.nonzero(sel)
        print("   变化区 bbox x %d..%d y %d..%d" % (xs.min(), xs.max(), ys.min(), ys.max()))
        mb, mg, mr = [float(img[:, :, k][sel].mean()) for k in range(3)]
        gb, gg, gr = [float(img_g[:, :, k][sel].mean()) for k in range(3)]
        hR = int(cv2.cvtColor(np.uint8([[[int(mb), int(mg), int(mr)]]]), cv2.COLOR_BGR2HSV)[0, 0][0]) * 2
        hG = int(cv2.cvtColor(np.uint8([[[int(gb), int(gg), int(gr)]]]), cv2.COLOR_BGR2HSV)[0, 0][0]) * 2
        print("   红态 BGR=(%.1f,%.1f,%.1f) hue=%d" % (mb, mg, mr, hR))
        print("   绿态 BGR=(%.1f,%.1f,%.1f) hue=%d" % (gb, gg, gr, hG))
        # 只取最亮的变化块
        mm = cv2.morphologyEx(sel.astype(np.uint8) * 255, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        nc, lab, st, ce = cv2.connectedComponentsWithStats(mm, 8)
        blobs = sorted([(int(st[i, cv2.CC_STAT_AREA]), int(ce[i][0]), int(ce[i][1]))
                        for i in range(1, nc)], reverse=True)[:5]
        print("   最大的几个变化块:")
        for a, cx, cy in blobs:
            def mm_of(im, x, y, hw=6):
                rr = im[max(0, y - hw):y + hw, max(0, x - hw):x + hw]
                if rr.size == 0:
                    return None
                gg2 = cv2.cvtColor(rr, cv2.COLOR_BGR2GRAY)
                yy, xx = np.unravel_index(int(np.argmax(gg2)), gg2.shape)
                pb, pg, pr = [int(rr[yy, xx, k]) for k in range(3)]
                hv = cv2.cvtColor(np.uint8([[[pb, pg, pr]]]), cv2.COLOR_BGR2HSV)[0, 0]
                return (pb, pg, pr, int(hv[0]) * 2)
            cr = mm_of(img, cx, cy)
            cg = mm_of(img_g, cx, cy)
            print("      a=%-4d @(%4d,%4d)  红态峰值 BGR=%s hue=%-3d   绿态峰值 BGR=%s hue=%d"
                  % (a, cx, cy, cr[:3], cr[3], cg[:3], cg[3]))

    for _, a in red_props:
        try:
            a.destroy()
        except Exception:
            pass
    tl.freeze(False)
    s.synchronous_mode = False
    s.fixed_delta_seconds = None
    world.apply_settings(s)
    print("\n产出:", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
