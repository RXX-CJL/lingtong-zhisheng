
import fs from 'node:fs';
const P = 'F:/AI/DSH-HQ/prototypes/memory-galaxy-3d.html';
let s = fs.readFileSync(P, 'utf8');
const before = s.length;
// 精确移除整条探针语句（按行删，避免误伤）
const lines = s.split(String.fromCharCode(10));
const kept = lines.filter(l => !l.includes('__CENTER__'));
s = kept.join(String.fromCharCode(10));
fs.writeFileSync(P, s);
console.log('移除行数: ' + (lines.length - kept.length) + '  字符: ' + before + ' -> ' + s.length);
