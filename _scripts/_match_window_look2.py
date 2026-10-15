"""第二轮参数扫描：固定 exposure_mode=manual（避免直方图自动曝光干扰色温），
在手动模式下扫 色温 × 曝光补偿，找最接近 CARLA 窗口的组合。
"""
import os
import sys
import time

import numpy as np
import carla
import cv2

OUT = r"E:\output\_screenshots"
WIN = cv2.imread(os.path.join(OUT, "win_crop.png"))
H, W = WIN.shape[:2]


def stats(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    b, g, r = [img[:, :, i].astype(np.float32).mean() for i in range(3)]
    return dict(V=float(hsv[:, :, 2].astype(np.float32).mean()),
                S=float(hsv[:, :, 1].astype(np.float32).mean()),
                B=float(b), G=float(g), R=float(r))


def render(world, spec, attrs):
    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(W))
    bp.set_attribute("image_size_y", str(H))
    bp.set_attribute("fov", "90")
    for k, v in attrs.items():
        try:
            bp.set_attribute(k, str(v))
        except Exception:
            pass
    cam = world.spawn_actor(bp, spec)
    got = []
    cam.listen(lambda im: got.append(im))
    for _ in range(6):
        world.tick()
        time.sleep(0.05)
    time.sleep(0.55)
    cam.stop()
    cam.destroy()
    return np.frombuffer(got[-1].raw_data, np.uint8).reshape(H, W, 4)[:, :, :3].copy()


def score(st, ws):
    """亮度差 + 色偏（R-B 关系）+ 饱和度差"""
    return (abs(st["V"] - ws["V"]) * 1.0
            + abs((st["R"] - st["B"]) - (ws["R"] - ws["B"])) * 1.0
            + abs(st["S"] - ws["S"]) * 0.3)


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(25.0)
    world = client.get_world()
    spec = world.get_spectator().get_transform()
    ws = stats(WIN)
    print("目标(窗口): V=%.1f S=%.1f B=%.1f G=%.1f R=%.1f  R-B=%+.1f"
          % (ws["V"], ws["S"], ws["B"], ws["G"], ws["R"], ws["R"] - ws["B"]))
    print()
    print("%-52s %-7s %-7s %-7s %-7s %-7s %-8s %s" %
          ("参数", "V", "S", "B", "G", "R", "R-B", "得分"))
    results = []
    for temp in (6500, 5000, 4000, 3400):
        for exp in (0.0, 0.4, 0.7, 1.0):
            attrs = {"exposure_mode": "manual", "temp": temp, "exposure_compensation": exp}
            arr = render(world, spec, attrs)
            st = stats(arr)
            sc = score(st, ws)
            results.append((sc, "manual temp=%d exp=%+.1f" % (temp, exp), arr.copy(), st, attrs))
            print("%-52s %-7.1f %-7.1f %-7.1f %-7.1f %-7.1f %-8.1f %.1f"
                  % (results[-1][1], st["V"], st["S"], st["B"], st["G"], st["R"],
                     st["R"] - st["B"], sc))
    # 对照：默认与 +0.5
    for label, attrs in (("默认（对照）", {}),
                         ("exposure_comp=+0.5（对照）", {"exposure_compensation": 0.5})):
        arr = render(world, spec, attrs)
        st = stats(arr)
        sc = score(st, ws)
        results.append((sc, label, arr.copy(), st, attrs))
        print("%-52s %-7.1f %-7.1f %-7.1f %-7.1f %-7.1f %-8.1f %.1f"
              % (label, st["V"], st["S"], st["B"], st["G"], st["R"], st["R"] - st["B"], sc))

    results.sort(key=lambda t: t[0])
    print("\n最优 3 组:")
    for sc, label, arr, st, attrs in results[:3]:
        print("   %-52s 得分=%.1f  V=%.1f S=%.1f R-B=%+.1f  %s"
              % (label, sc, st["V"], st["S"], st["R"] - st["B"], attrs))
    best = results[0]
    cv2.imwrite(os.path.join(OUT, "client_best2.png"), best[2])

    # 拼图：窗口 + 前三名
    tiles = [cv2.resize(WIN, (W // 3, H // 3))]
    cv2.putText(tiles[0], "CARLA WINDOW (target)", (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2, cv2.LINE_AA)
    for sc, label, arr, st, attrs in results[:3]:
        t = cv2.resize(arr, (W // 3, H // 3))
        cv2.putText(t, label[:34], (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(t, "score %.1f" % sc, (6, 44), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2, cv2.LINE_AA)
        tiles.append(t)
    while len(tiles) % 4:
        tiles.append(np.zeros_like(tiles[0]))
    p = os.path.join(OUT, "postprocess_match2.png")
    cv2.imwrite(p, np.vstack([np.hstack(tiles[0:4])]))
    print("\n对照图:", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
