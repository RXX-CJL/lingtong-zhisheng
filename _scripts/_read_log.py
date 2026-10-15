"""正确解码后端日志，找出豆包失败的真实原因链"""

import collections
import io
import os
import re

LOG = os.path.join(os.environ.get("TEMP", "."), "api-boot4.err")
print("日志:", LOG, os.path.getsize(LOG), "字节")

with io.open(LOG, encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()

print(f"总行数: {len(lines)}")

print()
print("=" * 78)
print("1) 唯一警告/错误（按次数）")
print("=" * 78)
warns = [l for l in lines if any(k in l for k in ("WARNING", "ERROR"))]
warns_norm = [re.sub(r"evt_\d+_\d+_[0-9a-f]+", "evt_<ID>", w) for w in warns]
for text, cnt in collections.Counter(warns_norm).most_common(12):
    print(f"  [{cnt:3d}x] {text[:150]}")

print()
print("=" * 78)
print("2) 云端协作相关日志（最近 20 条）")
print("=" * 78)
cloud = [l for l in lines if "CloudCollaborator" in l or "云端" in l]
for l in cloud[-20:]:
    print("  " + l[:160])

print()
print("=" * 78)
print("3) 豆包 / dashscope 相关")
print("=" * 78)
db = [l for l in lines if any(k in l.lower() for k in ("豆包", "doubao", "dashscope", "qwen"))]
print(f"  命中 {len(db)} 行")
for l in db[-15:]:
    print("  " + l[:170])
