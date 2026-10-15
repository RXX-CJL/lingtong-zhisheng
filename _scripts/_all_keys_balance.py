"""枚举 DSH 相关位置里所有 DeepSeek 风格 Key，并逐个查余额

目的：如果存在两把 key 属于不同账号，就能解释"充了 100 但余额没涨"。
只读，不回显完整 key。
"""

import glob
import hashlib
import json
import os
import re
import urllib.error
import urllib.request

SEARCH_ROOTS = [
    r"C:\Users\ROG\.dsh",
    r"C:\Users\ROG\.dsh\profiles\desktop\.dsh",
    r"C:\Users\ROG\.dsh\profiles\web\.dsh",
    r"E:\output\1\api",
]
# 只扫小体积的配置/凭据类文件，避免陷入 node_modules
SKIP = ("node_modules", "dist", "build", "__pycache__", ".git", "assets", "models")
EXTS = (".yaml", ".yml", ".json", ".env", ".txt", ".ini", ".cfg", ".credentials")

found = {}
for root in SEARCH_ROOTS:
    if not os.path.isdir(root):
        continue
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP]
        # 限制深度，避免全盘遍历
        depth = dirpath[len(root):].count(os.sep)
        if depth > 2:
            dirnames[:] = []
            continue
        for fn in filenames:
            if not fn.lower().endswith(EXTS):
                continue
            p = os.path.join(dirpath, fn)
            try:
                if os.path.getsize(p) > 2 * 1024 * 1024:
                    continue
                txt = open(p, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            for m in re.findall(r"sk-[A-Za-z0-9_\-]{20,}", txt):
                found.setdefault(m, set()).add(p)

print("=" * 78)
print(f"扫到 {len(found)} 把不同的 sk- 风格 Key")
print("=" * 78)
for k, paths in found.items():
    print(f"\n  {k[:6]}...{k[-4:]}  sha12={hashlib.sha256(k.encode()).hexdigest()[:12]}")
    for p in sorted(paths):
        print(f"      出处: {p}")

print()
print("=" * 78)
print("逐个查 DeepSeek 余额")
print("=" * 78)
for k, paths in found.items():
    fp = f"{k[:6]}...{k[-4:]}"
    try:
        req = urllib.request.Request(
            "https://api.deepseek.com/user/balance",
            headers={"Authorization": f"Bearer {k}", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=25) as r:
            j = json.loads(r.read().decode("utf-8", "ignore"))
            infos = (j.get("balance_infos") or [{}])[0]
            print(f"  [OK]   {fp:20s} 余额={infos.get('total_balance')} {infos.get('currency')} "
                  f"(充值 {infos.get('topped_up_balance')} / 赠送 {infos.get('granted_balance')})")
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", "ignore")[:80]
        print(f"  [ERR]  {fp:20s} HTTP {e.code} {msg}")
    except Exception as e:
        print(f"  [ERR]  {fp:20s} {type(e).__name__}")

print()
print("=" * 78)
print("参照值：充值前 = 33.11；若某把 key 现在约 133.x，则 100 元充到了那个账号")
print("=" * 78)
