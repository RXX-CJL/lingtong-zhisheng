"""逐个 Key 查余额归属（只读，不回显完整 Key）

目的：确定凭据文件里两个 Key 各属于哪个平台/账号、余额多少，
从而回答"挂件显示的余额是哪个账号"以及"该往哪个账号充值"。
"""

import hashlib
import json
import re
import urllib.error
import urllib.request

CRED = r"C:\Users\ROG\.dsh\.credentials.yaml"

txt = open(CRED, encoding="utf-8", errors="ignore").read()
keys = list(dict.fromkeys(re.findall(r"sk-[A-Za-z0-9_\-]{20,}", txt)))

# 从凭据文件里尝试把 key 名与值对应起来（yaml 结构里通常有 name/kind 字段）
print("凭据文件里出现的 Key：")
for i, k in enumerate(keys, 1):
    print(f"  #{i} len={len(k)} fp={k[:6]}...{k[-4:]} sha12={hashlib.sha256(k.encode()).hexdigest()[:12]}")

# 尝试提取 key 名 -> 值 的邻近关系（取每个 key 前后文里的 name/kind）
print()
print("凭据文件结构片段（key 值已脱敏）：")
lines = txt.splitlines()
for i, ln in enumerate(lines):
    if "sk-" in ln:
        ctx = lines[max(0, i - 4):i + 1]
        for c in ctx:
            cc = re.sub(r"(sk-[A-Za-z0-9_\-]{4})[A-Za-z0-9_\-]+", r"\1***", c).strip()
            if cc:
                print(f"    {cc[:110]}")

ENDPOINTS = [
    ("DeepSeek", "https://api.deepseek.com/user/balance",
     lambda j: (j.get("balance_infos") or [{}])[0].get("total_balance")),
    ("DashScope兼容(阿里)", "https://dashscope.aliyuncs.com/api/v1/user/balance", None),
]

print()
print("=" * 74)
for i, k in enumerate(keys, 1):
    print(f"Key #{i}  {k[:6]}...{k[-4:]}  (sha12={hashlib.sha256(k.encode()).hexdigest()[:12]})")
    for name, url, pick in ENDPOINTS:
        try:
            req = urllib.request.Request(url, headers={
                "Authorization": f"Bearer {k}", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=25) as r:
                body = r.read().decode("utf-8", "ignore")
                print(f"    [{name}] HTTP {r.status}")
                try:
                    j = json.loads(body)
                    print(f"       {json.dumps(j, ensure_ascii=False)[:280]}")
                except Exception:
                    print(f"       {body[:200]}")
        except urllib.error.HTTPError as e:
            print(f"    [{name}] HTTP {e.code}: {e.read().decode('utf-8','ignore')[:120]}")
        except Exception as e:
            print(f"    [{name}] {type(e).__name__}: {str(e)[:100]}")
    print("-" * 74)
