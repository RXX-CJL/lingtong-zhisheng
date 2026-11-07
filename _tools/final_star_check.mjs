
import fs from 'node:fs';
const P = 'F:/AI/DSH-HQ/prototypes/memory-galaxy-3d.html';
let s = fs.readFileSync(P, 'utf8');
// 把 window.__mixHex__ 独立函数改成模块内普通函数（去掉挂在 window 上的写法）
const oldA = `    // 十六进制颜色插值：恒星需要「本色→更亮/更暗」，而不是写死白与黑
    if (!window.__mixHex__) {
      window.__mixHex__ = function (h1, h2, k) {
        const p = (h) => [parseInt(h.slice(1,3),16), parseInt(h.slice(3,5),16), parseInt(h.slice(5,7),16)];
        const [a1,b1,c1] = p(h1), [a2,b2,c2] = p(h2);
        const to = (v) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2,'0');
        return "#" + to(a1+(a2-a1)*k) + to(b1+(b2-b1)*k) + to(c1+(c2-c1)*k);
      };
    }
    const mixHex = window.__mixHex__;`;
const newA = `    // 十六进制颜色插值：恒星需要「本色→更亮/更暗」，而不是写死白与黑
    const mixHex = (h1, h2, k) => {
      const p = (h) => [parseInt(h.slice(1,3),16), parseInt(h.slice(3,5),16), parseInt(h.slice(5,7),16)];
      const [a1,b1,c1] = p(h1), [a2,b2,c2] = p(h2);
      const to = (v) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2,'0');
      return "#" + to(a1+(a2-a1)*k) + to(b1+(b2-b1)*k) + to(c1+(c2-c1)*k);
    };`;
if (s.includes(oldA)) { s = s.replace(oldA, newA); console.log('已改为模块内函数'); }
else console.log('未找到 window 版本（可能已是模块内）');
fs.writeFileSync(P, s);
