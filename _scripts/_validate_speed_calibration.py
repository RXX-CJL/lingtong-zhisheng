# -*- coding: utf-8 -*-
"""测速标定端到端验证（真实渲染帧 + YOLO 检测框 + CARLA 世界坐标）

★为什么需要这个脚本（2026-10-06 由 DSH 建立）
  `E:\\output\\_dual_cam_demo\\ground_truth_dual.csv` 里的 **cam1_u / cam1_v 不是测量值**：
  它们是 `_scripts\\_dual_cam_demo.py:217`（`proj1.project(...)`）算出来、
  在 `:231` 直接写进 CSV 的**模型输出**。用同一份 `Proj` 重算那 580 行，
  u 方向中位误差只有 0.51 px —— 也就是说那份"真值"是**自证**的，
  拿它验证标定 = 用一个模型验证另一个模型（这正是此前 6 次修复失败的原因）。
  同理，整个 CSV 里 `cam1_in=1` 的 580 行，只覆盖"车已经开过相机之后"的时段
  （车驶近的全过程被标成 0 丢掉了）。

  本脚本改用唯一可信的真值组合：
     ① 真实渲染帧  `_dual_cam_demo\\cam1_XXX.png`（CARLA 相机实拍）
     ② YOLO(yolov8s) 检测框**底边中点** ≈ 轮胎触地点（真实测量，非模型输出）
     ③ CSV 里的 `(x, y)` —— 直读 CARLA actor transform，**这两列可信**

  验证三件事：
     A. 反投影精度：检测框底边 -> 地面点，与 CARLA 真值比（扣掉"车尾偏移"）
     B. 速度精度：两个时刻的地面距离 / Δt，与 CARLA 真值速度比
     C. 对照：`_dual_cam_demo.Proj` 那份错误基（fwd 朝上）在同一批点上的像素误差

用法（约 1 分钟，需 GPU/CPU 均可）：
    & 'C:\\miniconda\\envs\\zhitong-gpu\\python.exe' -B E:\\output\\_scripts\\_validate_speed_calibration.py

判定标准（脚本末尾会打印 PASS/FAIL）：
    A 段反投影平均误差 < 1.5 m ；B 段匀速样本 |误差| < 15%
"""
import csv
import math
import os
import sys

import numpy as np

sys.path.insert(0, r"E:\output\1\api")
import speed_calibration as SC  # noqa: E402

# ---- CARLA 演示机位（来自 _scripts\_dual_cam_demo.py 的 cam1_tf）----------
CAM = np.array([-15.720, -63.145, 5.732])
PITCH, YAW = -23.445, 179.536
W, H, FOV = 1920, 1080, 90.0
# camera_height_m 用"离路面"高度；此处路面 z≈0.7 -> 用世界 z 作为平面高度时
# 等价于把地面平面取在 z=0（平移不变），故这里用 5.732。
CAM_H = 5.732

CSV = r"E:\output\_dual_cam_demo\ground_truth_dual.csv"
IMGDIR = r"E:\output\_dual_cam_demo"
YOLO_MODEL = r"E:\output\1\zhitong\training\models\yolov8s.pt"
MARKERS = [180, 200, 220, 260, 300, 320, 360, 440, 500]
# 车长（用于把"车尾触地"换算回"车辆原点"）：特斯拉 Model3 / 奥迪 A2
LEN = {"red_runner": 4.69, "law_abiding": 3.80}
VEH = {"car", "truck", "bus"}


def load_rows():
    rows = list(csv.DictReader(open(CSV, encoding="utf-8")))
    byf = {}
    for r in rows:
        byf.setdefault(int(r["frame"]), []).append(r)
    return byf


def local_xy(x, y):
    """世界 -> 相机局部（前向 X, 右向 Y）"""
    yr = math.radians(YAW)
    d = np.array([x - CAM[0], y - CAM[1]])
    return (float(d @ np.array([math.cos(yr), math.sin(yr)])),
            float(d @ np.array([-math.sin(yr), math.cos(yr)])))


def forward_project(x, y, z, pitch=PITCH, yaw=YAW, h=CAM_H):
    """正确基的前向投影（本脚本自带，用于与真实渲染像素对照）"""
    p, yy = math.radians(pitch), math.radians(yaw)
    cp, sp, cy, sy = math.cos(p), math.sin(p), math.cos(yy), math.sin(yy)
    fwd = np.array([cp * cy, cp * sy, sp])
    up = np.array([-sp * cy, -sp * sy, cp])
    right = np.array([-sy, cy, 0.0])
    f = W / (2.0 * math.tan(math.radians(FOV) / 2.0))
    d = np.array([x - CAM[0], y - CAM[1], z - h])
    zc = float(d @ fwd)
    if zc <= 1e-6:
        return None
    return (W / 2.0 + f * float(d @ right) / zc,
            H / 2.0 - f * float(d @ up) / zc)


