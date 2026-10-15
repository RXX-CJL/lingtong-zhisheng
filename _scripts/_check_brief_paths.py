# -*- coding: utf-8 -*-
"""校验移交文档里引用的所有绝对路径是否真实存在（2026-10-11 由 DSH 编写）"""
import io
import os
import re

DOC = r'E:\output\_GPT6_HANDOFF_BRIEF.md'
txt = io.open(DOC, encoding='utf-8').read()

# 匹配 Windows 绝对路径（含反斜杠/正斜杠），到空白或反引号/括号前结束
cands = re.findall(r'[A-Za-z]:[\\/][^\s`\)\]"\'<>|]+', txt)
paths = sorted(set(c.rstrip('.,;:、。）】') for c in cands))

ok = missing = 0
known_missing = set()
for p in paths:
    if os.path.exists(p):
        ok += 1
    else:
        missing += 1
        known_missing.add(p)
        print('  MISSING: %s' % p)

print()
print('文档: %s' % DOC)
print('  引用的绝对路径: %d 个' % len(paths))
print('  存在: %d   缺失: %d' % (ok, missing))
if not known_missing:
    print('  ✅ 全部存在')
