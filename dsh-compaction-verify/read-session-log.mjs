// Decompress a session log and show the preset-related session-start metadata.
import { readFileSync } from 'node:fs';
import zlib from 'node:zlib';

const path = process.argv[2];
const buf = readFileSync(path);
let text;
try {
  text = zlib.zstdDecompressSync(buf).toString('utf8');
} catch (e) {
  console.error('zstd failed:', e.message);
  process.exit(1);
}
const lines = text.split('\n').filter(Boolean);
console.log('records:', lines.length);
for (const line of lines.slice(0, 3)) {
  let rec;
  try { rec = JSON.parse(line); } catch { console.log('RAW:', line.slice(0, 400)); continue; }
  const s = JSON.stringify(rec);
  console.log('---', rec.type ?? rec.kind ?? 'record', 'len', s.length, '| preset mention:', /preset/i.test(s));
  if (/preset/i.test(s)) console.log(s.slice(0, 3000));
}
