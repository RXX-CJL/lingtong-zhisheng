"""渲染一帧并叠加"已知世界坐标"的地面点，直接看出画面里哪段地面可见。

用之前**标定验证过**的方法（基准物法）：在相机视轴上按 4/8/12/16/20/26 m
放地面标记点，投影到画面并画出来。若某点画在画面内，那段地面就可见。
"""
import math
import os
import sys
import time

import numpy as np
import carla
import cv2

OUT = r"E:\output\_groundmap"
os.makedirs(OUT, exist_ok=True)
W, H, FOV = 1920, 1080, 90.0
# 这两个机位都试：spectator 基准 与 录制机位
CAMS = [
    ("spectator_x-19.720", (-19.720, -63.145, 5.732), -23.445, 179.536),
    ("record_x-15.720", (-15.720, -63.145, 5.732), -23.445, 179.536),
]


def proj(p, cam_loc, cam_pitch, cam_yaw, w=W, h=H, fov=FOV):
    """★ 2026-10-04 修正：up 向量符号错了（原写 [sp*cy, sp*sy, cp]）。

    正确：forward=(cp*cy, cp*sy, -sp)、right=(-sy, cy, 0)、up=(-sp*cy, -sp*sy, cp)。
    验证：yaw=−90、pitch=0 时 forward=(0,-1,0) 应朝 −Y。原式给的却是 +Y（朝后）。
    错误后果：所有"相机坐标系投影"算出的 v 都跑到画面外，
    导致物体摆放、灯珠采样点全部错位（本轮多次踩到）。
    """
    p_, y_ = math.radians(cam_pitch), math.radians(cam_yaw)
    cp, sp, cy, sy = math.cos(p_), math.sin(p_), math.cos(y_), math.sin(y_)
    fwd = np.array([cp * cy, cp * sy, -sp])
    right = np.array([-sy, cy, 0.0])
    up = np.array([-sp * cy, -sp * sy, cp])
    d = np.asarray(p, float) - np.asarray(cam_loc, float)
    z = float(d @ fwd)
    if z <= 1e-6:
        return None
    f = w / (2 * math.tan(math.radians(fov) / 2))
    return (w / 2 + f * float(d @ right) / z, h / 2 - f * float(d @ up) / z, z)


def render(world, loc, pitch, yaw, w=W, h=H):
    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(w))
    bp.set_attribute("image_size_y", str(h))
    bp.set_attribute("fov", str(FOV))
    cam = world.spawn_actor(bp, carla.Transform(
        carla.Location(*loc), carla.Rotation(pitch=pitch, yaw=yaw, roll=0.0)))
    got = []
    cam.listen(lambda im: got.append(im))
    for _ in range(6):
        world.tick()
        time.sleep(0.04)
    time.sleep(0.5)
    cam.stop()
    cam.destroy()
    return np.frombuffer(got[-1].raw_data, np.uint8).reshape(h, w, 4)[:, :, :3].copy()


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

    rows = []
    for tag, loc, pitch, yaw in CAMS:
        img = render(world, loc, pitch, yaw)
        vis = img.copy()
        print("\n=== %s ===" % tag)
        print("  %-8s %-26s %-16s %s" % ("距离", "世界坐标", "像素", "画面内?"))
        # 沿相机朝向 -X 方向放标记
        for d in (4, 6, 8, 10, 12, 16, 20, 26, 34, 44):
            p = [loc[0] - d, loc[1], 0.2]
            r = proj(p, loc, pitch, yaw)
            if r is None:
                print("  %-8d %-26s 无" % (d, "%.1f,%.1f" % (p[0], p[1])))
                continue
            x, y = int(r[0]), int(r[1])
            inside = 0 <= x < W and 0 <= y < H
            print("  %-8d (%8.1f,%8.1f)     (%4d,%4d)      %s" % (d, p[0], p[1], x, y,
                                                                  "IN" if inside else "out"))
            if inside:
                cv2.drawMarker(vis, (x, y), (0, 0, 255), cv2.MARKER_CROSS, 26, 3)
                cv2.putText(vis, "%dm" % d, (x + 10, y - 10), cv2.FONT_HERSHEY_SIMPLEX,
                            0.8, (0, 0, 255), 2, cv2.LINE_AA)
        # 再沿视轴横向放几个点（验证横向视野）
        for dy in (-8, -4, 4, 8):
            p = [loc[0] - 12, loc[1] + dy, 0.2]
            r = proj(p, loc, pitch, yaw)
            if r is None:
                continue
            x, y = int(r[0]), int(r[1])
            if 0 <= x < W and 0 <= y < H:
                cv2.drawMarker(vis, (x, y), (0, 255, 255), cv2.MARKER_TILTED_CROSS, 22, 2)
                cv2.putText(vis, "dy%+d" % dy, (x + 8, y + 22), cv2.FONT_HERSHEY_SIMPLEX,
                            0.6, (0, 255, 255), 2, cv2.LINE_AA)
        cv2.imwrite(os.path.join(OUT, "%s.png" % tag), vis)
        rows.append(tag)

    s.synchronous_mode = False
    s.fixed_delta_seconds = None
    world.apply_settings(s)
    print("\n产出:", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
