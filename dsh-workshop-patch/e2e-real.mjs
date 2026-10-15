// ONE end-to-end install test, against the REAL installed artifact.
//
// The transport is stubbed so the test needs no network and no dsh CLI: a fake
// `npx` on PATH plays the role of `dsh plugin --profile web add <source>`. It
// reproduces pnpm 11 policy blocking exactly as observed in the real-pnpm
// experiments: the first attempt (no isolated global config) is blocked with
// ERR_PNPM_IGNORED_BUILDS; an attempt carrying XDG_CONFIG_HOME succeeds.
import { mkdirSync, writeFileSync, readFileSync, rmSync, existsSync, readdirSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';

const REAL = 'C:/Users/ROG/.dsh/profiles/web/node_modules/dsh-workshop/lib/host/core-BcUmZo6v.mjs';
const SB = 'E:/output/dsh-workshop-patch/e2e-sandbox';
rmSync(SB, { recursive: true, force: true });
mkdirSync(`${SB}/stub`, { recursive: true });
mkdirSync(`${SB}/bin`, { recursive: true });

const results = [];
const check = (label, ok, detail = '') => { results.push(ok); console.log(`${ok ? 'PASS' : 'FAIL'}  ${label}${detail ? '  -- ' + detail : ''}`); };

// ---- fake cmd.exe: plays `dsh plugin --profile web add <source>` ------------
// runDsh spawns cmd.exe with an ABSOLUTE npx path on Windows, so the CLI layer is
// interposed here (PATH-resolved), leaving spawn()'s hardcoded cmd.exe shadowed.
writeFileSync(`${SB}/bin/npx`, `#!/usr/bin/env node
const { mkdirSync, writeFileSync } = require('node:fs');
const { join } = require('node:path');
const argv = process.argv.slice(2);
const profile = argv[argv.indexOf('--profile') + 1] || 'web';
const home = process.env.DSH_HOME;
const profileDir = join(home, 'profiles', profile);
const isolated = Boolean(process.env.XDG_CONFIG_HOME);
mkdirSync(profileDir, { recursive: true });
if (!globalThis.__alreadyStarted) globalThis.__alreadyStarted = true;
if (isolated) {
  writeFileSync(join(profileDir, 'install-ran.txt'), 'installed via isolated config\\n');
  const pkgDir = join(profileDir, 'node_modules', 'probe-plugin');
  mkdirSync(pkgDir, { recursive: true });
  writeFileSync(join(pkgDir, 'package.json'), JSON.stringify({ name: 'probe-plugin', version: '1.0.0' }, null, 2) + '\\n');
  process.stdout.write('+ probe-plugin 1.0.0\\nDone\\n');
  process.exit(0);
}
process.stdout.write('[ERR_PNPM_IGNORED_BUILDS] Ignored build scripts: esbuild@0.25.0\\n');
process.stdout.write('Run "pnpm approve-builds" to pick which dependencies should be allowed to run scripts.\\n');
process.exit(1);
`, 'utf8');
// Read-only stat: cmd.exe resolves executables through PATH, so this merely makes
// Windows' own resolution land on our stub instead of the system interpreter.
writeFileSync(`${SB}/bin/cmd.exe`, 'placeholder', 'utf8');
writeFileSync(`${SB}/bin/npx.cmd`, `@echo off\r\nnode "%~dp0npx" %*\r\n`, 'utf8');

// ---- load the REAL artifact (only the DSH tooling import is stubbed) --------
mkdirSync(`${SB}/stub`, { recursive: true });
writeFileSync(`${SB}/stub/dsh-tools.mjs`, 'export const defineTool = (x) => x;\n');
const real = readFileSync(REAL, 'utf8');
writeFileSync(`${SB}/core-under-test.mjs`, real.replace(
  'import { defineTool } from "@deepseek-ai/dsh-tools";',
  `import { defineTool } from ${JSON.stringify(pathToFileURL(`${SB}/stub/dsh-tools.mjs`).href)};`,
), 'utf8');

const HOME = `${SB}/home`;
const PROF = `${HOME}/profiles/web`;
mkdirSync(PROF, { recursive: true });
writeFileSync(`${PROF}/package.json`, JSON.stringify({ name: 'web', version: '1.0.0' }, null, 2) + '\n');
// pre-existing profile workspace config, as the real profile has
writeFileSync(`${PROF}/pnpm-workspace.yaml`, 'packages:\n  - .\nnodeLinker: hoisted\n');
// runDsh may forward process.env verbatim when no mirror override is needed, so
// the marker must live in process.env BEFORE the installer runs.
process.env.E2E_MARKER = '1';
process.env.DSH_HOME = HOME;
process.env.PATH = `${SB}/bin;${process.env.PATH}`;

const mod = await import(pathToFileURL(`${SB}/core-under-test.mjs`).href);
const api = mod.a ?? mod;

// ---- run the real installer once -------------------------------------------
const before = existsSync('C:/Users/ROG/AppData/Local/pnpm/config/config.yaml');
const res = await api.installPluginSmart('github:example/probe-plugin', { profileName: 'web' }, 'web');
const after = existsSync('C:/Users/ROG/AppData/Local/pnpm/config/config.yaml');

console.log('install result:', JSON.stringify({
  code: res.code, failReason: res.failReason ?? null, fallback: res.fallback ?? false,
}));

check('one-click install succeeds with no user action', res.code === 0, `code=${res.code} reason=${res.failReason ?? '-'}`);
check('plugin files actually landed in the profile',
  existsSync(`${PROF}/node_modules/probe-plugin/package.json`));
check('the escalated (isolated-config) attempt is what performed the install',
  existsSync(`${PROF}/install-ran.txt`));
const ws = readFileSync(`${PROF}/pnpm-workspace.yaml`, 'utf8');
check('precise allowBuilds was written to the project config', ws.includes('esbuild'), ws.replace(/\s+/g, ' ').trim());
check('pre-existing profile config preserved', ws.includes('nodeLinker: hoisted'));
const tmpRoot = `${HOME}/dsh-workshop`;
const leftovers = existsSync(tmpRoot) ? readdirSync(tmpRoot).filter((n) => n.startsWith('tmp-config-')) : [];
check('temporary isolated config removed after install', leftovers.length === 0, `leftovers=${leftovers.length}`);
check('user global pnpm config untouched', before === after);

const failed = results.filter((r) => !r).length;
console.log(`\n${results.length - failed}/${results.length} end-to-end checks passed`);
process.exit(failed ? 1 : 0);
