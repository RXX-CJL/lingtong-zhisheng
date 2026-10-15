// Verification suite for the patched dsh-workshop installer.
//   A. classification covers every documented failure stage
//   B. blocked-build / policy / prepare signals are distinguished
//   C. precise allowBuilds writer handles pnpm's placeholder template
//   D. isolated retry config is created, used, and always cleaned up
//   E. end-to-end: real pnpm fixture blocked -> auto-unblocked, no user action
//   F. preserved mechanisms: blocklist, verify+rollback, restart, mirror env
import { mkdirSync, writeFileSync, readFileSync, rmSync, existsSync, readdirSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';

const SRC = process.argv[2] ?? 'C:/Users/ROG/.dsh/profiles/web/node_modules/dsh-workshop/lib/host/core-BcUmZo6v.mjs';
console.log('verifying:', SRC);
const PATCH = 'E:/output/dsh-workshop-patch';
const SB = `${PATCH}/verify-v2-sandbox`;
rmSync(SB, { recursive: true, force: true });
mkdirSync(`${SB}/stub`, { recursive: true });

const results = [];
const check = (label, ok, detail = '') => {
  results.push({ label, ok });
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${label}${detail ? '  -- ' + detail : ''}`);
};

// ---------- loadable copy with the DSH-tools import stubbed ----------------
let core = readFileSync(SRC, 'utf8');
writeFileSync(`${SB}/stub/dsh-tools.mjs`, 'export const defineTool = (x) => x;\n');
core = core.replace(
  'import { defineTool } from "@deepseek-ai/dsh-tools";',
  `import { defineTool } from ${JSON.stringify(pathToFileURL(`${SB}/stub/dsh-tools.mjs`).href)};`,
);
// route the installer to a fixture driver so the full retry chain can be exercised
core = core.replace(
  /async function installPlugin\(source, profile = "web", env\) \{[\s\S]*?\n\}/,
  `async function installPlugin(source, profile = "web", env) {
	return await globalThis.__fixtureInstall(spawn, source, profile, env);
}`,
);
writeFileSync(`${SB}/core.mjs`, core, 'utf8');

// fixture: profile dir + a dependency whose build script pnpm blocks
const FIX = `${SB}/fix`;
const PROF = `${FIX}/profiles/web`;
const DEP = `${FIX}/dep-src`;
mkdirSync(PROF, { recursive: true });
mkdirSync(DEP, { recursive: true });
const pkg = (o) => JSON.stringify(o, null, 2) + '\n';
writeFileSync(`${DEP}/package.json`, pkg({
  name: 'probe-dep', version: '1.0.0',
  scripts: { postinstall: 'node -e "require(\'fs\').writeFileSync(\'built.txt\',\'ok\')"' },
}));
process.env.DSH_HOME = FIX;

const mod = await import(pathToFileURL(`${SB}/core.mjs`).href);
const api = typeof mod.parseBlockedBuildDeps === 'function' ? mod : (mod.a ?? mod);
const {
  classifyFailReason, failReasonHint, parseBlockedBuildDeps, isBuildBlocked,
  isBuildPolicyBlocked, isRealPrepareFailure, appendAllowBuilds,
  prepareIsolatedPnpmConfig, fixBlockedBuilds, profileDir, dshHome,
} = api;

// ---------- A. classification covers every stage ---------------------------
const HINT_LINE = 'allowBuilds:\n  probe-dep@file:../dep-src: true\n';
const GIT_BLOCK = `[ERR_PNPM_GIT_DEP_PREPARE_NOT_ALLOWED] The git-hosted package "pkg@1.0.0" needs to execute build scripts but is not in the "allowBuilds" allowlist.\n${HINT_LINE}`;
const IGNORED = `[ERR_PNPM_IGNORED_BUILDS] Ignored build scripts: esbuild@0.25.0\nRun "pnpm approve-builds" to pick which dependencies should be allowed to run scripts.`;
const NESTED_BLOCK = `...npm-install: > plugin@1.0.0 prepare\n...npm-install: [ERR_PNPM_IGNORED_BUILDS] Ignored build scripts: esbuild@0.25.0\n[ERR_PNPM_PREPARE_PACKAGE] Failed to prepare git-hosted package`;
const REAL_PREPARE = `> pkg@1.0.0 prepare\n> tsdown\nsh: tsdown: command not found\n[ERR_PNPM_PREPARE_PACKAGE] Failed to prepare`;
const NETWORK = `fatal: unable to access 'https://github.com/x/y/': Could not resolve host: github.com`;
const NPM404 = `[ERR_PNPM_FETCH_404] GET https://registry.npmjs.org/nope: Not Found - 404`;
const VERIFY = `安装产物校验失败：x 未正确安装到 profile（候选检查: x:missing），已自动回滚。`;
const WEIRD = `something entirely unexpected happened`;

const cases = [
  ['pnpm policy (IGNORED_BUILDS)', IGNORED, true, true, 'pnpm-build-policy'],
  ['pnpm policy (git prepare not allowed)', GIT_BLOCK, false, true, 'pnpm-build-policy'],
  ['pnpm policy (nested in prepare)', NESTED_BLOCK, true, true, 'pnpm-build-policy'],
  ['real upstream prepare failure', REAL_PREPARE, false, true, 'github-prepare-failed'],
  ['github network failure', NETWORK, false, true, 'github-network'],
  ['npm 404', NPM404, true, false, 'npm-not-found'],
  ['verify failed + rolled back', VERIFY, true, true, 'verify-failed'],
  ['genuinely unknown', WEIRD, false, false, 'unknown'],
];
let allOk = true;
for (const [label, out, npmTried, ghTried, want] of cases) {
  const got = classifyFailReason(out, npmTried, ghTried);
  const ok = got === want;
  if (!ok) allOk = false;
  check(`classify: ${label} -> ${want}`, ok, ok ? '' : `got ${got}`);
}
check('classification: no stage falls through to unknown when identifiable', allOk);

// every reason has a distinct, non-empty hint
const reasons = ['blocked', 'pnpm-build-policy', 'prepare-failed', 'npm-not-found', 'npm-install-failed',
  'github-network', 'github-prepare-failed', 'github-install-failed', 'verify-failed', 'restart-required'];
const hints = reasons.map((r) => failReasonHint(r));
check('every fail reason has a non-empty hint', hints.every((h) => typeof h === 'string' && h.length > 0));
check('unknown hint tells the user what to do instead of hiding the cause',
  /日志|重试/.test(failReasonHint('unknown')), failReasonHint('unknown').slice(0, 40));

// ---------- B. signal detection -------------------------------------------
check('isBuildBlocked: IGNORED_BUILDS + git-not-allowed', isBuildBlocked(IGNORED) && isBuildBlocked(GIT_BLOCK));
check('isBuildPolicyBlocked: also covers the prepare-wrapped nested case',
  isBuildPolicyBlocked(NESTED_BLOCK) && isBuildPolicyBlocked(IGNORED));
check('isRealPrepareFailure: true for genuine build error, false for policy block',
  isRealPrepareFailure(REAL_PREPARE) && !isRealPrepareFailure(NESTED_BLOCK) && !isRealPrepareFailure(IGNORED));

// ---------- C. precise allowBuilds writer ----------------------------------
const wsPath = `${PROF}/pnpm-workspace.yaml`;
rmSync(wsPath, { force: true });
await appendAllowBuilds(wsPath, ['esbuild@0.25.0', 'sharp@0.33.4']);
const ws1 = readFileSync(wsPath, 'utf8');
check('writes precise depPath keys', ws1.includes("'esbuild@0.25.0': true") && ws1.includes("'sharp@0.33.4': true"));
check('single allowBuilds section', (ws1.match(/allowBuilds:/g) ?? []).length === 1);

// pnpm's own placeholder template must be upgraded, not duplicated
writeFileSync(wsPath, 'allowBuilds:\n  esbuild@0.25.0: set this to true or false\n');
await appendAllowBuilds(wsPath, ['esbuild@0.25.0']);
const ws2 = readFileSync(wsPath, 'utf8');
check('upgrades pnpm placeholder instead of duplicating the key',
  ws2.includes("'esbuild': true") || ws2.includes("'esbuild@0.25.0': true"),
  ws2.replace(/\s+/g, ' ').trim());
check('no leftover placeholder text', !ws2.includes('set this to true or false'));

// idempotent
await appendAllowBuilds(wsPath, ['esbuild@0.25.0']);
const ws3 = readFileSync(wsPath, 'utf8');
check('repeated allowBuilds writes are idempotent', ws3 === ws2);
// existing unrelated config is preserved
writeFileSync(wsPath, 'packages:\n  - .\nnodeLinker: hoisted\n');
await appendAllowBuilds(wsPath, ['x@1.0.0']);
const ws4 = readFileSync(wsPath, 'utf8');
check('preserves unrelated workspace config',
  ws4.includes('nodeLinker: hoisted') && ws4.includes("'x@1.0.0': true"), ws4.replace(/\s+/g, ' ').trim());

// ---------- D. isolated config ---------------------------------------------
const isoDir = `${FIX}/iso-probe`;
const prepared = await prepareIsolatedPnpmConfig(isoDir, ['esbuild@0.25.0'], 'names');
const cfgPath = `${isoDir}/pnpm/config.yaml`;
check('isolated config created at <dir>/pnpm/config.yaml', prepared === isoDir && existsSync(cfgPath));
const cfgText = readFileSync(cfgPath, 'utf8');
check('precise mode allows only the named package, not everything',
  /allowBuilds:/.test(cfgText) && cfgText.includes('esbuild') && !/dangerouslyAllowAllBuilds/.test(cfgText),
  cfgText.replace(/\s+/g, ' ').trim().slice(0, 120));
const isoAll = `${FIX}/iso-probe-all`;
await prepareIsolatedPnpmConfig(isoAll, ['esbuild@0.25.0'], 'all');
const cfgAll = readFileSync(`${isoAll}/pnpm/config.yaml`, 'utf8');
check('last-resort mode is allow-all, still inside the throwaway dir',
  /dangerouslyAllowAllBuilds:\s*true/.test(cfgAll) && cfgAll.includes('esbuild'));
check('isolated config is scoped by XDG_CONFIG_HOME only (no user global write)',
  !existsSync('C:/Users/ROG/AppData/Local/pnpm/config/config.yaml'));

// ---------- E. end-to-end auto-unblock with real pnpm ----------------------
const resetProfile = () => {
  rmSync(`${PROF}/node_modules`, { recursive: true, force: true });
  rmSync(`${PROF}/pnpm-lock.yaml`, { force: true });
  rmSync(`${PROF}/pnpm-workspace.yaml`, { force: true });
  writeFileSync(`${PROF}/package.json`, pkg({
    name: 'web', version: '1.0.0', dependencies: { 'probe-dep': 'file:../../dep-src' },
  }));
};
const pnpmInstall = (env) => new Promise((resolve) => {
  const r = spawnSync('pnpm', ['install'], { cwd: PROF, env: { ...process.env, ...(env ?? {}) }, encoding: 'utf8', shell: true });
  resolve({ code: r.status ?? -1, output: `${r.stdout ?? ''}${r.stderr ?? ''}` });
});
let isolatedUsed = false;
let isolatedDirDuringRun = null;
globalThis.__fixtureInstall = (spawn, source, profile, env) => {
  if (env && env.XDG_CONFIG_HOME) {
    isolatedUsed = true;
    isolatedDirDuringRun = env.XDG_CONFIG_HOME;
  }
  return pnpmInstall(env);
};

resetProfile();
const before = await pnpmInstall();
check('fixture: pnpm 11 blocks the build script', isBuildBlocked(before.output) && before.code !== 0,
  (before.output.match(/Ignored build scripts:[^\n]*/) ?? ['-'])[0].trim());

const fixed = await fixBlockedBuilds(
  'probe-dep@file:../../dep-src', 'web',
  ['plugin', '--profile', 'web', 'add', 'probe-dep@file:../../dep-src'],
  undefined, before.output, 'probe-dep@file:../../dep-src',
);
check('auto-unblock succeeds with NO user action', fixed?.code === 0, `code=${fixed?.code}`);
check('build script actually ran', existsSync(`${PROF}/node_modules/probe-dep/built.txt`));
const wsAfter = readFileSync(`${PROF}/pnpm-workspace.yaml`, 'utf8');
check('precise allowBuilds written for the exact depPath', wsAfter.includes("'probe-dep@file:../../dep-src': true"));
check('stage 1 alone was enough (allow-all not needed)', !isolatedUsed, `isolatedUsed=${isolatedUsed}`);
check('no isolated config dir left behind', !existsSync(`${FIX}/dsh-workshop`) ||
  readdirSync(`${FIX}/dsh-workshop`).filter((n) => n.startsWith('tmp-config-')).length === 0);

// ---------- E2. nested-policy path escalates only when required ------------
let isoSeen = null;
globalThis.__fixtureInstall = (spawn, source, profile, env) => new Promise((resolve) => {
  const hasIso = Boolean(env && env.XDG_CONFIG_HOME);
  if (hasIso) isoSeen = env.XDG_CONFIG_HOME;
  // policy-blocked unless the isolated config is in play (mimics a nested prepare
  // install that cannot see the profile's pnpm-workspace.yaml)
  resolve({ code: hasIso ? 0 : 1, output: hasIso ? 'Done' : NESTED_BLOCK });
});
const fixed2 = await fixBlockedBuilds('inner@1.0.0', 'web', ['plugin', '--profile', 'web', 'add', 'x'],
  undefined, NESTED_BLOCK, 'inner@1.0.0');
check('nested prepare policy block escalates to the isolated config', isoSeen !== null && fixed2?.code === 0, `iso=${isoSeen}`);
check('isolated config used for the retry is removed afterwards',
  isoSeen !== null && !existsSync(isoSeen), `left=${isoSeen && existsSync(isoSeen)}`);
check('no leftover temp dirs after escalation',
  !existsSync(`${FIX}/dsh-workshop`) ||
  readdirSync(`${FIX}/dsh-workshop`).filter((n) => n.startsWith('tmp-config-')).length === 0);

// ---------- F. preserved mechanisms ----------------------------------------
const watched = readFileSync(SRC, 'utf8');
check('preserved: WEB_PROFILE_BLOCKLIST still present', watched.includes('WEB_PROFILE_BLOCKLIST'));
check('preserved: CORE_REPO_BLOCKLIST still present', watched.includes('CORE_REPO_BLOCKLIST'));
check('preserved: DANGER_PATCH_IDS still present', watched.includes('DANGER_PATCH_IDS'));
check('preserved: rollback call inside verify', watched.includes('await uninstallPlugin(depKey, profile, env);'));
check('preserved: mirror fallback (mirrorEnvFor) intact', watched.includes('async function mirrorEnvFor'));
check('preserved: restart mechanism (markPendingRestart) intact', watched.includes('function markPendingRestart'));
check('preserved: progress reporting intact', watched.includes('function finishProgress'));
check('preserved: npm-first flow with github fallback intact',
  watched.includes('npmPackageExists') && watched.includes('const gitSource = '));
check('blocked policy result now carries failReason', watched.includes('failReason: "blocked"'));
check('verify rollback result now carries failReason', watched.includes('failReason: "verify-failed"'));

const failed = results.filter((r) => !r.ok);
console.log(`\n${results.length - failed.length}/${results.length} checks passed`);
process.exit(failed.length ? 1 : 0);
