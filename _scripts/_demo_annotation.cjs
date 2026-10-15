// 人行道标注演示：可见 Edge 实操 + 分步截图
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

  console.log('打开 /live');
  await page.goto('http://127.0.0.1:5173/live', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(5000);

  // ---- 1) 确认页面结构 ----
  const st = await page.evaluate(() => ({
    panels: document.querySelectorAll('.panel').length,
    hasSceneBtn: [...document.querySelectorAll('button')].some(b => (b.innerText || '').includes('场景标注')),
    srcKind: (document.querySelector('.bar-right select, .bar-right .el-select') ? 'yes' : 'no'),
  }));
  console.log(`  三栏=${st.panels}  场景标注按钮=${st.hasSceneBtn}  源选择器=${st.srcKind}`);
  await page.screenshot({ path: OUT + '/demo-1-live.png' });

  // ---- 2) 打开场景标注对话框 ----
  console.log('点击「场景标注」');
  try {
    await page.getByRole('button', { name: /场景标注/ }).click({ timeout: 10000 });
  } catch (e) {
    console.log('  按文字点击失败，改用选择器');
    await page.evaluate(() => {
      const b = [...document.querySelectorAll('button')].find(x => (x.innerText || '').includes('场景标注'));
      if (b) b.click();
    });
  }
  await page.waitForTimeout(3500);

  const dlg = await page.evaluate(() => {
    const img = document.querySelector('.scene-img');
    const tip = document.querySelector('.scene-tip');
    return {
      hasImg: !!img,
      imgW: img ? img.naturalWidth : 0,
      imgH: img ? img.naturalHeight : 0,
      tip: tip ? tip.innerText.slice(0, 80) : '',
      hasSvg: !!document.querySelector('.scene-svg'),
    };
  });
  console.log(`  对话框: 画布图=${dlg.hasImg} (${dlg.imgW}x${dlg.imgH})  SVG覆盖层=${dlg.hasSvg}`);
  if (dlg.tip) console.log('  提示: ' + dlg.tip);
  await page.screenshot({ path: OUT + '/demo-2-dialog.png' });

  // ---- 3) 在画布上点 4 个角点 ----
  if (dlg.hasImg) {
    const box = await page.evaluate(() => {
      const img = document.querySelector('.scene-img');
      const r = img.getBoundingClientRect();
      return { x: r.x, y: r.y, w: r.width, h: r.height, nw: img.naturalWidth, nh: img.naturalHeight };
    });
    // 在画面下半部选一个"斑马线状"四边形（按自然坐标 1280x576 设计）
    const quad = [[180, 430], [980, 425], [1080, 520], [80, 528]];
    console.log('  依次点击 4 个角点（自然坐标）:');
    for (const [nx, ny] of quad) {
      const px = box.x + (nx / box.nw) * box.w;
      const py = box.y + (ny / box.nh) * box.h;
      await page.mouse.click(px, py);
      await page.waitForTimeout(500);
      const n = await page.evaluate(() => document.querySelectorAll('.pt').length);
      console.log(`    点击(${nx},${ny}) -> 画面点标记数=${n}`);
    }
    const poly = await page.evaluate(() => {
      const p = document.querySelector('.poly');
      return p ? p.getAttribute('points') : null;
    });
    console.log('  多边形已绘制: ' + (poly ? poly.slice(0, 70) : '无'));
    await page.screenshot({ path: OUT + '/demo-3-points.png' });

    // ---- 4) 保存 ----
    console.log('点击「保存标注」');
    await page.evaluate(() => {
      const b = [...document.querySelectorAll('button')].find(x => (x.innerText || '').includes('保存标注'));
      if (b) b.click();
    });
    await page.waitForTimeout(2500);
    const msg = await page.evaluate(() => {
      const m = document.querySelector('.el-message');
      return m ? m.innerText : '';
    });
    console.log('  提示信息: ' + (msg || '(无)'));
    await page.screenshot({ path: OUT + '/demo-4-saved.png' });
  }

  console.log('  页面错误: ' + errs.length);
  errs.slice(0, 4).forEach(e => console.log('    ' + e));
  console.log('>>> 窗口保持 15 秒 <<<');
  await page.waitForTimeout(15000);
  await b.close();
})().catch(e => { console.log('FAILED: ' + String(e).slice(0, 220)); process.exit(1); });
