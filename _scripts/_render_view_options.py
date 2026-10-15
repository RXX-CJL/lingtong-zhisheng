"""把"现状"与"后移 4m / 8m"两个候选机位渲染在同一批车辆位置上，供用户对比选择。

车辆位置取演示中的真实时刻：
  停止线（右车守法停车 / 左车闯红灯越线）、路口中心、对面停止线
"""
import math
import os
import sys
import time

import numpy as np
import carla
import cv2

OUT = r"E:\output\_demo_scene"
os.makedirs(OUT, exist_ok=True)
W, H, FOV = 1920, 1080, 90.0

STOP_X = -25.61
LANE1_Y, LANE2_Y = -64.7, -68.2
FAR_X = -68.44

# (相机位置, pitch, yaw, 标签)
VIEWS = [
    ([-19.720, -63.145, 5.732], -23.445, 179.536, "now"),
    ([-15.720, -63.145, 5.732], -23.445, 179.536, "back4m"),
    ([-11.720, -63.145, 5.732], -23.445, 179.536, "back8m"),
]

# 要摆的车辆位置：(tag, x, y, yaw)
PLACEMENTS = [
    ("at_stopline", [(STOP_X + 1.5, LANE1_Y, 180.6), (STOP_X + 1.5, LANE2_Y, 180.6)]),
    ("at_junction", [(-33.0, LANE1_Y, 180.6), (STOP_X + 1.5, LANE2_Y, 180.6)]),
    ("at_far",      [(FAR_X + 2.0, LANE1_Y, 180.6), (-33.0, LANE2_Y, 180.6)]),
]


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(25.0)
    world = client.get_world()

    # 清掉可能残留的车辆
    for v in world.get_actors().filter("vehicle.*"):
        v.destroy()

    bp_car = world.get_blueprint_library().filter("vehicle.tesla.model3")[0]
    bp_law = world.get_blueprint_library().filter("vehicle.audi.a2")[0]

    sheet = {}
    for cidx, (loc, pitch, yaw, tag) in enumerate(VIEWS):
        cam_tf = carla.Transform(carla.Location(x=loc[0], y=loc[1], z=loc[2]),
                                 carla.Rotation(pitch=pitch, yaw=yaw, roll=0.0))
        cbp = world.get_blueprint_library().find("sensor.camera.rgb")
        cbp.set_attribute("image_size_x", str(W))
        cbp.set_attribute("image_size_y", str(H))
        cbp.set_attribute("fov", str(FOV))
        cam = world.spawn_actor(cbp, cam_tf)

        rows = []
        for pname, cars in PLACEMENTS:
            spawned = []
            for k, (x, y, yw) in enumerate(cars):
                bp = bp_car if k == 0 else bp_law
                a = world.spawn_actor(bp, carla.Transform(
                    carla.Location(x=x, y=y, z=0.4), carla.Rotation(pitch=0, yaw=yw, roll=0)))
                spawned.append(a)
            frames = []
            cam.listen(lambda im: frames.append(im))
            for _ in range(5):
                world.tick()
                time.sleep(0.04)
            time.sleep(0.5)
            arr = np.frombuffer(frames[-1].raw_data, np.uint8).reshape(H, W, 4)[:, :, :3].copy()
            cam.stop()
            rows.append((pname, arr))
            for a in spawned:
                a.destroy()
        cam.destroy()
        sheet[tag] = rows
        print("rendered view", tag)

    # 拼图：每列一个机位，每行一个车辆位置
    cols = []
    for tag, rows in sheet.items():
        col = []
        for pname, arr in rows:
            small = cv2.resize(arr, (W // 3, H // 3))
            cv2.putText(small, "%s / %s" % (tag, pname), (8, 26),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2, cv2.LINE_AA)
            col.append(small)
        cols.append(np.vstack(col))
    out = np.hstack(cols)
    p = os.path.join(OUT, "view_compare.png")
    cv2.imwrite(p, out)
    print("wrote", p, out.shape)
    return 0


if __name__ == "__main__":
    sys.exit(main())
