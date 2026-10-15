# -*- coding: utf-8 -*-
"""只读：验证"新增事件的写入路径已修好"这半句结论。不改任何数据。"""
import sqlite3
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

con = sqlite3.connect("file:E:/output/1/api/zhitong_violations.db?mode=ro", uri=True)
cur = con.cursor()

print("== created_at 按月分布 ==")
for m, n in cur.execute(
        "SELECT substr(created_at,1,7), COUNT(*) FROM traffic_events "
        "GROUP BY 1 ORDER BY 1"):
    print(f"  {m}: {n}")

print("\n== 最近 8 条：新写入路径的 trigger_time 是否已是墙钟 ==")
for tid, tt, ca in cur.execute(
        "SELECT id, trigger_time, created_at FROM traffic_events "
        "ORDER BY id DESC LIMIT 8"):
    flag = "BAD-1970" if str(tt)[:4] == "1970" else "OK"
    print(f"  id={tid}  trigger_time={tt}  created_at={ca}  [{flag}]")

print("\n== 脏数据的 id / 时间范围 ==")
lo = cur.execute(
    "SELECT MIN(id), MIN(created_at) FROM traffic_events "
    "WHERE substr(CAST(trigger_time AS TEXT),1,4)='1970'").fetchone()
hi = cur.execute(
    "SELECT MAX(id), MAX(created_at) FROM traffic_events "
    "WHERE substr(CAST(trigger_time AS TEXT),1,4)='1970'").fetchone()
print("  最早:", lo)
print("  最晚:", hi)

print("\n== 脏数据最晚一条之后，还有没有新增的 1970 行 ==")
n = cur.execute(
    "SELECT COUNT(*) FROM traffic_events WHERE id > ? AND "
    "substr(CAST(trigger_time AS TEXT),1,4)='1970'", (hi[0],)).fetchone()[0]
print("  计数 =", n, "（0 = 新写入路径确实已不再产生 1970）")

con.close()
print("\n[只读] 完成。")
