# -*- coding: utf-8 -*-
"""真数据验证：每辆车只会被画一个框（2026-10-09 由 DSH 编写）

## 为什么这样做
"每辆车两个框"是个**不报错、不写日志**的视觉回归，只能靠肉眼看画面发现（用户就是这样发现的）。
本轮新增了 `/status` 的 `box_draw_stats`（见 `annotation_renderer._BOX_STATS`），
把渲染器每帧的关联结果暴露出来，于是**这个 bug 类以后可以被自动检测**。

## 前置条件
1. 后端 8001 正在跑，且**检测已启动**（源应为演示视频）；
2. 必须让服务端**真的在跑绘制** —— `_draw_detection_boxes()` 只在有 MJPEG 客户端时才执行。
   后端不主动画帧，所以**没人开着 /live 画面时 box_draw_stats 不会更新**。
   本脚本用浏览器打开一次 `/live` 来产生这个客户端（也可手动开着页面再跑本脚本）。

## 判定
`box_draw_stats.main_boxes` = 本帧主循环画的框数（≈ 车辆数 + 少量非车类）
`box_draw_stats.max_dets_per_track` = **单个 track 被几条 detection 占用**
   -> 旧 bug 下会 >1 或（更常见）出现"关联 0 条 + 兜底又画 1 个"的组合；
   -> 修复后应恒为 1。
输出纯 ASCII。
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

BASE = 'http://127.0.0.1:8001'
UI = 'http://localhost:5173/live'
FAILS = []
SAMPLES = 25


def check(name, ok, detail=''):
    print(('  PASS  ' if ok else '  FAIL  ') + name + (('  | ' + str(detail)) if detail else ''))
    if not ok:
        FAILS.append(name)


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=15) as r:
        return json.loads(r.read().decode('utf-8'))


def data_of(r):
    return r.get('data', r) if isinstance(r, dict) else {}


st = data_of(get('/api/realtime/status'))
print('=' * 74)
print('running=%s source=%s box_prediction=%s'
      % (st.get('running'), st.get('video_path'), st.get('box_prediction')))
print('=' * 74)
if not st.get('running'):
    print('  -> start detection in the UI first, then re-run')
    sys.exit(2)

# 打开一个**无头** Playwright 浏览器产生 MJPEG 客户端（否则绘制侧不跑、统计不更新）
# ⚠ 不要用系统 Chrome/Edge 起可见窗口：那会打扰用户（本轮已犯过一次，勿再犯）。
NODE = r'E:\node.exe'
UICHECK = r'E:\output\_uicheck'
driver_script = os.path.join(UICHECK, '_tmp_headless_open.mjs')
proc = None
if os.path.exists(NODE):
    with open(driver_script, 'w', encoding='utf-8') as f:
        f.write(
            "import { chromium } from 'playwright';\n"
            "const b = await chromium.launch({ headless: true });\n"
            "const p = await b.newPage();\n"
            "await p.goto('%s', { waitUntil: 'domcontentloaded', timeout: 30000 });\n"
            "await p.waitForTimeout(%d);\n"
            "await b.close();\n" % (UI, int(SAMPLES * 1200) + 8000))
    env = dict(os.environ)
    env['PATH'] = r'E:\;' + env.get('PATH', '')
    print('opening HEADLESS chromium to create the MJPEG client...')
    proc = subprocess.Popen([NODE, driver_script], cwd=UICHECK, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
else:
    print('WARN: node not found - open /live in a browser manually, then re-run')

print('sampling box_draw_stats for ~%ds (needs live drawing)...' % SAMPLES)
seen = []
with_veh = 0
try:
    for i in range(SAMPLES):
        time.sleep(1.2)
        s = data_of(get('/api/realtime/status'))
        b = s.get('box_draw_stats') or {}
        nveh = int(s.get('tracked_vehicle_count') or 0)
        if b.get('frames', 0) and b.get('last_update'):
            seen.append(b)
            if nveh > 0:
                with_veh += 1
            print('  %2d) frames=%-4s main=%-2s fallback=%-2s unmatched=%-2s '
                  'max_per_track=%-2s tracks=%-2s veh=%-2s @%s'
                  % (i, b.get('frames'), b.get('main_boxes'), b.get('fallback_boxes'),
                     b.get('unmatched_dets'), b.get('max_dets_per_track'),
                     b.get('tracks_drawn'), nveh, b.get('last_update')))
finally:
    if proc is not None:
        try:
            proc.terminate()
        except Exception:
            pass
    try:
        if os.path.exists(driver_script):
            os.remove(driver_script)
    except Exception:
        pass

print()
check('box_draw_stats updated (drawing really happened)', len(seen) > 0,
      'samples=%d' % len(seen))
check('drawing happened while vehicles were tracked (test is meaningful)',
      with_veh >= 3, 'samples with tracked_vehicle_count>0: %d' % with_veh)
if seen:
    fresh = [b for b in seen if int(b.get('main_boxes') or 0)
             + int(b.get('fallback_boxes') or 0) > 0]
    pool = fresh or seen
    max_per = max(int(b.get('max_dets_per_track') or 0) for b in pool)
    max_main = max(int(b.get('main_boxes') or 0) for b in pool)
    max_fb = max(int(b.get('fallback_boxes') or 0) for b in pool)
    stale = len({b.get('last_update') for b in seen})
    print('  frames with boxes drawn: %d / %d' % (len(fresh), len(seen)))
    check('★NO track is hit by more than one detection (would draw 2 boxes)',
          max_per <= 1, 'max_dets_per_track=%d' % max_per)
    check('main loop draws boxes (renderer active)', max_main > 0, 'max main_boxes=%d' % max_main)
    check('fallback loop is not doing the main loop job (old bug symptom)',
          max_fb <= max_main, 'fallback max=%d vs main max=%d' % (max_fb, max_main))
    check('stats are fresh (distinct timestamps while sampling)', stale >= 2,
          'distinct last_update=%d' % stale)

print()
print('=' * 74)
print('RESULT: %s   (%d failed)' % ('PASS' if not FAILS else 'FAIL', len(FAILS)))
for f in FAILS:
    print('  - ' + f)
print('=' * 74)
sys.exit(1 if FAILS else 0)
