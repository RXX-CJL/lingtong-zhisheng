"""查询 DeepSeek 账号余额（只读，不回显完整 Key）

用当前 DSH 实际在用的 Key 调官方余额接口，输出：
  - is_available / 币种 / 总额 / 赠送余额 / 充值余额
这样即可确定"这个 Key 对应哪个账号、还有多少钱"。
"""

import json
import os
import sys
import urllib.request

sys.path.insert(0, r"E:\output\1\api")
os.chdir(r"E:\output\1\api")
import config as C  # noqa: E402

KEY = C.Config.DEEPSEEK_API_KEY or ""
if not KEY:
    print("DEEPSEEK_API_KEY 为空，无法查询")
    sys.exit(1)

print(f"使用 Key 指纹: {KEY[:6]}...{KEY[-4:]}  (len={len(KEY)})")
print("=" * 70)

url = "https://api.deepseek.com/user/balance"
req = urllib.request.Request(url, headers={
    "Authorization": f"Bearer {KEY}",
    "Accept": "application/json",
})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read().decode("utf-8")
        print(f"HTTP {r.status}")
        data = json.loads(body)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        infos = data.get("balance_infos") or []
        for b in infos:
            print("-" * 70)
            print(f"  币种        : {b.get('currency')}")
            print(f"  总余额      : {b.get('total_balance')}")
            print(f"  赠送余额    : {b.get('granted_balance')}")
            print(f"  充值余额    : {b.get('topped_up_balance')}")
        print("-" * 70)
        print("  是否可用    :", data.get("is_available"))
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}: {e.read().decode('utf-8', 'ignore')[:300]}")
except Exception as e:
    print("请求失败:", type(e).__name__, str(e)[:200])
