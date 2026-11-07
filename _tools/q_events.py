# -*- coding: utf-8 -*-
import sqlite3, json, os, sys
os.chdir(r"E:\output\1\api")

def find_db():
    for name in ("zhitong_violations.db", "zhitong.db"):
        if os.path.exists(name):
            try:
                c = sqlite3.connect(name)
                tabs = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")]
                if "traffic_events" in tabs:
                    return name, c, tabs
                c.close()
            except Exception:
                pass
    return None, None, []

dbname, conn, tabs = find_db()
print("DB =", dbname)
if conn is None:
    sys.exit(1)

conn.row_factory = sqlite3.Row
cols = [r[1] for r in conn.execute("PRAGMA table_info(traffic_events)")]
print("COLS =", ",".join(cols))

rows = conn.execute("SELECT * FROM traffic_events ORDER BY id DESC LIMIT 12").fetchall()
print("RECENT_COUNT =", len(rows))
for r in rows:
    d = dict(r)
    aj = d.get("ai_judgment") or ""
    # 判断是否真云端
    method = "-"
    try:
        j = json.loads(aj) if aj.strip().startswith("{") else {}
        fin = j.get("final") or {}
        method = str(fin.get("method") or "-")
    except Exception:
        method = "PARSE_FAIL"
    print("ID=%s | %s | %s | method=%s | ai_len=%d" % (
        d.get("id"), str(d.get("trigger_time"))[:19], str(d.get("event_type"))[:14], method, len(aj)))

# 汇总
tot = conn.execute("SELECT COUNT(*) FROM traffic_events").fetchone()[0]
print("TOTAL_EVENTS =", tot)
rows2 = conn.execute("SELECT ai_judgment FROM traffic_events").fetchall()
n_local, n_real, n_empty = 0, 0, 0
for r in rows2:
    aj = r[0] or ""
    if not aj.strip():
        n_empty += 1
        continue
    if "local_fallback" in aj:
        n_local += 1
    else:
        n_real += 1
print("EMPTY =", n_empty, "| LOCAL_FALLBACK =", n_local, "| NON_LOCAL(疑似真云端) =", n_real)
