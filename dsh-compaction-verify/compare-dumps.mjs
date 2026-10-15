// Structural diff of the composed profile tree before vs. after the edit.
import { readFileSync } from 'node:fs';
import yaml from 'file:///C:/Users/ROG/AppData/Local/npm-cache/_npx/d460afef2690c19d/node_modules/js-yaml/index.js';

const jsTag = new yaml.Type('tag:yaml.org,2002:js', {
  kind: 'scalar',
  resolve: (d) => typeof d === 'string' && d.length > 0,
  construct: (d) => `<js:${d}>`,
});
const load = (p) => yaml.load(readFileSync(p, 'utf8'), { schema: yaml.DEFAULT_SCHEMA.extend([jsTag]) });

const DIR = 'E:/output/dsh-compaction-verify';
const before = load(`${DIR}/dump-before.yml`);
const after = load(`${DIR}/dump-after.yml`);
console.log('root rows before/after:', before.length, after.length);

const diffs = [];
const walk = (x, y, path) => {
  if (Array.isArray(x) || Array.isArray(y)) {
    if (!Array.isArray(x) || !Array.isArray(y)) return diffs.push(`${path}: array-ness differs`);
    if (x.length !== y.length) diffs.push(`${path}: length ${x.length} -> ${y.length}`);
    for (let i = 0; i < Math.max(x.length, y.length); i++) walk(x[i], y[i], `${path}[${i}]`);
    return;
  }
  if (x && y && typeof x === 'object' && typeof y === 'object') {
    for (const k of new Set([...Object.keys(x), ...Object.keys(y)])) walk(x[k], y[k], `${path}.${k}`);
    return;
  }
  if (JSON.stringify(x) !== JSON.stringify(y)) diffs.push(`${path}: ${JSON.stringify(x)} -> ${JSON.stringify(y)}`);
};
walk(before, after, 'root');

console.log('\n--- composed-tree differences ---');
console.log(diffs.length ? diffs.join('\n') : '(none)');

const top = after.find((r) => r.id === 'compaction-basic');
console.log('\nWeb Host top-level compaction-basic row  :', JSON.stringify(top));
const preset = after.find((r) => r.id === 'preset-standard');
const cb = preset.config.plugins.find((p) => p.id === 'compaction').config.find((r) => r.id === 'compaction-basic');
console.log('preset-standard effective compaction-basic:', JSON.stringify(cb));
console.log('default agent preset row                  :',
  JSON.stringify(after.filter((r) => r.name === '@deepseek-ai/dsh-agent-preset-registry' || r.id?.includes('preset')).map((r) => r.id)));
