// Verify the patched dsh-workshop installer:
//   A. parseBlockedBuildDeps against REAL pnpm 11.7.0 error output
//   B. fixBlockedBuilds end-to-end on a real pnpm fixture (precise allowBuilds + retry)
//   C. escalation path for a nested install the precise key cannot reach
//   D. failure-stage classification
import { mkdirSync, writeFileSync, readFileSync, rmSync, existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';

const PATCH = 'E:/output/dsh-workshop-patch';
const SANDBOX = `${PATCH}/verify-sandbox`;
const SRC = process.argv[2] ?? 'C:/Users/ROG/.dsh/profiles/web/node_modules/dsh-workshop/lib/host/core-BcUmZo6v.mjs';
console.log('verifying:', SRC);

const results = [];
const check = (label, ok, detail = '') => {
  results.push({ label, ok });
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${label}${detail ? '  -- ' + detail : ''}`);
};

// ---------- fixture layout: <FIX>/profiles/web is the pnpm project root -------
const FIX = `${SANDBOX}/fixture`;
const DEP = `${FIX}/dep-src`;          // the dependency whose build script is blocked
const APPDIR = `${FIX}/app-src`;       // holds package.json + dep, linked into the profile
rmSync(SANDBOX, { recursive: true, force: true });
mkdirSync(`${SANDBOX}/stub`, { recursive: true });
mkdirSync(DEP, { recursive: true });
mkdirSync(APPDIR, { recursive: true });

writeFileSync(`${DEP}/package.json`, JSON.stringify({
  name: 'probe-dep', version: '1.0.0',
  scripts: { postinstall: 'node -e "require(\'fs\').writeFileSync(\'built.txt\',\'ok\')"' },
}, null, 2) + '\n');
writeFileSync(`${APPDIR}/package.json`, JSON.stringify({
  name: 'probe-app', version: '1.0.0',
  dependencies: { 'probe-dep': 'file:../../dep-src' },
}, null, 2) + '\n');

// ---------- build a loadable copy of the patched module ----------------------
let core = readFileSync(SRC, 'utf8');
writeFileSync(`${SANDBOX}/stub/dsh-tools.mjs`, 'export const defineTool = (x) => x;\n');
core = core.replace(
  'import { defineTool } from "@deepseek-ai/dsh-tools";',
  `import { defineTool } from ${JSON.stringify(pathToFileURL(`${SANDBOX}/stub/dsh-tools.mjs`).href)};`,
);
core = core.replace(
  /async function installPlugin\(source, profile = "web", env\) \{[\s\S]*?\n\}/,
  `async function installPlugin(source, profile = "web", env) {
	return await globalThis.__fixtureInstall(spawn, source, profile, env);
}`,
);
writeFileSync(`${SANDBOX}/core.mjs`, core, 'utf8');

process.env.DSH_HOME = FIX;
const mod = await import(pathToFileURL(`${SANDBOX}/core.mjs`).href);
const core2 = typeof mod.parseBlockedBuildDeps === 'function' ? mod
  : (typeof mod.a?.parseBlockedBuildDeps === 'function' ? mod.a
    : (typeof mod.default?.parseBlockedBuildDeps === 'function' ? mod.default : mod));
const { parseBlockedBuildDeps, isBuildBlocked, fixBlockedBuilds, classifyFailReason } = core2;
check('patched module loads and exports the new helpers',
  typeof parseBlockedBuildDeps === 'function' && typeof isBuildBlocked === 'function' && typeof fixBlockedBuilds === 'function');

// ---------- A. parser against real pnpm output ------------------------------
const REAL_IGNORED = `Progress: resolved 1, reused 1, downloaded 0, added 1, done
[ERR_PNPM_IGNORED_BUILDS] Ignored build scripts: probe-dep@file:../dep-src

Run "pnpm approve-builds" to pick which dependencies should be allowed to run scripts.
`;
const REAL_GIT = `[ERR_PNPM_GIT_DEP_PREPARE_NOT_ALLOWED] Failed to prepare git-hosted package fetched from "file:///E:/x/git-dep3": The git-hosted package "git-probe3@1.0.0" needs to execute build scripts but is not in the "allowBuilds" allowlist.
Add the package to "allowBuilds" in your project's pnpm-workspace.yaml to allow it to run scripts. For example:
allowBuilds:
  git-probe3@git+file:///E:/output/x/git-dep3#7cd812602ec3c111635f87d6fd9d222642f30ede: true
`;
const REAL_MULTI = `[ERR_PNPM_IGNORED_BUILDS] Ignored build scripts: esbuild@0.21.5, sharp@0.33.4
allowBuilds: { esbuild@0.21.5: true, sharp@0.33.4: true }
`;
check('parses ERR_PNPM_IGNORED_BUILDS list',
  JSON.stringify(parseBlockedBuildDeps(REAL_IGNORED)) === JSON.stringify(['probe-dep@file:../dep-src']),
  JSON.stringify(parseBlockedBuildDeps(REAL_IGNORED)));
check('parses git-dep hint into the exact depPath key',
  JSON.stringify(parseBlockedBuildDeps(REAL_GIT)) === JSON.stringify(['git-probe3@git+file:///E:/output/x/git-dep3#7cd812602ec3c111635f87d6fd9d222642f30ede']),
  JSON.stringify(parseBlockedBuildDeps(REAL_GIT)));
check('parses comma list + inline mapping without duplicates',
  JSON.stringify(parseBlockedBuildDeps(REAL_MULTI)) === JSON.stringify(['esbuild@0.21.5', 'sharp@0.33.4']),
  JSON.stringify(parseBlockedBuildDeps(REAL_MULTI)));
check('isBuildBlocked detects both error codes',
  isBuildBlocked(REAL_IGNORED) && isBuildBlocked(REAL_GIT) && !isBuildBlocked('ERR_PNPM_FETCH_404'));

// ---------- D. failure classification ---------------------------------------
check('classify: blocked stage instead of unknown',
  classifyFailReason(REAL_GIT, false, true) === 'blocked'
  && classifyFailReason(REAL_IGNORED, true, true) === 'blocked',
  classifyFailReason(REAL_GIT, false, true));
check('classify: real prepare failure still github-prepare-failed',
  classifyFailReason('ERR_PNPM_PREPARE_PACKAGE prepare Failed', false, true) === 'github-prepare-failed');
check('classify: network/git failure still github-network',
  classifyFailReason('fatal: unable to access repository', false, true) === 'github-network');

// ---------- B. end-to-end via the real profile directory --------------------
const PROF = `${FIX}/profiles/web`;
const resetProfile = () => {
  rmSync(`${PROF}/node_modules`, { recursive: true, force: true });
  rmSync(`${PROF}/pnpm-lock.yaml`, { force: true });
  rmSync(`${PROF}/pnpm-workspace.yaml`, { force: true });
  rmSync(`${PROF}/package.json`, { force: true });
  mkdirSync(PROF, { recursive: true });
  // the profile directly depends on the fixture dependency (mirrors the profile's
  // own package.json after `dsh plugin add`, minus the CLI plumbing)
  writeFileSync(`${PROF}/package.json`, JSON.stringify({
    name: 'web', version: '1.0.0',
    dependencies: { 'probe-dep': 'file:../../dep-src' },
  }, null, 2) + '\n');
};

const pnpmInstall = (cwd, env) => new Promise((resolve) => {
  const child = spawnSync('pnpm', ['install'], {
    cwd, env: { ...process.env, ...(env ?? {}) }, encoding: 'utf8', shell: true,
  });
  resolve({ code: child.status ?? -1, output: `${child.stdout ?? ''}${child.stderr ?? ''}` });
});
globalThis.__fixtureInstall = (spawn, source, profile, env) => pnpmInstall(PROF, env);

resetProfile();
const before = await pnpmInstall(PROF);
check('fixture reproduces the pnpm 11 block',
  isBuildBlocked(before.output) && !existsSync(`${PROF}/node_modules/probe-dep/built.txt`),
  (before.output.match(/Ignored build scripts:[^\n]*/) ?? ['(no block line)'])[0].trim());
// pnpm itself writes an allowBuilds placeholder template under strictDepBuilds;
// that is the input the fix must cope with, not a clean slate.
const placeholderWs = existsSync(`${PROF}/pnpm-workspace.yaml`)
  ? readFileSync(`${PROF}/pnpm-workspace.yaml`, 'utf8') : '';
check('pnpm wrote its own allowBuilds placeholder template',
  placeholderWs.includes('allowBuilds:') && placeholderWs.includes('set this to true or false'),
  placeholderWs.replace(/\s+/g, ' ').trim().slice(0, 90));

const retry = await fixBlockedBuilds(
  'probe-dep@file:../../dep-src', 'web',
  ['plugin', '--profile', 'web', 'add', 'probe-dep@file:../../dep-src'],
  undefined, before.output, 'probe-dep@file:../../dep-src',
);
const wsPath = `${PROF}/pnpm-workspace.yaml`;
const ws = existsSync(wsPath) ? readFileSync(wsPath, 'utf8') : '(missing)';
check('writes the profile-level pnpm-workspace.yaml', existsSync(wsPath));
check('uses the exact depPath key', ws.includes("'probe-dep@file:../../dep-src': true"));
check('placeholder value is upgraded to true (no duplicate mapping key)',
  !ws.includes('set this to true or false') && ws.includes("'probe-dep': true"),
  ws.replace(/\s+/g, ' ').trim());
check('no duplicated allowBuilds section', (ws.match(/allowBuilds:/g) ?? []).length === 1);
check('retry reports success', retry?.code === 0, `code=${retry?.code}`);
check('build script actually ran after the retry', existsSync(`${PROF}/node_modules/probe-dep/built.txt`));
check('no workspace file leaked into the dependency app dir', !existsSync(`${APPDIR}/pnpm-workspace.yaml`));
check('profile package.json dependency preserved',
  JSON.parse(readFileSync(`${PROF}/package.json`, 'utf8')).dependencies['probe-dep'] !== undefined);

// ---------- C. escalation path ---------------------------------------------
const NESTED = `${FIX}/profiles/web2`;
mkdirSync(NESTED, { recursive: true });
let sawEscalation = false;
let firstAttemptFailed = false;
globalThis.__fixtureInstall = (spawn, source, profile, env) => new Promise((resolve) => {
  const allowAll = String(env?.pnpm_config_dangerously_allow_all_builds ?? '') === 'true';
  if (allowAll) sawEscalation = true;
  else firstAttemptFailed = true;
  resolve({ code: allowAll ? 0 : 1, output: allowAll ? 'Done' : REAL_IGNORED });
});
const retry2 = await fixBlockedBuilds(
  'inner-dep@file:./inner', 'web2',
  ['plugin', '--profile', 'web2', 'add', 'x'],
  undefined, REAL_IGNORED, 'inner-dep@file:./inner',
);
check('precise attempt is tried first', firstAttemptFailed);
check('escalates to allow-all only when the precise key is not enough', sawEscalation);
check('escalated retry reports success', retry2?.code === 0);
const ws2 = `${NESTED}/pnpm-workspace.yaml`;
check('precise key was still written before escalating',
  existsSync(ws2) && readFileSync(ws2, 'utf8').includes("'inner-dep@file:./inner': true"));

const failed = results.filter((r) => !r.ok);
console.log(`\n${results.length - failed.length}/${results.length} checks passed`);
process.exit(failed.length ? 1 : 0);
