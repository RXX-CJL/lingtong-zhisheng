
import fs from 'node:fs';
const P = 'F:/AI/DSH-HQ/prototypes/memory-galaxy-3d.html';
let s = fs.readFileSync(P, 'utf8');

// ① 光球：中心改成本色提亮，而不是「白占满」
const old1 = `      core.addColorStop(0,   hexA(drawColor, Math.min(1, bodyA * 0.98)));
      core.addColorStop(0.45, hexA(drawColor, Math.min(1, bodyA * 0.88)));
      core.addColorStop(0.86, hexA(drawColor, Math.min(1, bodyA * 0.70)));
      core.addColorStop(1,   hexA(drawColor, Math.min(1, bodyA * 0.44)));   // 临边昏暗，不是黑`;
const new1 = `      // 中心提亮但仍保持本色（不是纯白），否则 300 颗星全变成白点，光谱信息就没了
      core.addColorStop(0,   hexA(mixHex(drawColor, "#ffffff", 0.30), Math.min(1, bodyA * 0.98)));
      core.addColorStop(0.42, hexA(drawColor, Math.min(1, bodyA * 0.90)));
      core.addColorStop(0.82, hexA(drawColor, Math.min(1, bodyA * 0.74)));
      core.addColorStop(1,   hexA(mixHex(drawColor, "#000000", 0.22), Math.min(1, bodyA * 0.52)));   // 临边昏暗，不是黑`;

// ② 白热核心：只占 0.42r → 0.26r，且 alpha 减半
const old2 = `      if (r > 2.4) {
        const hr = r * 0.42;
        const hl = ctx.createRadialGradient(p.sx, p.sy, 0, p.sx, p.sy, hr);
        hl.addColorStop(0, "rgba(255,252,246," + (0.62 * bodyA) + ")");
        hl.addColorStop(0.45, "rgba(255,248,235," + (0.22 * bodyA) + ")");
        hl.addColorStop(1, "rgba(255,245,230,0)");
        ctx.beginPath(); ctx.arc(p.sx, p.sy, hr, 0, 6.284);
        ctx.fillStyle = hl; ctx.fill();
      }`;
const new2 = `      if (r > 2.4) {
        const hr = r * 0.26;                                   // 只占核心一小块，不要盖住本色
        const hl = ctx.createRadialGradient(p.sx, p.sy, 0, p.sx, p.sy, hr);
        hl.addColorStop(0, "rgba(255,252,246," + (0.34 * bodyA) + ")");
        hl.addColorStop(0.45, "rgba(255,248,235," + (0.12 * bodyA) + ")");
        hl.addColorStop(1, "rgba(255,245,230,0)");
        ctx.beginPath(); ctx.arc(p.sx, p.sy, hr, 0, 6.284);
        ctx.fillStyle = hl; ctx.fill();
      }`;

// ③ 加一个 mixHex 工具（在恒星块之前定义一次即可，用函数声明便于提升）
const anchor = '    // ── 恒星本体（2026-11-01 重做：从「行星」改成「恒星」）──';
const helper = `    // 十六进制颜色插值：恒星需要「本色→更亮/更暗」，而不是写死白与黑
    if (!window.__mixHex__) {
      window.__mixHex__ = function (h1, h2, k) {
        const p = (h) => [parseInt(h.slice(1,3),16), parseInt(h.slice(3,5),16), parseInt(h.slice(5,7),16)];
        const [a1,b1,c1] = p(h1), [a2,b2,c2] = p(h2);
        const to = (v) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2,'0');
        return "#" + to(a1+(a2-a1)*k) + to(b1+(b2-b1)*k) + to(c1+(c2-c1)*k);
      };
    }
    const mixHex = window.__mixHex__;

` + anchor;

let hit = 0;
if (s.includes(old1)) { s = s.replace(old1, new1); hit++; } else console.log('MISS 1');
if (s.includes(old2)) { s = s.replace(old2, new2); hit++; } else console.log('MISS 2');
if (s.includes(anchor) && !s.includes('__mixHex__')) { s = s.replace(anchor, helper); hit++; } else console.log('MISS 3');

fs.writeFileSync(P, s);
console.log('替换命中: ' + hit + '/3');
