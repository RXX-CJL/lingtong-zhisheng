
import fs from 'node:fs';
const P = 'F:/AI/DSH-HQ/prototypes/memory-galaxy-3d.html';
let s = fs.readFileSync(P, 'utf8');
const before = s;

const old1 = "      if (a > 0.016) {\n        const core = Math.max(0.8, r * 0.62);          // 只画核，不画轮廓";
const new1 = "      if (a > 0.016) {\n"
  + "        // ★ 2026-11-01 拉近修复：点的大小绝不能跟着 zoom 线性放大。\n"
  + "        //   原来 core = r*0.62 且 r = n.size*13*p.s，zoom 4.5 时 p.s 涨近 3 倍，\n"
  + "        //   点被放大成 20-40px 的大圆盘，看起来又变回了「球」—— 这就是「拉近后诡异」。\n"
  + "        //   真实星空里，星星再近也只是一个点，变的是亮度与位置，不是直径。\n"
  + "        const ZOOM_TAME = 0.35;                                   // 缩放对点尺寸的贡献压到 35%\n"
  + "        const effR = Math.min(r, n.size * 13 * (1 + (p.s - 1) * ZOOM_TAME));\n"
  + "        const core = Math.min(2.6, Math.max(0.8, effR * 0.62));   // 硬上限 2.6px";

const old2 = "        if (r > 2.2) {                                  // 大星带一圈短光晕（不是球，是辉光）\n          const G = r * 2.0;";
const new2 = "        if (effR > 2.2) {                               // 大星带一圈短光晕（不是球，是辉光）\n          const G = Math.min(9, effR * 2.0);          // 光晕同样设上限";

let hit = 0;
if (s.includes(old1)) { s = s.replace(old1, new1); hit++; } else console.log('MISS old1');
if (s.includes(old2)) { s = s.replace(old2, new2); hit++; } else console.log('MISS old2');
fs.writeFileSync(P, s);
console.log('替换命中: ' + hit + '/2');
