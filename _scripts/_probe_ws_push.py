# -*- coding: utf-8 -*-
"""确认后端 WebSocket 在违规时到底推不推（2026-10-11 由 DSH 编写）

背景：前端已确认连上 `ws://127.0.0.1:8001/api/realtime/violations/stream`，
但浏览器 CDP 侧一次 `violation_detected` 都没观察到。两种可能：
  ① 后端根本没推（`_push_violation_event` 的调度/异常被吞）
  ② 后端推了，但 CDP 的 framereceived 没捕获到（观测手段问题）
本脚本用**独立的 websockets 客户端**直接接收帧，并用 `violation_count` 增长做对照，
一次分清这两种可能。

用法：python _probe_ws_push.py [seconds]
输出纯 ASCII。
"""
import asyncio
import json
import sys
import time
import urllib.request

DURATION = float(sys.argv[1]) if len(sys.argv) > 1 else 200.0
URI = 'ws://127.0.0.1:8001/api/realtime/violations/stream'
BASE = 'http://127.0.0.1:8001'

try:
    import websockets
except ImportError:
    print('websockets not installed'); sys.exit(2)


def vcount():
    try:
        with urllib.request.urlopen(BASE + '/api/realtime/status', timeout=5) as r:
            d = json.loads(r.read().decode('utf-8'))
        return int((d.get('data', d)).get('violation_count') or 0)
    except Exception:
        return -1


async def main():
    t0 = time.time()
    events = []
    vc0 = vcount()
    print('=' * 74)
    print('ws  = %s' % URI)
    print('起始 violation_count = %d   观察 %.0f 秒' % (vc0, DURATION))
    print('=' * 74)
    try:
        async with websockets.connect(URI, open_timeout=10) as ws:
            print('已连接（后端已登记本客户端）')
            await ws.send('ping')

            async def recv_loop():
                while True:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=5)
                    except asyncio.TimeoutError:
                        continue
                    t = time.time() - t0
                    try:
                        j = json.loads(msg)
                    except Exception:
                        events.append((t, 'NON_JSON', str(msg)[:60]))
                        continue
                    if j.get('event') == 'violation_detected':
                        n = len(j.get('violations') or [])
                        types = [v.get('violation_type') for v in (j.get('violations') or [])]
                        events.append((t, 'PUSH', 'violations=%d %s conf=%s' % (n, types, j.get('confidence'))))
                    else:
                        events.append((t, 'OTHER', json.dumps(j)[:80]))

            async def poll_loop():
                prev = vc0
                while True:
                    await asyncio.sleep(2)
                    v = vcount()
                    if v > prev:
                        events.append((time.time() - t0, 'COUNTER', 'violation_count %d -> %d' % (prev, v)))
                        prev = v

            await asyncio.gather(
                recv_loop(),
                poll_loop(),
            ) if False else await asyncio.wait_for(
                asyncio.gather(recv_loop(), poll_loop()), timeout=DURATION)
    except asyncio.TimeoutError:
        pass
    except Exception as e:
        print('连接/接收异常: %s: %s' % (type(e).__name__, e))

    print()
    print('--- 时间轴（秒）---')
    for t, kind, detail in sorted(events, key=lambda x: x[0]):
        print('  %7.2fs  %-8s %s' % (t, kind, detail))
    pushes = [e for e in events if e[1] == 'PUSH']
    counters = [e for e in events if e[1] == 'COUNTER']
    others = [e for e in events if e[1] not in ('PUSH', 'COUNTER')]
    print()
    print('=' * 74)
    print('收到 violation_detected 推送: %d 次' % len(pushes))
    print('观测到 violation_count 上升 : %d 次' % len(counters))
    if others:
        print('其它帧: %d 条 例: %s' % (len(others), others[0][2]))
    if counters and not pushes:
        print('=> 后端**没有把违规推给 WebSocket 客户端**（问题在后端推送侧）')
    elif pushes and counters:
        # 配对：每次计数上升后，多久收到推送
        lags = []
        for t, _k, _d in counters:
            nxt = next((p[0] for p in pushes if p[0] >= t - 0.05), None)
            if nxt is not None:
                lags.append((nxt - t) * 1000)
        if lags:
            print('=> 推送正常。推送相对"计数上升"的延迟: %s'
                  % ', '.join('%.0fms' % x for x in lags))
    elif not counters and not pushes:
        print('=> 本窗口内没有违规发生（演示视频稀疏），需要更长的观察窗口')
    print('=' * 74)


asyncio.run(main())
