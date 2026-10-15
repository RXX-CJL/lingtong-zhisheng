// 用可见 Edge 打开 /live 并截图（你能直接看到窗口）
const PW = 'E:/deepseek-harness/node_modules/.pnpm/playwright@1.61.1/node_modules/playwright';
const OUT = 'E:/output/_screens';

(async () => {
  const { chromium } = require(PW);
  console.log('启动可见 Edge...');
  const b = await chromium.launch({
    channel: 'msedge', headless: false,
    args: ['--start-maximized'],
  });
  const ctx = await b.newContext({ viewport: null, locale: 'zh-CN' });
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(String(e).slice(0, 160)));
  page.on('console', m => { if (m.type() === 'error') errs.push('C: ' + m.text().slice(0, 140)); });

  console.log('打开 /live');
  await page.goto('http://127.0.0.1:5173/live', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(6000);

  const info = await page.evaluate(() => {
    const q = s => document.querySelectorAll(s).length;
    const panels = [...document.querySelectorAll('.panel')].map(p => {
      const r = p.getBoundingClientRect();
      const cs = getComputedStyle(p);
      return { cls: p.className.replace('panel ', ''), w: Math.round(r.width), transform: cs.transform.slice(0, 40) };
    });
    return {
      panels,
      clean: q('.vcard--ok'),
      bad: q('.vcard--bad'),
      shots: q('.shot'),
      streamOk: !!document.querySelector('.video-img'),
      streamLoaded: (() => { const i = document.querySelector('.video-img'); return i ? i.naturalWidth : -1; })(),
      console: q('.con-row'),
    };
  });
  console.log('  三栏: ' + JSON.stringify(info.panels));
  console.log('  正常卡=' + info.clean + '  违规卡=' + info.bad + '  抓拍=' + info.shots + '  控制行=' + info.console);
  console.log('  视频流 naturalWidth=' + info.streamLoaded);

  await page.screenshot({ path: OUT + '/live-page.png', fullPage: false });
  console.log('  截图: ' + OUT + '/live-page.png');

  // 滚动到底部看抓拍墙
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(2000);
  await page.screenshot({ path: OUT + '/live-page-bottom.png' });
  console.log('  底部截图: ' + OUT + '/live-page-bottom.png');

  console.log('  页面错误: ' + errs.length);
  errs.slice(0, 6).forEach(e => console.log('    ' + e));

  console.log('>>> 窗口保持 20 秒，你可直接查看 <<<');
  await page.waitForTimeout(20000);
  await b.close();
})().catch(e => { console.log('FAILED: ' + String(e).slice(0, 220)); process.exit(1); });
