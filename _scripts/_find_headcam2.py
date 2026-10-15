"""为近摄相机定机位：用**亮度**（不是饱和度）找点亮镜片，并核对其像素尺寸是否
符合镜片物理尺寸，从而确定"镜片要多大"。

镜片物理尺寸（light 9 灯箱半轴）：宽 2*0.20=0.40 m，高 2*0.59=1.18 m
→ 在距离 d、fov=60、宽 W 像素时，理论像素高 = 1.18 * (W/(2*tan(30°))) / d
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

# 真实灯头（raw 解释已被多轮验证与像素吻合）
HEADS = [
    ("left_lane", [-45.74, -64.26, 5.15], 0.40, 1.18),
    ("right_lane", [-45.74, -68.06, 5.15], 0.40, 1.18),
]


def bright_blob(arr, pct=99.0):
    """最大"比周围亮"的紧凑连通域 —— 不依赖饱和度。"""
    g = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    local = cv2.blur(g, (25, 25))
    m = ((g - local) > 18).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    n, lab, stats, cent = cv2.connectedComponentsWithStats(m, 8)
    best = None
    for i in range(1, n):
        a = int(stats[i, cv2.CC_STAT_AREA])
        if best is None or a > best[0]:
            best = (a, cent[i], stats[i])
    return best


def render(world, loc, rot, w, h, fov):
    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(w))
    bp.set_attribute("image_size_y", str(h))
    bp.set_attribute("fov", str(fov))
    cam = world.spawn_actor(bp, carla.Transform(loc, rot))
    got = []
    cam.listen(lambda im: got.append(im))
    for _ in range(5):
        world.tick()
        time.sleep(0.04)
    time.sleep(0.45)
    cam.stop()
    cam.destroy()
    return np.frombuffer(got[-1].raw_data, np.uint8).reshape(h, w, 4)[:, :, :3].copy()


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
    print("light %d = %s" % (tl.id, tl.get_state()))

    W, H, FOV = 1920, 1080, 60.0
    f = W / (2 * math.tan(math.radians(FOV) / 2))
    print("近摄规格 %dx%d fov=%.0f -> f=%.0f px" % (W, H, FOV, f))
    print("\n理论：距离 d 时，镜片(1.18m 高)占 %s" % " / ".join(
        ["%.0fm→%.0fpx" % (d, 1.18 * f / d) for d in (3, 5, 8, 12, 20)]))
    print("\n搜索机位（按最亮连通域尺寸评分）:")
    print("  %-11s %-34s %-7s %-9s %-11s %s"
          % ("灯头", "相机 (x,y,z)", "yaw", "亮区px", "理论镜片px", "画面占比"))

    results = []
    for hname, hp, lw, lh in HEADS:
        for dist in (4.0, 6.0, 8.0, 12.0, 18.0):
            for ang in range(0, 360, 30):
                r = math.radians(ang)
                loc = carla.Location(x=float(hp[0] + math.cos(r) * dist),
                                     y=float(hp[1] + math.sin(r) * dist),
                                     z=float(hp[2] + 0.3))
                yaw = math.degrees(math.atan2(hp[1] - loc.y, hp[0] - loc.x))
                arr = render(world, loc, carla.Rotation(pitch=-3.0, yaw=yaw, roll=0.0), W, H, FOV)
                b = bright_blob(arr)
                if not b or b[0] < 30:
                    continue
                a_, c, st = b
                bw, bh = int(st[cv2.CC_STAT_WIDTH]), int(st[cv2.CC_STAT_HEIGHT])
                theory_h = lh * f / dist
                frac = a_ / float(W * H)
                # 亮区宽度/高度比接近镜片比例（0.40:1.18 ≈ 1:3）才算正面
                ar = bh / max(1, bw)
                results.append({"head": hname, "cam": [round(loc.x, 2), round(loc.y, 2), round(loc.z, 2)],
                                "yaw": round(yaw, 1), "dist": dist, "ang": ang,
                                "blob": [bw, bh], "area": a_, "theory_h": round(theory_h, 1),
                                "aspect": round(ar, 2), "frac": round(frac, 5),
                                "px": [int(c[0]), int(c[1])]})
                print("  %-11s (%7.1f,%7.1f,%5.1f) %-7.1f %-9s %-11.0f %.4f%%  ratio=%.2f"
                      % (hname, loc.x, loc.y, loc.z, yaw, "%dx%d" % (bw, bh), theory_h,
                         frac * 100, ar))

    with open(os.path.join(OUT, "headcam_candidates.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=2)

    # 优先选：aspect 接近 3（正面竖长镜片）+ 面积大
    good = [r for r in results if 1.6 <= r["aspect"] <= 5.0]
    good.sort(key=lambda d: -d["area"])
    print("\n正面朝向（竖长比 1.6~5.0）且亮区最大的机位:")
    for r in good[:6]:
        print("   %-11s cam=(%.1f,%.1f,%.1f) yaw=%.1f d=%.0f ang=%d  亮区=%dx%d (%.0f px)"
              % (r["head"], r["cam"][0], r["cam"][1], r["cam"][2], r["yaw"], r["dist"],
                 r["ang"], r["blob"][0], r["blob"][1], r["area"]))
    if good:
        best = good[0]
        print("\n最佳近摄机位: %s cam=%s yaw=%.1f pitch=-3.0" % (best["head"], best["cam"], best["yaw"]))
        loc = carla.Location(*best["cam"])
        arr = render(world, loc, carla.Rotation(pitch=-3.0, yaw=best["yaw"], roll=0.0), W, H, FOV)
        cv2.imwrite(os.path.join(OUT, "headcam_best.png"), arr)
        print("   样张: %s" % os.path.join(OUT, "headcam_best.png"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
