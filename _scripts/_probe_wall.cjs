// 在浏览器上下文里直接复现 loadEvidence 的逻辑，定位异常
const PW = 'E:/deepseek-harness/node_modules/.pnpm/playwright@1.61.1/node_modules/playwright';

(async () => {
  const { chromium } = require(PW);
  const b = await chromium.launch({ channel: 'msedge', headless: false, args: ['--start-maximized'] });
  const ctx = await b.newContext({ viewport: null, locale: 'zh-CN' });
  const page = await ctx.newPage();
  const logs = [];
  page.on('console', m => logs.push(`[${m.type()}] ${m.text().slice(0, 220)}`));
  page.on('pageerror', e => logs.push('[pageerror] ' + String(e).slice(0, 220)));

  await page.goto('http://127.0.0.1:5173/live', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(6000);

  const probe = await page.evaluate(async () => {
    const out = {};
    try {
      const r = await fetch('/api/realtime/evidence?limit=5');
      out.fetchStatus = r.status;
      const j = await r.json();
      out.keys = Object.keys(j);
      out.dataIsArray = Array.isArray(j.data);
      out.total = j.total;
      out.firstItem = j.data && j.data[0] ? JSON.stringify(j.data[0]) : null;
      // 测图片能否加载
      if (j.data && j.data[0]) {
        const img = new Image();
        const p = new Promise(res => {
          img.onload = () => res({ ok: true, w: img.naturalWidth, h: img.naturalHeight });
          img.onerror = () => res({ ok: false });
          setTimeout(() => res({ ok: false, timeout: true }), 8000);
        });
        img.src = j.data[0].url;
        out.imgLoad = await p;
        out.imgSrc = j.data[0].url;
      }
    } catch (e) {
      out.error = String(e).slice(0, 200);
    }
    return out;
  });

  console.log('=== 浏览器内 fetch 探测 ===');
  console.log(JSON.stringify(probe, null, 2).slice(0, 1200));
  console.log('\n=== 页面日志（最后 12 条）===');
  logs.slice(-12).forEach(l => console.log('  ' + l));

  console.log('\n>>> 保持 10 秒 <<<');
  await page.waitForTimeout(10000);
  await b.close();
})().catch(e => { console.log('FAILED: ' + String(e).slice(0, 220)); process.exit(1); });
