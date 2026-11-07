
import fs from 'node:fs';
const P = 'C:/Users/ROG/AppData/Local/GlassBoard/layout.json';
const j = JSON.parse(fs.readFileSync(P, 'utf8'));

// 先备份
const stamp = new Date().toISOString().replace(/[:.]/g, '-');
fs.copyFileSync(P, P + '.bak-folders-' + stamp);
console.log('备份: layout.json.bak-folders-' + stamp);

const FOLDERS = ['文档', '图片', '工程', '视频'];
const before = j.Apps.length;

for (const name of FOLDERS) {
  const full = 'C:\\Users\\ROG\\Desktop\\' + name;
  if (!fs.existsSync(full)) { console.log('跳过（不存在）: ' + name); continue; }
  const dup = j.Apps.find(a => (a.Path || '').toLowerCase() === full.toLowerCase());
  if (dup) { console.log('已存在，跳过: ' + name); continue; }
  j.Apps.push({
    Group: '桌面文件',
    LaunchArguments: '',
    LaunchTarget: full,
    Name: name,
    Path: full,
    Pinned: true,
    ProductInfo: ''
  });
}

if (!j.Groups.includes('桌面文件')) j.Groups.push('桌面文件');

// Dock：四个文件夹排在 AI/开发 之前，方便随手点
const folderPaths = FOLDERS.map(n => 'C:\\Users\\ROG\\Desktop\\' + n)
  .filter(p => j.Apps.some(a => (a.Path || '') === p));
const rest = (j.DockOrder || []).filter(p => !folderPaths.includes(p));
j.DockOrder = [...folderPaths, ...rest].slice(0, 60);

j.SaveRevision = (j.SaveRevision || 0) + 1;
fs.writeFileSync(P, JSON.stringify(j, null, 1), 'utf8');

console.log('新增 Apps: ' + (j.Apps.length - before));
console.log('Apps 总数: ' + j.Apps.length);
console.log('Groups: ' + JSON.stringify(j.Groups));
console.log('DockOrder 前 6 项:');
j.DockOrder.slice(0, 6).forEach((p, i) => console.log('  ' + (i + 1) + '. ' + p.split('\\').pop()));
