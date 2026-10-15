// Patch dsh-workshop's installer to handle pnpm 11 build-script blocking.
//
// Verified against pnpm 11.7.0:
//   * allowBuilds keys are DEP PATHS (`pkg@file:../x`, `pkg@git+file:///...#sha`),
//     so the old name-keyed entry was silently ineffective.
//   * ERR_PNPM_GIT_DEP_PREPARE_NOT_ALLOWED prints the exact key in its hint.
//   * pnpm_config_dangerously_allow_all_builds=true is honoured from the
//     environment and is inherited by a nested `pnpm install` spawned from a
//     dependency's prepare script - the only way to unblock a nested project
//     whose pnpm-workspace.yaml we do not own.
//
// The generated code avoids template literals entirely so the patch text can be
// pasted without escaping hazards. Idempotent.
import { readFileSync, writeFileSync, existsSync, copyFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

const P = String.fromCharCode(96); // backtick, never emitted into the bundle
const TARGET = 'C:/Users/ROG/.dsh/profiles/web/node_modules/dsh-workshop/lib/host/core-BcUmZo6v.mjs';
const MARKER = 'parseBlockedBuildDeps';

let src = readFileSync(TARGET, 'utf8');
if (src.includes(MARKER)) {
  console.log('already patched - nothing to do');
  process.exit(0);
}

// ---------------------------------------------------------------- 1. helpers
const OLD_FIX = [
  '/** git 源插件构建被 pnpm 阻止时，自动写入 allowBuilds 并重装一次。 */',
  'async function fixBlockedBuilds(key, profile, installArgs, env) {',
  '\tconst wsPath = join(profileDir(profile), "pnpm-workspace.yaml");',
  '\tlet ws;',
  '\ttry {',
  '\t\tws = await readFile(wsPath, "utf8");',
  '\t} catch {',
  '\t\treturn null;',
  '\t}',
  '\treturn await (async () => {',
  '\t\ttry {',
  "\t\t\tif (!/allowBuilds/.test(ws)) ws += " + P + "\\nallowBuilds:\\n  '${key}': true\\n" + P + ";",
  "\t\t\telse if (!ws.includes(key)) ws = ws.replace(/allowBuilds:/, " + P + "allowBuilds:\\n  '${key}': true" + P + ");",
  '\t\t\tawait writeFile(wsPath, ws, "utf8");',
  '\t\t\treturn await installPlugin(installArgs[installArgs.length - 1], profile, env);',
  '\t\t} catch {',
  '\t\t\treturn null;',
  '\t\t}',
  '\t})();',
  '}',
].join('\n');

// String.raw keeps the emitted code byte-for-byte. The generated code is written
// WITHOUT regex escapes (newline is String.fromCharCode(10), patterns use indexOf
// and split) so no escaping layer can alter it.
const NEW_HELPERS = String.raw`/**
* 从 pnpm 输出解析被阻止构建的精确 depPath。
* pnpm 11 的 allowBuilds 以 depPath 为键（形如 probe-dep@file:../dep-src 或
* pkg@git+https://...#sha）；包名或不完整的键都不会生效。
* 优先读 ERR_PNPM_GIT_DEP_PREPARE_NOT_ALLOWED 的 hint —— 它直接给出正确键。
* @param output pnpm 安装输出
* @returns 去重后的 depPath 列表
*/
function parseBlockedBuildDeps(output) {
	const NL = String.fromCharCode(10);
	const keys = [];
	const push = (raw) => {
		const k = String(raw ?? "").trim().replace(/^['"]|['"]$/g, "");
		if (k && !keys.includes(k)) keys.push(k);
	};
	for (const line of output.split(NL)) {
		const t = line.trim();
		const hint = parseInlineAllowBuildKey(t);
		if (hint !== null) {
			push(hint);
			continue;
		}
		if (t.indexOf("allowBuilds:") !== 0) continue;
		const rest = t.slice(t.indexOf(":") + 1).trim().replace(/^\{|\}$/g, "").trim();
		for (const part of rest.split(",")) push(stripAllowBuildValue(part));
	}
	const marker = output.indexOf("Ignored build scripts:");
	if (marker >= 0) {
		const rest = output.slice(marker + "Ignored build scripts:".length);
		const end = rest.indexOf(NL);
		const list = end >= 0 ? rest.slice(0, end) : rest;
		for (const part of list.split(",")) push(part);
	}
	return keys;
}
/** 去掉 allowBuilds 行尾的 : true / : false。 */
function stripAllowBuildValue(part) {
	const s = String(part ?? "").trim();
	for (const suffix of [": true", ": false"]) {
		if (s.length > suffix.length && s.slice(-suffix.length) === suffix) return s.slice(0, -suffix.length);
	}
	return s;
}
/**
* 把 hint 行解析成 depPath 键，例如
* "git-probe3@git+file:///E:/x#abc: true"。不是该形状时返回 null。
* 从行尾的 ": " 切分，这样路径里的空格和冒号都不会误伤。
* @param line 已 trim 的一行
* @returns depPath 或 null
*/
function parseInlineAllowBuildKey(line) {
	const sep = line.lastIndexOf(": ");
	if (sep <= 0) return null;
	const value = line.slice(sep + 2).trim();
	if (value !== "true" && value !== "false") return null;
	const key = line.slice(0, sep).trim();
	const at = key.indexOf("@");
	if (at <= 0 || key.indexOf("/") < 0) return null;
	return key;
}
/** 输出中是否存在 pnpm 构建脚本阻止信号。 */
function isBuildBlocked(output) {
	return output.indexOf("ERR_PNPM_IGNORED_BUILDS") >= 0
		|| output.indexOf("ERR_PNPM_GIT_DEP_PREPARE_NOT_ALLOWED") >= 0
		|| output.indexOf("Ignored build scripts:") >= 0;
}
/** 目标项目级 pnpm-workspace.yaml：profile 侧优先（嵌套 prepare 会向上找到它）。 */
function profileWorkspacePath(profile) {
	return join(profileDir(profile), "pnpm-workspace.yaml");
}
/** 包名键：pnpm 自己的 allowBuilds 占位模板用的是包名，而不是 depPath。 */
function packageNameOf(depPath) {
	const at = String(depPath ?? "").lastIndexOf("@");
	return at > 0 ? String(depPath).slice(0, at) : String(depPath ?? "");
}
/** 让 allowBuilds 段里某个键生效：把占位值换成 true，缺失才新增一行。 */
function upgradeAllowBuildEntry(lines, key, insertAt) {
	const quoted = "  '" + key + "': true";
	const barePrefix = "  " + key + ":";
	const bareQuoted = "  '" + key + "':";
	const idx = lines.findIndex((l) => l.indexOf(barePrefix) === 0 || l.indexOf(bareQuoted) === 0);
	if (idx >= 0) {
		lines[idx] = quoted;
		return;
	}
	lines.splice(insertAt, 0, quoted);
}
/**
* 在项目级 pnpm-workspace.yaml 写入精确 allowBuilds 键，已有条目一律保留。
* pnpm 在 strictDepBuilds 下会自己生成 allowBuilds 占位模板
* （形如 "  pkg: set this to true or false"），因此这里既要补上 depPath 键，
* 也要把包名占位行改成 true，避免出现重复的 YAML 映射键。
* @param wsPath 目标 pnpm-workspace.yaml
* @param keys 需要放行的 depPath
* @returns 写入的文件路径，未写入时为 null
*/
async function appendAllowBuilds(wsPath, keys) {
	const wanted = (keys ?? []).map((k) => String(k ?? "").trim()).filter(Boolean);
	if (wanted.length === 0) return null;
	try {
		await mkdir(dirname(wsPath), { recursive: true });
	} catch {}
	let text = null;
	try {
		text = await readFile(wsPath, "utf8");
	} catch {}
	const NL = String.fromCharCode(10);
	const lines = (text ?? "").split(NL);
	let section = lines.findIndex((l) => l.indexOf("allowBuilds:") === 0);
	if (section < 0) {
		while (lines.length > 0 && lines[lines.length - 1].trim() === "") lines.pop();
		lines.push("allowBuilds:");
		section = lines.length - 1;
	}
	const insertAt = section + 1;
	for (const key of wanted) {
		const name = packageNameOf(key);
		if (name && name !== key) upgradeAllowBuildEntry(lines, name, insertAt);
		upgradeAllowBuildEntry(lines, key, insertAt);
	}
	await writeFile(wsPath, lines.join(NL), "utf8");
	return wsPath;
}
/**
* 构建脚本被 pnpm 阻止时自动解锁：写入精确 allowBuilds，然后重试安装。
* 两段式 —— 先精确放行（只放行 pnpm 实际点名的包）；仅当精确重试仍失败时，
* 才升级为 dangerouslyAllowAllBuilds，用于覆盖插件 prepare 内部自己发起的
* 嵌套 pnpm install（那个嵌套项目不读 profile 配置，只能靠环境变量继承）。
* @param key 已安装依赖键
* @param profile profile 名
* @param installArgs 原始 dsh 安装参数
* @param env 镜像等环境覆盖
* @param blockedOutput 触发重试的原始输出，用于解析精确 depPath
* @param forceKey 额外必须放行的键（git 源插件自身的 depPath）
*/
async function fixBlockedBuilds(key, profile, installArgs, env, blockedOutput, forceKey) {
	const sourceArg = installArgs[installArgs.length - 1];
	const keys = parseBlockedBuildDeps(blockedOutput ?? "");
	for (const extra of [forceKey, key]) {
		const k = String(extra ?? "").trim();
		if (k && !keys.includes(k)) keys.push(k);
	}
	try {
		await appendAllowBuilds(profileWorkspacePath(profile), keys);
	} catch {}
	const attempt = async (retryEnv) => {
		try {
			return await installPlugin(sourceArg, profile, retryEnv);
		} catch {
			return null;
		}
	};
	const precise = await attempt(env);
	if (precise && precise.code === 0) return precise;
	const escalated = await attempt({
		...(env ?? process.env),
		pnpm_config_dangerously_allow_all_builds: "true"
	});
	return escalated ?? precise;
}`;

// ------------------------------------------------- 2. depPath-aware retry call
const OLD_RETRY = [
  '\t\t\tconst retry = await fixBlockedBuilds(key, profile, [',
  '\t\t\t\t\t"plugin",',
  '\t\t\t\t\t"--profile",',
  '\t\t\t\t\tprofile,',
  '\t\t\t\t\t"add",',
  '\t\t\t\t\ts',
  '\t\t\t\t], env);',
].join('\n');
const NEW_RETRY = OLD_RETRY.replace('], env);', '], env, res.output, name + "@" + s);');

// ------------------------------------------- 3. classify blocked/prepare stage
const OLD_CLASSIFY_HEAD = [
  'function classifyFailReason(output, npmTried, githubTried) {',
  '\tif (/ERR_PNPM_PREPARE_PACKAGE|prepare\\s*Failed|Failed to prepare/i.test(output)) return "github-prepare-failed";',
].join('\n');
const NEW_CLASSIFY_HEAD = [
  'function classifyFailReason(output, npmTried, githubTried) {',
  '\tif (/ERR_PNPM_IGNORED_BUILDS|ERR_PNPM_GIT_DEP_PREPARE_NOT_ALLOWED|Ignored build scripts:/i.test(output)) return "blocked";',
  '\tif (/ERR_PNPM_PREPARE_PACKAGE|prepare\\s*Failed|Failed to prepare/i.test(output)) return "github-prepare-failed";',
].join('\n');

const OLD_HINT_BLOCKED = '\t\tcase "blocked": return "该插件与 Web 环境不兼容，已安全拦截";';
const NEW_HINT_BLOCKED = '\t\tcase "blocked": return "pnpm 拦截了构建脚本：已自动写入精确 allowBuilds 并解锁重试；仍失败说明构建脚本本身出错，可查看日志";';

// ------------------------------------------------------------- 4. exports
const OLD_EXPORT = '\tinstallPlugin: () => installPlugin,';
const NEW_EXPORT = [
  '\tinstallPlugin: () => installPlugin,',
  '\tparseBlockedBuildDeps: () => parseBlockedBuildDeps,',
  '\tisBuildBlocked: () => isBuildBlocked,',
  '\tappendAllowBuilds: () => appendAllowBuilds,',
  '\tfixBlockedBuilds: () => fixBlockedBuilds,',
].join('\n');

const edits = [
  ['helpers', OLD_FIX, NEW_HELPERS],
  ['retry call', OLD_RETRY, NEW_RETRY],
  ['classify', OLD_CLASSIFY_HEAD, NEW_CLASSIFY_HEAD],
  ['hint', OLD_HINT_BLOCKED, NEW_HINT_BLOCKED],
  ['exports', OLD_EXPORT, NEW_EXPORT],
];

const countOf = (h, n) => h.split(n).length - 1;
const problems = [];
for (const [label, oldText] of edits) {
  const n = countOf(src, oldText);
  if (n !== 1) problems.push(`${label}: anchor x${n}`);
}
if (problems.length) {
  console.error('ABORT: unexpected file shape -', problems.join(', '));
  process.exit(1);
}

for (const [, oldText, newText] of edits) src = src.replace(oldText, newText);

// The bundle legitimately contains backticks in its catalog data, so guard only
// on what this patch emits: an emitted backtick would break interpolation.
for (const [label, , newText] of edits) {
  if (newText.includes(P)) {
    const at = newText.indexOf(P);
    console.error(`ABORT: emitted text "${label}" contains a backtick:`, JSON.stringify(newText.slice(Math.max(0, at - 120), at + 60)));
    process.exit(1);
  }
}
for (const must of ['function parseBlockedBuildDeps', 'function isBuildBlocked', 'function appendAllowBuilds',
  'pnpm_config_dangerously_allow_all_builds', 'parseBlockedBuildDeps: () => parseBlockedBuildDeps']) {
  if (!src.includes(must)) {
    console.error('ABORT: patched file missing', must);
    process.exit(1);
  }
}

if (!existsSync(`${TARGET}.pre-patch`)) copyFileSync(TARGET, `${TARGET}.pre-patch`);
writeFileSync(TARGET, src, 'utf8');

// Never leave a broken bundle behind: syntax-check the result and restore on failure.
const check = spawnSync(process.execPath, ['--check', TARGET], { encoding: 'utf8' });
if (check.status !== 0) {
  copyFileSync(`${TARGET}.pre-patch`, TARGET);
  console.error('ABORT: patched file failed node --check; restored original');
  console.error(check.stderr);
  process.exit(1);
}

console.log('patched OK (node --check passed)');
console.log('  bytes:', readFileSync(`${TARGET}.pre-patch`, 'utf8').length, '->', src.length);
console.log('  regions replaced:', edits.length);
