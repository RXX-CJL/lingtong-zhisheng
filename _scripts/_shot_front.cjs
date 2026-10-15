// 用 Playwright 打开前端并截图（验证真实渲染）
// 运行: E:\node.exe E:\output\_shot_front.cjs
const PW = 'E:/deepseek-harness/node_modules/.pnpm/playwright@1.61.1/node_modules/playwright';
const OUT = 'E:/output/_screens/frontend-home.png';

(async () => {
  const { chromium } = require(PW);
  const b = await chromium.launch({ headless: true });
  const ctx = await b.newContext({ viewport: { width: 1600, height: 1000 }, locale: 'zh-CN' });
  const page = await ctx.newPage();

  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text().slice(0, 160)); });
  page.on('pageerror', e => errors.push('PAGEERROR: ' + String(e).slice(0, 160)));

  const resp = await page.goto('http://127.0.0.1:5173/', { waitUntil: 'networkidle', timeout: 60000 });
  console.log('HTTP_STATUS=' + (resp ? resp.status() : 'null'));
  await page.waitForTimeout(3000);

  const title = await page.title();
  const bodyLen = await page.evaluate(() => (document.body.innerText || '').length);
  const appHtmlLen = await page.evaluate(() => {
    const el = document.getElementById('app');
    return el ? el.innerHTML.length : -1;
  });
  const route = await page.evaluate(() => location.hash || location.pathname);

  console.log('TITLE=' + title);
  console.log('ROUTE=' + route);
  console.log('BODY_TEXT_LEN=' + bodyLen);
  console.log('APP_HTML_LEN=' + appHtmlLen);
  console.log('CONSOLE_ERRORS=' + errors.length);
  errors.slice(0, 8).forEach(e => console.log('  ERR: ' + e));

  await page.screenshot({ path: OUT });
  console.log('SHOT=' + OUT);
  await b.close();
})().catch(e => { console.log('FAILED: ' + String(e).slice(0, 240)); process.exit(1); });
