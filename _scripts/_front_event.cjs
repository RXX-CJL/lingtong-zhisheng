// 前端事件页可见性验证：打开事件详情，截图取证
const PW = 'E:/deepseek-harness/node_modules/.pnpm/playwright@1.61.1/node_modules/playwright';
const OUT = 'E:/output/_screens';
const EVENT = 'evt_1790880613866_6_5a903d';

(async () => {
  const { chromium } = require(PW);
  const fs = require('fs');
  const b = await chromium.launch({ headless: true });
  const ctx = await b.newContext({ viewport: { width: 1600, height: 1000 }, locale: 'zh-CN' });
  const page = await ctx.newPage();

  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text().slice(0, 140)); });
  page.on('pageerror', e => errors.push('PAGEERROR: ' + String(e).slice(0, 140)));
  const apiCalls = [];
  page.on('response', r => {
    const u = r.url();
    if (u.includes('/api/')) apiCalls.push(`${r.status()} ${u.replace('http://127.0.0.1:5173', '')}`);
  });

  // 尝试多个可能的事件页面路由
  const candidates = [
    'http://127.0.0.1:5173/#/events',
    'http://127.0.0.1:5173/#/realtime',
    'http://127.0.0.1:5173/',
  ];

  for (const url of candidates) {
    console.log('=== 打开 ' + url);
    try {
      const resp = await page.goto(url, { waitUntil: 'networkidle', timeout: 40000 });
      await page.waitForTimeout(3500);
      const text = await page.evaluate(() => document.body.innerText || '');
      const hasEvent = text.includes(EVENT.slice(0, 20)) || /speeding|超速/.test(text);
      const title = await page.title();
      console.log('   HTTP=' + (resp ? resp.status() : '?') + '  title=' + title);
      console.log('   页面文本长度=' + text.length + '  含事件/超速关键词=' + hasEvent);
      // 提取可见菜单，帮助定位正确路由
      const nav = await page.evaluate(() => {
        const els = [...document.querySelectorAll('a,button,li,span')]
          .map(e => (e.innerText || '').trim())
          .filter(t => t && t.length < 12);
        return [...new Set(els)].slice(0, 30);
      });
      console.log('   可见导航项: ' + nav.join(' | ').slice(0, 300));
      const shot = OUT + '/event-page-' + candidates.indexOf(url) + '.png';
      await page.screenshot({ path: shot });
      console.log('   截图: ' + shot);
      if (hasEvent) { console.log('   >>> 命中事件数据，采用此页'); break; }
    } catch (e) {
      console.log('   失败: ' + String(e).slice(0, 120));
    }
  }

  console.log();
  console.log('=== 本次页面发起的 API 请求 ===');
  apiCalls.slice(0, 20).forEach(c => console.log('   ' + c));
  console.log('=== 控制台错误: ' + errors.length + ' ===');
  errors.slice(0, 5).forEach(e => console.log('   ' + e));

  await b.close();
})().catch(e => { console.log('FAILED: ' + String(e).slice(0, 200)); process.exit(1); });
