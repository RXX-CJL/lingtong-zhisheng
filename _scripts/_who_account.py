"""提取 DSH 凭据里的账号身份线索（找出 sk-b60 属于哪个账号）

只读。凭据文件里的 token 疑似 DeepSeek 平台登录令牌（JWT 或自定义体），
尝试解码其 payload 以找出 account / email / userId 等线索。
"""

import base64
import json
import re

CRED = r"C:\Users\ROG\.dsh\.credentials.yaml"
txt = open(CRED, encoding="utf-8", errors="ignore").read()

print("=" * 76)
print("1) 凭据文件整体结构（脱敏）")
print("=" * 76)
out = re.sub(r"(sk-[A-Za-z0-9_\-]{4})[A-Za-z0-9_\-]+", r"\1***", txt)
out = re.sub(r"(token:\s*)(\S{6})\S+", r"\1\2***", out)
for i, ln in enumerate(out.splitlines(), 1):
    if ln.strip():
        print(f"  {i:3d}: {ln[:110]}")

print()
print("=" * 76)
print("2) 尝试解码 token（找 account / email / userId）")
print("=" * 76)
tokens = re.findall(r"token:\s*([A-Za-z0-9+/=_\-\.]{16,})", txt)
print(f"  发现 {len(tokens)} 个 token")


def b64pad(s):
    s = s.replace("-", "+").replace("_", "/")
    return s + "=" * (-len(s) % 4)


for idx, t in enumerate(dict.fromkeys(tokens), 1):
    print(f"\n  token #{idx} len={len(t)} 头部={t[:12]}...")
    # JWT 形式
    if t.count(".") == 2:
        for part_name, part in zip(("header", "payload", "sig"), t.split(".")):
            if part_name == "sig":
                continue
            try:
                dec = base64.b64decode(b64pad(part)).decode("utf-8", "ignore")
                print(f"    [{part_name}] {dec[:400]}")
            except Exception as e:
                print(f"    [{part_name}] 解码失败 {e}")
    else:
        raw = None
        try:
            raw = base64.b64decode(b64pad(t)).decode("utf-8", "ignore")
        except Exception:
            raw = base64.b64decode(b64pad(t)).decode("latin-1", "ignore")
        printable = sum(1 for c in raw if 32 <= ord(c) < 127)
        print(f"    解码后可见字符占比: {printable}/{len(raw)}")
        print(f"    内容片段: {raw[:300]!r}")

print()
print("=" * 76)
print("3) 全文件里出现的账号类线索")
print("=" * 76)
for pat, label in [(r"[\w\.\-]+@[\w\.\-]+", "邮箱"),
                   (r'"(?:account|user|uid|userId|accountId)"\s*:\s*"?[\w\-]+', "账号字段"),
                   (r"platform\.deepseek\.com[^\s\"']*", "platform 链接")]:
    hits = list(dict.fromkeys(re.findall(pat, txt, re.I)))
    print(f"  {label}: {hits if hits else '(无)'}")
