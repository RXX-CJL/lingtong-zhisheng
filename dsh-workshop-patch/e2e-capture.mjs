// Capture the real output of one installer run (bounded: no new strategy, just the error text).
import { mkdirSync, writeFileSync, readFileSync, rmSync, existsSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

const SB = 'E:/output/dsh-workshop-patch/e2e-sandbox';
rmSync(SB, { recursive: true, force: true });
mkdirSync(`${SB}/stub`, { recursive: true });
mkdirSync(`${SB}/bin`, { recursive: true });
writeFileSync(`${SB}/stub/dsh-tools.mjs`, 'export const defineTool = (x) => x;\n');

writeFileSync(`${SB}/bin/npx.cmd`, `@echo off\r\nnode "%~dp0npx" %*\r\n`, 'utf8');
writeFileSync(`${SB}/bin/npx`, `#!/usr/bin/env node
const { mkdirSync, writeFileSync } = require('node:fs');
const { join } = require('node:path');
const argv = process.argv.slice(2);
const profile = argv[argv.indexOf('--profile') + 1] || 'web';
const profileDir = join(process.env.DSH_HOME, 'profiles', profile);
const isolated = Boolean(process.env.XDG_CONFIG_HOME);
mkdirSync(profileDir, { recursive: true });
if (isolated) {
  writeFileSync(join(profileDir, 'install-ran.txt'), 'isolated\\n');
  const pkgDir = join(profileDir, 'node_modules', 'probe-plugin');
  mkdirSync(pkgDir, { recursive: true });
  writeFileSync(join(pkgDir, 'package.json'), JSON.stringify({ name: 'probe-plugin', version: '1.0.0' }, null, 2));
  process.stdout.write('+ probe-plugin 1.0.0\\nDone\\n');
  process.exit(0);
}
process.stdout.write('[ERR_PNPM_IGNORED_BUILDS] Ignored build scripts: esbuild@0.25.0\\n');
process.exit(1);
`, 'utf8');

const real = readFileSync('C:/Users/ROG/.dsh/profiles/web/node_modules/dsh-workshop/lib/host/core-BcUmZo6v.mjs', 'utf8');
writeFileSync(`${SB}/core.mjs`, real.replace(
  'import { defineTool } from "@deepseek-ai/dsh-tools";',
  `import { defineTool } from ${JSON.stringify(pathToFileURL(`${SB}/stub/dsh-tools.mjs`).href)};`,
), 'utf8');

const HOME = `${SB}/home`;
mkdirSync(`${HOME}/profiles/web`, { recursive: true });
writeFileSync(`${HOME}/profiles/web/package.json`, JSON.stringify({ name: 'web', version: '1.0.0' }, null, 2));
writeFileSync(`${HOME}/profiles/web/pnpm-workspace.yaml`, 'packages:\n  - .\n');

process.env.E2E_MARKER = '1';
process.env.DSH_HOME = HOME;
process.env.PATH = `${SB}/bin;${process.env.PATH}`;

const api = (await import(pathToFileURL(`${SB}/core.mjs`).href)).a;
const res = await api.installPluginSmart('github:example/probe-plugin', { profileName: 'web' }, 'web');
console.log('code:', res.code, '| failReason:', res.failReason ?? null);
console.log('--- raw output ---');
console.log(String(res.output ?? ''));
console.log('--- markers ---');
console.log('install-ran.txt:', existsSync(`${HOME}/profiles/web/install-ran.txt`));
console.log('workspace allowBuilds present:', readFileSync(`${HOME}/profiles/web/pnpm-workspace.yaml`, 'utf8').includes('allowBuilds'));
