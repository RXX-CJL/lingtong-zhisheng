import fs from 'node:fs';
const D = 'C:/Users/ROG/AppData/Local/GlassBoard';
console.log('=== session.log ===');
try { console.log(fs.readFileSync(D + '/session.log', 'utf8').slice(0, 1500)); } catch(e){ console.log('err '+e.message) }
const j = JSON.parse(fs.readFileSync(D + '/layout.json', 'utf8'));
console.log('\n=== Dock 配置 ===');
const d = j.Dock || {};
for (const k of Object.keys(d)) { const v = d[k]; console.log('  ' + k + ' = ' + (typeof v === 'object' ? JSON.stringify(v).slice(0,120) : JSON.stringify(v))); }
console.log('\n=== DockOrder（Dock 里显示的顺序）===');
(j.DockOrder||[]).forEach((p,i)=>console.log('  ' + (i+1) + '. ' + String(p).split('\\').pop()));
console.log('\n=== 未分组的 Apps 前 40 个 ===');
const un = j.Apps.filter(a => !a.Group);
console.log('共 ' + un.length + ' 个未分组');
un.slice(0,40).forEach(a=>console.log('  ' + (a.Name||'?') + '   [Path: ' + String(a.Path||a.LaunchTarget||'').slice(-60) + ']'));