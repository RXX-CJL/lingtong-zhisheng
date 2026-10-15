// 打开演示页（普通启动，避免持久化上下文锁冲突）
// 2026-10-04: 等待改为 24 小时 —— 用户要求窗口保持不关，方便随时观察
const PW = 'E:/deepseek-harness/node_modules/.pnpm/playwright@1.61.1/node_modules/playwright';
const OUT = 'E:/output/_screens';

(async () => {
  const { chromium } = require(PW);
  const b = await chromium.launch({
    channel: 'msedge', headless: false,
    args: ['--start-maximized'],
  });
  const ctx = await b.newContext({ viewport: null, locale: 'zh-CN' });
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(String(e).slice(0, 150)));

  await page.goto('http://127.0.0.1:5173/live', { waitUntil: 'networkidle', timeout: 60000 });
  console.log('  已打开 /live（后端此时已是 CARLA 视频源）');

  const ui = await page.evaluate(() => ({
    dropdowns: [...document.querySelectorAll('.el-select')].map(e => e.innerText.trim()),
    src: (() => { const i = document.querySelector('.video-img'); return i ? i.src.slice(-50) : ''; })(),
  }));
  console.log('  下拉框: ' + JSON.stringify(ui.dropdowns));
  console.log('  视频流: ' + ui.src);

  await page.waitForTimeout(40000);

  const st = await page.evaluate(() => ({
    clean: document.querySelectorAll('.vcard--ok').length,
    bad: document.querySelectorAll('.vcard--bad').length,
    kmh: [...document.querySelectorAll('.vc-kmh')].map(e => e.innerText.replace(/\s+/g, '')),
    dirs: [...document.querySelectorAll('.vc-dir')].map(e => e.innerText.trim()),
    w: (() => { const i = document.querySelector('.video-img'); return i ? i.naturalWidth : 0; })(),
  }));
  console.log(`  左栏=${st.clean} 右栏=${st.bad} 视频流宽=${st.w}`);
  console.log(`  km/h: ${JSON.stringify(st.kmh.slice(0, 8))}`);
  console.log(`  方向: ${JSON.stringify(st.dirs.slice(0, 8))}`);

  await page.screenshot({ path: OUT + '/demo-carla2.png' });
  console.log('  截图: demo-carla2.png');
  console.log('  页面错误: ' + errs.length);
  errs.slice(0, 3).forEach(e => console.log('    ' + e));
  console.log('  >>> Edge 窗口保持打开，供你观察 <<<');
  await page.waitForTimeout(86400000);   // 24 小时，窗口长期保持
  console.log('  脚本退出');
  process.exit(0);
})().catch(e => { console.log('FAILED: ' + String(e).slice(0, 250)); process.exit(1); });
