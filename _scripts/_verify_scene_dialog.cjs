// 验证：场景标注对话框（区域手绘 + 相机参数）
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
  console.log('  页面已加载');

  // 点「场景标注」
  await page.evaluate(() => {
    const b = [...document.querySelectorAll('button')].find(x => (x.innerText || '').trim() === '场景标注');
    if (b) b.click();
  });
  await page.waitForTimeout(6000);

  const st = await page.evaluate(() => {
    const dlg = document.querySelector('.el-dialog');
    const zones = [...document.querySelectorAll('.zone-item')].map(e => e.innerText.replace(/\s+/g, ' ').trim());
    const selects = [...document.querySelectorAll('.el-dialog .el-select')].map(e => e.innerText.trim());
    const inputs = [...document.querySelectorAll('.el-dialog .el-input-number input')].map(i => i.value);
    const canvas = document.querySelector('.scene-canvas img');
    return {
      dlgOpen: !!dlg,
      dlgTitle: dlg ? (dlg.querySelector('.el-dialog__title') || {}).innerText : '',
      zoneTypes: selects,
      camInputs: inputs,
      zones,
      canvasW: canvas ? canvas.naturalWidth : 0,
      canvasH: canvas ? canvas.naturalHeight : 0,
      ppmNote: (document.querySelector('.cf-note') || {}).innerText || '',
    };
  });
  console.log('  对话框: ' + st.dlgOpen + '  标题: ' + st.dlgTitle);
  console.log('  区域类型下拉: ' + JSON.stringify(st.zoneTypes));
  console.log('  相机参数输入: ' + JSON.stringify(st.camInputs));
  console.log('  画布: ' + st.canvasW + 'x' + st.canvasH);
  console.log('  已标注区域: ' + JSON.stringify(st.zones));
  console.log('  ppm 预览: ' + String(st.ppmNote).replace(/\s+/g, ' ').slice(0, 70));

  // 在画布上点 4 个点，测「添加到列表」
  const box = await page.evaluate(() => {
    const img = document.querySelector('.scene-canvas img');
    if (!img) return null;
    const r = img.getBoundingClientRect();
    return { x: r.x, y: r.y, w: r.width, h: r.height };
  });
  if (box) {
    const pts = [[0.2, 0.3], [0.5, 0.3], [0.5, 0.5], [0.2, 0.5]];
    for (const [fx, fy] of pts) {
      await page.mouse.click(box.x + box.w * fx, box.y + box.h * fy);
      await page.waitForTimeout(300);
    }
    await page.waitForTimeout(800);
    const afterPts = await page.evaluate(() => (document.querySelector('.scene-count') || {}).innerText || '');
    console.log('  点击 4 点后: ' + afterPts);

    // 点「添加到列表」
    await page.evaluate(() => {
      const b = [...document.querySelectorAll('.el-dialog button')]
        .find(x => (x.innerText || '').includes('添加到列表'));
      if (b) b.click();
    });
    await page.waitForTimeout(1200);
    const zones2 = await page.evaluate(() =>
      [...document.querySelectorAll('.zone-item')].map(e => e.innerText.replace(/\s+/g, ' ').trim()));
    console.log('  添加后区域列表: ' + JSON.stringify(zones2));
  }

  await page.screenshot({ path: OUT + '/scene-dialog.png' });
  console.log('  截图: scene-dialog.png');
  console.log('  页面错误: ' + errs.length);
  errs.slice(0, 4).forEach(e => console.log('    ' + e));
  console.log('  >>> 窗口保持 <<<');
  await page.waitForTimeout(86400000);
})().catch(e => { console.log('FAILED: ' + String(e).slice(0, 250)); process.exit(1); });
