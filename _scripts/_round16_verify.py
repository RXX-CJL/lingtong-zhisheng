"""验证事件 upsert 落库 + evidence_chain + 未标定超速跳过 AI"""

import io
import json
import sqlite3
import time
import urllib.request

BASE = "http://127.0.0.1:8001"
DB = r"E:\output\1\api\zhitong_violations.db"
out = []


def count_rows():
    c = sqlite3.connect(DB)
    n = c.execute("SELECT COUNT(*) FROM traffic_events").fetchone()[0]
    c.close()
    return n


base = count_rows()
out.append(f"基线（落库前）: {base} 行")
out.append("")
out.append("等待新事件落库（180 秒）...")
for i in range(6):
    time.sleep(30)
    n = count_rows()
    try:
        with urllib.request.urlopen(BASE + "/api/realtime/status", timeout=25) as r:
            d = json.loads(r.read().decode("utf-8", "ignore")).get("data", {})
        ev = d.get("event_engine") or {}
        out.append(f"[{(i+1)*30:>3}s] 内存事件={ev.get('total_events')}  "
                   f"数据库行数={n} (+{n-base})  processed={d.get('processed_frames')}")
    except Exception as e:
        out.append(f"[{(i+1)*30:>3}s] 数据库行数={n} (+{n-base})  状态查询失败 {type(e).__name__}")

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

out.append("")
out.append("=" * 72)
out.append("【验证 1】事件是否落库")
out.append("=" * 72)
cur.execute("SELECT COUNT(*) FROM traffic_events")
total = cur.fetchone()[0]
out.append(f"  总行数 {total}（基线 {base}，新增 {total-base}）")
out.append(f"  判定: {'✅ 事件已开始落库' if total > base else '❌ 仍不落库'}")

out.append("")
out.append("=" * 72)
out.append("【验证 2】evidence_chain 是否落库")
out.append("=" * 72)
cur.execute("""SELECT COUNT(*) t,
                      SUM(CASE WHEN evidence_chain IS NOT NULL AND evidence_chain != '' THEN 1 ELSE 0 END) h
               FROM traffic_events WHERE id > (SELECT MAX(id)-? FROM traffic_events)""", (max(1, total-base),))
r = cur.fetchone()
out.append(f"  新增事件中有证据链: {r['h']}/{r['t']}")
cur.execute("""SELECT event_id, event_type, state, LENGTH(evidence_chain) len
               FROM traffic_events WHERE evidence_chain IS NOT NULL AND evidence_chain != ''
               ORDER BY id DESC LIMIT 3""")
for x in cur.fetchall():
    out.append(f"    {x['event_id']}  {x['event_type']}  {x['state']}  {x['len']} 字节")
cur.execute("""SELECT COUNT(*) FROM traffic_events WHERE evidence_chain IS NOT NULL AND evidence_chain != ''""")
out.append(f"  全库有证据链: {cur.fetchone()[0]} 条（修复前 0 条）")

out.append("")
out.append("=" * 72)
out.append("【验证 3】未标定超速是否跳过 AI")
out.append("=" * 72)
cur.execute("""SELECT event_id, state, state_history FROM traffic_events
               WHERE event_type='speeding' ORDER BY id DESC LIMIT 8""")
skip = aiby = 0
for x in cur.fetchall():
    h = str(x["state_history"] or "")
    if "未经场景标定" in h or "跳过云端复核" in h:
        skip += 1
    if "AI 排除" in h or "AI 确认" in h:
        aiby += 1
    out.append(f"    {x['event_id']} {x['state']:14s} 跳过AI={('未经场景标定' in h)} AI判={('AI' in h and '排除' in h)}")
out.append(f"  最近 8 条 speeding: 标明跳过复核 {skip} 条，经 AI 判定 {aiby} 条")

out.append("")
out.append("=" * 72)
out.append("【验证 4】状态分布是否随实时变化")
out.append("=" * 72)
cur.execute("""SELECT state, COUNT(*) c FROM traffic_events
               WHERE id > (SELECT MAX(id)-? FROM traffic_events) GROUP BY state""", (max(1, total-base),))
for x in cur.fetchall():
    out.append(f"    {x['state']:16s} {x['c']}")
con.close()

io.open(r"E:\output\_round16_verify.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
