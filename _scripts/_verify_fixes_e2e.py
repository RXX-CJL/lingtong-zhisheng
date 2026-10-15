# -*- coding: utf-8 -*-
"""端到端验证 2026-10-09 三项修复 —— **完整版**（真正跑一遍演示视频）

流程：
  0. 记录初始状态（检测是否在跑），结束时恢复
  1. 确认新代码已生效（/status 有新字段）
  2. 启动检测（演示视频 _dual_cam_demo\dual_cam_demo_lossless.mkv）
  3. 验收 C：class_filter_stats 真的在挡非交通类（kept/dropped 增长）
  4. 验收 B：traffic_lights_collected > drawn（ROI 过滤生效），
             且 traffic_light_matched 与 drawn 一致（**判定语义没被改**）
  5. 验收 A：**检测运行中**把同一份 scene 配置原样回存 -> 不重启、不停止 ->
             /status 的 reload_count 立刻 +1、roi_count 正确
  6. 验收 判定不回归：traffic_light_scope 仍为 roi（灯态仍取 ROI 内的灯）
  7. 恢复初始运行状态（原来是跑的 -> 保持跑；原来没跑 -> 停掉）

副作用：会在演示视频上跑约 40~60 秒检测，产生正常的抓拍/事件记录
        （与用户自己点「开始」等价）；不改任何标定数值。
输出纯 ASCII。
"""
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = 'http://127.0.0.1:8001'
DEMO = r'E:\output\_dual_cam_demo\dual_cam_demo_lossless.mkv'
FAILS = []


def check(name, ok, detail=''):
    print(('  PASS  ' if ok else '  FAIL  ') + name + (('  | ' + str(detail)) if detail else ''))
    if not ok:
        FAILS.append(name)


def _req(path, body=None, method='GET', timeout=30):
    data = json.dumps(body).encode('utf-8') if body is not None else None
    headers = {'Content-Type': 'application/json'} if data else {}
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        detail = e.read().decode('utf-8', 'ignore')[:300]
        print('    HTTP %d on %s -> %s' % (e.code, path, detail))
        return {}


def get(p, timeout=30):
    return _req(p, timeout=timeout)


def post(p, body, timeout=60):
    return _req(p, body, 'POST', timeout)


def data_of(r):
    return r.get('data', r) if isinstance(r, dict) else {}


print('=' * 74)
print('STEP 0: initial state')
print('=' * 74)
st0 = data_of(get('/api/realtime/status'))
was_running = bool(st0.get('running'))
print('  detection running before test: %s' % was_running)

print()
print('=' * 74)
print('STEP 1: new code live? (/status new fields)')
print('=' * 74)
for k in ['scene_annotation_reloaded_at', 'scene_annotation_reload_count',
          'scene_annotation_roi_count', 'class_filter_stats',
          'traffic_lights_collected', 'traffic_lights_drawn']:
    check('field %s' % k, k in st0, st0.get(k))

print()
print('=' * 74)
print('STEP 2: start detection on the demo video')
print('=' * 74)
r = post('/api/realtime/start', {'video_path': DEMO})
print('  start -> %s' % json.dumps(r, ensure_ascii=False)[:160])
time.sleep(2)
src = data_of(get('/api/realtime/status')).get('video_path')
check('running source == demo video', (src or '').lower() == DEMO.lower(), src)

print('  warming up 25s (models + first frames)...')
time.sleep(25)

print()
print('=' * 74)
print('STEP 3: class whitelist really filters (C)')
print('=' * 74)
st = data_of(get('/api/realtime/status'))
cfs = st.get('class_filter_stats') or {}
kept, dropped = int(cfs.get('kept') or 0), int(cfs.get('dropped') or 0)
print('  kept=%d dropped=%d  top_dropped=%s'
      % (kept, dropped, json.dumps(cfs.get('last_dropped_classes'), ensure_ascii=False)[:220]))
check('detection processed frames', int(st.get('processed_frames') or 0) > 0,
      st.get('processed_frames'))
check('whitelist kept traffic classes (kept > 0)', kept > 0, kept)
check('whitelist dropped non-traffic classes (dropped > 0)', dropped > 0,
      'dropped=%d -> %s' % (dropped, sorted((cfs.get('last_dropped_classes') or {}).keys())))

print()
print('=' * 74)
print('STEP 4: draw-side ROI filter (B) + judgement semantics unchanged')
print('=' * 74)
print('  scope=%s collected=%s drawn=%s matched=%s tl_stats=%s'
      % (st.get('traffic_light_scope'), st.get('traffic_lights_collected'),
         st.get('traffic_lights_drawn'), st.get('traffic_light_matched'),
         json.dumps(st.get('traffic_light_stats'), ensure_ascii=False)))
