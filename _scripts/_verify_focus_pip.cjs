// 验证聚焦小窗：不遮挡主画面 + 开关可用
const PW = 'E:/deepseek-harness/node_modules/.pnpm/playwright@1.61.1/node_modules/playwright';
const OUT = 'E:/output/_screens';

(async () => {
  const { chromium } = require(PW);
  const b = await chromium.launch({ channel: 'msedge', headless: false, args: ['--start-maximized'] });
  const ctx = await b.newContext({ viewport: null, locale: 'zh-CN' });
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(String(e).slice(0, 200)));

  await page.goto('http://127.0.0.1:5173/live', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(6000);

  // 1) 确认开关存在
  const hasToggle = await page.evaluate(() =>
    [...document.querySelectorAll('.el-checkbox')].some(e => (e.innerText || '').includes('聚焦小窗')));
  console.log('  控制台"聚焦小窗"开关: ' + hasToggle);

  // 2) 等一个违规出现 -> 观察小窗
  let saw = false;
  for (let i = 0; i < 20; i++) {
    await page.waitForTimeout(4000);
    const info = await page.evaluate(() => {
      const pip = document.querySelector('.zoom-pip');
      const vid = document.querySelector('.video-wrap');
      const img = document.querySelector('.zoom-pip-img');
      const r = pip ? pip.getBoundingClientRect() : null;
      const vr = vid ? vid.getBoundingClientRect() : null;
      return {
        bad: document.querySelectorAll('.vcard--bad').length,
        pipExists: !!pip,
        pipRect: r ? { w: Math.round(r.width), h: Math.round(r.height), right: Math.round(r.right), bottom: Math.round(r.bottom) } : null,
        videoRect: vr ? { w: Math.round(vr.width), h: Math.round(vr.height) } : null,
        imgW: img ? img.naturalWidth : 0,
      };
    });
    if (info.bad > 0) {
      console.log(`  [${(i + 1) * 4}s] 右栏违规=${info.bad}  小窗存在=${info.pipExists}`);
      if (info.pipRect && info.videoRect) {
        const coverPct = (info.pipRect.w * info.pipRect.h) / (info.videoRect.w * info.videoRect.h) * 100;
        console.log(`     小窗尺寸 ${info.pipRect.w}x${info.pipRect.h}  主画面 ${info.videoRect.w}x${info.videoRect.h}`);
        console.log(`     小窗占主画面面积: ${coverPct.toFixed(1)}%   (全屏旧版为 100%)`);
        console.log(`     小窗图片 naturalWidth=${info.imgW}`);
      }
      if (info.pipExists) {
        await page.screenshot({ path: OUT + '/focus-pip.png' });
        console.log('     截图: focus-pip.png');
        saw = true;
        break;
      }
    }
  }
  if (!saw) console.log('  （等待期内未捕捉到聚焦小窗，可能没有违规事件）');

  // 3) 关掉开关，确认小窗不再出现
  await page.evaluate(() => {
    const cb = [...document.querySelectorAll('.el-checkbox')].find(e => (e.innerText || '').includes('聚焦小窗'));
    if (cb) cb.click();
  });
  await page.waitForTimeout(1500);
  const afterOff = await page.evaluate(() => !!document.querySelector('.zoom-pip'));
  console.log('  关闭开关后小窗存在: ' + afterOff + '  (期望 false)');

  console.log('  页面错误: ' + errs.length);
  errs.slice(0, 4).forEach(e => console.log('    ' + e));
  console.log('>>> 窗口保持 15 秒 <<<');
  await page.waitForTimeout(15000);
  await b.close();
})().catch(e => { console.log('FAILED: ' + String(e).slice(0, 220)); process.exit(1); });
