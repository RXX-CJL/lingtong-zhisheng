// Structural comparison: shipped standard preset plugins vs. the restated override.
// !!js scalars are loaded as plain strings so the trees can be deep-compared.
import { readFileSync } from 'node:fs';
import yaml from 'file:///C:/Users/ROG/AppData/Local/npm-cache/_npx/d460afef2690c19d/node_modules/js-yaml/index.js';

const jsTag = new yaml.Type('tag:yaml.org,2002:js', {
  kind: 'scalar',
  resolve: (data) => typeof data === 'string' && data.length > 0,
  construct: (data) => `<js:${data}>`,
});

const SRC = 'C:/Users/ROG/AppData/Local/npm-cache/_npx/d460afef2690c19d/node_modules/@deepseek-ai/dsh-web-app/presets/standard.patch.yml';
const NEW = 'E:/output/preset-standard-override-block.yml';

const load = (p) => {
  const docs = yaml.loadAll(readFileSync(p, 'utf8'), undefined, { schema: yaml.DEFAULT_SCHEMA.extend([jsTag]) });
  return docs.flat().filter(Boolean);
};

const shippedRow = load(SRC)[0].insert.find((r) => r.id === 'preset-standard');
const overrideRow = load(NEW).find((r) => r.id === 'preset-standard');

const a = shippedRow.config;
const b = overrideRow.config;

console.log('override keys      :', JSON.stringify(Object.keys(b)));
console.log('override id/order  :', b.id, b.order);
console.log('shipped  plugins n :', a.plugins.length);
console.log('override plugins n :', b.plugins.length);

// Walk both trees in parallel and list every divergence by path.
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
walk(a, b, 'config');

console.log('\n--- structural differences (shipped -> override) ---');
console.log(diffs.length ? diffs.join('\n') : '(none)');

// Confirm the id/name sequence of nested rows is untouched.
const ids = (rows) => rows.map((r) => r.id);
console.log('\ncounterpart id sequences equal:', JSON.stringify(ids(a.plugins)) === JSON.stringify(ids(b.plugins)));
const cmpGroup = a.plugins.find((p) => p.id === 'compaction');
const ovrGroup = b.plugins.find((p) => p.id === 'compaction');
console.log('compaction group ids equal   :', JSON.stringify(ids(cmpGroup.config)) === JSON.stringify(ids(ovrGroup.config)));
console.log('compaction isolate equal     :', JSON.stringify(cmpGroup.isolate) === JSON.stringify(ovrGroup.isolate));
console.log('pruner config equal          :', JSON.stringify(cmpGroup.config.find((r) => r.id === 'tool-result-pruner').config)
  === JSON.stringify(ovrGroup.config.find((r) => r.id === 'tool-result-pruner').config));
console.log('effective compaction-basic   :', JSON.stringify(ovrGroup.config.find((r) => r.id === 'compaction-basic')));
