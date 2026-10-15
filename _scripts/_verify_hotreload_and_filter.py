# -*- coding: utf-8 -*-
"""验证 2026-10-09 三项修复的后端部分（自校验，不需要正在跑的后端）

验证对象：
  A. image_recognizer.TRAFFIC_CLASS_WHITELIST + detector._filter_traffic_classes
     -> "盆栽/fire hydrant/sports ball" 类必须被挡掉；车辆/行人/红绿灯/头盔/车道线必须保留
  B. detector 场景标注**热重载**（mtime+size）
     -> 保存后**无需重启**，下一次 get_status / 下一帧即生效
  C. 绘制侧 ROI 过滤的谓词语义
     -> 没标 ROI 时全部画；标了 ROI 只画 ROI 内的（且不影响 _last_traffic_lights 本身）

安全说明：全程使用**临时目录**里的假场景配置，不碰
  E:\\output\\1\\api\\output\\scene_configs\\ 下任何真实标注文件。

输出：纯 ASCII，避免控制台 GBK 报错吞结果（本项目已踩过）。
"""
import os
import sys
import json
import time
import glob
import shutil
import tempfile

API = r'E:\output\1\api'
sys.path.insert(0, API)
FAILS = []


def check(name, ok, detail=''):
    print(('  PASS  ' if ok else '  FAIL  ') + name + (('  | ' + str(detail)) if detail else ''))
    if not ok:
        FAILS.append(name)


def det(cls, conf=0.9, bbox=(0, 0, 10, 10)):
    return {'class_name': cls, 'class_name_cn': cls, 'confidence': conf, 'bbox': list(bbox)}


print('=' * 72)
print('A. traffic class whitelist filter')
print('=' * 72)
from image_recognizer import TRAFFIC_CLASS_WHITELIST as WL
import realtime_detector as rd

print('  whitelist size = %d' % len(WL))

# 必须保留
KEEP = ['car', 'truck', 'bus', 'motorcycle', 'bicycle', 'person', 'rider',
        'traffic light', 'traffic_light', 'red', 'green', 'yellow',
        'red_light', 'green_light', 'yellow_light',
        'with_helmet', 'without_helmet', 'helmet',
        'lane_line', 'road_line', 'white_line', 'yellow_line',
        'stop sign', 'license_plate', 'plate']
# 必须挡掉（用户实际看到的盆栽 + COCO 其它无关类）
DROP = ['potted plant', 'fire hydrant', 'sports ball', 'chair', 'bench', 'dog',
        'cake', 'toothbrush', 'teddy bear', 'wine glass', 'book', 'clock',
        'vase', 'scissors', 'banana', 'surfboard', 'zebra']  # zebra=斑马(动物)不在白名单

missing_keep = [c for c in KEEP if c not in WL]
leaked_drop = [c for c in DROP if c in WL]
check('whitelist contains all rule-engine classes', not missing_keep, missing_keep)
check('whitelist rejects non-traffic COCO classes', not leaked_drop, leaked_drop)

d = rd.RealtimeViolationDetector()
mixed = [det(c) for c in KEEP] + [det(c) for c in DROP]
kept = d._filter_traffic_classes(mixed)
kept_names = sorted(set(x['class_name'] for x in kept))
check('filter keeps %d/%d and drops %d' % (len(KEEP), len(mixed), len(DROP)),
      len(kept) == len(KEEP) and len(mixed) - len(kept) == len(DROP),
      'kept=%d' % len(kept))
check('no dropped class survived', not (set(kept_names) & set(DROP)),
      sorted(set(kept_names) & set(DROP)))
st = d._class_filter_stats
check('filter stats observable (/status class_filter_stats)',
      st.get('kept') == len(KEEP) and st.get('dropped') == len(DROP), st)
check('empty input safe', d._filter_traffic_classes([]) == [] and d._filter_traffic_classes(None) == [])

print()
print('=' * 72)
print('B. scene annotation hot reload (mtime+size)')
print('=' * 72)
tmp = tempfile.mkdtemp(prefix='zt_hotreload_')
SRC = os.path.join(tmp, 'fake_demo_video.mkv')
SCENE_DIR = os.path.join(API, 'output', 'scene_configs')
cfg_path = os.path.join(SCENE_DIR, 'fake_demo_video_%s.json'
                        % __import__('hashlib').sha1(SRC.encode('utf-8')).hexdigest()[:12])
