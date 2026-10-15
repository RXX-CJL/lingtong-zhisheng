"""近摄取灯珠：把相机放到信号灯头正前方 ~8 m，量红灯态与绿灯态下
灯珠的实际像素。用来回答"到底是灯渲染太暗，还是判色/编码的问题"。
"""
import os
import sys
import time

import numpy as np
import carla
import cv2

OUT = r"E:\output\_rawcheck"
os.makedirs(OUT, exist_ok=True)
W, H, FOV = 1280, 720, 60.0
# 从截图看，画面里两颗信号灯头在 y≈142 附近；先把它们的世界位置求出来：
# 直接扫描场景里 traffic light 的灯箱，投影到 CAM-1 视图，找落在 y∈[100,200] 的
CAM1 = np.array([-15.720, -63.145, 5.732])
PITCH, YAW = -23.445, 179.536


def proj(p, w=1920, h=1080, fov=90.0):
    import math
    loc = CAM1
    p_, y_ = math.radians(PITCH), math.radians(YAW)
    cp, sp, cy, sy = math.cos(p_), math.sin(p_), math.cos(y_), math.sin(y_)
    fwd = np.array([cp * cy, cp * sy, -sp])
    right = np.array([-sy, cy, 0.0])
    up = np.array([sp * cy, sp * sy, cp])
    d = np.asarray(p, float) - loc
    z = float(d @ fwd)
    if z <= 1e-6:
        return None
    f = w / (2 * math.tan(math.radians(fov) / 2))
    return (w / 2 + f * float(d @ right) / z, h / 2 - f * float(d @ up) / z, z)


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(30.0)
    world = client.get_world()
    print("场景里各 traffic light 灯箱投影到 CAM-1 视图（只列画面内、y<400 的）:")
    cands = []
    for a in world.get_actors().filter("traffic.traffic_light*"):
        atf = a.get_transform()
        for i, b in enumerate(a.get_light_boxes()):
            raw = np.array([b.location.x, b.location.y, b.location.z])
            if max(b.extent.x, b.extent.y) > 2.0:
                continue
            r = proj(raw)
            if r and 0 <= r[0] < 1920 and r[1] < 400:
                print("   light %-3d box#%d world=(%8.2f,%8.2f,%5.2f) -> px=(%4.0f,%4.0f) d=%.1fm ext=(%.2f,%.2f,%.2f)"
                      % (a.id, i, raw[0], raw[1], raw[2], r[0], r[1], r[2],
                         b.extent.x, b.extent.y, b.extent.z))
                cands.append((a, raw, r, b.extent))

    if not cands:
        print("没找到候选灯箱")
        return 1
    # 选画面里最靠中的两颗
    cands.sort(key=lambda t: abs(t[2][0] - 960))
    tl = cands[0][0]
    lamp = cands[0][1]
    print("\n选用 light %d 的灯箱 world=(%.2f,%.2f,%.2f) 作为近摄目标" % (tl.id, lamp[0], lamp[1], lamp[2]))

    # 近摄机位：放在灯箱正东 8 m，同高
    cam_loc = carla.Location(x=float(lamp[0] + 8.0), y=float(lamp[1]), z=float(lamp[2]))
    yaw = 180.0
    cam_rot = carla.Rotation(pitch=0.0, yaw=yaw, roll=0.0)

    s = world.get_settings()
    s.synchronous_mode = True
    s.fixed_delta_seconds = 0.05
    world.apply_settings(s)

    tiles = []
    print("\n近摄 %dx%d fov=%.0f，距灯 %.1f m" % (W, H, FOV, 8.0))
    print("%-8s %-30s %s" % ("灯态", "灯珠中心 BGR / hue", "整幅最亮"))
    for name, st in (("Red", carla.TrafficLightState.Red),
                     ("Green", carla.TrafficLightState.Green),
                     ("Yellow", carla.TrafficLightState.Yellow)):
        tl.freeze(True)
        tl.set_state(st)
        for _ in range(6):
            world.tick()
            time.sleep(0.05)
        if str(tl.get_state()) != name:
            print("  %s 未生效" % name)
            continue
        bp = world.get_blueprint_library().find("sensor.camera.rgb")
        bp.set_attribute("image_size_x", str(W))
        bp.set_attribute("image_size_y", str(H))
        bp.set_attribute("fov", str(FOV))
        cam = world.spawn_actor(bp, carla.Transform(cam_loc, cam_rot))
        got = []
        cam.listen(lambda im: got.append(im))
        for _ in range(6):
            world.tick()
            time.sleep(0.05)
        time.sleep(0.6)
        cam.stop()
        cam.destroy()
        img = np.frombuffer(got[-1].raw_data, np.uint8).reshape(H, W, 4)[:, :, :3].copy()
        cv2.imwrite(os.path.join(OUT, "close_%s.png" % name.lower()), img)
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        y, x = np.unravel_index(int(np.argmax(g)), g.shape)
        pb, pg, pr = [int(img[y, x, i]) for i in range(3)]
        hsv = cv2.cvtColor(np.uint8([[[pb, pg, pr]]]), cv2.COLOR_BGR2HSV)[0, 0]
        print("  %-8s (%3d,%3d,%3d) hue=%-4d              灰度峰值=%d at (%d,%d)"
              % (name, pb, pg, pr, int(hsv[0]) * 2, int(g.max()), x, y))
        tiles.append(cv2.resize(img, (W // 2, H // 2)))

    if tiles:
        cv2.imwrite(os.path.join(OUT, "close_three_states.png"), np.vstack(tiles))
        print("\n三态近摄拼图:", os.path.join(OUT, "close_three_states.png"))

    tl.freeze(False)
    s.synchronous_mode = False
    s.fixed_delta_seconds = None
    world.apply_settings(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
