#!/usr/bin/env node
/**
 * session_scale.mjs v3 —— 【实测】单次模型调用的上下文长度分布
 *
 * 依据：DSH 会话日志（zstd 多帧，Node 原生可解）里 `assistant/message` 事件带 `usage`，
 *       字段 inputTokens / outputTokens / cacheRead / totalTokens。
 *       每个 step ≈ 一次模型调用（step/start 1839 : assistant/message 1831）。
 *       上下文长度 ≈ inputTokens + cacheRead。
 *
 * 目的：把 phase_sensitivity_verdict.md §2 的 A4 从"下界论证"升级为实测。
 * 用法：node E:\output\_tools\session_scale.mjs
 */
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { zstdDecompressSync } from 'node:zlib';

const ROOT = process.argv[2] || 'C:\\Users\\ROG\\.dsh\\sessions';
const MAGIC = Buffer.from([0x28, 0xb5, 0x2f, 0xfd]);

function walk(dir, out = []) {
  let ents = [];
  try { ents = readdirSync(dir, { withFileTypes: true }); } catch { return out; }
  for (const e of ents) {
    const p = join(dir, e.name);
    if (e.isDirectory()) walk(p, out);
    else if (e.name.endsWith('.zstd')) out.push(p);
  }
  return out;
}

function decompressFrames(buf) {
  const parts = [];
  let offset = 0;
  while (offset < buf.length) {
    const next = buf.indexOf(MAGIC, offset + 4);
    const end = next === -1 ? buf.length : next;
    try { parts.push(zstdDecompressSync(buf.subarray(offset, end)).toString('utf8')); } catch { /* 坏帧跳过 */ }
    if (next === -1) break;
    offset = next;
  }
  return parts.join('');
}

function flatNums(obj, prefix = '', out = {}) {
  if (!obj || typeof obj !== 'object') return out;
  for (const [k, v] of Object.entries(obj)) {
    const key = prefix ? `${prefix}.${k}` : k;
    if (typeof v === 'number') out[key] = v;
    else if (v && typeof v === 'object') flatNums(v, key, out);
  }
  return out;
}

const files = walk(ROOT).map((p) => ({ p, size: statSync(p).size })).sort((a, b) => b.size - a.size);
console.log(`扫描 ${files.length} 个会话日志…`);

const rows = [];
const keyCount = new Map();
let messages = 0, withUsage = 0, parseFail = 0;
let firstUsage = null;

for (const f of files) {
  let text = '';
  try { text = decompressFrames(readFileSync(f.p)); } catch (e) { console.log(`  ! ${f.p}: ${e.message}`); continue; }
  for (const line of text.split('\n')) {
    if (!line.trim()) continue;
    let o; try { o = JSON.parse(line); } catch { parseFail++; continue; }
    if (o.type !== 'assistant/message') continue;
    messages++;
    const u = o.data?.usage;
    if (!u || typeof u !== 'object') continue;
    withUsage++;
    if (!firstUsage) firstUsage = u;
    const nums = flatNums(u);
    for (const k of Object.keys(nums)) keyCount.set(k, (keyCount.get(k) || 0) + 1);
    rows.push({ t: o.time, turn: o.data?.turn, step: o.data?.step, nums });
  }
}

console.log(`assistant/message 事件 ${messages} 条，其中带 usage ${withUsage} 条；JSON 解析失败 ${parseFail} 行\n`);
console.log('usage 首个样本：');
console.log(JSON.stringify(firstUsage, null, 1));
console.log('\nusage 数值字段（出现次数）：');
for (const [k, v] of [...keyCount.entries()].sort((a, b) => b[1] - a[1])) console.log(`  ${k}: ${v}`);

function pick(name) {
  return rows.map((r) => r.nums[name]).filter((v) => typeof v === 'number');
}
function quant(arr, q) {
  if (!arr.length) return NaN;
  const a = [...arr].sort((x, y) => x - y);
  return a[Math.min(a.length - 1, Math.floor(q * (a.length - 1)))];
}
function report(label, arr) {
  if (!arr.length) { console.log(`\n--- ${label}: 无数据 ---`); return; }
  const a = [...arr].sort((x, y) => x - y);
  const sum = a.reduce((s, v) => s + v, 0);
  console.log(`\n--- ${label}（n=${a.length}）---`);
  console.log(`  min=${a[0].toLocaleString()}  p25=${quant(a, .25).toLocaleString()}  p50=${quant(a, .5).toLocaleString()}  p75=${quant(a, .75).toLocaleString()}`);
  console.log(`  p90=${quant(a, .9).toLocaleString()}  p95=${quant(a, .95).toLocaleString()}  p99=${quant(a, .99).toLocaleString()}  max=${a[a.length - 1].toLocaleString()}`);
  console.log(`  均值=${Math.round(sum / a.length).toLocaleString()}  合计=${sum.toLocaleString()}`);
  for (const th of [16384, 32768, 65536, 131072, 262144, 524288]) {
    const c = a.filter((v) => v >= th).length;
    console.log(`    >= ${String(th).padStart(7)} : ${String(c).padStart(5)} 次 (${(c / a.length * 100).toFixed(1)}%)`);
  }
}

const input = pick('inputTokens');
const cache = pick('cacheReadTokens');
const total = pick('totalTokens');

// 上下文长度 = inputTokens + cacheRead（同一行对齐求和）
const ctx = rows
  .map((r) => {
    const i = r.nums.inputTokens, c = r.nums.cacheReadTokens;
    return (typeof i === 'number' && typeof c === 'number') ? i + c : (typeof i === 'number' ? i : null);
  })
  .filter((v) => typeof v === 'number');

report('inputTokens（未命中缓存的 prompt）', input);
report('cacheRead（命中缓存的 prompt）', cache);
report('★ 上下文长度 = inputTokens + cacheRead', ctx);
report('totalTokens（按日志口径）', total);

// 按时间排序，看是否随会话推移增长
const withT = rows.filter((r) => typeof r.t === 'number' && typeof r.nums.inputTokens === 'number' && typeof r.nums.cacheReadTokens === 'number');
withT.sort((a, b) => a.t - b.t);
if (withT.length > 20) {
  const seg = Math.floor(withT.length / 4);
  console.log('\n--- 按时间四分段（看上下文是否随会话增长）---');
  for (let i = 0; i < 4; i++) {
    const s = withT.slice(i * seg, i === 3 ? withT.length : (i + 1) * seg);
    const v = s.map((r) => r.nums.inputTokens + r.nums.cacheReadTokens);
    console.log(`  第${i + 1}段 n=${v.length}  中位=${quant(v, .5).toLocaleString()}  p90=${quant(v, .9).toLocaleString()}`);
  }
}
