
import fs from 'node:fs';
const P = 'E:/output/handoff/main.template.md';
const S = fs.readFileSync('E:/output/_tools/section9.txt', 'utf8');
let s = fs.readFileSync(P, 'utf8');
if (s.includes('## 九、星图视觉层本轮三改')) { console.log('已存在，跳过'); process.exit(0); }
fs.writeFileSync(P, s.replace(/\s*$/, '') + S);
console.log('已追加 §九');
