# -*- coding: utf-8 -*-
"""验证「每辆车两个框」修复（2026-10-09 由 DSH 编写；替代旧的只读假设版）

## 被验证的机制（设计单 §12.3）
旧实现用 **bbox 精确匹配**把 detection 关联到 track：
    bbox_to_track[tuple(int(x) for x in bb[:4])] = veh
而**框位置预测**会把 tracked_vehicles 的框平移成带小数的值 -> 取整后不再相等 ->
主循环 tid=None -> 画车型标签且**不登记 drawn_tracks** ->
兜底循环（遍历 tracked_vehicles）**又画一次带 ID 的** => 一辆车两个框。

## 本脚本做什么
1. 用**真实代码路径**（_predict_boxes 真跑）制造"预测已平移"的状态；
2. 用**真实的新匹配器** _match_track_for_detection 决定每辆车的归属；
3. 算出渲染器两个循环的**框数**（主循环 = 有归属的 detection 数；
   兜底 = |tracked_vehicles| - |drawn_tracks|，该不变量由静态检查确认）；
4. 另外**真跑一次 render()** 确保不抛异常，并检查新加的 box_draw_stats。
"""
import inspect
import re
import sys
import time as _clock          # 用别名：别让 time 被后面的局部名遮蔽

sys.path.insert(0, r'E:\output\1\api')

import numpy as np
import annotation_renderer as ar
from realtime_detector import RealtimeViolationDetector

FAILS = []


def check(name, ok, detail=''):
    print(('  PASS  ' if ok else '  FAIL  ') + name + (('  | ' + str(detail)) if detail else ''))
    if not ok:
        FAILS.append(name)


def frame_boxes(tracked_vehicles, detections, used_ids):
    """复刻渲染器两个循环的**框数**（关联一律走真实匹配器，不复制逻辑）"""
    matched = 0
    drawn = set()
    for det in detections:
        cls = (det.get('class_name') or '').lower()
        if cls in ar.TRAFFIC_LIGHT_CLASS_NAMES:
            continue                      # 红绿灯走单独分支
        tid, _veh = ar._match_track_for_detection(
            det, by_id, by_bbox, boxed, used_ids)
        matched += 1                      # 主循环：每条非红绿灯 detection 画一个框
        if tid is not None:
            used_ids.add(tid)
            drawn.add(tid)
    # 兜底循环：遍历 tracked_vehicles，if tid_i in drawn_tracks: continue
    fallback = [t for t in tracked_vehicles if t not in drawn]
    return matched, fallback, drawn


print('=' * 74)
print('0) static check: fallback loop still skips only drawn_tracks')
print('=' * 74)
src = inspect.getsource(ar.AnnotationRenderer.render)
has_skip = re.search(r'if\s+tid_i\s+in\s+drawn_tracks\s*:\s*\n\s*continue', src)
has_add = 'drawn_tracks.add(tid)' in src
check('fallback loop still skips drawn_tracks', bool(has_skip))
check('main loop still registers drawn_tracks.add(tid)', has_add)

DET_BBOX = [1367, 623, 1725, 778]
VEH = {
    'id': 18,
    'bbox': [1367.0, 623.0, 1725.0, 778.0],
    'class_name': 'car', 'speed': 160.0, 'direction': 'up',
    'history': [{'center': (1450.0, 700.0), 'timestamp': 1.0},
                {'center': (1460.0, 690.0), 'timestamp': 1.05},
                {'center': (1470.0, 680.0), 'timestamp': 1.10}],
}
DET = {'bbox': list(DET_BBOX), 'class_name': 'car', 'confidence': 0.75,
       'source_model': 'vehicle'}

d = RealtimeViolationDetector()
d._last_detect_wall_ts = _clock.time() - 0.30      # 距上次检测 0.3s -> 会预测
d._det_interval_ema = 0.30

print()
print('=' * 74)
print('1) prediction really shifted the box (precondition)')
print('=' * 74)
pred_exact = d._predict_boxes({18: dict(VEH)})
pb = pred_exact[18]['bbox']
shifted = [round(v, 1) for v in pb] != [float(v) for v in VEH['bbox']]
check('_predict_boxes moved the bbox (float, not int-equal)', shifted,
      'orig=%s -> pred=%s' % (VEH['bbox'], [round(v, 1) for v in pb]))
