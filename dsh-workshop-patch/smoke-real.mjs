// Final smoke: the patched REAL artifact still imports and its new API is callable.
import { readFileSync, writeFileSync, rmSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

const CORE = 'C:/Users/ROG/.dsh/profiles/web/node_modules/dsh-workshop/lib/host/core-BcUmZo6v.mjs';
const TMP = 'E:/output/dsh-workshop-patch/core-smoke.mjs';
const stub = 'data:text/javascript,export const defineTool=(x)=>x;';
const src = readFileSync(CORE, 'utf8');
writeFileSync(TMP, src.replace(
  'import { defineTool } from "@deepseek-ai/dsh-tools";',
  `import { defineTool } from "${stub}";`,
), 'utf8');

const api = (await import(pathToFileURL(TMP).href)).a;
rmSync(TMP, { force: true });

const keys = ['parseBlockedBuildDeps', 'isBuildBlocked', 'isBuildPolicyBlocked', 'isRealPrepareFailure',
  'appendAllowBuilds', 'prepareIsolatedPnpmConfig', 'fixBlockedBuilds', 'installPluginSmart',
  'classifyFailReason', 'failReasonHint'];
const present = keys.filter((k) => typeof api[k] === 'function');
console.log(`real artifact imports OK; new/expected API present: ${present.length}/${keys.length}`);
console.log('classify(ERR_PNPM_IGNORED_BUILDS) ->', api.classifyFailReason('[ERR_PNPM_IGNORED_BUILDS] Ignored build scripts: esbuild@0.25.0', true, true));
console.log('classify(ERR_PNPM_GIT_DEP_PREPARE_NOT_ALLOWED) ->', api.classifyFailReason('ERR_PNPM_GIT_DEP_PREPARE_NOT_ALLOWED', false, true));
console.log('classify(ERR_PNPM_PREPARE_PACKAGE only) ->', api.classifyFailReason('[ERR_PNPM_PREPARE_PACKAGE] Failed to prepare', false, true));
