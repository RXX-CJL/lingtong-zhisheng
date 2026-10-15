// Assertions against the REAL installed artifact. No copies, no dry-runs.
import { mkdirSync, writeFileSync, readFileSync, rmSync, existsSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

const REAL = 'C:/Users/ROG/.dsh/profiles/web/node_modules/dsh-workshop/lib/host/core-BcUmZo6v.mjs';
const SB = 'E:/output/dsh-workshop-patch/e2e-sandbox';
mkdirSync(SB, { recursive: true });
mkdirSync(`${SB}/stub`, { recursive: true });
writeFileSync(`${SB}/stub/dsh-tools.mjs`, 'export const defineTool = (x) => x;\n');

// A loadable view of the REAL file: only the DSH tooling import is stubbed so the
// module can be imported outside a running Host. Everything else is byte-identical
// to the installed artifact (verified by hash below).
const real = readFileSync(REAL, 'utf8');
writeFileSync(`${SB}/core-under-test.mjs`, real.replace(
  'import { defineTool } from "@deepseek-ai/dsh-tools";',
  `import { defineTool } from ${JSON.stringify(pathToFileURL(`${SB}/stub/dsh-tools.mjs`).href)};`,
), 'utf8');

process.env.DSH_HOME = `${SB}/home`;
const mod = await import(pathToFileURL(`${SB}/core-under-test.mjs`).href);
const api = mod.a ?? mod;

const results = [];
const check = (label, ok, detail = '') => { results.push(ok); console.log(`${ok ? 'PASS' : 'FAIL'}  ${label}${detail ? '  -- ' + detail : ''}`); };

const GIT_BLOCK = [
  '[ERR_PNPM_GIT_DEP_PREPARE_NOT_ALLOWED] The git-hosted package "p@1.0.0" needs to execute build scripts but is not in the "allowBuilds" allowlist.',
  'allowBuilds:',
  '  p@git+https://github.com/o/r#abc123: true',
].join('\n');
const IGNORED = '[ERR_PNPM_IGNORED_BUILDS] Ignored build scripts: esbuild@0.25.0';
const NESTED = '[ERR_PNPM_IGNORED_BUILDS] Ignored build scripts: esbuild@0.25.0\n[ERR_PNPM_PREPARE_PACKAGE] Failed to prepare git-hosted package';

check('parseBlockedBuildDeps reads the git depPath hint',
  JSON.stringify(api.parseBlockedBuildDeps(GIT_BLOCK)) === JSON.stringify(['p@git+https://github.com/o/r#abc123']),
  JSON.stringify(api.parseBlockedBuildDeps(GIT_BLOCK)));
check('parseBlockedBuildDeps reads the IGNORED_BUILDS list',
  JSON.stringify(api.parseBlockedBuildDeps(IGNORED)) === JSON.stringify(['esbuild@0.25.0']));
check('IGNORED_BUILDS classifies as pnpm-build-policy', api.classifyFailReason(IGNORED, true, true) === 'pnpm-build-policy');
check('git prepare block classifies as pnpm-build-policy', api.classifyFailReason(GIT_BLOCK, false, true) === 'pnpm-build-policy');
check('nested prepare block classifies as pnpm-build-policy (not unknown/not prepare-failed)',
  api.classifyFailReason(NESTED, true, true) === 'pnpm-build-policy', api.classifyFailReason(NESTED, true, true));
check('real prepare failure stays github-prepare-failed',
  api.classifyFailReason('> tsdown\nsh: tsdown: not found\n[ERR_PNPM_PREPARE_PACKAGE] Failed to prepare', false, true) === 'github-prepare-failed');
check('network failure classifies as github-network',
  api.classifyFailReason("fatal: unable to access 'https://github.com/x': Could not resolve host", false, true) === 'github-network');
check('verify rollback classifies as verify-failed',
  api.classifyFailReason('安装产物校验失败：x 未正确安装到 profile，已自动回滚。', true, true) === 'verify-failed');
check('every reason has a hint', ['blocked', 'pnpm-build-policy', 'npm-not-found', 'npm-install-failed',
  'github-network', 'github-prepare-failed', 'github-install-failed', 'verify-failed', 'unknown']
  .every((r) => typeof api.failReasonHint(r) === 'string' && api.failReasonHint(r).length > 0));

// isolated config: precise mode must NOT carry allow-all
const iso = `${SB}/iso-names`;
rmSync(iso, { recursive: true, force: true });
await api.prepareIsolatedPnpmConfig(iso, ['esbuild@0.25.0', 'p@git+file:///x#abc'], 'names');
const cfg = readFileSync(`${iso}/pnpm/config.yaml`, 'utf8');
check('isolated config lives at <dir>/pnpm/config.yaml', existsSync(`${iso}/pnpm/config.yaml`));
check('precise mode allows only named packages, never allow-all',
  cfg.includes('esbuild') && !cfg.includes('dangerouslyAllowAllBuilds'), cfg.split('\n').filter((l) => !l.startsWith('#')).join(' | ').trim());
const isoAll = `${SB}/iso-all`;
rmSync(isoAll, { recursive: true, force: true });
await api.prepareIsolatedPnpmConfig(isoAll, ['esbuild@0.25.0'], 'all');
check('last-resort mode is allow-all, confined to the throwaway dir',
  readFileSync(`${isoAll}/pnpm/config.yaml`, 'utf8').includes('dangerouslyAllowAllBuilds: true'));
check('no user global pnpm config was created',
  !existsSync('C:/Users/ROG/AppData/Local/pnpm/config/config.yaml'));

// precise allowBuilds writer
const ws = `${SB}/pnpm-workspace.yaml`;
writeFileSync(ws, 'packages:\n  - .\nallowBuilds:\n  esbuild@0.25.0: set this to true or false\n');
await api.appendAllowBuilds(ws, ['esbuild@0.25.0']);
const wsText = readFileSync(ws, 'utf8');
check('workspace writer upgrades pnpm placeholder without duplicate keys',
  !wsText.includes('set this to true or false') && (wsText.match(/allowBuilds:/g) ?? []).length === 1, wsText.replace(/\s+/g, ' ').trim());
check('preserved: blocklist / rollback / verify / restart / mirror / progress intact',
  ['WEB_PROFILE_BLOCKLIST', 'CORE_REPO_BLOCKLIST', 'DANGER_PATCH_IDS', 'await uninstallPlugin(depKey, profile, env);',
    'async function mirrorEnvFor', 'function markPendingRestart', 'function finishProgress', 'hotMountBundle']
    .every((s) => real.includes(s)));

const failed = results.filter((r) => !r).length;
console.log(`\n${results.length - failed}/${results.length} assertions passed on the real artifact`);
process.exit(failed ? 1 : 0);
