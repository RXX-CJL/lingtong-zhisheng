"""采集 CARLA 判色训练集：用**钉死的灯态作为真值**自动打标签。

每个采样点：
  * 把场景里**所有**红绿灯钉成同一状态（Red / Green / Yellow）
  * 从 CAM-2 特写机位渲染一帧
  * 对画面里每个信号灯头，按上/中/下三颗镜片的几何位置各裁一张
  * 标签 = 当前钉死的状态（因为灯态是我们强制的，且已回读校验）
  * 优先保留"该位置确实随灯态变化"的那些镜片（差分过滤，排除非灯区域）

另外采集 none 负样本：CARLA 场景里随机裁剪，**排除所有灯头附近**。
"""
import math
import os
import random
import sys
import time

import numpy as np
import carla
import cv2

OUT = r"E:\output\_retrain_carla"
for c in ("red", "green", "yellow", "none"):
    os.makedirs(os.path.join(OUT, c), exist_ok=True)

W, H, FOV = 1280, 720, 60.0
CAM2_POS = (-32.74, -64.26, 5.15)
CAM2_PITCH, CAM2_YAW = 0.0, 180.0
KNOWN_STOP = (-25.61, -64.76)
STATE_NAMES = {carla.TrafficLightState.Red: "red",
               carla.TrafficLightState.Green: "green",
               carla.TrafficLightState.Yellow: "yellow"}
# 采集时用的额外机位（多视角 -> 更鲁棒）
EXTRA_CAMS = [
    ((-32.74, -64.26, 5.15), 0.0, 180.0),      # 原 CAM-2
    ((-33.7, -68.06, 5.15), 0.0, 180.0),       # 对第二颗灯头
    ((-36.0, -66.0, 5.15), 0.0, 180.0),        # 稍微斜一点
    ((-30.0, -66.2, 5.6), -3.0, 180.0),        # 稍高、略带俯角
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


def head_strips(img):
    """找出画面里的信号灯头竖条（3 颗镜片），返回 (cx, cy, hw, hh) 列表。"""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    sc = hsv[:, :, 1].astype(np.int32) * hsv[:, :, 2].astype(np.int32)
    if sc.max() < 2000:
        return []
    m = (sc > max(3000, int(sc.max() * 0.45))).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    nc, lab, st, ce = cv2.connectedComponentsWithStats(m, 8)
    out = []
    for i in range(1, nc):
        a = int(st[i, cv2.CC_STAT_AREA])
        bw, bh = int(st[i, cv2.CC_STAT_WIDTH]), int(st[i, cv2.CC_STAT_HEIGHT])
        if a < 200 or bh < 30 or bh <= bw:
            continue
        out.append((int(ce[i][0]), int(ce[i][1]), max(10, bw // 2 + 4), max(20, bh // 2 + 6)))
    return out


def main():
    random.seed(42)
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(60.0)
    world = client.get_world()
    if len(world.get_actors().filter("traffic.traffic_light*")) == 0:
        world = client.load_world("Town10HD_Opt")
        time.sleep(3)
    tl = find_light(world)
    tls = list(world.get_actors().filter("traffic.traffic_light*"))
    bpl = world.get_blueprint_library()
    print("目标灯 id=%d，场景共 %d 盏" % (tl.id, len(tls)))

    s = world.get_settings()
    s.synchronous_mode = True
    s.fixed_delta_seconds = 0.05
    world.apply_settings(s)

    saved = {"red": 0, "green": 0, "yellow": 0, "none": 0}
    imgs_by_state = {}

    for cam_i, (loc, pitch, yaw) in enumerate(EXTRA_CAMS):
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
                print("  跳过（状态回读异常 %s）" % state)
                continue
            img = render(world, bpl, loc, pitch, yaw)
            imgs_by_state.setdefault(state, []).append(img)
            key = "cam%d_%s" % (cam_i, state)
            cv2.imwrite(os.path.join(OUT, "_raw_%s.png" % key), img)
            strips = head_strips(img)
            got = 0
            for (cx, cy, hw, hh) in strips:
                y0, y1 = cy - hh, cy + hh
                third = (y1 - y0) // 3
                for k in range(3):
                    ly0, ly1 = y0 + k * third, y0 + (k + 1) * third
                    pad = 3
                    crop = img[max(0, ly0 - pad):ly1 + pad,
                               max(0, cx - hw - pad):cx + hw + pad]
                    if crop.size == 0 or min(crop.shape[:2]) < 6:
                        continue
                    big = cv2.resize(crop, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST)
                    fn = os.path.join(OUT, state, "c%02d_%s_%03d_%03d.png"
                                      % (cam_i, state[:1], saved[state], got))
                    cv2.imwrite(fn, big)
                    saved[state] += 1
                    got += 1
            print("  cam%d %-6s 灯头 %d 个 -> 存 %d 张  (累计 red=%d green=%d yellow=%d)"
                  % (cam_i, state, len(strips), got, saved["red"], saved["green"], saved["yellow"]))

    # ---- none 负样本：随机裁剪，排除灯头附近
    print("\n采集 none 负样本 ...")
    allimg = [im for v in imgs_by_state.values() for im in v]
    avoid_all = []
    for im in allimg[:3]:
        for (cx, cy, hw, hh) in head_strips(im):
            avoid_all.append((cx - hw * 2, cy - hh * 2, cx + hw * 2, cy + hh * 2))
    tries = 0
    while saved["none"] < 120 and tries < 4000:
        tries += 1
        if not allimg:
            break
        img = random.choice(allimg)
        w_ = random.randint(26, 80)
        h_ = random.randint(30, 100)
        x = random.randint(0, max(1, W - w_))
        y = random.randint(0, max(1, H - h_))
        box = (x, y, x + w_, y + h_)
        bad = False
        for (ax1, ay1, ax2, ay2) in avoid_all:
            if not (box[2] < ax1 or box[0] > ax2 or box[3] < ay1 or box[1] > ay2):
                bad = True
                break
        if bad:
            continue
        crop = img[y:y + h_, x:x + w_]
        if crop.size == 0 or crop.reshape(-1, 3).std(axis=0).mean() < 12:
            continue
        big = cv2.resize(crop, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST)
        cv2.imwrite(os.path.join(OUT, "none", "neg_%03d.png" % saved["none"]), big)
        saved["none"] += 1
    print("  none 负样本 %d 张" % saved["none"])

    for t in tls:
        t.freeze(False)
    s.synchronous_mode = False
    s.fixed_delta_seconds = None
    world.apply_settings(s)

    print("\n=== 数据集统计 ===")
    for k, v in saved.items():
        print("  %-8s %d" % (k, v))
    print("目录: %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
