// Detail the relevant uninstalled, skill-bearing plugins + check my current tool surface.
import { readFileSync } from 'node:fs';
const doc = JSON.parse(readFileSync('C:/Users/ROG/.dsh/dsh-workshop/registry.json', 'utf8'));
const want = ['modlens', 'ark-cli', 'huaweicloud-devkit', 'CloudBase-AI-Toolkit', 'dsh-genui',
  'distilly', 'Aegis', 'odai', 'mstar-harness', 'dsh-industry-research', 'dsh-memory',
  'codex-guard', 'engramory', 'ruflo', 'loopx'];
for (const name of want) {
  const p = doc.plugins.find((x) => x.name === name);
  if (!p) { console.log(`[${name}] 未在 registry 找到`); continue; }
  console.log(`### ${p.name}  ★${p.stars}  ${p.fullName}`);
  console.log(`  category=${p.category}  lang=${p.language}  updated=${(p.updatedAt ?? '').slice(0, 10)}  archived=${p.archived}`);
  console.log(`  install=${p.install}`);
  console.log(`  skillDir=${p.scanSignals?.hasSkillDir}  SKILL.md=${p.scanSignals?.hasSKILLMD}  hasMCP=${p.scanSignals?.hasDshManifest}  deps=${p.scanSignals?.deepseekDepCount}`);
  console.log(`  risk=${p.verification?.staticSecurity?.risk}  findings=${p.verification?.staticSecurity?.findingCount}`);
  console.log(`  desc=${(p.description ?? '').slice(0, 220)}`);
  console.log('');
}
