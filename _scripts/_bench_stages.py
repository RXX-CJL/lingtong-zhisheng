"""
分段计时：找出"标注帧率上不去"的真瓶颈（2026-10-06 由 DSH 编写）

背景：实测模型本体 5 个总共 137ms/帧，但端到端真实吞吐只有 1.39fps（=719ms/帧）。
      差出来的 ~580ms 必须定位到具体阶段，否则提帧率就是空谈。

只读：不启动检测、不改配置。只是在本进程里按阶段调用同样的函数并计时。
用法：& 'C:\miniconda\envs\zhitong-gpu\python.exe' -B E:\output\_scripts\_bench_stages.py
"""
import base64
import os
import sys
import time

sys.path.insert(0, r'E:\output\1\api')

import cv2

VIDEO = r'E:\output\_dual_cam_demo\dual_cam_demo_lossless.mkv'
cap = cv2.VideoCapture(VIDEO)
cap.set(cv2.CAP_PROP_POS_FRAMES, 260)
ok, frame = cap.read()
cap.release()
if not ok:
    raise SystemExit('取帧失败')
H, W = frame.shape[:2]
print(f'测试帧: {W}x{H}')


def ms(t0):
    return (time.time() - t0) * 1000


res = {}

# ---- 1) 采集侧：JPEG 编码 + base64（每帧都要做，纯 CPU）----
t = time.time()
_ok, _buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
DATA_URL = 'data:image/jpeg;base64,' + base64.b64encode(_buf.tobytes()).decode('ascii')
enc_b64 = ms(t)
res['① JPEG编码+base64'] = enc_b64
print(f'① JPEG编码+base64      : {enc_b64:7.1f} ms   ({len(DATA_URL)/1024:.0f} KB)')

# ---- 2) 多模型检测（含 base64 解码）----
from image_recognizer import init_all_models, multi_model_detect
try:
    init_all_models()
except Exception as e:
    print('init 异常（不致命）:', e)

t = time.time()
r = multi_model_detect(DATA_URL, conf_threshold=0.5)
mm = ms(t)
res['② 多模型检测(5个)'] = mm
dets = r.get('all_detections') or []
print(f'② 多模型检测(5个)      : {mm:7.1f} ms   检出 {len(dets)} 个')

# ---- 3) 追踪 ----
from vehicle_tracker import VehicleTracker
vt = VehicleTracker(use_bytetrack=True)
# 预热一次（ByteTrack 首次会建内部状态）
vt.update(dets, W, H, frame_ts=0.0)
ts = []
for i in range(3):
    t = time.time()
    tv = vt.update(dets, W, H, frame_ts=(i + 1) * 0.05)
    ts.append(ms(t))
tr = sorted(ts)[1]
res['③ 追踪(ByteTrack)'] = tr
print(f'③ 追踪(ByteTrack)      : {tr:7.1f} ms   跟踪 {len(tv)} 辆')

# ---- 4) 规则引擎 ----
# ★签名是 check_violations(detections, violation_type=None, scene_config=None)
#   —— 我第一次按 (detections, scene) 传，scene 落到了 violation_type 上 ->
#   "unhashable type: 'dict'"，白跑一轮。
from violation_rules import check_violations
scene = {
    'traffic_light_state': 'red', 'stop_line_y': 597, 'road_direction': 'up',
    'speed_limit': 60, 'frame_width': W, 'frame_height': H,
    'no_parking_zones': [], 'lane_lines': [],
}
ts = []
for _ in range(3):
    t = time.time()
    v = check_violations(dets, None, scene)
    ts.append(ms(t))
ru = sorted(ts)[1]
res['④ 规则引擎'] = ru
_vlist = (v or {}).get('violations') if isinstance(v, dict) else (v or [])
print(f'④ 规则引擎             : {ru:7.1f} ms   违规 {len(_vlist)} 条')

# ---- 5) 行为引擎 ----
from behavior_engine import BehaviorEngine
be = BehaviorEngine()
tv_list = list(tv.values())
ts = []
for _ in range(3):
    t = time.time()
    n = 0
    for veh in tv_list:
        out = be.analyze_all(veh, scene)
        n += len(out or [])
    ts.append(ms(t))
bh = sorted(ts)[1]
res['⑤ 行为引擎'] = bh
print(f'⑤ 行为引擎({len(tv_list)}辆)     : {bh:7.1f} ms')

# ---- 6) 判色（CNN）----
try:
    from traffic_light_classifier import classify_traffic_light
    tl_boxes = [d for d in dets if 'traffic' in str(d.get('class_name', '')).lower()
                or str(d.get('class_name', '')).lower() in ('red', 'green', 'yellow')]
    ts = []
    for _ in range(3):
        t = time.time()
        for d in tl_boxes[:6]:
            x1, y1, x2, y2 = [int(v) for v in d['bbox'][:4]]
            roi = frame[max(0, y1):y2, max(0, x1):x2]
            if roi.size:
                classify_traffic_light(roi)
        ts.append(ms(t))
    cc = sorted(ts)[1] if ts else 0
    res['⑥ 判色CNN'] = cc
    print(f'⑥ 判色CNN({len(tl_boxes[:6])}个灯)     : {cc:7.1f} ms')
except Exception as e:
    print('⑥ 判色跳过:', e)
    res['⑥ 判色CNN'] = 0

# ---- 7) 标注绘制 + 再编码（流接口每帧都做）----
try:
    from annotation_renderer import get_renderer
    rd = get_renderer()
    ts = []
    for _ in range(3):
        t = time.time()
        _f = rd.draw(frame.copy(), dets, tv, violations=None)
        ts.append(ms(t))
    dr = sorted(ts)[1]
    res['⑦ 标注绘制'] = dr
    print(f'⑦ 标注绘制             : {dr:7.1f} ms')
except Exception as e:
    print('⑦ 标注绘制跳过:', e)
    res['⑦ 标注绘制'] = 0

tot = sum(res.values())
print('\n===== 汇总（单帧串行耗时）=====')
for k, v in sorted(res.items(), key=lambda x: -x[1]):
    print(f'  {k:<22} {v:7.1f} ms   {100*v/tot:5.1f}%')
print(f'  {"合计":<22} {tot:7.1f} ms   -> 上限 {1000/tot:.2f} fps')
print(f'\n  对照：端到端实测真实吞吐 1.39 fps（719 ms/帧）')
