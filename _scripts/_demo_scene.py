"""闯红灯演示场景 —— 按用户剧本生成（2026-10-04）

剧本：
  红灯亮起时，两辆车并排从相机下方（东侧）驶入路口方向；
  到达停止线后 —— 右侧（守法）车停下等红灯，左侧（违规）车无视红灯直接通过；
  红灯转绿后，守法车起步通过停止线；违规车已驶出。
  红绿灯每 5 秒换一个颜色。

关键实现要点（都已实测确认）：
  * 相位必须由本脚本每帧 set_state 驱动 —— CARLA 的 set_green/yellow/red_time 不生效
  * 车辆必须用 autopilot（会等红灯/跟车/起步），绝不能用 enable_constant_velocity
  * 只让一辆车无视红灯：tm.ignore_lights_percentage(veh, 100.0)（必须指定车辆）

产出：视频、每帧真值 CSV、逐车统计、代表帧
"""
import csv
import math
import os
import sys
import time

import numpy as np
import carla
import cv2

# ---------------------------------------------------------------- 配置
HOST, PORT = "127.0.0.1", 2000
FPS = 20.0
DT = 1.0 / FPS
W, H, FOV = 1920, 1080, 90.0
OUTDIR = r"E:\output\_demo_scene"
os.makedirs(OUTDIR, exist_ok=True)

LIGHT_ID = 9                     # 旧实例编号，仅作参考；实际按停止线地理坐标找（见 find_light）
KNOWN_STOP = (-25.61, -64.76)    # 该灯控制的进口道停止线（road7 lane1/2）
STOP_X = -25.61                  # 停止线 x
LANE_Y = {1: -64.7, 2: -68.2}    # lane 1 = 左道, lane 2 = 右道（y 更小=更南=画面右侧）

PHASE_FRAMES = int(5.0 * FPS)    # 每 5 秒换色
START_X = 34.0                   # 起点：距停止线约 60 m
SPEED_MS = 32.0 / 3.6            # 32 km/h ≈ 8.89 m/s
RECORD_SECONDS = 26.0
CAM_BACK_M = 4.0                 # 录制机位相对用户 spectator 沿 +x 后移量（用户选定）

# 相位计划：先给一段"初始长红灯"，让守法车有一段明显的等待、且违规车在红灯中段越过停止线。
# 之后严格 5 秒一换。
#   t= 0..15s  Red      <- 两车驶入并到达停止线；左车在红灯下穿越（真·闯红灯），右车停下等
#   t=15..20s  Green    <- 右车起步通过停止线
#   t=20..25s  Yellow
#   t=25..30s  Red
G, Y, R = (carla.TrafficLightState.Green,
           carla.TrafficLightState.Yellow,
           carla.TrafficLightState.Red)
PHASE_PLAN = [R, R, R, G, Y, R]


def log(msg):
    print(msg, flush=True)


def find_light(world):
    """★2026-10-04：改为**按地理位置**找灯。

    CARLA 重启后红绿灯 ID 会重新分配（旧实例 light 9 -> 新实例 id 62），
    硬编码 LIGHT_ID 会在重启后失效。改为按该灯控制的停止线坐标匹配，对重启免疫。
    """
    best = None
    for a in world.get_actors().filter("traffic.traffic_light*"):
        d = 1e9
        try:
            for wp in a.get_stop_waypoints():
                sl = wp.transform.location
                d = min(d, math.dist((sl.x, sl.y), KNOWN_STOP))
        except Exception:
            pass
        if best is None or d < best[0]:
            best = (d, a)
    if best is None:
        return None
    log("  按地理位置选中 light id=%d（距已知停止线 %.2f m）" % (best[1].id, best[0]))
    return best[1]


class Proj:
    """已验证的投影（pitch 向下为负 -> Ry 用 -sin）"""
    def __init__(self, tf, w=W, h=H, fov=FOV):
        self.loc = np.array([tf.location.x, tf.location.y, tf.location.z])
        self.w, self.h = w, h
        self.f = w / (2 * math.tan(math.radians(fov) / 2))
        p, y, r = map(math.radians, (tf.rotation.pitch, tf.rotation.yaw, tf.rotation.roll))
        cz, sz = math.cos(y), math.sin(y)
        cp, sp = math.cos(p), math.sin(p)
        cx, sx = math.cos(r), math.sin(r)
        Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
        Ry = np.array([[cp, 0, -sp], [0, 1, 0], [sp, 0, cp]])
        Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
        self.R = Rz @ Ry @ Rx

    def project(self, p):
        vc = self.R.T @ (np.asarray(p, float) - self.loc)
        if vc[0] <= 1e-6:
            return None
        return (self.w / 2 + self.f * (vc[1] / vc[0]),
                self.h / 2 - self.f * (vc[2] / vc[0]), float(vc[0]))


