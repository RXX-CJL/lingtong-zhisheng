
import fs from 'node:fs';
const P = 'F:/AI/DSH-HQ/prototypes/memory-galaxy-3d.html';
let s = fs.readFileSync(P, 'utf8');
const probe = fs.readFileSync('E:/output/_tools/orb_probe.txt', 'utf8');
const anchor = '    const nearFocus = focusLevel > 0.02 && (fwById.get(n.id) || 0) > 0.55;';
if (!s.includes(anchor)) { console.log('ANCHOR MISS'); process.exit(1); }
if (s.includes('__ORB_CNT__')) { console.log('探针已存在，跳过'); process.exit(0); }
s = s.replace(anchor, anchor + probe);
fs.writeFileSync(P, s);
console.log('探针已插入');
