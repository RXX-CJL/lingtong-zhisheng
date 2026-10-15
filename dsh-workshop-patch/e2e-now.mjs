// ONE real install through the REAL patched installer, with the REAL dsh CLI.
// Target profile is a throwaway profile under the workspace; network goes through
// the same mirror the Workshop uses (direct github.com is blocked on this host).
import { mkdirSync, writeFileSync, readFileSync, rmSync, existsSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

const CORE = 'C:/Users/ROG/.dsh/profiles/web/node_modules/dsh-workshop/lib/host/core-BcUmZo6v.mjs';
const SB = 'E:/output/dsh-workshop-patch/e2e-now';
rmSync(SB, { recursive: true, force: true });
const HOME = `${SB}/home`;
const PROF = `${HOME}/profiles/web`;
mkdirSync(PROF, { recursive: true });
mkdirSync(`${SB}/stub`, { recursive: true });

writeFileSync(`${PROF}/package.json`, JSON.stringify({
  name: 'dsh-profile-web', private: true, dependencies: {},
  dsh: { profile: { bundles: ['@deepseek-ai/dsh-base', '@deepseek-ai/dsh-web-app'] } },
}, null, 2) + '\n');
writeFileSync(`${PROF}/cordis.yml`, '[]\n');
writeFileSync(`${PROF}/pnpm-workspace.yaml`, 'packages:\n  - .\n\nnodeLinker: hoisted\nautoInstallPeers: false\n');
writeFileSync(`${SB}/stub/dsh-tools.mjs`, 'export const defineTool = (x) => x;\n');

const real = readFileSync(CORE, 'utf8');
writeFileSync(`${SB}/core.mjs`, real.replace(
  'import { defineTool } from "@deepseek-ai/dsh-tools";',
  `import { defineTool } from ${JSON.stringify(pathToFileURL(`${SB}/stub/dsh-tools.mjs`).href)};`,
), 'utf8');

process.env.DSH_HOME = HOME;
process.env.DSH_PROFILE = 'web';
const api = (await import(pathToFileURL(`${SB}/core.mjs`).href)).a;

const SOURCE = process.argv[2];
console.log('source      :', SOURCE);
const res = await api.installPluginSmart(SOURCE, { profileName: 'web' }, 'web');
console.log('\n=== installer result ===');
console.log('code       :', res.code);
console.log('failReason :', res.failReason ?? null);
console.log('failHint   :', res.failHint ?? null);
console.log('hotMount   :', res.hotMount ?? null);

console.log('\n=== profile state ===');
console.log('dependencies:', readFileSync(`${PROF}/package.json`, 'utf8').match(/"dependencies"[\s\S]*?\}/)?.[0].replace(/\s+/g, ' '));
console.log('pnpm-workspace.yaml:');
console.log(readFileSync(`${PROF}/pnpm-workspace.yaml`, 'utf8').trim());
const nm = `${PROF}/node_modules`;
for (const d of ['dsh-open-design']) {
  console.log(`installed ${d}:`, existsSync(`${nm}/${d}/package.json`));
}
const tmpRoot = `${HOME}/dsh-workshop`;
const leftovers = existsSync(tmpRoot) ? readFileSync(tmpRoot, 'utf8') && null : null;
console.log('temp isolated config dirs:', existsSync(tmpRoot) ? 'DIR EXISTS' : 'none');
console.log('user global pnpm config  :', existsSync('C:/Users/ROG/AppData/Local/pnpm/config/config.yaml'));

if (res.code !== 0) {
  console.log('\n=== raw output tail ===');
  console.log(String(res.output ?? '').slice(-2500));
}