def demo_project(x, y, z):
    """旧 _dual_cam_demo.Proj 的错误基（fwd/up 的 z 分量都写反）——用于对照"""
    p, yy = math.radians(PITCH), math.radians(YAW)
    cp, sp, cy, sy = math.cos(p), math.sin(p), math.cos(yy), math.sin(yy)
    fwd = np.array([cp * cy, cp * sy, -sp])
    up = np.array([-sp * cy, -sp * sy, cp])
    right = np.array([-sy, cy, 0.0])
    f = W / (2.0 * math.tan(math.radians(FOV) / 2.0))
    d = np.array([x - CAM[0], y - CAM[1], z - CAM_H])
    zc = float(d @ fwd)
    if zc <= 1e-6:
        return None
    return (W / 2.0 + f * float(d @ right) / zc,
            H / 2.0 - f * float(d @ up) / zc)


def rear_xy(byf, fr, tag):
    """车辆原点 -> 车尾触地点（沿行驶方向后退半个车长）"""
    ks = sorted(byf)
    i = ks.index(fr)
    cur = [q for q in byf[fr] if q["tag"] == tag][0]
    a = [q for q in byf[ks[min(i + 3, len(ks) - 1)]] if q["tag"] == tag][0]
    b = [q for q in byf[ks[max(i - 3, 0)]] if q["tag"] == tag][0]
    hx, hy = float(a["x"]) - float(b["x"]), float(a["y"]) - float(b["y"])
    n = math.hypot(hx, hy) or 1.0
    return (float(cur["x"]) - hx / n * LEN[tag] / 2.0,
            float(cur["y"]) - hy / n * LEN[tag] / 2.0)


