"""用纯 ASCII 文件名重做灯珠亮度扫描，并输出「肉眼可核对」的对比图。

关键改动：
  1. 文件名/标签全用 ASCII（中文经 PowerShell→Python 会乱码）
  2. 不再只取 ROI 里最亮一点（那会采到静态高光），
     改为在**整个画面**里找"随灯态变化最大的区域"，再放大给人看
"""
import json
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
LIGHT_ID = 9

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


def render(world, attrs):
    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(W))
    bp.set_attribute("image_size_y", str(H))
    bp.set_attribute("fov", str(FOV))
    for k, v in attrs.items():
        try:
            bp.set_attribute(k, str(v))
        except Exception as e:
            print("    attr fail %s=%s (%s)" % (k, v, e))
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
    client.set_timeout(30.0)
    world = client.get_world()
    tl = None
    for _try in range(40):
        for a in world.get_actors().filter("traffic.traffic_light*"):
            if a.id == LIGHT_ID:
                tl = a
        if tl is not None:
            break
        print("  等待 light %d 出现... (%d)" % (LIGHT_ID, _try + 1))
        time.sleep(1.0)
    if tl is None:
        print("找不到 light %d（场景里共 %d 个红绿灯：%s）"
              % (LIGHT_ID, len(world.get_actors().filter("traffic.traffic_light*")),
                 [a.id for a in world.get_actors().filter("traffic.traffic_light*")][:20]))
        return 1
    print("已找到 light %d" % tl.id)
    s = world.get_settings()
    s.synchronous_mode = True
    s.fixed_delta_seconds = 0.05
    world.apply_settings(s)

    rows = []
    print("%-20s %-10s %-10s %-8s %-8s %s"
          % ("variant", "red_maxV", "green_maxV", "dMaxV", "dArea", "max-diff pixel"))
    for label, attrs in VARIANTS:
        imgs = {}
        for name, st in (("red", carla.TrafficLightState.Red),
                         ("green", carla.TrafficLightState.Green)):
            tl.freeze(True)
            tl.set_state(st)
            for _ in range(6):
                world.tick()
                time.sleep(0.04)
            if str(tl.get_state()) != name.capitalize():
                print("  %s: state not applied" % label)
                imgs = {}
                break
            img = render(world, attrs)
            imgs[name] = img
            cv2.imwrite(os.path.join(OUT, "%s_%s.png" % (label, name)), img)
        if len(imgs) != 2:
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
                     "red_v": int(g_r[y, x]), "green_v": int(g_g[y, x])})
        print("%-20s %-10d %-10d %-8d %-8d (%4d,%4d) red=%s green=%s"
              % (label, int(g_r.max()), int(g_g.max()), dmax, darea, x, y, p_r, p_g))

    with open(os.path.join(OUT, "sweep.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    rows.sort(key=lambda r: -r["dmax"])
    print("\n按 dMaxV 排序（灯态可分性，越大越好）:")
    for r in rows:
        print("   %-20s dMaxV=%-4d dArea=%-6d 红态%s 绿态%s  attrs=%s"
              % (r["label"], r["dmax"], r["darea"], r["red_bgr"], r["green_bgr"], r["attrs"]))

    # ==== 出图：最优 4 个变体，把"差异最大处"放大，红/绿并排 ====
    lines = []
    for r in rows[:4]:
        x, y = r["xy"]
        m = 40
        y0, y1 = max(0, y - m), min(H, y + m)
        x0, x1 = max(0, x - m), min(W, x + m)
        for name in ("red", "green"):
            im = cv2.imread(os.path.join(OUT, "%s_%s.png" % (r["label"], name)))
            c = im[y0:y1, x0:x1] if im is not None else None
            if c is None or c.size == 0:
                continue
            z = cv2.resize(c, (200, 200), interpolation=cv2.INTER_NEAREST)
            # 框出差异点
            cv2.drawMarker(z, (int((x - x0) * 200 / max(1, x1 - x0)),
                               int((y - y0) * 200 / max(1, y1 - y0))),
                           (255, 0, 255), cv2.MARKER_CROSS, 22, 2)
            col = (0, 0, 255) if name == "red" else (0, 255, 0)
            cv2.putText(z, "%s %s" % (r["label"][:14], name.upper()), (3, 15),
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
        print("\n红/绿灯珠对照图:", p)

    tl.freeze(False)
    s.synchronous_mode = False
    s.fixed_delta_seconds = None
    world.apply_settings(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
