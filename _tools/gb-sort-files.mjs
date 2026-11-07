
import fs from 'node:fs';
import path from 'node:path';

const DESK = 'C:/Users/ROG/Desktop';
const APPLY = process.argv.includes('--apply');

// 分类规则：先到先得，按顺序匹配
const RULES = [
  { dir: '文档', exts: ['.docx', '.doc', '.pdf', '.pptx', '.txt', '.md'] },
  { dir: '图片', exts: ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'] },
  { dir: '工程', exts: ['.gxw', '.csv', '.drawio', '.json', '.ini', '.xlsx', '.xls'] },
  { dir: '视频', exts: ['.mp4', '.mov', '.avi', '.mkv'] },
];

// 永不移动
const SKIP_EXACT = new Set(['desktop.ini', 'thumbs.db']);
function skip(name) {
  if (SKIP_EXACT.has(name.toLowerCase())) return '系统文件';
  if (name.startsWith('~$')) return 'Office 锁文件';
  if (/\.(lnk|url|exe|dll|msi)$/i.test(name)) return '程序/快捷方式';
  return null;
}

const entries = fs.readdirSync(DESK, { withFileTypes: true });
const plan = [];
let skipped = [];

for (const e of entries) {
  const name = e.name;
  const reason = skip(name);
  if (reason) { skipped.push({ name, reason }); continue; }

  if (e.isDirectory()) { plan.push({ name, dir: '文档' }); continue; }

  const ext = path.extname(name).toLowerCase();
  const rule = RULES.find(r => r.exts.includes(ext));
  if (rule) plan.push({ name, dir: rule.dir });
  else skipped.push({ name, reason: '未匹配扩展名 ' + (ext || '(无)') });
}

const byDir = {};
for (const p of plan) (byDir[p.dir] ||= []).push(p.name);

console.log('=== 计划（' + plan.length + ' 项）===');
for (const d of Object.keys(byDir)) {
  console.log('\n[' + d + '] ' + byDir[d].length + ' 项');
  byDir[d].forEach(n => console.log('   ' + n));
}
console.log('\n=== 跳过（' + skipped.length + ' 项）===');
skipped.forEach(s => console.log('   ' + s.name + '   ← ' + s.reason));

if (!APPLY) { console.log('\n[DRY-RUN] 未改动任何文件。加 --apply 才真执行。'); process.exit(0); }

// ===== 真执行 =====
let moved = 0, failed = [];
for (const d of Object.keys(byDir)) {
  const target = path.join(DESK, d);
  fs.mkdirSync(target, { recursive: true });
  for (const name of byDir[d]) {
    const src = path.join(DESK, name);
    const dst = path.join(target, name);
    if (fs.existsSync(dst)) { failed.push({ name, why: '目标已存在，跳过不覆盖' }); continue; }
    try { fs.renameSync(src, dst); moved++; }
    catch (e) { failed.push({ name, why: e.message }); }
  }
}
console.log('\n=== 执行结果 ===');
console.log('已移动: ' + moved);
console.log('失败: ' + failed.length);
failed.forEach(f => console.log('   ✗ ' + f.name + ' — ' + f.why));
