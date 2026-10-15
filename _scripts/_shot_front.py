"""用 Playwright 打开前端并截图，验证真实渲染（三级证据）"""

import os
import sys

PW = r"E:\deepseek-harness\node_modules\.pnpm\playwright@1.61.1\node_modules\playwright"
OUT_DIR = r"E:\output\_screens"
os.makedirs(OUT_DIR, exist_ok=True)

# 让 node 能 require 到仓库里的 playwright
NODE = r"E:\node.exe"
script = r"""
const { chromium } = require(process.argv[2]);
(async () => {
  const out = process.argv[3];
  const b = await chromium.launch({ headless: true });
  const ctx = await b.newContext({ viewport: { width: 1600, height: 1000 }, locale: 'zh-CN' });
  const page = await ctx.newPage();
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text().slice(0, 140)); });
  page.on('pageerror', e => errors.push('PAGEERROR: ' + String(e).slice(0, 140)));
  const resp = await page.goto('http://127.0.0.1:5173/', { waitUntil: 'networkidle', timeout: 60000 });
  console.log('HTTP_STATUS=' + (resp ? resp.status() : 'null'));
  await page.waitForTimeout(3000);
  const title = await page.title();
  const bodyLen = (await page.evaluate(() => document.body.innerText || '')).length;
  const appHtmlLen = (await page.evaluate(() => {
    const el = document.getElementById('app');
    return el ? el.innerHTML.length : -1;
  }));
  console.log('TITLE=' + title);
  console.log('BODY_TEXT_LEN=' + bodyLen);
  console.log('APP_HTML_LEN=' + appHtmlLen);
  console.log('CONSOLE_ERRORS=' + errors.length);
  for (const e of errors.slice(0, 6)) console.log('  ERR: ' + e);
  await page.screenshot({ path: out + '\\frontend-home.png', fullPage: false });
  console.log('SHOT=' + out + '\\frontend-home.png');
  await b.close();
})().catch(e => { console.log('FAILED: ' + String(e).slice(0, 200)); process.exit(1); });
"""
tmp = os.path.join(os.environ.get("TEMP", "."), "shot_front.py")
# 直接以 node 运行等价脚本更简单：这里改为生成 .cjs 后由 pwsh 调 node
cjs = os.path.join(os.environ.get("TEMP", "."), "shot_front.cjs")
with open(cjs, "w", encoding="utf-8") as f:
    f.write(script)
print("CJS=" + cjs)
print("PW=" + PW)
print("OUT=" + OUT_DIR)
