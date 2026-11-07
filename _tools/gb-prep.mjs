import fs from 'node:fs';
const D = 'C:/Users/ROG/AppData/Local/GlassBoard';
// 备份
const stamp = new Date().toISOString().replace(/[:.]/g,'-');
fs.copyFileSync(D + '/layout.json', D + '/layout.json.bak-shu-' + stamp);
console.log('backup = layout.json.bak-shu-' + stamp);
const j = JSON.parse(fs.readFileSync(D + '/layout.json', 'utf8'));
console.log('\n=== Apps 完整字段（一个样本）===');
console.log(JSON.stringify(j.Apps[0], null, 1));
console.log('\n=== 桌面上那 10 个未收录的，看它们的 lnk 是否真实存在 ===');
const missing = ['CC Switch','ChatGPT','Cloudflare','draw.io','DroidCamApp','Plain Craft Launcher 2','Radmin.exe','无畏契约WeGame版','电源-平衡模式','电源-高性能模式'];
for (const n of missing) {
  const desk = 'C:/Users/ROG/Desktop/' + n + '.lnk';
  const ok = fs.existsSync(desk);
  let same = '';
  try { const a = j.Apps.find(x => (x.Name||'').toLowerCase() === n.toLowerCase()); if (a) same = ' [Apps里有同名: '+a.Name+']'; } catch {}
  console.log('  ' + (ok?'有lnk':'无lnk') + '  ' + n + same);
}