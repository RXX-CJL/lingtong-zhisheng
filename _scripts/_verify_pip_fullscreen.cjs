// 验证：聚焦小窗（引用检测框）+ 全屏按钮
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
  await page.waitForTimeout(8000);
  console.log('  页面已加载');

  // 1) 全屏按钮是否存在
  const ui = await page.evaluate(() => {
    const fs = document.querySelector('.fs-btn');
    const vid = document.querySelector('.video-img');
    return {
      fsBtn: !!fs, fsText: fs ? fs.innerText.trim() : '',
      fsTitle: fs ? fs.title : '',
      videoW: vid ? vid.naturalWidth : 0,
      videoH: vid ? vid.naturalHeight : 0,
      pipToggle: [...document.querySelectorAll('.el-checkbox')].some(e => (e.innerText || '').includes('聚焦小窗')),
    };
  });
  console.log(`  全屏按钮: ${ui.fsBtn}  图标="${ui.fsText}"  提示="${ui.fsTitle}"`);
  console.log(`  视频: ${ui.videoW}x${ui.videoH}   聚焦小窗开关: ${ui.pipToggle}`);

  // 2) 等违规出现，观察小窗是否引用检测框内容
  let saw = null;
  for (let i = 0; i < 30; i++) {
    await page.waitForTimeout(4000);
    const st = await page.evaluate(() => {
      const pip = document.querySelector('.zoom-pip');
      const img = document.querySelector('.zoom-pip-img');
      const cap = document.querySelector('.zoom-pip-cap');
      const bad = document.querySelectorAll('.vcard--bad').length;
      const bbox = (() => {
        const el = document.querySelector('.vcard--bad');
        return el ? el.innerText.replace(/\s+/g, ' ').slice(0, 60) : '';
      })();
      return {
        bad, pip: !!pip,
        cap: cap ? cap.innerText.replace(/\s+/g, ' ').trim() : '',
        src: img ? String(img.src).slice(0, 40) : '',
        isDataUrl: img ? String(img.src).startsWith('data:image') : false,
        w: img ? img.naturalWidth : 0, h: img ? img.naturalHeight : 0,
        card: bbox,
      };
    });
    if (st.pip) {
      console.log(`  [${(i + 1) * 4}s] 小窗出现 ✅`);
      console.log(`     标题: "${st.cap}"`);
      console.log(`     来源: ${st.isDataUrl ? 'data:URL（检测框裁切快照）' : st.src}`);
      console.log(`     尺寸: ${st.w}x${st.h}   右栏违规车: ${st.bad}`);
      if (st.card) console.log(`     对应卡片: ${st.card}`);
      saw = st;
      await page.screenshot({ path: OUT + '/pip-bbox.png' });
      console.log('     截图: pip-bbox.png');
      break;
    }
  }
  if (!saw) console.log('  （等待期内无违规，小窗未出现）');

  // 3) 点全屏按钮（不真的全屏，只验证点击有响应且不报错）
  await page.evaluate(() => {
    const b = document.querySelector('.fs-btn');
    if (b) b.click();
  });
  await page.waitForTimeout(2500);
  const fsState = await page.evaluate(() => ({
    fullscreen: !!document.fullscreenElement,
    fsEl: document.fullscreenElement ? document.fullscreenElement.className : '',
    icon: (document.querySelector('.fs-btn') || {}).innerText || '',
  }));
  console.log(`  点击全屏后: fullscreen=${fsState.fullscreen}  元素=${fsState.fsEl}  图标="${String(fsState.icon).trim()}"`);
  await page.screenshot({ path: OUT + '/fullscreen-test.png' });
  console.log('  截图: fullscreen-test.png');

  console.log('  页面错误: ' + errs.length);
  errs.slice(0, 4).forEach(e => console.log('    ' + e));
  console.log('  >>> 窗口保持 <<<');
  await page.waitForTimeout(86400000);
})().catch(e => { console.log('FAILED: ' + String(e).slice(0, 250)); process.exit(1); });
