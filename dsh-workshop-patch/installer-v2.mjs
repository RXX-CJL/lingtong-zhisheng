// Comprehensive installer patch for dsh-workshop under DSH 0.1.7-alpha.2 + pnpm 11.
//
// Verified against pnpm 11.7.0 (see these notes because they drive every choice):
//   * allowBuilds keys are DEP PATHS (`pkg@file:../x`), never bare names.
//   * `pnpm_config_*` env vars are parsed by the config reader; `pnpm_config_
//     dangerously_allow_all_builds=true` IS inherited by the nested `pnpm install`
//     spawned from a dependency's prepare script.
//   * A prepare script runs with cwd inside the pnpm store tmp dir
//     (E:/.pnpm-store/v11/tmp/_tmp_*), so a nested install NEVER sees the profile's
//     pnpm-workspace.yaml. Exactly one mechanism reaches it: a global-scope config.
//   * pnpm's global config dir honours XDG_CONFIG_HOME, and globals are only used
//     when the project does not set its own dependency-build options. So an
//     isolated XDG_CONFIG_HOME directory is the clean way to carry a global-scope
//     setting for one install, without touching the user's real global config.
//   * `pnpm_config_allow_builds` cannot be a map, and .pnpmfile.cjs hooks cannot
//     re-enable a blocked script, so allow-all is the only global-scope switch.
//
// Patch is idempotent and only rewrites the regions listed below.
import { readFileSync, writeFileSync, existsSync, copyFileSync, mkdirSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { join } from 'node:path';

const TARGET = process.argv[2] ?? 'C:/Users/ROG/.dsh/profiles/web/node_modules/dsh-workshop/lib/host/core-BcUmZo6v.mjs';
const MARKER = 'pnpm11-build-policy';

let src = readFileSync(TARGET, 'utf8');
if (src.includes(MARKER)) {
  console.log('already patched - nothing to do');
  process.exit(0);
}

// ---------------------------------------------------------------- 1. helpers
// Read the pristine block straight from the file so the anchor can never drift.
const blockStart = src.indexOf('/** git 源插件构建被 pnpm 阻止时');
const blockEnd = src.indexOf('/** npm 包是否存在');
if (blockStart < 0 || blockEnd < 0 || blockEnd < blockStart) {
  console.error('ABORT: could not locate fixBlockedBuilds block');
  process.exit(1);
}
const OLD_FIX_BLOCK = src.slice(blockStart, blockEnd);

const NEW_HELPERS = String.raw`/**
* 从 pnpm 输出解析被阻止构建的精确 depPath（pnpm 11 的 allowBuilds 以 depPath 为键）。
* 兼容三种来源：ERR_PNPM_GIT_DEP_PREPARE_NOT_ALLOWED 的 hint 行、allowBuilds 内联映射、
* 以及 "Ignored build scripts: a@1, b@2" 列表。
* @param output pnpm 安装输出
* @returns 去重后的 depPath 列表
*/
function parseBlockedBuildDeps(output) {
	const NL = String.fromCharCode(10);
	const keys = [];
	const push = (raw) => {
		const k = String(raw == null ? "" : raw).trim().replace(/^['"]|['"]$/g, "");
		if (k && !keys.includes(k)) keys.push(k);
	};
	for (const line of String(output == null ? "" : output).split(NL)) {
		const t = line.trim();
		const hinted = parseInlineAllowBuildKey(t);
		if (hinted !== null) {
			push(hinted);
			continue;
		}
		if (t.indexOf("allowBuilds:") !== 0) continue;
		const rest = t.slice(t.indexOf(":") + 1).trim().replace(/^\{|\}$/g, "").trim();
		for (const part of rest.split(",")) push(stripAllowBuildValue(part));
	}
	const marker = String(output == null ? "" : output).indexOf("Ignored build scripts:");
	if (marker >= 0) {
		const rest = String(output).slice(marker + "Ignored build scripts:".length);
		const end = rest.indexOf(NL);
		const list = end >= 0 ? rest.slice(0, end) : rest;
		for (const part of list.split(",")) push(part);
	}
	return keys;
}
/** 去掉 allowBuilds 行尾的 ": true" / ": false"。 */
function stripAllowBuildValue(part) {
	const s = String(part == null ? "" : part).trim();
	for (const suffix of [": true", ": false"]) {
		if (s.length > suffix.length && s.slice(-suffix.length) === suffix) return s.slice(0, -suffix.length);
	}
	return s;
}
/**
* 把 hint 行解析成 depPath 键，例如 "pkg@git+https://...#abc: true"。
* 从行尾的 ": " 切分，避免路径中的空格或冒号误伤。非该形状返回 null。
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
	const o = String(output == null ? "" : output);
	return o.indexOf("ERR_PNPM_IGNORED_BUILDS") >= 0
		|| o.indexOf("ERR_PNPM_GIT_DEP_PREPARE_NOT_ALLOWED") >= 0
		|| o.indexOf("Ignored build scripts:") >= 0
		|| o.indexOf("is not in the \"allowBuilds\" allowlist") >= 0;
}
/**
* 输出是否是 pnpm 构建策略拒绝（而非插件自身构建失败）。
* prepare 阶段的嵌套安装被策略拦截时，外层只会看到 ERR_PNPM_PREPARE_PACKAGE，
* 因此这里同时检查该包装错误码与嵌套输出里的真实策略信号。
*/
function isBuildPolicyBlocked(output) {
	const o = String(output == null ? "" : output);
	return isBuildBlocked(o)
		|| o.indexOf("ERR_PNPM_GIT_DEP_PREPARE_NOT_ALLOWED") >= 0
		|| o.indexOf("Failed to create bin") >= 0
		|| o.indexOf("ERR_PNPM_PREPARE_PACKAGE") >= 0
		|| o.indexOf("approve-builds") >= 0
		|| o.indexOf("ignoredBuiltDependencies") >= 0
		|| o.indexOf("onlyBuiltDependencies") >= 0;
}
/** 真正的上游构建失败（prepare 自己报错），与策略拦截区分开。 */
function isRealPrepareFailure(output) {
	const o = String(output == null ? "" : output);
	if (isBuildBlocked(o)) return false;
	return /prepare\s*(Failed|failed)|Failed to prepare|ERR_PNPM_PREPARE_PACKAGE/i.test(o);
}
/** 目标项目级 pnpm-workspace.yaml（profile 侧）。 */
function profileWorkspacePath(profile) {
	return join(profileDir(profile), "pnpm-workspace.yaml");
}
/** 包名键：pnpm 的占位模板用包名，而不是 depPath。 */
function packageNameOf(depPath) {
	const at = String(depPath == null ? "" : depPath).lastIndexOf("@");
	return at > 0 ? String(depPath).slice(0, at) : String(depPath == null ? "" : depPath);
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
* @param wsPath 目标 pnpm-workspace.yaml
* @param keys 需要放行的 depPath
* @returns 写入的文件路径，未写入时为 null
*/
async function appendAllowBuilds(wsPath, keys) {
	const wanted = (keys == null ? [] : keys).map((k) => String(k == null ? "" : k).trim()).filter(Boolean);
	if (wanted.length === 0) return null;
	try {
		await mkdir(dirname(wsPath), { recursive: true });
	} catch {}
	let text = null;
	try {
		text = await readFile(wsPath, "utf8");
	} catch {}
	const NL = String.fromCharCode(10);
	const lines = (text == null ? "" : text).split(NL);
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
* 为一次重试创建隔离的全局 pnpm 配置目录。
*
* 为什么需要它：插件的 prepare 脚本在自己的临时目录里再跑一次 pnpm install，
* 该目录不在 profile 之下，读不到 profile 的 pnpm-workspace.yaml，也没有任何
* 项目级配置可写；只有“全局作用域”的配置能影响它（pnpm 仅在项目未设置
* dependency-build 选项时才采用全局值）。该目录只为这一次重试存在，用完即删，
* 绝不触碰用户真实的全局配置。
*
* 放行范围按“最小可用”递进：
*   1) mode = "names"   —— 只放行 pnpm 实际点名的包（包名 + 通用 depPath 形式）
*   2) mode = "all"     —— 仍失败才退化为该目录内的全局 allow-all
*
* @param dir 一次性配置目录
* @param keys pnpm 点名的 depPath 列表
* @param mode "names" | "all"
* @returns 配置目录路径，失败时为 null
*/
async function prepareIsolatedPnpmConfig(dir, keys, mode) {
	try {
		const pnpmDir = join(dir, "pnpm");
		await mkdir(pnpmDir, { recursive: true });
		const NL = String.fromCharCode(10);
		const lines = [
			"# dsh-workshop: temporary pnpm config for ONE install retry.",
			"# Global scope only: reaches the nested pnpm install that a dependency",
			"# prepare script spawns, which cannot see the profile config at all.",
			"# Deleted as soon as the retry finishes."
		];
		const names = [];
		const addName = (n) => {
			const v = String(n == null ? "" : n).trim();
			// npm package names never contain ':' - that would only come from a
			// transport prefix such as "git+file:", which is not a package name.
			if (!v || v.indexOf(":") >= 0) return;
			if (!names.includes(v)) names.push(v);
		};
		for (const key of (keys == null ? [] : keys)) {
			const raw = String(key == null ? "" : key).trim();
			if (!raw) continue;
			// pnpm depPaths look like "pkg@1.2.3", "pkg@file:../x" or
			// "pkg@git+https://host/repo#sha". Take the part before the first "@" as
			// the package name, and keep the full depPath too (harmless, and needed
			// for versioned ids).
			const at = raw.indexOf("@");
			addName(at > 0 ? raw.slice(0, at) : raw);
			addName(raw);
		}
		if (mode === "all") {
			lines.push("dangerouslyAllowAllBuilds: true");
		}
		if (names.length > 0) {
			lines.push("# dependencies pnpm reported as blocked during this install:");
			lines.push("allowBuilds:");
			for (const name of names) lines.push("  " + JSON.stringify(name) + ": true");
		} else if (mode !== "all") {
			lines.push("# nothing precise to allow yet");
		}
		await writeFile(join(pnpmDir, "config.yaml"), lines.join(NL) + NL, "utf8");
		return dir;
	} catch {
		return null;
	}
}
/**
* 构建脚本被 pnpm 策略阻止时的自动解锁重试。
*
* 三阶段：精确放行重试 -> 补充新发现的被阻止依赖再试 -> 隔离全局配置兜底重试。
* 只有最后一步使用 allow-all，且限定在一次性配置目录内；三步都会在返回前清理临时目录。
*
* @param key 已安装依赖键
* @param profile profile 名
* @param installArgs 原始 dsh 安装参数
* @param env 镜像等环境覆盖
* @param blockedOutput 触发重试的原始输出，用于解析精确 depPath
* @param forceKey 额外必须放行的键（git 源插件自身的 depPath）
*/
async function fixBlockedBuilds(key, profile, installArgs, env, blockedOutput, forceKey) {
	const sourceArg = installArgs[installArgs.length - 1];
	return await retryWithBuildPolicyRepair(sourceArg, profile, env, blockedOutput, [forceKey, key]);
}
/**
* 构建策略拒绝的实际重试循环（三阶段，见上）。
* @param sourceArg 传给 dsh plugin add 的源
* @param profile profile 名
* @param env 镜像等环境覆盖
* @param blockedOutput 触发重试的原始输出
* @param extraKeys 额外必须放行的键
* @returns 最后一次尝试的结果
*/
async function retryWithBuildPolicyRepair(sourceArg, profile, env, blockedOutput, extraKeys) {
	const discovered = [];
	const addKeys = (list) => {
		for (const k of list == null ? [] : list) {
			const v = String(k == null ? "" : k).trim();
			if (v && !discovered.includes(v)) discovered.push(v);
		}
	};
	addKeys(parseBlockedBuildDeps(blockedOutput));
	addKeys(extraKeys);
	const wsPath = profileWorkspacePath(profile);
	const attempt = async (retryEnv) => {
		try {
			return await installPlugin(sourceArg, profile, retryEnv);
		} catch {
			return null;
		}
	};
	let last = null;
	let lastWasPolicyBlock = false;
	let sawPolicyBlock = false;
	for (let pass = 0; pass < 2; pass++) {
		try {
			await appendAllowBuilds(wsPath, discovered);
		} catch {}
		last = await attempt(env);
		if (last && last.code === 0) return last;
		lastWasPolicyBlock = isBuildPolicyBlocked(last == null ? "" : last.output);
		if (lastWasPolicyBlock) sawPolicyBlock = true;
		if (!lastWasPolicyBlock) break;
		const newly = parseBlockedBuildDeps(last == null ? "" : last.output).filter((k) => !discovered.includes(k));
		if (newly.length === 0) break;
		addKeys(newly);
	}
	// Sticky: an earlier attempt may have been the policy block while the latest
	// says something else (e.g. prepare wrapper text), so never lose that signal.
	if ((sawPolicyBlock || lastWasPolicyBlock) && discovered.length > 0) {
		const baseEnv = env == null ? process.env : env;
		// Escalate through an isolated global config, least-privilege first:
		//   names -> only the packages pnpm named;  all -> that dir's allow-all.
		// A project-level allowBuilds cannot help a nested install (it runs in a
		// directory that cannot see the profile config), which is why global scope
		// is required here - but it is a throwaway directory, never the user's.
		for (const mode of ["names", "all"]) {
			const isoDir = join(dshHome(), "dsh-workshop", "tmp-config-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 8));
			const prepared = await prepareIsolatedPnpmConfig(isoDir, discovered, mode);
			try {
				if (prepared === null) break;
				const retried = await attempt({ ...baseEnv, XDG_CONFIG_HOME: isoDir });
				if (retried && retried.code === 0) return retried;
				if (retried !== null) {
					last = retried;
					// learn any newly named dependency before the next escalation
					addKeys(parseBlockedBuildDeps(retried.output));
				}
				lastWasPolicyBlock = isBuildPolicyBlocked(last == null ? "" : last.output);
				// keep the precise project-level list in sync for future installs
				try {
					await appendAllowBuilds(wsPath, discovered);
				} catch {}
				if (!lastWasPolicyBlock) break;
			} finally {
				try {
					await rm(isoDir, { recursive: true, force: true });
				} catch {}
			}
		}
	}
	return last;
}
/**
* 解析“这次到底装的是哪个依赖键”：优先 package.json 里的实际键，
* 否则回落到 pnpm 输出里的 "+ pkg" 行，最后才用调用方给的名字。
* @param name 包名
* @param profile profile 名
* @param output pnpm 输出
* @returns 依赖键
*/
async function resolveRepairKey(name, profile, output) {
	try {
		const resolved = await resolveDependencyKey(name, profile);
		if (resolved) return resolved;
	} catch {}
	return parseInstalledKey(output) ?? name;
}
/**
* 安装因 pnpm 构建策略失败时的通用自动修复出口。
* 只处理真正的策略拒绝；网络、构建脚本自身报错等情况原样返回责任给调用方。
* @param sourceArg 传给 dsh plugin add 的源
* @param name 包名
* @param profile profile 名
* @param res 失败的安装结果
* @param env 镜像等环境覆盖
* @returns 修复后的结果；不适用时为 null
*/
async function attemptBuildPolicyRepair(sourceArg, name, profile, res, env) {
	try {
		if (!isBuildPolicyBlocked(res.output)) return null;
		setProgressStage("pnpm 拦截了构建脚本，正在自动放行并重装…", sourceArg);
		const key = await resolveRepairKey(name, profile, res.output);
		// runDsh keeps only the tail of the output, so pnpm's allowBuilds hint line
		// may have been truncated away. Always carry the plugin's own package name
		// and the raw source as candidates in that case.
		const gitish = name + "@" + sourceArg;
		return await retryWithBuildPolicyRepair(sourceArg, profile, env, res.output, [key, gitish, name]);
	} catch {
		return null;
	}
}
`;

// ---------------------------------------------- 2. verify-failed classification
// Anchors are sliced out of the live file because they contain template literals;
// the insertion itself is a small, literal, backtick-free string.
const sliceFrom = (from, to) => {
  const a = src.indexOf(from);
  if (a < 0) { console.error('ABORT: anchor not found:', JSON.stringify(from)); process.exit(1); }
  const b = src.indexOf(to, a);
  if (b < 0) { console.error('ABORT: end anchor not found:', JSON.stringify(to)); process.exit(1); }
  return src.slice(a, b);
};
const insertBefore = (anchorText, needle, inserted) => {
  const at = anchorText.indexOf(needle);
  if (at < 0) { console.error('ABORT: needle not found:', JSON.stringify(needle)); process.exit(1); }
  return anchorText.slice(0, at) + inserted + anchorText.slice(at);
};

const VERIFY_BLOCK = sliceFrom('async function verifyInstalledAndRollback', '/** git 源插件构建被 pnpm 阻止时');
const NEW_VERIFY_BLOCK = insertBefore(
  VERIFY_BLOCK,
  'output: `',
  'failReason: "verify-failed",\n\t\tfailHint: failReasonHint("verify-failed"),\n\t\t',
);

// ------------------------------------------- 3. blocked-by-policy returns carry a reason
const BLOCKED_BLOCK = sliceFrom('\t\t\tfinishProgress(false, "安装被安全策略拒绝");', '\n\t\t}\n\t}\n\tconst { env, mirror }');
const NEW_BLOCKED_BLOCK = insertBefore(
  BLOCKED_BLOCK,
  'output: `',
  'failReason: "blocked",\n\t\t\t\tfailHint: failReasonHint("blocked"),\n\t\t\t\t',
);

// ------------------------- 3b. failure-path auto-repair (initial install non-zero)
// Before this patch the repair only ran when the install EXITED ZERO but the build
// script had been skipped. A real policy block exits non-zero, so nothing repaired it.
const IND = '\t';
/**
* Wrap one branch's `verifyInstalledAndRollback` success path with a
* build-policy auto-repair attempt. A real pnpm policy block makes the install
* exit non-zero, so without this the repair never ran.
*/
const wrapVerifyWithRepair = (text, depth) => {
  const pad = IND.repeat(depth);
  const marker = `${pad}const verified = await verifyInstalledAndRollback`;
  const first = text.indexOf(marker);
  if (first < 0) { console.error(`ABORT: verify marker at depth ${depth} not found`); process.exit(1); }
  if (text.indexOf(marker, first + 1) >= 0) { console.error(`ABORT: verify marker at depth ${depth} is ambiguous`); process.exit(1); }
  return text.slice(0, first)
    + `${pad}const repaired = await attemptBuildPolicyRepair(s, name, profile, res, env);\n`
    + `${pad}if (repaired && repaired.code === 0) {\n`
    + `${pad}${IND}const verified = await verifyInstalledAndRollback(await resolveRepairKey(name, profile, res.output), name, profile, repaired.output, env);\n`
    + `${pad}${IND}finishProgress(verified.code === 0, verified.code === 0 ? "安装完成（已自动放行构建脚本）" : "安装完成（构建仍异常）");\n`
    + `${pad}${IND}return { ...verified };\n`
    + `${pad}}\n`
    + text.slice(first);
};

// --- git branch: install exited non-zero -> repair before giving up --------
const GIT_TAIL = sliceFrom('\t\tif (res.code === 0) {', '\t}\n\tsetProgressStage("检查 npm 源…"');
const GIT_INSTALL = `\t\tconst res = await installPlugin(s, profile, env);\n`;
const GIT_REPAIR_CODE = [
  '\t\tconst repaired = await attemptBuildPolicyRepair(s, name, profile, res, env);',
  '\t\tif (repaired && repaired.code === 0) {',
  '\t\t\tconst verified = await verifyInstalledAndRollback(await resolveRepairKey(name, profile, res.output), name, profile, repaired.output, env);',
  '\t\t\tfinishProgress(verified.code === 0, verified.code === 0 ? "安装完成（已自动放行构建脚本）" : "安装完成（构建仍异常）");',
  '\t\t\treturn { ...verified };',
  '\t\t}',
].join('\n');
const OLD_GIT_INSTALL = GIT_INSTALL;
const NEW_GIT_INSTALL = `${GIT_INSTALL}${GIT_REPAIR_CODE}\n`;

// --- npm branch: previously had no repair at all --------------------------
const OLD_NPM_TAIL = [
  '\t\tif (npmOut.code === 0) {',
  '\t\t\tconst verified = await verifyInstalledAndRollback(parseInstalledKey(npmOut.output) ?? npmName, name, profile, npmOut.output, env);',
  '\t\t\tfinishProgress(verified.code === 0, verified.code === 0 ? "安装完成" : "安装失败");',
  '\t\t\treturn { ...verified };',
  '\t\t}',
].join('\n');
const NEW_NPM_TAIL = [
  '\t\tif (npmOut.code === 0) {',
  '\t\t\tconst verified = await verifyInstalledAndRollback(parseInstalledKey(npmOut.output) ?? npmName, name, profile, npmOut.output, env);',
  '\t\t\tfinishProgress(verified.code === 0, verified.code === 0 ? "安装完成" : "安装失败");',
  '\t\t\treturn { ...verified };',
  '\t\t}',
  '\t\tconst npmRepaired = await attemptBuildPolicyRepair(npmName, name, profile, npmOut, env);',
  '\t\tif (npmRepaired && npmRepaired.code === 0) {',
  '\t\t\tconst verified = await verifyInstalledAndRollback(await resolveRepairKey(name, profile, npmOut.output), name, profile, npmRepaired.output, env);',
  '\t\t\tfinishProgress(verified.code === 0, verified.code === 0 ? "npm 源安装完成（已自动放行构建脚本）" : "npm 源安装完成（构建仍异常）");',
  '\t\t\treturn { ...verified };',
  '\t\t}',
].join('\n');

// --- github fallback branch: repair before the "fallback failed" path ------
const FALLBACK_TAIL = sliceFrom('\tconst gitSource = `github:${full}`;', '\tconst sub = await probeMonorepoSubpackage(full);');
const NEW_FALLBACK_TAIL = wrapVerifyWithRepair(FALLBACK_TAIL, 2);

// --------------------------------------------- 4. richer failure classification
const OLD_CLASSIFY = String.raw`function classifyFailReason(output, npmTried, githubTried) {
	if (/ERR_PNPM_PREPARE_PACKAGE|prepare\s*Failed|Failed to prepare/i.test(output)) return "github-prepare-failed";
	if (/git ls-remote|fatal:|Unable to access|Could not connect|Connection (refused|reset|timed out)|Failed to connect|ETIMEDOUT|ECONNREFUSED|ENOTFOUND/i.test(output)) return "github-network";
	if (/ERR_PNPM_FETCH_404|not in the npm registry|404 - Not Found/i.test(output) && !githubTried) return "npm-not-found";
	if (npmTried && !githubTried && /ERR_PNPM_FETCH_404|not in the npm registry/.test(output)) return "npm-not-found";
	if (npmTried) return "npm-install-failed";
	if (githubTried) return "github-install-failed";
	if (/安装产物校验失败/.test(output)) return "verify-failed";
	return "unknown";
}`;

const NEW_CLASSIFY = String.raw`function classifyFailReason(output, npmTried, githubTried) {
	const o = String(output == null ? "" : output);
	// Order matters: cheapest and most specific signals first.
	if (isBuildBlocked(o)) return "pnpm-build-policy";
	if (isRealPrepareFailure(o)) return "github-prepare-failed";
	if (/ERR_PNPM_GIT_DEP_PREPARE_NOT_ALLOWED/i.test(o)) return "pnpm-build-policy";
	if (/安装产物校验失败/.test(o)) return "verify-failed";
	if (/ERR_PNPM_FETCH_404|not in the npm registry|404 - Not Found|ERR_PNPM_NO_MATCHING_VERSION|No matching version found/i.test(o)) return "npm-not-found";
	if (/git ls-remote|fatal:|Unable to access|Could not connect|Connection (refused|reset|timed out)|Failed to connect|ETIMEDOUT|ECONNREFUSED|ENOTFOUND|Could not resolve host|ERR_PNPM_FETCH_5\d\d|ETIMEDOUT|ERR_PNPM_TARBALL_INTEGRITY|ERR_PNPM_META_FETCH_FAIL/i.test(o)) return "github-network";
	if (/ERR_PNPM_PREPARE_PACKAGE|prepare\s*Failed|Failed to prepare/i.test(o)) return "github-prepare-failed";
	if (/ERR_PNPM_LINKED_PKG_DIR_NOT_FOUND|ERR_PNPM_LINKED_PKG_DIR|ERR_PNPM_MISSING_PKG_NAME|ERR_PNPM_INVALID_|ERR_PNPM_UNSUPPORTED|ERR_PNPM_.*_NOT_SUPPORTED|ERR_PNPM_OUTDATED_LOCKFILE|ERR_PNPM_PEER_DEP_ISSUES/i.test(o)) return "github-install-failed";
	if (npmTried && !githubTried) return "npm-install-failed";
	if (npmTried) return "npm-install-failed";
	if (githubTried) return "github-install-failed";
	return "unknown";
}`;

const OLD_HINT = String.raw`function failReasonHint(reason) {
	switch (reason) {
		case "blocked": return "该插件与 Web 环境不兼容，已安全拦截";
		case "npm-not-found": return "npm 上不存在该包名，已尝试 GitHub 源但仍失败";
		case "npm-install-failed": return "npm 安装失败，可检查网络后重试，或换 GitHub 源";
		case "github-network": return "GitHub 网络连接失败（镜像也不可用），请稍后重试或检查网络";
		case "github-prepare-failed": return "GitHub 源码安装时构建脚本失败（上游仓库问题），可尝试安装 npm 版本或联系作者";
		case "github-install-failed": return "GitHub 源安装失败，可稍后重试";
		case "verify-failed": return "安装产物校验失败，已自动回滚";
		default: return "未知错误，可查看日志或重试";
	}
}`;
const NEW_HINT = String.raw`function failReasonHint(reason) {
	switch (reason) {
		case "blocked": return "该插件与 Web 环境不兼容，已安全拦截";
		case "pnpm-build-policy": return "pnpm 拦截了构建脚本：已自动写入精确 allowBuilds 并重试（含插件 prepare 的嵌套安装），仍失败说明构建脚本本身出错，可查看日志";
		case "prepare-failed": return "插件源码构建（prepare）失败：上游仓库的构建脚本或依赖有问题，可尝试 npm 版本或联系作者";
		case "npm-not-found": return "npm 上不存在该包名，已尝试 GitHub 源但仍失败";
		case "npm-install-failed": return "npm 安装失败，可检查网络后重试，或换 GitHub 源";
		case "github-network": return "GitHub 网络连接失败（镜像也不可用），请稍后重试或检查网络";
		case "github-prepare-failed": return "GitHub 源码安装时构建脚本失败（上游仓库问题），可尝试安装 npm 版本或联系作者";
		case "github-install-failed": return "GitHub 源安装失败，可稍后重试";
		case "verify-failed": return "安装产物校验失败，已自动回滚";
		case "restart-required": return "安装成功但需要重启 dsh web 后完全生效";
		default: return "未知错误：请展开日志查看 pnpm/git 原始输出，或重试";
	}
}`;

// ------------------------------------------------ 5. export new helpers for tests
const OLD_EXPORT = '\tinstallPlugin: () => installPlugin,';
const NEW_EXPORT = [
  '\tinstallPlugin: () => installPlugin,',
  '\tparseBlockedBuildDeps: () => parseBlockedBuildDeps,',
  '\tisBuildBlocked: () => isBuildBlocked,',
  '\tisBuildPolicyBlocked: () => isBuildPolicyBlocked,',
  '\tisRealPrepareFailure: () => isRealPrepareFailure,',
  '\tappendAllowBuilds: () => appendAllowBuilds,',
  '\tprepareIsolatedPnpmConfig: () => prepareIsolatedPnpmConfig,',
  '\tretryWithBuildPolicyRepair: () => retryWithBuildPolicyRepair,',
  '\tattemptBuildPolicyRepair: () => attemptBuildPolicyRepair,',
  '\tresolveRepairKey: () => resolveRepairKey,',
  '\tfixBlockedBuilds: () => fixBlockedBuilds,',
].join('\n');

const edits = [
  ['helpers + fixBlockedBuilds', OLD_FIX_BLOCK, NEW_HELPERS],
  ['verify-failed reason', VERIFY_BLOCK, NEW_VERIFY_BLOCK],
  ['blocked reason', BLOCKED_BLOCK, NEW_BLOCKED_BLOCK],
  ['git-branch repair', OLD_GIT_INSTALL, NEW_GIT_INSTALL],
  ['npm-branch repair', OLD_NPM_TAIL, NEW_NPM_TAIL],
  ['fallback-branch repair', FALLBACK_TAIL, NEW_FALLBACK_TAIL],
  ['classification', OLD_CLASSIFY, NEW_CLASSIFY],
  ['hints', OLD_HINT, NEW_HINT],
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
// Only the hand-written replacement texts must be backtick-free; the two
// source-sliced blocks legitimately carry the original template literals.
const handWritten = new Set(['helpers + fixBlockedBuilds', 'classification', 'hints', 'exports']);
for (const [label, , newText] of edits) {
  if (!handWritten.has(label)) continue;
  if (newText.includes(String.fromCharCode(96))) {
    console.error(`ABORT: emitted text "${label}" contains a backtick`);
    process.exit(1);
  }
}

for (const [, oldText, newText] of edits) src = src.replace(oldText, newText);

// mark the file and make sure `rm` is imported (it is not in the original import list)
const anchor = 'export { core_exports as a';
const anchorAt = src.indexOf(anchor);
if (anchorAt < 0) {
  console.error('ABORT: export anchor not found');
  process.exit(1);
}
src = src.slice(0, anchorAt) + `// [${MARKER}] patched\n` + src.slice(anchorAt);

if (!/import \{[^}]*\brm\b[^}]*\} from "node:fs\/promises"/.test(src)) {
  const oldImport = 'import { mkdir, readFile, writeFile } from "node:fs/promises";';
  if (!src.includes(oldImport)) {
    console.error('ABORT: fs/promises import not found');
    process.exit(1);
  }
  src = src.replace(oldImport, 'import { mkdir, readFile, rm, writeFile } from "node:fs/promises";');
}

for (const must of ['function parseBlockedBuildDeps', 'function isBuildPolicyBlocked', 'function prepareIsolatedPnpmConfig',
  'XDG_CONFIG_HOME', 'dangerouslyAllowAllBuilds', 'pnpm-build-policy']) {
  if (!src.includes(must)) {
    console.error('ABORT: patched file missing', must);
    process.exit(1);
  }
}

if (!existsSync(`${TARGET}.pre-patch`)) copyFileSync(TARGET, `${TARGET}.pre-patch`);
writeFileSync(TARGET, src, 'utf8');

const check = spawnSync(process.execPath, ['--check', TARGET], { encoding: 'utf8' });
if (check.status !== 0) {
  copyFileSync(`${TARGET}.pre-patch`, TARGET);
  console.error('ABORT: node --check failed; restored original');
  console.error(check.stderr);
  process.exit(1);
}
console.log('patched OK (node --check passed)');
console.log('  bytes:', readFileSync(`${TARGET}.pre-patch`, 'utf8').length, '->', src.length);
console.log('  regions replaced:', edits.length);
