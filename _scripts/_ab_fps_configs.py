"""
对照实验：不同「模型序列 + 帧率 + imgsz」下的真实吞吐（2026-10-06 由 DSH 编写）

为什么要这个脚本：用户反馈"识别框帧率太低、跟不上车"。
实测证明**拍脑袋调 FRAME_RATE 没用**（提到 6 也只跑出 2.96fps），
因为天花板是"单帧总成本"，而每帧要串行跑 5 个模型、其中 license_plate 的
模型文件根本不存在（回退 COCO，检出消防栓/盆栽等垃圾，白花 ~30ms/帧）。

本脚本负责：把候选配置各跑一遍，输出**同一视频、同一时长下的真实吞吐**，
让"选哪套参数"变成有数据的选择题，而不是感觉题。

用法（需后端可重启权限；脚本会自己重启后端）：
  & 'C:\miniconda\envs\zhitong-gpu\python.exe' -B E:\output\_scripts\_ab_fps_configs.py
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

API = r'E:\output\1\api'
ROOT = r'E:\output\1'
PY = r'C:\miniconda\envs\zhitong-gpu\python.exe'
VIDEO = r'E:\output\_dual_cam_demo\dual_cam_demo_lossless.mkv'
BASE = 'http://127.0.0.1:8001'
LOGS = os.path.join(API, 'output', 'logs')

CONFIGS = [
    ('① 原始配置',                    {'FRAME_RATE': '3',  'YOLO_IMGSZ': '1280', 'YOLO_MODEL_SEQUENCE': ''}),
    ('② 只提帧率',                    {'FRAME_RATE': '6',  'YOLO_IMGSZ': '1280', 'YOLO_MODEL_SEQUENCE': ''}),
    ('③ 提帧率+降分辨率',              {'FRAME_RATE': '6',  'YOLO_IMGSZ': '960',  'YOLO_MODEL_SEQUENCE': ''}),
    ('④ ③+裁模型(vehicle,tl,helmet)', {'FRAME_RATE': '6',  'YOLO_IMGSZ': '960',  'YOLO_MODEL_SEQUENCE': 'vehicle,traffic_light,helmet'}),
    ('⑤ ④+再裁头盔(vehicle,tl)',      {'FRAME_RATE': '8',  'YOLO_IMGSZ': '960',  'YOLO_MODEL_SEQUENCE': 'vehicle,traffic_light'}),
]


def call(path, data=None, timeout=30):
    method = 'POST' if data is not None else 'GET'
    req = urllib.request.Request(BASE + path, method=method)
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, body, timeout=timeout) as r:
        return json.loads(r.read().decode())


def port_busy():
    out = subprocess.run(['netstat', '-ano'], capture_output=True, text=True).stdout
    return ':8001' in out and 'LISTENING' in out


def restart_backend(env_extra):
    # 先停
    try:
        call('/api/realtime/stop', {})
    except Exception:
        pass
    try:
        out = subprocess.run(
            ['powershell', '-NoProfile', '-Command',
             "(Get-NetTCPConnection -State Listen -LocalPort 8001 -EA SilentlyContinue)"
             ".OwningProcess | ForEach-Object { Stop-Process -Id $_ -Force }"],
            capture_output=True, text=True)
    except Exception as e:
        print('  停止失败:', e)
    for _ in range(30):
        if not port_busy():
            break
        time.sleep(0.5)

    env = dict(os.environ)
    env['PYTHONPATH'] = os.path.join(API) + ';' + ROOT
    for k, v in env_extra.items():
        if v:
            env[k] = v
        else:
            env.pop(k, None)
    subprocess.Popen(
        [PY, '-m', 'uvicorn', 'app:app', '--host', '127.0.0.1', '--port', '8001'],
        cwd=ROOT, env=env,
        stdout=open(os.path.join(LOGS, 'backend_stdout.log'), 'w', encoding='utf-8'),
        stderr=open(os.path.join(LOGS, 'backend_stderr.log'), 'w', encoding='utf-8'),
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    for _ in range(60):
        try:
            if call('/health', timeout=3).get('status') == 'healthy':
                return True
        except Exception:
            time.sleep(1)
    return False


def measure(seconds=24):
    # ★重启后端会让在途连接被重置（WinError 10054），所以每一步都要容错 ——
    #   第一版没兜住，脚本跑到一半就崩了。
    def safe(fn, *a, **kw):
        for attempt in range(3):
            try:
                return fn(*a, **kw)
            except Exception as e:
                if attempt == 2:
                    print(f'    (警告) {fn.__name__ if hasattr(fn, "__name__") else "call"} 失败: {str(e)[:70]}')
                    return None
                time.sleep(2)

    safe(call, '/api/realtime/start', {'video_path': VIDEO})
    time.sleep(8)                       # 预热
    s0 = safe(call, '/api/realtime/status')
    if not s0:
        return 0.0, {'processed_frames': 0, 'avg_fps': 0, 'frame_rate': 0}
    time.sleep(seconds)
    s1 = safe(call, '/api/realtime/status') or s0
    safe(call, '/api/realtime/stop', {})
    d0, d1 = s0['data'], s1['data']
    df = d1['processed_frames'] - d0['processed_frames']
    return (df / seconds if seconds else 0), d1


print(f'{"配置":<34}{"吞吐(fps)":>10}{"单帧(ms)":>10}{"avg_fps":>9}{"检测帧率上限":>13}')
print('-' * 78)
rows = []
for name, env in CONFIGS:
    if not restart_backend(env):
        print(f'{name:<34}  后端未就绪，跳过')
        continue
    fps, st = measure()
    per_ms = 1000.0 / fps if fps > 0 else 0
    print(f'{name:<34}{fps:>10.2f}{per_ms:>10.0f}{st["avg_fps"]:>9.2f}{st["frame_rate"]:>13}')
    rows.append((name, fps, per_ms))

print('\n===== 结论 =====')
if rows:
    best = max(rows, key=lambda r: r[1])
    base = rows[0][1]
    print(f'  最优: {best[0]}  ->  {best[1]:.2f} fps（单帧 {best[2]:.0f} ms）')
    print(f'  相对原始配置提升: {(best[1]/base - 1)*100:+.0f}%' if base else '')
    print('\n  换算成"框的更新间隔"（用户能直接感觉到的量）：')
    for name, fps, _ in rows:
        print(f'    {name:<34} 每 {1000/fps:.0f} ms 挪一次'
              + ('   ← 已接近 10fps 显示上限的一半' if fps >= 5 else ''))
print('\n注意：本脚本会重启后端。跑完请确认最终生效的环境变量（见 _STARTUP_GUIDE.md）。')
