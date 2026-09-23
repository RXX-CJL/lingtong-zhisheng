#!/usr/bin/env node
/**
 * M10: Element Plus 图标名称校验脚本
 *
 * 用途:
 *   1. 扫描 src/views/*.vue 与 src/components/*.vue 文件中
 *      `import { XxxIcon } from '@element-plus/icons-vue'` 的所有图标名
 *   2. 对照 @element-plus/icons-vue 包内 exports 校验存在性
 *   3. 不存在则输出缺失清单并以 exit code 1 退出
 *
 * 用法:
 *   node scripts/verify-icons.cjs
 *   或在 package.json 中: "scripts": { "verify-icons": "node scripts/verify-icons.cjs" }
 */

const fs = require('fs');
const path = require('path');

// ---------- 配置 ----------
const ROOT = path.resolve(__dirname, '..');
const SCAN_DIRS = [
  path.join(ROOT, 'src', 'views'),
  path.join(ROOT, 'src', 'components'),
];
const SCAN_EXT = ['.vue', '.js', '.jsx', '.ts', '.tsx'];

// 正则: 抓取 import { A, B as C } from '@element-plus/icons-vue'
const ICON_IMPORT_RE = /import\s*\{([^}]+)\}\s*from\s*['"]@element-plus\/icons-vue['"]/g;

// ---------- 加载 @element-plus/icons-vue 全部 export 名 ----------
function loadValidIconNames() {
  const pkgPath = path.join(ROOT, 'node_modules', '@element-plus', 'icons-vue');
  if (!fs.existsSync(pkgPath)) {
    console.error(`[verify-icons] 未找到 @element-plus/icons-vue 包: ${pkgPath}`);
    console.error('请先执行 `npm install` 安装依赖');
    process.exit(2);
  }
  // 解析 package.json 找入口文件
  const pkgJson = JSON.parse(fs.readFileSync(path.join(pkgPath, 'package.json'), 'utf-8'));
  const entryFile = path.join(pkgPath, pkgJson.main || 'dist/index.js');

  // 直接 require 整个模块，取 keys
  try {
    const mod = require(entryFile);
    return new Set(Object.keys(mod));
  } catch (e) {
    // 如果 require 失败，回退到解析 dist/index.js 的导出标识符
    console.warn(`[verify-icons] require 入口失败 (${e.message})，回退到静态解析`);
    return parseExportsFromDist(entryFile);
  }
}

function parseExportsFromDist(entryFile) {
  const names = new Set();
  if (!fs.existsSync(entryFile)) return names;
  const content = fs.readFileSync(entryFile, 'utf-8');
  // 匹配 export { A as B, C }; 或 export var X = ...
  const exportRe = /export\s*\{([^}]+)\}/g;
  let m;
  while ((m = exportRe.exec(content)) !== null) {
    const items = m[1].split(',');
    for (const item of items) {
      const parts = item.trim().split(/\s+as\s+/);
      const name = parts[parts.length - 1].trim();
      if (name) names.add(name);
    }
  }
  return names;
}

// ---------- 扫描源文件提取 import 的图标名 ----------
function walkDir(dir, exts, files = []) {
  if (!fs.existsSync(dir)) return files;
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const ent of entries) {
    const full = path.join(dir, ent.name);
    if (ent.isDirectory()) {
      // 跳过 node_modules
      if (ent.name === 'node_modules') continue;
      walkDir(full, exts, files);
    } else if (exts.includes(path.extname(ent.name))) {
      files.push(full);
    }
  }
  return files;
}

function extractIconNamesFromFile(filePath) {
  const content = fs.readFileSync(filePath, 'utf-8');
  const names = new Set();
  let m;
  ICON_IMPORT_RE.lastIndex = 0;
  while ((m = ICON_IMPORT_RE.exec(content)) !== null) {
    const items = m[1].split(',');
    for (const item of items) {
      const parts = item.trim().split(/\s+as\s+/);
      // 取原始名（as 前的部分），因为我们要校验包内是否导出该名
      const originalName = parts[0].trim();
      if (originalName) names.add(originalName);
    }
  }
  return names;
}

// ---------- 主流程 ----------
function main() {
  console.log('[verify-icons] 开始校验 Element Plus 图标名称...');
  const validNames = loadValidIconNames();
  console.log(`[verify-icons] 已加载 ${validNames.size} 个合法图标名`);

  if (validNames.size === 0) {
    console.error('[verify-icons] 未加载到任何合法图标名，校验中止');
    process.exit(2);
  }

  const allFiles = [];
  for (const dir of SCAN_DIRS) {
    walkDir(dir, SCAN_EXT, allFiles);
  }
  console.log(`[verify-icons] 扫描 ${allFiles.length} 个源文件`);

  // 文件 -> 该文件 import 的图标名
  const fileToNames = new Map();
  // 图标名 -> 出现的文件列表
  const nameToFiles = new Map();

  for (const file of allFiles) {
    const names = extractIconNamesFromFile(file);
    if (names.size === 0) continue;
    const rel = path.relative(ROOT, file);
    fileToNames.set(rel, names);
    for (const n of names) {
      if (!nameToFiles.has(n)) nameToFiles.set(n, []);
      nameToFiles.get(n).push(rel);
    }
  }

  console.log(`[verify-icons] 共发现 ${nameToFiles.size} 个唯一图标 import`);

  // 校验存在性
  const missing = [];
  for (const [name, files] of nameToFiles.entries()) {
    if (!validNames.has(name)) {
      missing.push({ name, files });
    }
  }

  if (missing.length === 0) {
    console.log('[verify-icons] ✓ 所有图标名称均合法');
    // 输出部分使用样例（前 5 个）
    let count = 0;
    for (const [name, files] of nameToFiles.entries()) {
      if (count >= 5) break;
      console.log(`  ✓ ${name} → ${files[0]}${files.length > 1 ? ` (+${files.length - 1})` : ''}`);
      count++;
    }
    process.exit(0);
  } else {
    console.error(`[verify-icons] ✗ 发现 ${missing.length} 个非法图标名:`);
    for (const { name, files } of missing) {
      console.error(`  ✗ ${name}`);
      for (const f of files) {
        console.error(`      在: ${f}`);
      }
    }
    console.error('\n参考: https://element-plus.org/zh-CN/component/icon.html#icons-collection');
    process.exit(1);
  }
}

main();