check('bbox no longer int-equal to detection',
      tuple(int(v) for v in pb) != tuple(int(v) for v in DET_BBOX),
      'pred_int=%s det=%s' % (tuple(int(v) for v in pb), tuple(int(v) for v in DET_BBOX)))


def run_case(label, tracked, det, expect_boxes):
    global by_id, by_bbox, boxed
    by_id, by_bbox, boxed = ar._build_track_index(tracked)
    used = set()
    matched, fallback, drawn = frame_boxes(tracked, [det], used)
    n = matched + len(fallback)
    tid, _veh = ar._match_track_for_detection(det, by_id, by_bbox, boxed, set())
    print('  %-38s main=%d fallback=%s drawn=%s -> %d box(es) (tid=%s)'
          % (label, matched, fallback or '[]', sorted(drawn) or '[]', n, tid))
    check('%s -> %d box(es)' % (label, expect_boxes), n == expect_boxes, 'boxes=%d' % n)
    return tid


print()
print('=' * 74)
print('2) new logic: every case must draw exactly 1 box per car')
print('=' * 74)
run_case('A pred OFF (exact bbox equal)', {18: dict(VEH)}, DET, 1)

det_b = dict(DET)
det_b['track_id'] = 18
det_b['vehicle_id'] = 18
run_case('B pred ON + track_id backfilled', pred_exact, det_b, 1)
run_case('C pred ON + no track_id (space fallback)', pred_exact, dict(DET), 1)

VEH2 = {'id': 7, 'bbox': [500.0, 600.0, 700.0, 760.0], 'class_name': 'truck',
        'speed': 120.0, 'direction': 'up',
        'history': [{'center': (600.0, 680.0), 'timestamp': 1.0},
                    {'center': (610.0, 675.0), 'timestamp': 1.05}]}
DET2 = {'bbox': [500, 600, 700, 760], 'class_name': 'truck', 'confidence': 0.8,
        'source_model': 'vehicle', 'track_id': 7}
by_id, by_bbox, boxed = ar._build_track_index({18: dict(VEH), 7: dict(VEH2)})
used = set()
m, fb, drawn = frame_boxes({18: dict(VEH), 7: dict(VEH2)}, [dict(DET), dict(DET2)], used)
check('D two cars, two detections -> 2 boxes, no fallback',
      m + len(fb) == 2 and not fb and drawn == {18, 7},
      'main=%d fallback=%s drawn=%s' % (m, fb, sorted(drawn)))

by_id, by_bbox, boxed = ar._build_track_index({18: dict(VEH), 7: dict(VEH2)})
used = set()
det_e = dict(DET)
det_e['track_id'] = 18
m, fb, drawn = frame_boxes({18: dict(VEH), 7: dict(VEH2)}, [det_e], used)
check('E missed-detection car still drawn by fallback (exactly 1 box)',
      m == 1 and fb == [7], 'main=%d fallback=%s' % (m, fb))

print()
print('=' * 74)
print('3) old logic replay (proves the two-box cause)')
print('=' * 74)
old_b2t = {tuple(int(x) for x in VEH['bbox'][:4]): VEH}
key = tuple(int(x) for x in DET_BBOX)
old_hit = old_b2t.get(key) is not None
old_b2t_pred = {tuple(int(x) for x in pred_exact[18]['bbox'][:4]): pred_exact[18]}
old_hit_pred = old_b2t_pred.get(key) is not None
print('  old logic (pred OFF): hit=%s -> main draws ID, fallback skips => 1 box' % old_hit)
print('  old logic (pred ON) : hit=%s -> main draws car, fallback draws ID => 2 boxes' % old_hit_pred)
check('old logic really fails when prediction is on (two boxes reproducible)',
      old_hit and not old_hit_pred)

print()
print('=' * 74)
print('4) really call render() (no exception, frame returned)')
print('=' * 74)
r = ar.get_renderer()
r.mode = 'minimal'
det_r = dict(DET)
det_r['track_id'] = 18
try:
    out = r.render(np.zeros((1080, 1920, 3), np.uint8), detections=[det_r],
                   tracked_vehicles={18: dict(VEH)}, violations=[], traffic_lights=[])
    ok = isinstance(out, np.ndarray) and out.shape == (1080, 1920, 3)
    check('render() returned a frame', ok, getattr(out, 'shape', None))
except Exception as e:
    check('render() returned a frame', False, '%s: %s' % (type(e).__name__, e))
