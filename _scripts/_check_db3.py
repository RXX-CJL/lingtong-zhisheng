"""只读核查 3：数据库路径一致性 + 各库真实内容"""

import os
import sqlite3

CANDS = [
    r"E:\output\1\zhitong_violations.db",
    r"E:\output\1\api\zhitong_violations.db",
    r"E:\output\1\api\zhitong.db",
]

for p in CANDS:
    print("=" * 74)
    if not os.path.exists(p):
        print(f"  {p}\n    不存在")
        continue
    print(f"  {p}")
    print(f"    大小 {os.path.getsize(p)} 字节")
    try:
        c = sqlite3.connect("file:" + p.replace("\\", "/") + "?mode=ro", uri=True)
        tables = [r[0] for r in c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        if not tables:
            print("    表: (无)")
        for t in tables:
            try:
                n = c.execute("SELECT COUNT(*) FROM " + t).fetchone()[0]
                print(f"      {t:24s} {n} 行")
            except Exception as e:
                print(f"      {t:24s} ERR {str(e)[:40]}")
        c.close()
    except Exception as e:
        print("    打开失败:", e)

print()
print("=" * 74)
print("  database.py 如何取路径")
print("=" * 74)
src = os.path.join(r"E:\output\1\api", "database.py")
if os.path.exists(src):
    with open(src, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if any(k in line for k in ("DB_PATH", "create_engine", "sqlite:///", "Config.")):
                print(f"    L{i}: {line.rstrip()[:100]}")
