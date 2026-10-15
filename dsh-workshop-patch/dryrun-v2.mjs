// Apply installer-v2 to a fresh workspace COPY (never the install) and verify it.
import { mkdirSync, rmSync, copyFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

const REAL = 'C:/Users/ROG/.dsh/profiles/web/node_modules/dsh-workshop/lib/host/core-BcUmZo6v.mjs';
const DIR = 'E:/output/dsh-workshop-patch/dryrun-v2';
const REL = 'lib/host/core-BcUmZo6v.mjs';
rmSync(DIR, { recursive: true, force: true });
mkdirSync(`${DIR}/lib/host`, { recursive: true });
copyFileSync(REAL, `${DIR}/${REL}`);

const out = spawnSync(process.execPath, ['E:/output/dsh-workshop-patch/installer-v2.mjs', `${DIR}/${REL}`], { stdio: 'inherit' });
console.log('patch exit:', out.status);
if (out.status !== 0) process.exit(out.status);

const verify = spawnSync(process.execPath, ['E:/output/dsh-workshop-patch/verify-v2.mjs', `${DIR}/${REL}`], { stdio: 'inherit' });
console.log('verify exit:', verify.status);
process.exit(verify.status ?? 1);
