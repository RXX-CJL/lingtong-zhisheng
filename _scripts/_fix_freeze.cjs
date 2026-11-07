const fs = require('fs');
const P = 'C:/Users/ROG/.dsh/task-board/ledger-v2.json';
const d = JSON.parse(fs.readFileSync(P,'utf8'));
const t = d.tasks.find(x => x.title.includes('违停'));
// 补 frozenAt（normalizeFreeze 强制要求）
t.freeze.frozenAt = Date.now();
d.revision = (d.revision||0) + 1;
fs.writeFileSync(P, JSON.stringify(d, null, 2), 'utf8');
console.log('已补 frozenAt:', t.freeze.frozenAt);
console.log(JSON.stringify(t.freeze, null, 1));