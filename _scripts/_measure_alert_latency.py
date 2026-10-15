# -*- coding: utf-8 -*-
"""量化「告警卡片比画面标注慢多少」（2026-10-11 由 DSH 编写）

## 两条链路
- **画面标注**：检测那一帧直接画在图上，编成 JPEG 进 MJPEG 流（20 fps 持续推）
  -> 违规一旦被判定，**下一个流帧**就能看到，追加延迟 ≈ 0（只剩流帧间隔 ≤50ms）
- **右栏告警**：写进 `_recent_violations` -> 前端**定时轮询** `/realtime/vehicles`
  -> 追加延迟 = **一次轮询周期的等待**（平均 T/2，最坏 T）

## 本脚本怎么量
以**后端判定成立的那一刻**为基准（轮询 `/status` 的 `violation_count` 增长，
采样间隔 50ms，量化误差 ±50ms），测右栏数据出现的时间差。
· 直接用 50ms 高频采样：得到的是"后端 -> 接口"的最小延迟（不含前端轮询等待）
· 再用"前端轮询周期 T"推算用户实际等待：**T/2 平均、T 最坏**

用法：python _measure_alert_latency.py [seconds]
输出纯 ASCII。
"""
import json
import sys
import time
import urllib.request

BASE = 'http://127.0.0.1:8001'
DURATION = float(sys.argv[1]) if len(sys.argv) > 1 else 240.0
SAMPLE = 0.05          # 50ms 高频采样（量化误差 ±50ms）

FRONT_POLL_MS = 800    # 前端当前轮询周期（LiveMonitor.vue: setInterval(refresh, 800)）


def get(path, timeout=5):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def data_of(r):
    return r.get('data', r) if isinstance(r, dict) else {}


st = data_of(get('/api/realtime/status'))
print('=' * 76)
print('running=%s  单帧耗时约 %.0fms (fps=%.2f)'
      % (st.get('running'), 1000.0 / max(0.01, float(st.get('current_fps') or 0.01)),
         float(st.get('current_fps') or 0)))
print('前端轮询周期 = %dms  ->  用户平均多等 %dms、最坏多等 %dms'
      % (FRONT_POLL_MS, FRONT_POLL_MS // 2, FRONT_POLL_MS))
print('采样间隔 = %dms（量化误差 ±%dms）' % (SAMPLE * 1000, SAMPLE * 1000))
print('=' * 76)
if not st.get('running'):
    print('detection not running'); sys.exit(2)

vc_prev = None
t_first_vc = None
t_first_panel = None
pairs = []
t0 = time.time()
n = 0
while time.time() - t0 < DURATION:
    n += 1
    try:
        s = data_of(get('/api/realtime/status'))
        v = data_of(get('/api/realtime/vehicles'))
        vc = int(s.get('violation_count') or 0)
        panel_n = len(v.get('violators') or [])
        t = time.time() - t0
        if vc_prev is not None and vc > vc_prev:
            t_first_vc = t
            t_first_panel = None
            print('  t=%7.2fs  后端判定成立 (累计违规 %d -> %d)' % (t, vc_prev, vc))
        if panel_n > 0 and t_first_vc is not None and t_first_panel is None:
            t_first_panel = t
            lag = (t_first_panel - t_first_vc) * 1000
            pairs.append(lag)
            print('  t=%7.2fs  右栏数据可见   -> 后端->接口延迟 = %+.0fms' % (t, lag))
        vc_prev = vc
    except Exception:
        pass
    time.sleep(SAMPLE)

print()
print('=' * 76)
print('采样 %d 次 / %.0f 秒，抓到 %d 对「判定->接口可见」' % (n, DURATION, len(pairs)))
if pairs:
    pairs_sorted = sorted(pairs)
    print('  后端->接口 延迟: min=%+.0fms  中位=%+.0fms  max=%+.0fms'
          % (pairs_sorted[0], pairs_sorted[len(pairs_sorted) // 2], pairs_sorted[-1]))
    med = pairs_sorted[len(pairs_sorted) // 2]
    print()
    print('  ⇒ 估算**用户实际感知**的额外延迟（含前端轮询等待 %dms/2 平均）:' % FRONT_POLL_MS)
    print('     平均 ≈ %+.0fms + %dms = 约 %.2f 秒' % (med, FRONT_POLL_MS // 2,
                                                (med + FRONT_POLL_MS / 2) / 1000.0))
    print('     最坏 ≈ %+.0fms + %dms = 约 %.2f 秒'
          % (pairs_sorted[-1], FRONT_POLL_MS, (pairs_sorted[-1] + FRONT_POLL_MS) / 1000.0))
else:
    print('  本窗口内没抓到违规（演示视频里违规较稀疏，可延长采样）')
print('=' * 76)
