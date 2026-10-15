// 诊断证据墙为空的原因（看 DOM + 拦截网络请求）
const PW = 'E:/deepseek-harness/node_modules/.pnpm/playwright@1.61.1/node_modules/playwright';

(async () => {
  const { chromium } = require(PW);
  const b = await chromium.launch({ channel: 'msedge', headless: false, args: ['--start-maximized'] });
  const ctx = await b.newContext({ viewport: null, locale: 'zh-CN' });
  const page = await ctx.newPage();

  const reqs = [];
  page.on('response', async r => {
    const u = r.url();
    if (u.includes('/api/') || u.includes('/uploads/')) {
      let bodyHead = '';
      try {
        const ct = r.headers()['content-type'] || '';
        if (ct.includes('json')) {
          const t = await r.text();
          bodyHead = t.slice(0, 200);
        }
      } catch (e) { /* ignore */ }
      reqs.push({ status: r.status(), url: u.replace('http://127.0.0.1:5173', ''), ct: (r.headers()['content-type'] || '').split(';')[0], body: bodyHead });
    }
  });

  await page.goto('http://127.0.0.1:5173/live', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(9000);

  console.log('=== 相关请求 ===');
  reqs.slice(0, 20).forEach(r => {
    console.log(`  [${r.status}] ${r.url}  (${r.ct})`);
    if (r.body) console.log(`        ${r.body.slice(0, 150)}`);
  });

  const dom = await page.evaluate(() => {
    const wall = document.querySelector('.wall');
    return {
      wallExists: !!wall,
      wallHTML: wall ? wall.innerHTML.replace(/\s+/g, ' ').slice(0, 400) : '',
      shotCount: document.querySelectorAll('.shot').length,
      emptyText: (() => { const e = document.querySelector('.empty'); return e ? e.innerText : ''; })(),
    };
  });
  console.log('\n=== DOM ===');
  console.log('  .wall 存在: ' + dom.wallExists);
  console.log('  .shot 数量: ' + dom.shotCount);
  console.log('  .empty 文案: ' + dom.emptyText);
  console.log('  wall HTML: ' + dom.wallHTML);

  console.log('\n>>> 保持 12 秒 <<<');
  await page.waitForTimeout(12000);
  await b.close();
})().catch(e => { console.log('FAILED: ' + String(e).slice(0, 220)); process.exit(1); });
