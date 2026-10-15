"""端到端：模拟两个新页面的完整请求序列

bind 页面流程：/bind/status -> 绑定 -> /bind/status（刷新）-> 解绑
notifications 页面流程：/notifications -> /notifications/read -> 仅未读
"""

import io
import json
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8001"
out = []


def call(method, path, body=None, headers=None, timeout=30):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8", "ignore"))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore")[:200]
    except Exception as e:
        return None, f"{type(e).__name__}: {str(e)[:110]}"


# 登录
st, js = call("POST", "/api/wx/login", {"code": "round13_e2e"})
openid = js["data"]["openid"]
H = {"X-Openid": openid}
out.append(f"登录 openid={openid}")

# ---------- bind 页面流程 ----------
out.append("")
out.append("=" * 70)
out.append("【bind 页面】流程")
out.append("=" * 70)
st, js = call("GET", "/api/wx/bind/status", None, H)
d = js.get("data", {}) if isinstance(js, dict) else {}
out.append(f"1. onLoad /bind/status     HTTP {st}  has_binding={d.get('has_binding')} "
           f"建议={len(d.get('suggest_plates') or [])} my={len(d.get('my_vehicles') or [])}")
sug = (d.get("suggest_plates") or [{}])[0].get("plate_number")

# 一键绑定（模拟点击建议车牌）
enc = urllib.parse.quote(sug) if sug else ""
st, js = call("POST", f"/api/wx/vehicles/bind-by-suggest?plate_number={enc}", None, H)
out.append(f"2. 点击建议车牌 {sug}    HTTP {st}  {json.dumps(js, ensure_ascii=False)[:110] if isinstance(js,dict) else js}")

# 刷新
st, js = call("GET", "/api/wx/bind/status", None, H)
d = js.get("data", {}) if isinstance(js, dict) else {}
out.append(f"3. 刷新 /bind/status       HTTP {st}  has_binding={d.get('has_binding')} "
           f"my={[x['plate_number'] for x in (d.get('my_vehicles') or [])]}")

# 未绑定车牌（手输路径，应 400 拒绝）
st, js = call("POST", "/api/wx/vehicles/bind-by-suggest?plate_number=%E4%BA%AC99999", None, H)
out.append(f"4. 绑定不存在的车牌 京99999 HTTP {st}  {str(js)[:110]}")

# 手动绑定（通用接口，允许）
st, js = call("POST", "/api/wx/vehicles/bind", {"plate_number": "测A12345"}, H)
out.append(f"5. 手动绑定 测A12345      HTTP {st}  {json.dumps(js, ensure_ascii=False)[:90] if isinstance(js,dict) else js}")

# 解绑
st, js = call("POST", "/api/wx/vehicles/unbind", {"plate_number": "测A12345"}, H)
out.append(f"6. 解绑 测A12345          HTTP {st}  {json.dumps(js, ensure_ascii=False)[:90] if isinstance(js,dict) else js}")

# ---------- notifications 页面流程 ----------
out.append("")
out.append("=" * 70)
out.append("【notifications 页面】流程")
out.append("=" * 70)
st, js = call("GET", "/api/wx/notifications", None, H)
before = len(js.get("data") or []) if isinstance(js, dict) else 0
out.append(f"1. onLoad /notifications   HTTP {st}  条数={before}")

# 造一条通知（用 notify-test 给已绑定车牌发）
st, js = call("POST", f"/api/wx/notify-test?plate_number={enc}", None, H)
out.append(f"2. 触发一条通知           HTTP {st}  {json.dumps(js, ensure_ascii=False)[:130] if isinstance(js,dict) else js}")

st, js = call("GET", "/api/wx/notifications", None, H)
rows = js.get("data") or [] if isinstance(js, dict) else []
unread = [r for r in rows if not r.get("is_read")]
out.append(f"3. 再查 /notifications     HTTP {st}  共 {len(rows)} 条，未读 {len(unread)} 条")
for r in rows[:3]:
    out.append(f"     #{r.get('id')} {str(r.get('title'))[:20]} plate={r.get('plate_number')} "
               f"is_read={r.get('is_read')} pushed={r.get('pushed')}")

# 标记单条已读
if rows:
    nid = rows[0].get("id")
    st, js = call("POST", "/api/wx/notifications/read", {"notification_id": nid}, H)
    out.append(f"4. 标记 #{nid} 已读        HTTP {st}  {json.dumps(js, ensure_ascii=False)[:90] if isinstance(js,dict) else js}")

# 只看未读
st, js = call("GET", "/api/wx/notifications?only_unread=true", None, H)
out.append(f"5. 只看未读               HTTP {st}  条数={len(js.get('data') or []) if isinstance(js,dict) else '?'}")

# 全部已读
st, js = call("POST", "/api/wx/notifications/read", {"all_read": True}, H)
out.append(f"6. 全部标记已读           HTTP {st}  {json.dumps(js, ensure_ascii=False)[:90] if isinstance(js,dict) else js}")
st, js = call("GET", "/api/wx/notifications?only_unread=true", None, H)
out.append(f"7. 确认未读清零           HTTP {st}  条数={len(js.get('data') or []) if isinstance(js,dict) else '?'}")

# 首页未读数同步（overview 的 unread 应变化）
st, js = call("GET", "/api/wx/overview", None, H)
out.append(f"8. /overview unread       HTTP {st}  unread={(js.get('data') or {}).get('unread') if isinstance(js,dict) else '?'}")

io.open(r"E:\output\_round13_e2e.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
