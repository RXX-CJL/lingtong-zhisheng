"""只读核查 2：视频路径真伪 + API 实际使用的数据库"""

import os
import sqlite3
import glob

API = r"E:\output\1\api"
print("=" * 76)
print("1) traffic_events 里的 event_video_path 到底指向什么")
print("=" * 76)
con = sqlite3.connect(os.path.join(API, "zhitong_violations.db"))
for eid, vp in con.execute(
        "SELECT event_id, COALESCE(event_video_path,'') FROM traffic_events ORDER BY id DESC LIMIT 5"):
    exists = os.path.exists(vp) if vp else False
    print(f"  {eid[:24]:26s} exists={exists}")
    print(f"     -> {vp}")
con.close()

print()
print("=" * 76)
print("2) 项目里所有 SQLite 库（找 API 真正在用的那个）")
print("=" * 76)
root = r"E:\output\1"
dbs = []
for p in glob.glob(os.path.join(root, "**", "*.db"), recursive=True):
    if any(s in p for s in (".venv", "node_modules", "__pycache__")):
        continue
    size = os.path.getsize(p)
    dbs.append((size, p))
for size, p in sorted(dbs, reverse=True):
    tables = []
    try:
        c = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
        tables = [r[0] for r in c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        counts = {}
        for t in tables:
            try:
                counts[t] = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            except Exception:
                counts[t] = "?"
        c.close()
    except Exception as e:
        counts = {"ERR": str(e)[:50]}
    print(f"\n  {p}")
    print(f"     大小 {size/1024:.0f} KB   表: {tables if tables else counts}")

print()
print("=" * 76)
print("3) config.py 里 DB_PATH 的解析结果")
print("=" * 76)
import sys
sys.path.insert(0, API)
os.chdir(API)
import config as C
print("  Config.DB_PATH =", getattr(C.Config, "DB_PATH", "(未定义)"))
print("  该文件存在:", os.path.exists(getattr(C.Config, "DB_PATH", "")))
