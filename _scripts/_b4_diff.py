"""B4 一锤定音：帧差值法判定"点亮镜片的真实颜色"。

按上一会话的建议：
  1. 同一相机、同一 tick 序列下，分别抓 Red 态与 Green 态（可复现）
  2. diff = |Red - Green|，**低阈值**找变化区域（排除静止灯箱）
  3. 看变化区域的**绝对色值** —— 那才是点亮镜片的真实颜色
  4. 同时用"ext 最薄轴"判定灯面法线，把相机放在正前方
"""
import json
import math
import os
import sys
import time

import numpy as np
import carla
import cv2

OUT = r"E:\output\_b4"
os.makedirs(OUT, exist_ok=True)
W, H, FOV = 1920, 1080, 90.0
CAM1 = carla.Location(x=-15.720, y=-63.145, z=5.732)
ROT1 = carla.Rotation(pitch=-23.445, yaw=179.536, roll=0.0)
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
        score = d_stop * 2.0 + d_mast * 0.5
        if best is None or score < best[0]:
            best = (score, a, d_mast, d_stop)
    return best


def render(world, cam_tf, extra=None):
    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(W))
    bp.set_attribute("image_size_y", str(H))
    bp.set_attribute("fov", str(FOV))
    for k, v in (extra or {}).items():
        try:
            bp.set_attribute(k, str(v))
        except Exception:
            pass
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


