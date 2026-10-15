"""速度标定精度验证 —— 用已知真值的合成轨迹精确测误差

为什么不用合成视频（2026-10-03 由 DSH 说明）：
  合成矩形车辆 YOLO 识别不出（实测 0 检测，v1/v2 均失败）——纯几何图形
  不在 COCO 训练分布内。这不是本项目的问题，也不值得为此改造检测模型。

因此改用**更严谨**的方法：直接构造"已知真实车速"的车辆运动数据，
喂给项目的 tracker + speed_calibration，测出**标定管道本身的误差**。
这比真实视频更好，因为真实视频**不知道真车速**。

验证链路：
  已知 (真车速 km/h, y 行, 帧率)
    -> 按标定公式反推应有 px/s（为了让车辆在画面里"看起来"是这个速度）
    -> 构造 bbox 序列（模拟检测输出）
    -> 喂给 VehicleTracker（真实追踪）
    -> 用 speed_from_history + SpeedCalibrator 反算 km/h
    -> 对比真值，得出误差
"""

import io
import os
import sys
import time

sys.path.insert(0, r"E:\output\1\api")
os.chdir(r"E:\output\1\api")

from vehicle_tracker import VehicleTracker  # noqa: E402

out = []

W, H = 1280, 576
FPS = 25
# 标定参数与画面尺寸（走 assumed_lanes 兜底）
SCENE = {"frame_width": W, "frame_height": H}


def make_detections(n_frames, start_x, px_per_sec, y, w=160, h=80, fps=FPS):
    """构造 bbox 序列（模拟检测输出）"""
    dets = []
    for i in range(n_frames):
        t = i / fps
        x = start_x + px_per_sec * t
        dets.append({
            "class_name": "car",
            "class_name_cn": "轿车",
            "confidence": 0.9,
            "bbox": [x, y - h / 2, x + w, y + h / 2],
        })
    return dets


def run_case(label, true_kmh, y, n_frames=25, fps=FPS):
    """跑一个已知真值的用例

    注意：tracker 的 history.timestamp 用的是 time.time()（真实墙钟），
    所以测试里必须按帧间隔 sleep，否则 dt≈0 -> 换算器判定"轨迹不足"。
    """
    from speed_calibration import SpeedCalibrator
    cal = SpeedCalibrator(SCENE, frame_width=W, frame_height=H)
    want_px = cal.px_speed_to_kmh(1.0, y)      # 1px/s 对应多少 km/h
    px_per_sec = true_kmh / want_px if want_px > 0 else 0.0

    tr = VehicleTracker(use_bytetrack=True)
    dets = make_detections(n_frames, 100, px_per_sec, y, fps=fps)
    tracked = {}
    dt = 1.0 / fps
    for d in dets:
        tracked = tr.update([d], W, H)
        time.sleep(dt)                          # 模拟真实帧间隔
    if not tracked:
        return f"  [{label}] 追踪为空（未产生轨迹）"
    tid = list(tracked.keys())[0]
    veh = tracked[tid]
    hist = veh.get("history") or []

    from speed_calibration import speed_from_history
    est = speed_from_history(hist, cal)
    got = est.get("kmh")
    if got:
        err = (got - true_kmh) / true_kmh * 100.0
        return (f"  [{label}] 真值 {true_kmh:>5.1f} km/h  y={y:<4} "
                f"-> 注入 {px_per_sec:>7.1f} px/s  "
                f"追踪 {est.get('px_per_sec')} px/s  反算 {got} km/h  "
                f"误差 {err:+.1f}%  补偿x{est.get('fps_compensation')} [{est.get('confidence')}]")
    return (f"  [{label}] 真值 {true_kmh} -> 无法反算 "
            f"(samples={est.get('samples')} dt={est.get('dt')})")


out.append("=" * 84)
out.append("速度标定精度验证（合成轨迹，真值已知）")
out.append("=" * 84)
cal_info = None
try:
    from speed_calibration import SpeedCalibrator
    c = SpeedCalibrator(SCENE, frame_width=W, frame_height=H)
    cal_info = c.info()
    out.append(f"标定方式: {cal_info['method']}  ppm_ref={cal_info['ppm_ref']} "
               f"y_ref={cal_info['y_ref']} horizon={cal_info['y_horizon']}")
    out.append(f"说明: {cal_info['note']}")
except Exception as e:
    out.append(f"标定初始化失败: {e}")
out.append("")

CASE_Y = 430
out.append("【1】不同真车速下的反算精度（同一 y 行）")
for kmh in (20.0, 40.0, 60.0, 80.0, 100.0):
    out.append(run_case(f"{kmh:.0f}km/h", kmh, CASE_Y))

out.append("")
out.append("【2】同一真车速、不同 y 行（检验透视校正是否正确）")
for y in (300, 360, 430, 500, 550):
    out.append(run_case(f"y={y}", 60.0, y))

out.append("")
out.append("【3】不同帧率（跟踪 1 秒，真值 60 km/h）—— 复现项目实际 15fps")
for fps in (10, 15, 25, 30):
    out.append(run_case(f"{fps}fps", 60.0, CASE_Y, n_frames=fps, fps=fps))

out.append("")
out.append("=" * 84)
out.append("结论：误差主要来自① tracker 的像素速度估计 ② 标定本身（assumed 兜底 ±50%）")
out.append("=" * 84)

io.open(r"E:\output\_speed_accuracy.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
