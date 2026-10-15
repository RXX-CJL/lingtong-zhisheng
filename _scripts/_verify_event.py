"""验证新事件的视频文件是否真的落盘，并通过接口/前端路径验证可访问"""

import json
import os
import sqlite3
import urllib.request

DB = r"E:\output\1\api\zhitong_violations.db"
BASE = "http://127.0.0.1:8001"
NEW_EVENT = "evt_1790880613866_6_5a903d"

print("=" * 78)
print("1) 数据库里最新事件")
print("=" * 78)
con = sqlite3.connect(f"file:{DB.replace(chr(92), '/')}?mode=ro", uri=True)
rows = con.execute(
    "SELECT event_id, event_type, state, trigger_time, event_video_path "
    "FROM traffic_events ORDER BY id DESC LIMIT 4").fetchall()
for eid, et, st, tt, vp in rows:
    exists = os.path.exists(vp) if vp else False
    size = f"{os.path.getsize(vp)/1024:.0f} KB" if exists else "-"
    print(f"  {eid[:32]:34s} {et:10s} {st:12s} {str(tt)[:19]}")
    print(f"      video: {'存在 ' + size if exists else ('路径有但文件不存在!' if vp else '无')}")
    if vp:
        print(f"      -> {vp}")
con.close()

print()
print("=" * 78)
print("2) 事件视频目录（含日期子目录）")
print("=" * 78)
root = r"E:\output\1\api\output\event_videos"
for dirpath, dirnames, filenames in os.walk(root):
    mp4 = [f for f in filenames if f.endswith(".mp4")]
    if mp4:
        print(f"  {dirpath}")
        for f in sorted(mp4)[-8:]:
            p = os.path.join(dirpath, f)
            print(f"     {f}   {os.path.getsize(p)/1024:.0f} KB   {os.path.getmtime(p):.0f}")

print()
print("=" * 78)
print("3) 通过后端接口访问该事件视频（前端走的就是这条）")
print("=" * 78)
for path in (f"/api/realtime/events/{NEW_EVENT}",
             f"/api/realtime/events/{NEW_EVENT}/video",
             f"/api/realtime/events/{NEW_EVENT}/frames",
             f"/api/realtime/events/{NEW_EVENT}/replay"):
    try:
        req = urllib.request.Request(BASE + path, method="GET")
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read()
            ctype = r.headers.get("Content-Type", "?")
            print(f"  [{r.status}] {path}")
            print(f"        content-type={ctype}  {len(body)} 字节")
            if "json" in ctype:
                try:
                    j = json.loads(body.decode("utf-8", "ignore"))
                    print(f"        {json.dumps(j, ensure_ascii=False)[:200]}")
                except Exception:
                    pass
    except Exception as e:
        print(f"  [ERR] {path}  {type(e).__name__}: {str(e)[:90]}")
