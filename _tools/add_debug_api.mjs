
import fs from 'node:fs';
const P = 'F:/AI/DSH-HQ/prototypes/memory-galaxy-3d.html';
let s = fs.readFileSync(P, 'utf8');
if (s.includes('__GALAXY_DBG__')) { console.log('调试接口已存在'); process.exit(0); }

// 在 draw 函数结束前挂一个调试接口，暴露焦点状态 + 可点击节点坐标
const anchor = 'pushLevel += ((focusMap ? 1 : 0) - pushLevel) * (INSTANT ? 1 : 0.055);';
if (!s.includes(anchor)) { console.log('MISS anchor'); process.exit(1); }

const inject = anchor + `
  // ★ 调试接口（仅 ?dbg=1）：让外部能量到「到底聚焦了没有、轨道在不在转」，
  //   而不是靠截图猜。之前几轮"看图判断"已经误判过两次。
  if (window.__DBG__) {
    window.__GALAXY_DBG__ = {
      focusId: focusNode ? focusNode.id : null,
      focusKind: focusNode ? focusNode.kind : null,
      focusLevel: +focusLevel.toFixed(3),
      pushLevel: +pushLevel.toFixed(3),
      orbitLevel: +orbitLevel.toFixed(3),
      orbitAngle: +orbitAngle.toFixed(4),
      focusSX: Math.round(_focusSX), focusSY: Math.round(_focusSY),
      // 给出「当前屏幕上可点中的节点」清单，供外部精确点击
      pickables: (function () {
        const out = [];
        for (const n of nodes) {
          if (n.kind === 'dark' || n.alpha < 0.06) continue;
          const p = project(n);
          if (p.behind) continue;
          const deg = (nbr.get(n.id) || []).length;
          out.push({ id: n.id, x: Math.round(p.sx), y: Math.round(p.sy), deg, kind: n.kind });
        }
        out.sort((a, b) => b.deg - a.deg);
        return out.slice(0, 40);
      })(),
    };
  }`;
s = s.replace(anchor, inject);
fs.writeFileSync(P, s);
console.log('调试接口已注入');
