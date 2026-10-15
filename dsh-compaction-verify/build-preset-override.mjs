// Build an id-targeted override row for the `preset-standard` loader entry.
// Source of truth: the shipped @deepseek-ai/dsh-web-app presets/standard.patch.yml.
// Only change: config.plugins[compaction/compaction-basic].config.maxTokens = 32768.
import { readFileSync, writeFileSync } from 'node:fs';

const SRC = 'C:/Users/ROG/AppData/Local/npm-cache/_npx/d460afef2690c19d/node_modules/@deepseek-ai/dsh-web-app/presets/standard.patch.yml';

// --- Pass 1: verify the shipped shape and locate the nested compaction-basic entry.
const shipped = readFileSync(SRC, 'utf8').split(/\r?\n/);
while (shipped.length && shipped[shipped.length - 1] === '') shipped.pop();

const rowStart = shipped.findIndex((l) => l === '    - id: preset-standard');
if (rowStart < 0) throw new Error('preset-standard insert row not found');
const pluginsAt = shipped.findIndex((l, i) => i > rowStart && l === '        plugins:');
if (pluginsAt < 0) throw new Error('plugins: not found');

const CB_ID = '              - id: compaction-basic';
const CB_NAME = "                name: '@deepseek-ai/dsh-compaction-basic'";
let cbIndex = -1;
for (let i = pluginsAt; i < shipped.length; i++) {
  if (shipped[i] === CB_ID) { cbIndex = i; break; }
}
if (cbIndex < 0) throw new Error('nested compaction-basic row not found');
if (shipped[cbIndex + 1] !== CB_NAME) {
  throw new Error('unexpected row following compaction-basic: ' + JSON.stringify(shipped[cbIndex + 1]));
}
if (shipped[cbIndex + 2] !== undefined && /^ {16}config:$/.test(shipped[cbIndex + 2])) {
  throw new Error('compaction-basic already carries a config block; refusing to guess');
}

// --- Pass 2: splice the maxTokens config into the plugin body.
const body = shipped.slice(pluginsAt); // begins with `        plugins:`
const spliced = [];
for (let i = 0; i < body.length; i++) {
  spliced.push(body[i]);
  if (body[i] === CB_ID) {
    spliced.push(CB_NAME);
    spliced.push('                config:');
    spliced.push('                  maxTokens: 32768');
    i += 1; // consume the shipped `name:` line we just restated
  }
}

// --- Pass 3: reassemble the override row, shifting the body from 8-space to
// 4-space base indentation (the row's own `config:` is at 2).
const shift = (line) => (line.length ? line.slice(4) : line);
const row = [
  '# Added for the Standard Agent Preset compaction tuning.',
  '# Purpose: set ONLY the Standard preset compaction summarizer generation cap.',
  '# Scope:   targets the existing `preset-standard` loader row from',
  '#          @deepseek-ai/dsh-web-app/presets/standard.patch.yml; that bundle file is',
  '#          untouched, and the Web Host top-level `compaction-basic` row',
  '#          (disabled: true) is NOT affected.',
  '# Note:    a non-insert patch replaces the entire row config, so the shipped',
  '#          plugins list is restated verbatim with the single maxTokens addition.',
  '# Revert:  delete this block from the end of this file, then re-run',
  '#          `dsh --profile web --dump-config` to confirm.',
  '- id: preset-standard',
  "  name: '@deepseek-ai/dsh-agent-preset'",
  '  config:',
  '    id: standard',
  '    order: 1',
  '    plugins:',
  ...spliced.slice(1).map(shift),
  '',
].join('\n');

writeFileSync('E:/output/preset-standard-override-block.yml', row, 'utf8');
console.log('OK: override block lines =', row.split('\n').length);
