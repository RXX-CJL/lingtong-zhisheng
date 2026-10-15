// 验证标注分级显示：切换档位 + 画面遮挡对比
const PW = 'E:/deepseek-harness/node_modules/.pnpm/playwright@1.61.1/node_modules/playwright';
const OUT = 'E:/output/_screens';

(async () => {
  const { chromium } = require(PW);
  const b = await chromium.launch({ channel: 'msedge', headless: false, args: ['--start-maximized'] });
  const ctx = await b.newContext({ viewport: null, locale: 'zh-CN' });
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(String(e).slice(0, 180)));

  await page.goto('http://127.0.0.1:5173/live', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(6000);

  // 1) 确认档位选择器存在
  const hasSel = await page.evaluate(() => {
    const sels = [...document.querySelectorAll('.console .el-select')];
    return { count: sels.length, labels: sels.map(s => s.innerText.trim()) };
  });
  console.log('  控制台下拉框: ' + JSON.stringify(hasSel));

  // 2) 起始检测（画面需要有车才看得出效果）
  await page.evaluate(() => {
    const btn = [...document.querySelectorAll('button')].find(x => (x.innerText || '').trim() === '开始');
    if (btn) btn.click();
  });
  console.log('  已点击「开始」');
  await page.waitForTimeout(25000);

  for (const mode of ['minimal', 'full']) {
    // 通过后端接口切档（前端下拉走同一接口）
    await page.evaluate(async (m) => {
      await fetch('/api/realtime/settings', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ display_mode: m }),
      });
    }, mode);
    await page.waitForTimeout(7000);
    const st = await page.evaluate(() => ({
      clean: document.querySelectorAll('.vcard--ok').length,
      bad: document.querySelectorAll('.vcard--bad').length,
      imgW: (() => { const i = document.querySelector('.video-img'); return i ? i.naturalWidth : 0; })(),
    }));
    console.log(`  [${mode}] 左栏=${st.clean} 右栏=${st.bad} 视频流宽=${st.imgW}`);
    await page.screenshot({ path: `${OUT}/mode-${mode}.png` });
    console.log(`     截图: mode-${mode}.png`);
  }

  console.log('  页面错误: ' + errs.length);
  errs.slice(0, 4).forEach(e => console.log('    ' + e));
  console.log('>>> 窗口保持 15 秒 <<<');
  await page.waitForTimeout(15000);
  await b.close();
})().catch(e => { console.log('FAILED: ' + String(e).slice(0, 220)); process.exit(1); });
