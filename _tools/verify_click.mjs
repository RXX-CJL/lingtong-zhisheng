
import { chromium } from 'playwright-core';
const b = await chromium.launch({ channel: 'msedge', headless: true });
const p = await b.newPage({ viewport: { width: 1280, height: 800 } });
const errs = [];
p.on('pageerror', e => errs.push(String(e).slice(0, 200)));
await p.goto('http://127.0.0.1:7717/?instant=1', { waitUntil: 'networkidle', timeout: 30000 });
await p.waitForTimeout(2500);

// 读内部状态：拿一个有邻居的节点
const probe = await p.evaluate(() => {
  const w = window;
  // 尝试从常见全局名拿 nodes / links
  const keys = Object.keys(w).filter(k => /node|link|galaxy|graph/i.test(k));
  return { keys, hasFlow: typeof w.triggerFlow === 'function' };
});
console.log('EXPOSE:', JSON.stringify(probe));

// 不依赖内部变量：直接在画布上找一颗亮星并点击
const pts = await p.evaluate(() => {
  const cv = document.querySelector('canvas');
  const r = cv.getBoundingClientRect();
  return { x: r.x, y: r.y, w: r.width, h: r.height };
});
console.log('CANVAS:', JSON.stringify(pts));

// 用像素扫描找最亮的点（星球）再点它
const target = await p.evaluate(() => {
  const cv = document.querySelector('canvas');
  const ctx = cv.getContext('2d');
  const W = cv.width, H = cv.height;
  const img = ctx.getImageData(0, 0, W, H).data;
  let best = -1, bx = 0, by = 0;
  for (let y = 40; y < H - 40; y += 4) {
    for (let x = 40; x < W - 40; x += 4) {
      const i = (y * W + x) * 4;
      const lum = img[i] + img[i+1] + img[i+2];
      if (lum > best) { best = lum; bx = x; by = y; }
    }
  }
  const dpr = W / cv.getBoundingClientRect().width;
  return { cssX: bx / dpr, cssY: by / dpr, lum: best };
});
console.log('BRIGHTEST:', JSON.stringify(target));

const before = await p.screenshot();
const beforeBuf = Buffer.from(before);

await p.mouse.click(target.cssX, target.cssY);
await p.waitForTimeout(120);
const during = await p.screenshot();

await p.waitForTimeout(1500);
const after = await p.screenshot();

const diffB = Buffer.compare(beforeBuf, Buffer.from(during)) !== 0;
const diffA = Buffer.compare(beforeBuf, Buffer.from(after)) !== 0;
console.log('CLICK_EFFECT_120ms:', diffB);
console.log('CLICK_EFFECT_1500ms:', diffA);
console.log('PAGE_ERRORS:', JSON.stringify(errs));

await p.screenshot({ path: 'F:/AI/DSH-HQ/logs/shots/click_during.png' });
await b.close();
