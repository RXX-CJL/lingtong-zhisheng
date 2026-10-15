// Integration proof: drive the REAL patched installer against a REAL pnpm fixture
// where the plugin's own prepare script runs a nested `pnpm install` that pnpm 11
// blocks. The user must not be asked to do anything.
import { mkdirSync, writeFileSync, readFileSync, rmSync, existsSync, readdirSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';

const SRC = process.argv[2];
const SB = 'E:/output/dsh-workshop-patch/verify-v2-sandbox';
const FIX = `${SB}/fix`;
const PROF = `${FIX}/profiles/web`;
const results = [];
const check = (l, ok, d = '') => { results.push(ok); console.log(`${ok ? 'PASS' : 'FAIL'}  ${l}${d ? '  -- ' + d : ''}`); };
const pkg = (o) => JSON.stringify(o, null, 2) + '\n';

// --- a git plugin whose prepare runs a nested install that gets blocked -----
const GIT = `${SB}/git-plugin`;
rmSync(GIT, { recursive: true, force: true });
mkdirSync(`${GIT}/native`, { recursive: true });
writeFileSync(`${GIT}/native/package.json`, pkg({
  name: 'native-lib', version: '1.0.0',
  scripts: { postinstall: 'node -e "require(\'fs\').writeFileSync(\'native-built.txt\',\'ok\')"' },
}));
writeFileSync(`${GIT}/probe.cjs`, `
const fs = require('fs'), cp = require('child_process');
const r = cp.spawnSync('pnpm', ['install'], { cwd: __dirname, encoding: 'utf8', shell: true });
fs.writeFileSync('prepare-result.json', JSON.stringify({
  status: r.status,
  tail: ((r.stdout||'')+(r.stderr||'')).slice(-800),
  nativeBuilt: fs.existsSync(__dirname + '/native/node_modules/native-lib/native-built.txt'),
}, null, 2));
`);
writeFileSync(`${GIT}/package.json`, pkg({
  name: 'git-nested-plugin', version: '1.0.0',
  dependencies: { 'native-lib': 'file:./native' },
  scripts: { prepare: 'node probe.cjs' },
}));
for (const args of [['init', '-q'], ['add', '-A'], ['-c', 'user.email=t@t', '-c', 'user.name=t', 'commit', '-q', '-m', 'i']]) {
  spawnSync('git', args, { cwd: GIT, shell: true });
}
const GIT_URL = `git+file:///${GIT.replace(/\\/g, '/')}`;

// --- load the patched module against the fixture profile --------------------
let core = readFileSync(SRC, 'utf8');
core = core.replace(
  'import { defineTool } from "@deepseek-ai/dsh-tools";',
  `import { defineTool } from ${JSON.stringify(pathToFileURL(`${SB}/stub/dsh-tools.mjs`).href)};`,
);
// replace only the dsh-CLI transport: keep everything else (retry, allowBuilds, verify)
core = core.replace(
  /async function installPlugin\(source, profile = "web", env\) \{[\s\S]*?\n\}/,
  `async function installPlugin(source, profile = "web", env) {
	return await globalThis.__fixtureInstall(spawn, source, profile, env);
}`,
);
writeFileSync(`${SB}/core-int.mjs`, core, 'utf8');
process.env.DSH_HOME = FIX;

const mod = await import(pathToFileURL(`${SB}/core-int.mjs`).href);
const api = typeof mod.installPluginSmart === 'function' ? mod : (mod.a ?? mod);
const { installPluginSmart } = api;

// fixture transport: real pnpm inside the fixture profile
const isoDirsSeen = [];
const isoConfigs = [];
globalThis.__fixtureInstall = (spawn, source, profile, env) => new Promise((resolve) => {
  if (env && env.XDG_CONFIG_HOME) {
    isoDirsSeen.push(env.XDG_CONFIG_HOME);
    try { isoConfigs.push(readFileSync(`${env.XDG_CONFIG_HOME}/pnpm/config.yaml`, 'utf8')); } catch { isoConfigs.push('(unreadable)'); }
  }
  const r = spawnSync('pnpm', ['add', source], {
    cwd: PROF, env: { ...process.env, ...(env ?? {}) }, encoding: 'utf8', shell: true,
  });
  resolve({ code: r.status ?? -1, output: `${r.stdout ?? ''}${r.stderr ?? ''}` });
});

// reset the fixture profile
rmSync(`${PROF}/node_modules`, { recursive: true, force: true });
rmSync(`${PROF}/pnpm-lock.yaml`, { force: true });
rmSync(`${PROF}/pnpm-workspace.yaml`, { force: true });
rmSync(`${GIT}/prepare-result.json`, { force: true });
rmSync(`${GIT}/native/node_modules`, { recursive: true, force: true });
writeFileSync(`${PROF}/package.json`, pkg({ name: 'web', version: '1.0.0' }));

console.log('=== installing a git plugin whose prepare runs a blocked nested install ===');
const res = await installPluginSmart(GIT_URL, { profileName: 'web' }, 'web');
console.log('result code:', res.code, '| failReason:', res.failReason ?? '(none)');
console.log('isolated configs used:', isoConfigs.length);
for (const [i, cfg] of isoConfigs.entries()) {
  console.log(`  #${i}: ${cfg.split('\n').filter((l) => !l.startsWith('#')).join(' | ').trim() || '(empty)'}`);
}
if (res.code !== 0) {
  console.log('--- installer output tail ---');
  console.log(String(res.output ?? '').split('\n').slice(-20).join('\n'));
}

const installed = `${PROF}/node_modules/git-nested-plugin`;
check('installer reports success', res.code === 0, `code=${res.code} reason=${res.failReason ?? '-'}`);
check('plugin is present in the profile', existsSync(`${installed}/package.json`));
const pr = `${installed}/prepare-result.json`;
check('plugin prepare actually ran and completed', existsSync(pr) && JSON.parse(readFileSync(pr, 'utf8')).status === 0);
if (existsSync(pr)) {
  const j = JSON.parse(readFileSync(pr, 'utf8'));
  check('nested install inside prepare was unblocked', j.nativeBuilt === true, `nativeBuilt=${j.nativeBuilt}`);
}
check('auto-repair wrote precise allowBuilds into the profile workspace',
  existsSync(`${PROF}/pnpm-workspace.yaml`) &&
  readFileSync(`${PROF}/pnpm-workspace.yaml`, 'utf8').includes('git-nested-plugin'));
check('escalation used an isolated pnpm config', isoDirsSeen.length > 0, `n=${isoDirsSeen.length}`);
check('all isolated config dirs were cleaned up', isoDirsSeen.every((d) => !existsSync(d)));
check('no temp-config dirs left in DSH_HOME', !existsSync(`${FIX}/dsh-workshop`) ||
  readdirSync(`${FIX}/dsh-workshop`).filter((n) => n.startsWith('tmp-config-')).length === 0);
check('user global pnpm config untouched', !existsSync('C:/Users/ROG/AppData/Local/pnpm/config/config.yaml'));

// failure classification on a plugin that cannot be installed at all
const bad = await installPluginSmart('github:deepseek-ai/deepseek-harness', { profileName: 'web' }, 'web');
check('web-compatibility blocklist still rejects core repo with a visible reason',
  bad.code !== 0 && bad.failReason === 'blocked', `reason=${bad.failReason}`);

const failed = results.filter((r) => !r).length;
console.log(`\n${results.length - failed}/${results.length} checks passed`);
process.exit(failed ? 1 : 0);
