
import fs from 'node:fs';
const P = 'F:/AI/DSH-HQ/prototypes/memory-galaxy-3d.html';
let s = fs.readFileSync(P, 'utf8');
let hit = 0;

// ① 在 pushLevel 定义旁边加轨道状态与辅助函数
const anchorA = 'let pushLevel = 0;';
const addA = `let pushLevel = 0;
// ★ 2026-11-01 新增：选中后「绕焦点公转」的状态。
//   orbitLevel —— 0..1 的过渡进度，和 pushLevel 同节奏淡入淡出，避免一闪。
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
if (s.includes(anchorA) && !s.includes('orbitLevel')) { s = s.replace(anchorA, addA); hit++; }
else if (s.includes('let orbitLevel')) console.log('变量已存在');
else console.log('MISS 变量锚点');

// ② 在 pushLevel 每帧更新旁边加 orbitLevel / orbitAngle 更新
const anchorB = 'pushLevel += ((focusMap ? 1 : 0) - pushLevel) * (INSTANT ? 1 : 0.055);';
const addB = `pushLevel += ((focusMap ? 1 : 0) - pushLevel) * (INSTANT ? 1 : 0.055);
  // 轨道与推远同步淡入（INSTANT 时直接到位，方便截图验证）
  const _orbitWant = (focusMap && focusNode && focusNode.kind !== 'stellar') ? 1 : 0;
  orbitLevel += (_orbitWant - orbitLevel) * (INSTANT ? 1 : 0.055);
  if (orbitLevel > 0.001) orbitAngle += (INSTANT ? 0 : 0.0022);   // 约 48 秒一圈，慢到不晕
  // 记录焦点屏幕坐标，作为轨道圆心（相机已对准它，基本等于视图锚点）
  if (focusNode) {
    const _fp = project(focusNode);
    if (!_fp.behind) { _focusSX = _fp.sx; _focusSY = _fp.sy; }
  }`;
if (s.includes(anchorB) && !s.includes('_orbitWant')) { s = s.replace(anchorB, addB); hit++; }
else if (s.includes('_orbitWant')) console.log('更新已存在');
else console.log('MISS 更新锚点');

fs.writeFileSync(P, s);
console.log('替换命中: ' + hit + '/2');
