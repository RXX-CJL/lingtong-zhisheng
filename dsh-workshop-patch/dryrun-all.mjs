// Run BOTH patch stages against a fresh workspace copy, never touching the install.
// Stage scripts are rewritten so their TARGET points at the copy.
import { readFileSync, writeFileSync, mkdirSync, rmSync, existsSync, copyFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

const REAL = 'C:/Users/ROG/.dsh/profiles/web/node_modules/dsh-workshop/lib/host/core-BcUmZo6v.mjs';
const DIR = 'E:/output/dsh-workshop-patch/dryrun-install';
const REL = 'lib/host/core-BcUmZo6v.mjs';
const COPY = `${DIR}/${REL}`;

rmSync(DIR, { recursive: true, force: true });
mkdirSync(`${DIR}/lib/host`, { recursive: true });
copyFileSync(REAL, COPY);
const pristine = readFileSync(COPY, 'utf8');

const stages = ['patch-installer.mjs', 'patch-installer2.mjs'];
for (const script of stages) {
  let src = readFileSync(`E:/output/dsh-workshop-patch/${script}`, 'utf8');
  // Rewrite whatever TARGET form the stage declares to point at the copy.
  const before = src;
  src = src.replace(/(const TARGET = )(process\.argv\[2\] \?\? )?'[^']*'/, `$1'${COPY}'`);
  if (src === before) {
    console.error(`could not retarget ${script}`);
    process.exit(1);
  }
  const tmp = `E:/output/dsh-workshop-patch/_stage-${script}`;
  writeFileSync(tmp, src, 'utf8');
  const out = spawnSync(process.execPath, [tmp], { stdio: 'inherit' });
  console.log(`${script} exit:`, out.status);
  if (out.status !== 0) process.exit(out.status);
}

const final = readFileSync(COPY, 'utf8');
const realNow = readFileSync(REAL, 'utf8');
console.log('\n--- dry-run copy ---');
console.log('marker present           :', final.includes('blocked-build sites patched'));
console.log('github-fallback retry arg:', final.includes('], env, second.output, name + "@" + gitSource);'));
console.log('npm retry arg            :', final.includes('], env, npmOut.output, npmName);'));
console.log('sidecars                 :', existsSync(`${COPY}.pre-patch`), existsSync(`${COPY}.pre-patch2`));
console.log('\n--- real install untouched by this harness? ---');
console.log('real file unchanged vs pristine source:', realNow === pristine || !realNow.includes('blocked-build sites patched'));
