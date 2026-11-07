import fs from 'node:fs';
const P = 'C:/Users/ROG/AppData/Local/GlassBoard/layout.json';
const j = JSON.parse(fs.readFileSync(P, 'utf8'));
console.log('=== 现有 Groups ===');
console.log(JSON.stringify(j.Groups));
console.log('\n=== Apps 按 Group 统计 ===');
const cnt = {};
for (const a of j.Apps) { const g = a.Group || '(未分组)'; cnt[g] = (cnt[g]||0)+1; }
Object.entries(cnt).sort((a,b)=>b[1]-a[1]).forEach(([k,v])=>console.log('  ' + k + ': ' + v));
console.log('\n=== 桌面的 38 个 lnk 在 Apps 里的对应 ===');
const deskNames = ['CanMV IDE K230','CC Switch','ChatGPT','Claude','Cloudflare','Configure Virtual Serial Port Driver','DeepSeek Harness','draw.io','DroidCamApp','GitHub Desktop','GitHub','Microsoft Edge','Mineradio','Notion','Ollama','Plain Craft Launcher 2','Proteus 8 Professional','Qoder CN IDE','Qoder CN','Radmin.exe','STOVE','Trae CN','Visual Studio Code','WebCodex Desktop','WPS Office','和平精英模拟器','崩坏：星穹铁道','微信开发者工具','抖音','无畏契约WeGame版','瑶光','电源-平衡模式','电源-高性能模式','百度网盘','米哈游启动器','迅雷','雷电多开器','雷电模拟器9'];
let found = 0;
for (const n of deskNames) {
  const hit = j.Apps.find(a => (a.Name||'').toLowerCase() === n.toLowerCase() || (a.Path||'').toLowerCase().includes(n.toLowerCase()));
  if (hit) { found++; console.log('  ✓ ' + n + '  →  组[' + (hit.Group||'无') + ']'); }
  else console.log('  ✗ ' + n + '  →  未收录');
}
console.log('\n命中 ' + found + '/' + deskNames.length);