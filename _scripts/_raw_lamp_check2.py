"""用与录制**完全相同**的 CAM-1 机位重抓原始帧，并把"同一颗灯"在
① 原始 CARLA 渲染  ② 录制视频  两种来源下并排放大，直接判定颜色差异来自哪一环。

先自动定位"红灯时最亮的镜片"（在原始帧里找），再把同一坐标的视频帧取出来对比。
"""
import os
import sys
import time

import numpy as np
import carla
import cv2

OUT = r"E:\output\_rawcheck"
os.makedirs(OUT, exist_ok=True)
W, H, FOV = 1920, 1080, 90.0
CAM1 = carla.Location(x=-15.720, y=-63.145, z=5.732)
ROT1 = carla.Rotation(pitch=-23.445, yaw=179.536, roll=0.0)
VIDEO = r"E:\output\_dual_cam_demo\dual_cam_demo_lossless.mkv"


def grab(world, states):
    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(W))
    bp.set_attribute("image_size_y", str(H))
    bp.set_attribute("fov", str(FOV))
    bp.set_attribute("exposure_compensation", "0.5")
    cam = world.spawn_actor(bp, carla.Transform(CAM1, ROT1))
    got = []
    cam.listen(lambda im: got.append(im))
    for _ in range(6):
        world.tick()
        time.sleep(0.05)
    time.sleep(0.6)
    cam.stop()
    cam.destroy()
    return np.frombuffer(got[-1].raw_data, np.uint8).reshape(H, W, 4)[:, :, :3].copy()


def top_lamps(img, k=4):
    """找"亮的、带色的、紧凑的"小区域 —— 点亮镜片的候选。"""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    s = hsv[:, :, 1].astype(np.int16)
    v = hsv[:, :, 2].astype(np.int16)
    m = ((s > 90) & (v > 140)).astype(np.uint8) * 255
    m[int(H * 0.6):, :] = 0
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    n, lab, st, ce = cv2.connectedComponentsWithStats(m, 8)
    out = []
    for i in range(1, n):
        a = int(st[i, cv2.CC_STAT_AREA])
        if a < 8 or a > 2000:
            continue
        w_, h_ = int(st[i, cv2.CC_STAT_WIDTH]), int(st[i, cv2.CC_STAT_HEIGHT])
        if max(w_, h_) / max(1, min(w_, h_)) > 4:
            continue
        out.append((a, int(ce[i][0]), int(ce[i][1]), w_, h_))
    out.sort(key=lambda t: -t[0])
    return out[:k]


def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(30.0)
    world = client.get_world()
    tl = None
    for a in world.get_actors().filter("traffic.traffic_light*"):
        if a.id == 9:
            tl = a
    s = world.get_settings()
    s.synchronous_mode = True
    s.fixed_delta_seconds = 0.05
    world.apply_settings(s)

    raws = {}
    for name, st in (("Red", carla.TrafficLightState.Red),
                     ("Green", carla.TrafficLightState.Green)):
        tl.freeze(True)
        tl.set_state(st)
        for _ in range(6):
            world.tick()
            time.sleep(0.05)
        if str(tl.get_state()) != name:
            print("!! %s 未生效" % name)
            continue
        img = grab(world, st)
        raws[name] = img
        cv2.imwrite(os.path.join(OUT, "cam1_%s.png" % name.lower()), img)
        lamps = top_lamps(img)
        print("原始 CARLA %-5s 检出 %d 个亮色斑块:" % (name, len(lamps)))
        for a, cx, cy, w_, h_ in lamps:
            b, g, r = [int(img[cy, cx, i]) for i in range(3)]
            hsv = cv2.cvtColor(np.uint8([[[b, g, r]]]), cv2.COLOR_BGR2HSV)[0, 0]
            print("    area=%-4d (%4d,%4d) %2dx%-3d BGR=(%3d,%3d,%3d) hue=%-3d"
                  % (a, cx, cy, w_, h_, b, g, r, int(hsv[0]) * 2))

    # 视频同帧（录制时 CAM-1 的 t=10.05s 对应帧 201；红灯）
    cap = cv2.VideoCapture(VIDEO)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 201)
    ok, vid = cap.read()
    cap.release()

    # 并排：原始 Red / 原始 Green / 视频(红灯)
    if "Red" in raws and ok:
        # 取原始红灯帧里最亮的斑块作为"同一颗灯"的锚点
        lamps = top_lamps(raws["Red"])
        if lamps:
            a, cx, cy, w_, h_ = lamps[0]
            print("\n以原始红灯帧最亮斑块 (%d,%d) 为锚点，并排对比:" % (cx, cy))
            tiles = []
            for tag, im in (("RAW Red", raws["Red"]), ("RAW Green", raws.get("Green")),
                            ("VIDEO f201", vid)):
                if im is None:
                    continue
                m = 40
                y0, y1 = max(0, cy - m), min(H, cy + m)
                x0, x1 = max(0, cx - m), min(W, cx + m)
                c = im[y0:y1, x0:x1].copy()
                if c.size == 0:
                    continue
                z = cv2.resize(c, (260, 260), interpolation=cv2.INTER_NEAREST)
                cv2.drawMarker(z, (int((cx - x0) * 260 / max(1, x1 - x0)),
                                   int((cy - y0) * 260 / max(1, y1 - y0))),
                               (255, 0, 255), cv2.MARKER_CROSS, 20, 2)
                pb, pg, pr = [int(c[max(0, cy - y0 - 1), max(0, cx - x0 - 1), i]) for i in range(3)]
                cv2.putText(z, tag, (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)
                cv2.putText(z, "(%d,%d,%d)" % (pb, pg, pr), (4, 252),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1, cv2.LINE_AA)
                tiles.append(z)
            if tiles:
                sheet = np.hstack(tiles)
                p = os.path.join(OUT, "same_lamp_raw_vs_video.png")
                cv2.imwrite(p, sheet)
                print("   并排图:", p)

    tl.freeze(False)
    s.synchronous_mode = False
    s.fixed_delta_seconds = None
    world.apply_settings(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
