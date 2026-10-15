// 用正确的 HTML5 history 路由验证事件中心与事件详情
const PW = 'E:/deepseek-harness/node_modules/.pnpm/playwright@1.61.1/node_modules/playwright';
const EVENT = 'evt_1790880613866_6_5a903d';

(async () => {
  const { chromium } = require(PW);
  const b = await chromium.launch({ headless: true });
  const ctx = await b.newContext({ viewport: { width: 1600, height: 1100 }, locale: 'zh-CN' });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(String(e).slice(0, 120)));

  async function visit(url, name, wait = 4000) {
    console.log('=== ' + url);
    try {
      const r = await page.goto(url, { waitUntil: 'networkidle', timeout: 40000 });
      await page.waitForTimeout(wait);
      const text = await page.evaluate(() => document.body.innerText || '');
      const imgs = await page.evaluate(() => {
        const list = [...document.querySelectorAll('img')];
        return { total: list.length, broken: list.filter(i => !i.complete || i.naturalWidth === 0).length };
      });
      const videos = await page.evaluate(() => {
        const v = [...document.querySelectorAll('video')];
        return v.map(x => ({ src: (x.currentSrc || x.src || '').slice(-60), readyState: x.readyState, w: x.videoWidth }));
      });
      console.log('   HTTP=' + (r ? r.status() : '?') + '  文本=' + text.length + '  图片=' + imgs.total + '(破损' + imgs.broken + ')');
      console.log('   含事件ID=' + text.includes(EVENT.slice(0, 22)) + '  含speeding=' + /speeding|超速/i.test(text));
      if (videos.length) console.log('   video 标签: ' + JSON.stringify(videos));
      console.log('   片段: ' + text.slice(0, 260).replace(/\n+/g, ' | '));
      const shot = 'E:/output/_screens/' + name + '.png';
      await page.screenshot({ path: shot, fullPage: false });
      console.log('   截图: ' + shot);
    } catch (e) {
      console.log('   失败: ' + String(e).slice(0, 140));
    }
    console.log();
  }

  await visit('http://127.0.0.1:5173/events', 'front-events');
  await visit('http://127.0.0.1:5173/events/' + EVENT, 'front-event-detail', 6000);

  console.log('=== 页面错误: ' + errors.length + ' ===');
  errors.slice(0, 5).forEach(e => console.log('   ' + e));
  await b.close();
})().catch(e => { console.log('FAILED: ' + String(e).slice(0, 200)); process.exit(1); });
