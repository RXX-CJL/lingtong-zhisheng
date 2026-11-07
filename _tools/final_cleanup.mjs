
import fs from 'node:fs';
const P = 'F:/AI/DSH-HQ/prototypes/memory-galaxy-3d.html';
let s = fs.readFileSync(P, 'utf8');
const before = s.length;
// 移除 __GALAXY_DBG__ 调试接口（它在 draw 里每帧跑，有性能开销）
const start = s.indexOf('  // ★ 调试接口（仅 ?dbg=1）');
if (start < 0) { console.log('探针未找到'); }
else {
  const endMark = '  }' + String.fromCharCode(10) + '  // 轨道与推远同步淡入';
  const end = s.indexOf(endMark, start);
  if (end < 0) { console.log('结束标记未找到'); }
  else { s = s.slice(0, start) + '  // 轨道与推远同步淡入' + s.slice(end + endMark.length); console.log('调试接口已移除'); }
}
fs.writeFileSync(P, s);
console.log('字符: ' + before + ' -> ' + s.length);
