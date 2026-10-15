"""① 让信号灯珠亮起来：扫客户端相机后处理参数。

对每组参数，分别在 Red / Green 两个锁定相位下渲染 CAM-1 视图，
量出"灯珠最亮像素"的差异（目标 >= 60 灰阶），并输出对比图供人工核对。

判据（三项都要看）：
  * ΔV  = 红灯态灯珠亮度 − 绿灯态灯珠亮度     （相位可分性）
  * 红珠 BGR 的 R 是否明显高于 G/B           （颜色正确性）
  * 灯珠亮度 vs 路面亮度                      （是否可见）
"""
import json
import math
import os
import sys
import time

import numpy as np
import carla
import cv2

OUT = r"E:\output\_lightup"
os.makedirs(OUT, exist_ok=True)
W, H, FOV = 1920, 1080, 90.0
CAM1 = carla.Location(x=-15.720, y=-63.145, z=5.732)
ROT1 = carla.Rotation(pitch=-23.445, yaw=179.536, roll=0.0)
LIGHT_ID = 9
# 端到端里 YOLO 稳定框住的灯头位置（视频帧坐标），用作灯珠 ROI
LAMP_ROIS = [(1644, 901, 1660, 941), (998, 122, 1017, 170), (1770, 901, 1787, 944)]

VARIANTS = [
    ("默认(基线)", {}),
    ("曝光+0.5(当前)", {"exposure_compensation": 0.5}),
    ("曝光+1.5", {"exposure_compensation": 1.5}),
    ("曝光+3.0", {"exposure_compensation": 3.0}),
    ("自动曝光", {"exposure_mode": "manual", "exposure_compensation": 1.5}),
    ("bloom=3", {"bloom_intensity": 3.0}),
    ("bloom=6", {"bloom_intensity": 6.0}),
    ("曝光+1.5+bloom=3", {"exposure_compensation": 1.5, "bloom_intensity": 3.0}),
    ("曝光+1.5+bloom=6", {"exposure_compensation": 1.5, "bloom_intensity": 6.0}),
    ("gamma=1.6", {"gamma": 1.6}),
    ("gamma=1.6+曝光+1.5", {"gamma": 1.6, "exposure_compensation": 1.5}),
]


def render(world, attrs):
    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(W))
    bp.set_attribute("image_size_y", str(H))
    bp.set_attribute("fov", str(FOV))
    ok, bad = [], []
    for k, v in attrs.items():
        try:
            bp.set_attribute(k, str(v))
            ok.append("%s=%s" % (k, v))
        except Exception as e:
            bad.append("%s(%s)" % (k, e))
    cam = world.spawn_actor(bp, carla.Transform(CAM1, ROT1))
    got = []
    cam.listen(lambda im: got.append(im))
    for _ in range(6):
        world.tick()
        time.sleep(0.04)
    time.sleep(0.5)
    cam.stop()
    cam.destroy()
    img = np.frombuffer(got[-1].raw_data, np.uint8).reshape(H, W, 4)[:, :, :3].copy()
    return img, ok, bad


def lamp_stats(img):
    """在三个 ROI 里取最亮像素，返回 (最大亮度, 对应BGR, 该ROI的R主导度)"""
    best = None
    for (x1, y1, x2, y2) in LAMP_ROIS:
        roi = img[y1:y2, x1:x2]
        if roi.size == 0:
            continue
        g = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        y, x = np.unravel_index(int(np.argmax(g)), g.shape)
        pb, pg, pr = [int(roi[y, x, i]) for i in range(3)]
        v = int(g[y, x])
        if best is None or v > best[0]:
            best = (v, (pb, pg, pr), (x1 + x, y1 + y))
    return best


