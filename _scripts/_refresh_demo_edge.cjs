// 刷新演示页并切换数据源到 CARLA 视频（复用已有 Edge 窗口）
const PW = 'E:/deepseek-harness/node_modules/.pnpm/playwright@1.61.1/node_modules/playwright';
const OUT = 'E:/output/_screens';

(async () => {
  const { chromium } = require(PW);
  const ctx = await chromium.launchPersistentContext('E:/output/_edge_profile', {
    channel: 'msedge', headless: false, viewport: null, locale: 'zh-CN',
    args: ['--start-maximized'],
  });
  const page = ctx.pages().length ? ctx.pages()[0] : await ctx.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(String(e).slice(0, 150)));

  await page.goto('http://127.0.0.1:5173/live', { waitUntil: 'networkidle', timeout: 60000 });
  console.log('  页面已刷新');

  // 通过 UI 的下拉框明确选择「视频文件」并填路径（避免退回 camera）
  // 先看下拉框与输入框结构
  const ui = await page.evaluate(() => {
    const sel = document.querySelector('.console ~ * select, .el-select');
    const inputs = [...document.querySelectorAll('input')].map(i => ({
      ph: i.placeholder || '', val: (i.value || '').slice(0, 60),
    }));
    return {
      selectText: sel ? sel.innerText.trim() : '',
      inputs: inputs.slice(0, 8),
      videoImg: !!document.querySelector('.video-img'),
      srcImg: (() => { const i = document.querySelector('.video-img'); return i ? i.src : ''; })(),
    };
  });
  console.log('  下拉框: ' + JSON.stringify(ui.selectText));
  console.log('  输入框: ' + JSON.stringify(ui.inputs));
  console.log('  视频流 src: ' + String(ui.srcImg).slice(-60));

  await page.waitForTimeout(35000);

  const st = await page.evaluate(() => ({
    clean: document.querySelectorAll('.vcard--ok').length,
    bad: document.querySelectorAll('.vcard--bad').length,
    kmh: [...document.querySelectorAll('.vc-kmh')].map(e => e.innerText.replace(/\s+/g, '')),
    src: (() => { const i = document.querySelector('.video-img'); return i ? i.naturalWidth : 0; })(),
  }));
  console.log(`  左栏=${st.clean} 右栏=${st.bad} 视频流宽=${st.src}`);
  console.log(`  km/h: ${JSON.stringify(st.kmh.slice(0, 8))}`);

  await page.screenshot({ path: OUT + '/demo-carla2.png' });
  console.log('  截图: demo-carla2.png');
  console.log('  页面错误: ' + errs.length);
  errs.slice(0, 3).forEach(e => console.log('    ' + e));
  console.log('  >>> Edge 窗口保持打开 <<<');
  await page.waitForTimeout(600000);
  process.exit(0);
})().catch(e => { console.log('FAILED: ' + String(e).slice(0, 250)); process.exit(1); });
