"""验证两个修复：① 未标定超速跳过 AI 复核 ② evidence_chain 落库"""

import io
import json
import sqlite3
import time
import urllib.request

BASE = "http://127.0.0.1:8001"
DB = r"E:\output\1\api\zhitong_violations.db"
out = []

print("等待事件产生（150 秒）...")
for i in range(5):
    time.sleep(30)
    try:
        with urllib.request.urlopen(BASE + "/api/realtime/status", timeout=25) as r:
            d = json.loads(r.read().decode("utf-8", "ignore")).get("data", {})
        ev = d.get("event_engine") or {}
        out.append(f"[{(i+1)*30:>3}s] processed={d.get('processed_frames')} "
                   f"事件总数={ev.get('total_events')} pending_ai={ev.get('pending_ai')} "
                   f"confirmed={ev.get('confirmed')}")
    except Exception as e:
        out.append(f"[{(i+1)*30:>3}s] 查询失败 {type(e).__name__}")

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

out.append("")
out.append("=" * 72)
out.append("【修复 2】evidence_chain 是否已落库")
out.append("=" * 72)
cur.execute("""SELECT COUNT(*) total,
                      SUM(CASE WHEN evidence_chain IS NOT NULL AND evidence_chain != '' THEN 1 ELSE 0 END) has_chain
               FROM traffic_events""")
r = cur.fetchone()
out.append(f"  总事件 {r['total']}，有证据链 {r['has_chain']} 条 "
           f"({r['has_chain']/max(1,r['total'])*100:.1f}%)   ← 修复前是 0%")

cur.execute("""SELECT event_id, event_type, state, LENGTH(evidence_chain) len
               FROM traffic_events WHERE evidence_chain IS NOT NULL AND evidence_chain != ''
               ORDER BY id DESC LIMIT 3""")
rows = cur.fetchall()
for x in rows:
    out.append(f"    {x['event_id']}  {x['event_type']}  {x['state']}  {x['len']} 字节")
if rows:
    cur.execute("SELECT evidence_chain FROM traffic_events WHERE event_id=?", (rows[0]["event_id"],))
    raw = cur.fetchone()["evidence_chain"]
    try:
        d = json.loads(raw)
        out.append(f"    证据链字段: {sorted(d.keys())[:14]}")
        out.append(f"    vehicle_id={d.get('vehicle_id')} plate={d.get('plate_number')!r} "
                   f"key_frames={len(d.get('key_frames') or [])} "
                   f"trajectory={len(d.get('trajectory') or [])} "
                   f"final_status={d.get('final_status')} note={d.get('_note')}")
    except Exception as e:
        out.append(f"    解析失败: {e}")

out.append("")
out.append("=" * 72)
out.append("【修复 1】未标定超速是否跳过 AI 复核")
out.append("=" * 72)
cur.execute("""SELECT event_type, state, COUNT(*) c FROM traffic_events
               GROUP BY event_type, state ORDER BY event_type, c DESC""")
out.append("  事件类型 × 状态:")
for x in cur.fetchall():
    out.append(f"    {x['event_type']:18s} {x['state']:16s} {x['c']}")

# 看 speeding 事件的 state_history 是否含"未经场景标定"
cur.execute("""SELECT event_id, state, state_history FROM traffic_events
               WHERE event_type='speeding' ORDER BY id DESC LIMIT 6""")
out.append("")
hit_skip = 0
for x in cur.fetchall():
    h = str(x["state_history"] or "")
    skip = "未经场景标定" in h or "跳过云端复核" in h
    if skip:
        hit_skip += 1
    out.append(f"    {x['event_id']} state={x['state']:14s} 含'跳过AI'说明={skip}")
out.append(f"")
out.append(f"  最近 6 条 speeding 中，标明'未经标定跳过复核'的: {hit_skip} 条")
out.append(f"  （修复 1 生效的话，未标定的超速不应再出现 pending_ai / rejected-by-AI）")
con.close()

io.open(r"E:\output\_round15_verify.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
