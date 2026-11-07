# -*- coding: utf-8 -*-
import sqlite3, json, os
os.chdir(r"E:\output\1\api")
c = sqlite3.connect("zhitong_violations.db")
c.row_factory = sqlite3.Row

print("=== 精确统计（按 ai_judgment 实际内容分类）===")
rows = c.execute("SELECT id, ai_judgment FROM traffic_events").fetchall()
cat = {"空(NULL/空串)":0, "{}或[]空壳":0, "local_fallback":0, "真云端结果":0, "其他":0}
for r in rows:
    aj = (r[0+1] or "")
    s = aj.strip()
    if not s: cat["空(NULL/空串)"] += 1
    elif s in ("{}","[]","null"): cat["{}或[]空壳"] += 1
    elif "local_fallback" in s: cat["local_fallback"] += 1
    elif '"final"' in s or "doubao" in s.lower(): cat["真云端结果"] += 1
    else: cat["其他"] += 1
for k,v in cat.items(): print("  %-16s %d" % (k, v))
print("  合计", sum(cat.values()))

print()
print("=== 今天(2026-11-01)产生的事件 ===")
today = c.execute("SELECT id,trigger_time,event_type,state,ai_confidence,ai_explanation,ai_judgment,event_video_path,key_frames FROM traffic_events WHERE trigger_time LIKE '2026-11-01%' ORDER BY id").fetchall()
print("今日事件数 =", len(today))
for r in today:
    d = dict(r)
    aj = d.get("ai_judgment") or ""
    print("  ID=%s | %s | %s | state=%s | ai_conf=%s | ai_len=%d" % (
        d["id"], str(d["trigger_time"])[11:19], d["event_type"], d["state"], d["ai_confidence"], len(aj)))

print()
print("=== 关键帧/视频产出 ===")
for r in today:
    d = dict(r)
    try: kf = len(json.loads(d["key_frames"] or "[]"))
    except: kf = -1
    print("  ID=%s key_frames=%s video=%s" % (d["id"], kf, d["event_video_path"]))
