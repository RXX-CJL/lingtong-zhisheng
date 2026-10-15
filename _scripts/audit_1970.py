# -*- coding: utf-8 -*-
"""只读复核 1970 脏数据（不改任何数据，不用写连接模式）。

对应 _DSH_OFFICE_STATE.md §26.7 的结论：traffic_events 共 3209 行，其中 566 行
trigger_time 年份是 1970。本脚本用于验证该结论是否仍成立。
"""
import sqlite3
import sys

# 控制台按 UTF-8 输出，避免 GBK 乱码
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

DB = r"E:\output\1\api\zhitong_violations.db"

# mode=ro：只读打开，物理上不可能写入
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
cur = con.cursor()

print("== 表清单 ==")
tables = [r[0] for r in cur.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
print(", ".join(tables))

if "traffic_events" not in tables:
    print("!! 没有 traffic_events 表")
    sys.exit(1)

print("\n== traffic_events 总数 ==")
total = cur.execute("SELECT COUNT(*) FROM traffic_events").fetchone()[0]
print("total =", total)

print("\n== trigger_time 年份分布 ==")
rows = cur.execute("""
    SELECT substr(CAST(trigger_time AS TEXT), 1, 4) AS yr, COUNT(*) AS n
    FROM traffic_events GROUP BY yr ORDER BY n DESC
""").fetchall()
for yr, n in rows:
    print(f"  {yr}: {n}")

dirty = cur.execute("""
    SELECT COUNT(*) FROM traffic_events
    WHERE substr(CAST(trigger_time AS TEXT), 1, 4) = '1970'
""").fetchone()[0]
print("\n1970 行数 =", dirty, f"({dirty * 100.0 / total:.1f}%)" if total else "")

print("\n== 1970 样本 5 条 ==")
sample_cols = [c for c in ("id", "trigger_time", "created_at", "event_type",
                           "violation_type", "vehicle_plate")
               if c in [r[1] for r in cur.execute("PRAGMA table_info(traffic_events)")]]
for r in cur.execute(f"""
    SELECT {', '.join(sample_cols)}
    FROM traffic_events
    WHERE substr(CAST(trigger_time AS TEXT), 1, 4) = '1970'
    ORDER BY id LIMIT 5
"""):
    print("  ", r)

print("\n== created_at 里有没有 1970 ==")
c = cur.execute("""
    SELECT COUNT(*) FROM traffic_events
    WHERE substr(CAST(created_at AS TEXT), 1, 4) = '1970'
""").fetchone()[0]
print("created_at 1970 行数 =", c)

print("\n== 是否已有 wall_time 列（新写入路径的修复标志）==")
cols = [r[1] for r in cur.execute("PRAGMA table_info(traffic_events)")]
print("列：", ", ".join(cols))
print("有 wall_time 列 =", "wall_time" in cols)
if "wall_time" in cols:
    w = cur.execute("""
        SELECT COUNT(*) FROM traffic_events
        WHERE substr(CAST(wall_time AS TEXT), 1, 4) = '1970'
    """).fetchone()[0]
    print("wall_time 里 1970 行数 =", w)

con.close()
print("\n[只读] 完成，未修改任何数据。")
