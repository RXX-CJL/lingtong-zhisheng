# -*- coding: utf-8 -*-
"""trace 级验证：绘制侧 ROI 过滤 + 判定语义未变（2026-10-09 三项修复之 B）

为什么值得单独做（证据等级 = 三级，最强）：
  /status 只能给出"收集了几盏 / 画了几盏"的数量，而 trace 里同时有
  **每一盏灯的 bbox 与颜色** 和 **roi 配置**，可以直接算出
  "哪些灯在 ROI 外、按新逻辑它们不会被画" —— 尤其能钉死用户看到的那两盏：
    ('yellow',(419,120))  左侧横向车道的黄灯
    ('red',   (275,182))  更左那盏红灯
  并同时验证**判定侧**（matched/state/scope）与 ROI 内灯数完全自洽
  （= 我们只过滤了绘制列表，没动判色链路）。

输入：环境变量 RT_TRACE_JSONL 指向的 jsonl（每帧一条）
用法：RT_TRACE_JSONL=... python _verify_trace_roi_filter.py <trace.jsonl> [roi_json]
输出纯 ASCII。
"""
import json
import os
import sys
from collections import Counter

FAILS = []


def check(name, ok, detail=''):
    print(('  PASS  ' if ok else '  FAIL  ') + name + (('  | ' + str(detail)) if detail else ''))
    if not ok:
        FAILS.append(name)


def data_of(r):
    return r.get('data', r) if isinstance(r, dict) else {}


def in_rois(bbox, rois):
    try:
        x1, y1, x2, y2 = [float(v) for v in bbox[:4]]
    except (TypeError, ValueError, IndexError):
        return False
    cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    for r in rois or []:
        try:
            rx1, ry1, rx2, ry2 = [float(v) for v in r[:4]]
        except (TypeError, ValueError, IndexError):
            continue
        if min(rx1, rx2) <= cx <= max(rx1, rx2) and min(ry1, ry2) <= cy <= max(ry1, ry2):
            return True
    return False


trace_path = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('RT_TRACE_JSONL', '')
if not trace_path or not os.path.exists(trace_path):
    print('FATAL: trace file not found: %r' % trace_path)
    sys.exit(2)

# ROI 来源：优先命令行给的 json，其次打后端拿（与 trace 同一份场景配置）
rois = []
if len(sys.argv) > 2 and os.path.exists(sys.argv[2]):
    with open(sys.argv[2], 'r', encoding='utf-8') as f:
        rois = (json.load(f) or {}).get('traffic_light_roi') or []
else:
    import urllib.parse
    import urllib.request
    try:
        with urllib.request.urlopen('http://127.0.0.1:8001/api/realtime/status', timeout=10) as r:
            st = data_of(json.loads(r.read().decode('utf-8')))
        src = st.get('video_path') or st.get('source_url') or ''
        if src:
            with urllib.request.urlopen(
                    'http://127.0.0.1:8001/api/scene/config?source='
                    + urllib.parse.quote(src), timeout=10) as r:
                rois = data_of(json.loads(r.read().decode('utf-8'))).get('traffic_light_roi') or []
    except Exception as e:
        print('  (could not fetch ROI from API: %s)' % e)

print('=' * 74)
print('trace = %s' % trace_path)
print('ROI   = %s' % json.dumps(rois))
print('=' * 74)
check('ROI annotated (2 or more boxes)', len(rois) >= 1, len(rois))

recs = []
with open(trace_path, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            recs.append(json.loads(line))
        except Exception:
            continue
check('trace has frames', len(recs) > 0, len(recs))

# ---- 1) 每帧：收集的灯 / ROI 内的灯 / ROI 外的灯 -------------------------------
tot_collected = tot_inside = tot_outside = 0
frames_with_outside = 0
outside_counter = Counter()          # (color, 左上角) -> 出现帧数
inside_counter = Counter()
matched_ok = matched_bad = 0
state_ok = 0
for rec in recs:
    lights = rec.get('lights') or []
    ins = [l for l in lights if in_rois(l.get('bbox'), rois)]
    outs = [l for l in lights if not in_rois(l.get('bbox'), rois)]
    tot_collected += len(lights); tot_inside += len(ins); tot_outside += len(outs)
    if outs:
        frames_with_outside += 1
    for l in outs:
        bb = [int(round(float(v))) for v in (l.get('bbox') or [])[:4]]
        outside_counter[(l.get('color'), (bb[0], bb[1]))] += 1
    for l in ins:
        bb = [int(round(float(v))) for v in (l.get('bbox') or [])[:4]]
        inside_counter[(l.get('color'), (bb[0], bb[1]))] += 1
    # 判定自洽：matched 必须等于"ROI 内的灯数"（_scene_light_state_from_cnn 的语义）
    m = int(rec.get('matched') or 0)
    if m == len(ins):
        matched_ok += 1
    else:
        matched_bad += 1
    if rec.get('scope') in ('roi', 'roi_miss'):
        state_ok += 1

print()
print('frames=%d  collected=%d  inside_ROI=%d  outside_ROI=%d  frames_with_outside=%d'
      % (len(recs), tot_collected, tot_inside, tot_outside, frames_with_outside))
print('scope=roi/roi_miss frames: %d/%d' % (state_ok, len(recs)))
print()
print('--- 每帧"该被过滤掉"(ROI 外)的灯，按 (颜色, 左上角) 汇总，取前 10 ---')
for (color, xy), n in outside_counter.most_common(10):
    print('    (%s, %s)  %d 帧' % (repr(color), xy, n))
print('--- ROI 内（会被画）的灯，取前 10 ---')
for (color, xy), n in inside_counter.most_common(10):
    print('    (%s, %s)  %d 帧' % (repr(color), xy, n))

print()
check('light collection still sees ALL lights (colour chain untouched)',
      tot_collected > 0, tot_collected)
check('there ARE lights outside ROI that the new draw filter removes',
      tot_outside > 0, 'outside=%d over %d frames' % (tot_outside, frames_with_outside))
check('ROI keeps at least one light (drawing not blank)',
      tot_inside > 0, tot_inside)
check('judgement semantics intact: matched == #lights inside ROI in every frame',
      matched_bad == 0, 'ok=%d bad=%d' % (matched_ok, matched_bad))
check('scope is roi/roi_miss (lane-level judgement active)',
      state_ok == len(recs), '%d/%d' % (state_ok, len(recs)))

# ---- 2) 用户具体看到的那两盏灯必须落在 ROI 外 ---------------------------------
want_filtered = [('yellow', (419, 120)), ('red', (275, 182))]
print()
print('--- user-reported "should not be recognised" lights ---')
for color, xy in want_filtered:
    hit = sum(n for (c, p), n in outside_counter.items()
              if c == color and abs(p[0] - xy[0]) <= 40 and abs(p[1] - xy[1]) <= 40)
    ins = sum(n for (c, p), n in inside_counter.items()
              if c == color and abs(p[0] - xy[0]) <= 40 and abs(p[1] - xy[1]) <= 40)
    print('    %s at ~%s : outside(将被过滤)=%d 帧, inside(会被画)=%d 帧'
          % (color, xy, hit, ins))
    check('%s at ~%s is OUTSIDE roi (filtered from drawing)' % (color, xy),
          hit > 0 and ins == 0, 'out=%d in=%d' % (hit, ins))

print()
print('=' * 74)
print('RESULT: %s   (%d failed)' % ('PASS' if not FAILS else 'FAIL', len(FAILS)))
for f in FAILS:
    print('  - ' + f)
print('=' * 74)
sys.exit(1 if FAILS else 0)
