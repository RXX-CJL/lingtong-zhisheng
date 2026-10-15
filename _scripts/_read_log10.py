"""正确解析 UTF-8 日志 -> 写入文件（避免控制台 GBK 限制）"""

import collections
import io
import os
import re

LOG = os.path.join(os.environ.get("TEMP", "."), "api-boot10.err")
OUT = r"E:\output\_log10_report.md"

with io.open(LOG, encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()

buf = [f"# 解耦验证日志分析（{len(lines)} 行）\n"]

CHECKS = {
    "云端 worker 启动": "云端咨询后台线程已启动",
    "云端咨询完成": "云端咨询完成",
    "云端咨询失败": "云端咨询异步任务失败",
    "入队失败": "云端咨询入队失败",
    "格式化错误(format code)": "format code",
    "帧处理异常": "帧处理异常",
    "检测循环异常": "检测循环异常",
    "画框失败": "画框失败",
}

buf.append("\n## 1) 关键事件计数\n")
buf.append("| 事件 | 次数 |")
buf.append("|---|---|")
for label, kw in CHECKS.items():
    n = sum(1 for l in lines if kw in l)
    buf.append(f"| {label} | **{n}** |")

buf.append("\n## 2) 日志级别统计\n")
lv = collections.Counter()
for l in lines:
    m = re.search(r" - (DEBUG|INFO|WARNING|ERROR) - ", l)
    if m:
        lv[m.group(1)] += 1
for k, v in lv.most_common():
    buf.append(f"- {k}: {v}")

buf.append("\n## 3) 云端相关样本（最多 8 条）\n")
cloud = [l for l in lines if "CloudCollaborator" in l or "云端" in l]
for l in cloud[-8:]:
    buf.append(f"- `{l[:200]}`")

buf.append("\n## 4) WARNING/ERROR 样本（最多 10 条）\n")
we = [l for l in lines if "WARNING" in l or "ERROR" in l]
wew = [re.sub(r"evt_\d+_\d+_[0-9a-f]+", "evt_<ID>", x) for x in we]
for text, cnt in collections.Counter(wew).most_common(10):
    buf.append(f"- [{cnt}x] `{text[:200]}`")

buf.append("\n## 5) 最后 5 行\n")
for l in lines[-5:]:
    buf.append(f"- `{l[:220]}`")

with io.open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(buf) + "\n")
print("OK ->", OUT, os.path.getsize(OUT), "bytes")
