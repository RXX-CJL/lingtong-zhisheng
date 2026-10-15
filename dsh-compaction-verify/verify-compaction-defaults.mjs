import * as mod from 'file:///C:/Users/ROG/AppData/Local/npm-cache/_npx/d460afef2690c19d/node_modules/@deepseek-ai/dsh-compaction-basic/lib/index.js';
const { resolveConfig, resolveTargetPolicy } = mod.default ?? mod;

const cases = {
  'shipped standard (no config)': {},
  'proposed (maxTokens 32768)': { maxTokens: 32768 },
};

for (const [label, cfg] of Object.entries(cases)) {
  const resolved = resolveConfig(cfg);
  const target = resolveTargetPolicy(resolved, { provider: 'deepseek-official', model: 'deepseek-flash' });
  console.log(label, JSON.stringify({
    thresholdRatio: resolved.thresholdRatio,
    retainRatio: resolved.retainRatio,
    headroomTokens: resolved.headroomTokens,
    maxTokens: resolved.maxTokens,
    compactionRetries: resolved.compactionRetries,
    maxOverflowRetries: resolved.maxOverflowRetries,
    auto: resolved.auto,
    summarizationProvider: resolved.summarizationProvider,
    summarizationModel: resolved.summarizationModel,
    targetMaxTokens: target.maxTokens,
  }, null, 2));
}
