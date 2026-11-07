
import fs from 'node:fs';
const P = 'F:/AI/DSH-HQ/prototypes/memory-galaxy-3d.html';
let s = fs.readFileSync(P, 'utf8');
const before = s.length;
// 移除 __ORB_CNT__ 计数探针（验证用完了，不该留在生产代码里）
const probe = fs.readFileSync('E:/output/_tools/orb_probe.txt', 'utf8');
if (s.includes(probe)) { s = s.replace(probe, ''); console.log('计数探针已移除'); }
else console.log('计数探针未找到（可能格式不同），尝试逐行清理');
// 兜底：按行删除
s = s.split('\n').filter(l => !l.includes('__ORB_CNT__')).join('\n');
fs.writeFileSync(P, s);
console.log('字节: ' + before + ' -> ' + s.length);
