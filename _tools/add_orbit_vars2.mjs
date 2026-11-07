
import fs from 'node:fs';
const P = 'F:/AI/DSH-HQ/prototypes/memory-galaxy-3d.html';
let s = fs.readFileSync(P, 'utf8');
if (s.includes('let orbitLevel')) { console.log('变量已存在，跳过'); process.exit(0); }

// 用正则定位，容忍前后空白
const m = s.match(/^[ \t]*let pushLevel = 0;[ \t]*$/m);
if (!m) { console.log('MISS 正则也没找到'); process.exit(1); }

const addA = m[0] + `
// ★ 2026-11-01 新增：选中后「绕焦点公转」的状态。
//   orbitLevel —— 0..1 过渡进度，和 pushLevel 同节奏淡入淡出，避免一闪。
//   orbitAngle —— 全局公转相位，随时间推进。所有节点共享同一个时钟，
//                 但每颗星有自己的初相位（idPhase），所以不会像刚体一样整体旋转。
let orbitLevel = 0;
let orbitAngle = 0;
let _focusSX = 0, _focusSY = 0;      // 上一帧焦点的屏幕坐标，供轨道中心使用

// 用节点 id 算一个稳定的初相位（0..1）。同一个节点永远在同一个起始角度，
// 这样「转一圈回到原位」时你还能认出是它。
function idPhase(id) {
  let h = 2166136261;
  const str = String(id);
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return ((h >>> 0) % 10000) / 10000;
}`;
s = s.replace(m[0], addA);
fs.writeFileSync(P, s);
console.log('变量已插入');
