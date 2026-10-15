"""按"灯面朝东"的推断，在东侧扫近摄机位，并用**红色 + 尺寸吻合**双重判据确认。

判据：
  * 找到红色发光区（色相判据放宽：CARLA 灯珠过曝后偏淡）
  * 该区尺寸接近镜片理论像素（宽 0.40 m、高 1.18 m，fov=60、W=1920）
"""
import json
import math
import os
import sys
import time

import numpy as np
import carla
import cv2

OUT = r"E:\output\_dual_cam"
os.makedirs(OUT, exist_ok=True)
LIGHT_ID = 9
HEADS = {
    "left_lane": [-45.74, -64.26, 5.15],
    "right_lane": [-45.74, -68.06, 5.15],
}
LW, LH = 0.40, 1.18
W, H, FOV = 1920, 1080, 60.0
F = W / (2 * math.tan(math.radians(FOV) / 2))


def red_blob(arr):
    """红色发光区：用通道关系，不用严格色相（灯珠过曝会偏淡）。"""
    b, g, r = [arr[:, :, i].astype(np.int16) for i in range(3)]
    g8 = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    local = cv2.blur(g8, (31, 31))
    m = ((r > g + 12) & (r > b + 25) & (g8 > local + 8)).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    n, lab, stats, cent = cv2.connectedComponentsWithStats(m, 8)
    best = None
    for i in range(1, n):
        a = int(stats[i, cv2.CC_STAT_AREA])
        if best is None or a > best[0]:
            best = (a, cent[i], stats[i])
    return best


def render(world, loc, pitch, yaw):
    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(W))
    bp.set_attribute("image_size_y", str(H))
    bp.set_attribute("fov", str(FOV))
    cam = world.spawn_actor(bp, carla.Transform(loc, carla.Rotation(pitch=pitch, yaw=yaw, roll=0.0)))
    got = []
    cam.listen(lambda im: got.append(im))
    for _ in range(5):
        world.tick()
        time.sleep(0.04)
    time.sleep(0.45)
    cam.stop()
    cam.destroy()
    return np.frombuffer(got[-1].raw_data, np.uint8).reshape(H, W, 4)[:, :, :3].copy()


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(25.0)
    world = client.get_world()
    tl = None
    for a in world.get_actors().filter("traffic.traffic_light*"):
        if a.id == LIGHT_ID:
            tl = a
    tl.freeze(True)
    tl.set_state(carla.TrafficLightState.Red)
    for _ in range(6):
        world.tick()
        time.sleep(0.06)
    print("light =", tl.get_state())
    print("镜片理论像素: %s" % " / ".join(
        ["%.0fm→%.0fx%.0f" % (d, LW * F / d, LH * F / d) for d in (4, 6, 10, 15)]))

    hits = []
    print("\n%-10s %-32s %-6s %-6s %-9s %-11s %s"
          % ("灯头", "相机", "pitch", "yaw", "红区px", "理论px", "评分"))
    for hname, hp in HEADS.items():
        for dist in (4.0, 5.0, 6.0, 8.0, 10.0, 13.0):
            for dy in (0.0, -1.5, 1.5):
                loc = carla.Location(x=float(hp[0] + dist), y=float(hp[1] + dy), z=float(hp[2]))
                yaw = math.degrees(math.atan2(hp[1] - loc.y, hp[0] - loc.x))
                for pitch in (-5.0, 0.0, 5.0):
                    arr = render(world, loc, pitch, yaw)
                    b = red_blob(arr)
                    if not b or b[0] < 12:
                        continue
                    a_, c, st = b
                    bw, bh = int(st[cv2.CC_STAT_WIDTH]), int(st[cv2.CC_STAT_HEIGHT])
                    tw, th = LW * F / dist, LH * F / dist
                    # 评分：宽高都要接近理论
                    err = abs(bw - tw) / max(tw, 1) + abs(bh - th) / max(th, 1)
                    if err > 1.2:
                        continue
                    hits.append({"head": hname, "cam": [round(loc.x, 2), round(loc.y, 2), round(loc.z, 2)],
                                 "pitch": pitch, "yaw": round(yaw, 1), "dist": dist,
                                 "blob": [bw, bh], "theory": [round(tw, 1), round(th, 1)],
                                 "area": a_, "err": round(err, 3),
                                 "px": [int(c[0]), int(c[1])],
                                 "file": os.path.join(OUT, "head_%s_d%.0f_dy%.1f_p%.0f.png" % (hname, dist, dy, pitch))})
                    cv2.imwrite(hits[-1]["file"], arr)
                    print("%-10s (%7.1f,%7.1f,%5.1f) %-6.0f %-6.1f %-9s %-11s %.2f"
                          % (hname, loc.x, loc.y, loc.z, pitch, yaw, "%dx%d" % (bw, bh),
                             "%.0fx%.0f" % (tw, th), err))

    hits.sort(key=lambda d: d["err"])
    if hits:
        best = hits[0]
        print("\n最佳近摄机位: %s cam=%s pitch=%.0f yaw=%.1f" %
              (best["head"], best["cam"], best["pitch"], best["yaw"]))
        print("   红区 %dx%d px（理论 %.0fx%.0f）误差 %.2f" %
              (best["blob"][0], best["blob"][1], best["theory"][0], best["theory"][1], best["err"]))
        print("   样张:", best["file"])
        # 顺带渲染绿/黄，确认同一机位能区分三态
        for st_name, st_val in (("Green", carla.TrafficLightState.Green),
                                ("Yellow", carla.TrafficLightState.Yellow)):
            tl.set_state(st_val)
            for _ in range(5):
                world.tick()
                time.sleep(0.05)
            loc = carla.Location(*best["cam"])
            arr = render(world, loc, best["pitch"], best["yaw"])
            cv2.imwrite(os.path.join(OUT, "head_%s_%s.png" % (best["head"], st_name.lower())), arr)
            print("   已渲染 %s 态样张" % st_name)
    else:
        print("\n没有找到尺寸吻合的机位 —— 说明灯面朝向推断有误，需要换思路")
    with open(os.path.join(OUT, "headcam_final.json"), "w", encoding="utf-8") as f:
        json.dump(hits, f, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
