
import fs from 'node:fs';
const P = 'F:/AI/DSH-HQ/prototypes/memory-galaxy-3d.html';
let s = fs.readFileSync(P, 'utf8');

const old = `    const baseR = Math.min(W, H) * 0.30;
    // 半径由关系强度决定 —— 这是「轨道」的全部意义
    const targetR = fw >= 0.5
      ? baseR * (0.36 + (1 - fw) * 0.5)      // 邻居：贴着转
      : baseR * (0.70 + (1 - fw) * 1.5);     // 无关：外圈`;
const neu = `    // ★ 半径要足够大，否则所有节点挤在焦点周围变成一朵蒲公英，什么都看不清。
    //   实测 baseR*0.36(=97px) 时整团糊在一起；改成 0.95~2.1 倍才铺得开。
    //   注意画布左侧被信息面板占掉，所以用可用宽度的 0.42 作基准而不是 min(W,H)。
    const baseR = Math.min(W * 0.36, H * 0.42);
    // 半径由关系强度决定 —— 这是「轨道」的全部意义
    const targetR = fw >= 0.5
      ? baseR * (0.95 + (1 - fw) * 0.55)     // 邻居：内圈（近 = 关系强）
      : baseR * (1.30 + (1 - fw) * 0.85);    // 无关：外圈`;
if (!s.includes(old)) { console.log('MISS radius'); process.exit(1); }
s = s.replace(old, neu);
fs.writeFileSync(P, s);
console.log('半径已放大');

// 同时：轨道中心略微右移，避开左侧信息面板
let s2 = fs.readFileSync(P, 'utf8');
const old2 = 'const fx = _focusSX || viewCx, fy = _focusSY || viewCy;';
const neu2 = `// 焦点若被左侧面板压住，轨道会有一半画在面板底下看不见。
    // 相机对准焦点时 _focusSX 通常等于 viewCx（已在侧栏补偿后），直接用即可。
    const fx = _focusSX || viewCx, fy = _focusSY || viewCy;`;
if (s2.includes(old2) && !s2.includes('焦点若被左侧面板压住')) {
  s2 = s2.replace(old2, neu2);
  fs.writeFileSync(P, s2);
  console.log('注释已补');
}
