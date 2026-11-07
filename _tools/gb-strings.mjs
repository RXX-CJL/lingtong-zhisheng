import fs from 'node:fs';
const buf = fs.readFileSync('F:/AI/GlassBoard/GlassBoard/GlassBoard.exe');
// 提 ASCII 与 UTF-16LE 字符串
const ascii = buf.toString('latin1').match(/[\x20-\x7E]{6,}/g) || [];
const uni = buf.toString('utf16le').match(/[\x20-\x7E\u4e00-\u9fa5]{4,}/g) || [];
const all = [...ascii, ...uni];
const kw = /autostart|auto-start|Run\\|StartupApproved|开机|自启|启动项|CurrentVersion\\Run|Shell:startup|StartUp|StartWithWindows|LaunchAtLogin/i;
const hits = [...new Set(all.filter(s => kw.test(s)))].slice(0, 40);
console.log('=== 命中 ' + hits.length + ' 条 ===');
hits.forEach(s => console.log('  ' + s.slice(0, 150)));
console.log('\n=== 含 GlassBoard 的字符串 ===');
[...new Set(all.filter(s => /GlassBoard/i.test(s)))].slice(0, 20).forEach(s => console.log('  ' + s.slice(0, 120)));