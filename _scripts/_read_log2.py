"""正确解码后端日志 -> 写入 UTF-8 报告文件（绕开控制台 GBK 限制）"""

import collections
import io
import os
import re

LOG = os.path.join(os.environ.get("TEMP", "."), "api-boot4.err")
OUT = r"E:\output\_log_report.md"

with io.open(LOG, encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()

buf = []
buf.append(f"# 后端日志分析（{os.path.basename(LOG)}，{len(lines)} 行）\n")

buf.append("\n## 1) 唯一警告/错误（按次数排序）\n")
warns = [l for l in lines if ("WARNING" in l or "ERROR" in l)]
warns_norm = [re.sub(r"evt_\d+_\d+_[0-9a-f]+", "evt_<ID>", w) for w in warns]
if not warns:
    buf.append("（无）")
for text, cnt in collections.Counter(warns_norm).most_common(15):
    buf.append(f"- **[{cnt}x]** `{text[:200]}`")

buf.append("\n## 2) 云端协作 / 豆包 相关（最近 30 条）\n")
cloud = [l for l in lines
         if any(k in l for k in ("CloudCollaborator", "豆包", "doubao", "dashscope", "qwen", "云端"))]
buf.append(f"命中 {len(cloud)} 行\n")
for l in cloud[-30:]:
    buf.append(f"- `{l[:220]}`")

buf.append("\n## 3) 事件生命周期相关（最近 20 条）\n")
life = [l for l in lines if any(k in l for k in ("事件", "event", "AI 复核", "生命周期"))]
for l in life[-20:]:
    buf.append(f"- `{l[:220]}`")

buf.append("\n## 4) 日志最后 15 行\n")
for l in lines[-15:]:
    buf.append(f"- `{l[:220]}`")

with io.open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(buf) + "\n")

print("OK ->", OUT, os.path.getsize(OUT), "bytes")
