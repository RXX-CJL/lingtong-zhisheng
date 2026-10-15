// 验证证据抓拍墙（可见 Edge + 截图）
const PW = 'E:/deepseek-harness/node_modules/.pnpm/playwright@1.61.1/node_modules/playwright';
const OUT = 'E:/output/_screens';

(async () => {
  const { chromium } = require(PW);
  const b = await chromium.launch({ channel: 'msedge', headless: false, args: ['--start-maximized'] });
  const ctx = await b.newContext({ viewport: null, locale: 'zh-CN' });
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(String(e).slice(0, 200)));
  page.on('console', m => { if (m.type() === 'error') errs.push('C: ' + m.text().slice(0, 180)); });

  await page.goto('http://127.0.0.1:5173/live', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(8000);

  const st = await page.evaluate(() => {
    const imgs = [...document.querySelectorAll('.shot img')];
    return {
      shots: imgs.length,
      loaded: imgs.filter(i => i.naturalWidth > 0).length,
      firstSrc: imgs[0] ? imgs[0].getAttribute('src') : null,
      firstW: imgs[0] ? imgs[0].naturalWidth : 0,
      wallCount: (() => { const e = document.querySelector('.wall-count'); return e ? e.innerText : ''; })(),
      caps: [...document.querySelectorAll('.shot-cap')].slice(0, 6).map(e => e.innerText),
      times: [...document.querySelectorAll('.shot-time')].slice(0, 4).map(e => e.innerText),
    };
  });
  console.log(`  抓拍图: ${st.shots} 张，已加载 ${st.loaded} 张`);
  console.log(`  计数标签: ${st.wallCount}`);
  console.log(`  首图: ${st.firstSrc}  naturalWidth=${st.firstW}`);
  console.log(`  类型标签: ${JSON.stringify(st.caps)}`);
  console.log(`  时间标签: ${JSON.stringify(st.times)}`);

  // 滚到证据墙
  await page.evaluate(() => {
    const w = document.querySelector('.wall');
    if (w) w.scrollIntoView({ block: 'center' });
  });
  await page.waitForTimeout(3000);
  await page.screenshot({ path: OUT + '/evidence-wall.png' });
  console.log('  截图: evidence-wall.png');

  console.log('  页面错误: ' + errs.length);
  errs.slice(0, 5).forEach(e => console.log('    ' + e));
  console.log('>>> 窗口保持 18 秒 <<<');
  await page.waitForTimeout(18000);
  await b.close();
})().catch(e => { console.log('FAILED: ' + String(e).slice(0, 220)); process.exit(1); });
