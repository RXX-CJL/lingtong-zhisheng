// ONE real end-to-end install, driven by the REAL installed core module and the
// REAL `dsh plugin --profile web add` CLI path. The target profile is a throwaway
// profile under the workspace, so the user's real profile is never touched.
import { mkdirSync, writeFileSync, readFileSync, rmSync, existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';

const CORE = 'C:/Users/ROG/.dsh/profiles/web/node_modules/dsh-workshop/lib/host/core-BcUmZo6v.mjs';
const SB = 'E:/output/dsh-workshop-patch/e2e-auth';
rmSync(SB, { recursive: true, force: true });
const HOME = `${SB}/home`;
const PROF = `${HOME}/profiles/web`;
mkdirSync(`${PROF}`, { recursive: true });
mkdirSync(`${SB}/stub`, { recursive: true });

// minimal but faithful web profile: the same bundle layers the real one uses
writeFileSync(`${PROF}/package.json`, JSON.stringify({
  name: 'dsh-profile-web',
  private: true,
  dependencies: {},
  dsh: { profile: { bundles: ['@deepseek-ai/dsh-base', '@deepseek-ai/dsh-web-app'] } },
}, null, 2) + '\n');
writeFileSync(`${PROF}/cordis.yml`, '[]\n');
writeFileSync(`${PROF}/pnpm-workspace.yaml`, 'packages:\n  - .\n\nnodeLinker: hoisted\nautoInstallPeers: false\n');
writeFileSync(`${SB}/stub/dsh-tools.mjs`, 'export const defineTool = (x) => x;\n');

// load the REAL artifact (only the Host-tooling import is stubbed)
const real = readFileSync(CORE, 'utf8');
writeFileSync(`${SB}/core.mjs`, real.replace(
  'import { defineTool } from "@deepseek-ai/dsh-tools";',
  `import { defineTool } from ${JSON.stringify(pathToFileURL(`${SB}/stub/dsh-tools.mjs`).href)};`,
), 'utf8');

process.env.DSH_HOME = HOME;              // isolate the whole install to the throwaway profile
process.env.DSH_PROFILE = 'web';
const api = (await import(pathToFileURL(`${SB}/core.mjs`).href)).a;

const SOURCE = process.argv[2] ?? 'github:loguhan/dsh-workshop';
console.log('source      :', SOURCE);
console.log('target prof :', PROF);
console.log('global pnpm config exists before:', existsSync('C:/Users/ROG/AppData/Local/pnpm/config/config.yaml'));

const res = await api.installPluginSmart(SOURCE, { profileName: 'web' }, 'web');

console.log('\n=== result ===');
console.log(JSON.stringify({
  code: res.code,
  failReason: res.failReason ?? null,
  failHint: res.failHint ?? null,
  fallback: res.fallback ?? false,
  usedSource: res.usedSource ?? null,
  hotMount: res.hotMount ?? null,
}, null, 2));

console.log('\n=== evidence ===');
const wsPath = `${PROF}/pnpm-workspace.yaml`;
console.log('profile pnpm-workspace.yaml now:');
console.log(readFileSync(wsPath, 'utf8').trim());
const nm = `${PROF}/node_modules`;
const entries = existsSync(nm) ? readFileSync(`${nm}/.modules.yaml`, 'utf8').length && null : null;
const dep = JSON.parse(readFileSync(`${PROF}/package.json`, 'utf8')).dependencies ?? {};
console.log('profile dependencies:', JSON.stringify(dep));
for (const k of Object.keys(dep)) {
  const p = `${nm}/${k}/package.json`;
  console.log(`  ${k}: package.json present=${existsSync(p)}`);
}
console.log('temp isolated configs left:', existsSync(`${HOME}/dsh-workshop`)
  ? readFileSync(`${HOME}/dsh-workshop`, 'utf8') && 'dir exists'
  : 'none');
console.log('global pnpm config exists after :', existsSync('C:/Users/ROG/AppData/Local/pnpm/config/config.yaml'));
