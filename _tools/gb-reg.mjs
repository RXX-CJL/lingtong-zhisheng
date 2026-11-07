import fs from 'node:fs';
const b = fs.readFileSync('F:/AI/GlassBoard/GlassBoard/GlassBoard.exe');
const uni = b.toString('utf16le').match(/[\x20-\x7E\u4e00-\u9fa5]{3,}/g) || [];
const asc = b.toString('latin1').match(/[\x20-\x7E]{3,}/g) || [];
const all = [...new Set([...uni, ...asc])];
// 找注册表路径、值名、任务名、快捷方式名
const pat = /CurrentVersion\\\\Run|Shell:startup|StartupApproved|GetFolderPath|StartupFolder|TaskService|\\\\GlassBoard|Startup\\b|autostart/i;
console.log('=== 注册表/启动相关（去重前 40）===');
const h1 = all.filter(s => /CurrentVersion\\|StartupApproved|StartupFolder|Shell:startup|\\\\Run\\b/i.test(s));
h1.slice(0, 40).forEach(s => console.log('  [' + s.length + '] ' + s.slice(0, 160)));
console.log('\n=== 短字符串里含 Run/Startup 的（可能是值名）===');
const h2 = all.filter(s => s.length <= 40 && /run|startup|glass/i.test(s));
h2.slice(0, 50).forEach(s => console.log('  ' + JSON.stringify(s)));