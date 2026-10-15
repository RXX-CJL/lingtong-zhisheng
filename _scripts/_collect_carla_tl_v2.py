"""重做采集（修正版）：只裁**被点亮的那颗镜片**，用固定物理尺寸，标签=钉死灯态。

修正了上一版的三个错误：
  1. ❌ 上一版对灯头三颗镜片**都**打当前状态标签 -> 污染（未亮的镜片是中性白）
     ✅ 本版：按亮度选出被点亮的那颗，**只裁它**；未确认点亮的丢弃
  2. ❌ 上一版裁图尺寸随灯头变化
     ✅ 本版：固定裁剪窗口（灯珠物理直径约 8.5cm，在给定机位/分辨率下像素尺寸固定）
  3. ❌ 上一版把"灯珠+灯箱"一起给模型，模型学到灯箱（青蓝）
     ✅ 本版：裁图尽量只含灯珠本身

另外补采 None 负样本。
"""
import math
import os
import random
import sys
import time

import numpy as np
import carla
import cv2

OUT = r"E:\output\_retrain_carla2"
for c in ("red", "green", "yellow", "none"):
    os.makedirs(os.path.join(OUT, c), exist_ok=True)

W, H, FOV = 1280, 720, 60.0
KNOWN_STOP = (-25.61, -64.76)
# 多个机位，增加视角多样性
CAMS = [
    ((-32.74, -64.26, 5.15), 0.0, 180.0),
    ((-33.70, -68.06, 5.15), 0.0, 180.0),
    ((-35.50, -66.20, 5.15), 0.0, 180.0),
    ((-31.00, -66.20, 5.45), -3.0, 180.0),
    ((-30.00, -64.26, 5.80), -5.0, 180.0),
]


def grab(image):
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


def render(world, bpl, loc, pitch, yaw):
    bp = bpl.find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(W))
    bp.set_attribute("image_size_y", str(H))
    bp.set_attribute("fov", str(FOV))
    cam = world.spawn_actor(bp, carla.Transform(
        carla.Location(*loc), carla.Rotation(pitch=pitch, yaw=yaw, roll=0.0)))
    got = []
    cam.listen(lambda im: got.append(im))
    for _ in range(6):
        world.tick()
        time.sleep(0.04)
    time.sleep(0.45)
    cam.stop()
    cam.destroy()
    return grab(got[-1])


def head_boxes(img):
    """找灯头竖条。返回 (cx, cy, hw, hh)。固定用 ext 推导的物理比例。"""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    sc = hsv[:, :, 1].astype(np.int32) * hsv[:, :, 2].astype(np.int32)
    if sc.max() < 1500:
        return []
    m = (sc > max(2500, int(sc.max() * 0.40))).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    nc, lab, st, ce = cv2.connectedComponentsWithStats(m, 8)
    out = []
    for i in range(1, nc):
        a = int(st[i, cv2.CC_STAT_AREA])
        bw, bh = int(st[i, cv2.CC_STAT_WIDTH]), int(st[i, cv2.CC_STAT_HEIGHT])
        if a < 150 or bh < 28 or bh <= bw:
            continue
        out.append((int(ce[i][0]), int(ce[i][1]), bw, bh))
    return out


