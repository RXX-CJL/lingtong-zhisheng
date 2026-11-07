
import fs from 'node:fs';
const P = 'F:/AI/DSH-HQ/prototypes/memory-galaxy-3d.html';
let s = fs.readFileSync(P, 'utf8');

// ① 拉近时提高连线阈值：只留最强的关系
const oldA = "    if(l.weight < 0.40) continue;   // 弱关系不画：少而清楚，胜过多而模糊";
const newA = "    // ★ 2026-11-01 拉近修复：zoom 越大，只画越强的连线。\n"
  + "    //   原来固定 0.40，拉近后线条被拉长、密度反而堆积成蜘蛛网（「拉近后诡异」的另一半）。\n"
  + "    //   真实星空里，看近时星星是散开的，那些「关系」本来就不该看见。\n"
  + "    const minWeight = zoom > 3.2 ? 0.66 : (zoom > 2.2 ? 0.52 : 0.40);\n"
  + "    if(l.weight < minWeight) continue;   // 弱关系不画：少而清楚，胜过多而模糊";

// ② 拉近时压制连线亮度
const oldB = "      ctx.strokeStyle=hexA(c,(0.055+l.weight*0.24+midBoost)*dep);\n      ctx.lineWidth=0.5+l.weight*0.9;";
const newB = "      // ★ 拉近时连线整体压暗压细，别抢星点的注意力\n"
  + "      const zoomTame = 1 / (1 + Math.max(0, (zoom - 1.55) * 0.62));\n"
  + "      ctx.strokeStyle=hexA(c,(0.055+l.weight*0.24+midBoost)*dep*zoomTame);\n"
  + "      ctx.lineWidth=(0.5+l.weight*0.9)*Math.max(0.55, zoomTame);";

let hit = 0;
if (s.includes(oldA)) { s = s.replace(oldA, newA); hit++; } else console.log('MISS A');
if (s.includes(oldB)) { s = s.replace(oldB, newB); hit++; } else console.log('MISS B');
fs.writeFileSync(P, s);
console.log('替换命中: ' + hit + '/2');
