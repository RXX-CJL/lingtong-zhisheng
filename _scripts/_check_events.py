"""只读核查：事件状态分布 / 事件视频产出 / 数据库实况"""

import os
import sqlite3

API = r"E:\output\1\api"
DB = os.path.join(API, "zhitong_violations.db")
VID_DIR = os.path.join(API, "output", "event_videos")

print("=" * 74)
print("1) 数据库实况")
print("=" * 74)
con = sqlite3.connect(DB)
cur = con.cursor()
for t in ("violations", "traffic_events", "appeals", "users"):
    try:
        n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t:16s} {n} 行")
    except Exception as e:
        print(f"  {t:16s} ERR {e}")

try:
    print("  traffic_events 状态分布:")
    for state, n in cur.execute(
            "SELECT state, COUNT(*) FROM traffic_events GROUP BY state ORDER BY 2 DESC"):
        print(f"     {state:16s} x{n}")
    withv = cur.execute(
        "SELECT COUNT(*) FROM traffic_events "
        "WHERE event_video_path IS NOT NULL AND event_video_path LIKE '%.mp4'").fetchone()[0]
    print(f"  有 .mp4 事件视频的: {withv}")
    print("  最近 5 条事件:")
    for row in cur.execute(
            "SELECT event_id, event_type, state, created_at, COALESCE(event_video_path,'') "
            "FROM traffic_events ORDER BY id DESC LIMIT 5"):
        eid, etype, state, cat, vp = row
        print(f"     {eid[:22]:24s} {etype:12s} {state:12s} {str(cat)[:19]:20s} video={'YES' if vp else 'no'}")
except Exception as e:
    print("  事件表查询失败:", e)
con.close()

print()
print("=" * 74)
print("2) 事件视频目录实况")
print("=" * 74)
if os.path.isdir(VID_DIR):
    files = [f for f in os.listdir(VID_DIR) if os.path.isfile(os.path.join(VID_DIR, f))]
    print(f"  目录: {VID_DIR}")
    print(f"  文件数: {len(files)}")
    for f in files[:10]:
        p = os.path.join(VID_DIR, f)
        print(f"     {f}  {os.path.getsize(p)/1024:.1f} KB")
    if not files:
        print("     (空)  -> 印证交接报告：尚无真实事件视频产出")
else:
    print(f"  目录不存在: {VID_DIR}")

print()
print("=" * 74)
print("3) 结论提示")
print("=" * 74)
print("  若存在 state=pending_ai 的事件且无 .mp4 -> 事件闭环在'录制/取视频'环节未完成")
print("  若存在 state=confirmed 且有 .mp4        -> 闭环曾真实跑通")