print('  temp source : %s' % SRC)
print('  scene file  : %s' % cfg_path)
try:
    # 初始标注：1 个 ROI（模拟用户此前只标了 1 个）
    with open(cfg_path, 'w', encoding='utf-8') as f:
        json.dump({'_source': SRC, 'annotated_by': 'manual',
                   'traffic_light_roi': [[988, 110, 1028, 182]]}, f)

    d2 = rd.RealtimeViolationDetector()
    d2._source_path = SRC
    d2._source_url = None
    d2._scene_cfg_path = None          # 强制走 _scene_config_path() 推导
    d2._scene_sig = None
    d2._scene_annotation = {}
    d2._scene_reload_at = 0.0

    changed = d2._maybe_reload_scene_annotation(force=True)
    check('initial load reads 1 ROI', changed and len(d2._scene_annotation.get('traffic_light_roi') or []) == 1,
          d2._scene_annotation.get('traffic_light_roi'))

    again = d2._maybe_reload_scene_annotation(force=True)
    check('unchanged file does NOT reload (no wasted work)', again is False)
    check('reload_count still 1', d2._scene_reload_count == 1, d2._scene_reload_count)

    # 模拟"运行中保存了 4 个 ROI"（只改文件，不重启任何东西）
    time.sleep(1.2)                     # 确保 mtime 变化（避免同秒同 size 判定不出）
    with open(cfg_path, 'w', encoding='utf-8') as f:
        json.dump({'_source': SRC, 'annotated_by': 'manual',
                   'traffic_light_roi': [[988, 110, 1028, 182], [1129, 119, 1150, 170],
                                         [1325, 154, 1353, 214], [1639, 894, 1793, 945]],
                   'stop_line_y': 511}, f)
    got = d2._maybe_reload_scene_annotation(force=True)
    n_roi = len(d2._scene_annotation.get('traffic_light_roi') or [])
    check('HOT RELOAD picks up 1 -> 4 ROIs without restart', got and n_roi == 4, 'roi=%d' % n_roi)
    check('stop_line_y also reloaded', d2._scene_annotation.get('stop_line_y') == 511)
    check('reload_count incremented', d2._scene_reload_count == 2, d2._scene_reload_count)
    check('reloaded_at timestamp recorded', bool(d2._scene_reload_last), d2._scene_reload_last)

    # /status 暴露的字段
    s = d2.get_status()
    for k in ('scene_annotation_reloaded_at', 'scene_annotation_reload_count',
              'scene_annotation_roi_count', 'class_filter_stats',
              'traffic_lights_collected', 'traffic_lights_drawn'):
        check('/status has %s' % k, k in s, s.get(k))

    # 删除标注文件后也应被识别（保存->删除同样要热生效）
    time.sleep(1.1)
    os.remove(cfg_path)
    d2._maybe_reload_scene_annotation(force=True)
    check('deleting annotation reloads to empty', not d2._scene_annotation.get('traffic_light_roi'),
          d2._scene_annotation.get('traffic_light_roi'))
finally:
    try:
        if os.path.exists(cfg_path):
            os.remove(cfg_path)
        shutil.rmtree(tmp, ignore_errors=True)
    except Exception:
        pass
    left = glob.glob(os.path.join(SCENE_DIR, 'fake_demo_video_*.json'))
    check('temp scene file cleaned up', not left, left)

print()
print('=' * 72)
print('C. draw-side ROI filter predicate')
print('=' * 72)
# 与 _draw_detection_boxes 里完全相同的谓词，用 trace 铁证里的真实灯框
LIGHTS = [{'bbox': [816, 123, 860, 190], 'color': 'red'},      # ROI 内
          {'bbox': [1324, 161, 1368, 220], 'color': 'red'},    # ROI 内
          {'bbox': [419, 120, 450, 190], 'color': 'yellow'},   # 左侧横向车道（不该画）
          {'bbox': [275, 182, 300, 250], 'color': 'red'}]      # 更左（不该画）
ROIS = [[988, 110, 1028, 182], [1129, 119, 1150, 170],
        [1325, 154, 1353, 214], [1639, 894, 1793, 945]]
no_roi = list(LIGHTS)
check('no ROI -> draw all (first-time calibration can find lights)', len(no_roi) == 4, len(no_roi))
with_roi = [it for it in LIGHTS if rd.RealtimeViolationDetector._light_in_rois(it['bbox'], ROIS)]
check('with ROI -> only ROI lights drawn (left yellow/red gone)', len(with_roi) == 1,
      [tuple(int(v) for v in it['bbox'][:2]) for it in with_roi])
check('judgement list _last_traffic_lights is NOT touched by draw filter', len(LIGHTS) == 4)

print()
print('=' * 72)
print('RESULT: %s   (%d failed)' % ('PASS' if not FAILS else 'FAIL', len(FAILS)))
if FAILS:
    for f in FAILS:
        print('  - ' + f)
print('=' * 72)
sys.exit(1 if FAILS else 0)
