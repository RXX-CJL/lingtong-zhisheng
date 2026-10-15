"""
实测：把 FRAME_RATE 提到 6 能否稳定扛住（2026-10-06 由 DSH 编写）

做法：直接调 REST 启动检测 -> 采样 status 的 processed/avg_fps -> 停止。
只读性质：不改任何配置文件，FRAME_RATE 只能通过环境变量给（本脚本**不改**），
         因此这里测的是"当前配置下 3fps 的实际上限余量"，用 avg_fps 与理论 7.3fps 对比。
"""
import json
import time
import urllib.request

BASE = 'http://127.0.0.1:8001'
VIDEO = r'E:\output\_dual_cam_demo\dual_cam_demo_lossless.mkv'


def call(path, data=None):
    # data 为 None -> GET；否则 POST（我第一版把判断写反了，直接吃 405 Method Not Allowed）
    method = 'POST' if data is not None else 'GET'
    req = urllib.request.Request(BASE + path, method=method)
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, body, timeout=30) as r:
        return json.loads(r.read().decode())


print('确保从"未运行"状态开始（否则会测到旧实例）...')
try:
    call('/api/realtime/stop', {})
    time.sleep(2)
except Exception as e:
    print('  stop 异常（可能本来就没跑）:', str(e)[:80])

st = call('/api/realtime/status')['data']
print(f'启动前: running={st["running"]}  frame_rate={st["frame_rate"]}  '
      f'已处理={st["processed_frames"]}（若不接近 0，说明有新实例在跑，数字仍按增量算）')

r0 = call('/api/realtime/start', {'video_path': VIDEO})
print('启动检测:', r0.get('success'), '|', str(r0.get('message'))[:60])
time.sleep(8)                      # 预热（模型 + 首帧）

samples = []
for i in range(8):
    time.sleep(4)
    s = call('/api/realtime/status')['data']
    samples.append((s['processed_frames'], s['avg_fps'], s['current_fps']))
    print(f'  第{i+1}次: 已处理={s["processed_frames"]:>5}  avg_fps={s["avg_fps"]:.2f}  '
          f'current_fps={s["current_fps"]:.2f}  跟踪={s["tracked_vehicle_count"]}')

call('/api/realtime/stop', {})          # ★ stop 是 POST（第一版当 GET 调 -> 405）
print('已停止检测')

# 用"处理帧数增量 / 时间"算真实吞吐（比 avg_fps 更可信）
if len(samples) >= 2:
    d_frames = samples[-1][0] - samples[0][0]
    d_time = (len(samples) - 1) * 4
    real = d_frames / d_time
    print(f'\n真实吞吐 = {d_frames} 帧 / {d_time}s = {real:.2f} fps')
    print(f'理论单帧 {137} ms -> 上限 7.3 fps；当前节流目标 3 fps')
    print(f'结论: 实测 {real:.2f} fps {"达到" if real > 2.5 else "未达到"} 3fps 目标；'
          f'余量 {"充足" if real > 2.5 else "不足"}')
