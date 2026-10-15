"""修复后最终验证：事件应从 pending_ai 推进到 AI_REVIEWED/CONFIRMED，且不再有 AI 分析失败"""

import io
import json
import os
import re
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8001"
VIDEO = r"E:\output\1\test_assets\traffic_videos\test1.mp4"
LOG = os.path.join(os.environ.get("TEMP", "."), "api-boot5.err")
OUT = r"E:\output\_verify_final.md"


def call(method, path, body=None, timeout=90):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "ignore")
            try:
                return r.status, json.loads(raw)
            except Exception:
                return r.status, raw
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore")[:200]
    except Exception as e:
        return None, f"{type(e).__name__}: {str(e)[:150]}"


buf = []


def out(s=""):
    buf.append(s)


out("# 事件闭环修复验证\n")

st, js = call("GET", "/api/realtime/events?page=1&size=200")
before = {}
if isinstance(js, dict):
    for r in (js.get("data") or []):
        before[r.get("event_id")] = r.get("state")
out(f"- 启动前事件数: **{len(before)}**\n")

out("\n## 启动检测（修复后）\n")
st, js = call("POST", "/api/realtime/start", {"video_path": VIDEO})
out(f"- HTTP {st}: `{js}`\n")

out("\n## 观察 100 秒\n")
out("| 时刻 | running | total | processed | 违规 | 事件数 |")
out("|---|---|---|---|---|---|")
proc_series = []
for i in range(10):
    time.sleep(10)
    st, sjs = call("GET", "/api/realtime/status")
    d = sjs.get("data", {}) if isinstance(sjs, dict) else {}
    st2, ejs = call("GET", "/api/realtime/events?page=1&size=200")
    n = len((ejs.get("data") or [])) if isinstance(ejs, dict) else -1
    proc_series.append(d.get("processed_frames", 0))
    out(f"| {i*10+10}s | {d.get('running')} | {d.get('total_frames')} | "
        f"{d.get('processed_frames')} | {d.get('violation_count')} | {n} |")

out(f"\n- processed 增长: {proc_series[0]} -> {proc_series[-1]} "
    f"(+{proc_series[-1]-proc_series[0]})\n")

out("\n## 新增事件的状态分布（关键指标）\n")
st, ejs = call("GET", "/api/realtime/events?page=1&size=200")
rows = ejs.get("data") or [] if isinstance(ejs, dict) else []
new = [r for r in rows if r.get("event_id") not in before]
states = {}
for r in new:
    states[r.get("state")] = states.get(r.get("state"), 0) + 1
out(f"- 新增 {len(new)} 条，状态分布: `{states}`\n")
out("\n| 事件ID | 类型 | 状态 | AI置信度 | 视频 |")
out("|---|---|---|---|---|")
for r in new[:14]:
    out(f"| `{str(r.get('event_id'))[:30]}` | {r.get('event_type')} | "
        f"**{r.get('state')}** | {r.get('ai_confidence')} | "
        f"{'Y' if r.get('event_video_path') else 'N'} |")

call("POST", "/api/realtime/stop")

out("\n## 后端日志：'AI 分析失败' 是否消失\n")
if os.path.exists(LOG):
    with io.open(LOG, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    fails = [l for l in lines if "推送 AI 分析失败" in l or "AI 分析失败" in l]
    fmterr = [l for l in lines if "format code" in l]
    out(f"- 日志行数: {len(lines)}")
    out(f"- **AI 分析失败 次数: {len(fails)}** （修复前为 11 次）")
    out(f"- **format code 错误次数: {len(fmterr)}** （修复前多次）")
    if fails:
        out("\n  仍存在的失败样本：")
        for l in fails[:5]:
            out(f"  - `{l[:180]}`")
else:
    out(f"- 日志不存在: {LOG}")

with io.open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(buf) + "\n")
print("OK ->", OUT)
