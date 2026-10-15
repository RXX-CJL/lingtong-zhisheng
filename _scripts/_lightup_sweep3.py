"""① 让信号灯珠亮起来 —— 扫相机后处理参数（重启免疫版）

改动要点（吸取的教训）：
  1. **不硬编码红绿灯 ID** —— CARLA 重启后 ID 会重新分配（9/15/17 → 60..）。
     改为按**地理位置**找：离已知 mast 位置最近的灯。
  2. 文件名/标签全 ASCII（中文经 PowerShell→Python 会乱码）。
  3. 除了"最亮像素"，还统计"随灯态变化的像素面积/最大差"，避免采到静态高光。
"""
import json
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

# 情报：控制 road 7 lane 1/2 的灯，其 mast 位于此（不是 ID）
KNOWN_MAST = (-46.17, -73.56)      # 旧场景 light 9 的 actor 位置
KNOWN_STOP = (-25.61, -64.76)      # 它的停止线

VARIANTS = [
    ("A_default", {}),
    ("B_exp0p5", {"exposure_compensation": 0.5}),
    ("C_exp1p5", {"exposure_compensation": 1.5}),
    ("D_exp3p0", {"exposure_compensation": 3.0}),
    ("E_bloom3", {"bloom_intensity": 3.0}),
    ("F_bloom6", {"bloom_intensity": 6.0}),
    ("G_exp1p5_bloom3", {"exposure_compensation": 1.5, "bloom_intensity": 3.0}),
    ("H_gamma1p6", {"gamma": 1.6}),
    ("I_manual_exp1p5", {"exposure_mode": "manual", "exposure_compensation": 1.5}),
]


def find_light(world):
    """按地理位置找控制我们进口道的那盏灯（对 CARLA 重启免疫）。"""
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


