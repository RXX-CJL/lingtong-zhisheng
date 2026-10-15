"""小程序编译前静态验证：模拟微信开发者工具的关键检查

检查项：
  1. app.json 里每个页面是否 4 文件齐全
  2. 页面 json 是否存在（微信要求每个页面有 .json）
  3. require/import 的相对路径是否可解析
  4. tabBar 的 pagePath 是否都在 pages 列表里
  5. app.js 的 globalData 与 utils/api.js 读取的字段是否一致
"""

import io
import json
import os
import re

ROOT = r"E:\output\1\wechat-miniprogram\src"
out = []
ok_all = True


def mark(cond):
    return "PASS" if cond else "FAIL"


# ---- 1) 读 app.json ----
app_json_path = os.path.join(ROOT, "app.json")
if not os.path.exists(app_json_path):
    out.append("FAIL app.json 不存在")
    raise SystemExit(1)
app = json.load(io.open(app_json_path, encoding="utf-8"))
pages = app.get("pages", [])
out.append(f"app.json 声明 {len(pages)} 个页面")

# ---- 2) 每页 4 文件 ----
out.append("")
out.append("=== 页面文件完整性 ===")
for p in pages:
    missing = []
    for ext in (".js", ".wxml", ".json", ".wxss"):
        if not os.path.exists(os.path.join(ROOT, p + ext)):
            missing.append(ext)
    # .json 必需；.wxss 可选；.js/.wxml 必需
    hard_missing = [m for m in missing if m in (".js", ".wxml", ".json")]
    if hard_missing:
        ok_all = False
    out.append(f"  [{mark(not hard_missing)}] {p:28s} 缺: {missing or '无'}")

# ---- 3) tabBar pagePath 是否都在 pages 中 ----
out.append("")
out.append("=== tabBar 一致性 ===")
for item in (app.get("tabBar", {}) or {}).get("list", []):
    pp = item.get("pagePath")
    good = pp in pages
    if not good:
        ok_all = False
    icon_note = ""
    if item.get("iconPath"):
        ip = os.path.join(ROOT, item["iconPath"])
        exists = os.path.exists(ip)
        size = os.path.getsize(ip) if exists else 0
        icon_note = f"  icon={item['iconPath']}({size}B{' 占位符?' if size < 500 else ''})"
        if not exists:
            ok_all = False
    out.append(f"  [{mark(good)}] {pp:28s} {item.get('text','')}{icon_note}")

# ---- 4) require/import 相对路径可解析 ----
out.append("")
out.append("=== 模块引用可解析性 ===")
bad_refs = 0
for dirpath, _dirs, files in os.walk(ROOT):
    for fn in files:
        if not fn.endswith(".js"):
            continue
        fp = os.path.join(dirpath, fn)
        try:
            content = io.open(fp, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        for m in re.finditer(r"""(?:require|import)\s*\(?\s*['"]([^'"]+)['"]""", content):
            ref = m.group(1)
            if not ref.startswith("."):
                continue
            base = os.path.normpath(os.path.join(dirpath, ref))
            cands = [base, base + ".js", os.path.join(base, "index.js")]
            if not any(os.path.exists(c) for c in cands):
                bad_refs += 1
                ok_all = False
                out.append(f"  [FAIL] {os.path.relpath(fp, ROOT)} -> {ref}  (解析不到)")
if bad_refs == 0:
    out.append("  [PASS] 所有相对引用均可解析")

# ---- 5) globalData 字段一致性 ----
out.append("")
out.append("=== globalData 字段一致性（易踩坑）===")
app_js = io.open(os.path.join(ROOT, "app.js"), encoding="utf-8", errors="replace").read()
api_js_path = os.path.join(ROOT, "utils", "api.js")
api_js = io.open(api_js_path, encoding="utf-8", errors="replace").read() if os.path.exists(api_js_path) else ""

# app.js 里定义的 globalData 键（用括号配对提取对象体，避免被注释里的 } 干扰）
defined = set()
if "globalData" in app_js:
    tail = app_js.split("globalData", 1)[1]
    depth = 0
    body_chars = []
    started = False
    for ch in tail:
        if ch == "{":
            depth += 1
            started = True
            continue
        if ch == "}":
            depth -= 1
            if depth <= 0:
                break
        if started:
            body_chars.append(ch)
    body = "".join(body_chars)
    # 去掉注释行，再取 "键:" 形式
    body_clean = re.sub(r"//[^\n]*", "", body)
    defined = set(re.findall(r"(\w+)\s*:", body_clean))
out.append(f"  app.js globalData 定义的键: {sorted(defined)}")

used = set(re.findall(r"app\.globalData\.(\w+)", api_js))
out.append(f"  utils/api.js 读取的键:      {sorted(used)}")
missing_keys = used - defined
if missing_keys:
    ok_all = False
    out.append(f"  [FAIL] api.js 读取了 app.js 未定义的键: {sorted(missing_keys)}")
    out.append("         -> 运行时会得到 undefined，请求 URL 会变成 'undefined/api/...'")
else:
    out.append("  [PASS] 键一致")

# 顺带检查页面直接用到的 globalData 键
page_used = set()
for dirpath, _d, files in os.walk(os.path.join(ROOT, "pages")):
    for fn in files:
        if fn.endswith(".js"):
            c = io.open(os.path.join(dirpath, fn), encoding="utf-8", errors="replace").read()
            page_used |= set(re.findall(r"app\.globalData\.(\w+)", c))
if page_used:
    miss2 = page_used - defined
    out.append(f"  页面读取的键:               {sorted(page_used)}")
    if miss2:
        ok_all = False
        out.append(f"  [FAIL] 页面读取了未定义的键: {sorted(miss2)}")

out.append("")
out.append("=" * 66)
out.append(f"总体: {'静态检查全部通过 ✅' if ok_all else '存在 FAIL 项 ❌'}")
io.open(r"E:\output\_miniapp_compile_check.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK")
