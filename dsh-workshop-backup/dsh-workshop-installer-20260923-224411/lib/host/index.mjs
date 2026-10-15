import { l as installPluginSmart, n as categorize, p as uninstallPlugin, r as clearCatalogCache, t as buildCatalogView } from "./core-BcUmZo6v.mjs";
import { defineTool } from "@deepseek-ai/dsh-tools";
//#region src/host/index.ts
/**
* dsh-workshop host 工具半：模型可用的插件搜索 / 安装 / 卸载 / 状态工具。
* 契约：@deepseek-ai/dsh-tools 的 defineTool。
*/
const name = "dsh-workshop";
const inject = ["tools"];
function formatTime(iso) {
	if (!iso) return "—";
	const d = new Date(iso);
	if (Number.isNaN(d.getTime())) return iso;
	return d.toLocaleString("zh-CN", { hour12: false });
}
function apply(ctx, config) {
	const profile = config.profileName ?? "web";
	ctx.tools.register(defineTool({
		name: "workshop_status",
		description: "查看创意工坊状态：本地目录规模与已安装插件列表。",
		parameters: {},
		output: {
			schema: {
				type: "object",
				additionalProperties: false,
				properties: {
					total: { type: "number" },
					generatedAt: { oneOf: [{ type: "string" }, { type: "null" }] },
					installed: {
						type: "array",
						items: { type: "string" }
					}
				}
			},
			render: (_args, value) => [{
				type: "text",
				text: `创意工坊目录共 ${value.total} 个插件（数据 ${formatTime(value.generatedAt)}）\n已安装 ${value.installed.length} 个：\n${value.installed.map((i) => `  - ${i}`).join("\n") || "  （无）"}`
			}]
		},
		async execute() {
			const view = await buildCatalogView(config);
			return {
				total: view.plugins.filter((p) => !p.excluded).length,
				generatedAt: view.meta.generatedAt ?? null,
				installed: view.installed
			};
		}
	}));
	ctx.tools.register(defineTool({
		name: "workshop_search",
		description: "在创意工坊目录中搜索插件（按名称/描述/分类），返回带安装命令的结果。",
		parameters: {
			query: {
				type: "string",
				required: true,
				description: "检索词，如「通知」"
			},
			category: {
				type: "string",
				description: "分类过滤，如「UI 增强」「工具与能力」"
			},
			limit: {
				type: "number",
				description: "返回条数，默认 10，最大 30"
			}
		},
		output: {
			schema: {
				type: "object",
				additionalProperties: false,
				properties: { results: {
					type: "array",
					items: {
						type: "object",
						additionalProperties: false,
						properties: {
							fullName: { type: "string" },
							url: { type: "string" },
							description: { type: "string" },
							stars: { type: "number" },
							score: { type: "number" },
							category: { type: "string" },
							install: { type: "string" }
						}
					}
				} }
			},
			render: (_args, value) => [{
				type: "text",
				text: value.results.length === 0 ? "无匹配结果" : value.results.map((r) => `${r.fullName}（★${r.stars} score ${r.score} · ${r.category}）\n  ${r.description}\n  安装：dsh plugin --profile web add ${r.install}`).join("\n")
			}]
		},
		async execute(args) {
			const view = await buildCatalogView(config);
			const q = args.query.toLowerCase();
			return { results: view.plugins.filter((p) => !p.excluded).filter((p) => !args.category || categorize(p) === args.category).filter((p) => `${p.fullName} ${p.name} ${p.description ?? ""} ${categorize(p)}`.toLowerCase().includes(q)).sort((a, b) => (b.score ?? 0) - (a.score ?? 0)).slice(0, Math.min(args.limit ?? 10, 30)).map((p) => ({
				fullName: p.fullName,
				url: p.url,
				description: p.description ?? "",
				stars: p.stars ?? 0,
				score: p.score ?? 0,
				category: categorize(p),
				install: p.name
			})) };
		}
	}));
	ctx.tools.register(defineTool({
		name: "workshop_install",
		description: "一键安装插件到 web profile：npm 优先，失败自动回退 GitHub 源。",
		parameters: { source: {
			type: "string",
			required: true,
			description: "npm 包名或 github:owner/repo"
		} },
		output: {
			schema: {
				type: "object",
				additionalProperties: false,
				properties: {
					ok: { type: "boolean" },
					output: { type: "string" }
				}
			},
			render: (_args, value) => [{
				type: "text",
				text: value.ok ? `✅ 安装成功（重启 dsh web 后生效）` : `❌ 安装失败，最后 800 字符：\n${value.output.slice(-800)}`
			}]
		},
		async execute(args) {
			const res = await installPluginSmart(args.source, config, profile);
			if (res.code === 0) return {
				ok: true,
				output: res.fallback ? `${res.output}\n（已自动回退 GitHub 源：${res.usedSource}）` : res.output
			};
			return {
				ok: false,
				output: res.output
			};
		}
	}));
	ctx.tools.register(defineTool({
		name: "workshop_uninstall",
		description: "卸载已安装插件（dsh plugin remove + 层栈清理）。",
		parameters: { id: {
			type: "string",
			required: true,
			description: "插件包名，如 dsh-find-plugin"
		} },
		output: {
			schema: {
				type: "object",
				additionalProperties: false,
				properties: {
					ok: { type: "boolean" },
					output: { type: "string" }
				}
			},
			render: (_args, value) => [{
				type: "text",
				text: value.ok ? "✅ 已卸载（重启 dsh web 后完全生效）" : `❌ 卸载失败：\n${value.output.slice(-800)}`
			}]
		},
		async execute(args) {
			const res = await uninstallPlugin(args.id.trim(), profile);
			return {
				ok: res.code === 0,
				output: res.output
			};
		}
	}));
	ctx.tools.register(defineTool({
		name: "workshop_refresh",
		description: "强制刷新本地插件目录（重新下载 registry.json）。",
		parameters: {},
		output: {
			schema: {
				type: "object",
				additionalProperties: false,
				properties: { total: { type: "number" } }
			},
			render: (_args, value) => [{
				type: "text",
				text: `目录已刷新：共 ${value.total} 个插件`
			}]
		},
		async execute() {
			await clearCatalogCache(config.cachePath);
			return { total: (await buildCatalogView(config)).plugins.filter((p) => !p.excluded).length };
		}
	}));
}
//#endregion
export { apply, inject, name };

//# sourceMappingURL=index.mjs.map