def analyse_pair(red, green, tag):
    """低阈值差值，列出变化区域及其绝对色值。"""
    d = cv2.absdiff(red, green).max(axis=2)
    print("\n===== %s =====" % tag)
    for thr in (5, 10, 15, 25):
        mm = (d > thr).astype(np.uint8)
        n = int(mm.sum())
        print("  阈值>%-3d 变化像素=%-7d" % (thr, n))
        if n == 0:
            continue
        # 连通块
        mm2 = cv2.morphologyEx(mm * 255, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        nc, lab, st, ce = cv2.connectedComponentsWithStats(mm2, 8)
        blobs = sorted([(int(st[i, cv2.CC_STAT_AREA]), int(ce[i][0]), int(ce[i][1]),
                         int(st[i, cv2.CC_STAT_WIDTH]), int(st[i, cv2.CC_STAT_HEIGHT]))
                        for i in range(1, nc)], reverse=True)[:6]
        for a, cx, cy, bw, bh in blobs:
            roi_mask = (lab == 0)
            # 该块内的像素：取红态与绿态在该块的平均色
            sel = np.zeros_like(mm, dtype=bool)
            idx = None
            for i in range(1, nc):
                if (int(st[i, cv2.CC_STAT_AREA]) == a and int(ce[i][0]) == cx
                        and int(ce[i][1]) == cy):
                    idx = i
                    break
            if idx is None:
                continue
            sel = (lab == idx)
            rb, rg, rr = [float(red[:, :, k][sel].mean()) for k in range(3)]
            gb, gg, gr = [float(green[:, :, k][sel].mean()) for k in range(3)]
            def hue_of(b, g, r):
                hsv = cv2.cvtColor(np.uint8([[[int(b), int(g), int(r)]]]), cv2.COLOR_BGR2HSV)[0, 0]
                return int(hsv[0]) * 2, int(hsv[1]), int(hsv[2])
            hR, sR, vR = hue_of(rb, rg, rr)
            hG, sG, vG = hue_of(gb, gg, gr)
            print("     块 a=%-5d @(%4d,%4d) %3dx%-3d" % (a, cx, cy, bw, bh))
            print("        红态均色 BGR=(%5.1f,%5.1f,%5.1f) hue=%-3d sat=%-3d V=%-3d" % (rb, rg, rr, hR, sR, vR))
            print("        绿态均色 BGR=(%5.1f,%5.1f,%5.1f) hue=%-3d sat=%-3d V=%-3d" % (gb, gg, gr, hG, sG, vG))
    return d


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(60.0)
    world = client.get_world()
    if len(world.get_actors().filter("traffic.traffic_light*")) == 0:
        print("交通灯为 0，load_world ...")
        world = client.load_world("Town10HD_Opt")
        time.sleep(3)
    print("地图=%s 交通灯=%d" % (world.get_map().name,
                                len(world.get_actors().filter("traffic.traffic_light*"))))
    found = find_light(world)
    score, tl, d_mast, d_stop = found
    atf = tl.get_transform()
    print("选中 light id=%d  actor loc=(%.2f,%.2f,%.2f) yaw=%.1f  (距mast %.1f m, 距停止线 %.1f m)"
          % (tl.id, atf.location.x, atf.location.y, atf.location.z, atf.rotation.yaw, d_mast, d_stop))

    # 用 ext 最薄轴确定灯面法线（上一会话的教训）
    print("\n灯箱与法线（ext 最薄轴 = 法线方向）:")
    heads = []
    for i, b in enumerate(tl.get_light_boxes()):
        if max(b.extent.x, b.extent.y) > 2.0:
            continue
        ext = np.array([b.extent.x, b.extent.y, b.extent.z])
        thin = int(np.argmin(ext))
        axis = "XYZ"[thin]
        raw = np.array([b.location.x, b.location.y, b.location.z])
        heads.append((i, raw, ext, axis))
        print("   #%d world=(%8.2f,%8.2f,%6.2f) ext=(%.2f,%.2f,%.2f) 最薄轴=%s"
              % (i, raw[0], raw[1], raw[2], ext[0], ext[1], ext[2], axis))

    s = world.get_settings()
    s.synchronous_mode = True
    s.fixed_delta_seconds = 0.05
    world.apply_settings(s)

    # 观测 A：用户机位（平视）
    print("\n----- 观测 A：用户机位（CAM1，平视）-----")
    pair = {}
    for name, st in (("red", carla.TrafficLightState.Red),
                     ("green", carla.TrafficLightState.Green)):
        tl.freeze(True)
        tl.set_state(st)
        for _ in range(6):
            world.tick()
            time.sleep(0.04)
        if str(tl.get_state()).lower() != name:
            print("  %s 未生效" % name)
        pair[name] = render(world, carla.Transform(CAM1, ROT1))
        cv2.imwrite(os.path.join(OUT, "A_%s.png" % name), pair[name])
        print("  %s 帧全图均值 BGR=%s" % (name,
              [round(float(pair[name][:, :, k].mean()), 2) for k in range(3)]))
    dA = analyse_pair(pair["red"], pair["green"], "A 用户机位 差值分析")
    cv2.imwrite(os.path.join(OUT, "A_diff.png"),
                cv2.applyColorMap(np.clip(dA * 6, 0, 255).astype(np.uint8), cv2.COLORMAP_JET))

    # 观测 B：灯正前方 6 m（按法线选方向：+X 与 -X 各试）
    print("\n----- 观测 B：灯正前方 6 m -----")
    tgt = heads[0][1] if heads else np.array([-45.74, -64.26, 5.15])
    for sign, lbl in ((+1.0, "plusX"), (-1.0, "minusX")):
        loc = carla.Location(x=float(tgt[0] + sign * 6.0), y=float(tgt[1]), z=float(tgt[2]))
        rot = carla.Rotation(pitch=0.0, yaw=180.0 if sign > 0 else 0.0, roll=0.0)
        pr = {}
        for name, st in (("red", carla.TrafficLightState.Red),
                         ("green", carla.TrafficLightState.Green)):
            tl.freeze(True)
            tl.set_state(st)
            for _ in range(6):
                world.tick()
                time.sleep(0.04)
            pr[name] = render(world, carla.Transform(loc, rot))
            cv2.imwrite(os.path.join(OUT, "B_%s_%s.png" % (lbl, name)), pr[name])
        d = cv2.absdiff(pr["red"], pr["green"]).max(axis=2)
        print("  %s: 变化像素 >5 =%d, >25 =%d" % (lbl, int((d > 5).sum()), int((d > 25).sum())))
        if int((d > 5).sum()) > 0:
            ys, xs = np.nonzero(d > 5)
            print("      变化区 bbox x %d..%d y %d..%d" % (xs.min(), xs.max(), ys.min(), ys.max()))
            sel = d > 5
            rb, rg, rr = [float(pr["red"][:, :, k][sel].mean()) for k in range(3)]
            gb, gg, gr = [float(pr["green"][:, :, k][sel].mean()) for k in range(3)]
            hR = int(cv2.cvtColor(np.uint8([[[int(rb), int(rg), int(rr)]]]), cv2.COLOR_BGR2HSV)[0, 0][0]) * 2
            hG = int(cv2.cvtColor(np.uint8([[[int(gb), int(gg), int(gr)]]]), cv2.COLOR_BGR2HSV)[0, 0][0]) * 2
            print("      红态变化区均色 BGR=(%.1f,%.1f,%.1f) hue=%d" % (rb, rg, rr, hR))
            print("      绿态变化区均色 BGR=(%.1f,%.1f,%.1f) hue=%d" % (gb, gg, gr, hG))
        cv2.imwrite(os.path.join(OUT, "B_%s_diff.png" % lbl),
                    cv2.applyColorMap(np.clip(d * 6, 0, 255).astype(np.uint8), cv2.COLORMAP_JET))

    tl.freeze(False)
    s.synchronous_mode = False
    s.fixed_delta_seconds = None
    world.apply_settings(s)
    print("\n产出目录:", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
