"""验证事件中心前端链路：接口返回 + 数据新鲜度 + 证据完整度"""

import io
import json
import sqlite3
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8001"
DB = r"E:\output\1\api\zhitong_violations.db"
out = []


def get(path, timeout=30):
    try:
        with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8", "ignore"))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore")[:200]
    except Exception as e:
        return None, f"{type(e).__name__}: {str(e)[:110]}"


con = sqlite3.connect(DB)
cur = con.cursor()
total = cur.execute("SELECT COUNT(*) FROM traffic_events").fetchone()[0]
has_chain = cur.execute(
    "SELECT COUNT(*) FROM traffic_events WHERE evidence_chain IS NOT NULL "
    "AND evidence_chain != ''").fetchone()[0]
has_video = cur.execute(
    "SELECT COUNT(*) FROM traffic_events WHERE event_video_path IS NOT NULL "
    "AND event_video_path != ''").fetchone()[0]
has_kf = cur.execute(
    "SELECT COUNT(*) FROM traffic_events WHERE key_frames IS NOT NULL "
    "AND key_frames NOT IN ('', '[]')").fetchone()[0]
con.close()

out.append("=== 数据库现状 ===")
out.append(f"  事件总数      {total}")
out.append(f"  有证据链      {has_chain}  ({has_chain/max(1,total)*100:.0f}%)")
out.append(f"  有事件视频    {has_video}  ({has_video/max(1,total)*100:.0f}%)")
out.append(f"  有关键帧      {has_kf}  ({has_kf/max(1,total)*100:.0f}%)")

out.append("")
out.append("=== 接口 /api/realtime/events ===")
st, js = get("/api/realtime/events?limit=5")
if isinstance(js, dict):
    d = js.get("data")
    rows = d if isinstance(d, list) else (d or {}).get("events") or (d or {}).get("items") or []
    out.append(f"  HTTP {st}  顶层键={sorted(js.keys())}  返回 {len(rows)} 条")
    for x in rows[:5]:
        if isinstance(x, dict):
            out.append(f"    {str(x.get('event_id'))[:32]:34s} {str(x.get('event_type')):16s} "
                       f"{str(x.get('state')):14s} video={'有' if x.get('event_video_path') else '无'} "
                       f"chain={'有' if x.get('evidence_chain') else '无'}")
else:
    out.append(f"  HTTP {st}: {str(js)[:200]}")

out.append("")
out.append("=== 接口 /api/realtime/events/active ===")
st, js = get("/api/realtime/events/active")
if isinstance(js, dict):
    d = js.get("data")
    rows = d if isinstance(d, list) else (d or {}).get("events") or []
    out.append(f"  HTTP {st}  返回 {len(rows)} 条活跃事件")

out.append("")
out.append("=== 取一个最新事件的详情 ===")
con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()
cur.execute("SELECT event_id FROM traffic_events ORDER BY id DESC LIMIT 1")
row = cur.fetchone()
con.close()
if row:
    eid = row["event_id"]
    st, js = get(f"/api/realtime/events/{eid}")
    if isinstance(js, dict):
        d = js.get("data") or js
        out.append(f"  event_id={eid}")
        out.append(f"  HTTP {st}  键: {sorted(d.keys())[:16] if isinstance(d, dict) else type(d)}")
        if isinstance(d, dict):
            out.append(f"    type={d.get('event_type')} state={d.get('state')} "
                       f"conf={d.get('ai_confidence')}")
            ec = d.get("evidence_chain")
            if ec:
                try:
                    ecj = json.loads(ec) if isinstance(ec, str) else ec
                    out.append(f"    证据链字段: {sorted(ecj.keys())[:16]}")
                    out.append(f"      plate={ecj.get('plate_number')!r} "
                               f"vehicle_id={ecj.get('vehicle_id')} "
                               f"key_frames={len(ecj.get('key_frames') or [])} "
                               f"trajectory={len(ecj.get('trajectory') or [])} "
                               f"final_status={ecj.get('final_status')}")
                except Exception as e:
                    out.append(f"    证据链解析失败: {e}")
            else:
                out.append("    该事件无证据链")
    else:
        out.append(f"  HTTP {st}: {str(js)[:180]}")

io.open(r"E:\output\_events_frontend.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
