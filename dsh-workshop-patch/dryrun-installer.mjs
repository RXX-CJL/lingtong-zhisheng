// Dry-run the installer patch against a workspace copy, then validate it.
import { readFileSync, writeFileSync, existsSync, rmSync, mkdirSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

const rel = 'lib/host/core-BcUmZo6v.mjs';
const srcDir = 'C:/Users/ROG/.dsh/profiles/web/node_modules/dsh-workshop';
const tmpRoot = 'E:/output/dsh-workshop-patch/dryrun-install';
rmSync(tmpRoot, { recursive: true, force: true });
mkdirSync(tmpRoot, { recursive: true });

const patchSrc = readFileSync('E:/output/dsh-workshop-patch/patch-installer.mjs', 'utf8');
const rewritten = patchSrc.replace(
  /const TARGET = '[^']*';/,
  `const TARGET = '${tmpRoot}/${rel}';`,
);
mkdirSync(`${tmpRoot}/lib/host`, { recursive: true });
writeFileSync(`${tmpRoot}/${rel}`, readFileSync(`${srcDir}/${rel}`), 'utf8');
writeFileSync('E:/output/dsh-workshop-patch/_dryrun-installer.mjs', rewritten, 'utf8');

const out = spawnSync(process.execPath, ['E:/output/dsh-workshop-patch/_dryrun-installer.mjs'], { stdio: 'inherit' });
console.log('dry-run exit:', out.status);
console.log('sidecar created:', existsSync(`${tmpRoot}/${rel}.pre-patch`));
