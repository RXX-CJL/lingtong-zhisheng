import { spawn } from "node:child_process";
import { readFileSync } from "node:fs";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { homedir } from "node:os";
//#region \0rolldown/runtime.js
var __defProp = Object.defineProperty;
var __exportAll = (all, no_symbols) => {
	let target = {};
	for (var name in all) __defProp(target, name, {
		get: all[name],
		enumerable: true
	});
	if (!no_symbols) __defProp(target, Symbol.toStringTag, { value: "Module" });
	return target;
};
//#endregion
//#region src/data/desc-zh.json
var plugins = [
	{
		"name": "dsh-tianshu-tui",
		"owner": "huiliyi37",
		"url": "https://github.com/huiliyi37/dsh-tianshu-tui",
		"category": "ui",
		"description": {
			"en": "A terminal UI (TUI) for DeepSeek Harness.",
			"zh": "DeepSeek Harness 的终端 UI（TUI）。"
		},
		"install": "dsh plugin --profile web add github:huiliyi37/dsh-tianshu-tui",
		"added": "2026-08-13"
	},
	{
		"name": "deepseek-harness-tui",
		"owner": "openma-ai",
		"url": "https://github.com/openma-ai/deepseek-harness-tui",
		"category": "ui",
		"description": {
			"en": "A Rust/ratatui terminal client that speaks the DSH SDK JSON-RPC protocol directly and runs standalone or as a profile bundle.",
			"zh": "Rust/ratatui 终端客户端，直接使用 DSH SDK JSON-RPC 协议，支持独立运行或作为 profile bundle 加载。"
		},
		"install": "dsh plugin --profile web add github:openma-ai/deepseek-harness-tui",
		"added": "2026-08-14"
	},
	{
		"name": "dsh-at-file",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/dsh-at-file",
		"category": "ui",
		"description": {
			"en": "Codex-style `@file` mentions: search workspace files in the composer and attach their contents to prompts.",
			"zh": "Codex 风格的 `@file` 文件引用，输入框里直接搜索并引用工作区文件。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/dsh-at-file",
		"added": "2026-08-13"
	},
	{
		"name": "ui-status-label",
		"owner": "alingalingling",
		"url": "https://github.com/alingalingling/ui-status-label",
		"category": "ui",
		"description": {
			"en": "Customize the \"deep diving\" thinking status label to anything you like.",
			"zh": "把鲸鱼娘思考时的 \"deep diving\" 状态文案自定义成任意你想要的样子。"
		},
		"install": "dsh plugin --profile web add github:alingalingling/ui-status-label",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-openpencil",
		"owner": "ZSeven-W",
		"url": "https://github.com/ZSeven-W/dsh-openpencil",
		"category": "ui",
		"description": {
			"en": "OpenPencil design preview and editing plugin.",
			"zh": "OpenPencil 设计预览与编辑插件。"
		},
		"install": "dsh plugin --profile web add github:ZSeven-W/dsh-openpencil",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-visualize",
		"owner": "Nagi-ovo",
		"url": "https://github.com/Nagi-ovo/dsh-visualize",
		"category": "ui",
		"description": {
			"en": "In-conversation generative UI: the model renders interactive HTML cards into the chat stream, with streaming preview and sandboxed rendering.",
			"zh": "对话内生成式 UI：模型把交互式 HTML 卡片直接画进会话流，带流式预览与沙箱渲染。"
		},
		"install": "dsh plugin --profile web add github:Nagi-ovo/dsh-visualize",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-side-panel",
		"owner": "ccq1",
		"url": "https://github.com/ccq1/dsh-side-panel",
		"category": "ui",
		"description": {
			"en": "Side panel with file browser, terminal, and Git review for quick file previews.",
			"zh": "侧边栏集成文件浏览器、终端和 Git 审查，方便预览文件。"
		},
		"install": "dsh plugin --profile web add github:ccq1/dsh-side-panel",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-focus-chat",
		"owner": "dingyi222666",
		"url": "https://github.com/dingyi222666/dsh-focus-chat",
		"category": "ui",
		"description": {
			"en": "A \"focus chat\" minimal view that shows only final outputs.",
			"zh": "「聚焦会话」精简视图，只关注最终产出结果。"
		},
		"install": "dsh plugin --profile web add github:dingyi222666/dsh-focus-chat",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-genui",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/dsh-genui",
		"category": "ui",
		"description": {
			"en": "Interactive UI components rendered inline in replies: layout, charts, forms, quizzes, mermaid, 3D scenes, and an action event loop back to the model.",
			"zh": "助手回复内渲染交互式 UI 组件：布局、图表、表单、测验、mermaid、3D 场景与回传事件循环。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/dsh-genui",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-annotation",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/dsh-annotation",
		"category": "ui",
		"description": {
			"en": "Select text → annotate → send with your message; replies map back to each annotation.",
			"zh": "选中文字→批注→随消息发送，回复按批注逐条对照。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/dsh-annotation",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-navbar",
		"owner": "vlln",
		"url": "https://github.com/vlln/dsh-navbar",
		"category": "ui",
		"description": {
			"en": "Conversation node navigation bar for quick jumps between user messages.",
			"zh": "对话节点导航条，右缘节点串快速跳转 user 消息。"
		},
		"install": "dsh plugin --profile web add github:vlln/dsh-navbar",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-task-status",
		"owner": "vlln",
		"url": "https://github.com/vlln/dsh-task-status",
		"category": "ui",
		"description": {
			"en": "Background task status bar: progress plus live output tail on the chat page.",
			"zh": "后台任务状态条：对话页任务进度 + 实时输出 tail。"
		},
		"install": "dsh plugin --profile web add github:vlln/dsh-task-status",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-web-archive",
		"owner": "renat3u",
		"url": "https://github.com/renat3u/dsh-web-archive",
		"category": "ui",
		"description": {
			"en": "Collapse noisy messages (Think, Bash, etc.) in conversations.",
			"zh": "折叠对话中的 Think、Bash 等「无用消息」。"
		},
		"install": "dsh plugin --profile web add github:renat3u/dsh-web-archive",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-spotlight",
		"owner": "0xsline",
		"url": "https://github.com/0xsline/dsh-spotlight",
		"category": "ui",
		"description": {
			"en": "Keyboard-first command palette for the DSH Web UI.",
			"zh": "键盘优先的命令面板（command palette）。"
		},
		"install": "dsh plugin --profile web add github:0xsline/dsh-spotlight",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-101",
		"owner": "bill9109",
		"url": "https://github.com/bill9109/dsh-101",
		"category": "ui",
		"description": {
			"en": "Document reading mode for DSH.",
			"zh": "DSH 文档阅读模式。"
		},
		"install": "dsh plugin --profile web add github:bill9109/dsh-101",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-drag-and-drop",
		"owner": "bill9109",
		"url": "https://github.com/bill9109/dsh-drag-and-drop",
		"category": "ui",
		"description": {
			"en": "Cross-platform file drag-and-drop with raw path insertion, no file copying.",
			"zh": "跨平台文件拖拽与原始路径插入，无需复制文件。"
		},
		"install": "dsh plugin --profile web add github:bill9109/dsh-drag-and-drop",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-deeplink",
		"owner": "qyw233",
		"url": "https://github.com/qyw233/dsh-deeplink",
		"category": "ui",
		"description": {
			"en": "Deep links: open a specific session or workspace via `?session=` / `?workspace=`.",
			"zh": "`?session=` / `?workspace=` 深链直达指定项目对话。"
		},
		"install": "dsh plugin --profile web add github:qyw233/dsh-deeplink",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-diff-viewer",
		"owner": "lehhair",
		"url": "https://github.com/lehhair/dsh-diff-viewer",
		"category": "ui",
		"description": {
			"en": "PiUI-style diff viewer replacing the stock DiffBlock for write/edit tool calls.",
			"zh": "PiUI 风格 diff 查看器，替换 write/edit 工具调用的默认 DiffBlock。"
		},
		"install": "dsh plugin --profile web add github:lehhair/dsh-diff-viewer",
		"added": "2026-08-13"
	},
	{
		"name": "ex-setting",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/ex-setting",
		"category": "ui",
		"description": {
			"en": "Settings extensions for DSH.",
			"zh": "DSH 的设置扩展。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/ex-setting",
		"added": "2026-08-13"
	},
	{
		"name": "web-components",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/web-components",
		"category": "ui",
		"description": {
			"en": "Web Components support.",
			"zh": "Web Components 支持。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/web-components",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-turn-navigator",
		"owner": "vibeinging",
		"url": "https://github.com/vibeinging/dsh-turn-navigator",
		"category": "ui",
		"description": {
			"en": "Turn navigation for the DSH Web UI.",
			"zh": "对话轮次导航。"
		},
		"install": "dsh plugin --profile web add github:vibeinging/dsh-turn-navigator",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-milestone",
		"owner": "SnowCrescenter-tech",
		"url": "https://github.com/SnowCrescenter-tech/dsh-milestone",
		"category": "ui",
		"description": {
			"en": "Right-side dot-timeline rail: jump between user messages.",
			"zh": "右侧圆点时间轴导航条，点击跳转到任意用户消息。"
		},
		"install": "dsh plugin --profile web add github:SnowCrescenter-tech/dsh-milestone",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-balance-meter",
		"owner": "Ghost011118",
		"url": "https://github.com/Ghost011118/dsh-balance-meter",
		"category": "ui",
		"description": {
			"en": "DeepSeek account balance and session cost in the composer dock, with auto-fetched official pricing and peak/off-peak support.",
			"zh": "输入框 dock 显示 DeepSeek 账户余额与会话花费，自动拉取官方定价，支持高峰/低谷计价。"
		},
		"install": "dsh plugin --profile web add github:Ghost011118/dsh-balance-meter",
		"added": "2026-08-14"
	},
	{
		"name": "dsh-cc-tui",
		"owner": "ccch1mneyyy",
		"url": "https://github.com/ccch1mneyyy/dsh-cc-tui",
		"category": "ui",
		"description": {
			"en": "Claude Code-style full-screen terminal UI: pixel-whale header, live status line, and streaming thought expansion.",
			"zh": "Claude Code 风格全屏终端 UI：像素鲸鱼顶栏、实时工作状态行、思考流式展开。"
		},
		"install": "dsh plugin --profile web add github:ccch1mneyyy/dsh-cc-tui",
		"added": "2026-08-14"
	},
	{
		"name": "DSH-better-sidebar",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/DSH-better-sidebar",
		"category": "ui",
		"description": {
			"en": "Full sidebar workbench with file rendering and editing, terminal, Git, and subagents; third-party plugins can register new tabs.",
			"zh": "侧边栏完整工作台：内置文件渲染编辑、终端、Git 与子代理，支持三方插件注册新 Tab。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/DSH-better-sidebar",
		"added": "2026-08-14"
	},
	{
		"name": "dsh-turn-rewind",
		"owner": "Anionex",
		"url": "https://github.com/Anionex/dsh-turn-rewind",
		"category": "session",
		"description": {
			"en": "Rewind conversation and workspace state, powered by a persistent Change Ledger.",
			"zh": "对话回退：基于持久 Change Ledger 回滚会话与工作区状态。"
		},
		"install": "dsh plugin --profile web add github:Anionex/dsh-turn-rewind",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-crosstalk",
		"owner": "Jesse-njx",
		"url": "https://github.com/Jesse-njx/dsh-crosstalk",
		"category": "session",
		"description": {
			"en": "Cross-session messaging for DSH: any session on the machine can list and message any other, Claude Code-style, via a local heartbeat registry and inbox.",
			"zh": "跨会话消息：本机任意会话都可像 Claude Code 一样列出并互发消息，基于本地心跳注册表与收件箱。"
		},
		"install": "dsh plugin --profile web add github:Jesse-njx/dsh-crosstalk",
		"added": "2026-08-14"
	},
	{
		"name": "distill",
		"owner": "LoserFox",
		"url": "https://github.com/LoserFox/distill",
		"category": "session",
		"description": {
			"en": "Automatic conversation distillation: background subagent reflection + skill create/update.",
			"zh": "自动对话蒸馏：后台 subagent 反省 + 技能 create/update。"
		},
		"install": "dsh plugin --profile web add github:LoserFox/distill",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-share",
		"owner": "hellodigua",
		"url": "https://github.com/hellodigua/dsh-share",
		"category": "session",
		"description": {
			"en": "Share your conversations with one click.",
			"zh": "一键分享你的对话。"
		},
		"install": "dsh plugin --profile web add github:hellodigua/dsh-share",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-message-edit",
		"owner": "Moeblack",
		"url": "https://github.com/Moeblack/dsh-message-edit",
		"category": "session",
		"description": {
			"en": "Branch-based message editing, reroll, retry, and a version timeline.",
			"zh": "基于分支的消息编辑、reroll、重试与版本时间线。"
		},
		"install": "dsh plugin --profile web add github:Moeblack/dsh-message-edit",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-mnemon",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/dsh-mnemon",
		"category": "session",
		"description": {
			"en": "Deep Mnemon integration: local three-tier memory (Runtime Memory, retrievable Documents, supervised Memory Spaces).",
			"zh": "Mnemon 深度集成：本地三层记忆（Runtime Memory、可检索 Documents、受监督 Memory Spaces）。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/dsh-mnemon",
		"added": "2026-08-13"
	},
	{
		"name": "nowledge-mem-deepseek-harness",
		"owner": "nowledge-co",
		"url": "https://github.com/nowledge-co/nowledge-mem-deepseek-harness",
		"category": "session",
		"description": {
			"en": "One memory layer for every AI tool and agent: Context Bundle injection, prompt-time recall, MCP tools, and turn-end DSH thread capture.",
			"zh": "给所有 AI 工具和 Agent 共用的一层记忆：注入 Context Bundle、提示时检索、MCP 工具与回合结束 DSH 线程捕获。"
		},
		"install": "dsh plugin --profile web add github:nowledge-co/nowledge-mem-deepseek-harness",
		"added": "2026-08-14"
	},
	{
		"name": "dsh-memory",
		"owner": "Jesse-njx",
		"url": "https://github.com/Jesse-njx/dsh-memory",
		"category": "session",
		"description": {
			"en": "Cited memory over DSH's lossless session log: distilled facts carry `(sessionId, eventRange)` citations that expand back to the exact original log excerpt.",
			"zh": "基于 DSH 无损会话日志的引用式记忆：蒸馏出的事实带 `(sessionId, eventRange)` 引用，可随时展开回原始日志片段。"
		},
		"install": "dsh plugin --profile web add github:Jesse-njx/dsh-memory",
		"added": "2026-08-14"
	},
	{
		"name": "dsh-sidechain",
		"owner": "Buyi-wsgzg",
		"url": "https://github.com/Buyi-wsgzg/dsh-sidechain",
		"category": "session",
		"description": {
			"en": "`/side` persistent side sessions and `/btw` one-shot side questions, run in a temporary fork without touching main history.",
			"zh": "`/side` 持续性侧会话与 `/btw` 一次性侧问，在临时 fork 中运行、不写入主会话历史。"
		},
		"install": "dsh plugin --profile web add github:Buyi-wsgzg/dsh-sidechain",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-conversation-share",
		"owner": "bill9109",
		"url": "https://github.com/bill9109/dsh-conversation-share",
		"category": "session",
		"description": {
			"en": "Share any excerpt of a conversation.",
			"zh": "分享任意段落的对话。"
		},
		"install": "dsh plugin --profile web add github:bill9109/dsh-conversation-share",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-explain",
		"owner": "yuezengwu",
		"url": "https://github.com/yuezengwu/dsh-explain",
		"category": "session",
		"description": {
			"en": "Local-first learning mode: cross-session learning threads with per-source explanations.",
			"zh": "本地优先学习模式：跨会话全局学习线程、按来源讲解。"
		},
		"install": "dsh plugin --profile web add github:yuezengwu/dsh-explain",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-prompt-studio",
		"owner": "Moeblack",
		"url": "https://github.com/Moeblack/dsh-prompt-studio",
		"category": "session",
		"description": {
			"en": "Edit user and built-in system-prompt sections with live preview.",
			"zh": "带实时预览的用户/内置 system prompt 分节编辑器。"
		},
		"install": "dsh plugin --profile web add github:Moeblack/dsh-prompt-studio",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-chat-import",
		"owner": "Nwflower",
		"url": "https://github.com/Nwflower/dsh-chat-import",
		"category": "session",
		"description": {
			"en": "Import Claude Code / Codex / ChatGPT / Cursor chat histories as resumable DeepSeek Harness sessions.",
			"zh": "把 Claude Code / Codex / ChatGPT / Cursor 的聊天记录全保真导入为可续聊的 DSH 会话。"
		},
		"install": "dsh plugin --profile web add github:Nwflower/dsh-chat-import",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-interconnect",
		"owner": "Chinesezjc",
		"url": "https://github.com/Chinesezjc/dsh-interconnect",
		"category": "session",
		"description": {
			"en": "Cross-instance message and event handoff between DSH instances via an interconnect server.",
			"zh": "跨实例互联：经 interconnect 服务在多个 DSH 实例间转发消息与事件。"
		},
		"install": "dsh plugin --profile web add github:Chinesezjc/dsh-interconnect",
		"added": "2026-08-14"
	},
	{
		"name": "dsh-vision-toolkit",
		"owner": "Anionex",
		"url": "https://github.com/Anionex/dsh-vision-toolkit",
		"category": "tools",
		"description": {
			"en": "Vision tasks for text-only models: intent-aware image Q&A, long-screenshot OCR, UI reproduction, grounding, and pixel diff.",
			"zh": "让纯文本模型更好地做视觉任务：带意图的图片问答、长截图 OCR、UI 还原等。"
		},
		"install": "dsh plugin --profile web add github:Anionex/dsh-vision-toolkit",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-custom-tool",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/dsh-custom-tool",
		"category": "tools",
		"description": {
			"en": "Create and manage sandboxed JavaScript tools with a Monaco editor and model-driven tool lifecycle.",
			"zh": "用 Monaco 编辑器创建和管理沙箱化的自定义 JavaScript 工具。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/dsh-custom-tool",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-computer-use",
		"owner": "Anionex",
		"url": "https://github.com/Anionex/dsh-computer-use",
		"category": "tools",
		"description": {
			"en": "Accessibility-first macOS computer use: fresh observations, stale-state rejection, scoped permissions, and safe input.",
			"zh": "macOS 电脑控制：Accessibility 观测、过期状态拒绝、作用域权限与安全输入。"
		},
		"install": "dsh plugin --profile web add github:Anionex/dsh-computer-use",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-data-agent",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/dsh-data-agent",
		"category": "tools",
		"description": {
			"en": "Let the AI connect to databases and write SQL for you.",
			"zh": "让 AI 帮你连数据库、写 SQL。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/dsh-data-agent",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-toolkit",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/dsh-toolkit",
		"category": "tools",
		"description": {
			"en": "Zero-dependency toolkit: time / encoding / json / calculator / csv / regex / markdown / diff / stat / schema — ten deterministic tools in one install.",
			"zh": "零依赖工具包：time / encoding / json / calculator / csv / regex / markdown / diff / stat / schema 十件套一键安装。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/dsh-toolkit",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-tool-csv",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/dsh-tool-csv",
		"category": "tools",
		"description": {
			"en": "Parse/query/aggregate/convert CSV (RFC 4180) with a zero-dependency state-machine parser.",
			"zh": "CSV 解析/查询/统计/转换（RFC 4180），零依赖状态机解析器。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/dsh-tool-csv",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-tool-calculator",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/dsh-tool-calculator",
		"category": "tools",
		"description": {
			"en": "Safe math expression evaluator, zero-dependency recursive-descent parser.",
			"zh": "安全的数学表达式求值器，零依赖递归下降解析器。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/dsh-tool-calculator",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-tool-diff",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/dsh-tool-diff",
		"category": "tools",
		"description": {
			"en": "Structured comparison and unified diffs for text/JSON/CSV/Markdown.",
			"zh": "文本/JSON/CSV/Markdown 结构化比较与 unified diff。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/dsh-tool-diff",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-tool-encoding",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/dsh-tool-encoding",
		"category": "tools",
		"description": {
			"en": "base64/url/hex encoding, common hashes, and UUID generation.",
			"zh": "base64/url/hex 编解码、常用哈希、UUID 生成。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/dsh-tool-encoding",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-tool-json",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/dsh-tool-json",
		"category": "tools",
		"description": {
			"en": "JSON queries with a JMESPath subset.",
			"zh": "JMESPath 子集 JSON 查询。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/dsh-tool-json",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-tool-markdown",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/dsh-tool-markdown",
		"category": "tools",
		"description": {
			"en": "HTML↔Markdown conversion, GFM table normalization, and TOC generation.",
			"zh": "HTML↔Markdown 转换、GFM 表格规范化、目录生成。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/dsh-tool-markdown",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-tool-regex",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/dsh-tool-regex",
		"category": "tools",
		"description": {
			"en": "Test/extract/safe-replace/statically explain regexes without executing code.",
			"zh": "正则测试/提取/安全替换/静态解释（不执行代码）。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/dsh-tool-regex",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-tool-schema",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/dsh-tool-schema",
		"category": "tools",
		"description": {
			"en": "JSON Schema validation: validate/paths/explain/normalize.",
			"zh": "JSON Schema 验证：validate/paths/explain/normalize。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/dsh-tool-schema",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-tool-stat",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/dsh-tool-stat",
		"category": "tools",
		"description": {
			"en": "Descriptive statistics, percentiles, frequency distributions, and correlation.",
			"zh": "描述统计/百分位数/频数分布/相关性。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/dsh-tool-stat",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-tool-time",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/dsh-tool-time",
		"category": "tools",
		"description": {
			"en": "Strict ISO 8601 parsing, IANA timezone conversion, and UTC calendar arithmetic.",
			"zh": "严格 ISO 8601 解析、IANA 时区转换、UTC 日历运算。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/dsh-tool-time",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-kb-sieve",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/dsh-kb-sieve",
		"category": "tools",
		"description": {
			"en": "Build auditable KB packs (SQLite FTS5) from md/txt/docx/pdf with deterministic retrieval and original-text reading.",
			"zh": "从 md/txt/docx/pdf 构建可审计知识库包（SQLite FTS5），确定性检索与原文阅读。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/dsh-kb-sieve",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-plugin-mineru",
		"owner": "HuanLinOTO",
		"url": "https://github.com/HuanLinOTO/dsh-plugin-mineru",
		"category": "tools",
		"description": {
			"en": "Expose MineRU document parsing tools to the model.",
			"zh": "向模型暴露 MineRU 文档解析工具。"
		},
		"install": "dsh plugin --profile web add github:HuanLinOTO/dsh-plugin-mineru",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-cowork",
		"owner": "Jesse-njx",
		"url": "https://github.com/Jesse-njx/dsh-cowork",
		"category": "tools",
		"description": {
			"en": "Bounded, cell-addressed `doc_read`/`doc_write` for xlsx / pdf / docx / pptx / ipynb, plus an MCP server and CLI.",
			"zh": "doc_read/doc_write：以有界、单元格寻址的方式读写 xlsx / pdf / docx / pptx / ipynb，另附 MCP 服务器与 CLI。"
		},
		"install": "dsh plugin --profile web add github:Jesse-njx/dsh-cowork",
		"added": "2026-08-14"
	},
	{
		"name": "dsh-skillport",
		"owner": "Jesse-njx",
		"url": "https://github.com/Jesse-njx/dsh-skillport",
		"category": "tools",
		"description": {
			"en": "Bring your existing Agent Skills (SKILL.md) library to DSH: discover skills across Claude/Codex/Cursor/Gemini paths, inject a progressive-disclosure index, and load bodies on demand.",
			"zh": "把已有的 Agent Skills（SKILL.md）技能库带进 DSH：扫描 Claude/Codex/Cursor/Gemini 技能目录、注入渐进式索引，按需加载技能正文。"
		},
		"install": "dsh plugin --profile web add github:Jesse-njx/dsh-skillport",
		"added": "2026-08-14"
	},
	{
		"name": "dsh-tool-search",
		"owner": "vibeinging",
		"url": "https://github.com/vibeinging/dsh-tool-search",
		"category": "tools",
		"description": {
			"en": "Per-agent on-demand tool discovery and progressive schema disclosure.",
			"zh": "按 agent 的按需工具发现与渐进式 schema 披露。"
		},
		"install": "dsh plugin --profile web add github:vibeinging/dsh-tool-search",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-openmaic",
		"owner": "THU-MAIC",
		"url": "https://github.com/THU-MAIC/dsh-openmaic",
		"category": "tools",
		"description": {
			"en": "OpenMAIC: classrooms, slides, interactive widgets, and Socratic teaching.",
			"zh": "OpenMAIC 教学：课堂、幻灯片、交互组件与苏格拉底式教学。"
		},
		"install": "dsh plugin --profile web add github:THU-MAIC/dsh-openmaic",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-scholar",
		"owner": "lzszq",
		"url": "https://github.com/lzszq/dsh-scholar",
		"category": "tools",
		"description": {
			"en": "Academic assistant plugin.",
			"zh": "学术助手插件。"
		},
		"install": "dsh plugin --profile web add github:lzszq/dsh-scholar",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-apple-mode",
		"owner": "jihongboo",
		"url": "https://github.com/jihongboo/dsh-apple-mode",
		"category": "tools",
		"description": {
			"en": "Xcode AI integration for DSH: 26 Xcode MCP tools (mcpbridge) + Apple platform skills + Xcode Intelligence-style persona (agent preset or global bundle).",
			"zh": "DSH 的 Xcode AI 集成：26 个 Xcode MCP 工具（mcpbridge）+ Apple 平台技能 + Xcode Intelligence 风格 persona（agent preset 或全局 bundle）。"
		},
		"install": "dsh plugin --profile web add github:jihongboo/dsh-apple-mode",
		"added": "2026-08-14"
	},
	{
		"name": "dsh-continual-evolve",
		"owner": "ZK-Andy",
		"url": "https://github.com/ZK-Andy/dsh-continual-evolve",
		"category": "tools",
		"description": {
			"en": "Continual self-evolution: versioned, auditable, rollback-safe harness state (prompts, memory, skills, subagent specs) refined from session trajectories, with review gates and hot-reloaded skills.",
			"zh": "持续自进化：从会话轨迹沉淀版本化、可审计、可回滚的 harness 状态（提示词/记忆/技能/子代理规格），带审查门禁与技能热加载。"
		},
		"install": "dsh plugin --profile web add github:ZK-Andy/dsh-continual-evolve",
		"added": "2026-08-14"
	},
	{
		"name": "dsh-recommend",
		"owner": "zp-home",
		"url": "https://github.com/zp-home/dsh-recommend",
		"category": "tools",
		"description": {
			"en": "Transparent rankings and recommendations for the DSH plugin ecosystem: daily auto-fetched topic data, an open scoring model, and rank/search/recommend tools with a settings-page leaderboard.",
			"zh": "DSH 插件透明排行与推荐：每日自动抓取 `dsh-plugin` 话题生态，公开评分模型，提供 rank/search/recommend 工具与设置页榜单。"
		},
		"install": "dsh plugin --profile web add github:zp-home/dsh-recommend",
		"added": "2026-08-14"
	},
	{
		"name": "modlens",
		"owner": "liustack",
		"url": "https://github.com/liustack/modlens",
		"category": "tools",
		"description": {
			"en": "Vision bridge for text-only models: paste an image, get structured JSON evidence (OCR, layout, semantics).",
			"zh": "为纯文本模型架起视觉桥梁：粘贴图片，输出结构化 JSON 证据（OCR、版面、语义）。"
		},
		"install": "dsh plugin --profile web add github:liustack/modlens",
		"added": "2026-08-14"
	},
	{
		"name": "dsh_workflow",
		"owner": "icetomoyo",
		"url": "https://github.com/icetomoyo/dsh_workflow",
		"category": "workflow",
		"description": {
			"en": "UltraCode-style multi-agent orchestration: a generatable, savable, governable, observable, resumable workflow layer.",
			"zh": "把 UltraCode 式多 Agent 调度带给 DSH：可生成、可保存、可治理、可观察、可恢复的 Workflow 层。"
		},
		"install": "dsh plugin --profile web add github:icetomoyo/dsh_workflow",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-agent-teams",
		"owner": "NanmiCoder",
		"url": "https://github.com/NanmiCoder/dsh-agent-teams",
		"category": "workflow",
		"description": {
			"en": "AgentTeams multi-agent teams.",
			"zh": "AgentTeams 多智能体团队。"
		},
		"install": "dsh plugin --profile web add github:NanmiCoder/dsh-agent-teams",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-automation",
		"owner": "titanwings",
		"url": "https://github.com/titanwings/dsh-automation",
		"category": "workflow",
		"description": {
			"en": "Scheduled coding runs in fresh agent sessions with auditable history.",
			"zh": "定时任务：让 Coding 任务按计划在全新 Agent Session 中运行，保留可审计历史。"
		},
		"install": "dsh plugin --profile web add github:titanwings/dsh-automation",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-routines",
		"owner": "Jesse-njx",
		"url": "https://github.com/Jesse-njx/dsh-routines",
		"category": "workflow",
		"description": {
			"en": "Scheduled agents on a cron: run a prompt on a schedule and get the digest where you already are, with overlap/missed-run/timeout safety defaults.",
			"zh": "定时 Agent：按 cron 计划运行 prompt，把摘要送到你已有的地方，内置重叠/漏跑/超时安全策略。"
		},
		"install": "dsh plugin --profile web add github:Jesse-njx/dsh-routines",
		"added": "2026-08-14"
	},
	{
		"name": "dsh-plannotator",
		"owner": "titanwings",
		"url": "https://github.com/titanwings/dsh-plannotator",
		"category": "workflow",
		"description": {
			"en": "Plan review with anchored annotations and structured feedback back to the agent.",
			"zh": "计划批注：选中计划原文逐条批注，结构化反馈送回 Agent。"
		},
		"install": "dsh plugin --profile web add github:titanwings/dsh-plannotator",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-loop",
		"owner": "vlln",
		"url": "https://github.com/vlln/dsh-loop",
		"category": "workflow",
		"description": {
			"en": "Recurring loops: `/loop` command + loop tool + activity status bar.",
			"zh": "定时循环：`/loop` 命令 + loop 工具 + 活动状态条。"
		},
		"install": "dsh plugin --profile web add github:vlln/dsh-loop",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-sentinel",
		"owner": "fuhefei",
		"url": "https://github.com/fuhefei/dsh-sentinel",
		"category": "workflow",
		"description": {
			"en": "Condition-driven wakeup: durable file/command/http/process/webhook watches that wake the agent.",
			"zh": "条件驱动唤醒：file/command/http/process/webhook 持久监视，触发即唤醒 agent。"
		},
		"install": "dsh plugin --profile web add github:fuhefei/dsh-sentinel",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-deep-research",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/dsh-deep-research",
		"category": "workflow",
		"description": {
			"en": "Adaptive deep-research orchestrator built on the official workflow engine.",
			"zh": "自适应深度研究编排器（基于官方 workflow 引擎）。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/dsh-deep-research",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-inspect",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/dsh-inspect",
		"category": "workflow",
		"description": {
			"en": "Adversarial checkup → fix → review loop toolset.",
			"zh": "发现问题→修复交付→质量复查的对抗式闭环工具集。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/dsh-inspect",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-track",
		"owner": "fakechris",
		"url": "https://github.com/fakechris/dsh-track",
		"category": "workflow",
		"description": {
			"en": "Embedded task management engine: decision-point protocol, idea capture wall, Linear-style issue store.",
			"zh": "嵌入式任务管理引擎：决策点协议、念头捕获墙、Linear 形 issue 存储。"
		},
		"install": "dsh plugin --profile web add github:fakechris/dsh-track",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-advisor",
		"owner": "btspoony",
		"url": "https://github.com/btspoony/dsh-advisor",
		"category": "workflow",
		"description": {
			"en": "Pair a second model that passively reviews each turn and injects notes.",
			"zh": "搭配一个副模型，每轮被动审查并注入见解。"
		},
		"install": "dsh plugin --profile web add github:btspoony/dsh-advisor",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-open-in-vscode",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/dsh-open-in-vscode",
		"category": "notify",
		"description": {
			"en": "Open DSH workspace directories in VS Code directly from the web GUI.",
			"zh": "从 Web GUI 一键在 VS Code 中打开工作区目录。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/dsh-open-in-vscode",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-notification",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/dsh-notification",
		"category": "notify",
		"description": {
			"en": "Desktop notifications for turn completions, with per-outcome controls and keyword rules.",
			"zh": "回合完成桌面通知，按结果分控 + 关键词过滤。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/dsh-notification",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-acp-for-bitfun",
		"owner": "bobleer",
		"url": "https://github.com/bobleer/dsh-acp-for-bitfun",
		"category": "notify",
		"description": {
			"en": "ACP bridge between BitFun and DSH.",
			"zh": "BitFun 与 DSH 的 ACP 交互对接。"
		},
		"install": "dsh plugin --profile web add github:bobleer/dsh-acp-for-bitfun",
		"added": "2026-08-13"
	},
	{
		"name": "telegram",
		"owner": "LoserFox",
		"url": "https://github.com/LoserFox/telegram",
		"category": "notify",
		"description": {
			"en": "Bridge to the Telegram Bot API: long polling, per-chat sessions, HTML formatting.",
			"zh": "Telegram Bot API 桥接：长轮询、per-chat 会话、HTML 格式化。"
		},
		"install": "dsh plugin --profile web add github:LoserFox/telegram",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-chatnode-wechat",
		"owner": "Jesse-njx",
		"url": "https://github.com/Jesse-njx/dsh-chatnode-wechat",
		"category": "notify",
		"description": {
			"en": "Chat with, monitor, and approve your DSH agents from WeChat via the iLink gateway: text both ways, session targeting, digest heartbeats, and numbered approval prompts.",
			"zh": "通过 iLink 网关在微信里与 DSH agent 聊天、监控与审批：双向文本、会话切换、进度摘要与编号审批提示。"
		},
		"install": "dsh plugin --profile web add github:Jesse-njx/dsh-chatnode-wechat",
		"added": "2026-08-14"
	},
	{
		"name": "dsh-session-notification",
		"owner": "dingyi222666",
		"url": "https://github.com/dingyi222666/dsh-session-notification",
		"category": "notify",
		"description": {
			"en": "Notifications for four session states, with browser alerts and prompts.",
			"zh": "会话完成等四种状态的通知响应，支持浏览器提示。"
		},
		"install": "dsh plugin --profile web add github:dingyi222666/dsh-session-notification",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-web-ui-notify",
		"owner": "bill9109",
		"url": "https://github.com/bill9109/dsh-web-ui-notify",
		"category": "notify",
		"description": {
			"en": "Desktop notification reminders.",
			"zh": "桌面通知提醒。"
		},
		"install": "dsh plugin --profile web add github:bill9109/dsh-web-ui-notify",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-webbridge",
		"owner": "bill9109",
		"url": "https://github.com/bill9109/dsh-webbridge",
		"category": "notify",
		"description": {
			"en": "DSH meets Kimi WebBridge.",
			"zh": "DSH 结合 Kimi WebBridge。"
		},
		"install": "dsh plugin --profile web add github:bill9109/dsh-webbridge",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-im-bridge",
		"owner": "BiBoyang",
		"url": "https://github.com/BiBoyang/dsh-im-bridge",
		"category": "notify",
		"description": {
			"en": "Two-way WeChat (iLink) bridge: turn-end and approval-request push, in-chat approve/reject and message injection, persistent dedup and convergent long-reply chunking; channel layer extensible to other IMs.",
			"zh": "微信（iLink）双向桥：turn 完成/批准请求推送、聊天内批准与消息注入、持久去重与长回复收敛分段；通道层为多 IM 预留。"
		},
		"install": "dsh plugin --profile web add github:BiBoyang/dsh-im-bridge",
		"added": "2026-08-14"
	},
	{
		"name": "fabric",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/fabric",
		"category": "dev",
		"description": {
			"en": "An MC-Fabric-style hook processor.",
			"zh": "类似 MC Fabric 的 hook 处理器。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/fabric",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-git-identity",
		"owner": "LoserFox",
		"url": "https://github.com/LoserFox/dsh-git-identity",
		"category": "dev",
		"description": {
			"en": "Pin Git commits to the environment's own author identity; env-var injection overrides all `git config` settings.",
			"zh": "git 提交固定使用环境自身作者身份，环境变量注入压过一切 `git config` 设置。"
		},
		"install": "dsh plugin --profile web add github:LoserFox/dsh-git-identity",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-context-doctor",
		"owner": "Zhenyu98",
		"url": "https://github.com/Zhenyu98/dsh-context-doctor",
		"category": "dev",
		"description": {
			"en": "Context injection audit: token costs of instruction chains / skill catalogs / tool schemas, duplicate and conflict detection.",
			"zh": "上下文注入审计：统计指令链/技能目录/工具 schema 的 token 成本，检测重复与冲突。"
		},
		"install": "dsh plugin --profile web add github:Zhenyu98/dsh-context-doctor",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-plugin-check",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/dsh-plugin-check",
		"category": "dev",
		"description": {
			"en": "Plugin health checks: manifest protocol / patch format / build traps, zero-dependency and read-only.",
			"zh": "插件健康检查：扫描清单协议/patch 格式/构建陷阱，零依赖只读。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/dsh-plugin-check",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-security-audit",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/dsh-security-audit",
		"category": "dev",
		"description": {
			"en": "Local security audit: config, plugin origins, sessions, network exposure — read-only redacted risk report.",
			"zh": "本机安全审计：配置/插件来源/会话/网络暴露面，只读脱敏风险报告。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/dsh-security-audit",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-session-health",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/dsh-session-health",
		"category": "dev",
		"description": {
			"en": "Frame-level scan diagnostics for session files (torn/corrupt/empty detection).",
			"zh": "会话文件帧级扫描诊断（torn/损坏/空会话检测）。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/dsh-session-health",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-evolve",
		"owner": "william-jin-cmu",
		"url": "https://github.com/william-jin-cmu/dsh-evolve",
		"category": "dev",
		"description": {
			"en": "Self-evolution: the agent hot-mounts/removes persistent plugins on itself mid-session.",
			"zh": "自进化：agent 在会话内给自己热挂载/卸载持久化插件。"
		},
		"install": "dsh plugin --profile web add github:william-jin-cmu/dsh-evolve",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-trace",
		"owner": "vibeinging",
		"url": "https://github.com/vibeinging/dsh-trace",
		"category": "dev",
		"description": {
			"en": "Telemetry backend exporting turns, model steps, and tool calls to yiTrace.",
			"zh": "遥测后端：把 turns、model steps、tool calls 导出到 yiTrace。"
		},
		"install": "dsh plugin --profile web add github:vibeinging/dsh-trace",
		"added": "2026-08-13"
	},
	{
		"name": "sandbox-micro",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/sandbox-micro",
		"category": "dev",
		"description": {
			"en": "Support for the microsandbox backend.",
			"zh": "microsandbox 沙箱支持。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/sandbox-micro",
		"added": "2026-08-13"
	},
	{
		"name": "sandbox-mxc",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/sandbox-mxc",
		"category": "dev",
		"description": {
			"en": "Microsoft cross-platform sandbox support.",
			"zh": "微软跨平台沙盒支持。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/sandbox-mxc",
		"added": "2026-08-13"
	},
	{
		"name": "sandbox-nono",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/sandbox-nono",
		"category": "dev",
		"description": {
			"en": "Support for the nono sandbox backend.",
			"zh": "nono 沙盒支持。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/sandbox-nono",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-agent-budget",
		"owner": "vibeinging",
		"url": "https://github.com/vibeinging/dsh-agent-budget",
		"category": "dev",
		"description": {
			"en": "Agent-tree token budget management.",
			"zh": "agent 树 token 预算管理。"
		},
		"install": "dsh plugin --profile web add github:vibeinging/dsh-agent-budget",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-llm-fallbacks",
		"owner": "btspoony",
		"url": "https://github.com/btspoony/dsh-llm-fallbacks",
		"category": "dev",
		"description": {
			"en": "Role-based LLM retry & fallback strategies.",
			"zh": "基于角色的模型重试与备用策略。"
		},
		"install": "dsh plugin --profile web add github:btspoony/dsh-llm-fallbacks",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-polyglot",
		"owner": "Jesse-njx",
		"url": "https://github.com/Jesse-njx/dsh-polyglot",
		"category": "dev",
		"description": {
			"en": "The model switch for DSH: point it at any OpenAI-compatible endpoint, with curated free/cheap DeepSeek provider presets and automatic fallback when a free tier rate-limits you.",
			"zh": "DSH 的模型切换器：指向任意 OpenAI 兼容端点，内置精选免费/低价 DeepSeek 服务商预设，免费额度限流时自动回退。"
		},
		"install": "dsh plugin --profile web add github:Jesse-njx/dsh-polyglot",
		"added": "2026-08-14"
	},
	{
		"name": "dsh-tool-approval",
		"owner": "ilharp",
		"url": "https://github.com/ilharp/dsh-tool-approval",
		"category": "dev",
		"description": {
			"en": "Manual approval mode (\"Manual Mode\" / \"Ask Mode\").",
			"zh": "手动审批模式（Manual/Ask Mode）。"
		},
		"install": "dsh plugin --profile web add github:ilharp/dsh-tool-approval",
		"added": "2026-08-13"
	},
	{
		"name": "plugin-template",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/plugin-template",
		"category": "dev",
		"description": {
			"en": "Plugin template repo (based on the official turtle-ui repo).",
			"zh": "插件模板仓库（基于 turtle-ui 官方仓库）。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/plugin-template",
		"added": "2026-08-13"
	},
	{
		"name": "Qwen-MM-Plugins",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/Qwen-MM-Plugins",
		"category": "dev",
		"description": {
			"en": "Qwen multi-modal plugin support.",
			"zh": "Qwen 多模态插件支持。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/Qwen-MM-Plugins",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-tps",
		"owner": "Small-tailqwq",
		"url": "https://github.com/Small-tailqwq/dsh-tps",
		"category": "dev",
		"description": {
			"en": "A TPS metrics plugin.",
			"zh": "TPS 指标插件。"
		},
		"install": "dsh plugin --profile web add github:Small-tailqwq/dsh-tps",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-fail-logger",
		"owner": "Areium",
		"url": "https://github.com/Areium/dsh-fail-logger",
		"category": "dev",
		"description": {
			"en": "Auto-log failed tool calls across native tools, PTC run_code, and inline invocations: dedup and count root causes into a skill so repeated mistakes fade.",
			"zh": "全模式调用工具失败自动实录：把原生工具 / PTC run_code / 代码内嵌工具调用的失败错因去重计数后写入 skill，越用越少错。"
		},
		"install": "dsh plugin --profile web add github:Areium/dsh-fail-logger",
		"added": "2026-08-14"
	},
	{
		"name": "dsh-eval-harness",
		"owner": "BiBoyang",
		"url": "https://github.com/BiBoyang/dsh-eval-harness",
		"category": "dev",
		"description": {
			"en": "Evaluation harness for DSH plugins: YAML cases drive real headless agent runs, assert on tool calls, args, results and token usage, with a baseline gate for CI regression.",
			"zh": "DSH 插件评测框架：YAML 用例驱动真实 headless agent，断言工具调用/参数/返回与 token 用量，baseline 门禁做 CI 回归。"
		},
		"install": "dsh plugin --profile web add github:BiBoyang/dsh-eval-harness",
		"added": "2026-08-14"
	},
	{
		"name": "oh-dsh",
		"owner": "hust-open-atom-club",
		"url": "https://github.com/hust-open-atom-club/oh-dsh",
		"category": "dev",
		"description": {
			"en": "Community distribution: TUI, desktop, and Web UI as one bundle with layered installation.",
			"zh": "社区发行版：TUI、桌面端与 Web UI 统一体验，分层安装、一步到位。"
		},
		"install": "dsh plugin --profile web add github:hust-open-atom-club/oh-dsh",
		"added": "2026-08-14"
	},
	{
		"name": "dsh-ads",
		"owner": "Nagi-ovo",
		"url": "https://github.com/Nagi-ovo/dsh-ads",
		"category": "fun",
		"description": {
			"en": "Parody ads in 2005-Chinese-web style: sidebar banners, in-chat feeds, corner popups, and a close button whose hit area is smaller than it looks. All fictional.",
			"zh": "2005 年中文站点风格的整活广告插件：侧栏广告/信息流/角落弹窗 + 假关闭叉，素材全虚构。"
		},
		"install": "dsh plugin --profile web add github:Nagi-ovo/dsh-ads",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-gomoku",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/dsh-gomoku",
		"category": "fun",
		"description": {
			"en": "Play Gomoku against the AI, or let two AIs battle it out.",
			"zh": "与 AI 下五子棋，也可让 AI 对局比棋力。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/dsh-gomoku",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-stock-market",
		"owner": "AnacondaKC",
		"url": "https://github.com/AnacondaKC/dsh-stock-market",
		"category": "fun",
		"description": {
			"en": "Fixes the bug where your account can't lose money while you code.",
			"zh": "有效解决了写代码的时候账户不能同时亏钱的 BUG。"
		},
		"install": "dsh plugin --profile web add github:AnacondaKC/dsh-stock-market",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-emoji",
		"owner": "hellodigua",
		"url": "https://github.com/hellodigua/dsh-emoji",
		"category": "fun",
		"description": {
			"en": "Automatically add emojis to AI replies.",
			"zh": "为 AI 回复自动添加表情。"
		},
		"install": "dsh plugin --profile web add github:hellodigua/dsh-emoji",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-minigames",
		"owner": "lhh010",
		"url": "https://github.com/lhh010/dsh-minigames",
		"category": "fun",
		"description": {
			"en": "Side-panel arcade: 18 offline mini-games to play while the model thinks.",
			"zh": "右侧小游戏面板：18 款离线小游戏，等模型回复时的摸鱼神器。"
		},
		"install": "dsh plugin --profile web add github:lhh010/dsh-minigames",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-stickers",
		"owner": "william-jin-cmu",
		"url": "https://github.com/william-jin-cmu/dsh-stickers",
		"category": "fun",
		"description": {
			"en": "Bidirectional sticker reactions between user and agent.",
			"zh": "用户与 agent 双向表情贴纸互动。"
		},
		"install": "dsh plugin --profile web add github:william-jin-cmu/dsh-stickers",
		"added": "2026-08-13"
	},
	{
		"name": "whale-girl",
		"owner": "vlln",
		"url": "https://github.com/vlln/whale-girl",
		"category": "fun",
		"description": {
			"en": "Desktop pet (QQ-pet style): floats in the corner, draggable, feedable, playable.",
			"zh": "桌面宠物（QQ 宠物形态）：右下角悬浮、可拖拽/投喂/玩耍。"
		},
		"install": "dsh plugin --profile web add github:vlln/whale-girl",
		"added": "2026-08-13"
	},
	{
		"name": "deepseek-manners",
		"owner": "Moeblack",
		"url": "https://github.com/Moeblack/deepseek-manners",
		"category": "fun",
		"description": {
			"en": "Append a thank-you note after every message. Mind your manners.",
			"zh": "给每次消息后注入感谢语，做个有礼貌的人。"
		},
		"install": "dsh plugin --profile web add github:Moeblack/deepseek-manners",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-plugin-d399",
		"owner": "HuanLinOTO",
		"url": "https://github.com/HuanLinOTO/dsh-plugin-d399",
		"category": "fun",
		"description": {
			"en": "Pops up a mini-game menu (wordle, match-3, extensible) while the model generates.",
			"zh": "模型生成时弹出小游戏菜单（wordle/消消乐，可扩展）。"
		},
		"install": "dsh plugin --profile web add github:HuanLinOTO/dsh-plugin-d399",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-auto-chess",
		"owner": "omdsh-dev",
		"url": "https://github.com/omdsh-dev/dsh-auto-chess",
		"category": "fun",
		"description": {
			"en": "Auto chess: human vs AI, or AI vs AI.",
			"zh": "自走棋：人机对战或双 AI 对弈。"
		},
		"install": "dsh plugin --profile web add github:omdsh-dev/dsh-auto-chess",
		"added": "2026-08-13"
	},
	{
		"name": "dsh-douyin",
		"owner": "AnacondaKC",
		"url": "https://github.com/AnacondaKC/dsh-douyin",
		"category": "fun",
		"description": {
			"en": "Short-video sidebar: native player, series navigation, precise history replay.",
			"zh": "侧栏短视频：原生播放器、系列导航、精确历史回放。"
		},
		"install": "dsh plugin --profile web add github:AnacondaKC/dsh-douyin",
		"added": "2026-08-13"
	}
];
//#endregion
//#region src/core.ts
/**
* dsh-workshop 共享核心：插件目录读取、已安装检测、dsh CLI 执行。
* 被 host 工具半与 web API 半共同使用（tsdown 分别内联）。
*/
var core_exports = /* @__PURE__ */ __exportAll({
	buildCatalogView: () => buildCatalogView,
	categorize: () => categorize,
	categoryCounts: () => categoryCounts,
	checkWebCompatible: () => checkWebCompatible,
	classifyFailReason: () => classifyFailReason,
	clearCatalogCache: () => clearCatalogCache,
	clearMirrorCache: () => clearMirrorCache,
	currentMirror: () => currentMirror,
	dshHome: () => dshHome,
	failReasonHint: () => failReasonHint,
	fetchCatalog: () => fetchCatalog,
	finishProgress: () => finishProgress,
	getPendingRestart: () => getPendingRestart,
	getProgress: () => getProgress,
	hotMountBundle: () => hotMountBundle,
	installPlugin: () => installPlugin,
	installPluginSmart: () => installPluginSmart,
	lookupPluginFullName: () => lookupPluginFullName,
	markPendingRestart: () => markPendingRestart,
	mirrorEnvFor: () => mirrorEnvFor,
	normalizeInstalledId: () => normalizeInstalledId,
	pickFastestMirror: () => pickFastestMirror,
	profileDir: () => profileDir,
	pushProgressLine: () => pushProgressLine,
	readCachedCatalog: () => readCachedCatalog,
	readInstalled: () => readInstalled,
	resetProgress: () => resetProgress,
	runDsh: () => runDsh,
	serial: () => serial,
	setProgressStage: () => setProgressStage,
	testAllMirrors: () => testAllMirrors,
	uninstallPlugin: () => uninstallPlugin
});
const DESC_MAP = /* @__PURE__ */ new Map();
for (const entry of plugins ?? []) DESC_MAP.set(entry.name, entry);
/** awesome 精选分类 → 中文分区标签。 */
const CURATED_CATEGORIES = {
	ui: "UI 增强",
	session: "会话与记忆",
	tools: "工具与能力",
	workflow: "工作流与自动化",
	notify: "通知与集成",
	dev: "开发与运行时",
	fun: "趣味娱乐"
};
function dshHome() {
	return process.env.DSH_HOME ?? join(homedir(), ".dsh");
}
function profileDir(profileName = "web") {
	return join(dshHome(), "profiles", profileName);
}
/** 分类规则（关键词 → Steam 风格分区），顺序优先。 */
const CATEGORY_RULES = [
	["UI 增强", /ui|skin|theme|tui|sidebar|panel|navbar|nav|visual|web-ui|webui|frontend|status-label|focus-chat|layout|diff-viewer|command-palette|spotlight|drag|deep-link/i],
	["会话与记忆", /memory|session|conversation|share|rewind|import|message|chat-import|mnem|mneme|crosstalk|distill|explain|prompt-studio/i],
	["工具与能力", /tool|mcp|terminal|bash|browser|search|vision|docker|git|excel|pdf|doc|sql|data|image|video|voice|computer-use|skillport|openpencil/i],
	["工作流与自动化", /workflow|automation|schedule|cron|loop|agent-team|plan|task|routines|sentinel|research|advisor|specflow/i],
	["通知与集成", /notification|notify|telegram|wechat|weixin|wechat|desktop|im-bridge|vscode|bitfun|acp|webbridge/i],
	["开发与运行时", /sandbox|llm|model|oauth|auth|provider|runtime|debug|audit|security|hmr|health|manager|updater|plugin-manager|registry/i],
	["趣味娱乐", /pet|game|emoji|sticker|whale|fun|mini|chess|stock|ads|douyin/i]
];
function categorize(p) {
	const haystack = `${p.name} ${p.fullName} ${p.description ?? ""} ${(p.topics ?? []).join(" ")} ${p.category ?? ""}`;
	for (const [label, re] of CATEGORY_RULES) if (re.test(haystack)) return label;
	return "其他";
}
/** 目录分类计数（用于侧栏）。 */
function categoryCounts(plugins) {
	const map = /* @__PURE__ */ new Map();
	for (const p of plugins) {
		const c = categorize(p);
		map.set(c, (map.get(c) ?? 0) + 1);
	}
	return [...map.entries()].sort((a, b) => b[1] - a[1]).map(([label, count]) => ({
		label,
		count
	}));
}
/** 读取本地缓存的目录；缺失/损坏返回 null。 */
async function readCachedCatalog(cachePath) {
	try {
		const doc = JSON.parse(await readFile(cachePath, "utf8"));
		if (!Array.isArray(doc.plugins)) return null;
		return doc;
	} catch {
		return null;
	}
}
/** 删除本地缓存（强制刷新用）。 */
async function clearCatalogCache(cachePath) {
	try {
		const { rm } = await import("node:fs/promises");
		await rm(cachePath, { force: true });
	} catch {}
}
/** 拉取目录（dataUrl 失败回退 backupUrl / dsh-recommend 已有缓存），写入本地缓存。 */
async function fetchCatalog(cfg) {
	const cached = await readCachedCatalog(cfg.cachePath);
	if (cached) return cached;
	const recommendCache = join(dshHome(), "dsh-recommend", "registry.json");
	try {
		const doc = JSON.parse(await readFile(recommendCache, "utf8"));
		if (Array.isArray(doc.plugins)) {
			await mkdir(dirname(cfg.cachePath), { recursive: true });
			await writeFile(cfg.cachePath, JSON.stringify(doc), "utf8");
			return doc;
		}
	} catch {}
	let lastErr = null;
	for (const url of [
		cfg.dataUrl,
		cfg.backupUrl,
		...RAW_BACKUPS.map((b) => b.build("data/registry.json"))
	].filter(Boolean)) try {
		const res = await fetch(url, { signal: AbortSignal.timeout(2e4) });
		if (!res.ok) throw new Error(`HTTP ${res.status}`);
		const text = await res.text();
		const doc = JSON.parse(text);
		if (!Array.isArray(doc.plugins)) throw new Error("catalog 结构异常");
		await mkdir(dirname(cfg.cachePath), { recursive: true });
		await writeFile(cfg.cachePath, text, "utf8");
		return doc;
	} catch (e) {
		lastErr = e;
	}
	throw new Error(`插件目录下载失败: ${String(lastErr)}`);
}
/** 官方核心包（非插件，已含于 base/web-app 层），不在已安装列表中展示。 */
const CORE_PACKAGES = /* @__PURE__ */ new Set([
	"@deepseek-ai/dsh",
	"@deepseek-ai/dsh-base",
	"@deepseek-ai/dsh-web-app"
]);
/** 读取 profile 已安装插件（package.json 依赖 + patch insert 行）。 */
async function readInstalled(profile = "web") {
	const dir = profileDir(profile);
	const out = [];
	try {
		const pkg = JSON.parse(await readFile(join(dir, "package.json"), "utf8"));
		const bundles = new Set(pkg.dsh?.profile?.bundles ?? []);
		for (const name of Object.keys(pkg.dependencies ?? {})) {
			if (CORE_PACKAGES.has(name)) continue;
			out.push({
				id: name,
				kind: bundles.has(name) ? "bundle" : "insert"
			});
		}
	} catch {}
	try {
		const patch = await readFile(join(dir, "cordis.patch.yml"), "utf8");
		for (const m of patch.matchAll(/^\s*- id:\s*([^\s]+)/gm)) {
			const id = m[1];
			if (!out.some((e) => e.id === id)) out.push({
				id,
				kind: "insert"
			});
		}
	} catch {}
	return out;
}
/** 按 npm 包名（目录名）查 GitHub fullName，用于安装回退。 */
async function lookupPluginFullName(cfg, name) {
	try {
		return (await fetchCatalog(cfg)).plugins.find((p) => p.name === name)?.fullName ?? null;
	} catch {
		return null;
	}
}
/** git 智能协议代理镜像（ghproxy 系），直连排第一作为基准。 */
const GIT_MIRRORS = [
	{
		name: "github.com 直连",
		base: "https://github.com/"
	},
	{
		name: "ghfast.top",
		base: "https://ghfast.top/https://github.com/"
	},
	{
		name: "gh-proxy.com",
		base: "https://gh-proxy.com/https://github.com/"
	},
	{
		name: "ghproxy.net",
		base: "https://ghproxy.net/https://github.com/"
	},
	{
		name: "ghproxy.cc",
		base: "https://ghproxy.cc/https://github.com/"
	},
	{
		name: "gh.llkk.cc",
		base: "https://gh.llkk.cc/https://github.com/"
	},
	{
		name: "github.moeyy.xyz",
		base: "https://github.moeyy.xyz/https://github.com/"
	}
];
/** 目录/文件下载备份源（raw 系）。 */
const RAW_BACKUPS = [
	{
		name: "jsdelivr",
		build: (p) => `https://cdn.jsdelivr.net/gh/zp-home/dsh-recommend@main/${p}`
	},
	{
		name: "raw.githubusercontent",
		build: (p) => `https://raw.githubusercontent.com/zp-home/dsh-recommend/main/${p}`
	},
	{
		name: "gh-proxy raw",
		build: (p) => `https://gh-proxy.com/https://raw.githubusercontent.com/zp-home/dsh-recommend/main/${p}`
	},
	{
		name: "ghfast.top raw",
		build: (p) => `https://ghfast.top/https://raw.githubusercontent.com/zp-home/dsh-recommend/main/${p}`
	}
];
let mirrorCache = null;
/** 对单个镜像做 git 智能协议连通性/时延探测。 */
async function testMirror(m, repo) {
	const url = `${m.base}${repo}.git/info/refs?service=git-upload-pack`;
	const start = Date.now();
	try {
		const res = await fetch(url, { signal: AbortSignal.timeout(1e4) });
		return {
			...m,
			latencyMs: Date.now() - start,
			ok: res.status === 200 || res.status === 401
		};
	} catch {
		return {
			...m,
			latencyMs: null,
			ok: false
		};
	}
}
/** 并行测速全部镜像，选延迟最低的可达镜像（结果缓存 10 分钟）。 */
async function pickFastestMirror(repo) {
	if (mirrorCache && mirrorCache.repo === repo && Date.now() - mirrorCache.at < 6e5) return mirrorCache.chosen;
	const results = await Promise.all(GIT_MIRRORS.map((m) => testMirror(m, repo)));
	const chosen = results.filter((r) => r.ok).sort((a, b) => (a.latencyMs ?? Infinity) - (b.latencyMs ?? Infinity))[0] ?? results[0];
	mirrorCache = {
		at: Date.now(),
		chosen,
		repo
	};
	return chosen;
}
/** 查询当前生效镜像（未测速时为直连默认）。 */
function currentMirror() {
	return mirrorCache?.chosen ?? {
		name: "github.com 直连",
		base: "https://github.com/",
		latencyMs: null,
		ok: true
	};
}
/** 清空测速缓存（重新测速）。 */
function clearMirrorCache() {
	mirrorCache = null;
}
/** 测速并返回全部镜像结果（供 UI 展示）。 */
async function testAllMirrors(repo) {
	const results = await Promise.all(GIT_MIRRORS.map((m) => testMirror(m, repo)));
	const ok = results.filter((r) => r.ok).sort((a, b) => (a.latencyMs ?? Infinity) - (b.latencyMs ?? Infinity));
	mirrorCache = {
		at: Date.now(),
		chosen: ok[0] ?? results[0] ?? GIT_MIRRORS[0],
		repo
	};
	return [...ok, ...results.filter((r) => !r.ok)];
}
/** 定位用户全局 git 配置文件路径。 */
async function globalGitConfigPath() {
	try {
		const { execFile } = await import("node:child_process");
		return await new Promise((resolvePromise) => {
			execFile("git", [
				"config",
				"--global",
				"--list",
				"--show-origin"
			], (err, stdout) => {
				if (err) {
					resolvePromise(null);
					return;
				}
				const m = stdout.split("\n").find((l) => l.startsWith("file:"));
				resolvePromise(m ? m.slice(5, m.indexOf("	")) : null);
			});
		});
	} catch {
		return null;
	}
}
/** 生成带镜像重写的临时 git 配置（GIT_CONFIG_GLOBAL 注入，不改用户全局配置）。 */
async function buildMirrorGitConfig(mirror) {
	const globalPath = await globalGitConfigPath();
	const lines = [];
	if (globalPath) lines.push(`[include]\n\tpath = ${globalPath.replace(/\\/g, "/")}`);
	lines.push(`[url "${mirror.base}"]\n\tinsteadOf = https://github.com/`);
	const file = join(dshHome(), "dsh-workshop", "gitconfig-mirror");
	await mkdir(dirname(file), { recursive: true });
	await writeFile(file, lines.join("\n") + "\n", "utf8");
	return file;
}
/** 取最快镜像对应的环境（供 install/uninstall 直传 runDsh）。 */
async function mirrorEnvFor(repo) {
	const mirror = await pickFastestMirror(repo);
	if (mirror.base === "https://github.com/") return {
		env: void 0,
		mirror
	};
	const cfg = await buildMirrorGitConfig(mirror);
	return {
		env: cfg ? {
			...process.env,
			GIT_CONFIG_GLOBAL: cfg
		} : void 0,
		mirror
	};
}
/** 与 web profile 冲突的已知插件（TUI / 独立发行版 / 依赖 web 不存在的服务）。 */
const WEB_PROFILE_BLOCKLIST = /* @__PURE__ */ new Set([
	"dsh-cc-tui",
	"dsh-TUI",
	"dsh-tianshu-tui",
	"deepseek-harness-tui",
	"oh-dsh",
	"dsh-cc",
	"dsh-vision-toolkit"
]);
/** DSH 本体 / 官方核心仓库：不是可安装的插件，禁止安装。 */
const CORE_REPO_BLOCKLIST = /* @__PURE__ */ new Set([
	"deepseek-ai/deepseek-harness",
	"deepseek-ai/dsh",
	"deepseek-ai/deepseek-cli"
]);
/** patch 中出现即视为「接管核心配置」的危险行（web profile 下拒绝安装）。 */
const DANGER_PATCH_IDS = [
	"- id: agent-presets",
	"- id: agent-loop",
	"- id: cc-tui",
	"- id: agent-instructions"
];
/** 拉取仓库 cordis.patch.yml（jsdelivr 优先，raw 兜底）。 */
async function fetchRepoPatch(fullName) {
	for (const url of [
		`https://cdn.jsdelivr.net/gh/${fullName}@main/cordis.patch.yml`,
		`https://cdn.jsdelivr.net/gh/${fullName}@master/cordis.patch.yml`,
		`https://raw.githubusercontent.com/${fullName}/main/cordis.patch.yml`
	]) try {
		const res = await fetch(url, { signal: AbortSignal.timeout(15e3) });
		if (!res.ok) continue;
		return await res.text();
	} catch {}
	return null;
}
/** 安装前的 web 兼容性预检。 */
async function checkWebCompatible(name, fullName) {
	if (CORE_REPO_BLOCKLIST.has(fullName ?? "") || name === "deepseek-harness" || name === "dsh-root") return {
		ok: false,
		reason: `${fullName ?? name} 是 DSH 本体 / 官方核心仓库，不是可安装的插件，无需安装`
	};
	if (WEB_PROFILE_BLOCKLIST.has(name)) return {
		ok: false,
		reason: `${name} 是终端 TUI / 独立发行版插件，会接管 agent 配置，与 Web 界面冲突，禁止安装`
	};
	if (!fullName) return { ok: true };
	const patch = await fetchRepoPatch(fullName);
	if (patch) {
		for (const id of DANGER_PATCH_IDS) if (patch.includes(id)) return {
			ok: false,
			reason: `检测到冲突配置（${id.trim()}）：该插件会覆盖核心 agent 配置，仅适合独立 profile（如 tui），装进 Web 会破坏启动`
		};
	}
	return { ok: true };
}
/** 从 pnpm 输出解析实际安装的依赖键（取最后一次「+ key」行，github 源可能被重命名）。 */
function parseInstalledKey(output) {
	return [...output.matchAll(/\+ ([^\s]+)/g)].pop()?.[1] ?? null;
}
/** 按目录名解析 profile 中实际的依赖键（兼容 @dsh-external/ 前缀与任意 scope 键名）。 */
async function resolveDependencyKey(name, profile) {
	try {
		const pkg = JSON.parse(await readFile(join(profileDir(profile), "package.json"), "utf8"));
		return Object.keys(pkg.dependencies ?? {}).find((k) => {
			if (k.toLowerCase() === name.toLowerCase() || k === `@dsh-external/${name}`) return true;
			return (k.split("/").pop() ?? "").toLowerCase() === name.toLowerCase();
		}) ?? null;
	} catch {
		return null;
	}
}
/** 校验依赖键对应的包目录存在且可解析，否则自动回滚。优先按 package.json 依赖键匹配。 */
async function verifyInstalledAndRollback(key, name, profile, output, env) {
	const depKey = await resolveDependencyKey(name, profile) ?? key;
	const candidates = [
		depKey,
		key,
		name,
		`@dsh-external/${name}`
	];
	let ok = false;
	for (const cand of candidates) {
		if (!cand) continue;
		try {
			await readFile(join(profileDir(profile), "node_modules", cand, "package.json"), "utf8");
			ok = true;
			break;
		} catch {}
	}
	if (ok) {
		let hotMount = "";
		let hotMountRestart = false;
		try {
			const hm = await hotMountBundle(depKey, profile);
			hotMount = hm.note;
			hotMountRestart = hm.restart ?? false;
			if (hotMountRestart) markPendingRestart(depKey);
		} catch {}
		return {
			code: 0,
			output,
			hotMount,
			hotMountRestart
		};
	}
	const probe = candidates.map((c) => `${c}:${(() => {
		try {
			readFileSync(join(profileDir(profile), "node_modules", c ?? "", "package.json"), "utf8");
			return "ok";
		} catch {
			return "missing";
		}
	})()}`).join(", ");
	await uninstallPlugin(depKey, profile, env);
	return {
		code: -1,
		output: `${output}\n---\n安装产物校验失败：${name} 未正确安装到 profile（候选检查: ${probe}），已自动回滚。`
	};
}
/** git 源插件构建被 pnpm 阻止时，自动写入 allowBuilds 并重装一次。 */
async function fixBlockedBuilds(key, profile, installArgs, env) {
	const wsPath = join(profileDir(profile), "pnpm-workspace.yaml");
	let ws;
	try {
		ws = await readFile(wsPath, "utf8");
	} catch {
		return null;
	}
	return await (async () => {
		try {
			if (!/allowBuilds/.test(ws)) ws += `\nallowBuilds:\n  '${key}': true\n`;
			else if (!ws.includes(key)) ws = ws.replace(/allowBuilds:/, `allowBuilds:\n  '${key}': true`);
			await writeFile(wsPath, ws, "utf8");
			return await installPlugin(installArgs[installArgs.length - 1], profile, env);
		} catch {
			return null;
		}
	})();
}
/** npm 包是否存在（registry.npmjs.org 优先，npmmirror 兜底；兼容小写包名），返回可用的包名。 */
async function npmPackageExists(name) {
	const candidates = [name, name.toLowerCase()];
	for (const cand of [...new Set(candidates)]) for (const reg of ["https://registry.npmjs.org", "https://registry.npmmirror.com"]) try {
		if ((await fetch(`${reg}/${encodeURIComponent(cand)}`, {
			method: "HEAD",
			signal: AbortSignal.timeout(8e3)
		})).status === 200) return cand;
	} catch {}
	return null;
}
/** 探测 GitHub 仓库中的 dsh 子包（monorepo），返回子包相对路径（如 packages/foo）。 */
async function probeMonorepoSubpackage(fullName) {
	try {
		const res = await fetch(`https://data.jsdelivr.com/v1/packages/gh/${fullName}@main?structure=flat`, { signal: AbortSignal.timeout(15e3) });
		if (!res.ok) return null;
		const candidates = ((await res.json()).files?.map((f) => f.name) ?? []).filter((f) => /^\/[^/]+\/package\.json$/.test(f) || /^\/packages\/[^/]+\/package\.json$/.test(f)).filter((f) => f !== "/package.json");
		for (const f of candidates) try {
			const pkgRes = await fetch(`https://cdn.jsdelivr.net/gh/${fullName}@main${f}`, { signal: AbortSignal.timeout(1e4) });
			if (!pkgRes.ok) continue;
			const pkg = await pkgRes.json();
			if (pkg.dsh || pkg.cordis) return f.replace(/\/package\.json$/, "").replace(/^\//, "");
		} catch {}
		return null;
	} catch {
		return null;
	}
}
/** 安装/更新插件（npm 失败自动回退 GitHub 源）。source: npm 包名或 github:owner/repo。 */
async function installPluginSmart(source, cfg, profile = "web") {
	const s = source.trim();
	const isGit = s.startsWith("github:") || s.startsWith("git:") || s.includes("/");
	const name = s.replace(/^github:[^/]+\//, "").replace(/^@[^/]+\//, "").split("/")[0];
	const full = isGit ? s.startsWith("github:") ? s.slice(7) : s : await lookupPluginFullName(cfg, s);
	if (profile === "web") {
		const check = await checkWebCompatible(name, full);
		if (!check.ok) {
			finishProgress(false, "安装被安全策略拒绝");
			return {
				code: -1,
				output: `⛔ 已阻止安装：${check.reason}`
			};
		}
	}
	const { env, mirror } = await mirrorEnvFor(full && full.includes("/") ? full : "deepseek-ai/deepseek-harness");
	const mirrorSuffix = mirror.base === "https://github.com/" ? "" : `（镜像：${mirror.name}）`;
	if (isGit) {
		setProgressStage(`正在安装（GitHub 源 ${full}）${mirrorSuffix}…`, s);
		const res = await installPlugin(s, profile, env);
		if (res.code === 0) {
			let key = parseInstalledKey(res.output) ?? s;
			const verified = await verifyInstalledAndRollback(key, name, profile, res.output, env);
			if (verified.code === 0 && /allowBuilds|Failed to create bin/i.test(res.output)) {
				key = await resolveDependencyKey(name, profile) ?? key;
				setProgressStage("构建脚本被阻止，正在解锁并重装…", s);
				const retry = await fixBlockedBuilds(key, profile, [
					"plugin",
					"--profile",
					profile,
					"add",
					s
				], env);
				if (retry && retry.code === 0) {
					const verified2 = await verifyInstalledAndRollback(parseInstalledKey(retry.output) ?? key, name, profile, retry.output, env);
					finishProgress(verified2.code === 0, verified2.code === 0 ? "安装完成（含构建）" : "安装完成（构建仍异常）");
					return { ...verified2 };
				}
				finishProgress(true, "安装完成（构建可能未执行，可稍后重试）");
				return { ...verified };
			}
			finishProgress(verified.code === 0, verified.code === 0 ? "安装完成" : "安装失败");
			return { ...verified };
		}
		finishProgress(false, "安装失败");
		return {
			...res,
			failReason: classifyFailReason(res.output, false, true),
			failHint: failReasonHint(classifyFailReason(res.output, false, true))
		};
	}
	setProgressStage("检查 npm 源…", s);
	const npmName = await npmPackageExists(s);
	let npmOut = null;
	if (npmName) {
		setProgressStage(`正在安装（npm 源：${npmName}）…`, s);
		npmOut = await installPlugin(npmName, profile, env);
		if (npmOut.code === 0) {
			const verified = await verifyInstalledAndRollback(parseInstalledKey(npmOut.output) ?? npmName, name, profile, npmOut.output, env);
			finishProgress(verified.code === 0, verified.code === 0 ? "安装完成" : "安装失败");
			return { ...verified };
		}
	}
	if (!full || full === s) {
		finishProgress(false, "npm 未找到，且无可用 GitHub 回退源");
		const reason = npmName && npmOut ? "npm-install-failed" : "npm-not-found";
		return {
			code: -1,
			failReason: reason,
			failHint: failReasonHint(reason),
			output: `${npmName && npmOut ? "npm 安装失败" : `npm 上不存在 ${s}`}，且目录中无对应 GitHub 仓库，无法安装。${npmOut ? `\n${npmOut.output.slice(-500)}` : ""}`
		};
	}
	const gitSource = `github:${full}`;
	setProgressStage(`npm 未找到，正在回退 GitHub 源（${full}）${mirrorSuffix}…`, s);
	const second = await installPlugin(gitSource, profile, env);
	if (second.code === 0) {
		let key = parseInstalledKey(second.output) ?? gitSource;
		const verified = await verifyInstalledAndRollback(key, name, profile, second.output, env);
		if (verified.code === 0 && /allowBuilds|Failed to create bin/i.test(second.output)) {
			key = await resolveDependencyKey(name, profile) ?? key;
			setProgressStage("构建脚本被阻止，正在解锁并重装…", s);
			const retry = await fixBlockedBuilds(key, profile, [
				"plugin",
				"--profile",
				profile,
				"add",
				gitSource
			], env);
			if (retry && retry.code === 0) {
				const verified2 = await verifyInstalledAndRollback(parseInstalledKey(retry.output) ?? key, name, profile, retry.output, env);
				finishProgress(verified2.code === 0, verified2.code === 0 ? "GitHub 源安装完成（含构建）" : "GitHub 源安装完成（构建仍异常）");
				return {
					...verified2,
					fallback: true,
					usedSource: gitSource
				};
			}
			finishProgress(true, "安装完成（构建可能未执行，可稍后重试）");
			return {
				...verified,
				fallback: true,
				usedSource: gitSource
			};
		}
		finishProgress(verified.code === 0, verified.code === 0 ? "GitHub 源安装完成" : "安装失败");
		return {
			...verified,
			fallback: true,
			usedSource: gitSource
		};
	}
	const sub = await probeMonorepoSubpackage(full);
	if (sub) {
		setProgressStage(`检测到 monorepo，尝试子包 ${sub}…`, s);
		const third = await installPlugin(`github:${full}#main&path=/${sub}`, profile, env);
		if (third.code === 0) {
			const verified3 = await verifyInstalledAndRollback(parseInstalledKey(third.output) ?? s, name, profile, third.output, env);
			finishProgress(verified3.code === 0, verified3.code === 0 ? "子包安装完成" : "子包安装失败");
			return {
				...verified3,
				fallback: true,
				usedSource: `github:${full}#main&path=/${sub}`
			};
		}
	}
	const prepareFailed = /ERR_PNPM_PREPARE_PACKAGE|prepare\s*Failed|Failed to prepare/i.test(second.output);
	const reason = classifyFailReason(`${npmOut?.output ?? ""}\n${second.output}`, Boolean(npmName), true);
	finishProgress(false, "安装失败");
	return {
		code: -1,
		failReason: reason,
		failHint: failReasonHint(reason),
		output: `${npmName && npmOut ? `npm 安装失败：${npmOut.output.slice(-800)}` : `npm 上不存在 ${s}`}\n---\n[GitHub 回退失败]\n${second.output}${prepareFailed ? "\n\n提示：该仓库需要源码构建（prepare），构建脚本在上游仓库即失败（常见为 tsdown/unrun 依赖缺失）。可先确认 npm 上是否有同名小写包，或联系插件作者修复构建。" : ""}`
	};
}
/** 运行 dsh CLI（通过 npx），返回退出码与合并输出。env 覆盖环境（镜像 git 配置注入）。 */
function runDsh(args, timeoutMs = 3e5, env) {
	return new Promise((resolvePromise) => {
		const isWin = process.platform === "win32";
		const npxPath = join(dirname(process.execPath), isWin ? "npx.cmd" : "npx");
		const fullArgs = isWin ? [
			"/c",
			npxPath,
			"-y",
			"@deepseek-ai/dsh",
			...args
		] : [
			"-y",
			"@deepseek-ai/dsh",
			...args
		];
		let child;
		try {
			child = spawn(isWin ? "cmd.exe" : "npx", fullArgs, {
				env: env ?? process.env,
				windowsHide: true,
				shell: false
			});
		} catch (e) {
			resolvePromise({
				code: -1,
				output: String(e)
			});
			return;
		}
		let out = "";
		const timer = setTimeout(() => {
			child.kill();
			resolvePromise({
				code: -1,
				output: `${out}\n[超时 ${Math.round(timeoutMs / 1e3)}s，已终止]`
			});
		}, timeoutMs);
		child.stdout.on("data", (d) => {
			const text = d.toString();
			out += text;
			for (const line of text.split("\n")) pushProgressLine(line);
		});
		child.stderr.on("data", (d) => {
			const text = d.toString();
			out += text;
			for (const line of text.split("\n")) pushProgressLine(line);
		});
		child.on("error", (e) => {
			clearTimeout(timer);
			resolvePromise({
				code: -1,
				output: `${out}\n${String(e)}`
			});
		});
		child.on("close", (code) => {
			clearTimeout(timer);
			resolvePromise({
				code: code ?? -1,
				output: out.slice(-4e4)
			});
		});
	});
}
/** 安装/更新插件。source: npm 包名或 github:owner/repo。 */
async function installPlugin(source, profile = "web", env) {
	return runDsh([
		"plugin",
		"--profile",
		profile,
		"add",
		source
	], 3e5, env);
}
/** 卸载插件（按目录名或实际依赖键匹配）；dsh remove 后清理 bundle 层栈残留。走最快镜像。 */
async function uninstallPlugin(id, profile = "web", env) {
	const dir = profileDir(profile);
	let rawId = id;
	let probeRepo = "deepseek-ai/deepseek-harness";
	try {
		const pkg = JSON.parse(await readFile(join(dir, "package.json"), "utf8"));
		const hit = Object.keys(pkg.dependencies ?? {}).find((k) => k === id || normalizeInstalledId(k) === id);
		if (hit) {
			rawId = hit;
			const m = (pkg.dependencies?.[hit] ?? "").match(/^github:([^/]+\/[^/#]+)/);
			if (m) probeRepo = m[1];
		}
	} catch {}
	setProgressStage("正在卸载…", rawId);
	let res;
	if (env) res = await runDsh([
		"plugin",
		"--profile",
		profile,
		"remove",
		rawId
	], 3e5, env);
	else {
		const { env: mirrorEnv } = await mirrorEnvFor(probeRepo);
		res = await runDsh([
			"plugin",
			"--profile",
			profile,
			"remove",
			rawId
		], 3e5, mirrorEnv);
	}
	let wasBundle = false;
	try {
		const pkgPath = join(dir, "package.json");
		const pkg = JSON.parse(await readFile(pkgPath, "utf8"));
		const bundles = pkg.dsh?.profile?.bundles ?? [];
		if (bundles.includes(rawId) || bundles.some((b) => normalizeInstalledId(b) === id)) {
			wasBundle = true;
			pkg.dsh.profile.bundles = bundles.filter((b) => normalizeInstalledId(b) !== id);
			if (pkg.dependencies?.[rawId]) delete pkg.dependencies[rawId];
			await writeFile(pkgPath, `${JSON.stringify(pkg, null, 2)}\n`, "utf8");
		} else if (pkg.dependencies?.[rawId]) {
			delete pkg.dependencies[rawId];
			await writeFile(pkgPath, `${JSON.stringify(pkg, null, 2)}\n`, "utf8");
		}
	} catch {}
	finishProgress(res.code === 0, res.code === 0 ? "卸载完成" : "卸载失败（package.json 已尽力清理）");
	if (res.code === 0 && wasBundle) {
		markPendingRestart(rawId);
		return {
			...res,
			hotMountRestart: true,
			hotMount: "bundle 插件：重启后完全卸载"
		};
	}
	return res;
}
/** github: 源安装会被 pnpm 重命名为 @dsh-external/<name>，匹配时归一化。 */
function normalizeInstalledId(id) {
	return id.replace(/^@dsh-external\//, "");
}
/** 已知依赖键 → 目录名的别名表（仓库名与发布名不一致的情况）。 */
const INSTALL_ALIASES = {
	"@linxin666/dsh-web-ui-all": "dsh-web-ui",
	"@linxin666/dsh-skins": "dsh-web-ui",
	"@linxin666/dsh-ssh": "dsh-ssh",
	"@linxin666/dsh-pet": "dsh-pet",
	"@liustack/modlens": "modlens",
	"@zseven-w/dsh-openpencil": "dsh-openpencil"
};
const progress = {
	active: false,
	source: "",
	stage: "idle",
	lines: [],
	ok: false
};
function getProgress() {
	return {
		...progress,
		lines: [...progress.lines]
	};
}
function setProgressStage(stage, source = "") {
	progress.active = true;
	progress.source = source || progress.source;
	progress.stage = stage;
}
function pushProgressLine(line) {
	const t = line.replace(/\r/g, "").trim();
	if (!t) return;
	progress.lines.push(t);
	if (progress.lines.length > 20) progress.lines.splice(0, progress.lines.length - 20);
}
function finishProgress(ok, stage) {
	progress.active = false;
	progress.ok = ok;
	progress.stage = stage;
}
function resetProgress() {
	progress.active = false;
	progress.source = "";
	progress.stage = "idle";
	progress.lines = [];
	progress.ok = false;
}
/** 组装前端视图：目录 + 已安装 + 分类计数（合并精选中文描述/分类）。 */
async function buildCatalogView(cfg) {
	const doc = await fetchCatalog(cfg);
	const installedRaw = await readInstalled(cfg.profileName ?? "web");
	const byName = /* @__PURE__ */ new Map();
	for (const p of doc.plugins) {
		if (p.excluded) continue;
		byName.set(p.name.toLowerCase(), p);
		byName.set(p.fullName.toLowerCase(), p);
		const seg = p.name.split("/").pop() ?? "";
		byName.set(seg.toLowerCase(), p);
	}
	const matchPlugin = (key) => {
		const norm = normalizeInstalledId(key);
		const alias = INSTALL_ALIASES[key] ?? INSTALL_ALIASES[norm];
		if (alias) {
			const hit = doc.plugins.find((p) => !p.excluded && p.name.toLowerCase() === alias.toLowerCase());
			if (hit) return hit;
		}
		return byName.get(norm.toLowerCase()) ?? byName.get(key.toLowerCase()) ?? byName.get((key.split("/").pop() ?? "").toLowerCase());
	};
	const installed = [];
	const installedOther = [];
	for (const entry of installedRaw) {
		if (entry.id === "dsh-workshop") continue;
		const hit = matchPlugin(entry.id);
		if (hit && hit.name !== "dsh-workshop") installed.push(hit.name);
		else installedOther.push(entry.id);
	}
	const plugins = doc.plugins.filter((p) => !CORE_REPO_BLOCKLIST.has(p.fullName) && !WEB_PROFILE_BLOCKLIST.has(p.name) && p.name !== "deepseek-harness" && p.name !== "dsh-root").map((p) => {
		const curated = DESC_MAP.get(p.name);
		return {
			...p,
			descZh: curated?.description?.zh,
			curatedCategory: curated?.category ? CURATED_CATEGORIES[curated.category] : void 0
		};
	});
	return {
		meta: doc.meta,
		plugins,
		installed,
		installedOther,
		categories: categoryCounts(plugins.filter((p) => !p.excluded))
	};
}
/** 从 bundle patch 原文中提取顶层 `- insert:` 块（保持原始 YAML 文本，含 !!js 表达式）。 */
function extractInsertBlocks(patch) {
	const blocks = [];
	const lines = patch.split("\n");
	let current = null;
	for (const line of lines) if (/^- insert:\s*$/.test(line)) {
		if (current) blocks.push(current.join("\n"));
		current = [line];
	} else if (current) {
		if (/^\S/.test(line) && !line.startsWith("- insert:")) {
			blocks.push(current.join("\n"));
			current = null;
		} else current.push(line);
	}
	if (current) blocks.push(current.join("\n"));
	return blocks;
}
/**
* 安装后热挂载：把已安装 bundle 的 insert 行写入 profile cordis.patch.yml，
* 借助配置 HMR 实时挂载（免重启）。返回说明文案。
*/
async function hotMountBundle(depKey, profile) {
	try {
		const pkgDir = join(profileDir(profile), "node_modules", depKey);
		let pkgJson = "";
		try {
			pkgJson = await readFile(join(pkgDir, "package.json"), "utf8");
		} catch {
			return {
				ok: true,
				note: "包未就绪"
			};
		}
		if (JSON.parse(pkgJson).dsh?.bundle) return {
			ok: true,
			note: "bundle 插件：需要重启服务加载",
			restart: true
		};
		let patch = "";
		try {
			patch = await readFile(join(pkgDir, "cordis.patch.yml"), "utf8");
		} catch {
			return {
				ok: true,
				note: "纯 cordis 插件，无需热挂载"
			};
		}
		const blocks = extractInsertBlocks(patch);
		if (blocks.length === 0) return {
			ok: true,
			note: "无 insert 行，无需热挂载"
		};
		const profilePatchPath = join(profileDir(profile), "cordis.patch.yml");
		let profilePatch = "";
		try {
			profilePatch = await readFile(profilePatchPath, "utf8");
		} catch {}
		const existingIds = /* @__PURE__ */ new Set();
		for (const m of profilePatch.matchAll(/^\s*- id:\s*([^\s]+)/gm)) {
			const id = m[1];
			if (id) existingIds.add(id);
		}
		const fresh = [];
		for (const block of blocks) {
			const idMatch = block.match(/^\s*- id:\s*([^\s]+)/m);
			if (!idMatch) continue;
			if (existingIds.has(idMatch[1])) continue;
			fresh.push(block);
			existingIds.add(idMatch[1]);
		}
		if (fresh.length === 0) return {
			ok: true,
			note: "insert 行已挂载"
		};
		const root = profilePatch.trim().length === 0 || /^\[\]\s*$/.test(profilePatch.trim());
		let next;
		if (root) next = fresh.join("\n\n") + "\n";
		else next = profilePatch.replace(/\s*$/, "") + "\n\n" + fresh.join("\n\n") + "\n";
		await writeFile(profilePatchPath, next, "utf8");
		return {
			ok: true,
			note: `已热挂载 ${fresh.length} 行（配置 HMR 实时生效，免重启）`
		};
	} catch (e) {
		return {
			ok: false,
			note: `热挂载失败：${String(e)}（可重启 dsh web 生效）`
		};
	}
}
/** 单例串行队列：安装/卸载互斥执行（pnpm 锁）。 */
let queue = Promise.resolve();
function serial(fn) {
	const next = queue.then(fn, fn);
	queue = next.catch(() => void 0);
	return next;
}
const pendingRestart = /* @__PURE__ */ new Set();
function markPendingRestart(id) {
	pendingRestart.add(id);
}
function getPendingRestart() {
	return [...pendingRestart];
}
/** 从 pnpm/git 输出中推断失败原因。 */
function classifyFailReason(output, npmTried, githubTried) {
	if (/ERR_PNPM_PREPARE_PACKAGE|prepare\s*Failed|Failed to prepare/i.test(output)) return "github-prepare-failed";
	if (/git ls-remote|fatal:|Unable to access|Could not connect|Connection (refused|reset|timed out)|Failed to connect|ETIMEDOUT|ECONNREFUSED|ENOTFOUND/i.test(output)) return "github-network";
	if (/ERR_PNPM_FETCH_404|not in the npm registry|404 - Not Found/i.test(output) && !githubTried) return "npm-not-found";
	if (npmTried && !githubTried && /ERR_PNPM_FETCH_404|not in the npm registry/.test(output)) return "npm-not-found";
	if (npmTried) return "npm-install-failed";
	if (githubTried) return "github-install-failed";
	if (/安装产物校验失败/.test(output)) return "verify-failed";
	return "unknown";
}
/** 失败原因 → 用户可读的建议。 */
function failReasonHint(reason) {
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
}
//#endregion
export { core_exports as a, getProgress as c, serial as d, testAllMirrors as f, clearMirrorCache as i, installPluginSmart as l, categorize as n, currentMirror as o, uninstallPlugin as p, clearCatalogCache as r, getPendingRestart as s, buildCatalogView as t, resetProgress as u };

//# sourceMappingURL=core-BcUmZo6v.mjs.map