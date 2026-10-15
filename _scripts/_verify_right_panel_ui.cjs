// 验证右栏真的显示违规车辆（可见 Edge + 长等待 + 多次截图）
const PW = 'E:/deepseek-harness/node_modules/.pnpm/playwright@1.61.1/node_modules/playwright';
const OUT = 'E:/output/_screens';

(async () => {
  const { chromium } = require(PW);
  console.log('启动可见 Edge...');
  const b = await chromium.launch({ channel: 'msedge', headless: false, args: ['--start-maximized'] });
  const ctx = await b.newContext({ viewport: null, locale: 'zh-CN' });
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(String(e).slice(0, 140)));

  await page.goto('http://127.0.0.1:5173/live', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(4000);

  let shots = 0;
  let sawViolator = false;
  const log = [];
  // 轮询最多 150 秒，捕捉右栏出现违规车辆的时刻
  for (let i = 0; i < 30; i++) {
    await page.waitForTimeout(5000);
    const st = await page.evaluate(() => ({
      clean: document.querySelectorAll('.vcard--ok').length,
      bad: document.querySelectorAll('.vcard--bad').length,
      badText: [...document.querySelectorAll('.vcard--bad')].map(e => e.innerText.replace(/\n+/g, ' | ').slice(0, 90)),
      cleanText: [...document.querySelectorAll('.vcard--ok')].map(e => e.innerText.replace(/\n+/g, ' | ').slice(0, 70)),
      unassigned: document.querySelector('.ph-count.danger') ? document.querySelector('.ph-count.danger').innerText : '',
    }));
    const line = `[${String((i + 1) * 5).padStart(3)}s] 左栏=${st.clean} 右栏=${st.bad}`;
    console.log(line);
    log.push(line);
    if (st.bad > 0 && !sawViolator) {
      sawViolator = true;
      console.log('  ★ 右栏出现违规车辆:');
      st.badText.forEach(t => console.log('     ' + t));
      await page.screenshot({ path: OUT + '/right-panel-violator.png' });
      console.log('     截图: right-panel-violator.png');
      shots++;
    }
    if (st.clean > 0 && shots === 0 && i % 4 === 3) {
      await page.screenshot({ path: OUT + '/right-panel-waiting.png' });
      shots++;
      console.log('     (等待中截图)');
    }
    if (sawViolator && i > 2) break;
  }

  const final = await page.evaluate(() => ({
    clean: document.querySelectorAll('.vcard--ok').length,
    bad: document.querySelectorAll('.vcard--bad').length,
    unassigned: document.querySelectorAll('.unassigned-item').length,
    panelHeads: [...document.querySelectorAll('.panel-head')].map(e => e.innerText.replace(/\n/g, ' ')),
  }));
  console.log('最终: 左栏=' + final.clean + ' 右栏=' + final.bad);
  console.log('面板头: ' + JSON.stringify(final.panelHeads));
  console.log('页面错误: ' + errs.length);
  console.log('>>> 窗口保持 20 秒 <<<');
  await page.waitForTimeout(20000);
  await b.close();
})().catch(e => { console.log('FAILED: ' + String(e).slice(0, 220)); process.exit(1); });
