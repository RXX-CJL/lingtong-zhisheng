
import fs from 'node:fs';
const P = 'F:/AI/DSH-HQ/prototypes/memory-galaxy-3d.html';
let s = fs.readFileSync(P, 'utf8');
if (s.includes('__CENTER__')) { console.log('已存在'); process.exit(0); }
const anchor = '  // 轨道与推远同步淡入（INSTANT 时直接到位，方便截图验证）';
if (!s.includes(anchor)) { console.log('MISS'); process.exit(1); }
s = s.replace(anchor, '  if (window.__DBG__) window.__CENTER__ = { fx: Math.round(_focusSX), fy: Math.round(_focusSY), vx: Math.round(viewCx), vy: Math.round(viewCy), fl: +focusLevel.toFixed(2), ol: +orbitLevel.toFixed(2), id: focusNode ? focusNode.id : null, kind: focusNode ? focusNode.kind : null };' + String.fromCharCode(10) + anchor);
fs.writeFileSync(P, s);
console.log('迷你探针已加');
