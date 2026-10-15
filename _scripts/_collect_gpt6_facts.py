# -*- coding: utf-8 -*-
"""收集交接给 GPT6 所需的事实（只读，2026-10-11 由 DSH 编写）"""
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import urllib.request

DB = r'E:\output\1\api\zhitong_violations.db'
BASE = 'http://127.0.0.1:8001'

print('=' * 78)
print('1) 当前后端状态')
print('=' * 78)
try:
    with urllib.request.urlopen(BASE + '/api/realtime/status', timeout=8) as r:
        st = json.loads(r.read().decode('utf-8'))
    st = st.get('data', st)
    print('  running        :', st.get('running'))
    print('  source         :', st.get('video_path'))
    print('  processed      :', st.get('processed_frames'))
    print('  scope / roi    :', st.get('traffic_light_scope'), '/', st.get('scene_annotation_roi_count'))
    print('  tl_color_model :', (st.get('tl_color_model') or {}).get('file'))
    print('  model_sequence :', st.get('model_sequence'))
    print('  yolo_imgsz     :', st.get('yolo_imgsz'))
    print('  ws_push        :', json.dumps(st.get('ws_push'), ensure_ascii=False))
except Exception as e:
    print('  /status 失败:', e)

print()
print('=' * 78)
print('2) 数据库规模与脏数据')
print('=' * 78)
c = sqlite3.connect(DB)
c.row_factory = sqlite3.Row
n_all = list(c.execute('select count(*) from traffic_events'))[0][0]
n_1970 = list(c.execute(
    "select count(*) from traffic_events where trigger_time < '2000-01-01'"))[0][0]
n_ev = list(c.execute('select count(*) from violation_evidences'))[0][0]
print('  traffic_events       :', n_all)
print('  其中 1970 年时间戳   :', n_1970, '(%.1f%%)' % (100.0 * n_1970 / max(1, n_all)))
print('  violation_evidences  :', n_ev)
print()
print('  --- 最近 300 条事件的 state 分布（看云端复核是否在乱驳回）---')
for r in c.execute("select state, count(*) n from (select state from traffic_events "
                   "order by rowid desc limit 300) group by state order by n desc"):
    print('    %-16s %d' % (r['state'], r['n']))
print()
print('  --- 最近 8 条事件（看 timestamp 是否正常）---')
for r in c.execute('select event_id, event_type, state, trigger_time from traffic_events '
                   'order by rowid desc limit 8'):
    print('    %s  %-11s %-14s %s' % (str(r['trigger_time'])[:19], r['event_type'],
                                      r['state'], r['event_id']))

print()
print('=' * 78)
print('3) 今天 python.exe 崩溃记录（Application Error）')
print('=' * 78)
try:
    ps = subprocess.run(
        ['powershell', '-NoProfile', '-Command',
         "Get-WinEvent -FilterHashtable @{LogName='Application';ProviderName='Application Error';"
         "StartTime=(Get-Date).AddDays(-1)} -ErrorAction SilentlyContinue | "
         "Where-Object { $_.Message -match 'python' } | "
         "ForEach-Object { $_.TimeCreated.ToString('MM-dd HH:mm:ss') + ' | ' + "
         "([regex]::Match($_.Message,'出错模块名称：\\s*([^,]+)')).Groups[1].Value.Trim() + ' | ' + "
         "([regex]::Match($_.Message,'异常代码：\\s*(\\S+)')).Groups[1].Value.Trim() }"],
        capture_output=True, text=True, timeout=90)
    out = (ps.stdout or '').strip()
    print('  ' + (out.replace('\n', '\n  ') if out else '(过去 24 小时无 python 崩溃记录)'))
except Exception as e:
    print('  查询失败:', e)

print()
print('=' * 78)
print('4) 崩溃转储文件')
print('=' * 78)
d = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'CrashDumps')
if os.path.isdir(d):
    files = sorted((f for f in os.listdir(d) if f.startswith('python.exe')),
                   key=lambda f: os.path.getmtime(os.path.join(d, f)), reverse=True)[:6]
    for f in files:
        fp = os.path.join(d, f)
        print('  %-34s %6.0f MB  %s' % (f, os.path.getsize(fp) / 1048576,
                                        time.strftime('%m-%d %H:%M', time.localtime(os.path.getmtime(fp)))))
else:
    print('  无 CrashDumps 目录')

print()
print('=' * 78)
print('5) 关键素材')
print('=' * 78)
for p in (r'E:\output\_dual_cam_demo\dual_cam_demo_lossless.mkv',
          r'E:\output\_dual_cam_demo\dual_cam_demo_h264.mp4'):
    if os.path.exists(p):
        print('  %-52s %8.1f MB' % (os.path.basename(p), os.path.getsize(p) / 1048576))
    else:
        print('  %-52s (缺失)' % os.path.basename(p))
c.close()
