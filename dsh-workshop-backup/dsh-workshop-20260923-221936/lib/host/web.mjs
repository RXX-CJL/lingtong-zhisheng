import { c as getProgress, d as serial, f as testAllMirrors, i as clearMirrorCache, l as installPluginSmart, o as currentMirror, p as uninstallPlugin, r as clearCatalogCache, s as getPendingRestart, t as buildCatalogView, u as resetProgress } from "./core-BcUmZo6v.mjs";
import { spawn } from "node:child_process";
import { dirname, join } from "node:path";
//#region src/host/web.ts
const name = "dsh-workshop-web";
const inject = ["webServer"];
function send(res, status, body) {
	const payload = typeof body === "string" ? body : JSON.stringify(body);
	res.writeHead(status, {
		"content-type": "application/json; charset=utf-8",
		"cache-control": "no-store"
	});
	res.end(payload);
}
function readBody(req) {
	return new Promise((resolvePromise, reject) => {
		let data = "";
		req.on("data", (c) => {
			data += c.toString();
			if (data.length > 65536) reject(/* @__PURE__ */ new Error("body too large"));
		});
		req.on("end", () => {
			try {
				resolvePromise(data ? JSON.parse(data) : {});
			} catch (e) {
				reject(e);
			}
		});
		req.on("error", reject);
	});
}
/**
* 同源校验：阻止跨站请求伪造（CSRF）与端口暴露后的远程滥用。
* 规则：
*  - Host 必须是本机回环地址（127.0.0.1 / localhost / ::1）
*  - 带 Origin/Referer 的请求，来源必须与 Host 一致（浏览器同源）
*  - 无 Origin/Referer 的请求视为本地 CLI/脚本调用，允许
*/
function checkSameOrigin(req) {
	const host = (req.headers.host ?? "").toLowerCase();
	if (!/^(127\.0\.0\.1|localhost|\[::1\])(:\d+)?$/.test(host)) return {
		ok: false,
		reason: `非本机 Host（${host || "空"}），拒绝访问`
	};
	const origin = req.headers.origin ?? "";
	const referer = req.headers.referer ?? "";
	if (!origin && !referer) return { ok: true };
	const m = (origin || referer).toLowerCase().match(/^https?:\/\/([^/]+)/);
	if (!m) return {
		ok: false,
		reason: "无法解析来源"
	};
	if (m[1] !== host) return {
		ok: false,
		reason: `跨站请求被拒绝：来源 ${m[1]} ≠ Host ${host}`
	};
	return { ok: true };
}
function apply(ctx, config) {
	const profile = config.profileName ?? "web";
	const cfg = {
		dataUrl: config.dataUrl,
		backupUrl: config.backupUrl,
		cachePath: config.cachePath,
		profileName: profile
	};
	const route = (method, path, handler) => {
		ctx.effect(() => ctx.webServer.register({
			kind: "exact",
			path,
			handler: (req, res) => {
				if (req.method !== method) {
					send(res, 405, { error: `method ${req.method} not allowed` });
					return;
				}
				handler(req, res);
			}
		}), `dsh-workshop: ${method} ${path}`);
	};
	/** 带同源校验的 POST 路由封装。 */
	const guardedRoute = (method, path, handler) => {
		ctx.effect(() => ctx.webServer.register({
			kind: "exact",
			path,
			handler: (req, res) => {
				if (req.method !== method) {
					send(res, 405, { error: `method ${req.method} not allowed` });
					return;
				}
				const guard = checkSameOrigin(req);
				if (!guard.ok) {
					send(res, 403, { error: guard.reason });
					return;
				}
				handler(req, res);
			}
		}), `dsh-workshop: ${method} ${path} (guarded)`);
	};
	let restartScheduled = false;
	/**
	* 调度服务自动重启：bundle 插件的客户端 manifest 在启动时扫描，
	* 安装/卸载后必须重启才能完整加载（含 UI）。
	* 方案：spawn 独立 node 引导进程（无 shell 字符串拼接），延迟 5s 后
	* 直接以 npx-cli.js 启动新服务（fd 写日志，完全脱离本进程树）；
	* 本进程 4s 后自行退出让出 3080 端口。
	*/
	const scheduleRestart = () => {
		if (restartScheduled) return;
		restartScheduled = true;
		const cwd = process.cwd();
		const logPath = join(cwd, "dsh-web.log");
		const npxCli = join(dirname(process.execPath), "node_modules", "npm", "bin", "npx-cli.js");
		const booterCode = `const {spawn}=require('node:child_process');const {openSync}=require('node:fs');setTimeout(()=>{const out=openSync(${JSON.stringify(logPath)},'a');const c=spawn(process.execPath,[${JSON.stringify(npxCli)},'-y','@deepseek-ai/dsh','web'],{cwd:${JSON.stringify(cwd)},stdio:['ignore',out,out],detached:true,windowsHide:true});c.unref();},5000);`;
		spawn(process.execPath, ["-e", booterCode], {
			stdio: "ignore",
			detached: true,
			windowsHide: true
		}).unref();
		setTimeout(() => process.exit(0), 4e3);
	};
	route("GET", "/dsh-workshop/catalog", async (_req, res) => {
		try {
			send(res, 200, {
				...await buildCatalogView(cfg),
				pendingRestart: getPendingRestart()
			});
		} catch (e) {
			send(res, 500, { error: String(e) });
		}
	});
	route("GET", "/dsh-workshop/installed", async (_req, res) => {
		try {
			const { readInstalled } = await import("./core-BcUmZo6v.mjs").then((n) => n.a);
			send(res, 200, await readInstalled(profile));
		} catch (e) {
			send(res, 500, { error: String(e) });
		}
	});
	route("GET", "/dsh-workshop/progress", async (_req, res) => {
		send(res, 200, getProgress());
	});
	route("GET", "/dsh-workshop/mirror", async (_req, res) => {
		send(res, 200, currentMirror());
	});
	guardedRoute("POST", "/dsh-workshop/mirror/retest", async (_req, res) => {
		try {
			clearMirrorCache();
			const list = await testAllMirrors("omdsh-dev/dsh-tool-time");
			send(res, 200, {
				ok: true,
				chosen: list[0],
				mirrors: list
			});
		} catch (e) {
			send(res, 500, { error: String(e) });
		}
	});
	guardedRoute("POST", "/dsh-workshop/install", async (req, res) => {
		try {
			const body = await readBody(req);
			const source = String(body.source ?? "").trim();
			if (!source) {
				send(res, 400, { error: "缺少 source" });
				return;
			}
			resetProgress();
			const result = await serial(() => installPluginSmart(source, cfg, profile));
			send(res, 200, {
				ok: result.code === 0,
				code: result.code,
				output: result.output.slice(-4e3),
				fallback: result.fallback ?? false,
				usedSource: result.usedSource ?? null,
				hotMount: result.hotMount ?? null,
				restarting: false,
				failReason: result.failReason ?? null,
				failHint: result.failHint ?? null
			});
		} catch (e) {
			send(res, 500, { error: String(e) });
		}
	});
	guardedRoute("POST", "/dsh-workshop/uninstall", async (req, res) => {
		try {
			const body = await readBody(req);
			const id = String(body.id ?? "").trim();
			if (!id) {
				send(res, 400, { error: "缺少 id" });
				return;
			}
			resetProgress();
			const result = await serial(() => uninstallPlugin(id, profile));
			send(res, 200, {
				ok: result.code === 0,
				code: result.code,
				output: result.output.slice(-4e3),
				restarting: false,
				failReason: result.failReason ?? null,
				failHint: result.failHint ?? null
			});
		} catch (e) {
			send(res, 500, { error: String(e) });
		}
	});
	guardedRoute("POST", "/dsh-workshop/refresh", async (_req, res) => {
		try {
			await clearCatalogCache(config.cachePath);
			send(res, 200, {
				ok: true,
				total: (await buildCatalogView(cfg)).plugins.filter((p) => !p.excluded).length
			});
		} catch (e) {
			send(res, 500, { error: String(e) });
		}
	});
	/** 手动重启服务（用户确认后触发；bundle 插件安装/卸载后需要）。 */
	guardedRoute("POST", "/dsh-workshop/restart", async (_req, res) => {
		scheduleRestart();
		send(res, 200, {
			ok: true,
			restarting: true
		});
	});
}
//#endregion
export { apply, inject, name };

//# sourceMappingURL=web.mjs.map