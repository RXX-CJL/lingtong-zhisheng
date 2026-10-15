# -*- coding: utf-8 -*-
"""分析闯红灯违规的真实性：trace 逐帧对照（2026-10-10 由 DSH 编写）

用户反馈："实时检测的违规抓拍证据功能似乎存在不同步和重复的无意义的取证问题"。
数据库现象：**每 ~31 秒就有一条 red_light**，track_id 各不相同（32 秒 ≈ 一圈的墙钟时间）。

本脚本用逐帧 trace 回答三个问题：
  1. 每一条 red_light 违规时，**灯态是不是真的红**？（判色链路）
  2. 违规车辆**当时到底在哪**？（是否真的越过停止线）
  3. 是不是"摄像机拍到的每一辆过线车都报一次"？（按 track 统计）

用法：RT_TRACE_JSONL=xxx 启动后端 -> 跑检测 -> 用本脚本分析该 trace。
输出纯 ASCII。
"""
import json
import sys
from collections import Counter, defaultdict

path = sys.argv[1] if len(sys.argv) > 1 else r'E:\output\_rt_trace_redlight_audit.jsonl'
recs = []
with open(path, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            recs.append(json.loads(line))
        except Exception:
            pass

print('=' * 74)
print('trace = %s   frames=%d' % (path, len(recs)))
print('=' * 74)

# 灯态分布
states = Counter(r.get('state') for r in recs)
scopes = Counter(r.get('scope') for r in recs)
print('light state distribution : %s' % dict(states))
print('light scope distribution : %s' % dict(scopes))

# 违规事件
viols = []
for r in recs:
    for v in (r.get('viol') or []):
        if (v.get('type') or '') == 'red_light':
            viols.append((r, v))
print('red_light violation frames: %d' % len(viols))

if not viols:
    print('  (no red_light in this trace)')
    sys.exit(0)

# 按 track 归并"同一个车连续帧算一次违规"
by_track = defaultdict(list)
for r, v in viols:
    by_track[v.get('vid')].append((r.get('t'), r.get('f'), r.get('state')))

print()
print('--- 每一次 red_light：灯态 / 车辆当时的框与位置 ---')
print('  %-9s %-6s %-6s %-26s %s' % ('t(s)', 'frame', 'state', 'violating bbox', '所有被追踪车辆(中心x,y)'))
seen_keys = set()
uniq = 0
# 逐帧打印（同一帧多条只打一次）
printed = set()
for r, v in viols:
    key = (r.get('f'), v.get('vid'))
    if key in printed:
        continue
    printed.add(key)
    uniq += 1
    if uniq > 25:
        continue
    vid = v.get('vid')
    vb = None
    for veh in (r.get('veh') or []):
        if veh.get('id') == vid:
            vb = veh.get('bbox')
            break
    others = ['%s:(%d,%d)' % (x.get('id'), int((x['bbox'][0] + x['bbox'][2]) / 2),
                              int((x['bbox'][1] + x['bbox'][3]) / 2))
              for x in (r.get('veh') or []) if x.get('id') != vid and x.get('bbox')]
    print('  %-9s %-6s %-6s %-26s %s'
          % (r.get('t'), r.get('f'), r.get('state'), str(vb), ' '.join(others) or '-'))

print()
print('--- 统计 ---')
print('  唯一 (帧, track) 组合 = %d   （≈ 真实上报次数）' % uniq)
print('  涉及不同 track        = %d' % len(by_track))
print('  每 track 上报次数     : %s' % {k: len(v) for k, v in sorted(by_track.items(), key=lambda kv: str(kv[0]))})

# 关键判据：violating 车辆是否真的在"停止线附近/外侧"？这里没有 stop_line 直接字段，
# 用"车辆框底边 y"是否越过画面 55% 线做一个粗判（配置里 stop_line_y 由标注给出）。
print()
print('--- 灯态真值核对（每条违规当时 state 必须全是 red）---')
bad = [(t, st) for t, f, st in [x for v in by_track.values() for x in v] if st != 'red']
print('  非 red 状态下的 red_light 上报: %d' % len(bad))
if bad[:5]:
    print('  例: %s' % bad[:5])
