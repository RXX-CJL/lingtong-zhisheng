// 验证速度质量徽标在 UI 里真的渲染
const PW = 'E:/deepseek-harness/node_modules/.pnpm/playwright@1.61.1/node_modules/playwright';
const OUT = 'E:/output/_screens';

(async () => {
  const { chromium } = require(PW);
  const b = await chromium.launch({ channel: 'msedge', headless: false, args: ['--start-maximized'] });
  const ctx = await b.newContext({ viewport: null, locale: 'zh-CN' });
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(String(e).slice(0, 160)));

  await page.goto('http://127.0.0.1:5173/live', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(9000);

  const st = await page.evaluate(() => {
    const kmh = [...document.querySelectorAll('.vc-kmh')].map(e => e.innerText.replace(/\s+/g, ''));
    const badges = [...document.querySelectorAll('.vc-badge')].map(e => ({
      t: e.innerText.trim(), cls: e.className.replace('vc-badge', '').trim(),
    }));
    const cards = document.querySelectorAll('.vcard--ok').length;
    return { cards, kmh, badges };
  });
  console.log(`  左栏卡片: ${st.cards}`);
  console.log(`  km/h 元素: ${st.kmh.length} 个 -> ${JSON.stringify(st.kmh.slice(0, 6))}`);
  console.log(`  徽标: ${st.badges.length} 个`);
  const uniq = {};
  st.badges.forEach(b => { uniq[b.t + '|' + b.cls] = (uniq[b.t + '|' + b.cls] || 0) + 1; });
  Object.entries(uniq).forEach(([k, v]) => console.log(`     ${k}  ×${v}`));

  await page.screenshot({ path: OUT + '/speed-badges.png' });
  console.log('  截图: speed-badges.png');
  console.log('  页面错误: ' + errs.length);
  errs.slice(0, 4).forEach(e => console.log('    ' + e));
  console.log('>>> 窗口保持 15 秒 <<<');
  await page.waitForTimeout(15000);
  await b.close();
})().catch(e => { console.log('FAILED: ' + String(e).slice(0, 220)); process.exit(1); });