def lit_lens_crop(img, cx, cy, bw, bh):
    """在灯头里找**被点亮**的那颗镜片，返回固定尺寸的裁图 + 诊断信息。

    判据：
      * 灯头竖条均分三片，取各片"最亮 10% 像素均值"
      * 被点亮的那片最亮，且需与其他片有明显差距（否则视为无法判定，丢弃）
    固定窗：以点亮片的最亮点为中心，窗宽 = 灯头宽 x1.5，窗高 = 片高 x1.1
    """
    hw = max(8, int(bw * 0.75))
    hh = max(14, int(bh * 0.55))
    x0, y0 = max(0, cx - hw), max(0, cy - hh)
    x1, y1 = min(W, cx + hw), min(H, cy + hh)
    roi = img[y0:y1, x0:x1]
    if roi.size == 0:
        return None
    g = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY).astype(np.float32)
    h = g.shape[0]
    third = max(4, h // 3)
    scores = []
    for k in range(3):
        seg = g[k * third:(k + 1) * third] if k < 2 else g[2 * third:]
        if seg.size == 0:
            scores.append(0.0)
            continue
        thr = np.percentile(seg, 90)
        scores.append(float(seg[seg >= thr].mean()))
    lit = int(np.argmax(scores))
    srt = sorted(scores, reverse=True)
    if srt[0] - srt[1] < 3.0:            # 三片亮度接近 -> 无法可靠判定
        return None
    seg_y0 = y0 + lit * third
    seg_y1 = y0 + ((lit + 1) * third if lit < 2 else (y1 - y0))
    seg = img[seg_y0:seg_y1, x0:x1]
    if seg.size == 0:
        return None
    gg = cv2.cvtColor(seg, cv2.COLOR_BGR2GRAY)
    yy, xx = np.unravel_index(int(np.argmax(gg)), gg.shape)
    px, py = x0 + xx, seg_y0 + yy
    # 固定窗（像素尺寸固定，不随灯头大小变）
    cw, ch = 26, 22
    a0, b0 = max(0, px - cw // 2), max(0, py - ch // 2)
    a1, b1 = min(W, a0 + cw), min(H, b0 + ch)
    crop = img[b0:b1, a0:a1]
    if crop.size == 0:
        return None
    pb, pg, pr = [int(img[py, px, k]) for k in range(3)]
    hsvp = cv2.cvtColor(np.uint8([[[pb, pg, pr]]]), cv2.COLOR_BGR2HSV)[0, 0]
    return {"crop": crop, "lit": lit, "scores": scores,
            "peak": (pb, pg, pr), "hue": int(hsvp[0]) * 2, "sat": int(hsvp[1]),
            "xy": (px, py)}


def main():
    random.seed(7)
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(60.0)
    world = client.get_world()
    if len(world.get_actors().filter("traffic.traffic_light*")) == 0:
        world = client.load_world("Town10HD_Opt")
        time.sleep(3)
    tl = find_light(world)
    tls = list(world.get_actors().filter("traffic.traffic_light*"))
    bpl = world.get_blueprint_library()
    print("目标灯 id=%d，共 %d 盏" % (tl.id, len(tls)))

    s = world.get_settings()
    s.synchronous_mode = True
    s.fixed_delta_seconds = 0.05
    world.apply_settings(s)

    saved = {"red": 0, "green": 0, "yellow": 0, "none": 0}
    stats = {"red": [], "green": [], "yellow": []}
    allimg = []

    for cam_i, (loc, pitch, yaw) in enumerate(CAMS):
        for st in (carla.TrafficLightState.Red, carla.TrafficLightState.Green,
                   carla.TrafficLightState.Yellow):
            for t in tls:
                t.freeze(True)
                t.set_state(st)
            for _ in range(6):
                world.tick()
                time.sleep(0.04)
            state = str(tl.get_state()).lower()
            if state not in ("red", "green", "yellow"):
                continue
            img = render(world, bpl, loc, pitch, yaw)
            allimg.append(img)
            got = 0
            for (cx, cy, bw, bh) in head_boxes(img):
                L = lit_lens_crop(img, cx, cy, bw, bh)
                if L is None:
                    continue
                crop = L["crop"]
                big = cv2.resize(crop, (64, 64), interpolation=cv2.INTER_NEAREST)
                fn = os.path.join(OUT, state, "c%d_%s_%03d.png" % (cam_i, state[:1], saved[state]))
                cv2.imwrite(fn, big)
                stats[state].append((L["lit"], L["peak"], L["hue"], L["sat"]))
                saved[state] += 1
                got += 1
            print("  cam%d %-6s 灯头%d -> 采到 %d 张 (累计 r=%d g=%d y=%d)"
                  % (cam_i, state, len(head_boxes(img)), got,
                     saved["red"], saved["green"], saved["yellow"]))

    # none 负样本
    print("\n采集 none ...")
    avoid = []
    for im in allimg[:4]:
        for (cx, cy, bw, bh) in head_boxes(im):
            avoid.append((cx - bw * 2, cy - bh * 1.5, cx + bw * 2, cy + bh * 1.5))
    tries = 0
    while saved["none"] < 120 and tries < 5000 and allimg:
        tries += 1
        img = random.choice(allimg)
        w_ = random.randint(20, 70)
        h_ = random.randint(20, 70)
        x = random.randint(0, max(1, W - w_))
        y = random.randint(0, max(1, H - h_))
        box = (x, y, x + w_, y + h_)
        if any(not (box[2] < a1 or box[0] > a2 or box[3] < b1 or box[1] > b2)
               for (a1, b1, a2, b2) in avoid):
            continue
        crop = img[y:y + h_, x:x + w_]
        if crop.size == 0 or crop.reshape(-1, 3).std(axis=0).mean() < 12:
            continue
        cv2.imwrite(os.path.join(OUT, "none", "neg_%03d.png" % saved["none"]),
                    cv2.resize(crop, (64, 64), interpolation=cv2.INTER_AREA))
        saved["none"] += 1

    for t in tls:
        t.freeze(False)
    s.synchronous_mode = False
    s.fixed_delta_seconds = None
    world.apply_settings(s)

    print("\n=== 数据集 ===")
    for k, v in saved.items():
        print("  %-8s %d" % (k, v))
    print("\n=== 各态灯珠峰值像素（用于说明可辨识性）===")
    for k, rows in stats.items():
        if not rows:
            continue
        sats = [r[3] for r in rows]
        hues = [r[2] for r in rows]
        print("  %-7s n=%-3d 峰值饱和度 均值%.0f 中位%.0f | 峰值色相 均值%.0f"
              % (k, len(rows), np.mean(sats), np.median(sats), np.mean(hues)))
    print("\n目录: %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
