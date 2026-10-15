# -*- coding: utf-8 -*-
"""核查"00:16:26~00:16:37 的 28 次 15000ms 超时"到底是什么故障（2026-10-11 由 DSH 编写）

线索：用户还原的这份日志（export 于本地 2026-10-11 00:16:37）显示
  /realtime/status 与 /realtime/vehicles 各超时 14 次，cost 精确 15000/15001ms
—— 与另一份日志的"25 个 500 覆盖 9 接口"**是两种不同故障**。
本脚本查这个时刻的旁证：Windows 崩溃事件、后端日志、tcp 监听情况。
输出纯 ASCII。
"""
import io
import os
import subprocess
import sys

LOG = r'E:\output\1\api\output\logs\api.log'
WIN = '2026-10-11 00:0'      # 本地时间 00:0x（= 日志里的本地时间格式）

print('=' * 76)
print('1) Windows 崩溃事件（近 3 天全部）')
print('=' * 76)
ps = ("Get-WinEvent -FilterHashtable @{LogName='Application';ProviderName='Application Error';"
      "StartTime=(Get-Date).AddDays(-3)} -ErrorAction SilentlyContinue | "
      "Where-Object { $_.Message -match 'python' } | ForEach-Object { "
      "$m=$_.Message; $_.TimeCreated.ToString('MM-dd HH:mm:ss') + '  ' + "
      "([regex]::Match($m,'出错模块名称：\\s*([^,]+)')).Groups[1].Value.Trim() + '  ' + "
      "([regex]::Match($m,'异常代码：\\s*(\\S+)')).Groups[1].Value.Trim() }")
try:
    r = subprocess.run(['powershell', '-NoProfile', '-Command', ps],
                       capture_output=True, text=True, errors='replace', timeout=120)
    out = (r.stdout or '').strip()
    print('  ' + (out.replace('\n', '\n  ') if out else '(近 3 天无 python 崩溃事件)'))
except Exception as e:
    print('  查询失败:', e)

print()
print('=' * 76)
print('2) 后端日志在 2026-10-11 00:05~00:20 的记录（关键行）')
print('=' * 76)
if not os.path.exists(LOG):
    print('  日志不存在'); sys.exit(0)
lines = io.open(LOG, encoding='utf-8', errors='replace').read().splitlines()
keys = ('RealtimeDetector', 'ERROR', 'WARNING', 'Traceback', 'Exception',
        'settings', 'start', 'stop', '云端', '事件')
hits = [l for l in lines
        if l[:16] >= '2026-10-11 00:05' and l[:16] <= '2026-10-11 00:20']
print('  该时段日志行数: %d' % len(hits))
for l in hits[-45:]:
    print('   ', l[:165])

print()
print('=' * 76)
print('3) 日志里 00:16 前后是否有"启动/停止"痕迹（判断当时进程是否重启过）')
print('=' * 76)
for l in lines:
    if l[:16] >= '2026-10-11 00:00' and l[:16] <= '2026-10-11 00:30':
        low = l.lower()
        if any(k in low for k in ('uvicorn', 'started', 'application startup', 'shutdown',
                                  'detector] 检测已启动', 'detector] 检测已停止',
                                  '数据源已就绪')):
            print('   ', l[:165])
