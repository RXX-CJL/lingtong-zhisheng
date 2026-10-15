# -*- coding: utf-8 -*-
"""验证第 6 项：云端开关是否**真的省钱**、以及**是否会自动打开**（2026-10-10 由 DSH 编写）

## 为什么用"调用计数"而不是"看日志"
`config_runtime.json` 里 dashscope/deepseek 各有一个 `call_count`，是**云端调用的真实累加器**。
它在 `config_manager` 的每次云端请求里 +1（`image_recognizer` 走同一套）。
所以：**只要 call_count 不涨 = 一个 token 都没花**，这比翻日志可靠（日志会被轮转/清空）。

## 判据
- `cloud_review=False`（事件级复核关）时，**call_count 必须一点不涨**
  （即使后台真的产出了违规事件）
- `cloud_review=True` 时，应该**涨**
（测试前会把开关恢复成原样，绝不留改动）

输出纯 ASCII。
"""
import json
import os
import sys
import time
import urllib.request

BASE = 'http://127.0.0.1:8001'
CFG = r'E:\output\1\api\config_runtime.json'
DEMO = r'E:\output\_dual_cam_demo\dual_cam_demo_lossless.mkv'
FAILS = []


def check(name, ok, detail=''):
    print(('  PASS  ' if ok else '  FAIL  ') + name + (('  | ' + str(detail)) if detail else ''))
    if not ok:
        FAILS.append(name)


def get(path, timeout=20):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def post(path, body, timeout=30):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode('utf-8'),
                                 headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def data_of(r):
    return r.get('data', r) if isinstance(r, dict) else {}


def counters():
    with open(CFG, 'r', encoding='utf-8') as f:
        d = json.load(f)
    return int(d.get('dashscope', {}).get('call_count') or 0), \
           int(d.get('deepseek', {}).get('call_count') or 0)


def events_count():
    import sqlite3
    c = sqlite3.connect(r'E:\output\1\api\zhitong_violations.db')
    n = list(c.execute('select count(*) from traffic_events'))[0][0]
    c.close()
    return n


def latest_events(k=6):
    import sqlite3
    c = sqlite3.connect(r'E:\output\1\api\zhitong_violations.db')
    c.row_factory = sqlite3.Row
    rows = [dict(r) for r in c.execute(
        'select event_id, event_type, state, trigger_time from traffic_events '
        'order by rowid desc limit ?', (k,))]
    c.close()
    return rows


s = data_of(get('/api/realtime/settings'))
original = {
    'cloud_review': s.get('cloud_review'),
    'cloud_consult': s.get('cloud_consult'),
}
print('=' * 74)
print('开关原值: cloud_review=%s  cloud_consult=%s' % (original['cloud_review'], original['cloud_consult']))
print('=' * 74)

st = data_of(get('/api/realtime/status'))
if not st.get('running'):
    post('/api/realtime/start', {'video_path': DEMO})
    print('已启动检测（演示视频）…')
    time.sleep(20)
else:
    print('检测已在运行')

results = {}
try:
    for mode in (False, True):
        # 只动 cloud_review；cloud_consult 保持原值（若为 True，逐帧咨询会污染计数）
        post('/api/realtime/settings', {'cloud_review': mode})
        time.sleep(1)
        s_now = data_of(get('/api/realtime/settings'))
        c0 = counters()
        e0 = events_count()
        print()
        print('--- cloud_review=%s ：观察 150 秒 ---' % mode)
        print('    起始 call_count: dashscope=%d deepseek=%d   事件总数=%d' % (c0[0], c0[1], e0))
        time.sleep(150)
        c1 = counters()
        e1 = events_count()
        d = (c1[0] - c0[0], c1[1] - c0[1])
        ev_new = e1 - e0
        print('    结束 call_count: dashscope=%d deepseek=%d  -> 增量 %s' % (c1[0], c1[1], d))
        print('    期间新增事件: %d 条' % ev_new)
        for ev in latest_events(3):
            print('      · %s %-11s state=%s' % (str(ev['trigger_time'])[:19], ev['event_type'], ev['state']))
        results[mode] = {'delta': d, 'events': ev_new, 'switch': s_now.get('cloud_review')}
        # 开关值本身必须等于我们设的（"不会自己变"）
        check('cloud_review=%s 时开关保持不动（没有自动打开/关闭）' % mode,
              s_now.get('cloud_review') == mode, 'now=%s' % s_now.get('cloud_review'))
finally:
    # 还原成用户原来的设置
    post('/api/realtime/settings', original)
    time.sleep(1)
    s_fin = data_of(get('/api/realtime/settings'))
    print()
    print('已还原开关: cloud_review=%s cloud_consult=%s'
          % (s_fin.get('cloud_review'), s_fin.get('cloud_consult')))

off = results.get(False, {})
on = results.get(True, {})
print()
print('=' * 74)
print('结论')
print('=' * 74)
if off:
    check('★关闭事件级复核后：**云端调用零增长**（真的不花钱）',
          off['delta'] == (0, 0),
          'call_count 增量=%s（事件新增 %d 条）' % (off['delta'], off['events']))
    print('    ※ 若期间确实产出了事件（>0 条），这条证据才算充分；否则再跑久一点')
if on:
    check('开启事件级复核后：**云端调用有增长**（开关真的起作用）',
          on['delta'][0] > 0 or on['delta'][1] > 0,
          'call_count 增量=%s（事件新增 %d 条）' % (on['delta'], on['events']))

print()
print('=' * 74)
print('RESULT: %s   (%d failed)' % ('PASS' if not FAILS else 'FAIL', len(FAILS)))
for f in FAILS:
    print('  - ' + f)
print('=' * 74)
sys.exit(1 if FAILS else 0)
