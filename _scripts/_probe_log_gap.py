# -*- coding: utf-8 -*-
"""细看 00:16:20~00:16:45 那 25 秒逐行日志（超时窗口）2026-10-11 由 DSH 编写"""
import io
import re
from collections import Counter

LOG = r'E:\output\1\api\output\logs\api.log'
lines = io.open(LOG, encoding='utf-8', errors='replace').read().splitlines()

def ts(l):
    return l[:19]

lo, hi = '2026-10-11 00:16:00', '2026-10-11 00:17:30'
win = [l for l in lines if lo <= ts(l) <= hi]
print('窗口 %s ~ %s  共 %d 行' % (lo, hi, len(win)))
print('=' * 78)
for l in win:
    print(l[:170])

print()
print('=' * 78)
print('日志"空档"分析：整条日志里相邻两行间隔 > 5 秒的地方（= 进程可能卡住）')
print('=' * 78)
from datetime import datetime


def parse(l):
    try:
        return datetime.strptime(l[:23], '%Y-%m-%d %H:%M:%S,%f')
    except Exception:
        try:
            return datetime.strptime(l[:19], '%Y-%m-%d %H:%M:%S')
        except Exception:
            return None


stamped = [(parse(l), l) for l in lines if parse(l)]
gaps = []
for (t1, l1), (t2, l2) in zip(stamped, stamped[1:]):
    d = (t2 - t1).total_seconds()
    if d > 5:
        gaps.append((d, t1, t2, l1, l2))
gaps.sort(key=lambda x: -x[0])
print('  间隔 >5 秒的处数: %d' % len(gaps))
for d, t1, t2, l1, l2 in gaps[:12]:
    print('  %6.1fs  %s -> %s' % (d, t1.strftime('%m-%d %H:%M:%S'), t2.strftime('%H:%M:%S')))
    print('        前一行: %s' % l1[:135])
    print('        后一行: %s' % l2[:135])
