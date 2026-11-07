import fs from 'node:fs';
const P = 'C:/Users/ROG/AppData/Local/GlassBoard/layout.json';
const j = JSON.parse(fs.readFileSync(P, 'utf8'));
console.log('TOP KEYS:', Object.keys(j).join(' | '));
for (const k of Object.keys(j)) {
  const v = j[k];
  if (Array.isArray(v)) {
    console.log('\n[' + k + '] array len=' + v.length);
    if (v.length) console.log('  first=' + JSON.stringify(v[0]).slice(0, 350));
  } else if (v && typeof v === 'object') {
    const ks = Object.keys(v);
    console.log('\n[' + k + '] obj keys(' + ks.length + ')=' + ks.slice(0,12).join(','));
    if (ks.length) console.log('  sample[' + ks[0] + ']=' + JSON.stringify(v[ks[0]]).slice(0, 350));
  } else {
    console.log('\n[' + k + '] = ' + JSON.stringify(v).slice(0, 200));
  }
}