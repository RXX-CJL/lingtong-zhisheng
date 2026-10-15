// 深挖前端 404 的具体 URL + 交通事件在前端是否有入口
const PW = 'E:/deepseek-harness/node_modules/.pnpm/playwright@1.61.1/node_modules/playwright';

(async () => {
  const { chromium } = require(PW);
  const b = await chromium.launch({ headless: true });
  const ctx = await b.newContext({ viewport: { width: 1600, height: 1000 }, locale: 'zh-CN' });
  const page = await ctx.newPage();

  const bad = [];
  page.on('response', r => {
    if (r.status() >= 400) bad.push(`${r.status()} ${r.url()}`);
  });

  await page.goto('http://127.0.0.1:5173/', { waitUntil: 'networkidle', timeout: 40000 });
  await page.waitForTimeout(3000);
  console.log('=== 4xx/5xx 请求明细 ===');
  [...new Set(bad)].slice(0, 15).forEach(u => console.log('   ' + u));

  console.log();
  console.log('=== 前端路由表（从 src 里找路由定义）===');
  const routes = await page.evaluate(async () => {
    try {
      const r = await fetch('/src/router/index.js');
      const t = await r.text();
      return t.slice(0, 1500);
    } catch (e) { return 'ERR ' + e; }
  });
  console.log(routes);

  console.log();
  console.log('=== 点“违规管理”菜单后页面变化 ===');
  try {
    await page.click('text=违规管理', { timeout: 8000 });
    await page.waitForTimeout(2500);
    const url = page.url();
    const text = await page.evaluate(() => document.body.innerText || '');
    console.log('   URL=' + url);
    console.log('   文本长度=' + text.length);
    console.log('   片段: ' + text.slice(0, 300).replace(/\n+/g, ' | '));
    await page.screenshot({ path: 'E:/output/_screens/front-violations.png' });
    console.log('   截图: E:/output/_screens/front-violations.png');
  } catch (e) {
    console.log('   点击失败: ' + String(e).slice(0, 120));
  }

  await b.close();
})().catch(e => { console.log('FAILED: ' + String(e).slice(0, 200)); process.exit(1); });
