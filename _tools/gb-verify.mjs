import fs from 'node:fs';
import crypto from 'node:crypto';
const dir = 'F:/AI/GlassBoard/GlassBoard';
const lines = fs.readFileSync(dir + '/SHA256SUMS.txt', 'utf8').split(/\r?\n/).filter(Boolean);
let ok = 0, bad = 0, miss = 0, skipped = 0;
for (const l of lines) {
  const m = l.trim().match(/^([a-f0-9]{64})\s+(.+)$/);
  if (!m) { skipped++; continue; }
  const h = m[1], f = m[2].trim();
  const p = dir + '/' + f;
  if (!fs.existsSync(p)) { console.log('MISS ' + f); miss++; continue; }
  const a = crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
  if (a === h) ok++; else { console.log('BAD  ' + f); bad++; }
}
console.log('');
console.log('RESULT ok=' + ok + '  bad=' + bad + '  missing=' + miss + '  unparsed=' + skipped + '  totalLines=' + lines.length);