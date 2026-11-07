import fs from 'node:fs';
import path from 'node:path';
const D = 'C:/Users/ROG/Desktop';
const out = 'E:/output/_glassboard_snapshot';
fs.mkdirSync(out, { recursive: true });
const items = fs.readdirSync(D, { withFileTypes: true }).map(e => {
  const p = path.join(D, e.name);
  let size = 0, mtime = '';
  try { const s = fs.statSync(p); size = s.size; mtime = s.mtime.toISOString(); } catch {}
  return { name: e.name, type: e.isDirectory() ? 'dir' : 'file', size, mtime };
});
items.sort((a, b) => a.name.localeCompare(b.name, 'zh'));
const stamp = new Date().toISOString().replace(/[:.]/g, '-');
fs.writeFileSync(out + '/desktop-before-' + stamp + '.json', JSON.stringify({ capturedAt: new Date().toISOString(), deskPath: D, count: items.length, items }, null, 2), 'utf8');
fs.writeFileSync(out + '/desktop-before.tsv', ['name\ttype\tsize', ...items.map(i => i.name + '\t' + i.type + '\t' + i.size)].join('\n'), 'utf8');
const byType = {};
for (const i of items) { const m = i.name.match(/\.([A-Za-z0-9]+)$/); const k = i.type === 'dir' ? '<dir>' : (m ? m[1].toLowerCase() : '<none>'); byType[k] = (byType[k] || 0) + 1; }
console.log('snapshot written, count=' + items.length);
console.log('KEY: ' + Object.entries(byType).sort((a,b)=>b[1]-a[1]).map(([k,v])=>k+'='+v).join('  '));
console.log('STAMP: ' + stamp);