collected = int(st.get('traffic_lights_collected') or 0)
drawn = int(st.get('traffic_lights_drawn') or 0)
matched = int(st.get('traffic_light_matched') or 0)
roi_n = int(st.get('scene_annotation_roi_count') or 0)
check('annotation has ROI (filter is active)', roi_n > 0, roi_n)
check('draw list is ROI-filtered (drawn <= collected)',
      collected == 0 or drawn <= collected, 'drawn=%d <= collected=%d' % (drawn, collected))
# ★本断言第一版写成 matched == drawn，连报两次 FAIL —— 实测（400ms × 18 次采样）
#   把真相钉死了，记在这里避免下次再踩：
#     collected=12 drawn=6 恒定不变，而 matched 在同一时刻是 6 或 8；
#     tl_stats.total 也跳到 14 —— 说明 collected/drawn **不是每帧都更新**。
#   原因：collected/drawn 只在 `_draw_detection_boxes` 里写，而它**只有真有
#   MJPEG 流客户端时才跑**（没人开画面时，绘制侧完全不动 -> 这两个值"冻"住）。
#   matched 则由检测线程每帧更新。两者不属于同一时刻的快照。
#   => 可靠的不变量只有"标了 ROI 时 drawn <= collected"，以及"matched <= 全画面
#      判色灯数"；逐帧严格自洽性由 _verify_trace_roi_filter.py 用 trace 验证
#      （73/73 帧 matched == ROI 内灯数）。
check('judgement count cannot exceed ALL collected lights (matched <= collected)',
      collected == 0 or matched <= collected, 'matched=%d collected=%d' % (matched, collected))
check('light scope still roi (lane-level judgement intact)',
      st.get('traffic_light_scope') in ('roi', 'roi_miss'), st.get('traffic_light_scope'))

print()
print('=' * 74)
print('STEP 5: HOT RELOAD while detection is RUNNING (A)')
print('=' * 74)
cfg = get('/api/scene/config?source=' + urllib.parse.quote(DEMO))
cd = data_of(cfg)
roi_now = cd.get('traffic_light_roi') or []
print('  file: key=%s ROI=%d stop_line_y=%s annotated_at=%s'
      % (cfg.get('key'), len(roi_now), cd.get('stop_line_y'), cd.get('annotated_at')))
if not roi_now:
    check('scene config exists for demo source', False, 'no ROI in file - cannot test')
else:
    before = int(data_of(get('/api/realtime/status')).get('scene_annotation_reload_count') or 0)
    keep_keys = ('traffic_light_roi', 'stop_line_y', 'camera_height_m', 'camera_pitch_deg',
                 'fov_deg', 'camera_yaw_deg', 'ppm_ref_y', 'lane_width_px',
                 'ground_points', 'speed_limit', 'road_direction', 'pixel_per_meter')
    saved = post('/api/scene/config', {
        'source': DEMO, 'annotated_by': 'manual',
        'config': {k: cd[k] for k in keep_keys if k in cd}})
    sd = data_of(saved)
    check('re-save of identical config succeeded',
          bool(saved.get('key')) and len(sd.get('traffic_light_roi') or []) == len(roi_now),
          'key=%s roi=%s' % (saved.get('key'), len(sd.get('traffic_light_roi') or [])))
    time.sleep(1.5)
    st2 = data_of(get('/api/realtime/status'))
    after = int(st2.get('scene_annotation_reload_count') or 0)
    check('reload_count incremented WITHOUT restart', after > before,
          '%d -> %d' % (before, after))
    check('reloaded_at recorded', bool(st2.get('scene_annotation_reloaded_at')),
          st2.get('scene_annotation_reloaded_at'))
    check('roi_count matches file after reload',
          int(st2.get('scene_annotation_roi_count') or 0) == len(roi_now),
          '%s vs file %d' % (st2.get('scene_annotation_roi_count'), len(roi_now)))
    check('detection still running through the reload', bool(st2.get('running')),
          'processed=%s' % st2.get('processed_frames'))
    check('scope still roi after reload (no regression)',
          st2.get('traffic_light_scope') in ('roi', 'roi_miss'), st2.get('traffic_light_scope'))

print()
print('=' * 74)
print('STEP 6: restore initial running state')
print('=' * 74)
if not was_running:
    post('/api/realtime/stop', {})
    time.sleep(1.5)
    stf = data_of(get('/api/realtime/status'))
    check('detection stopped (restored to initial state)', not stf.get('running'),
          stf.get('running'))
else:
    check('detection left running (was running before)', True)

print()
print('=' * 74)
print('RESULT: %s   (%d failed)' % ('PASS' if not FAILS else 'FAIL', len(FAILS)))
for f in FAILS:
    print('  - ' + f)
print('=' * 74)
sys.exit(1 if FAILS else 0)