def render(world, attrs):
    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(W))
    bp.set_attribute("image_size_y", str(H))
    bp.set_attribute("fov", str(FOV))
    for k, v in attrs.items():
        try:
            bp.set_attribute(k, str(v))
        except Exception as e:
            print("      attr fail %s=%s (%s)" % (k, v, e))
    cam = world.spawn_actor(bp, carla.Transform(CAM1, ROT1))
    got = []
    cam.listen(lambda im: got.append(im))
    for _ in range(6):
        world.tick()
        time.sleep(0.04)
    time.sleep(0.5)
    cam.stop()
    cam.destroy()
    return np.frombuffer(got[-1].raw_data, np.uint8).reshape(H, W, 4)[:, :, :3].copy()


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(60.0)
    world = client.get_world()
    if len(world.get_actors().filter("traffic.traffic_light*")) == 0:
        print("交通灯为 0，重新加载地图 ...")
        world = client.load_world("Town10HD_Opt")
        time.sleep(3)
    print("地图=%s  交通灯=%d" % (world.get_map().name,
                                 len(world.get_actors().filter("traffic.traffic_light*"))))

    found = find_light(world)
    if found is None:
        print("找不到灯")
        return 1
    score, tl, d_mast, d_stop = found
    print("按地理定位选中 light id=%d（距已知 mast %.1f m，距已知停止线 %.1f m）"
          % (tl.id, d_mast, d_stop))
    print("  actor loc=(%.2f,%.2f,%.2f)" % (tl.get_transform().location.x,
                                            tl.get_transform().location.y,
                                            tl.get_transform().location.z))

    s = world.get_settings()
    s.synchronous_mode = True
    s.fixed_delta_seconds = 0.05
    world.apply_settings(s)

    rows = []
    print("\n%-20s %-10s %-10s %-8s %-9s %s"
          % ("variant", "red_maxV", "green_maxV", "dMaxV", "dArea>25", "max-diff pixel"))
    for label, attrs in VARIANTS:
        imgs = {}
        ok = True
        for name, st in (("red", carla.TrafficLightState.Red),
                         ("green", carla.TrafficLightState.Green)):
            tl.freeze(True)
            tl.set_state(st)
            for _ in range(6):
                world.tick()
                time.sleep(0.04)
            if str(tl.get_state()).lower() != name:
                print("  %-20s state not applied (%s)" % (label, tl.get_state()))
                ok = False
                break
            img = render(world, attrs)
            imgs[name] = img
            cv2.imwrite(os.path.join(OUT, "%s_%s.png" % (label, name)), img)
        if not ok:
            continue
        g_r = cv2.cvtColor(imgs["red"], cv2.COLOR_BGR2GRAY).astype(np.int16)
        g_g = cv2.cvtColor(imgs["green"], cv2.COLOR_BGR2GRAY).astype(np.int16)
        diff = np.abs(g_r - g_g)
        dmax = int(diff.max())
        darea = int((diff > 25).sum())
        y, x = np.unravel_index(int(np.argmax(diff)), diff.shape)
        p_r = [int(imgs["red"][y, x, i]) for i in range(3)]
        p_g = [int(imgs["green"][y, x, i]) for i in range(3)]
        rows.append({"label": label, "attrs": attrs, "dmax": dmax, "darea": darea,
                     "xy": [int(x), int(y)], "red_bgr": p_r, "green_bgr": p_g,
                     "red_v": int(g_r[y, x]), "green_v": int(g_g[y, x]),
                     "img_max": int(g_r.max())})
        print("%-20s %-10d %-10d %-8d %-9d (%4d,%4d) red=%s green=%s"
              % (label, int(g_r.max()), int(g_g.max()), dmax, darea, x, y, p_r, p_g))

    with open(os.path.join(OUT, "sweep.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    rows.sort(key=lambda r: -r["dmax"])
    print("\n按灯态可分性 dMaxV 排序:")
    for r in rows:
        print("   %-20s dMaxV=%-4d dArea=%-6d 红态%s 绿态%s"
              % (r["label"], r["dmax"], r["darea"], r["red_bgr"], r["green_bgr"]))

    # 出图：最优 4 组的差异点放大，红/绿并排
    lines = []
    for r in rows[:4]:
        x, y = r["xy"]
        m = 40
        y0, y1 = max(0, y - m), min(H, y + m)
        x0, x1 = max(0, x - m), min(W, x + m)
        for name in ("red", "green"):
            p = os.path.join(OUT, "%s_%s.png" % (r["label"], name))
            im = cv2.imread(p) if os.path.exists(p) else None
            if im is None:
                continue
            c = im[y0:y1, x0:x1]
            if c.size == 0:
                continue
            z = cv2.resize(c, (200, 200), interpolation=cv2.INTER_NEAREST)
            cv2.drawMarker(z, (int((x - x0) * 200 / max(1, x1 - x0)),
                               int((y - y0) * 200 / max(1, y1 - y0))),
                           (255, 0, 255), cv2.MARKER_CROSS, 22, 2)
            col = (0, 0, 255) if name == "red" else (0, 255, 0)
            cv2.putText(z, "%s %s" % (r["label"][:12], name.upper()), (3, 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, col, 1, cv2.LINE_AA)
            cv2.putText(z, "dMaxV=%d" % r["dmax"], (3, 194), cv2.FONT_HERSHEY_SIMPLEX,
                        0.40, (0, 255, 255), 1, cv2.LINE_AA)
            lines.append(z)
    if lines:
        while len(lines) % 4:
            lines.append(np.zeros((200, 200, 3), np.uint8))
        sheet = np.vstack([np.hstack(lines[i:i + 4]) for i in range(0, len(lines), 4)])
        p = os.path.join(OUT, "lamp_red_vs_green_best.png")
        cv2.imwrite(p, sheet)
        print("\n★ 红/绿灯珠对照图:", p)

    tl.freeze(False)
    s.synchronous_mode = False
    s.fixed_delta_seconds = None
    world.apply_settings(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
