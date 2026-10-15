// Second-stage patch: make every blocked-build detection and retry site
// consistent, and retry blocked npm-source installs too.
import { readFileSync, writeFileSync, existsSync, copyFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

const TARGET = process.argv[2] ?? 'C:/Users/ROG/.dsh/profiles/web/node_modules/dsh-workshop/lib/host/core-BcUmZo6v.mjs';
const MARKER = '// [dsh-workshop] blocked-build sites patched';

let src = readFileSync(TARGET, 'utf8');
if (src.includes(MARKER)) {
  console.log('already patched - nothing to do');
  process.exit(0);
}

const BLOCKED_TEST = 'isBuildBlocked(res.output) || /allowBuilds|Failed to create bin/i.test(res.output)';

// 1. isGit branch: broaden the detection used to decide whether to retry.
const OLD_GIT_TEST = '\t\tif (verified.code === 0 && /allowBuilds|Failed to create bin/i.test(res.output)) {';
const NEW_GIT_TEST = `\t\tif (verified.code === 0 && (${BLOCKED_TEST})) {`;

// 2. GitHub-fallback branch: broaden detection AND pass the exact depPath data.
const OLD_FALLBACK_TEST = '\t\tif (verified.code === 0 && /allowBuilds|Failed to create bin/i.test(second.output)) {';
const NEW_FALLBACK_TEST = '\t\tif (verified.code === 0 && (isBuildBlocked(second.output) || /allowBuilds|Failed to create bin/i.test(second.output))) {';

const OLD_FALLBACK_ARGS = [
  '\t\t\tconst retry = await fixBlockedBuilds(key, profile, [',
  '\t\t\t\t"plugin",',
  '\t\t\t\t"--profile",',
  '\t\t\t\tprofile,',
  '\t\t\t\t"add",',
  '\t\t\t\tgitSource',
  '\t\t\t], env);',
].join('\n');
const NEW_FALLBACK_ARGS = OLD_FALLBACK_ARGS.replace('], env);', '], env, second.output, name + "@" + gitSource);');

// 3. npm-source branch: no retry existed at all; add the same two-stage unlock.
const OLD_NPM_BRANCH = [
  '\t\tif (npmOut.code === 0) {',
  '\t\t\tconst verified = await verifyInstalledAndRollback(parseInstalledKey(npmOut.output) ?? npmName, name, profile, npmOut.output, env);',
  '\t\t\tfinishProgress(verified.code === 0, verified.code === 0 ? "安装完成" : "安装失败");',
  '\t\t\treturn { ...verified };',
  '\t\t}',
].join('\n');
const NEW_NPM_BRANCH = [
  '\t\tif (npmOut.code === 0) {',
  '\t\t\tlet npmKey = parseInstalledKey(npmOut.output) ?? npmName;',
  '\t\t\tconst verified = await verifyInstalledAndRollback(npmKey, name, profile, npmOut.output, env);',
  '\t\t\tif (verified.code === 0 && (isBuildBlocked(npmOut.output) || /allowBuilds|Failed to create bin/i.test(npmOut.output))) {',
  '\t\t\t\tnpmKey = await resolveDependencyKey(name, profile) ?? npmKey;',
  '\t\t\t\tsetProgressStage("构建脚本被阻止，正在解锁并重装…", s);',
  '\t\t\t\tconst retry = await fixBlockedBuilds(npmKey, profile, [',
  '\t\t\t\t\t"plugin",',
  '\t\t\t\t\t"--profile",',
  '\t\t\t\t\tprofile,',
  '\t\t\t\t\t"add",',
  '\t\t\t\t\tnpmName',
  '\t\t\t\t], env, npmOut.output, npmName);',
  '\t\t\t\tif (retry && retry.code === 0) {',
  '\t\t\t\t\tconst verified2 = await verifyInstalledAndRollback(parseInstalledKey(retry.output) ?? npmKey, name, profile, retry.output, env);',
  '\t\t\t\t\tfinishProgress(verified2.code === 0, verified2.code === 0 ? "npm 源安装完成（含构建）" : "npm 源安装完成（构建仍异常）");',
  '\t\t\t\t\treturn { ...verified2 };',
  '\t\t\t\t}',
  '\t\t\t\tfinishProgress(true, "安装完成（构建可能未执行，可稍后重试）");',
  '\t\t\t\treturn { ...verified };',
  '\t\t\t}',
  '\t\t\tfinishProgress(verified.code === 0, verified.code === 0 ? "安装完成" : "安装失败");',
  '\t\t\treturn { ...verified };',
  '\t\t}',
].join('\n');

// Build the actual replacement list (label, old, new)
const replacements = [
  ['isGit detection', OLD_GIT_TEST, NEW_GIT_TEST],
  ['github-fallback detection', OLD_FALLBACK_TEST, NEW_FALLBACK_TEST],
  ['github-fallback retry args', OLD_FALLBACK_ARGS, NEW_FALLBACK_ARGS],
  ['npm-source retry', OLD_NPM_BRANCH, NEW_NPM_BRANCH],
];

const countOf = (h, n) => h.split(n).length - 1;
const problems = [];
for (const [label, oldText] of replacements) {
  const n = countOf(src, oldText);
  if (n !== 1) problems.push(`${label}: anchor x${n}`);
}
if (problems.length) {
  console.error('ABORT: unexpected file shape -', problems.join(', '));
  process.exit(1);
}
for (const [, , newText] of replacements) {
  if (newText.includes(String.fromCharCode(96))) {
    console.error('ABORT: replacement text contains a backtick');
    process.exit(1);
  }
}

for (const [, oldText, newText] of replacements) src = src.replace(oldText, newText);

const anchor = 'export { core_exports as a';
const anchorAt = src.indexOf(anchor);
if (anchorAt < 0) {
  console.error('ABORT: export anchor not found');
  process.exit(1);
}
src = src.slice(0, anchorAt) + MARKER + '\n' + src.slice(anchorAt);

if (!existsSync(`${TARGET}.pre-patch2`)) copyFileSync(TARGET, `${TARGET}.pre-patch2`);
writeFileSync(TARGET, src, 'utf8');

const check = spawnSync(process.execPath, ['--check', TARGET], { encoding: 'utf8' });
if (check.status !== 0) {
  copyFileSync(`${TARGET}.pre-patch2`, TARGET);
  console.error('ABORT: node --check failed; restored');
  console.error(check.stderr);
  process.exit(1);
}
console.log('patched OK (node --check passed), regions:', replacements.length);
