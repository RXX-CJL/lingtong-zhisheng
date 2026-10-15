// Dry-run harness: regenerate a patcher pointed at a workspace COPY of the
// installed bundle, run it, then validate the result. Never touches the install.
import { readFileSync, writeFileSync, existsSync, rmSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

const patchSrc = readFileSync('E:/output/dsh-workshop-patch/patch-client.mjs', 'utf8');
const installed = readFileSync('C:/Users/ROG/.dsh/profiles/web/node_modules/dsh-workshop/lib/client.js', 'utf8');

const tmp = 'E:/output/dsh-workshop-patch/client.dryrun.js';
if (existsSync(`${tmp}.pre-patch`)) rmSync(`${tmp}.pre-patch`);
writeFileSync(tmp, installed, 'utf8');

const rewritten = patchSrc.replace(/const TARGET = '[^']*';/, `const TARGET = '${tmp}';`);
writeFileSync('E:/output/dsh-workshop-patch/_dryrun-module.mjs', rewritten, 'utf8');

// stdio inherit: this sandbox cannot capture piped child output.
const out = spawnSync(process.execPath, ['E:/output/dsh-workshop-patch/_dryrun-module.mjs'], { stdio: 'inherit' });
console.log('exit:', out.status);
