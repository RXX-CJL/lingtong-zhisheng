"""把客户端 sensor 的画面调到与 CARLA 窗口一致。

实测差异（同机位、同内容）：
  V 窗口 +16.1（更亮）   R +30.1（更暖）   G +15.5   B +0.9   S -1.1（饱和度几乎无差）
→ 需要更暖的色温 + 更高曝光。参数候选均可用 env 覆盖，所以逐组扫描后给出最佳组合。
"""
import os
import sys
import time

import numpy as np
import carla
import cv2

OUT = r"E:\output\_screenshots"
WIN = cv2.imread(os.path.join(OUT, "win_crop.png"))
W, H = WIN.shape[1], WIN.shape[0]


def stats(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    b, g, r = [img[:, :, i].astype(np.float32).mean() for i in range(3)]
    return dict(V=float(hsv[:, :, 2].astype(np.float32).mean()),
                S=float(hsv[:, :, 1].astype(np.float32).mean()),
                B=float(b), G=float(g), R=float(r))


def render(world, spec, attrs, w=W, h=H):
    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(w))
    bp.set_attribute("image_size_y", str(h))
    bp.set_attribute("fov", "90")
    applied, failed = [], []
    for k, v in attrs.items():
        try:
            bp.set_attribute(k, str(v))
            applied.append("%s=%s" % (k, v))
        except Exception as e:
            failed.append("%s(%s)" % (k, e))
    cam = world.spawn_actor(bp, spec)
    got = []
    cam.listen(lambda im: got.append(im))
    for _ in range(6):
        world.tick()
        time.sleep(0.05)
    time.sleep(0.6)
    cam.stop()
    cam.destroy()
    arr = np.frombuffer(got[-1].raw_data, np.uint8).reshape(h, w, 4)[:, :, :3].copy()
    return arr, applied, failed


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(25.0)
    world = client.get_world()
    spec = world.get_spectator().get_transform()

    ws = stats(WIN)
    print("目标（CARLA 窗口）  V=%.1f S=%.1f  B=%.1f G=%.1f R=%.1f" %
          (ws["V"], ws["S"], ws["B"], ws["G"], ws["R"]))
    print()
    print("%-46s %-8s %-8s %-8s %-8s %-8s %s" %
          ("参数", "V", "S", "B", "G", "R", "Δ(与窗口)"))
    best = None
    variants = [
        ("默认", {}),
        ("temp=4500", {"temp": 4500}),
        ("temp=3500", {"temp": 3500}),
        ("temp=3000", {"temp": 3000}),
        ("exposure_comp=+0.5", {"exposure_compensation": 0.5}),
        ("exposure_comp=+1.0", {"exposure_compensation": 1.0}),
        ("temp=3500 exp=+0.5", {"temp": 3500, "exposure_compensation": 0.5}),
        ("temp=4000 exp=+0.7", {"temp": 4000, "exposure_compensation": 0.7}),
        ("temp=3500 exp=+0.7 gamma=2.0", {"temp": 3500, "exposure_compensation": 0.7, "gamma": 2.0}),
        ("exp_mode=manual temp=3500 exp=+0.7",
         {"exposure_mode": "manual", "temp": 3500, "exposure_compensation": 0.7}),
    ]
    tiles = []
    for label, attrs in variants:
        arr, applied, failed = render(world, spec, attrs)
        st = stats(arr)
        d = abs(st["V"] - ws["V"]) + abs(st["R"] - ws["R"]) + abs(st["G"] - ws["G"]) + abs(st["B"] - ws["B"])
        print("%-46s %-8.1f %-8.1f %-8.1f %-8.1f %-8.1f %.1f%s"
              % (label, st["V"], st["S"], st["B"], st["G"], st["R"], d,
                 ("  失败:" + ",".join(failed)) if failed else ""))
        if best is None or d < best[1]:
            best = (label, d, arr.copy(), st)
        small = cv2.resize(arr, (W // 3, H // 3))
        cv2.putText(small, label[:30], (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2, cv2.LINE_AA)
        tiles.append(small)

    print("\n最佳: %s  Δ=%.1f" % (best[0], best[1]))
    bn = stats(best[2])
    print("   窗口 V=%.1f R=%.1f G=%.1f B=%.1f  |  最佳 V=%.1f R=%.1f G=%.1f B=%.1f"
          % (ws["V"], ws["R"], ws["G"], ws["B"], bn["V"], bn["R"], bn["G"], bn["B"]))

    # 拼图：窗口 + 默认 + 最佳 + 其他
    win_tile = cv2.resize(WIN, (W // 3, H // 3))
    cv2.putText(win_tile, "CARLA WINDOW (target)", (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2, cv2.LINE_AA)
    allt = [win_tile] + tiles
    while len(allt) % 4:
        allt.append(np.zeros_like(allt[0]))
    rows = [np.hstack(allt[i:i + 4]) for i in range(0, len(allt), 4)]
    p = os.path.join(OUT, "postprocess_match.png")
    cv2.imwrite(p, np.vstack(rows))
    cv2.imwrite(os.path.join(OUT, "client_best.png"), best[2])
    print("对照图:", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
