
import fs from 'node:fs';
const P = 'F:/AI/DSH-HQ/prototypes/memory-galaxy-3d.html';
let s = fs.readFileSync(P, 'utf8');
let hit = 0;

// ① 深度推远大幅减弱：它才是「三点一线」的元凶
const oldA = `    pushOut = fw >= 0.5
      ? (1 - fw) * 1.15            // 邻居：让开但不消失，别把目标埋住
      : (1 - fw) * 1.85;           // 无关：推远
    pushOut *= pushLevel;`;
const newA = `    // ★ 2026-11-01：深度推远从 1.15/1.85 降到 0.28/0.34。
    //   原来沿深度推开，投影后全排成一条直线 —— 这就是用户说的「三点一线」。
    //   现在只保留一点「让开遮挡」的作用，主要位移交给屏幕空间轨道（见下方 orbit）。
    pushOut = fw >= 0.5
      ? (1 - fw) * 0.28
      : (1 - fw) * 0.34;
    pushOut *= pushLevel;`;
if (s.includes(oldA)) { s = s.replace(oldA, newA); hit++; } else console.log('MISS A');

// ② 替换 project 的 return 段为轨道版
const oldB = `  const persp = FOCAL / Math.max(0.06, camDepth);
  const screenScale = Math.min(W, H) * 0.30 * zoom;
  // 视图锚点：缩放中心由滚轮发生时指针的位置决定，之后固定不动。
  return {
    sx: viewCx + cx1 * persp * screenScale,
    sy: viewCy + cy2 * persp * screenScale,
    s: persp * zoom,
    persp,
    depth,
    z: depth,
    behind: false,
  };
}`;
const orbitBody = fs.readFileSync('E:/output/_tools/orbit_patch.txt', 'utf8');
const newB = `  const persp = FOCAL / Math.max(0.06, camDepth);
  const screenScale = Math.min(W, H) * 0.30 * zoom;
  // 视图锚点：缩放中心由滚轮发生时指针的位置决定，之后固定不动。
` + orbitBody;
if (s.includes(oldB)) { s = s.replace(oldB, newB); hit++; } else console.log('MISS B');

fs.writeFileSync(P, s);
console.log('替换命中: ' + hit + '/2');
