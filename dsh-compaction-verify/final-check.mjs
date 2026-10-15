// Final consolidated assertion over the freshly dumped composed profile.
import { readFileSync } from 'node:fs';
import yaml from 'file:///C:/Users/ROG/AppData/Local/npm-cache/_npx/d460afef2690c19d/node_modules/js-yaml/index.js';

const jsTag = new yaml.Type('tag:yaml.org,2002:js', {
  kind: 'scalar',
  resolve: (d) => typeof d === 'string' && d.length > 0,
  construct: (d) => `<js:${d}>`,
});
const DIR = 'E:/output/dsh-compaction-verify';
const load = (p) => yaml.load(readFileSync(p, 'utf8'), { schema: yaml.DEFAULT_SCHEMA.extend([jsTag]) });

const before = load(`${DIR}/dump-before.yml`);
const final = load(`${DIR}/dump-final.yml`);

// 1. Exactly one difference across the whole composed tree.
const diffs = [];
const walk = (x, y, path) => {
  if (Array.isArray(x) || Array.isArray(y)) {
    if (!Array.isArray(x) || !Array.isArray(y)) return diffs.push(`${path}: array-ness`);
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
walk(before, final, 'root');

const check = (label, ok, detail) => console.log(`${ok ? 'PASS' : 'FAIL'}  ${label}${detail ? '  -- ' + detail : ''}`);

check('composed tree changes exactly one value', diffs.length === 1, diffs.join(' | '));
check('that value is compaction-basic.maxTokens = 32768',
  diffs[0]?.endsWith('undefined -> {"maxTokens":32768}'), diffs[0]);

const top = final.find((r) => r.id === 'compaction-basic');
check('Web Host top-level compaction-basic still present, still disabled',
  top?.disabled === true && top?.config === undefined, JSON.stringify(top));

const presetRow = final.find((r) => r.id === 'preset-standard');
const preset = presetRow.config;
check('preset-standard keeps id/order', preset.id === 'standard' && preset.order === 1);
check('preset-standard plugin count unchanged (19)', preset.plugins.length === 19, String(preset.plugins.length));

const beforePlugins = before.find((r) => r.id === 'preset-standard').config.plugins;
check('plugin id sequence unchanged',
  JSON.stringify(beforePlugins.map((p) => p.id)) === JSON.stringify(preset.plugins.map((p) => p.id)));

const cb = preset.plugins.find((p) => p.id === 'compaction').config.find((r) => r.id === 'compaction-basic');
check('preset-standard compaction-basic maxTokens = 32768',
  cb.config.maxTokens === 32768, JSON.stringify(cb));
check('no thresholdRatio/retainRatio/headroom/auto/retries set (untouched defaults)',
  cb.config.thresholdRatio === undefined && cb.config.retainRatio === undefined &&
  cb.config.headroomTokens === undefined && cb.config.auto === undefined &&
  cb.config.compactionRetries === undefined && cb.config.maxOverflowRetries === undefined,
  JSON.stringify(cb.config));

const pruner = preset.plugins.find((p) => p.id === 'compaction').config.find((r) => r.id === 'tool-result-pruner');
check('tool-result-pruner config untouched',
  JSON.stringify(pruner.config) === JSON.stringify({ thresholdChars: 8192, headChars: 4096, tailChars: 1024 }),
  JSON.stringify(pruner.config));

const delegation = preset.plugins.find((p) => p.id === 'delegation');
const beforeDelegation = beforePlugins.find((p) => p.id === 'delegation');
check('delegation group untouched', JSON.stringify(delegation) === JSON.stringify(beforeDelegation));

const otherPresets = ['preset-ptc', 'preset-minimal', 'preset-cordis'];
check('other presets untouched',
  otherPresets.every((id) => JSON.stringify(before.find((r) => r.id === id)) === JSON.stringify(final.find((r) => r.id === id))));

// Model default must be unchanged.
const dm = final.find((r) => r.id === 'agent-default-model');
check('agent-default-model untouched (deepseek-flash / low)',
  dm?.config?.model === 'deepseek-flash' && dm?.config?.reasoningEffort === 'low', JSON.stringify(dm?.config));

console.log('\ntotal differences:', diffs.length);
