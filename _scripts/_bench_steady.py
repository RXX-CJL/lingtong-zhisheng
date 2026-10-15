"""
干净的重复计时（2026-10-06 由 DSH 编写）—— 排除"首次调用含 CUDA 预热"的干扰。

前两次测试的教训：
  · 第一次传 np.ndarray -> detect_with_yolo 直接 success=False（要 base64 data URL）
  · 第二次只跑 1 次 multi_model_detect -> 得到 1715ms，那是**冷启动**（CUDA kernel/cudnn
    benchmark 首次编译），不是稳态耗时
本脚本：同一帧连续跑 5 次，报每一次，取后 4 次的中位数作为稳态值。
"""
import base64
import sys
import time

sys.path.insert(0, r'E:\output\1\api')
import cv2

cap = cv2.VideoCapture(r'E:\output\_dual_cam_demo\dual_cam_demo_lossless.mkv')
cap.set(cv2.CAP_PROP_POS_FRAMES, 260)
_, frame = cap.read()
cap.release()
H, W = frame.shape[:2]

_, buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
URL = 'data:image/jpeg;base64,' + base64.b64encode(buf.tobytes()).decode('ascii')

from image_recognizer import init_all_models, multi_model_detect
init_all_models()

print(f'输入帧 {W}x{H}, data URL {len(URL)/1024:.0f} KB')
print('\n=== multi_model_detect 连续 5 次 ===')
ts = []
for i in range(5):
    t = time.time()
    r = multi_model_detect(URL, conf_threshold=0.5)
    dt = (time.time() - t) * 1000
    ts.append(dt)
    print(f'  第{i+1}次: {dt:7.1f} ms   检出 {len(r.get("all_detections") or [])} 个'
          + ('   <- 含冷启动' if i == 0 else ''))
steady = sorted(ts[1:])[len(ts[1:]) // 2]
print(f'\n稳态中位（去掉首次）= {steady:.1f} ms  ->  上限 {1000/steady:.1f} fps')

# 单模型对照（同样取稳态）
from image_recognizer import detect_with_yolo
print('\n=== 单模型稳态对照 ===')
for key in ['vehicle', 'traffic_light', 'helmet', 'lane', 'license_plate']:
    t = []
    for i in range(3):
        t0 = time.time()
        rr = detect_with_yolo(URL, key, 0.5)
        t.append((time.time() - t0) * 1000)
    print(f'  {key:<15} {sorted(t)[1]:7.1f} ms   检出 {len(rr.get("detections") or [])}')

print(f'\n结论：稳态 multi_model_detect = {steady:.0f} ms/帧')
print(f'      当前 Config.FRAME_RATE=3 -> 每帧预算 333 ms，'
      f'{"有余量" if steady < 333 else "已超预算！"}')
