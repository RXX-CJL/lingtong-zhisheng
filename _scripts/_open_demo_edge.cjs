// 打开演示页并保持窗口（不关闭，方便用户观察）
const PW = 'E:/deepseek-harness/node_modules/.pnpm/playwright@1.61.1/node_modules/playwright';
const OUT = 'E:/output/_screens';

(async () => {
  const { chromium } = require(PW);
  // 用持久化上下文 -> 复用同一个 Edge 窗口，避免每次新开
  const ctx = await chromium.launchPersistentContext('E:/output/_edge_profile', {
    channel: 'msedge',
    headless: false,
    viewport: null,
    locale: 'zh-CN',
    args: ['--start-maximized', '--disable-blink-features=AutomationControlled'],
  });
  const pages = ctx.pages();
  const page = pages.length ? pages[0] : await ctx.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(String(e).slice(0, 160)));

  await page.goto('http://127.0.0.1:5173/live', { waitUntil: 'networkidle', timeout: 60000 });
  console.log('  已打开 /live');

  // 点「开始」让画面动起来
  await page.evaluate(() => {
    const b = [...document.querySelectorAll('button')].find(x => (x.innerText || '').trim() === '开始');
    if (b) b.click();
  });
  console.log('  已点击「开始」');

  await page.waitForTimeout(30000);

  const st = await page.evaluate(() => ({
    clean: document.querySelectorAll('.vcard--ok').length,
    bad: document.querySelectorAll('.vcard--bad').length,
    kmh: [...document.querySelectorAll('.vc-kmh')].map(e => e.innerText.replace(/\s+/g, '')),
    status: (document.querySelector('.status-line') || {}).innerText || '',
    imgW: (() => { const i = document.querySelector('.video-img'); return i ? i.naturalWidth : 0; })(),
    evidence: document.querySelectorAll('.shot').length,
  }));
  console.log(`  左栏(正常)=${st.clean}  右栏(违规)=${st.bad}  证据墙=${st.evidence}  视频流宽=${st.imgW}`);
  console.log(`  km/h: ${JSON.stringify(st.kmh.slice(0, 8))}`);
  console.log(`  状态栏: ${String(st.status).replace(/\s+/g, ' ').slice(0, 90)}`);

  await page.screenshot({ path: OUT + '/demo-carla.png' });
  console.log('  截图: demo-carla.png');
  console.log('  页面错误: ' + errs.length);
  errs.slice(0, 3).forEach(e => console.log('    ' + e));

  // 保持窗口打开：长等待后退出（不关闭浏览器窗口本身）
  console.log('  >>> Edge 窗口保持打开，供你观察 <<<');
  console.log('  >>> 如需重开请手动刷新；脚本 10 分钟后自动退出（窗口不关）<<<');
  await page.waitForTimeout(600000);
  // 不调用 ctx.close() —— 让 Edge 窗口留在桌面上
  console.log('  脚本退出，Edge 窗口保留');
  process.exit(0);
})().catch(e => { console.log('FAILED: ' + String(e).slice(0, 250)); process.exit(1); });