def to_rgb_array(image):
    """★ 2026-10-04 修正：**不要**再加 [:, :, ::-1]。

    CARLA sensor 的 raw_data 字节序是 **BGRA**，所以
    `reshape(H,W,4)[:, :, :3]` 取到的**就是 BGR**，可直接交给 OpenCV。
    多加一次反转会变成 RGB 却被当成 BGR 用 -> 红蓝互换
    （实测：橙色路障被读成 B 主导、红灯被读成青蓝）。
    """
    a = np.frombuffer(image.raw_data, dtype=np.uint8).reshape(image.height, image.width, 4)[:, :, :3]
    return a.copy()


def main():
    client = carla.Client(HOST, PORT)
    client.set_timeout(30.0)
    world = client.get_world()
    m = world.get_map()
    spec_tf = world.get_spectator().get_transform()
    # 录制机位 = 用户 spectator 机位沿 +x 后移 CAM_BACK_M（用户 2026-10-04 选定，理由：
    # 守法车停在停止线时位于 lane 2（y 偏南 5.1 m），原地投影 u=1948 超出 1920 被右边缘裁掉；
    # 后移 4 m 后两车在停止线处 100% 完整入画，高度/俯角/朝向不变）
    cam_tf = carla.Transform(
        carla.Location(x=spec_tf.location.x + CAM_BACK_M,
                       y=spec_tf.location.y, z=spec_tf.location.z),
        spec_tf.rotation)

    # ---------------- 前置检查
    veh_existing = world.get_actors().filter("vehicle.*")
    if len(veh_existing) > 0:
        log("!! 场景里已有 %d 辆车，先清理" % len(veh_existing))
        for v in veh_existing:
            v.destroy()
    tl = find_light(world)
    if tl is None:
        log("找不到 light %d" % LIGHT_ID)
        return 1

    # 校验车道方向：lane 1 的 next() 应该指向 -x
    wp = m.get_waypoint(carla.Location(x=0.0, y=LANE_Y[1], z=2.0),
                        project_to_road=True, lane_type=carla.LaneType.Driving)
    nxt = wp.next(10.0)
    log("lane 探针: road=%d lane=%d yaw=%.1f  next-> (%s)"
        % (wp.road_id, wp.lane_id, wp.transform.rotation.yaw,
           ("%.1f,%.1f" % (nxt[0].transform.location.x, nxt[0].transform.location.y)) if nxt else "None"))
    wx = m.get_waypoint(carla.Location(x=0.0, y=LANE_Y[2], z=2.0),
                        project_to_road=True, lane_type=carla.LaneType.Driving)
    nx2 = wx.next(10.0)
    log("lane 探针: road=%d lane=%d yaw=%.1f  next-> (%s)"
        % (wx.road_id, wx.lane_id, wx.transform.rotation.yaw,
           ("%.1f,%.1f" % (nx2[0].transform.location.x, nx2[0].transform.location.y)) if nx2 else "None"))

    # ---------------- 同步模式
    settings = world.get_settings()
    settings.synchronous_mode = True
    settings.fixed_delta_seconds = DT
    world.apply_settings(settings)
    tm = client.get_trafficmanager(8000)
    tm.set_synchronous_mode(True)
    tm.set_global_distance_to_leading_vehicle(3.5)

    spawn_lane1 = m.get_waypoint(carla.Location(x=START_X, y=LANE_Y[1], z=2.0),
                                 project_to_road=True, lane_type=carla.LaneType.Driving)
    spawn_lane2 = m.get_waypoint(carla.Location(x=START_X, y=LANE_Y[2], z=2.0),
                                 project_to_road=True, lane_type=carla.LaneType.Driving)
    log("\n起点: lane1=(%.1f,%.1f) lane2=(%.1f,%.1f)  停止线 x=%.1f"
        % (spawn_lane1.transform.location.x, spawn_lane1.transform.location.y,
           spawn_lane2.transform.location.x, spawn_lane2.transform.location.y, STOP_X))

    bpl = world.get_blueprint_library()
    vehicles = {}
    def spawn(bp_id, wp_, tag):
        bp = bpl.filter(bp_id)[0]
        if bp.has_attribute("role_name"):
            bp.set_attribute("role_name", tag)
        tr = wp_.transform
        tr.location.z += 0.4
        a = world.spawn_actor(bp, tr)
        log("  生成 %-8s actor id=%-4d at (%.1f,%.1f)" % (tag, a.id, tr.location.x, tr.location.y))
        return a

    v_law = spawn("vehicle.audi.a2", spawn_lane2, "law_abiding")
    v_run = spawn("vehicle.tesla.model3", spawn_lane1, "red_runner")
    vehicles = {"law_abiding": v_law, "red_runner": v_run}

    for tag, a in vehicles.items():
        a.set_autopilot(True, tm.get_port())
        tm.vehicle_percentage_speed_difference(a, 0.0)
        tm.auto_lane_change(a, False)
        tm.distance_to_leading_vehicle(a, 3.5)
    tm.ignore_lights_percentage(v_run, 100.0)      # ★ 只有它无视红灯
    log("  已设定：red_runner 无视红灯 100%%；两者 autopilot")

    # 相机：与用户机位完全一致
    cbp = bpl.find("sensor.camera.rgb")
    cbp.set_attribute("image_size_x", str(W))
    cbp.set_attribute("image_size_y", str(H))
    cbp.set_attribute("fov", str(FOV))
    # 亮度对齐 CARLA 窗口（用户所见）：实测客户端 sensor 默认比窗口暗 16 灰阶、
    # 且偏冷（白线发青）。+0.5 档曝光把亮度差从 -16 收到 -1，色偏同时减小。
    try:
        cbp.set_attribute("exposure_compensation", "0.5")
    except Exception as e:
        log("  !! exposure_compensation 设置失败: %s" % e)
    cam = world.spawn_actor(cbp, cam_tf)
    frames = []
    cam.listen(lambda im: frames.append(im))
    proj = Proj(cam_tf)
    log("  录制机位: (%.3f,%.3f,%.3f) pitch=%.3f yaw=%.3f  (spectator +x %.0f m)"
        % (cam_tf.location.x, cam_tf.location.y, cam_tf.location.z,
           cam_tf.rotation.pitch, cam_tf.rotation.yaw, CAM_BACK_M))

    # ---------------- 录制循环
    csv_path = os.path.join(OUTDIR, "ground_truth.csv")
    fcsv = open(csv_path, "w", newline="", encoding="utf-8")
    wtr = csv.writer(fcsv)
    wtr.writerow(["frame", "t_sec", "light_state", "phase_idx",
                  "tag", "actor_id", "x", "y", "speed_kmh",
                  "dist_to_stop_m", "crossed_stop", "in_frame", "u", "v"])

    # 代表帧（含关键瞬间：驶入、到达停止线、闯红灯越线、绿灯起步、通过对面）
    MARKERS = [0, 60, 120, 160, 180, 200, 220, 260, 300, 320, 340, 380, 440, 500]

    total = int(RECORD_SECONDS * FPS)
    t0 = world.get_snapshot().timestamp.elapsed_seconds
    stats = {t: {"max": 0.0, "sum": 0.0, "n": 0, "stop_frames": 0, "cross_t": None, "in_frame": 0}
             for t in vehicles}
    sample_frames = {}
    log("\n开始录制 %d 帧 / %.0f 秒 ..." % (total, RECORD_SECONDS))

    for i in range(total):
        phase_i = (i // PHASE_FRAMES)
        if phase_i >= len(PHASE_PLAN):
            phase_i = len(PHASE_PLAN) - 1
        commanded = PHASE_PLAN[phase_i]        # ★ 以命令值为真值（set_state 是异步的）
        tl.set_state(commanded)                # ★ 每帧强制相位
        world.tick()
        t = world.get_snapshot().timestamp.elapsed_seconds - t0
        state = str(commanded)

        for tag, a in vehicles.items():
            tfv = a.get_transform()
            v = a.get_velocity()
            spd = 3.6 * math.sqrt(v.x ** 2 + v.y ** 2 + v.z ** 2)
            x, y = tfv.location.x, tfv.location.y
            dist = x - STOP_X                       # >0 表示还没到停止线
            crossed = 1 if x < STOP_X else 0
            pr = proj.project([x, y, tfv.location.z + 0.8])
            in_frame = 1 if (pr and 0 <= pr[0] < W and 0 <= pr[1] < H) else 0
            st = stats[tag]
            if spd > st["max"]:
                st["max"] = spd
            st["sum"] += spd
            st["n"] += 1
            if spd < 0.5:
                st["stop_frames"] += 1
            if crossed and st["cross_t"] is None:
                st["cross_t"] = round(t, 2)
            if in_frame:
                st["in_frame"] += 1
            wtr.writerow([i, round(t, 3), state, phase_i, tag, a.id,
                          round(x, 3), round(y, 3), round(spd, 2),
                          round(dist, 3), crossed, in_frame,
                          round(pr[0], 1) if pr else "", round(pr[1], 1) if pr else ""])
        if i % 40 == 0:
            log("   %4d/%d  t=%5.2fs  light=%-6s  law=%.1fkm/h@x%.0f  run=%.1fkm/h@x%.0f"
                % (i, total, t, state,
                   stats["law_abiding"]["sum"] / max(1, stats["law_abiding"]["n"]),
                   vehicles["law_abiding"].get_transform().location.x,
                   stats["red_runner"]["sum"] / max(1, stats["red_runner"]["n"]),
                   vehicles["red_runner"].get_transform().location.x))
        # 记录代表帧时刻
        if i in MARKERS:
            sample_frames[i] = len(frames) - 1

    fcsv.close()
    time.sleep(1.0)
    cam.stop()
    cam.destroy()

    # ---------------- 写视频（★ 用无损编码）
    # 为什么必须无损：mp4v (MPEG-4 Part 2) 会把颜色压坏 —— 实测在饱和内容上
    # 平均差 44/255，并导致 YOLO 对远处车辆的置信度从 0.676 掉到 0.418。
    # FFV1 实测与原始帧 逐像素差 = 0，规格 1920x1080/20fps 下约 40-60 KB/帧。
    vid = os.path.join(OUTDIR, "red_light_demo_lossless.mkv")
    if frames:
        vw = cv2.VideoWriter(vid, cv2.VideoWriter_fourcc(*"FFV1"), FPS, (W, H))
        if not vw.isOpened():
            raise RuntimeError("FFV1 编码器不可用，无法保证颜色保真")
        for im in frames:
            vw.write(to_rgb_array(im))
        vw.release()
        log("\n无损视频: %s  (%d 帧, %.1f MB)"
            % (vid, len(frames), os.path.getsize(vid) / 1e6))
    else:
        log("\n!! 没有抓到帧")

    # ---------------- 统计
    log("\n================ 录制结果 ================")
    for tag, st in stats.items():
        avg = st["sum"] / max(1, st["n"])
        log("  %-12s avg=%5.1f km/h  max=%5.1f km/h  停车帧数=%d  越过停止线@t=%s  画面内帧数=%d"
            % (tag, avg, st["max"], st["stop_frames"], st["cross_t"], st["in_frame"]))

    # 代表帧（含关键瞬间：驶入、到达停止线、闯红灯越线、绿灯起步、通过对面）
    STAR = {"law_abiding": (0, 255, 0), "red_runner": (0, 0, 255)}
    for mark, idx in sorted(sample_frames.items()):
        if not (0 <= idx < len(frames)):
            continue
        full = to_rgb_array(frames[idx])
        cv2.imwrite(os.path.join(OUTDIR, "frame_%03d.png" % mark), full)
        # 标注版：停止线 + 路口中心 + 两车位置
        ov = full.copy()
        for nm, pt, col in (("STOP", [STOP_X, LANE_Y[1], 0.15], (0, 255, 255)),
                            ("STOP2", [STOP_X, LANE_Y[2], 0.15], (0, 255, 255)),
                            ("JUNCTION", [-29.09, -64.80, 0.0], (255, 128, 0))):
            r = proj.project(pt)
            if r and 0 <= r[0] < W and 0 <= r[1] < H:
                cv2.drawMarker(ov, (int(r[0]), int(r[1])), col, cv2.MARKER_CROSS, 30, 3)
                cv2.putText(ov, nm, (int(r[0]) + 12, int(r[1]) - 12),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, col, 2, cv2.LINE_AA)
        for tag, a in vehicles.items():
            tfv = a.get_transform()
            r = proj.project([tfv.location.x, tfv.location.y, tfv.location.z + 0.8])
            v = a.get_velocity()
            spd = 3.6 * math.sqrt(v.x ** 2 + v.y ** 2 + v.z ** 2)
            if r and 0 <= r[0] < W and 0 <= r[1] < H:
                col = STAR.get(tag, (255, 255, 255))
                cv2.drawMarker(ov, (int(r[0]), int(r[1])), col, cv2.MARKER_TILTED_CROSS, 40, 4)
                cv2.putText(ov, "%s %.0fkm/h" % (tag, spd), (int(r[0]) + 14, int(r[1]) + 34),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.85, col, 2, cv2.LINE_AA)
        cv2.imwrite(os.path.join(OUTDIR, "frame_%03d_marked.png" % mark), ov)

    # ---------------- 清理
    for a in vehicles.values():
        try:
            a.destroy()
        except Exception:
            pass
    tm.set_synchronous_mode(False)
    settings.synchronous_mode = False
    settings.fixed_delta_seconds = None
    world.apply_settings(settings)
    log("\n已清理车辆并复位同步模式。真值: %s" % csv_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
