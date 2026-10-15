"""真验证：CARLA raw_data 的字节序到底是 BGRA 还是 RGBA？

之前我的"验证"是假的 —— 我用 cv2.imwrite 存已知 BGR、再 cv2.imread 读回，
两边必然一致，那只证明 imwrite/imread 自洽，没验证 CARLA。

本次做法：**同一帧**，用两种字节序解释各测一次同一个橙色路障。
  * 读法 A（我一直在用的）：[:, :, :3][:, :, ::-1]   -> 若 R/B 互换则错
  * 读法 B（上一会话建议）：[:, :, :3]              -> 按 BGRA 直接当 BGR
判据（streetbarrier 实际是**橙色**）：
  * 读法 B 得到 R 最大（R≈200+，B≈20-30） -> B 对，A 错，我的 [::-1] 是 bug
  * 读法 A 得到 R 最大                   -> A 对，问题不在通道
"""
import os
import sys
import time

import numpy as np
import carla
import cv2

OUT = r"E:\output\_byteorder"
os.makedirs(OUT, exist_ok=True)
W, H, FOV = 1280, 720, 90.0


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(60.0)
    world = client.get_world()
    if len(world.get_actors().filter("traffic.traffic_light*")) == 0:
        world = client.load_world("Town10HD_Opt")
        time.sleep(3)
    s = world.get_settings()
    s.synchronous_mode = True
    s.fixed_delta_seconds = 0.05
    world.apply_settings(s)

    bl = world.get_blueprint_library()
    # 相机从高处俯视正下方，保证道具一定在画面中央
    cam_loc = carla.Location(x=-36.0, y=-63.145, z=6.0)
    cam_rot = carla.Rotation(pitch=-60.0, yaw=179.536, roll=0.0)
    placed = []
    for i, dy in enumerate((-2.5, 0.0, 2.5)):
        bp = bl.filter("static.prop.streetbarrier")[0]
        a = world.spawn_actor(bp, carla.Transform(
            carla.Location(x=-36.0, y=-63.145 + dy, z=0.3),
            carla.Rotation(pitch=0, yaw=90, roll=0)))
        placed.append((dy, a))
        print("放置 streetbarrier at y=%.1f" % (-63.145 + dy))

    bp = bl.find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(W))
    bp.set_attribute("image_size_y", str(H))
    bp.set_attribute("fov", str(FOV))
    cam = world.spawn_actor(bp, carla.Transform(cam_loc, cam_rot))
    got = []
    cam.listen(lambda im: got.append(im))
    for _ in range(8):
        world.tick()
        time.sleep(0.05)
    time.sleep(0.6)
    cam.stop()
    cam.destroy()
    raw = got[-1].raw_data
    arr = np.frombuffer(raw, np.uint8).reshape(H, W, 4)
    print("\nraw_data 长度=%d  预期 %dx%dx4=%d" % (len(raw), H, W, H * W * 4))

    # 两种解释
    A = arr[:, :, :3][:, :, ::-1].copy()          # 我一直在用（多反转一次）
    B = arr[:, :, :3].copy()                       # 上一会话建议
    # 第三种：假设是 RGBA，则取前三再反转才是 BGR（等价于 A）
    print("\n取一个像素看两种解释：")
    for (yy, xx) in ((int(H * 0.5), int(W * 0.5)), (int(H * 0.55), int(W * 0.5))):
        print("  像素(%d,%d): raw4=%s  读法A=%s  读法B=%s"
              % (yy, xx, tuple(int(v) for v in arr[yy, xx]),
                 tuple(int(v) for v in A[yy, xx]), tuple(int(v) for v in B[yy, xx])))

    res = {}
    for tag, img in (("A_flip", A), ("B_noflip", B)):
        cv2.imwrite(os.path.join(OUT, "%s.png" % tag), img)
        # 找最饱和的块（就是路障）
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        sc = hsv[:, :, 1].astype(np.int32) * hsv[:, :, 2].astype(np.int32)
        m = (sc > 12000).astype(np.uint8) * 255
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        n, lab, st, ce = cv2.connectedComponentsWithStats(m, 8)
        blobs = sorted([(int(st[i, cv2.CC_STAT_AREA]), int(ce[i][0]), int(ce[i][1]))
                        for i in range(1, n)], reverse=True)[:3]
        print("\n=== 读法 %s ===" % tag)
        out = []
        for a_, cx, cy in blobs:
            b, g, r = [int(img[cy, cx, k]) for k in range(3)]
            hh = cv2.cvtColor(np.uint8([[[b, g, r]]]), cv2.COLOR_BGR2HSV)[0, 0]
            hue = int(hh[0]) * 2
            nm = ("红/橙(R主导)" if (hue < 45 or hue >= 340) else
                  "绿(G主导)" if 100 <= hue < 150 else
                  "青/蓝(B主导)" if 180 <= hue < 260 else "其他")
            print("   a=%-5d @(%4d,%4d) BGR=(%3d,%3d,%3d) hue=%-3d sat=%-3d -> %s"
                  % (a_, cx, cy, b, g, r, hue, int(hh[1]), nm))
            out.append((b, g, r))
        res[tag] = out

    # 判据
    print("\n" + "=" * 70)
    for tag in ("A_flip", "B_noflip"):
        pts = res.get(tag) or []
        if not pts:
            print("读法 %-9s 没找到饱和块" % tag)
            continue
        b, g, r = pts[0]
        verdict = ("R 最大 -> 橙色正确（通道顺序对）" if r > b and r > g else
                   "B 最大 -> 偏蓝（通道被反转）" if b > r and b > g else
                   "G 最大" if g > r and g > b else "接近灰")
        print("读法 %-9s 最饱和块 BGR=(%3d,%3d,%3d)  ->  %s" % (tag, b, g, r, verdict))

    for _, a in placed:
        try:
            a.destroy()
        except Exception:
            pass
    s.synchronous_mode = False
    s.fixed_delta_seconds = None
    world.apply_settings(s)
    print("\n产出（两张图可直接打开对比）:", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
