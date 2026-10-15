// 可见 Edge 演示：打开前端事件中心 + 事件详情，实时演给你看
// 特点：channel='msedge' + headless:false —— 会弹出真实浏览器窗口
const PW = 'E:/deepseek-harness/node_modules/.pnpm/playwright@1.61.1/node_modules/playwright';
const EVENT_ARG = process.argv[2] || '';
const OUT = 'E:/output/_screens';

(async () => {
  const { chromium } = require(PW);
  console.log('启动可见 Edge 窗口...');
  // 使用系统 Edge（可见），带上 --start-maximized 便于观察
  const b = await chromium.launch({
    channel: 'msedge',
    headless: false,
    args: ['--start-maximized', '--disable-features=msEdgeSidebarV2'],
  });
  const ctx = await b.newContext({ viewport: null, locale: 'zh-CN' });
  const page = await ctx.newPage();

  const errors = [];
  page.on('pageerror', e => errors.push(String(e).slice(0, 140)));

  // 1) 事件中心
  console.log('打开事件中心 /events');
  await page.goto('http://127.0.0.1:5173/events', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(4000);
  const t1 = await page.evaluate(() => document.body.innerText || '');
  const m = t1.match(/交通事件列表（共\s*(\d+)\s*条）/);
  console.log('  ' + (m ? `事件总数 = ${m[1]}` : '未找到事件总数'));
  const statusLines = [...t1.matchAll(/(待\s*AI\s*分析|待AI分析|已确认|已排除|待人工复核)/g)]
    .map(x => x[1]);
  const counts = {};
  statusLines.forEach(s => { counts[s.replace(/\s/g, '')] = (counts[s.replace(/\s/g, '')] || 0) + 1; });
  console.log('  首页可见状态计数:', JSON.stringify(counts));
  await page.screenshot({ path: OUT + '/edge-events.png' });

  // 2) 事件详情（优先用传入的 event id，否则取列表第一行）
  let evId = EVENT_ARG;
  if (!evId) {
    const mm = t1.match(/evt_\d+_\d+_[0-9a-f]+/);
    evId = mm ? mm[0] : '';
  }
  if (evId) {
    console.log('打开事件详情 /events/' + evId);
    await page.goto('http://127.0.0.1:5173/events/' + evId, { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(5000);
    const t2 = await page.evaluate(() => document.body.innerText || '');
    console.log('  状态片段: ' + t2.slice(0, 220).replace(/\n+/g, ' | '));

    // 尝试播放视频（可见窗口里能直接看到）
    const played = await page.evaluate(async () => {
      const v = document.querySelector('video');
      if (!v) return 'no-video-tag';
      try {
        v.muted = true;
        await v.play();
        return `playing readyState=${v.readyState} ${v.videoWidth}x${v.videoHeight} t=${v.currentTime.toFixed(1)}s dur=${(v.duration || 0).toFixed(1)}s`;
      } catch (e) { return 'play-failed: ' + String(e).slice(0, 80); }
    });
    console.log('  视频: ' + played);
    await page.waitForTimeout(6000);
    const after = await page.evaluate(() => {
      const v = document.querySelector('video');
      return v ? `currentTime=${v.currentTime.toFixed(1)}s paused=${v.paused}` : 'gone';
    });
    console.log('  6 秒后: ' + after);
    await page.screenshot({ path: OUT + '/edge-event-detail.png' });
    console.log('  截图: ' + OUT + '/edge-event-detail.png');
  } else {
    console.log('  未取得事件 ID');
  }

  console.log('页面错误数: ' + errors.length);
  errors.slice(0, 5).forEach(e => console.log('  ' + e));

  console.log('\n>>> 浏览器窗口保持打开 25 秒，你可以直接看 <<<');
  await page.waitForTimeout(25000);
  await b.close();
  console.log('已关闭浏览器');
})().catch(e => { console.log('FAILED: ' + String(e).slice(0, 250)); process.exit(1); });