def road_v(img):
    """路面亮度参考（画面下部中央 200x100）"""
    r = img[int(H * 0.75):int(H * 0.85), int(W * 0.4):int(W * 0.6)]
    return float(cv2.cvtColor(r, cv2.COLOR_BGR2GRAY).mean())


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(30.0)
    world = client.get_world()
    tl = None
    for a in world.get_actors().filter("traffic.traffic_light*"):
        if a.id == LIGHT_ID:
            tl = a
    if tl is None:
        print("找不到 light", LIGHT_ID)
        return 1
    s = world.get_settings()
    s.synchronous_mode = True
    s.fixed_delta_seconds = 0.05
    world.apply_settings(s)

    rows = []
    tiles = []
    print("%-22s %-26s %-26s %-8s %-8s %s"
          % ("参数", "红灯态灯珠 峰值BGR@V", "绿灯态灯珠 峰值BGR@V", "ΔV", "路面V", "红珠R主导"))
    for label, attrs in VARIANTS:
        pair = {}
        for name, st in (("Red", carla.TrafficLightState.Red),
                         ("Green", carla.TrafficLightState.Green)):
            tl.freeze(True)
            tl.set_state(st)
            for _ in range(6):
                world.tick()
                time.sleep(0.04)
            if str(tl.get_state()) != name:
                pair = None
                break
            img, ok, bad = render(world, attrs)
            pair[name] = img
            if name == "Red":
                cv2.imwrite(os.path.join(OUT, "cfg_%s_red.png" % label.replace("+", "p").replace("=", "").replace("(", "").replace(")", "").replace(" ", "_")), img)
        if not pair:
            print("  %-22s 状态设置失败" % label)
            continue
        rs = lamp_stats(pair["Red"])
        gs = lamp_stats(pair["Green"])
        if rs is None or gs is None:
            continue
        dv = rs[0] - gs[0]
        rv = road_v(pair["Red"])
        pb, pg, pr = rs[1]
        r_dom = pr - max(pb, pg)
        applied = ", ".join("%s=%s" % kv for kv in attrs.items()) or "(默认)"
        print("%-22s (%3d,%3d,%3d) V=%-4d @(%4d,%4d)  (%3d,%3d,%3d) V=%-4d  %-8d %-8.0f %+d"
              % (label, pb, pg, pr, rs[0], rs[2][0], rs[2][1],
                 gs[1][0], gs[1][1], gs[1][2], gs[0], dv, rv, r_dom))
        rows.append({"label": label, "attrs": attrs, "red": {"v": rs[0], "bgr": list(rs[1]), "xy": list(rs[2])},
                     "green": {"v": gs[0], "bgr": list(gs[1])}, "dV": dv, "road_v": rv, "r_dom": r_dom})
        # 拼图：每行 = 红/绿 两个灯珠放大
        for tag, img, st_ in (("R", pair["Red"], rs), ("G", pair["Green"], gs)):
            x, y = (st_[2] if tag == "R" else rs[2])
            m = 30
            y0, y1 = max(0, y - m), min(H, y + m)
            x0, x1 = max(0, x - m), min(W, x + m)
            c = img[y0:y1, x0:x1].copy()
            z = cv2.resize(c, (170, 170), interpolation=cv2.INTER_NEAREST) if c.size else np.zeros((170, 170, 3), np.uint8)
            cv2.putText(z, "%s %s V=%d" % (label[:14], tag, st_[0]), (3, 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 255), 1, cv2.LINE_AA)
            tiles.append(z)

    with open(os.path.join(OUT, "sweep.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    # 按 ΔV 排序，给出对比图
    rows_sorted = sorted(rows, key=lambda r: -r["dV"])
    print("\n按 ΔV 排序（越大越可分）:")
    for r in rows_sorted[:6]:
        print("   %-22s ΔV=%-5d 红珠(%3d,%3d,%3d) R主导%+d 路面V=%.0f"
              % (r["label"], r["dV"], r["red"]["bgr"][0], r["red"]["bgr"][1], r["red"]["bgr"][2],
                 r["r_dom"], r["road_v"]))

    # 拼图：最优 5 组的红/绿对照
    sel = rows_sorted[:5]
    lines = []
    for r in sel:
        lab = r["label"]
        f1 = os.path.join(OUT, "cfg_%s_red.png" % lab.replace("+", "p").replace("=", "").replace("(", "").replace(")", "").replace(" ", "_"))
        if not os.path.exists(f1):
            continue
        # 用相同 ROI 从红/绿图里各裁一块
        img_r = cv2.imread(f1)
        x, y = r["red"]["xy"]
        m = 34
        y0, y1 = max(0, y - m), min(H, y + m)
        x0, x1 = max(0, x - m), min(W, x + m)
        c = img_r[y0:y1, x0:x1]
        if c.size:
            z = cv2.resize(c, (150, 150), interpolation=cv2.INTER_NEAREST)
            cv2.putText(z, "%s" % lab[:18], (3, 13), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(z, "dV=%d V=%d" % (r["dV"], r["red"]["v"]), (3, 146), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 255, 0), 1, cv2.LINE_AA)
            lines.append(z)
    if lines:
        while len(lines) % 5:
            lines.append(np.zeros((150, 150, 3), np.uint8))
        p = os.path.join(OUT, "best_candidates.png")
        cv2.imwrite(p, np.hstack(lines))
        print("\n候选对比图:", p)

    if tiles:
        cols = 6
        while len(tiles) % cols:
            tiles.append(np.zeros((170, 170, 3), np.uint8))
        sheet = np.vstack([np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)])
        cv2.imwrite(os.path.join(OUT, "all_variants_lamps.png"), sheet)
        print("全部变体灯珠拼图:", os.path.join(OUT, "all_variants_lamps.png"))

    tl.freeze(False)
    s.synchronous_mode = False
    s.fixed_delta_seconds = None
    world.apply_settings(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
