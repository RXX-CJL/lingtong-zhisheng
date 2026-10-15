# -*- coding: utf-8 -*-
"""解析用户导出的前端日志（2026-10-10 由 DSH 编写）

目的：第 5 项("开久了像断网")的取证。设计单 §12.1 的判据：
  · 若**几乎所有接口**一起失败 -> 线程池耗尽（僵尸 MJPEG 流）
  · 若只有**某几个 URL** -> 另找该接口的慢点
本脚本按 URL 聚合失败、看时间聚集、看 cost 分布，并单独列出后端 500 的时段。

用法：python _analyze_frontend_log.py <json>
输出纯 ASCII。
"""
import json
import re
import sys
from collections import Counter, defaultdict

path = sys.argv[1] if len(sys.argv) > 1 else r'C:\Users\ROG\Desktop\zhitong-frontend-log.json'
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

items = data.get('items') or []
print('=' * 78)
print('file      : %s' % path)
print('exportedAt: %s' % data.get('exportedAt'))
print('href      : %s' % data.get('href'))
print('entries   : %d' % len(items))
print('=' * 78)

levels = Counter(x.get('level') for x in items)
tags = Counter(x.get('tag') for x in items)
print('levels:', dict(levels))
print('tags  :', dict(tags.most_common(12)))

# ---- 1) HTTP 失败：按状态码 / URL 聚合 --------------------------------------
fail_re = re.compile(r'HTTP FAIL\s+(?P<status>\S+)\s+(?P<method>\S+)\s+(?P<url>\S+)\s+cost=(?P<cost>\d+)ms')
fails = []
for x in items:
    m = fail_re.search(x.get('message') or '')
    if m:
        fails.append({
            't': x.get('t'), 'tag': x.get('tag'),
            'status': m.group('status'), 'method': m.group('method'),
            'url': m.group('url'), 'cost': int(m.group('cost')),
        })

print()
print('=' * 78)
print('HTTP 失败总数: %d' % len(fails))
print('=' * 78)
by_status = Counter(f['status'] for f in fails)
print('按状态码:', dict(by_status))

def norm(u):
    u = u.split('?')[0]
    u = re.sub(r'/\d{2,}$', '/{id}', u)
    return u

by_url = Counter(norm(f['url']) for f in fails)
print()
print('按 URL 聚合（归一化后）:')
for u, n in by_url.most_common(25):
    costs = sorted(f['cost'] for f in fails if norm(f['url']) == u)
    print('  %-42s x%-3d  cost: min=%-6d med=%-6d max=%-6d'
          % (u, n, costs[0], costs[len(costs) // 2], costs[-1]))

# ---- 2) 500 错误的时间聚集（后端崩溃窗口）----------------------------------
http500 = [f for f in fails if f['status'].startswith('5')]
noresp = [f for f in fails if f['status'] in ('NO_RESP', 'TIMEOUT')]
print()
print('=' * 78)
print('5xx 失败: %d    无响应/超时: %d' % (len(http500), len(noresp)))
print('=' * 78)
if http500:
    ts = sorted(f['t'] for f in http500)
    print('5xx 时间范围: %s  ->  %s' % (ts[0][11:23], ts[-1][11:23]))
    # 按秒聚集
    per_sec = Counter(t[11:19] for t in ts)
    print('5xx 按秒聚集（前 12）:')
    for s, n in sorted(per_sec.items())[:12]:
        print('   %s  x%d' % (s, n))
    print()
    print('5xx 覆盖的不同 URL 数: %d  -> %s'
          % (len(set(norm(f['url']) for f in http500)),
             sorted(set(norm(f['url']) for f in http500))[:12]))
    # 各接口的 cost 趋势：越早越慢 = 排队积压
    print()
    print('5xx 的 cost 序列（按时间）：')
    for f in sorted(http500, key=lambda x: x['t'])[:14]:
        print('   %s  %-6s %-40s cost=%-6dms' % (f['t'][11:23], f['status'], norm(f['url']), f['cost']))

# ---- 3) 非 HTTP 的 console 错误 --------------------------------------------
print()
print('=' * 78)
print('其它 ERROR 日志（非 HTTP FAIL）')
print('=' * 78)
seen = Counter()
for x in items:
    if x.get('level') not in ('ERROR', 'FATAL'):
        continue
    msg = (x.get('message') or '')
    if fail_re.search(msg):
        continue
    key = re.sub(r'\d+', 'N', msg)[:110]
    seen[key] += 1
for k, n in seen.most_common(20):
    print('  x%-3d %s' % (n, k))

# ---- 4) 时间轴首尾：这次会话持续多久、失败发生在第几分钟 -------------------
print()
print('=' * 78)
allt = sorted(x.get('t') for x in items if x.get('t'))
if allt:
    print('日志时间跨度: %s  ->  %s' % (allt[0][11:23], allt[-1][11:23]))
if http500:
    first = allt[0]
    print('首次 5xx 出现在会话开始后约 %d 秒'
          % (int((__import__('datetime').datetime.fromisoformat(sorted(f['t'] for f in http500)[0].replace('Z', '+00:00'))
                  - __import__('datetime').datetime.fromisoformat(first.replace('Z', '+00:00'))).total_seconds())))
