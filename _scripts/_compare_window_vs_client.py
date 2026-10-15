"""精确配对：CARLA 窗口实拍 vs 客户端 sensor 渲染，同一机位。

窗口截图 = cua-driver 抓的 CARLA 窗口（用户所见）
客户端帧 = sensor.camera.rgb 从 spectator 机位渲染（我出的图）
两者 crop 出重叠区域后逐像素比较。
"""
import os
import sys
import time

import numpy as np
import carla
import cv2

SHOT = r"E:\output\_screenshots\carla_window.png"
OUT = r"E:\output\_screenshots"
# 窗口截图中 3D 画面的区域（去掉标题栏左右黑边）—— 由人工从图上量得
CROP = (0, 25, 810, 538)   # x0, y0, x1, y1


def stats(img, tag):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    s, v = hsv[:, :, 1].astype(np.float32), hsv[:, :, 2].astype(np.float32)
    b, g, r = [img[:, :, i].astype(np.float32).mean() for i in range(3)]
    return {"tag": tag, "S": float(s.mean()), "V": float(v.mean()),
            "B": float(b), "G": float(g), "R": float(r),
            "colored": 100.0 * float((s > 60).mean()),
            "S_colored": float(s[s > 60].mean()) if (s > 60).sum() else 0.0}


def main():
    shot = cv2.imread(SHOT)
    if shot is None:
        print("窗口截图不存在:", SHOT)
        return 1
    x0, y0, x1, y1 = CROP
    win = shot[y0:y1, x0:x1]
    print("窗口截图 3D 区域: %dx%d" % (win.shape[1], win.shape[0]))
    cv2.imwrite(os.path.join(OUT, "win_crop.png"), win)

    # 客户端渲染同机位
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(25.0)
    world = client.get_world()
    spec = world.get_spectator().get_transform()
    W, H = win.shape[1], win.shape[0]
    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(W))
    bp.set_attribute("image_size_y", str(H))
    bp.set_attribute("fov", "90")
    cam = world.spawn_actor(bp, spec)
    got = []
    cam.listen(lambda im: got.append(im))
    for _ in range(8):
        world.tick()
        time.sleep(0.05)
    time.sleep(0.8)
    cam.stop()
    cam.destroy()
    cli = np.frombuffer(got[-1].raw_data, np.uint8).reshape(H, W, 4)[:, :, :3].copy()
    cv2.imwrite(os.path.join(OUT, "client_crop.png"), cli)

    print("\n%-22s %-8s %-8s %-8s %-8s %-8s %-10s %s"
          % ("来源", "S均值", "V均值", "B均值", "G均值", "R均值", "有色像素%", "S(有色)"))
    for img, tag in ((win, "CARLA 窗口（你所见）"), (cli, "客户端 sensor（我出的图）")):
        st = stats(img, tag)
        print("%-22s %-8.1f %-8.1f %-8.1f %-8.1f %-8.1f %-10.1f %.1f"
              % (tag, st["S"], st["V"], st["B"], st["G"], st["R"], st["colored"], st["S_colored"]))

    d = np.abs(win.astype(np.int16) - cli.astype(np.int16))
    print("\n逐像素差异: 平均绝对差=%.1f  最大差=%d" % (d.mean(), d.max()))
    sw, sc = stats(win, ""), stats(cli, "")
    print("窗口相对客户端:  V %+.1f   S %+.1f   R %+.1f   G %+.1f   B %+.1f"
          % (sw["V"] - sc["V"], sw["S"] - sc["S"], sw["R"] - sc["R"],
             sw["G"] - sc["G"], sw["B"] - sc["B"]))

    # 并排图 + 放大对照
    side = np.hstack([win, cli])
    cv2.putText(side, "CARLA window (yours)", (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(side, "client sensor (mine)", (W + 10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2, cv2.LINE_AA)
    p = os.path.join(OUT, "window_vs_client.png")
    cv2.imwrite(p, side)
    print("\n并排对照图:", p)

    # 取同一小区域放大对比（黄线 / 人行道）
    for name, (rx, ry, rw, rh) in (("yellow_line", (180, 300, 40, 60)),
                                   ("sidewalk", (600, 180, 60, 40))):
        a = win[ry:ry + rh, rx:rx + rw]
        b_ = cli[ry:ry + rh, rx:rx + rw]
        if a.size and b_.size:
            za = cv2.resize(a, (rw * 6, rh * 6), interpolation=cv2.INTER_NEAREST)
            zb = cv2.resize(b_, (rw * 6, rh * 6), interpolation=cv2.INTER_NEAREST)
            pair = np.hstack([za, np.full((za.shape[0], 8, 3), 255, np.uint8), zb])
            cv2.imwrite(os.path.join(OUT, "zoom_%s.png" % name), pair)
            print("  放大对照 %-12s 窗口BGR=(%.0f,%.0f,%.0f)  客户端BGR=(%.0f,%.0f,%.0f)"
                  % (name, a[:, :, 0].mean(), a[:, :, 1].mean(), a[:, :, 2].mean(),
                     b_[:, :, 0].mean(), b_[:, :, 1].mean(), b_[:, :, 2].mean()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
