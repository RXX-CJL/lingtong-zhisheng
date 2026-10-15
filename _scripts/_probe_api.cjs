// 决定性测试：在浏览器里直接 import 同一个 api 模块并调用
const PW = 'E:/deepseek-harness/node_modules/.pnpm/playwright@1.61.1/node_modules/playwright';

(async () => {
  const { chromium } = require(PW);
  const b = await chromium.launch({ channel: 'msedge', headless: false, args: ['--start-maximized'] });
  const ctx = await b.newContext({ viewport: null, locale: 'zh-CN' });
  const page = await ctx.newPage();
  const logs = [];
  page.on('console', m => logs.push(`[${m.type()}] ${m.text().slice(0, 260)}`));
  page.on('pageerror', e => logs.push('[pageerror] ' + String(e).slice(0, 260)));

  await page.goto('http://127.0.0.1:5173/live', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(6000);

  const res = await page.evaluate(async () => {
    const out = {};
    try {
      const mod = await import('/src/api/index.js');
      out.modKeys = Object.keys(mod).slice(0, 12);
      out.hasDefault = !!mod.default;
      if (mod.default) {
        out.defaultIsFn = typeof mod.default === 'function' || typeof mod.default.get === 'function';
        try {
          const r = await mod.default.get('/realtime/evidence', { params: { limit: 3 } });
          out.status = r.status;
          out.topKeys = Object.keys(r.data);
          out.dataIsArray = Array.isArray(r.data.data);
          out.total = r.data.total;
          out.firstName = r.data.data && r.data.data[0] ? r.data.data[0].name : null;
        } catch (e2) {
          out.callError = String(e2).slice(0, 260);
        }
      }
    } catch (e) {
      out.importError = String(e).slice(0, 260);
    }
    return out;
  });

  console.log('=== 直接调用 api 模块 ===');
  console.log(JSON.stringify(res, null, 2).slice(0, 1400));
  console.log('\n=== 页面日志 ===');
  logs.slice(-14).forEach(l => console.log('  ' + l));

  console.log('\n>>> 保持 10 秒 <<<');
  await page.waitForTimeout(10000);
  await b.close();
})().catch(e => { console.log('FAILED: ' + String(e).slice(0, 220)); process.exit(1); });