def main():
    byf = load_rows()
    cal = SC.SpeedCalibrator(dict(camera_height_m=CAM_H, camera_pitch_deg=PITCH,
                                  fov_deg=FOV, camera_yaw_deg=YAW),
                             frame_width=int(W), frame_height=int(H))
    print("=" * 78)
    print("测速标定端到端验证（真实渲染帧 + YOLO + CARLA 世界坐标）")
    print("=" * 78)
    print("标定器: method=%s calibrated=%s horizon_y=%.1f" % (
        cal.method, cal.calibrated, cal.horizon_y() or -1))
    print("相机  : 世界(%0.3f,%0.3f,%0.3f) pitch=%.3f yaw=%.3f fov=%.1f  %dx%d" % (
        CAM[0], CAM[1], CAM[2], PITCH, YAW, FOV, W, H))
    print("真值  : CSV 的 (x,y) 可信；cam1_u/v **不可信**（是模型输出，仅用于对照）\n")

    from ultralytics import YOLO
    model = YOLO(YOLO_MODEL)

    detections = {}     # (frame, tag) -> (u, v_bottom)
    px_err = {"correct": [], "demo": []}
    matched = 0
    for fr in MARKERS:
        p = os.path.join(IMGDIR, "cam1_%03d.png" % fr)
        if not os.path.exists(p) or fr not in byf:
            continue
        res = model.predict(p, imgsz=1280, conf=0.25, verbose=False)[0]
        boxes = []
        for bx in res.boxes:
            if res.names[int(bx.cls)] in VEH:
                x1, y1, x2, y2 = [float(t) for t in bx.xyxy[0]]
                boxes.append(((x1 + x2) / 2.0, y2, (x1 + x2) / 2.0, (y1 + y2) / 2.0))
        used = set()
        for r in byf[fr]:
            tag = r["tag"]
            x, y = float(r["x"]), float(r["y"])
            pred = forward_project(x, y, 0.72)
            if pred is None:
                continue
            best, bd = None, 1e9
            for k, b in enumerate(boxes):
                if k in used:
                    continue
                dd = math.dist(b[2:], pred)
                if dd < bd:
                    best, bd = k, dd
            if best is None or bd > 400:
                continue
            used.add(best)
            detections[(fr, tag)] = (boxes[best][0], boxes[best][1])
            matched += 1
            # 与两种基的像素误差对照（对检测框中心）
            for nm, fn in (("correct", forward_project), ("demo", demo_project)):
                pr = fn(x, y, 0.72)
                if pr:
                    px_err[nm].append(math.dist(pr, boxes[best][2:]))
    print("匹配到 %d 组「车辆世界坐标 <-> YOLO 检测框」（%d 帧）\n" % (matched, len(MARKERS)))

    print("-" * 78)
    print("A) 反投影精度：检测框底边 -> 地面  vs  CARLA 车尾真值")
    print("-" * 78)
    errs = []
    for (fr, tag) in sorted(detections):
        u, v = detections[(fr, tag)]
        g = cal.ground_point(u, v)
        if g is None:
            print("  fr%-4d %-12s 反投影失败" % (fr, tag))
            continue
        rx, ry = rear_xy(byf, fr, tag)
        tx, ty = local_xy(rx, ry)
        e = math.hypot(g[0] - tx, g[1] - ty)
        errs.append(e)
        print("  fr%-4d %-12s 反解=(%7.2f,%6.2f)  真值=(%7.2f,%6.2f)  误差=%.2f m"
              % (fr, tag, g[0], g[1], tx, ty, e))
    if errs:
        errs.sort()
        a_mean = sum(errs) / len(errs)
        print("  -> 平均 %.2f m  中位 %.2f  p90 %.2f  (n=%d)"
              % (a_mean, errs[len(errs) // 2], errs[int(0.9 * len(errs))], len(errs)))

    print("\n" + "-" * 78)
    print("B) 速度：反投影法 vs CARLA 真值速度（只用匀速样本）")
    print("-" * 78)
    spd_err = []
    for tag in ("red_runner", "law_abiding"):
        ks = [f for f in sorted(detections_set(detections)) if (f, tag) in detections]
        for a, b in zip(ks, ks[1:]):
            ra = [q for q in byf[a] if q["tag"] == tag][0]
            rb = [q for q in byf[b] if q["tag"] == tag][0]
            dt = float(rb["t_sec"]) - float(ra["t_sec"])
            if dt <= 0:
                continue
            v_a, v_b = float(ra["speed_kmh"]), float(rb["speed_kmh"])
            d_true = math.hypot(float(rb["x"]) - float(ra["x"]),
                                float(rb["y"]) - float(ra["y"]))
            v_true = d_true / dt * 3.6
            if v_true < 5 or abs(v_b - v_a) > 0.25 * max(v_a, 1.0):
                continue      # 太慢 / 明显加减速 -> 与"区间平均"不可比
            d_meas = cal.ground_distance(detections[(a, tag)], detections[(b, tag)])
            if d_meas is None:
                continue
            v_meas = d_meas / dt * 3.6
            err = (v_meas - v_true) / v_true * 100.0
            spd_err.append(abs(err))
            print("  %-12s %3d>%-3d dt=%.1fs  真值=%5.1f km/h  实测=%5.1f km/h  误差=%+6.1f%%"
                  % (tag, a, b, dt, v_true, v_meas, err))
    if spd_err:
        print("  -> 平均绝对误差 %.1f%%   最大 %.1f%%  (n=%d)"
              % (sum(spd_err) / len(spd_err), max(spd_err), len(spd_err)))

    print("\n" + "-" * 78)
    print("C) 对照：两种相机基对同一批检测框的像素误差（越小越好）")
    print("-" * 78)
    for nm, label in (("correct", "正交俯视基(fwd_z=+sin p, up_z=+cos p)  ★本次修正"),
                      ("demo", "_dual_cam_demo.Proj(fwd_z=-sin p)  ✗已知错误基")):
        e = sorted(px_err[nm])
        if e:
            print("  %-46s 平均 %7.1f px  中位 %7.1f  p90 %7.1f" % (
                label, sum(e) / len(e), e[len(e) // 2], e[int(0.9 * len(e))]))

    print("\n" + "=" * 78)
    ok_a = bool(errs) and (sum(errs) / len(errs)) < 1.5
    ok_b = bool(spd_err) and (sum(spd_err) / len(spd_err)) < 15.0
    print("判定: A 反投影平均误差 < 1.5 m -> %s    B 速度平均误差 < 15%% -> %s"
          % ("PASS" if ok_a else "FAIL", "PASS" if ok_b else "FAIL"))
    print("=" * 78)
    return 0 if (ok_a and ok_b) else 1


def detections_set(detections):
    return sorted({f for (f, _t) in detections})


if __name__ == "__main__":
    sys.exit(main())
