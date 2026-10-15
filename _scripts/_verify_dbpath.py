"""验证 database.py 路径修复：从不同 cwd 导入，engine 必须指向同一个真库"""

import os
import subprocess
import sys

API = r"E:\output\1\api"
GPU = r"C:\miniconda\envs\zhitong-gpu\python.exe"
TRUTH = os.path.join(API, "zhitong_violations.db")

PROBE = r'''
import os, sys
sys.path.insert(0, r"{api}")
os.chdir(r"{cwd}")
import database as db
print("ENGINE_URL=" + str(db.engine.url))
print("RESOLVED=" + str(db.engine.url.database))
'''.format(api=API, cwd="__CWD__")

print("=" * 78)
print("真库（应始终被指向）:", TRUTH)
print("大小:", os.path.getsize(TRUTH), "字节")
print("=" * 78)

cwds = [API, r"E:\output\1", r"E:\output", os.environ.get("TEMP", "C:\\")]
results = []
for cwd in cwds:
    code = PROBE.replace("__CWD__", cwd)
    p = subprocess.run([GPU, "-c", code], capture_output=True, text=True,
                       encoding="utf-8", errors="ignore", cwd=cwd)
    resolved = ""
    for line in (p.stdout or "").splitlines():
        if line.startswith("RESOLVED="):
            resolved = line.split("=", 1)[1].strip()
    ok = os.path.normcase(os.path.abspath(resolved)) == os.path.normcase(os.path.abspath(TRUTH))
    results.append(ok)
    print(f"  cwd={cwd:32s} -> {resolved}")
    print(f"       {'PASS' if ok else 'FAIL'}  (指向真库={ok})")
    if p.returncode != 0:
        print("       stderr:", (p.stderr or "").strip()[-200:])

print()
print("=" * 78)
print("RESULT:", "PASS - 与启动目录无关，始终指向真库" if all(results)
      else "FAIL - 仍有 cwd 依赖")
sys.exit(0 if all(results) else 1)
