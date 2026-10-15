"""精确验证「未标定超速跳过 AI」——只看本次新增事件"""

import io
import json
import sqlite3

DB = r"E:\output\1\api\zhitong_violations.db"
out = []
con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

# 本次新增 = 最近 80 行
cur.execute("SELECT MAX(id) m FROM traffic_events")
maxid = cur.fetchone()["m"]
cut = maxid - 80

cur.execute("SELECT event_type, state, COUNT(*) c FROM traffic_events WHERE id > ? GROUP BY event_type, state ORDER BY event_type, c DESC", (cut,))
out.append("=== 新增事件 类型 × 状态 ===")
for x in cur.fetchall():
    out.append(f"   {x['event_type']:18s} {x['state']:16s} {x['c']}")

out.append("")
out.append("=== 新增 speeding 事件的 state_history ===")
cur.execute("""SELECT event_id, state, state_history, vehicle_info FROM traffic_events
               WHERE id > ? AND event_type='speeding' ORDER BY id DESC LIMIT 5""", (cut,))
rows = cur.fetchall()
if not rows:
    out.append("   （本次新增里没有 speeding 事件）")
for x in rows:
    out.append(f"  --- {x['event_id']} state={x['state']}")
    h = str(x["state_history"] or "")
    try:
        hist = json.loads(h)
        for item in hist:
            out.append(f"      {item.get('old_state')} -> {item.get('new_state')}: {str(item.get('reason'))[:110]}")
    except Exception:
        out.append(f"      {h[:200]}")
    # 看 vehicle_info 里有没有 calibration
    try:
        vi = json.loads(x["vehicle_info"] or "{}")
        out.append(f"      vehicle_info.calibration={vi.get('calibration')} "
                   f"speed_method={vi.get('speed_method')} speed={vi.get('speed')}")
    except Exception:
        pass

out.append("")
out.append("=== 新增事件里所有含「跳过」或「未经场景标定」的记录 ===")
cur.execute("""SELECT event_id, event_type, state FROM traffic_events
               WHERE id > ? AND (state_history LIKE '%跳过%' OR state_history LIKE '%未经场景标定%')
               ORDER BY id DESC LIMIT 6""", (cut,))
sk = cur.fetchall()
if sk:
    for x in sk:
        out.append(f"   {x['event_id']} {x['event_type']} {x['state']}")
else:
    out.append("   （无 —— 说明本次没有触发该门禁，需确认是否有未标定超速事件）")

# 统计所有新增事件的类型
cur.execute("SELECT event_type, COUNT(*) c FROM traffic_events WHERE id > ? GROUP BY event_type ORDER BY c DESC", (cut,))
out.append("")
out.append("=== 新增事件类型汇总 ===")
for x in cur.fetchall():
    out.append(f"   {x['event_type']:18s} {x['c']}")
con.close()
io.open(r"E:\output\_round16_speeding.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
