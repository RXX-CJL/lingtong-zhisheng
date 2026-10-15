"""回答用户真正关心的问题：红绿灯的颜色在「CARLA 窗口」和「我的图」里是否一致，
以及项目判色器能否正确判红。

步骤：
  1. 把控制本进口道的 light 9 钉成 Red
  2. 用已验证投影算出灯头在画面里的位置
  3. 抓窗口截图 + 渲染客户端帧，在**同一点**采样颜色
  4. 把两边的灯头 crop 交给项目判色器（CNN4 + HSV）判色
"""
import json
import math
import os
import subprocess
import sys
import time

import numpy as np
import carla
import cv2

OUT = r"E:\output\_redlight_colour_check"
os.makedirs(OUT, exist_ok=True)
CUA = os.path.join(os.environ["USERPROFILE"], ".local", "bin", "cua-driver", "cua-driver.exe")
WIN_PID, WIN_HWND = 26268, 1181484
WIN_CROP = (0, 25, 810, 538)      # 窗口内 3D 画面区域（已量得）

W, H, FOV = 1920, 1080, 90.0
# 需要采样的信号灯头（世界坐标，来自 light 9 的灯箱：控制 road 7 lane 1/2）
HEADS = [
    ("light9_headA", [-45.7, -64.3, 5.15]),
    ("light9_headB", [-45.7, -68.1, 5.15]),
    ("light17_headA", [-59.7, -60.8, 5.15]),
]


def proj_factory(tf, w, h, fov=90.0):
    loc = np.array([tf.location.x, tf.location.y, tf.location.z])
    p, y, r = map(math.radians, (tf.rotation.pitch, tf.rotation.yaw, tf.rotation.roll))
    cz, sz = math.cos(y), math.sin(y)
    cp, sp = math.cos(p), math.sin(p)
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    Ry = np.array([[cp, 0, -sp], [0, 1, 0], [sp, 0, cp]])
    f = w / (2 * math.tan(math.radians(fov) / 2))

    def pr(pt):
        vc = Rz @ Ry @ (np.asarray(pt, float) - loc)
        # 注意：这里用 Ry 的修正版（pitch 向下为负 -> -sin）
        vc = np.array([np.dot(np.array([cp * cz, cp * sz, -sp]), np.asarray(pt, float) - loc),
                       np.dot(np.array([-sz, cz, 0.0]), np.asarray(pt, float) - loc),
                       np.dot(np.array([sp * cz, sp * sz, cp]), np.asarray(pt, float) - loc)])
        if vc[0] <= 1e-6:
            return None
        return (w / 2 + f * (vc[1] / vc[0]), h / 2 - f * (vc[2] / vc[0]), float(vc[0]))
    return pr


def grab_window(path):
    args = json.dumps({"pid": WIN_PID, "window_id": WIN_HWND,
                       "include_accessibility_tree": False,
                       "screenshot_out_file": path})
    p = subprocess.run([CUA, "call", "get_window_state"], input=args,
                       capture_output=True, text=True, timeout=90)
    return os.path.exists(path)


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(25.0)
    world = client.get_world()
    spec = world.get_spectator().get_transform()

    tl = None
    for a in world.get_actors().filter("traffic.traffic_light*"):
        if a.id == 9:
            tl = a
    tl.freeze(True)
    tl.set_state(carla.TrafficLightState.Red)
    for _ in range(6):
        world.tick()
        time.sleep(0.06)
    print("light 9 =", tl.get_state())

    # 客户端帧（1920x1080，与录制同规格）
    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(W))
    bp.set_attribute("image_size_y", str(H))
    bp.set_attribute("fov", "90")
    bp.set_attribute("exposure_compensation", "0.5")
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
    cv2.imwrite(os.path.join(OUT, "client_1080.png"), cli)

    # 窗口截图
    wp = os.path.join(OUT, "window.png")
    grab_window(wp)
    win_full = cv2.imread(wp)
    x0, y0, x1, y1 = WIN_CROP
    win = win_full[y0:y1, x0:x1]
    cv2.imwrite(os.path.join(OUT, "window_3d.png"), win)
    wW, wH = win.shape[1], win.shape[0]
    print("窗口 3D 区域: %dx%d" % (wW, wH))

    pr_cli = proj_factory(spec, W, H)
    pr_win = proj_factory(spec, wW, wH)

    print("\n%-16s %-22s %-22s %s" % ("灯头", "客户端1920 像素/BGR", "窗口810 像素/BGR", "一致?"))
    tiles = []
    for name, pt in HEADS:
        rc = pr_cli(pt)
        rw = pr_win(pt)
        if not rc or not rw:
            print("%-16s 投影失败" % name)
            continue
        uc, vc = int(round(rc[0])), int(round(rc[1]))
        uw, vw = int(round(rw[0])), int(round(rw[1]))

        def sample(img, u, v, half=8):
            a = img[max(0, v - half):v + half + 1, max(0, u - half):u + half + 1]
            if a.size == 0:
                return None
            b, g, r = [float(a[:, :, i].mean()) for i in range(3)]
            hsv = cv2.cvtColor(a, cv2.COLOR_BGR2HSV)
            return (b, g, r, float(hsv[:, :, 1].mean()), float(hsv[:, :, 2].mean()))

        sc = sample(cli, uc, vc)
        sw = sample(win, uw, vw)
        if sc and sw:
            print("%-16s (%4d,%4d) B%3.0f G%3.0f R%3.0f S%3.0f  (%4d,%4d) B%3.0f G%3.0f R%3.0f S%3.0f  %s"
                  % (name, uc, vc, sc[0], sc[1], sc[2], sc[3],
                     uw, vw, sw[0], sw[1], sw[2], sw[3],
                     "偏色差R%.0f" % (sw[2] - sc[2])))
            # 裁两边灯头贴图
            for img, u, v, tag, scale in ((cli, uc, vc, "cli", 1), (win, uw, vw, "win", 1)):
                hh = max(0, v - 60), min(img.shape[0], v + 60)
                ww = max(0, u - 60), min(img.shape[1], u + 60)
                crop = img[hh[0]:hh[1], ww[0]:ww[1]]
                if crop.size:
                    cv2.drawMarker(crop, (u - ww[0], v - hh[0]), (255, 0, 255), cv2.MARKER_CROSS, 20, 2)
                    tiles.append((name + "_" + tag, cv2.resize(crop, (240, 240), interpolation=cv2.INTER_NEAREST)))

    # 判色器测试
    sys.path.insert(0, r"E:\output\1\api")
    import traffic_light_classifier as tlc
    print("\n项目判色器对两边灯头 crop 的判定（真值 = red）:")
    for nm, t in tiles:
        st, conf = tlc.classify_traffic_light(t)
        print("   %-22s CNN4 -> %-8s conf=%.3f   %s" % (nm, st, conf, "✅" if st == "red" else "❌"))

    if tiles:
        cols = 4
        row = []
        for nm, t in tiles:
            c = t.copy()
            cv2.putText(c, nm[:26], (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 255), 1, cv2.LINE_AA)
            row.append(c)
        while len(row) % cols:
            row.append(np.zeros_like(row[0]))
        cv2.imwrite(os.path.join(OUT, "head_crops.png"),
                    np.vstack([np.hstack(row[i:i + cols]) for i in range(0, len(row), cols)]))

    tl.freeze(False)
    print("\nwrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
