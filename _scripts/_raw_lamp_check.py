"""① 抓**原始 CARLA 帧**（PNG，不经任何视频编码）测信号灯灯珠颜色。

目的：判定"红灯期镜片呈青蓝色"是 ① 视频编码造成、② 客户端后处理造成、
还是 ③ CARLA 本来就这么渲染。

做法：重建演示场景（两车 + 灯钉红），用与录制**完全相同**的相机参数逐态抓 PNG，
再把灯头区域放大保存，同时打印像素值。
"""
import csv
import math
import os
import sys
import time

import numpy as np
import carla
import cv2

OUT = r"E:\output\_rawcheck"
os.makedirs(OUT, exist_ok=True)
W, H, FOV = 1920, 1080, 90.0
LIGHT_ID = 9
# 与录制完全相同的 CAM-1
CAM1 = carla.Location(x=-15.720, y=-63.145, z=5.732)
ROT1 = carla.Rotation(pitch=-23.445, yaw=179.536, roll=0.0)


def grab(world, cam_tf):
    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(W))
    bp.set_attribute("image_size_y", str(H))
    bp.set_attribute("fov", str(FOV))
    try:
        bp.set_attribute("exposure_compensation", "0.5")
    except Exception:
        pass
    cam = world.spawn_actor(bp, cam_tf)
    got = []
    cam.listen(lambda im: got.append(im))
    for _ in range(6):
        world.tick()
        time.sleep(0.05)
    time.sleep(0.6)
    cam.stop()
    cam.destroy()
    return np.frombuffer(got[-1].raw_data, np.uint8).reshape(H, W, 4)[:, :, :3].copy()


def report_lamp(img, tag, boxes):
    """在给定框内找最亮点，打印其颜色。"""
    print("  %-8s" % tag, end="")
    for (x1, y1, x2, y2) in boxes:
        roi = img[y1:y2, x1:x2]
        if roi.size == 0:
            print("  [empty]", end="")
            continue
        g = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        y, x = np.unravel_index(int(np.argmax(g)), g.shape)
        pb, pg, pr = [int(roi[y, x, i]) for i in range(3)]
        hsv = cv2.cvtColor(np.uint8([[[pb, pg, pr]]]), cv2.COLOR_BGR2HSV)[0, 0]
        print("  (%3d,%3d,%3d) h=%-3d" % (pb, pg, pr, int(hsv[0]) * 2), end="")
    print()


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(30.0)
    world = client.get_world()
    tl = None
    for a in world.get_actors().filter("traffic.traffic_light*"):
        if a.id == LIGHT_ID:
            tl = a
    if tl is None:
        print("找不到 light", LIGHT_ID)
        return 1

    s = world.get_settings()
    s.synchronous_mode = True
    s.fixed_delta_seconds = 0.05
    world.apply_settings(s)

    cam_tf = carla.Transform(CAM1, ROT1)
    # 录制时 YOLO 框的稳定位置（从端到端结果里读到的）
    BOXES = [(1644, 901, 1660, 941), (998, 122, 1017, 170), (1770, 901, 1787, 944)]

    print("原始 CARLA 帧（PNG，未经视频编码）灯头峰值像素:")
    print("  %-8s  框A(1644,901)      框B(998,122)       框C(1770,901)" % "灯态")
    results = {}
    for name, st in (("Red", carla.TrafficLightState.Red),
                     ("Green", carla.TrafficLightState.Green),
                     ("Yellow", carla.TrafficLightState.Yellow)):
        tl.freeze(True)
        tl.set_state(st)
        for _ in range(6):
            world.tick()
            time.sleep(0.05)
        actual = str(tl.get_state())
        if actual != name:
            print("  !! %s 未生效（实际 %s）" % (name, actual))
            continue
        img = grab(world, cam_tf)
        cv2.imwrite(os.path.join(OUT, "raw_%s_full.png" % name.lower()), img)
        report_lamp(img, name, BOXES)
        results[name] = img
        # 放大每个框保存
        tiles = []
        for k, (x1, y1, x2, y2) in enumerate(BOXES):
            m = 30
            cy0, cy1 = max(0, y1 - m), min(H, y2 + m)
            cx0, cx1 = max(0, x1 - m), min(W, x2 + m)
            crop = img[cy0:cy1, cx0:cx1]
            if crop.size:
                tiles.append(cv2.resize(crop, (200, 300), interpolation=cv2.INTER_NEAREST))
        if tiles:
            while len(tiles) < 3:
                tiles.append(np.zeros((300, 200, 3), np.uint8))
            sheet = np.hstack(tiles)
            cv2.putText(sheet, "RAW CARLA %s" % name, (6, 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2, cv2.LINE_AA)
            cv2.imwrite(os.path.join(OUT, "raw_%s_lamps.png" % name.lower()), sheet)

    # 三态并排
    rows = []
    for name in ("Red", "Green", "Yellow"):
        if name in results:
            rows.append(cv2.resize(results[name], (W // 3, H // 3)))
    if rows:
        cv2.imwrite(os.path.join(OUT, "raw_three_states.png"), np.vstack(rows))

    # 关掉后处理再抓一次（对照：看是不是后处理把红变青）
    print("\n对照：关闭 enable_postprocess_effects 后再抓 Red:")
    tl.set_state(carla.TrafficLightState.Red)
    for _ in range(6):
        world.tick()
        time.sleep(0.05)
    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(W))
    bp.set_attribute("image_size_y", str(H))
    bp.set_attribute("fov", str(FOV))
    try:
        bp.set_attribute("enable_postprocess_effects", "False")
    except Exception as e:
        print("  设置失败:", e)
    cam = world.spawn_actor(bp, cam_tf)
    got = []
    cam.listen(lambda im: got.append(im))
    for _ in range(6):
        world.tick()
        time.sleep(0.05)
    time.sleep(0.6)
    cam.stop()
    cam.destroy()
    nop = np.frombuffer(got[-1].raw_data, np.uint8).reshape(H, W, 4)[:, :, :3].copy()
    cv2.imwrite(os.path.join(OUT, "raw_red_nopostprocess.png"), nop)
    report_lamp(nop, "Red无PP", BOXES)

    tl.freeze(False)
    s.synchronous_mode = False
    s.fixed_delta_seconds = None
    world.apply_settings(s)
    print("\nwrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
