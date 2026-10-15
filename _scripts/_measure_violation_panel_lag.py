# -*- coding: utf-8 -*-
"""实测「违规从画面到右栏」的端到端延迟（2026-10-10 由 DSH 编写）

## 用户反馈
"视频左上角的违规反应很快，但是违规告警页面很慢，有时候甚至还来不及反应"

## 两条链路（都从 `process_frame` 里同一个 `violations` 列表出发）
- **画面标注**：`_draw_detection_boxes(violations=...)` -> MJPEG 流（20 fps 重画，肉眼即时）
- **右栏"违规告警"**：`_push_recent_violations()` -> `GET /api/realtime/vehicles` 的 `violators`
  （前端每 **1.5 秒**轮询一次）

## 本脚本测什么
每 0.25 秒同时采样两个接口，记录**每一次"违规出现/消失"的时刻**：
  · `/api/realtime/status`  -> `violation_count`（后端累计违规数，画面侧的信号）
  · `/api/realtime/vehicles` -> `violators` 列表（右栏的数据源）
然后量化：右栏比画面**晚多少**才出现、**早多少**就消失、有没有**完全没出现**的。

用法：python _measure_violation_panel_lag.py [seconds]
输出纯 ASCII。
"""
import json
import sys
import time
import urllib.request

BASE = 'http://127.0.0.1:8001'
DURATION = float(sys.argv[1]) if len(sys.argv) > 1 else 300.0
INTERVAL = 0.25


def get(path, timeout=10):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def data_of(r):
    return r.get('data', r) if isinstance(r, dict) else {}


st0 = data_of(get('/api/realtime/status'))
print('=' * 78)
print('running=%s source=%s' % (st0.get('running'), (st0.get('video_path') or '')[-40:]))
print('sampling every %.2fs for %.0fs' % (INTERVAL, DURATION))
print('=' * 78)
if not st0.get('running'):
    print('detection is NOT running - start it first')
    sys.exit(2)

# 事件序列：[{t, frameViol (violation_count), panelIds (frozenset), panelList}]
samples = []
t0 = time.time()
last_vc = None
while time.time() - t0 < DURATION:
    t = time.time() - t0
    try:
        s = data_of(get('/api/realtime/status'))
        v = data_of(get('/api/realtime/vehicles'))
        vc = int(s.get('violation_count') or 0)
        ids = frozenset(
            (str(x.get('track_id')), str(x.get('primary_violation')))
            for x in (v.get('violators') or []))
        samples.append({'t': t, 'vc': vc, 'ids': ids,
                        'n': len(v.get('violators') or []),
                        'clean': len(v.get('clean') or [])})
    except Exception as e:
        samples.append({'t': t, 'err': str(e)[:60]})
    time.sleep(INTERVAL)

print('samples=%d' % len(samples))

# ---- 1) 画面侧信号：violation_count 的增长点 --------------------------------
rises = []
prev = None
for s in samples:
    if 'vc' not in s:
        continue
    if prev is not None and s['vc'] > prev:
        rises.append({'t': s['t'], 'delta': s['vc'] - prev, 'vc': s['vc']})
    prev = s['vc']

print()
print('后端累计违规数上升次数: %d' % len(rises))
for r in rises[:12]:
    print('   t=%7.2fs  +%d  (total=%d)' % (r['t'], r['delta'], r['vc']))

# ---- 2) 右栏侧：violators 非空的区间 ---------------------------------------
segments = []
cur = None
for s in samples:
    if 'ids' not in s:
        continue
    if s['n'] > 0 and cur is None:
        cur = {'start': s['t'], 'ids': set(s['ids']), 'nmax': s['n']}
    elif s['n'] > 0 and cur is not None:
        cur['ids'] |= set(s['ids'])
        cur['nmax'] = max(cur['nmax'], s['n'])
    elif s['n'] == 0 and cur is not None:
        cur['end'] = s['t']
        segments.append(cur)
        cur = None
if cur is not None:
    cur['end'] = samples[-1]['t']
    segments.append(cur)

print()
print('右栏 violators 非空的区间数: %d' % len(segments))
for seg in segments[:12]:
    print('   %7.2fs -> %7.2fs (%.2fs)  %s'
          % (seg['start'], seg['end'], seg['end'] - seg['start'],
             sorted(seg['ids'])[:3]))

# ---- 3) 关键量化：每次违规上升后，右栏多久才出现？ --------------------------
print()
print('=' * 78)
print('每次"画面侧违规上升" -> 右栏出现的时间差')
print('=' * 78)
if not rises:
    print('  本次采样窗口内后端累计违规数没有上升（没抓到违规）')
else:
    lags = []
    for r in rises:
        seg = next((x for x in segments if x['start'] >= r['t'] - 0.3), None)
        if seg is None:
            print('   t=%7.2fs  -> 右栏**从未出现**（窗口内）  <-- 用户说的"来不及反应"' % r['t'])
            lags.append(None)
        else:
            lag = seg['start'] - r['t']
            lags.append(lag)
            print('   t=%7.2fs  -> 右栏于 %7.2fs 出现，延迟 %5.2fs，持续 %.2fs'
                  % (r['t'], seg['start'], lag, seg['end'] - seg['start']))
    got = [x for x in lags if x is not None]
    print()
    if got:
        print('  延迟统计: n=%d  min=%.2fs  中位=%.2fs  max=%.2fs'
              % (len(got), min(got), sorted(got)[len(got) // 2], max(got)))
    miss = sum(1 for x in lags if x is None)
    print('  未出现次数: %d / %d' % (miss, len(rises)))

# ---- 4) 前端轮询周期的影响（理论值）---------------------------------------
print()
print('=' * 78)
print('参考：前端轮询 1.5s -> 理论最坏额外延迟 1.5s；后端检测周期 %.2fs'
      % (1.0 / max(0.001, float(st0.get('current_fps') or 0.1))))
print('=' * 78)
