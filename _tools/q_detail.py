# -*- coding: utf-8 -*-
import sqlite3, json, os
os.chdir(r"E:\output\1\api")
c = sqlite3.connect("zhitong_violations.db"); c.row_factory = sqlite3.Row

print("############ ID=3250（第二次，开了云端复核）############")
d = dict(c.execute("SELECT * FROM traffic_events WHERE id=3250").fetchone())
print("event_id   =", d["event_id"])
print("type/time  =", d["event_type"], d["trigger_time"])
print("state      =", d["state"])
print("ai_conf    =", d["ai_confidence"])
print("ai_explain =", str(d["ai_explanation"])[:300])
print()
j = json.loads(d["ai_judgment"])
print("ai_judgment 顶层键 =", list(j.keys()))
print()
for k in list(j.keys()):
    v = j[k]
    s = json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v
    print("--- %s ---" % k)
    print(s[:700])
    print()

print("############ ID=3249（第一次，没开云端）############")
d2 = dict(c.execute("SELECT * FROM traffic_events WHERE id=3249").fetchone())
print("ai_judgment repr =", repr(d2["ai_judgment"]))
print("ai_conf =", d2["ai_confidence"], "| ai_explain =", repr(d2["ai_explanation"])[:200])
print("rule_judgment =", str(d2["rule_judgment"])[:300])
