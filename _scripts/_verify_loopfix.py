"""隔离验证：给视频源加"循环回开头"是否能持续产出帧

不修改项目代码，只模拟 _detection_loop 的读取逻辑：
  A. 现状（读完即失败）→ 观察 3 秒内能读到多少帧
  B. 加循环回开头        → 观察 3 秒内能读到多少帧
证明修复方向有效。
"""

import time

import cv2

VIDEO = r"E:\output\1\test_assets\traffic_videos\test1.mp4"
FRAME_RATE = 3          # 项目 Config.FRAME_RATE
DURATION = 3.0


def run(mode: str):
    cap = cv2.VideoCapture(VIDEO)
    total_read = 0
    processed = 0
    loops = 0
    fails_in_a_row = 0
    t0 = time.time()
    last_process = t0
    interval = 1.0 / FRAME_RATE

    while time.time() - t0 < DURATION:
        ret, frame = cap.read()
        if not ret:
            fails_in_a_row += 1
            if mode == "loop":
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                loops += 1
                time.sleep(0.005)
                continue
            else:
                time.sleep(0.05)
                continue
        fails_in_a_row = 0
        total_read += 1
        now = time.time()
        if now - last_process >= interval:
            last_process = now
            processed += 1
    cap.release()
    print(f"  [{mode:5s}] {DURATION}s 内: 读帧={total_read}  被处理={processed}  "
          f"连续失败={fails_in_a_row}  回到开头次数={loops}")
    return total_read, processed


print("=" * 74)
print(f"模拟 _detection_loop（FRAME_RATE={FRAME_RATE}, 运行 {DURATION}s）")
print("=" * 74)
a = run("now")
b = run("loop")
print()
print("=" * 74)
print(f"  现状: 读 {a[0]} 帧 / 处理 {a[1]} 帧")
print(f"  循环: 读 {b[0]} 帧 / 处理 {b[1]} 帧")
print(f"  => 修复后处理帧数提升: {b[1] / max(a[1], 1):.1f}x")
print("=" * 74)