try:
    out2 = r.render(np.zeros((1080, 1920, 3), np.uint8), detections=[dict(DET)],
                    tracked_vehicles={18: dict(VEH)}, violations=[], traffic_lights=[])
    check('render() ok without track_id (space fallback path)', isinstance(out2, np.ndarray))
except Exception as e:
    check('render() ok without track_id (space fallback path)', False, str(e)[:120])

try:
    stats = ar.get_box_draw_stats()
    check('box_draw_stats is populated (observability works)',
          stats.get('frames', 0) >= 2 and 'main_boxes' in stats,
          {k: stats.get(k) for k in ('frames', 'main_boxes', 'fallback_boxes',
                                     'unmatched_dets', 'max_dets_per_track')})
except Exception as e:
    check('box_draw_stats is populated (observability works)', False, str(e)[:120])

print()
print('=' * 74)
print('5) three-colour scheme: grey = not tracked yet, and NO text on it')
print('=' * 74)
# 用真渲染器验证：无 ID 的检测框必须画成灰色、且**不产生任何文字**。
# 做法：把 draw_texts 换成一个记录器（不真画字），从而精确数出"要画几条文字"。
captured = []
_orig_draw_texts = r.draw_texts


def _capture(frame, texts):
    captured.extend(list(texts))
    return frame


r.draw_texts = _capture
try:
    # 5a) 无 ID 的检测 -> 灰框 + 无文字
    frame_gray = np.zeros((400, 400, 3), np.uint8)
    captured.clear()
    r.render(frame_gray, detections=[{'bbox': [50, 50, 250, 250], 'class_name': 'car',
                                      'confidence': 0.7}],
             tracked_vehicles={}, violations=[], traffic_lights=[])
    gray_px = int(((frame_gray[:, :, 0] > 120) & (frame_gray[:, :, 0] < 180)
                   & (abs(frame_gray[:, :, 0].astype(int) - frame_gray[:, :, 1]) < 30)).sum())
    check('5a untracked detection draws a GREY box', gray_px > 200, 'greyish px=%d' % gray_px)
    check('5a untracked detection draws NO text at all', len(captured) == 0,
          'texts=%s' % captured)

    # 5b) 有 ID 的正常车 -> 绿框 + "ID18"
    frame_ok = np.zeros((400, 400, 3), np.uint8)
    captured.clear()
    r.render(frame_ok, detections=[{'bbox': [50, 50, 250, 250], 'class_name': 'car',
                                    'track_id': 18, 'confidence': 0.7}],
             tracked_vehicles={18: {'id': 18, 'bbox': [50.0, 50.0, 250.0, 250.0],
                                    'class_name': 'car', 'speed': 10.0}},
             violations=[], traffic_lights=[])
    green_px = int((frame_ok[:, :, 1] > 180).sum())
    check('5b tracked non-violating car draws a GREEN box', green_px > 200,
          'green px=%d' % green_px)
    check('5b tracked car labelled with ID, not class name',
          any('ID18' in str(t[0]) for t in captured) and
          not any('car' in str(t[0]) for t in captured),
          'texts=%s' % [t[0] for t in captured])

    # 5c) 违规车 -> 红框 + ID（保留用户认可的红/绿配色）
    frame_v = np.zeros((400, 400, 3), np.uint8)
    captured.clear()
    r.render(frame_v, detections=[{'bbox': [50, 50, 250, 250], 'class_name': 'car',
                                   'track_id': 18, 'confidence': 0.7}],
             tracked_vehicles={18: {'id': 18, 'bbox': [50.0, 50.0, 250.0, 250.0],
                                    'class_name': 'car'}},
             violations=[{'violation_type': 'red_light', 'vehicle_id': 18,
                          'violation_type_cn': '闯红灯'}],
             traffic_lights=[])
    red_px = int((frame_v[:, :, 2] > 180).sum())
    check('5c violating car draws a RED box', red_px > 200, 'red px=%d' % red_px)
    check('5c violating car still shows its ID', any('ID18' in str(t[0]) for t in captured),
          'texts=%s' % [t[0] for t in captured])
finally:
    r.draw_texts = _orig_draw_texts

print()
print('=' * 74)
print('RESULT: %s   (%d failed)' % ('PASS' if not FAILS else 'FAIL', len(FAILS)))
for f in FAILS:
    print('  - ' + f)
print('=' * 74)
sys.exit(1 if FAILS else 0)
