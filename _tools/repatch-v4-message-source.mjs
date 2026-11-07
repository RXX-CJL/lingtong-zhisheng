#!/usr/bin/env node
/**
 * repatch-v4-message-source.mjs —— 重打「V4 消息 source」本地补丁。
 *
 * 背景（2026-10-29 实测定位）：
 *   DSH Session V4 的 message-sources 准入校验拒绝 kind === 'plugin'：
 *     if (... || value["kind"] === "plugin")
 *       throw new SessionFormatError("format v4 message requires a producer-owned source kind")
 *   第三方插件若仍用 V3 旧写法 { kind: 'plugin', plugin: '<name>' } 往对话里注入消息，
 *   该轮会直接失败（用户可见为「本轮运行失败」+ 错误码 UNKNOWN）。
 *
 *   正确写法是生产者自有 kind：'plugin:<namespace>'。
 *   这与核心 producerKind() 的兜底 return `plugin:${plugin}` 一致，
 *   也与已修复的 dsh-llm-retry-settings / dsh-vision-router 的写法一致。
 *
 * 被修的两处（原始 3 处，第 3 处是 consolidation 输入快照，无关，不动）：
 *   dsh-batch-tool-calls   lib/index.js:60  上下文压缩后注入 reminder 消息
 *   @hr98w/dsh-memory      lib/index.mjs    记忆整合 worker 注入 2 条消息
 *
 * 用法：
 *   node repatch-v4-message-source.mjs --check   只检查，不写
 *   node repatch-v4-message-source.mjs           打补丁（幂等）
 *
 * 何时需要重跑：任何 pnpm add / install / update 之后（会覆盖 node_modules）。
 */

import { readFileSync, writeFileSync, copyFileSync, existsSync } from 'node:fs'
import { join } from 'node:path'

const NM = process.env.DSH_PROFILE_NM ?? 'C:/Users/ROG/.dsh/profiles/desktop/node_modules'
const CHECK_ONLY = process.argv.includes('--check')
const STAMP = '.bak-before-v4-source-fix'

const TARGETS = [
  {
    label: 'dsh-batch-tool-calls',
    file: join(NM, 'dsh-batch-tool-calls', 'lib', 'index.js'),
    pattern: /Object\.freeze\(\{\s*kind:\s*'plugin',\s*plugin:\s*name\s*\}\)/g,
    expected: 1,
    replacement: "Object.freeze({ kind: 'plugin:' + name })",
  },
  {
    label: '@hr98w/dsh-memory',
    file: join(NM, '@hr98w', 'dsh-memory', 'lib', 'index.mjs'),
    pattern: /source:\s*\{\s*\n\s*kind:\s*"plugin",\s*\n\s*plugin:\s*"dsh-memory"\s*\n\s*\}/g,
    expected: 2,
    replacement: 'source: { kind: "plugin:dsh-memory" }',
  },
]

let failed = 0
for (const t of TARGETS) {
  if (!existsSync(t.file)) {
    console.log(`[SKIP] ${t.label}: 文件不存在 ${t.file}`)
    continue
  }
  const src = readFileSync(t.file, 'utf8')
  const hits = (src.match(t.pattern) ?? []).length

  if (hits === 0) {
    console.log(`[OK]   ${t.label}: 已是修复后写法（无需处理）`)
    continue
  }
  if (hits !== t.expected) {
    console.log(`[WARN] ${t.label}: 命中 ${hits} 处，预期 ${t.expected} 处 —— 版本可能已变，人工确认`)
    failed++
    continue
  }
  if (CHECK_ONLY) {
    console.log(`[NEED] ${t.label}: ${hits} 处待修（--check 模式未写入）`)
    failed++
    continue
  }
  copyFileSync(t.file, t.file + STAMP)
  writeFileSync(t.file, src.replace(t.pattern, t.replacement), 'utf8')
  const residual = (readFileSync(t.file, 'utf8').match(/kind:\s*[\"']plugin[\"']\s*,/g) ?? []).length
  console.log(`[FIX]  ${t.label}: 修复 ${hits} 处，残留非法写法 ${residual} 处`)
}

if (failed > 0) {
  console.log(`\n未完成项 ${failed} 个。`)
  process.exitCode = 1
} else {
  console.log('\n全部就绪。改动 node_modules 后需要重启 DSH Desktop 才生效。')
}
