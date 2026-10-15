// Scan the workshop registry for plugins that ship skills and are NOT installed.
import { readFileSync } from 'node:fs';

const REG = 'C:/Users/ROG/.dsh/dsh-workshop/registry.json';
const doc = JSON.parse(readFileSync(REG, 'utf8'));
const installed = new Set([
  'dsh-open-design', 'dsh-desktop', 'dsh-whale-widget', 'dsh-workshop',
  'dsh-deep-whale', 'OpenViking',
]);

const skills = doc.plugins.filter((p) => p.scanSignals?.hasSkillDir || p.scanSignals?.hasSKILLMD);
const notInstalled = skills.filter((p) => !installed.has(p.name));

console.log(`registry total: ${doc.plugins.length}`);
console.log(`plugins shipping skills: ${skills.length}`);
console.log(`  of which NOT installed: ${notInstalled.length}\n`);

const KW = /python|vision|opencv|yolo|traffic|data|dataset|train|model|deploy|inference|backend|api|sql|database|test|debug|refactor|engineering|code|mcp|document|paper|proposal|spec|research/i;
const rows = notInstalled.map((p) => {
  const text = `${p.name} ${p.description ?? ''} ${(p.topics ?? []).join(' ')}`;
  return { p, hit: KW.test(text) };
});
const relevant = rows.filter((r) => r.hit);
const others = rows.filter((r) => !r.hit);

console.log('=== 关键词相关的（候选） ===');
for (const { p } of relevant) {
  console.log(`${p.name}  [${p.fullName}]  ★${p.stars}`);
  console.log(`   ${(p.description ?? '').slice(0, 150)}`);
}
console.log(`\n=== 其余未安装带技能插件（名称+星标） 共 ${others.length} ===`);
for (const { p } of others) console.log(`  ${p.name} ★${p.stars} — ${(p.description ?? '').slice(0, 80)}`);
