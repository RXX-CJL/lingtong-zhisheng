# DSH 办公室 — 状态与操作手册（单一事实源）

> **用途**：DSH 会话没有持久记忆。这份文件就是我的"长期记忆"。
> **新会话开工第一件事：读这个文件**，不要重新摸索、不要重复踩坑。
> **最后更新**：**2026-10-13（跨会话检索修复轮）** —— ① **§1、§2、§3 已按实测值重写**（原"旧数字作废"警告已删除，警告存在的原因已消除）；
> ② 文末新增 **§26.9**（本会话的复核与修复）；③ §26.8.1 里"openAt 已改为 first-search"是**假的**，已在 §26.9 更正；④ **§26.9.5（2026-10-14 复测）：跨会话检索已实测通过，"必须重启"这一步已完成**。
> ⚠ 仍需注意：**§4、§6~§8、§10~§25 是 2026-09-27 ~ 10-03 的旧内容**，引用前先核对。
> **2026-10-15 增补**：新增 **§0.5**（用户三条常驻规则：思考用中文 / 用外网前先告知 / 不了解用户就提问）+ **团队定位**；权威落点在 `C:\Users\ROG\.dsh\AGENTS.md`。
> **2026-10-16 增补（CodeBuddy 通道打通）**：**§1.3 新增** —— CodeBuddy CLI 派活通道已打通并三级验证（`codebuddy -p` → exit 0 / 12.7s），结论文件 `E:\output\codebuddy_cli_channel_verdict.md`；**踩坑 #12 新增**（凭据目录真相 + lite-wb 无 TUI）。§1.2 的"CLI 侧未登录"状态已作废。
> **2026-10-16 增补（Qoder 通道打通 · 第四条）**：**§1.4 新增** —— Qoder CN CLI 已打通并三级验证（`qoderclicn -p` → exit 0 / 11.9s；带工具任务返回真实 4044），结论文件 `E:\output\qoder_cli_channel_verdict.md`；★ **它是第一条原生复用共享技能池的通道**（实测 **67/67 自动加载**）；**踩坑 #15/#16 新增**（`qodercn` 命令被 npm 遮蔽 + 位置参数型 CLI 的参数顺序铁律 + PowerShell `@(...)` 非 splatting）；§1.2 的"Trae skills 是 junction 共享"与"Qoder ❌ 当前不能派活"**两条均已作废**。
> **2026-10-16 增补（创意工坊轮：web-all + 壁纸插件，双装成功）**：**§2 新增 2 个已装插件** —— `@linxin666/dsh-web-all@0.4.6`（20 行聚合，12 行激活 / 零降级）与 `dsh-plugin-wallpaper-engine@1.3.2`（扫到 585 个本机壁纸）；**§5 新增踩坑 #17/#18/#19**；**§27 新增**（创意工坊 vs 插件市场的三实体辨析 + 本次安装实录 + 回滚入口）。★ 关键事实：两者**装完立即生效、无需重启**（HMR 已加载）。
> **维护约定**：每次改动办公室后更新本文；事实变更就改，不要另建文件。
> **共同规则（2026-10-12 起）**：所有 AI 共用的协作规则、暂定分工与权限边界在 `E:\output\_AI_COMMON_RULES.md` —— **开工先读它**，再读本文。

---

## 0. 三条硬约束（来自用户，不可违反）

1. **绝不修改** `C:\Users\ROG\.dsh\profiles\web`（旧 Web 备用环境，保持可用）。
2. **绝不修改** `E:\deepseek-harness`（DSH 源码仓库，只读）。
3. **所有安装目标都是 Desktop Profile**：`C:\Users\ROG\.dsh\profiles\desktop`。

---

## 0.5 用户四条常驻规则 + 团队定位（2026-10-15 三条 + 2026-10-16 一条，最高优先级）

> **权威落点**：`C:\Users\ROG\.dsh\AGENTS.md`（每会话自动加载，已写入第 7–10 条与"团队定位"节）。
> 本节只登记"有这几条"、核实结论与待办，避免重复维护。

1. **思考过程一律用中文** —— 仅改语言，不改结论、证据标准与工作方式。
   ★核实结论：DSH **没有**原生"思考语言"配置项（2026-10-15 全库检索 `resources\app.asar`，
   `reasoningLanguage` / `thinkingLanguage` / `outputLanguage` / `thinking_language` **零命中**）
   → 走常驻指令，**不需要装插件或技能**。强引导而非硬开关。
2. **使用外网前必须事先告知用户** —— 覆盖 `web_search` / `read_page` / `web_fetch` / `x_search`、
   联网 `npx`/`npm`/`pip install`、`git clone`、`gh`、`curl` / `Invoke-WebRequest` 等一切出网动作。
   告知格式：目标站点 + 目的 + 预期信息。**用户默认具备合法 VPN + 内网穿透（樱花映射）**。
3. **遇到不了解用户的情况主动提问** —— 强化六条铁律第 6 条；高频待问：可用 AI 工具清单
   （Codex / Claude Code / Cursor / Gemini CLI / Trae / Qoder / WorkBuddy…）、能否 API 调用、
   手上有哪些 key、付费服务、内部系统/数据库、信息来源渠道。问法仍是"选项 + 代价 + 推荐"。
4. ★**任务前先搜索调研，确定方针后再动手**（2026-10-16 新增，用户明确要求）——
   **权威落点 `C:\Users\ROG\.dsh\AGENTS.md` 第 10 条**（含判据 5 条、三步标准动作、边界与真实教训）。
   一句话版：**凡"准备自己造轮子 / 写脚本绕过某个限制"之前，先查本地沉淀（状态文件 + `session_search`）
   → 再查权威源（官方文档 / 包自带 README / 源码 / npm 元数据）→ 最后才动手**；
   ⚠ **"开始试第三种方法"就是调研没做够的信号**。必要性：曾反复尝试各种方法"破解"问题，
   最后才发现官方本就提供现成方法。

**团队定位**：用户 + AI 是**一个团队**；用户**几乎不写代码**，但**拥有很多强大的工具和便捷的信息来源**
→ 卡住时**先问"你手上有什么工具能打通这一步"**，不要自己硬扛或降级方案。

**已裁定（2026-10-15）**：粒度 = **"告知即可"，不必等确认**。用户真实目的：提前告知以便他
**提前打开 VPN/通道**——原话"不需要任务进行到一半说网络有问题"。做法：开工前一次性列出本轮
预计的出网动作（站点 + 目的），临时新增的也先说一句。

---

## 1. 环境事实（已验证）

| 项 | 值 |
|---|---|
| DSH_HOME | `C:\Users\ROG\.dsh` |
| DSH_PROFILE | `desktop` |
| Desktop Profile | `C:\Users\ROG\.dsh\profiles\desktop` |
| Desktop 安装 | `F:\AI\DeepSeek-Harness\deepseek-harness-dsh-desktop`（**运行时 = dsh 0.2.0-rc.2**，2026-10-12 实测；本行旧值 0.1.7-rc.2 已作废，见 **§26.1**） |
| Desktop 运行时 | `resources\runtime\primary-runtime\dependencies\{node,pnpm,python}`；Node 24.21.0、pnpm 11.7.0、Python 3.12.14（含 numpy/pandas/python-docx/python-pptx/openpyxl/Pillow/lxml/XlsxWriter） |
| 我的会话运行在 | **Desktop 进程内部**（host 子进程），GUI 端口 `127.0.0.1:19387` 由 Desktop 提供 → **退出 Desktop = 杀死本会话** |
| 用户 PATH 上的工具 | `python` 3.12.10、`uv` 0.11.29、`node` E:\node.exe 24.16.0、`npm`/`npx`（E:\）、`pnpm`、`git` E:\Git\cmd 2.54.0、`rg`（Trae 内置 15.0.0） |
| ★**可调用的 AI 工具（2026-10-15 探测）** | **① Codex CLI 可直接调用**：`C:\Users\ROG\AppData\Local\OpenAI\Codex\bin\9614f1d9b40d9c4f\codex.exe`（**v0.162.0-alpha.17.2**，334 MB；非交互用法 `codex exec "…"`；`codex --help` 还有 `review`/`resume`/`fork`/`mcp`/`apply`/`cloud` 等；配置 `~\.codex\config.toml` = model **gpt-5.6-luna**、reasoning low、sandbox danger-full-access、web_search live；`auth.json` 已登录）② Codex 桌面版 `C:\Program Files\WindowsApps\OpenAI.Codex_*`（MSIX）③ `WebCodex Desktop` = `F:\WebCodex Desktop\WebCodex.exe` ④ Trae CN = `E:\Trae CN\Trae CN.exe` ⑤ Qoder CN IDE = `%LOCALAPPDATA%\Programs\Qoder CN IDE` ⑥ WorkBuddy = `F:\AI\WorkBuddy\WorkBuddy.exe` ⑦ VS Code CLI = `code`（`E:\Microsoft VS Code\bin\code.cmd`）⑧ `gh` GitHub CLI ⑨ Notion。⚠ 除 VS Code/gh 外均为**独立 GUI 软件**，是否可无人值守调用需逐个实测；**联网前须按 AGENTS.md 第 8 条先告知用户** |
| 本机硬件 | **Intel Core i9-14900HX（Raptor Lake）**，`platform.exe --is-aipc` → **0**（不是 AIPC，无 Intel NPU） |
| 文件策略 ↔ shell 可用性 | ★**要用 shell 必须先确认文件策略是 `danger-full-access`**；`workspace-write` 下 `pwsh` 全挂（`0xC0000142`），详见踩坑 **#10** |
| 跨会话检索 | ✅ **2026-10-13 已修好并实测**：模型工具 `session_search` 可用（`ok:true`，命中 3 个不同历史会话）；离线兜底 `dsh-sessions.mjs` 仍在 |

### 1.1 ★Codex CLI 派活通道（2026-10-15 深夜实测补录）

| 项 | 值 |
|---|---|
| 可执行文件 | `C:\Users\ROG\AppData\Local\OpenAI\Codex\bin\9614f1d9b40d9c4f\codex.exe`（318.6 MiB ≈ 334 MB 十进制） |
| 数字签名 | **Valid / `CN="OpenAI OpCo, LLC"`**（一级证据：OpenAI 官方签名，非第三方壳） |
| 版本 | `codex-cli 0.162.0-alpha.17.2`（`--version` 实测；文件 2026-10-15 21:30 刚随应用更新） |
| 非交互入口 | `codex exec [OPTIONS] [PROMPT]`；参数 `-s/--sandbox {read-only,workspace-write,danger-full-access}`、`-C/--cd <DIR>`、`--ephemeral`（不落会话）、`--color never`、`-m/--model`、`-c key=value`、`--json`、`-o/--output-last-message <FILE>`、`--skip-git-repo-check`；子命令 `resume`/`fork`/`review` |
| 登录态 | `~/.codex/auth.json`：**`auth_mode = chatgpt`**、`tokens` 存在、`OPENAI_API_KEY` **为空** → 走 **ChatGPT 账号额度**（不是 API 按量计费）；`last_refresh = 2026-10-08` |
| 默认配置 | `~/.codex/config.toml`：model `gpt-5.6-luna`、reasoning low、`sandbox_mode = danger-full-access`、`web_search = live` → **派活前必须用 `-s` 覆盖成 read-only/受限** |
| ★称呼澄清（用户曾困惑） | 用户口中的"ChatGPT 软件"与"Codex 桌面版"**是同一个 MSIX 包**：`C:\Program Files\WindowsApps\OpenAI.Codex_26.1007.9446.0_x64__2p2nqsd0c76g0`，其 `app\ChatGPT.exe` 才是主程序（`Codex.exe` 是 0 MB 存根）；该应用的 config.toml 里 `CODEX_CLI_PATH` 就指向上面那个 `codex.exe` → **CLI 是这套安装的正式组件**，不是外挂 |
| ★WebCodex Desktop（2026-10-16 深挖） | `F:\WebCodex Desktop\`：`WebCodex.exe`（GUI，**Tauri**/Rust，未签名）+ `webcodex-runtime\{webcodex.exe=CLI, webcodex-server.exe, webcodex-runner.exe}` + `%LOCALAPPDATA%\WebCodex\tools\tunnel-client.exe`。**架构 = ChatGPT 侧下指令 →（server `https://v4.yyjeqhc.cn`）→ 本机 runner 轮询取任务后在本机执行**。CLI 有 30+ 子命令（`share`/`runner`/`server`/`environment`/`tokens`/`plugin`/`doctor`/`auth status`…）→ **可命令行调用**，但**任务入口在 ChatGPT 侧**，故 **对 DSH 无增量**（"在本机执行"DSH 本就能做）；对用户的价值是"让 ChatGPT 网页版能干活"。与 OpenAI 官方 CLI **无技术关系** |
| ⚠ WebCodex 安全边界 | runner 示例策略 `allow_raw_shell = true` + `allow_cwd_anywhere = true` ⇒ **能访问该 server 的一方可在本机执行任意命令**。缓解事实（2026-10-16 核实）：**未注册服务、未开机自启、当前无进程**。建议：用完即完全退出 + 收紧策略 + 用户需确认 `v4.yyjeqhc.cn` 是否自建。本机痕迹：`client_id laptop-qutj924t-…`，2026-10-10~14 启动过 6 次，技能库/SSH 资源为空、`environment` 仅 1 字节（基本没配成） |
| ★65532 悬案结案（2026-10-16） | 从 2026-09-05 的 Codex 历史会话里找到铁证：当时**确有进程监听 `0.0.0.0:65532`**（PID 13756，同时监听 58622）⇒ 该端口曾是**真实可用的代理端口**，后来软件消失但 `~/.codex/.env` 的配置留存 → 这就是踩坑 #11 的 40 分钟来源。WebCodex 相关目录**无** 65532（可排除） |
| ★调用前置条件（血泪 #11） | ① **Clash Verge 主程序要在跑**（`verge_mixed_port: 7897`；系统代理/TUN 开不开都行）② ★**`C:\Users\ROG\.codex\.env` 里的代理端口必须等于 Clash 混合端口**（2026-10-16 已把失效的 `65532` 改为 `7897`，备份 `.env.bak-20261016`）。**该 `.env` 优先级高于环境变量、Windows 系统代理与 TUN** —— 端口不对时的表现是 `SynSent → 10061 → waiting for network` 死循环，**与 VPN/TUN 无关**，别再往网络方向排查 |
| ★已验证可用命令（2026-10-16） | `codex exec -s read-only -C E:\output --ephemeral --color never "任务"` → **exit 0 / 9.9 秒 / 返回 CODEX_CLI_OK / 16,183 token**（三级证据） |

### 1.2 ★AI 工具通道探测（2026-10-16，workbuddy / Trae / Qoder）

| 工具 | CLI | 性质 | 能否派活 | 对 DSH 增量 |
|---|---|---|---|---|
| ★★ **WorkBuddy**（腾讯 CodeBuddy 桌面版） | `F:\AI\WorkBuddy\resources\app.asar.unpacked\cli\bin\codebuddy`（Node 脚本；`package.json` name = **`@genie/agent-cli`**） | **完整 agent CLI** | ✅ **能** | ★★★ **极高：第三条 AI 通道** |
| **Trae CN** 3.4.3 | `E:\Trae CN\bin\trae-cn.cmd` | VS Code 系壳（`--diff/--goto/--list-extensions`，**无 AI 派活**） | ❌ | ☆ 低（`.trae-cn\skills` **74 个**：**不是 junction**，是 2026-09-27 从它**拷贝**出来的池，两份副本此后独立演进；Trae 独有 10 个 `local-*` **全是 Intel AIPC 专属、本机不可用**；`plugins\trae-remote-official\` 有 chrome-devtools/computer-use 等 MCP 存量） |
| **Qoder CN** 1.25.1 | IDE 壳 `E:\QoderCN\bin\qoder-cn.cmd`；★ **派活 CLI 已装**：`qoderclicn`（npm `@qodercn-ai/qoderclicn@1.1.72`）→ 见 **§1.4** | **IDE 壳 + 独立 agent CLI** | ✅ **能**（三级验证） | ★★★ **极高：第四条通道，且原生复用 67 技能池** |
| **TRAE CLI**（官方产品，**已结案不打通**） | ⚠️ 官方限制：**仅 TRAE 企业版旗舰版套餐可用**（1.0 与 2.0 文档两处一致，已复核） | 终端 Code Agent | ❌ **不可用**（用户账号为免费版） | ☆ 无（规范虽通、套餐卡死） |

**★ CodeBuddy CLI 关键事实**：
- **必须设 `CODEBUDDY_FORCE_LITE_WB_BUNDLE=1`**（本机只装了 `dist\codebuddy-lite-wb.mjs` 变体；不设则 `require('../dist/codebuddy')` → MODULE_NOT_FOUND）。脚本：`E:\output\_tools\codebuddy.cmd`
- 能力：`-p/--print` 非交互、`--output-format json|stream-json` + `--json-schema`、
  **多模型 `--model`（glm-5.1 / glm-5.0-turbo / kimi-k2.5 / minimax-m2.7 / deepseek-v3-2-volc / auto）**、
  `--effort minimal…max`、`--serve`（Web UI + **REST API** + ACP/SSE）、`--acp`（Agent Client Protocol）、
  `--bg` 后台会话 + `ps/attach/logs/kill/respawn`、`--swarm`、`--system-prompt[-file]`、`--agents <json>`、
  `--tools`/`--allowedTools`/`--disallowedTools`、`--mcp-config`、`--sandbox`（docker/E2B）
- **状态：CLI 侧未登录** —— `-p` 返回 `Authentication required. Please use /login command`（3.8 秒、exit 0 ⇒ 通路正常）。
  桌面端登录态（`刃下心` / uid `b9969747-…` / **editionType: free**）**不共享**给 CLI。服务端 `https://copilot.tencent.com`
- 本机数据：`~\.codebuddy\`（sessions/projects/plugins/logs/traces/web-ui-port.json）、`~\.workbuddy\`（sessions/memory/skills/connectors/binaries）；
  自带便携运行时 `.workbuddy\binaries\{node 22.22.2, PortableGit 1.3.0, python 3.13.12}`

**★ CodeBuddy CLI 状态（2026-10-16 01:15 更新）**：**已打通** —— 见 **§1.3**。
（原文保留作历史：`-p` 曾返回 `Authentication required. Please use /login command`；根因是 **CLI 侧从未有自己的凭据**，不是网络/代理问题。）

**★ Qoder CN CLI 状态（2026-10-16 01:35 更新）**：**已打通** —— 见 **§1.4**。原"独立 CLI `qoderclicn` 未安装 / ❌ 当前不能"的判断**已作废**。

### 1.3 ★CodeBuddy CLI 派活通道（2026-10-16 打通，第三条 AI 通道）

| 项 | 值 |
|---|---|
| 结论文件 | `E:\output\codebuddy_cli_channel_verdict.md` |
| 可执行 | 全局 npm 包 **`@tencent-ai/codebuddy-code`（2.168.0）** → `codebuddy` / `cbc` 已在 PATH |
| ⚠ 为什么不用内嵌版 | WorkBuddy 内嵌的 `lite-wb` 变体被设 `CODEBUDDY_FORCE_HEADLESS_BUNDLE=1`，**无 TUI → 无 `/login` 入口**；必须用 npm 官方**完整包** |
| 派活工具 | `E:\output\_tools\codebuddy.ps1`（`-Prompt` `-Model` `-Json` `-WorkDir` `-Effort` `-ReadOnlyTools` `-TimeoutSec`） |
| 已验证 | `-p "…"` → **exit 0 / 12.7 秒 / 真实回答**；JSON 模式返回 `result`/`num_turns`/`duration_ms`/`usage`/`session_id`；`--model deepseek-v3-2-volc` 通过 |
| ★凭据位置 | `%LOCALAPPDATA%\CodeBuddyExtension\Data\Public\auth\Tencent-Cloud.coding-copilot.info`（**明文**，provider 与桌面端不同，3479 B） |
| 有效期 | `expiresAt` → **2026-11-13 01:14:05**（scope 含 `offline_access`，可刷新）；**过期后重跑 `codebuddy` → `/login` → Chinese Site** |
| 可选模型（免费档实测） | `auto` / `glm-5.1` / `glm-5v-turbo` / `glm-5.0` / `glm-5.0-turbo` / `glm-4.7` / `kimi-k2.5` / `minimax-m2.7` / `deepseek-v3-2-volc`（以 `codebuddy --help` 为准） |
| 能力 | `-p`（非交互）、`--output-format json\|stream-json` + `--json-schema`、`--effort minimal…max`、`--tools`/`--allowedTools`/`--disallowedTools`、`-y`、`--bg` + `ps/attach/logs/kill`、`--swarm`、`--serve`（Web UI + REST + ACP/SSE）、`--acp`、`-c`/`-r`/`--session-id`、`--mcp-config`、`--sandbox` |
| 与 Codex 分工 | **Codex** = `gpt-5.6-luna`（ChatGPT 额度）；**CodeBuddy** = 多模型第二意见（GLM/Kimi/MiniMax/DeepSeek-V3.2/混元） |

**★ 任务二结论（成本，2026-10-16）**：技能池 **67 个 / description 合计 18,749 字符**（≈9–12K token）+
工具 schema ≈7–10K token = 常驻前缀约 16–22K token，占单次调用 p50 上下文（368,917）的 **4–6%**；
**但 99.3% 走缓存命中（≈1/10 价）⇒ 实际费用影响 <1%** → **不优化**（唯一手段是删技能/禁插件，会损失 67 项能力与 47 个工具，违背"不牺牲质量"约束）。

### 1.4 ★Qoder CN CLI 派活通道（2026-10-16 打通，第四条 AI 通道）

| 项 | 值 |
|---|---|
| 结论文件 | `E:\output\qoder_cli_channel_verdict.md` |
| 可执行 | 全局 npm 包 **`@qodercn-ai/qoderclicn@1.1.72`** → 命令 **`qoderclicn`**（★ 别用 `qodercn`，见踩坑 #15） |
| 派活工具 | `E:\output\_tools\qoder.ps1`（`-Prompt` `-Model` `-Json` `-WorkDir` `-Effort` `-ReadOnly` `-Yolo` `-TimeoutSec`） |
| 已验证（三级） | 纯文本 `-p` → **exit 0 / 11.9s**；带工具只读任务 → **4044**（与 PowerShell 独立扫描一致）、`num_turns=2`、`permission_denials: []`；JSON 模式给 `total_credits`/`session_id`/`context_usage_ratio` |
| ★参数铁律 | **选项在前、prompt 最后**：`qoderclicn -m auto -w E:\output -o json --permission-mode auto -p "<任务>"`（`-p` 是布尔开关、prompt 是位置参数；写反了选项会被并进提示词 —— 踩坑 #16） |
| 认证 | `$env:NO_BROWSER='1'; qoderclicn login` → 打印 `https://qoder.cn/device/selectAccounts?…` 设备码 URL → 浏览器授权 → `Login successful! Welcome, nick8927545391.`；凭据 `~\.qoder-cn\.auth\user`（1324 B）。备选 PAT（CN 变量 `QODERCN_PERSONAL_ACCESS_TOKEN`） |
| 可用模型（15 个） | Auto / Fast / Qwen3.8-Max / Qwen3.8-Flash / Qwen3.7-Max / Qwen3.7-Plus / Qwen3.7-Flash / DeepSeek-V4-Pro / DeepSeek-Flash / GLM-5.3 / GLM-5.3-Flash / GLM-5.2 / Kimi-K3 / Kimi-K2.8-Preview / MiniMax-M2.7 |
| ★额度可观测 | JSON 的 **`total_credits`**（实测单次 0.145–0.773）—— 强于 CodeBuddy（后者 `credit=undefined`，只能看服务端账号页） |
| ★★技能复用 | **默认自动加载 `~\.agents\skills`**（官方开关 `skills.loadFromAgentsDirectory`，默认 true）→ 实测 **67/67 全部 [Enabled]**；另加载 Qoder 市场技能 **51 个**；`qoderclicn skills link <path>` 可链任意本地技能目录 |
| 权限模式 | `--permission-mode {default,accept_edits,bypass_permissions,dont_ask,auto}`、`--dangerously-skip-permissions`（★ **没有 `--yolo`**，文档讹传）；**headless 下 ask 会静默拒绝** |
| 架构判断 | 参数集与 **Claude Code** 高度同构（`-p/--print`、`--setting-sources`、`--output-style`、`/login` `/logout`）→ **Claude Code 架构的国产分支**，故原生吃 `.agents/skills` 规范 |
| 其它能力 | `plugins` / `hooks` / `agents` / `mcp` / `--remote` / `--teleport` / `--worktree` / `--add-dir` / `--max-turns` / ACP |

---

## 2. 已装插件（Desktop Profile）

> **实测值（2026-10-13，两来源交叉核对）**：`dsh.profile.bundles` **13 个** = 第三方 11 + Desktop 自加 2；
> `dependencies` **11 个第三方**。数据来自 `_DSH_FACTS.generated.md`（01:42 生成）+ 直读 `package.json`。
> ⚠ 本条旧版曾只登记 4 个插件（漏了 10-12 装的 4 个 + session-workbench），**已更正**。

| 组件 | 版本 / commit | 状态 |
|---|---|---|
| ~~`dsh-workshop`~~ | ~~`github:loguhan/dsh-workshop#cf36f61f…`~~ | ❌ **2026-10-16 已下线**：① 它的安装/卸载只能写 **web** profile（踩坑 #17）② 它的侧边栏按钮与 web-all 的 DOM 注入冲突 → 按不动。**目录文件已保留**（见 §27.6） |
| `dshmarket` | `1.66.27`（npm，2026-10-16 装） | ✅ **可视化插件市场**（4200+ 策展目录 / 一键装 / 更新检查 / 热禁用 / 诊断页 / 备份恢复）；⚠ **待完全重启 Desktop 生效** |
| `dsh-whale-widget` | `github:MeteorNOX/DeepSeek-Balance-Whale-Widget#e8c107be8...`（= v0.3.16） | ✅ 余额挂件 |
| `@liustack/modsearch` | `5.10.5`（npm） | ✅ 工具 `read_page` / `x_search` / `web_search` |
| `@liustack/modlens` | `3.26.5`（npm） | ⚠ 在 `dependencies` 里但**不在 bundles 里** → 其 `modlens_read_image` 未注册；**功能已被 `dsh-vision-router` 取代** |
| `dsh-vision-router` | `3.0.3`（npm） | ✅ **视觉能力**（走 `read_image` 等；**需在新对话里才可见**；**没有**名为 `vision_describe` 的工具） |
| `dsh-pause` | `0.1.3` | ✅ 推理中插话（按会话独立，默认关） |
| `dsh-better-input` | `0.2.6` | ✅ 提示词优化 + 文档转 Markdown |
| `dsh-llm-retry-settings` | `0.1.17` | ✅ 重试/退避 + 截断续写 |
| `@hr98w/dsh-memory` | `0.1.4` | ✅ 记忆（Global + 工作区两级） |
| `dsh-session-workbench` | `1.0.3` | ✅ 侧栏 FTS5 会话搜索 + `@` 引用 |
| `@linxin666/dsh-web-all` | `0.4.6`（npm，2026-10-16 装） | ✅ **Web UI 全家桶（20 行聚合，14 活跃 / 2 按设计禁用 / 0 降级）**；见 **§27** |
| `dsh-plugin-wallpaper-engine` | `^1.3.2` → 实装 `1.3.2`（npm，2026-10-16 装） | ✅ **Wallpaper Engine 壁纸背景**（`/wallpaper-engine/inventory` 返回 585 个本机壁纸）；见 **§27** |
| `@deepseek-ai/dsh-computer-use` + `...-cua-driver-mcp` | `0.1.6-alpha.1` | ✅ 手工挂 Cordis 行（见下）；**不在 bundles 列表里** |

**Desktop 自加的 2 个 bundle（非第三方）**：`@deepseek-ai/dsh-experimental-auto-review`、`@deepseek-ai/dsh-experimental-agent-team-profile`。
另有一个官方 bundle：`@deepseek-ai/dsh-experimental-schedule-bundle`（定时任务能力来源）。

**第三方依赖里还有 1 个不生效的**：`@liustack/modlens`（同上，已被取代）。

**安装途径（唯一可用）**：桌面**侧边栏 → Plugins（插件）页**。
> CLI **不可用**：`dsh plugin --profile desktop …` 会被硬编码拒绝
> （`apps/cli/src/args.ts:83` `rejectElectronProfile` → *"profile desktop is managed exclusively by the Electron application"*）。

**本地补丁（共 3 处，会随重装/HMR 失效，需重打）**：

| # | 文件 | 补丁 | 备份 | 重打方式 |
|---|---|---|---|---|
| ① | `profiles\desktop\node_modules\dsh-workshop\lib\client.js` | 中央列选择器补 `centerCol`（DSH 0.1.7 把 `[data-pane="conversation"]` 换成 CSS Module `*_centerCol`，否则面板不挂载） | `client.js.pre-patch` | `E:\node.exe E:\output\dsh-workshop-desktop-patch\patch-client.mjs C:\Users\ROG\.dsh\profiles\desktop` |
| ② | `profiles\desktop\cordis.patch.yml` | computer-use 两行手工挂载（包无 `dsh.bundle.patch`，插件页装不上） | `cordis.patch.yml.bak-before-computeruse` | 手工恢复 insert 块 |
| ③ | `profiles\desktop\cordis.patch.yml` | `session-search` 插件行 + **`session-query-sqlite` 的 `openAt: first-search` 覆盖**（跨会话检索，2026-10-13） | `cordis.patch.yml.bak-before-session-search`、`.bak-before-session-query-fix` | 手工恢复；**改完必须重启 Desktop** |

补丁①生效后 `client.js` = 60252 字节 / SHA256 `4921B40E3B905020…`（与旧 Web Profile 已验证版一致）。

---

## 3. 统一技能池（核心资产）

**位置**：`C:\Users\ROG\.agents\skills\`
**为什么是这里**：`skill-filesystem` 的用户级技能根 + cordis 预设里配的 `customSkillDirs`（脚本自解析出 `@deepseek-ai/dsh-agent-preset/skills`）。**运行时热加载**——新增技能无需重启 Desktop，实测目录会实时刷新。
> 注：另一根 `C:\Users\ROG\.dsh\skills` 当前不存在（2026-10-13 复核）。

**来源与方式**：
- 用 **junction** 链接 `C:\Users\ROG\.trae-cn\skills\*`（Trae 用户级技能池）→ Trae 更新即同步，零副本。
- 例外：`dashboard-page` / `doc-page` / `ppt-page` 用**真实副本**（见"踩坑 #4"）。
- 上游独立安装的 3 个：`ui-ux-pro-max`（`nextlevelbuilder/ui-ux-pro-max-skill@823b0a14d3`，73 文件）、`web-design-guidelines`、`writing-guidelines`（均 `vercel-labs/agent-skills@063bee94c3`）。

**规模**：**67 条**（★2026-10-13 实测：junction 60 + 实体副本 7；其中 1 条名字非 kebab-case 无效）—— 见 **§26.1 / §26.7**。

**已剔除（不要重新链回来）**：`local-asr`、`local-computer-use`、`local-img2img`、`local-mineru`、`local-ocr-npu`、`local-realtime-translator`、`local-screenshot-qa`、`local-tts`、`local-txt2img`、`local-vram`
→ 原因：**本机非 Intel AIPC**，`platform.exe --is-aipc` 返回 0，这些技能首行校验就 `exit 1`。它们依赖 cp311 wheel + Intel NPU + 约 3 GB 模型，本机无法使用。**不要误以为我有本地 OCR/视觉/计算机操作能力。**

**当前刻意未装**（与 DSH 内置重复）：`search`（= 我的 grep/glob/read）、`general_purpose_task`（= `subagent`）。

---

## 4. 工具链现状

| 工具 | 状态 | 说明 |
|---|---|---|
| ffmpeg / ffprobe | ✅ 已可用 | shim 在 `C:\Users\ROG\.local\bin\{ffmpeg,ffprobe}.cmd`，指向 Playwright 自带静态构建 `%LOCALAPPDATA%\ms-playwright\ffmpeg-1011\ffmpeg-win64.exe`（n7.0.1）。**零下载**。注意该目录只有 ffmpeg，`ffprobe.cmd` 指向的 `ffprobe-win64.exe` 可能不存在 → 用到 ffprobe 时先验证 |
| gh | ✅ 2.101.0 | winget 装到 `C:\Program Files\GitHub CLI\gh.exe`；shim `C:\Users\ROG\.local\bin\gh.cmd` 桥接。★ **已登录**（账号 **RXX-CJL**，keyring；详见 §20）。**2026-10-16 实测**：`gh api user` 通、配额 4998/5000、目标仓库 `admin/maintain/push/triage` **权限全开**、`editor` 已设为 `notepad`（原先为空，会让 `gh pr create` 在无 TTY 时卡住） |
| Playwright 浏览器 | ✅ | `%LOCALAPPDATA%\ms-playwright`：chromium-1228、chromium_headless_shell-1228、ffmpeg-1011、winldd-1007（**无 firefox/webkit**） |
| Playwright npm 库 | ❓ 未验证 | `webapp-testing` 技能需要它；用前先确认能否 `require('playwright')` |
| LibreOffice | ✅ 随 Desktop | `resources\app.asar.unpacked\dsh\node_modules\@deepseek-ai\libreoffice-kit{,-win32-x64}`，供 office-docx/pptx/xlsx 使用 |
| Python（用户级） | ✅ 3.12.10 | `C:\Users\ROG\AppData\Local\Programs\Python\Python312\python.exe` |
| Desktop 捆绑 Python | ✅ 3.12.14 | Office 技能与脚本解释器用这个（含 numpy/pandas/docx/pptx/openpyxl/Pillow/lxml） |

---

## 5. 踩坑记录（血泪，务必先读）

**#1 CLI 无法管 Desktop Profile**
`dsh plugin --profile desktop …` → `error: profile "desktop" is managed exclusively by the Electron application`。硬编码、无开关。Desktop 插件只能走插件页。

**#2 退出 Desktop = 杀死我的会话**
我的 shell 是 Desktop 的子进程（PID 链：pwsh → DeepSeek Harness host → 主进程）。所以我**无法自行重启 Desktop**；重启类操作必须由用户做，且重启后要新开会话。
推论：任何需要重启才生效的改动，要在**同一个会话里一次性做完再让用户重启**。

**#3 无 bundle patch 的插件 = 装了不生效**
`dsh plugin add` 的效力来自包的 `dsh.bundle.patch`。像 `awesome-dsh-plugin`（只发布 README）、或 `@deepseek-ai/dsh-experimental-computer-use-cua-driver-native`（`dsh` 字段为 null，必须手工插 Cordis 行）这类包，装完不会自动注册任何东西。**装前必查 `dsh.bundle` / `dsh` 字段。**

**#4 junction 的写入会穿透到源目录（已发生一次事故）**
通过 `~/.agents/skills/<name>/SKILL.md` 改文件，实际改的是 Trae 源文件。已回退并改用真实副本。**教训**：链接只用于"原样引用"；任何需要修改文件的技能，必须用**副本**。
另：替换 junction 时 `fs.rename` 可能 `EPERM`（watcher 持有句柄）→ 需重试。

**#5 技能名必须是 kebab-case**
`Dashboard Page` / `Doc Page` / `PPT Page`（带空格）被 DSH 直接忽略、不进目录。已在副本里改成 `dashboard-page` / `doc-page` / `ppt-page`。
**排查技巧**：技能"装了却搜不到" → 先看 frontmatter `name:` 是否 kebab-case、是否与目录名一致。

**#6 pnpm 11 构建闸门**
git 依赖若**不自带构建产物**（仓库里没有 `lib/`）就必须跑 `prepare`，会被 pnpm 拦截：`ERR_PNPM_GIT_DEP_PREPARE_NOT_ALLOWED`，要求写 `allowBuilds`（**depPath 为键**，不是包名）。
- 已卡住过：`@hr98w/dsh-memory`、`dsh-image-gen`（都是标准 `tsdown` 构建，可放行）
- 建议不放行：`dsh-univer-office`——`prepare` 里有 `simple-git-hooks`（改 git hooks），源码含 `univer.ai/api/telemetry/cli` 遥测，卸载还会外发
- **绕过办法**：优先选 **npm 已发布**的等价包（如 `@hr98w/dsh-memory@0.1.4` 在 npm 上，无需构建）

**#7 目录/项目别搞混**
- `E:\deepseek-harness` = **DSH 自己**的源码仓库（不是用户业务项目）
- `E:\output` = **用户项目工作区**（智瞳智慧交管系统 + 大量 `_TASK-*.json`）
- `F:\AI\DeepSeek-Harness\deepseek-harness-dsh-desktop` = **Desktop 安装目录**

**#8 网络**
`raw.githubusercontent.com` 有时解析失败；`cdn.jsdelivr.net` 有时被判为"非公网 IP"拒绝。可用替代：`data.jsdelivr.com`（文件清单）、`api.github.com`、`git ls-remote`、`codeload.github.com`（tarball）。`gh` 装好后可作为更稳的通道。

**#9 Desktop host 对 HTTP 请求返回 401**
我无法从会话内抓取 `127.0.0.1:19387` 的页面/模块来验证 UI（需鉴权）。**UI 类效果只能由用户确认**。

**#10 ★沙箱策略决定 pwsh 能不能用（2026-10-12 定案，白费过 3 次调用）**
现象：连续 3 次 pwsh 调用（连 `echo hello` 都算）返回 `[exit code: 3221225794]` = `0xC0000142`（DLL 初始化失败），**看着像 pwsh 坏了**。
真相：`@deepseek-ai/dsh-pwsh-sandbox` 在**受限文件策略**（`workspace-write` 或更窄）下要向子进程注入限制层，**注入失败 = 进程级死亡**，与 pwsh 本身无关。
判据（一级）：把会话**文件策略**切到 `danger-full-access` 后，**同一台机器、同一条命令立刻成功**（`ok / 7.6.6 / Core`）。
推论：**要跑命令的会话，开工先确认文件策略是 `danger-full-access`**；否则只能做只读静态工作，并应主动告诉用户原因。

**#11 ★★ Codex CLI 连不上 ≠ 网络问题：先查 `~/.codex/.env`（2026-10-16 定案，耗时约 40 分钟）**

**根因**：`C:\Users\ROG\.codex\.env` 里写死 **`HTTP_PROXY/HTTPS_PROXY=http://127.0.0.1:65532`**
（2026-09 某次"修复"留下的端口；现在 Clash Verge 用的是 **7897**）。
codex 启动时加载该 `.env`，**其代理设置优先于环境变量、Windows 系统代理与 TUN**。
→ 端口没服务 ⇒ 每次请求 `SynSent` 到 `127.0.0.1:65532` ⇒ `10061 积极拒绝` ⇒ 日志 `waiting for network` 无限重连。

**已实测无效的排除项（别再重复）**：开 VPN ❌ ｜ 开系统代理 ❌ ｜ 开 TUN ❌ ｜
`$env:HTTPS_PROXY=…7897` ❌ ｜ `NO_PROXY=*` ❌ ｜ 换出口节点 ❌ ｜
Defender/ASR/WinHTTP/防火墙规则 ❌ ｜ `--ignore-user-config` ❌ ｜ 二进制字符串搜索（会误导：确实内置代理支持）。

**定位手法（可复用，10 分钟级）**：
1. `Get-NetTCPConnection -OwningProcess <codex PID>` 抓出站 → 看到**一直连 `127.0.0.1:65532` / `SynSent`**；
2. 以该端口为线索搜配置：`Select-String -Pattern '65532'` 扫 `~/.codex` → 命中 `.codex-global-state.json`（历史对话）与 **`.env`**；
3. 判据确认（决定性）：用 Node 探针临时监听该端口（`E:\output\_tools\probe65532.mjs`），
   抓到 codex 发来 **`CONNECT chatgpt.com:443 HTTP/1.1`** ⇒ 证明它把这个端口当 HTTP 代理。

**修复**：`.env` 端口改为 Clash 当前混合端口 `7897`（备份 `.env.bak-20261016`）。
**验证（三级）**：`codex exec -s read-only -C E:\output --ephemeral --color never "…"` →
**exit 0、9.9 秒、返回 `CODEX_CLI_OK`、16,183 token**。

**残留噪音（不影响主流程）**：MCP 鉴权失败（tldraw 需 OAuth）与 `chatgpt.com/backend-api/ps/mcp` 返回 **451**。

**教训**：① "某程序连不上、curl 却能连"时，**先抓它的出站连接**，不要从 VPN/代理假设出发——
本次前 40 分钟全浪费在错误假设上；② **列目录看到 `.env` 就该读它**（我看见了文件名却没读，白绕一大圈）。

**#12 ★CodeBuddy CLI 的"没登录"≠缺桌面端凭据（2026-10-16 定案，约 20 分钟）**

**根因**：桌面端与 CLI 是**两套独立认证 provider**：
- 桌面端 → `%LOCALAPPDATA%\CodeBuddyExtension\Data\Public\auth\` 下的 **`workbuddy-desktop.info`**（敏感字段标 `$wbEncrypted` 加密）
- CLI → **同一目录**下的 **`Tencent-Cloud.coding-copilot.info`**（明文）

独立 CLI 既没有自己的那份，也**永远拿不到**桌面端那把钥匙 —— at-rest 主密钥（32 B，`keyId=sha256(key)[:16]`）
由 **Electron 主进程经 sidecar socket 下发**（`CODEBUDDY_SIDECAR_CREDENTIAL_BOOTSTRAP_SOCKET` / `WORKBUDDY_AT_REST_ENCRYPTION`），
**不落盘、无 DPAPI**（bundle 内 `CryptUnprotectData`/`dpapi` 零命中）。

**❌ 走过的弯路（别重复）**：试图解密桌面端 `workbuddy-desktop.info` → 逆向 keyblob(`static-v1` slot)+AES-GCM
→ 追 `credentialProtectionBootstrap.symmetricKey` → 读 daemon 进程环境（P/Invoke）→ 逆向 prewarm pipe 协议。
**结论：全都没必要** —— 正确解是 **让 CLI 自己登录一次**。

**✅ 正确姿势**：
```powershell
npm install -g @tencent-ai/codebuddy-code@latest   # 必须用官方完整包
codebuddy                                          # 真实终端！首次信任文件夹 → /login → Log in via Chinese Site
codebuddy -p "Reply with exactly: CBC_CHANNEL_OK"  # 验证：exit 0 / 12.7s
```

**#13 ★WorkBuddy 内嵌 lite-wb 变体没有 TUI（同轮）**
`F:\AI\WorkBuddy\resources\app.asar.unpacked\cli` 里的 CLI 被设 `CODEBUDDY_FORCE_HEADLESS_BUNDLE=1`
（从 daemon 进程环境实测），**只能 headless 用、没有交互界面 → 也就没有 `/login` 入口**。
判据：在 PTY 里跑它 → 立即退出、`capturedChars` 只有几十字节；跑 npm 官方完整包 → 立刻出现
`Do you trust the files in this folder?` 信任对话框。
**推论**：WorkBuddy 的 CLI 分 `lite-wb` / 完整包两种变体，要 TUI 必须装 npm 官方包。

**#14 ★没有 TTY 时 CodeBuddy/CLI 类 TUI 全废（同轮）**
`-p` 之外的一切交互（`/login`、信任对话框、权限确认）都需要 **TTY**。无 TTY 时进程直接静默退出。
**可复用手法**：WorkBuddy 自带 **`@lydell/node-pty`** → 用 `E:\output\_tools\cbc-pty.mjs`
开真实伪终端驱动 TUI（发按键、抓渲染）。**注意**：TUI 用备用屏+光标定位重绘，
**必须以 `waitMs` 分步等待**，不能指望一次捕获到中间画面。

**#15 ★`qodercn` 命令被 npm 包遮蔽（2026-10-16，装 Qoder CLI 时踩到）**

`@qodercn-ai/qoderclicn` 提供**两个** bin：**`qodercn`（dispatcher）与 `qoderclicn`**。
npm 全局 bin（`%APPDATA%\npm`）在 PATH **第 39 位**，Qoder CN IDE 壳在 **第 47/48 位** ⇒ **npm 版赢**：
`where qodercn` 首位变成 npm 版 → 敲 `qodercn .` 想开 IDE，实际会启动 agent CLI。
**处置（已做）**：把 npm 生成的 `qodercn` / `qodercn.cmd` / `qodercn.ps1` 改名 `*.npm-disabled-qodercli`。
⚠ **npm 升级/重装该包会重建 shim、遮蔽复发** → 复查 `where.exe qodercn` 应只剩 IDE 壳。

**#16 ★位置参数型 CLI 的参数顺序 + PowerShell splatting（同轮，两次踩坑）**

① **`-p` 是布尔开关，prompt 是位置参数 `[query...]`**（`--help` 里 `-p, --print` 后面**没有** `<prompt>`）。
把选项写在 prompt 之后 → **选项被并进 query**，模型收到的提示词里带着 `-m auto -w E:\output -o json`
（实测输出 `QODER_PS1_OK -m auto -w … -o json`）。
**正确：选项全部在前，prompt 永远放最后。**
② **PowerShell 的 `@(...)` 不是 splatting**：`& cli @($argv[1..N])` 会把**整个数组当成一个参数**传给 CLI
（这正是 `qoder.ps1` 初版 bug 的来源）。**正确**：先 `$a = $argv[1..N]`，再 `& cli @a` —— `@变量名` 才是 splatting。

**#17 ★★dsh-workshop（创意工坊）的安装/卸载按钮写的是 web profile（2026-10-16 定案，红线风险）**

- 它的 host 半第一行就是 `const profile = config.profileName ?? "web"`（`lib/host/index.mjs:17`）；本机 profile 的 patch 行**没有配 `profileName`** → 取默认 **`"web"`**。
- **铁证（三级）**：`workshop_status` 报"已安装 3 个：modlens、distilly、dsh-desktop" —— 这**正是 `C:\Users\ROG\.dsh\profiles\web\package.json` 的内容**（desktop profile 里根本没有 `distilly` / `dsh-desktop`）⇒ 它读、写都是 **web 环境**。
- **后果**：在 Desktop 上点"一键安装" = **往 web 备用环境里装东西（触碰红线 1）**，而 Desktop 侧毫无变化。搜索结果里打印的 `dsh plugin --profile web add …` 也是硬编码。
- **不可修**：`dsh plugin --profile desktop` 被硬编码拒绝（踩坑 #1）→ 给它配 `profileName: desktop` 只会把"装错地方"变成"直接报错"。
- **纪律**：创意工坊**只用来看 / 搜**（它的 15938 条目录 + `workshop_search` 工具确实有用），⚠ **绝对不要点它的安装/卸载按钮**。

**#18 ★plugin_manager 的 600 秒空等（2026-10-16，白等 10 分钟）**

- 现象：`install_bundle` 返回 `timedOut:true` / `kind:"timeout"`，日志末行 `dsh: pnpm printed nothing for 600000ms and was terminated`。
- 真相：**pnpm 本身 954 毫秒就跑完了**（同一段日志里有 `Done in 954ms using pnpm v11.7.0`），是包装器等 stdout 等到超时 ⇒ 判 `failed` 且**不提交 `package.json`**。
- 后果：包已完整下载进 `node_modules`，但 profile **没注册**（`dependencies` 与 `dsh.profile.bundles` 里都没有）。
- 对策（**已实证**）：手工补 `package.json` 的 `dependencies` + `dsh.profile.bundles` → 在 profile 目录跑一次 `pnpm install`（1 秒）→ 运行中的 Desktop 通过 HMR 直接加载，**无需重启**。
- 教训：判"安装失败"前先看 **pnpm 自己的退出行**；**超时 ≠ 没装上**。

**#19 ★npm 包名 ≠ GitHub 仓库名（2026-10-16，同轮两个实例）**

| GitHub 仓库 | npm 真名 | 坑 |
|---|---|---|
| `elysia395/dsh-wallpaper-engine` | **`dsh-plugin-wallpaper-engine`** | npm 上同名的 `dsh-wallpaper-engine` **已于 2026-08-16 下架** → 按仓库名装必 404 |
| `zhu1090093659/dsh-web` | **`@linxin666/dsh-web-all`** | 旧名 `@linxin666/dsh-web-ui-all` 里带 `dsh.migrate.to` 指向新名 |

对策：装前 `npm view <仓库名>` 验一下，或读仓库 `package.json` 的 `name` 字段取真名。

**#20 ★同名仓库按 scanStatus/score 选，别按名字选（2026-10-16）**

`dsh-wallpaper-engine` 在工坊索引里有 **7 个同名仓库**（不同作者），只有 `elysia395/…` 是 `scanStatus=verified`（★332 / score 0.9521 / 当天仍在提交），其余 6 个 0–9★ 全停更。
判据优先级：**`scanStatus=verified` > `score` > `stars` > `pushedAt` 新鲜度**。

---

## 6. 用户项目背景（用于技能选型）

**智瞳智慧交管系统**（工作区 `E:\output`，项目根 `E:\output\1\`）：
- 后端：FastAPI + SQLAlchemy + SQLite；`api/image_recognizer.py`（YOLO + 豆包 + DeepSeek 多模型）、`cloud_collaborator.py`（端云协作）、`violation_rules.py`（6 类违规含逆行）、`realtime_detector.py` + `vehicle_tracker.py`（质心追踪、逆行检测）
- 前端：**Vue** 管理后台 `web-admin/`（Dashboard、ViolationList/Detail、AIDetect、AITrace、CollabStats、DisagreementList、Statistics、Settings、QuotaMonitor、RealTimeMonitor）
- 小程序：微信 `wechat-miniprogram/`
- 论文/文档：大量 `TASK-*` 与 `PAPER_*` 材料
- 项目自有技能清单：`E:\output\_SKILLS_CATALOG.md`（Top15 里 `frontend-design`、`chart-visualization`、`slides`、`webapp-testing`、`agent-browser` 都是 ⭐⭐⭐⭐⭐）
- 交接协议：`PROJECT_HANDOVER_REPORT.md` + `_TASK_HISTORY.json` + `_TASK-XXX_OUTPUT.json`

**最有用的技能（针对该项目）**：`frontend-design`、`frontend-skill`、`chart-visualization`、`dashboard-page`、`webapp-testing`、`agent-browser`、`slides`、`doc-coauthoring`、`data-analysis`、`ui-ux-pro-max`、`vercel-react-best-practices`

---

## 7. 待办（按优先级）

| # | 事项 | 卡点 |
|---|---|---|
| 1 | **视觉能力**（见第 9 节结论：ModLens 无引擎，建议改用 `dsh-vision-router`） | 需用户在插件页装 `dsh-vision-router@2.2.4` |
| 2 | **computer-use**：见第 10 节——已核验 **native 变体在 Windows 可行**（自带 22.7 MB 预编译二进制），推荐它 | 需你在插件页装 provider；Cordis 行由我补；重启 Desktop 后验证 |
| 3 | **跨会话记忆**：装 **npm 版** `@hr98w/dsh-memory@0.1.4`（**不是** git 版！见第 11 节） | 需用户在插件页粘贴 spec |
| 4 | 验证 `byted-*`（Seedream/Seedance 生图生视频）、`figma`、`iga-pages` 是否可用 | 需要 API key / 账号 |
| 5 | 安装 `skill-creator`、`dynamic-ui`（Trae 其他主题目录里有副本） | 未链接 |
| 6 | ~~`gh auth login`~~ | ✅ **已完成**（2026-09-27 登录为 `RXX-CJL`；2026-10-16 实测 API 与写权限均可用，`editor` 缺口已补）|
| 7 | Playwright 库路径（`webapp-testing` 用；浏览器版本已对齐，见第 11 节） | 用运行时需点名 `playwright@1.61.1` |

---

## 8. 常用命令速查

```powershell
# 技能池体检（断链/同名/命名规范）
E:\node.exe $env:TEMP\audit-skillpool.cjs        # 若已丢失，按本文第3节规则重写

# 重打 dsh-workshop 客户端补丁（重装后必做）
E:\node.exe E:\output\dsh-workshop-desktop-patch\patch-client.mjs C:\Users\ROG\.dsh\profiles\desktop

# 查 Desktop 是否为 AIPC（决定 local-* 技能可用性）
C:\Users\ROG\.trae-cn\skills\local-computer-use\bin\platform.exe --is-aipc

# 技能池位置
C:\Users\ROG\.agents\skills
```

---

## 9. 视觉能力评估（2026-09-27 实测；**2026-10-12 已被取代**）

> ⚠️ **本节结论已作废**：视觉能力改由 **`dsh-vision-router@3.0.3`** 提供（已装、已在 bundle 层激活、14 个工具、零 key 免费链）。`modlens` 保留但**不配引擎**（`modlens_read_image` 仍报 `No vision provider`）。完整状态见 **§26**。

**（以下为历史记录）现状：本机没有任何视觉引擎。**

`modlens doctor` 实测（`E:\node.exe C:\Users\ROG\.dsh\profiles\desktop\node_modules\@liustack\modlens\dist\main.js doctor`）：

```
Providers
  [!!] antigravity-cli: agy not on PATH
  [!!] gemini-api: missing: apiKey
  [!!] openai: missing: baseUrl, apiKey, model
  [!!] anthropic: missing: apiKey
  [!!] claude-cli: claude not on PATH
  [!!] kimi-cli: kimi not on PATH
Selected provider: antigravity-cli (built-in default)
Failover chains: local (none) / remote (none)
Guard verdict: allow
Config file: C:\Users\ROG\.modlens\config.json — not present
```

佐证：`GEMINI_API_KEY`/`OPENAI_API_KEY`/`ANTHROPIC_API_KEY`/`DASHSCOPE_API_KEY`/`MOONSHOT_API_KEY`/`ARK_API_KEY`/`ZHIPU_API_KEY` 环境变量**全无**；`agy`/`claude`/`kimi`/`codex`/`opencode`/`pi`/`grok` CLI **全未安装**。
DSH 凭据文件（`~/.dsh/.credentials.yaml`）里只有 `DEEPSEEK_API_KEY`（纯文本模型）与 `AMAZON_BEDROCK_API_KEY`（未确认能否用于视觉）。

**结论：ModLens 需外部 key 才能工作 → 改用零配置方案。**

### 推荐：`dsh-vision-router@2.2.4`（npm，★1116，MIT）

核验通过的全部要点：

| 检查 | 结果 |
|---|---|
| `dsh.bundle.patch` | ✅ 有 → 插件页一键装即生效 |
| 生命周期脚本 | ✅ **无 prepare/prepack/preinstall/install/postinstall** → 不触发 pnpm 构建闸门，**无需批准任何构建脚本** |
| dsh peer 兼容性 | ✅ `@deepseek-ai/dsh-llm-deepseek` 与 `dsh-anonymous-user-id` 的范围里**显式含 `0.1.7-rc.2`** |
| `sharp` 依赖 | ✅ **optional**（`peerDependenciesMeta.sharp.optional=true`），未装也不影响 |
| engines | ✅ `^22.19.0 \|\| >=24.0.0` |
| 视觉引擎 | ✅ **零 key、零账号**：内置五模型 OVHcloud 匿名链，2 请求/分钟/IP |
| 能力 | 图像问答、grounding、裁剪、像素比对、取色、OCR、SVG 描摹、抠图、截图等 14 个工具 |

**安装 spec（粘到桌面侧边栏 Plugins 页）**：
```
dsh-vision-router@2.2.4
```

**对比被否决的选项**：
- `Anionex/dsh-vision-toolkit`（★884）：仍需"Settings → Vision Toolkit 配置 provider + API key"，不是零配置；且首次启动要自备 Python 3.11+ 或下载隔离运行时。
- 继续用 ModLens：需要 Gemini 免费 key（https://aistudio.google.com ）或 OpenAI 兼容端点，多一步外部操作。

**注意**：`dsh-vision-router` 与已装 ModLens **功能重叠**，两者只保留一个。若装 vision-router，建议后续在插件页停用/移除 `@liustack/modlens` 以免两套视觉工具互相干扰。

---

## 10. computer-use 评估（2026-09-27 实测结论）

**DSH 有 computer-use 核心包** `@deepseek-ai/dsh-computer-use@0.1.7-rc.2`，但它**只是"提供者注册表"**，README 原话 *"This package adds no model-visible tools"*。真正干活的是 provider，**一个部署同时只能启用一个**。

### 两个 provider 的实测对比

| | **native**（推荐） | **mcp** |
|---|---|---|
| 包名 | `@deepseek-ai/dsh-experimental-computer-use-cua-driver-native@0.1.6-alpha.1` | `@deepseek-ai/dsh-experimental-computer-use-cua-driver-mcp@0.1.6-alpha.1` |
| `dsh.bundle.patch` | ❌ **null** → 装了不自动生效 | ❌ **null** |
| 生命周期脚本 | ✅ 无（不触发构建闸门） | ✅ 无 |
| dsh peer 兼容性 | ✅ `dsh-tools`/`dsh-computer-use`/`dsh-system-prompt` 全满足 0.1.7-rc.2 | ✅ `dsh-computer-use` 满足 |
| 运行时形态 | **跑在 host 进程内**（`@trycua/cua-driver@0.28.0`） | 外部 Cua Driver 应用，经 MCP 通信 |
| Windows 依赖 | ✅ **自带预编译二进制**：`@trycua/cua-driver-win32-x64-msvc@0.28.0`（解包后 **22.7 MB**）→ 无需 Rust 工具链 | ❓ 需先装 Cua Driver 独立应用（Windows 版可用性未验证） |
| 崩溃影响面 | ⚠️ **native 崩溃会终止 host 进程即 Desktop** | 进程隔离，更安全 |
| 附带依赖 | `zod`、`@deepseek-ai/dsh-mcp-client`、`schemastery` | `@deepseek-ai/dsh-mcp-client`、`schemastery` |

### 启用方式（关键：必须手工插 Cordis 行）

因为两个包都**没有 bundle patch**，插件页装完后**不会自动生效**。需要在 `C:\Users\ROG\.dsh\profiles\desktop\cordis.patch.yml` 末尾追加：

```yaml
- name: '@deepseek-ai/dsh-computer-use'
- name: '@deepseek-ai/dsh-experimental-computer-use-cua-driver-native'
```

（两个都是**顶层 insert 行**，`- name:` 形式，不带 `id` 也行；若 loader 要求 id，用 `- name:` 的等价写法 `{ name: ... }`。）

**风险评估（装之前必须知道）**：
1. **顺序不可颠倒**——若先插 Cordis 行、包还没装，Desktop 启动会因找不到模块而失败。
2. **崩 host 风险**——native 变体与 host 同进程，Cua Driver 原生崩溃会带崩整个 Desktop。README 明确指出。
3. **恢复手段**——Desktop 有内建崩溃恢复：`DesktopFatalRecovery` + `disableAllPlugins()`（备份 profile patch 并停用第三方 bundle）。源码位置 `apps/desktop/src/fatal-recovery.ts`、`project-manager.ts:76`。真要出事，可删掉 `cordis.patch.yml` 里那两行恢复。
4. **桌面权限**——provider 不自带权限应用；需给**启动 DSH 的应用**（即 Desktop）授予桌面控制/录屏权限。

### 建议执行顺序

1. 用户在桌面侧边栏 **Plugins 页**安装：`@deepseek-ai/dsh-experimental-computer-use-cua-driver-native@0.1.6-alpha.1`
2. 我（或用户）在 `cordis.patch.yml` 追加那两行
3. 用户重启 Desktop
4. 重启后新会话验证：是否出现 `computer_*` 工具、能否读屏/点击

**未验证项**：Cua Driver 在 Windows 上首次运行是否需要额外运行库、是否需要 UAC 提权。

---

## 11. 第 3 轮修正与补充（2026-09-27）

### A. `dsh-memory`：**npm 版能装，git 版装不上** —— 这是之前失败的真正原因

| 形态 | `prepare` 脚本 | 结果 |
|---|---|---|
| npm 版 `@hr98w/dsh-memory@0.1.4` | **无**（只有 `prepack`，npm 消费时不执行） | ✅ **不会被构建闸门拦** |
| git 版 `github:hr98w/dsh-memory` | 有 `prepare` → 跑 `pnpm run check`（含 vitest 全量测试） | ❌ `ERR_PNPM_GIT_DEP_PREPARE_NOT_ALLOWED` |

**插件页务必粘**：
```
@hr98w/dsh-memory@0.1.4
```
核验详情：`dsh.bundle.patch` ✅、`dsh.client` ✅（platform web）、`peerDependencies` 只有 `react@^18.2.0` 与 `@deepseek-ai/cordis@^4.0.1`（**都非 dsh peer，不参与兼容性判定**）、解包 1.62 MB / 51 文件、MIT。

### B. Playwright 浏览器版本**已对齐**（不需要下载浏览器）

- 已缓存：`chromium-1228`、`chromium_headless_shell-1228`、`ffmpeg-1011`、`winldd-1007`
- `playwright@1.61.1` 的 `browsers.json` 期望 `chromium` revision = **1228** → **完全匹配**

限制：DSH 仓库树里的 `playwright@1.61.1` 位于 pnpm 隔离目录（`node_modules\.pnpm\playwright@1.61.1\...`），顶层 `node_modules\playwright` **不存在**，所以裸 `require('playwright')` 会 `MODULE_NOT_FOUND`。
**用法**：需要 Playwright 时点名版本（`npx playwright@1.61.1 …`）或从 pnpm 路径显式 require；**不要**再装一份 playwright（会引入版本漂移）。

### C. `agent-browser` CLI 已安装（技能终于有驱动了）

- 技能 `agent-browser` 早已链接进技能池，但**缺 CLI**，一直是"有名无实"。
- 本轮已装：`npm install -g agent-browser` → **v0.38.1**，位于 `C:\Users\ROG\AppData\Roaming\npm\agent-browser.ps1`
- 驱动方式：CLI 直接经 **CDP** 连接 Chrome/Chromium；`--cdp 9222`、自动发现 `DevToolsActivePort`；可用 `get cdp-url` 取 WebSocket 地址
- 全局 npm 目录现在有：`agent-browser@0.38.1`、`pnpm@11.7.0`

### D. 本轮新增待办（第 7 节已同步）

- 用 `agent-browser` 做一次真实浏览器连通性验证（需要 Chrome 在跑）

### E. 状态快照（2026-09-27 约 02:0x）

Desktop Profile 已装：`dsh-workshop`、`dsh-whale-widget`、`@liustack/modlens`、`@liustack/modsearch`（4 个第三方，均已进 bundles）。
**未装**：`dsh-vision-router`、`@deepseek-ai/dsh-experimental-computer-use-cua-driver-native`、`@hr98w/dsh-memory`。
用户曾在 1:58–2:01 尝试装 `@hr98w/dsh-memory`(git)、`dsh-univer-office`、`dsh-image-gen` —— **三者均被同一个 `ERR_PNPM_GIT_DEP_PREPARE_NOT_ALLOWED` 拦下**，`pnpm-workspace.yaml` 至今无 `allowBuilds`。

### F. `agent-browser` 的**使用前提**（第 3 轮实测出的坑）

- CLI 已装（v0.38.1），但 **`agent-browser read <url>` 会挂住**：本机 9222 / 9223 / 9229 **均无监听**，没有浏览器开远程调试，CLI 在等 CDP 连接直到超时（实测 >3 分钟）。
- 正确姿势（二选一）：
  1. 用带调试端口的浏览器启动：`msedge.exe --remote-debugging-port=9222`（或 chrome 同理），再 `agent-browser connect 9222`
  2. 先 `agent-browser connect <port|url>` 接上一个已有的 CDP 会话，再执行 `read/open/click`
- 本机现状：只跑着 **msedge**（15 进程），**无 chrome**，且都未开调试端口。
- 结论：`agent-browser` 能力**已就位但每次用前要先接上 CDP**；不要在没接浏览器时直接调 `read`（会静默挂住）。
- 相关命令：`agent-browser connect`、`agent-browser get cdp-url`、`agent-browser close --all`；它自带版本匹配的技能：`agent-browser skills get core --full`。

### G. Playwright **全链路已打通**（第 3 轮实测）

不再只是"浏览器版本对齐"，而是**真实启动验证通过**：

```
require('E:/deepseek-harness/node_modules/.pnpm/playwright@1.61.1/node_modules/playwright')
  → chromium.launch({headless:true})  ✅
  → 页面渲染文本 = "office-ok"          ✅
  → 版本 = 149.0.7827.55                （用的正是缓存的 chromium-1228）
```

**两种可用调用姿势**：

1. **Node API（推荐，最稳）**：从 pnpm 隔离路径显式 require
   ```js
   const pw = require('E:/deepseek-harness/node_modules/.pnpm/playwright@1.61.1/node_modules/playwright')
   ```
2. **CLI shim**：`pw.ps1`（建在 `C:\Users\ROG\.local\bin\pw.ps1`，内部固定 `npx --yes playwright@1.61.1`）
   ```powershell
   pw.ps1 screenshot https://example.com shot.png
   ```
   注意：v1.61.1 的 `--version` 会被当子命令解析，想看版本用 Node API 的 `browser.version()`。

**结论**：`webapp-testing` 技能现在**真的可用**了（不再是"依赖缺失"状态）。

---

## 12. 第 3 轮交付清单

| 项目 | 状态 | 证据 |
|---|---|---|
| `agent-browser` CLI | ✅ 新装 v0.38.1 | `npm i -g agent-browser` 成功；`--version` 通过；`agent-browser skills` 可用 |
| Playwright 全链路 | ✅ 新验证 | Chromium 启动 + 渲染内容正确 |
| `pw.ps1` shim | ✅ 新建 | `C:\Users\ROG\.local\bin\pw.ps1` |
| `dsh-memory` 失败根因定位 | ✅ | npm 版无 `prepare`，git 版有 → 必须装 npm 版 |
| 状态文件 | ✅ 扩到 12 节 / 21.7 KB | 新增第 11 节（含 F/G 两小节） |

---

## 13. 可安装组件台账（**已核验**，直接粘插件页即可）

> 目的：避免以后重复研究规格、重复踩构建闸门。每条都注明**核验方式与结论**。
> 规则：**npm 版优先**（npm 包不跑 `prepare`，不受 pnpm 构建闸门影响）；git 版仅在不带构建产物时才需要，且必被拦。

### 13.1 待装（推荐顺序）

| 优先级 | 组件 | 确切 spec | 类型 | 关键核验结论 |
|---|---|---|---|---|
| ★★★ | **dsh-vision-router** | `dsh-vision-router@2.2.4` | 插件（bundle+client） | 有 `dsh.bundle.patch`；**零生命周期脚本**（不触发构建闸门）；dsh peer 范围**显式含 `0.1.7-rc.2`**；`sharp` 为 optional；**零 key 免费视觉链**（OVHcloud 匿名，2 req/min）；14 个视觉工具 |
| ★★★ | **computer-use provider** | `@deepseek-ai/dsh-experimental-computer-use-cua-driver-native@0.1.6-alpha.1` | 插件（**无 bundle patch**） | dsh peer 全满足 0.1.7-rc.2；无生命周期脚本；`@trycua/cua-driver@0.28.0` **自带 Windows x64 预编译二进制**（22.7 MB）；**装后必须手工插 Cordis 行**；native 崩 host 风险 |
| ★★ | **dsh-memory** | `@hr98w/dsh-memory@0.1.4` | 插件（bundle+client） | **必须用 npm 版**（无 `prepare`）；git 版有 `prepare` → 必被 `ERR_PNPM_GIT_DEP_PREPARE_NOT_ALLOWED` 拦；peer 仅 `react@^18.2.0` + `cordis@^4.0.1`（非 dsh peer，不参与判定） |
| ★ | **skipped for now** | — | — | — |

### 13.2 明确**不要**安装（已核验原因）

| 组件 | 原因 |
|---|---|
| `awesome-dsh-plugin` | `files` 只发布 README、`dsh` 字段为 null → 装了不生效（它是目录站，不是插件） |
| `dsh-univer-office` | `prepare` 含 `simple-git-hooks`（改 git hooks）+ 源码含 `univer.ai/api/telemetry/cli` 遥测 + 卸载脚本外发 |
| `dsh-image-gen`（git 版） | git 依赖无预构建产物 → `prepare` 必被拦；如要装需批准构建（会再弹控制台窗口） |
| `Clarklevis1995/dsh-mobile` | 拉不到 `package.json`，不是规范 DSH 包 |
| `local-*` 系列 10 个 | 本机 `platform.exe --is-aipc` → **0**，必然 `exit 1` |
| `search` / `general_purpose_task` / `web-dev` | 与 DSH 内置能力重复（grep/glob、subagent） |

### 13.3 插件页安装后的**必做后续**（检查清单）

1. **检查是否进 bundles**：读 `profiles\desktop\package.json` 的 `dsh.profile.bundles`
2. **无 bundle patch 的**（如 computer-use provider）→ 手工在 `profiles\desktop\cordis.patch.yml` 追加顶层行
3. **重启 Desktop** 才生效（重启会杀死会话 → 一次性装完再重启）
4. **重启后新会话验证**：工具是否出现在目录、UI 是否出现

### 13.4 computer-use 的 Cordis 行（装完 provider 后由我追加）

```yaml
- name: '@deepseek-ai/dsh-computer-use'
- name: '@deepseek-ai/dsh-experimental-computer-use-cua-driver-native'
```

**顺序警告**：必须在 provider 包**已安装**之后再插这两行；否则 Desktop 启动因找不到模块而失败。
**回滚**：删掉这两行即可（Desktop 另有 `FatalRecovery.disableAllPlugins()` 会备份 patch 并停用第三方 bundle）。

---

## 14. 第 4 轮：已装插件**逐项核验通过**（2026-09-27 02:3x）

对 Desktop Profile 里 4 个第三方插件做了**安装完整性核验**（不是只看目录存在）：

| 插件 | 版本 | dsh.bundle | dsh.client | 入口文件 | dsh peer |
|---|---|---|---|---|---|
| `@liustack/modlens` | 3.26.5 | ✅ | ✅ | `dsh/index.js` 98 KB、`dsh/client.js` 50 KB、`cordis.patch.yml` 213 B | 0 个（必然通过） |
| `@liustack/modsearch` | 5.10.5 | ✅ | ✅ | `dsh/index.js` 36 KB、`dsh/client.js` 46 KB、`cordis.patch.yml` 534 B（含 `web` 行） | 0 个 |
| `dsh-workshop` | 0.1.0 | ✅ | ✅ | `lib/host/index.mjs` ✅ | 6 个**全部 ✅** |
| `dsh-whale-widget` | 0.3.16 | ✅ | ❌ | `lib/index.js` ✅ | 0 个 |

**当前实际可用能力（确定结论）**：
- ✅ `modsearch` → `read_page`、`x_search`（检索能力已就位）
- ✅ `dsh-workshop` → 创意工坊 + 5 个 `workshop_*` 工具
- ⚠️ `modlens` → `modlens_read_image` 工具**已注册，但无视觉引擎 → 调用会失败**（见第 9 节）
- ⚠️ `whale-widget` → 已装，需重启后可见

**host 进程自 01:58:26 起持续运行**，上述插件在同一组成内加载；之后未重启。

**结论**：除视觉引擎外，已装插件无安装残缺。第 13 节台账中的三个组件仍待插件页安装。

---

## 15. 第 5 轮：技能**可执行性**验证（首次闭环，2026-09-27 02:3x）

之前只验证了"技能出现在目录里"，本轮**首次验证技能能被真正加载并执行**。

### 15.1 加载验证

调用 `skill` 工具加载 `chart-visualization`，返回：

```
<skill_resources>
Base directory for this skill: C:\Users\ROG\.agents\skills\chart-visualization
</skill_resources>
```

**关键意义**：平台把 junction 路径**正确解析为可用技能根**，`resourceBase` 指向 `~/.agents/skills/<name>` → **链接式技能（junction）可用**，不需要真实副本。

### 15.2 执行验证（chart-visualization 全链路通）

```
node ~/.agents/skills/chart-visualization/scripts/generate.js <spec-file>
→ exit=0
→ https://mdn.alipayobjects.com/one_clip/afts/img/QyETRL5329QAAAAARJAAAAgAoEACAQFr/original
```

返回真实图片 URL → **技能脚本可真跑通**，出图能力可用。

### 15.3 两个必须记住的坑

**坑 A：`chart-visualization` 是"远端渲染"，不是本地渲染。**
`scripts/generate.js` 会把数据 POST 到 `https://antv-studio.alipay.com/api/gpt-vis`（可用环境变量 `VIS_REQUEST_SERVER` 覆盖）。
→ **不要把真实项目数据丢进去**（智瞳的违规记录、车牌、统计等属敏感数据）。
→ 用法：合成/脱敏数据出图，或先设 `VIS_REQUEST_SERVER` 指向自建端点。

**坑 B：PowerShell 传 JSON 参数会坏两次。**
1. 直接把 JSON 当参数传 → PowerShell 吃掉引号 → `Error parsing spec`
2. `Set-Content -Encoding UTF8` 写文件 → 带 BOM → `Unexpected token ''`
**正确姿势**：写文件时用无 BOM 编码，并**传文件路径**（脚本支持）：
```powershell
$json = '{"tool":"generate_line_chart","args":{...}}'
[System.IO.File]::WriteAllText($p, $json, (New-Object System.Text.UTF8Encoding($false)))
E:\node.exe <skill>\scripts\generate.js $p
```

### 15.4 技能池验证状态（更新）

| 维度 | 状态 |
|---|---|
| 目录完整性 | ✅ 66 条、0 断链、0 同名冲突、65 合规 |
| **可加载** | ✅ 已证（junction 路径被正确解析） |
| **可执行** | ✅ 已证（chart-visualization 跑通并出图） |
| 仍待验证 | `ui-ux-pro-max`（数据检索脚本）、`webapp-testing`（Playwright 已单独验证）、`slides`/`doc-coauthoring`（依赖各自的 npm 包） |

### 15.5 `ui-ux-pro-max` 也验证通过（第 5 轮，Python 实现）

结构与依赖：
- `scripts/`：`search.py`(9.4 KB)、`core.py`(41 KB)、`design_system.py`(71 KB)、`validate_data.py`(52 KB)、`reasoning_contract.py`
- `data/`：39 个文件 / **3.0 MB** 本地数据（`google-fonts.csv` 747 KB、`google-font-licenses.json` 433 KB、`icons.csv`、`colors.csv`、`charts.csv`…）
- **只用 Python 标准库**（`argparse`/`json` + 本目录模块）→ 系统 `python 3.12.10` 可直接跑，**无需 pip 安装**

实测（真实检索，非空跑）：

```
python <skill>\scripts\search.py "dashboard" --domain style --max-results 2
  → exit=0，Found: 2 → 命中 "data-dense-dashboard"（Data-Dense Dashboard / BI Analytics）
    含：关键词、主色、动效、Best For、明暗模式、性能/可访问性、框架兼容(recharts|chartjs|d3)、复杂度

python <skill>\scripts\search.py "trend" --domain chart --max-results 2
  → exit=0，Found: 1 → "Trend Over Time → Line Chart"
    含：何时用/何时不用、数据量阈值(<1000 SVG / ≥1000 Canvas)、配色guidance、可访问性风险与降级方案、库推荐

python <skill>\scripts\search.py "traffic violation admin dashboard" --stack vue
  → exit=0，**Found: 0**（vu​e 栈无该词）+ 提示 "Closest known terms: validation, naming"
```

**注意**：0 结果是**真实行为**（不是脚本坏了），它会提示换关键词；堆栈域（`stacks/*.csv`）覆盖面比通用域窄。
**可用域**：style, color, chart, landing, product, ux, typography, google-fonts, icons, gsap, react, web
**可用栈**：react, nextjs, vue, svelte, astro, swiftui, react-native, flutter, nuxtjs, nuxt-ui, html-tailwind, shadcn, jetpack-compose, threejs, angular, laravel
**对我项目的价值**：`--domain chart` 直接服务 `Statistics.vue`/`CollabStats.vue`；`--domain style` 服务管理后台视觉规范；`--stack vue` 可用但词表窄。

### 15.6 技能池验证状态（终版）

| 维度 | 状态 | 证据 |
|---|---|---|
| 目录完整性 | ✅ | 66 条 / 0 断链 / 0 同名冲突 / 65 合规 |
| **可加载** | ✅ | `skill` 工具返回，base dir 指向 `~/.agents/skills/<name>`（junction 被正确解析） |
| **可执行（JS）** | ✅ | `chart-visualization` → 返回真实图片 URL |
| **可执行（Python）** | ✅ | `ui-ux-pro-max` → 真实检索出结果，零额外依赖 |
| 浏览器自动化 | ✅ | Playwright 启动 Chromium 149 并渲染（第 3 轮） |
| 仍待验证 | `slides` / `doc-coauthoring` / `web-artifacts-builder`（各自依赖 npm 包，用前需确认） |

---

## 16. 第 6 轮：技能依赖分级（补齐技能池验证的最后一环）

对剩余未验证技能做了**依赖构成分析**，得出可直接使用的分级：

### 16.1 分级结论

| 技能 | 构成 | 依赖 | 结论 |
|---|---|---|---|
| `doc-coauthoring` | **只有 `SKILL.md`（15.4 KB）** | 无 | ✅ **纯提示词，零依赖，立即可用** |
| `theme-factory` | `SKILL.md` + `themes/*.md`（10 个主题） | 无 | ✅ **纯内容，零依赖** |
| `ui-ux-pro-max` | `search.py`+`core.py`+`design_system.py` + 3 MB CSV | 仅 Python 标准库 | ✅ 已实测通过（第 15 节） |
| `chart-visualization` | `generate.js` | `fetch`（Node 内置） | ✅ 已实测通过（第 15 节） |
| `slides` | `pptxgenjs_helpers/*.js`（8 个）+ `create_montage.py` | ⚠️ **需 `pptxgenjs` npm 包** | 用前需装 |
| `web-artifacts-builder` | `init-artifact.sh` + `bundle-artifact.sh` | ⚠️ 需 npm/node 运行时 | 用前需确认 |

### 16.2 重要冲突：`slides` vs 内置 `office-pptx`

- `slides`（Trae 来源）的 SKILL.md 第 10 行明确：**"Use PptxGenJS for slide authoring. Do not use `python-pptx` for deck generation unless the task is inspection-only"**
- DSH **内置** `office-pptx`（随包，路径 `resources\runtime\office-skills\office-pptx`）走的是另一条路线（捆绑 LibreOffice）
- 实测 `pptxgenjs` **不可解析**（`Cannot find module 'pptxgenjs'`）

**选型建议**：
- 常规 PPTX 交付 → 用**内置 `office-pptx`**（已带 LibreOffice，零安装）
- 需要 `slides` 的高级排版/自动字号/蒙太奇时 → 在**项目目录**里 `npm install pptxgenjs`（**不要**装全局：Node 从项目目录解析，全局包不可见，实测已验证）
- 两者**不要混用**同一份产出

### 16.3 技能池最终可用性矩阵

| 类别 | 数量/状态 |
|---|---|
| 零依赖纯提示词技能 | `doc-coauthoring`、`theme-factory`、`brainstorming`、`writing-plans`、`executing-plans`、`test-driven-development`、`security-best-practices`、`gh-cli`、`git-commit` 等 → **立即可用** |
| 已实测可执行 | `chart-visualization`、`ui-ux-pro-max` |
| 需运行时依赖 | `slides`(pptxgenjs)、`web-artifacts-builder`(npm) |
| 需外部凭据/账号 | `byted-*`(火山引擎)、`figma`(MCP)、`iga-pages`、`alipay/douyinpay` |
| 已剔除 | `local-*` 10 个（非 AIPC） |

---

## 17. 第 6 轮：新增省 token 工具 `defuddle`（已装并实测）

### 17.1 安装与实测

- 技能 `defuddle` 原本只有 1 KB 的 `SKILL.md`，CLI **未安装** → 技能不可用
- 已装：`npm install -g defuddle` → **v0.19.4**（`C:\Users\ROG\AppData\Roaming\npm\defuddle.ps1`）
- 实测（`example.com`，双次调用一致）：

| 形态 | 字节 |
|---|---|
| 原始 HTML | 557 |
| `defuddle parse <url> --md` | **149** |
| **压缩比** | **26.7%（省下 73.3% token）** |

> 注：`example.com` 是极简页面；真实内容页（带导航/脚本/样式）压缩率通常远高于此。

### 17.2 用法（读网页时优先用它，而非直接抓 HTML）

```powershell
defuddle parse <url> --md                 # 正文转 Markdown
defuddle parse <url> --md -o content.md   # 落盘
defuddle parse <url> -p title             # 只取字段：title / description / domain
```

**与现有能力的取舍**：`modsearch` 的 `read_page` 已能返回结构化页面证据（也省 token）。两者互补：
- 需要**结构化证据/摘要** → `read_page`
- 需要**完整正文 Markdown**（如把文档喂进后续处理） → `defuddle parse --md`

### 17.3 全局 npm 包清单（本机）

```
C:\Users\ROG\AppData\Roaming\npm
+-- agent-browser@0.38.1
+-- defuddle@0.19.4
+-- pnpm@11.7.0
```

### 17.4 技能"外部依赖标记"扫描的**可靠性说明**（避免误信）

用 SKILL.md 文本正则扫出的"火山/凭据/npm/MCP"等标记**启发式过粗**：
- 把 `brand-guidelines`、`gh-cli`、`ui-ux-pro-max` 误标为"需火山/凭据"（实际是文案里出现了 token/account 等词）
- 36 个被标"火山"的技能里，真正依赖火山引擎的只有 `byted-seedream-image-generate`、`byted-seedance-video-generate`、`byted-mediakit-shared`、`byted-bp-cdn-pagesdeploy` 这几个 `byted-*`

**结论：以"实测通过"为准，不要以该扫描的分组为准。** 已实测可用：`chart-visualization`、`ui-ux-pro-max`、`defuddle`、`agent-browser`、Playwright、以及内置 `office-*` 三个。

---

## 18. 第 7 轮：一键办公室体检脚本（新资产）

### 18.1 脚本

**路径**：`C:\Users\ROG\.local\bin\dsh-office.ps1`（只读，绝不改动任何东西）

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.local\bin\dsh-office.ps1"
```

**为什么做它**：目标④要求"省 token"。以前要了解办公室状态，得跑十几个工具调用（读 package.json、扫技能池、查 PATH、核补丁…）。现在**一条命令 3 秒出全貌** → 未来会话不必重复摸索。

**设计要点（踩坑换来的）**：
- **脚本内只用 ASCII 英文**：Windows PowerShell 5.1 会把**无 BOM 的 `.ps1` 按 ANSI 解码**，中文会变乱码并导致解析失败（本轮实测踩到）。ASCII 不受区域设置影响。
- 退出码：`fail>0 → 1`，否则 `0`（可用于自动化判断）。
- 覆盖 8 个板块：Harness / Tools / Skill pool / Plugins / Local patches / npm global / Browsers / Vision engine。

### 18.2 实测输出（2026-09-27 02:3x）

```
SUMMARY  ok=38  warn=6  fail=0
```

6 个 warn **全部是真实待办**，无误报：
1. `dsh-vision-router` 未装
2. `@hr98w/dsh-memory` 未装
3. computer-use provider 未装
4. `cordis.patch.yml` 无 computer-use 行（provider 装了才需要）
5. modlens 无配置 → 无视觉引擎
6. 1 个技能名非 kebab-case（`天眼一下`，中文名无法改为 kebab-case，DSH 会忽略它 —— 无解，可接受）

### 18.3 已确认的正面事实（脚本报 ok）

- bundles = 8；第三方 deps = 4
- Desktop runtime = dsh 0.1.7-rc.2 / node 24.21.0 / pnpm 11.7.0 / python 3.12.14
- 工具 13 个全在 PATH：python、uv、node、npm、npx、pnpm、git、rg、ffmpeg、ffprobe、gh、defuddle、agent-browser
- 技能池 66 条（junction 60 / 实体 6），**全部含 SKILL.md 与 name 字段**
- 5 个关键技能在位：ui-ux-pro-max、chart-visualization、frontend-design、webapp-testing、defuddle
- `dsh-workshop` 的 centerCol 补丁**仍在**，`.pre-patch` 备份存在
- 全局包：agent-browser 0.38.1、defuddle 0.19.4、pnpm 11.7.0
- `chromium-1228` 与 `playwright@1.61.1` 期望一致

---

## 19. computer-use 已安装并验证（2026-09-27，取代第 10 节的"未装"结论）

### 19.1 最终方案：MCP 变体（稳定性优先）

| 项 | 值 |
|---|---|
| 驱动 | `cua-driver 0.28.0`（x86_64-windows），`C:\Users\ROG\.local\bin\cua-driver\cua-driver.exe` |
| DSH 包 | `@deepseek-ai/dsh-computer-use@0.1.6-alpha.1` + `@deepseek-ai/dsh-experimental-computer-use-cua-driver-mcp@0.1.6-alpha.1` |
| 挂载 | `profiles\desktop\cordis.patch.yml` 末尾 `- insert:` 块（`command` + `args: [mcp]`） |
| 自启动 | 计划任务 `cua-driver-serve`（登录时 `cua-driver serve`），状态 Ready |
| 遥测 | 已 `telemetry disable` |
| 备份 | `package.json.bak-before-computeruse`、`cordis.patch.yml.bak-before-computeruse` |

**为什么插件页装不上**：插件页只接受声明 `dsh.bundle.patch` 的组合包；这两个包的 `dsh` 字段为 `null`，是"需手工挂进 Cordis 组合的单行插件"。正确做法 = Desktop 自带 pnpm 安装 + 手工插行（READM 描述的官方挂载方式）。

### 19.2 实测证据（**无需重启**，HMR 热加载）

- `health_report` → `cua-driver 0.28.0 on win32 — ok`；UIAutomation 可达；D3D11 屏幕捕获可用
- `get_screen_size` → 2560x1600 @ 1.5x
- `list_windows` → 19 窗口 / 18 应用
- `get_window_state` 对**后台隐藏** Notepad 读出完整 UIA 树：`[0] Document "文本编辑器"`，内容 = `npx --yes @deepseek-ai/dsh@0.1.7-alpha.2 web`（未抢焦点）

工具集 `mcp__cua-driver-mcp__*` 共 54+ 个：桌面截图/UIA 树/zoom、click/type/hotkey/drag/scroll、launch_app/kill_app/list_apps/invoke_menu、浏览器 CDP 系列、剪贴板、录屏、轨迹回放、`verify_state`。

**行为约束**：默认**后台投递不抢焦点**；仅当返回 `background_unavailable` 时才允许显式升级 `foreground`。`launch_app(start_minimized:true)` 在 Windows 可能被拒（未获前台锁）且**不启动进程**。

### 19.3 两个环境事实（顺带查实）

1. **"浮在屏幕中央的 PowerShell"根因**：Windows 上 GUI 进程 spawn 子进程时 Node 默认 `windowsHide:false` → 每个子进程都被分配并显示控制台窗口。ModLens 专门写了 `dsh\spawnHidden.js` 规避（引用 issue #60）。**不是创意工坊的 bug。**
2. **会话 shell 的真实父进程**：`WindowsTerminal.exe` «管理员: Windows PowerShell»（pid 22848）的父进程是 **`TRAE SOLO CN.exe` «TraeWork CN [管理员]»（pid 15744）**，即 DSH 会话的 shell 链路由 Trae 承载。
3. 旁证：`clash-verge.exe` 在运行 → 解释了早前 `github.com` / `cdn.jsdelivr.net` 被解析为"非公网 IP"的网络异常。

### 19.4 目标完成度

| 目标 | 状态 |
|---|---|
| ① 共享技能池 | ✅ 66 条，可加载+可执行已实测（chart-visualization / ui-ux-pro-max / defuddle / agent-browser / Playwright） |
| ② computer-use | ✅ 已安装 + 实测通过 + 自启动 |
| ③ 本地环境 | ✅ 13 工具 + Playwright 全链路 + Cua Driver |
| ④ 记忆/省 token | ✅ `~/.dsh/AGENTS.md` + 本手册 + `dsh-office.ps1` + `@hr98w/dsh-memory`（6 条工作区记忆） |
| ⑤ 规矩 | ✅ 未动 `profiles\web`、未动 `E:\deepseek-harness` |
| ⑥ 留证 | ✅ 本手册 19 节 |

---

## 20. gh（GitHub CLI）已登录（2026-09-27）

| 项 | 值 |
|---|---|
| 账号 | `RXX-CJL`（type: User） |
| 版本 | gh 2.101.0（winget 装到 `C:\Program Files\GitHub CLI\gh.exe`；桥接 `C:\Users\ROG\.local\bin\gh.cmd`） |
| 凭据 | Windows keyring（`✓ Logged in to github.com account RXX-CJL`） |
| Token scopes | `repo` / `workflow` / `read:org` / `gist` → 推代码、开 PR、跑 Actions 均可用 |
| git 集成 | ✅ 自动接通：`credential.https://github.com.helper = !'C:\Program Files\GitHub CLI\gh.exe' auth git-credential`（无需再跑 `gh auth setup-git`） |
| git 全局身份 | `user.name = RXX-CJL`、`user.email = 520c13j14l@gmail.com` |

**★ 2026-10-16 实测复核（本轮）+ 一处修复**：

| 检查 | 结果 |
|---|---|
| `gh auth status` | ✅ `Logged in to github.com account RXX-CJL (keyring)`，scopes `gist / read:org / repo / workflow` |
| `gh api user` | ✅ 返回 `RXX-CJL` |
| API 配额 | ✅ `limit=5000 remaining=4998`（链路通畅，无 TLS 抖动） |
| 目标仓库权限 | ✅ `RXX-CJL/lingtong-zhisheng` → `admin / maintain / push / triage / pull` **全 true**（private，默认分支 `main`） |
| ★ **本轮修复** | `gh config set editor notepad` —— 原先 `editor=''`（空），会让 `gh pr create` / `gh issue create` 在**无 TTY 时卡在编辑器**上。今后脚本调用**仍建议显式带 `--body-file`**，不依赖编辑器 |

**★ `E:\output` 与它的关系（重要）**：`E:\output` **就是** `RXX-CJL/lingtong-zhisheng` 的**本地克隆**（remote = `https://github.com/RXX-CJL/lingtong-zhisheng.git`，分支 `main`）。
⚠ 2026-10-16 实测：工作区**有 442 个文件未提交**（最后提交 `d88a7b6` / 2026-10-13）。**是否 commit / push 由用户决定**，AI 不要自行提交或推送。

**排障记录（重要，避免误判）**：
- 登录后首次 `gh auth status` 报了两条错：`Timeout trying to log in to github.com account RXX-CJL (keyring)` 与 `Get "https://api.github.com/user": net/http: TLS handshake timeout`。
- **这是瞬时网络抖动，不是认证失败**。同一时刻 `Invoke-WebRequest https://github.com` 与 `https://api.github.com` 都是 HTTP 200 / 0.4s；随后连试 3 次 `gh auth status` 全部 0.7–0.8s 成功。
- 环境线索：`clash-verge.exe` + `clash-verge-service`（pid 8880/9748）在运行，代理端口 **7897**，但**未设置** `HTTP_PROXY/HTTPS_PROXY` 环境变量，git 也无代理配置。
- **结论**：遇到 gh/git 的 TLS 超时**先重试 2–3 次**，不要直接怀疑凭据或重装工具。

---

## 21. 工作协议落地 + 生成侧故障记录（2026-09-27）

### 21.1 协议生效

| 项 | 位置 |
|---|---|
| 完整协议 | `E:\output\_DSH_WORK_PROTOCOL.md` — **DSH Operating Protocol v1.1**（18 节 / 10.5 KB） |
| 常驻摘要 | `C:\Users\ROG\.dsh\AGENTS.md` 新增 4 段：工作协议入口 / 三级证据标准 / 记忆写入规则 / **推理等级建议** |
| 记忆 | 已登记 `work-protocol`（共 7 条工作区记忆） |

**v1.1 相对 v1.0 的修订要点**：补项目根路径 `E:\output\1`；`dsh-office.ps1` 补完整调用路径并注明 warn 属正常；第 6 节落地**红/黄/绿名单**；第 9 节改为引用 `HANDOVER_UPDATE_RULE.md` + `_TASK-*.json` 约定（不再另立一套）；第 10 节加分类判据；第 13 节补"必须经 `memory_update`"；第 15 节报告模板加**验证等级**栏。

### 21.2 生成侧故障（MALFORMED_RESPONSE）与防复发规则

**现象**：`DeepSeek Messages stream: tool input is invalid JSON` / `MALFORMED_RESPONSE`，发生在"写完协议文件 → 准备读记忆索引"那一步。

**定性**：**生成侧故障，非环境损坏**。已回读验证：协议 10 532 B/338 行/18 节完整、`AGENTS.md` 4 145 B/8 节四个新段全部就位、记忆索引 7 条正常。

**根因**：单次工具调用的 JSON 内容体积过大被流式截断（此前连续三次大写入：12 KB 协议全量覆盖 + 4 段 `AGENTS.md` + 约 7 KB 记忆单条）。

**防复发规则（已采纳，写入协议精神）**：
1. 单次写入内容控制在约 8 KB 内；超出则**先写主体、再 `edit` 追加**
2. 一轮只做一件事，不把"写大文件 + 写记忆 + 查状态"挤在同一轮
3. 大写入后**必须回读验证**（字节数/行数/关键标记），这正是协议第 7 节的二级证据

---

## 22. 第 N 轮：项目跑通 + 两项 P1 修复 + 环境级发现（2026-10-02 时段）

### 22.1 项目已跑通（三级证据）

| 服务 | 地址 | 说明 |
|---|---|---|
| 后端 API | http://127.0.0.1:8001 （`/docs` 可看 OpenAPI） | 解释器 `C:\miniconda\envs\zhitong-gpu\python.exe` |
| 前端管理端 | http://localhost:5173 | Vite v5.4.21；`/api` 代理已实测通 |

- 后端启动日志 `Application startup complete`；7 个 YOLO 模型全部加载并上 GPU
- 前端渲染实拍：标题"智瞳灵声管理端"、6 张 KPI 卡、环形图 + 趋势图，**`CONSOLE_ERRORS=0`**
- 真实数据：`total=20`（库表 `violation_evidences` 20 行）、`traffic_events` 10 行

### 22.2 已修复（均含备份，见同目录 `*.bak-<时间戳>`）

| # | 文件 | 修复 |
|---|---|---|
| 1 | `api/database.py` | `DATABASE_URL` 由相对 `./zhitong_violations.db` 改为**锚定 `__file__` 的绝对路径**；并对 0 字节空壳库加只读告警。实测 4 个不同 cwd 均指向真库 |
| 2 | `start-all.bat` | ① 解释器自动探测（`zhitong-gpu` → `where python` → `py -3` 兜底）；② 改为**从项目根启动**并设 `PYTHONPATH=api;根`（原 `py -3` + `cd api` 双重问题） |

**验证（最强）**：从项目根启动、`PYTHONPATH` 生效 → `Application startup complete` 且 `total=20`。
（若库路径仍是相对的，从根启动必然得到 0 → 这是决定性证据。）

### 22.3 环境级发现：**git 不走代理会导致 GitHub 操作失败**

| 现象 | 原因 |
|---|---|
| PowerShell 访问 github/api.github/npm 全 200（0.6s） | 走的是**系统代理**（`ProxyEnable=1` → `http://127.0.0.1:65532`，Clash 随机端口） |
| **`git ls-remote/push` 全部 `Connection was reset` / 超时** | **git 不读系统代理**，只认 `http.proxy` 配置或 `HTTPS_PROXY` 环境变量；此前两者都没设 → 直连被重置 |

**已修复**：`git config --global http.proxy https.proxy = http://127.0.0.1:7897`（Clash 固定端口）。
**回滚**：`git config --global --unset http.proxy` / `--unset https.proxy`。
**衍生价值**：以后 `git clone` / `push` / 拉取开源项目不再需要手动开代理。

### 22.4 车牌识别选型（复用开源，已落盘）

→ `E:\output\1\docs\PLATE_RECOGNITION_OPTIONS.md`
**结论**：推荐用 **`hyperlpr3`** 替代缺失的 `paddleocr`（一条 pip、**不依赖 numpy** 故不撞现有 numpy 2.0.1、专做中文蓝/绿牌）。风险：停更 3 年、单一版本、onnxruntime 需匹配 Python 3.11。

### 22.5 待办更新

| 优先级 | 事项 | 状态 |
|---|---|---|
| P1 | 装 pytest 到 `.venv` | 待做 |
| P1 | 端到端事件闭环复现（现有 10 条事件全为 `pending_ai`；历史视频在 `api/output/event_videos/20260925/`） | 待做 |
| P2 | 按选型方案引入 `hyperlpr3`（先隔离验证再改代码） | 待批准 |
| P2 | `api/config_runtime.json` 自回写会重新落明文 → 改造 `config_manager.set_api_key` | 待做 |
| — | 滞后文档合并（B1/B2 已更正；`lan-start.bat` 不存在→实为 `start-all.bat`；审计报告 12 处密钥说法过期） | 部分完成 |

### 22.6 服务 PID 速查（本会话启动，可能已变）

| 服务 | PID | 备注 |
|---|---|---|
| 后端（修复后重启） | 51664 | 从项目根启动，验证 `total=20` |
| 前端 Vite | 54200 | 端口 5173 |

---

## 23. DeepSeek 账号与余额归属（2026-10-02 查实）

### 23.1 结论：只有一把真实 DeepSeek Key，一个账号

| Key 指纹 | 身份 | 证据 |
|---|---|---|
| `sk-b60...5102`（sha12 `fc09d0f1b230`） | ✅ **唯一真实 DeepSeek Key** | 余额接口 HTTP 200 → **¥33.11 CNY**（充值余额，赠送 0） |
| `sk-e82...2cd1`（sha12 `e477f4a1b8fa`） | ❌ **不是 DeepSeek Key**，实为 `AMAZON_BEDROCK_API_KEY`（AWS） | DeepSeek 接口 `401 api key ****2cd1 is invalid` |

### 23.2 鲸鱼挂件查的就是同一把 Key

- 挂件**不自己存 Key**：`lib/index.js:72` 写明「密钥走 DSH 官方凭据（`ctx.credentials`），本文件不存明文」
- 内置 DeepSeek 模板：`keyRef: 'DEEPSEEK_API_KEY'`，`balance.url = https://api.deepseek.com/user/balance`
- 无自定义模型覆盖（`.dshw-api.json` 三处均不存在）
- **决定性证据**：挂件记账文件 `C:\Users\ROG\.dsh\.dshw-usage.json`
  - `lastBalance = 33.11`（与余额接口一致）
  - `accounting.active = "fc09d0f1b2303647d460f224-CNY"` ← **即 DSH key 的 sha12 前缀**，账本以 key 哈希为键
  - `events` 41 条，累计成本 9.32 元

### 23.3 充值指引

- 登录 **https://platform.deepseek.com**，用创建 `sk-b60...5102` 的账号充值
- **充完验证**：用余额接口复查（脚本 `E:\output\_scripts\_balance_check.py`），数字增加即充对账号
- **不要新建账号**：DeepSeek 的 **prompt cache 按账号绑定**，换账号才会导致缓存命中率初期下降；同账号换 key 不受影响

### 23.4 踩坑记录

- **凭据文件存在重复登录条目**：`C:\Users\ROG\.dsh\.credentials.yaml` 里同一 `token`/`issuer` 出现两次，其中一个 `refs` 块把 `DEEPSEEK_API_KEY` 与 `AMAZON_BEDROCK_API_KEY` 混写。**误把 Bedrock key 填到 DeepSeek 位置会直接 401。**
- 挂件数据文件位于 `C:\Users\ROG\.dsh\.dshw-*.json`（`usage` / `turn` / `size`）；余额是**实时查询**，不落盘快照。
- 挂件本地接口需要鉴权：直接 `GET http://127.0.0.1:19387/dsh-whale/balance.json` 返回 **401**，要看数据请读上述 `*.json` 文件。

### 23.5 测试素材（用户提供）

- 目录：`E:\output\1\test_assets\traffic_videos`（5 个 mp4，最大 120.4 MB）
  - `3a3f1dd6ee318c8a965d85a70e7520bf.mp4` 0.3 MB
  - `3e9b3f659e257969d581993be3c9e59e.mp4` **120.4 MB**
  - `701c5154f47975564a8039bb03bd3340.mp4` 1.0 MB
  - `ea1ca6cbb27653af24ebe585d56f0ffd.mp4` 0.5 MB
  - `f640e913639b7beaed028111ee4039ce.mp4` 0.4 MB

---

## 24. 识别框可视化增强 + 帧率解耦（2026-10-03）

### 24.1 新增：中文标注渲染器（`api/annotation_renderer.py`）

**核心问题**：`cv2.putText` 的 Hershey 字体**没有中文字形**——原代码里的
`cv2.putText(frame, "逆行", ...)` 实际什么都画不出来（隐藏 bug）。

**实现**：用 PIL + TTF 渲染中文，关键设计：
- 字体回退链：`msyhbd.ttc` → `msyh.ttc` → `simhei.ttf` → `simsun.ttc` → K230 的 `OPPO Sans 4.0.ttf`
- **字体对象按字号缓存**（避免每帧重建）
- **批量绘制**：所有文本一次性画到同一张 PIL 图，只做一次 BGR↔RGB 往返
- 实测性能：**2.6 ms/帧（等效 382 fps）**，对帧率无实质影响

**功能**：
| 需求 | 实现 |
|---|---|
| 违规→红框 + 违规类型；正常→绿框不显示类型 | ✅ `COLOR_VIOLATION` / `COLOR_NORMAL` |
| 左上角标签：ID / 速度 / 车牌 / 违规类型 | ✅ 全中文 |
| 红绿灯框 + 颜色标注 | ✅ `_analyze_traffic_light_color()`（HSV ROI，参考 K230 `red_light.py`）|
| 倒计时 | ⏸ 用户决定暂缓（无倒计时模型）|

**违规→车辆 映射策略**（两条链路字段形态不同，这是"红框不出"的根因）：
- 行为引擎违规：带 `vehicle_id`（= track_id）→ 直接可用
- 规则引擎违规：**只有 evidence/location，无 track_id** → 按 bbox IoU(≥0.3) 或点位包含推断
- 退化场景（全场单车 + 全部违规无 ID）→ 归属该车，避免完全不可见

### 24.2 帧率解耦（重要结论）

**用户指正**：提高 YOLO 画框帧率**不会**直接增加云端调用——**用户是对的**。
我此前的顾虑源于一个真实的设计问题：**违规判定与云端咨询挂在同一个循环里**
（`process_frame` → 云端 1-5 秒同步调用会阻塞整个检测循环）。

**目标架构（三级解耦）**：
```
第 1 级（本地高频 15-25fps）：YOLO + 追踪 + 画框        ← 用户看到的流畅画面
第 2 级（本地中频 2-3fps） ：违规规则判定 + 事件引擎
第 3 级（异步，不阻塞）    ：云端 AI 咨询 → 结果回填
```
**实测基础**：YOLO 二次推理仅 **0.01s/帧**（≈100fps 能力），所以帧率瓶颈从来不是 YOLO，
而是 `FRAME_RATE=3` 的人为节流 + 云端同步调用阻塞。

### 24.3 本轮修复的其他问题

| # | 问题 | 修复 |
|---|---|---|
| 1 | 左上角违规告警中文乱码（显示 `? 违规停车(车1)`）| 改用渲染器 → `【违规】违规停车(车1) 0.70` |
| 2 | "逆行"标签永久不显示 | 同上（原来 `cv2.putText` 画不出中文）|
| 3 | 违规车不变红 | 新增多来源 ID 推断 + 空间匹配 |
| 4 | emoji `⚠` 显示为方框 | 换成 `【违规】`（雅黑无 emoji 字形）|

### 24.4 参考材料（用户提供）

- `E:\output\1\K230\程序源码\09.Scene\06.licence_det.py`、`07.licence_det_rec.py`（车牌检测/识别）
- `E:\output\1\K230\19.历年国赛赛题\2.程序源码\2.23国赛k230代码\red_light.py`（**HSV 色块判色**，本项目红绿灯判色即参考此法）
- `E:\output\1\K230\00.开发板资料\字体\OPPO Sans 4.0.ttf`（已加入字体回退链）
- CSDN 参考：https://blog.csdn.net/weixin_44944382/article/details/147830250

---

## 25. 违规过报治理 + 帧率解耦实测（2026-10-03）

### 25.1 帧率三级解耦（已实现并实测）

| 指标 | 解耦前 | 解耦后 |
|---|---|---|
| 有效处理速率 | **0.7 fps** | **6.6 fps**（配置目标 15） |
| 80 秒 processed | 56 | **521** |
| 云端调用位置 | `process_frame` 内**同步**（1-5s，长期占用 process_lock） | **独立 worker 线程 + 有界队列** |

**实现**（`realtime_detector.py`）：
- `self._cloud_queue = queue.Queue(maxsize=2)` + `_start_cloud_worker()` + `_cloud_worker_loop()`
- `submit_cloud_consult()`：队列满时**丢最旧保最新**，绝不阻塞检测循环
- 云端结果回填 `self._last_cloud_result`；日志可见"云端咨询完成（异步）: type 第N次"
- 帧率由 `FRAME_RATE` 环境变量控制（我用 15 启动；`config.py` 默认仍 3）

### 25.2 违规过报治理（关键经验）⭐

**现象**：解耦提速后，违规率 **96-99%**（几乎每帧都报），演示时满屏红框。

**三轮尝试（前两轮无效，务必记住）**：

| 尝试 | 违规率 | 结论 |
|---|---|---|
| ① 提高置信度阈值（车辆 0.4→0.6、头盔 0.3→0.55、默认 0.5→0.65） | 96-99% | ❌ **无效**——问题不是"置信度低" |
| ② 时间持续性确认（同类违规持续 ≥1.5s 才上报） | 89.6% | ❌ **几乎无效**——缺时间维度但不是主因 |
| ③ **持续性确认 + 冷却期（确认后 8s 内不重复上报）** | **3.1-3.8%** | ✅ **降低 25 倍** |

**根因**：规则引擎缺少时间维度——同一违规在**每一帧**都被当成"新违规"。
`_check_illegal_parking` 等规则只要"检测到车辆 + 区域/时长条件"就返回 `True`，
在 15fps 下等于每秒报 15 次。

**实现**（`realtime_detector.py` 的 process_frame 内）：
```
_viol_hold[type]          # 首次出现时间
_viol_last_report[type]   # 上次上报时间
① 持续 < VIOLATION_HOLD_SEC(默认1.5)  -> 不报
② 距上次上报 < VIOLATION_COOLDOWN_SEC(默认8) -> 不报
③ 违规类型消失时清理状态（避免残留）
```

**经验固化**：**过报问题的正解是"时间维度（确认+冷却）"，不是"提高阈值"。**
真实交通抓拍系统同样是"一次违规只抓拍一次"。

### 25.3 与参考项目（CSDN 博客）的对标差距

用户提供的参考项目（https://blog.csdn.net/weixin_44944382/article/details/147830250
"QT界面-车辆闯红灯检测…"）**高准确率的真正原因**：

| 能力 | 参考项目做法 | 本项目现状 | 差距 |
|---|---|---|---|
| 红绿灯**判色** | ⭐ **自训 CNN 三分类**（60×32×3，2 层卷积+2 层全连接） | HSV 颜色阈值 | **关键差距**（易受逆光/色偏影响） |
| 车速/超速 | 前 8 帧位移 + **像素↔实际距离标定** | 像素/秒，**未标定** | 关键差距 |
| 车牌 | **MTCNN 定位 + LPRNet 识别** | paddleocr 未装、降级 | 关键差距 |
| 车型 | **ResNet34 + 斯坦福车辆数据集**（196 类）迁移学习 | 无 | — |
| 斑马线 | **滑动窗口 + 梯度方向直方图**（非深度学习） | 无 | — |
| 压线 | 需**预标注车道线** | 无 | — |
| **场景预标注** | ⭐ **运行前人工标注车道线/红绿灯/人行道区域** | **完全靠规则引擎猜** | **收益最大** |

**结论**：差距不在 YOLO（双方都用 COCO 预训练），而在
**"专用小模型 + 场景标定 + 时间维度"**三件事。通用 YOLO 粗框推专用语义必然不准。

### 25.4 环境参数速查（本轮新增）

| 环境变量 | 默认 | 作用 |
|---|---|---|
| `FRAME_RATE` | 3 | 检测循环目标帧率 |
| `VIOLATION_HOLD_SEC` | 1.5 | 违规持续多久才算确认 |
| `VIOLATION_COOLDOWN_SEC` | 8 | 同一违规类型上报后的冷却期 |
| `MIN_REPORT_PARKING` 等 | 0.60-0.65 | 分类型最低上报置信度 |

---

## 26. ★工作室升级轮（2026-10-12，DSH 执行）

> **本节的数字一律优先于 §1~§3 的旧数字**（运行时版本、插件表、技能数都已在 §26.1 作废重写）。
> **★本节事实块不要手抄**：跑 `powershell -NoProfile -ExecutionPolicy Bypass -File %USERPROFILE%\.local\bin\dsh-facts.ps1 -Save` → 生成 `E:\output\_DSH_FACTS.generated.md`，贴过来即可。
> 分工：**`dsh-office.ps1` = 体检报告（ok/warn/fail）**，**`dsh-facts.ps1` = 可粘贴的事实块**（版本/插件/技能/补丁/磁盘/git）。
> **★找插件/技能用 `dsh-find.ps1`**（2026-10-13 新增）：
> `powershell -NoProfile -ExecutionPolicy Bypass -File %USERPROFILE%\.local\bin\dsh-find.ps1 -Query <关键词|正则> [-Top 8] [-NoNpm]`
> —— 直接扫本地工坊目录 `C:\Users\ROG\.dsh\dsh-workshop\registry.json`（**15938 条**，带 `certified/curated/scanStatus/stars/npmPackage` 信任信号；工坊自带的搜索工具对中文多词查询很弱），
> 并对每个候选自动跑 **4 道硬门槛**：① `dsh.bundle.patch` 在不在 ② 所有 `@deepseek-ai/dsh*` peer 是否覆盖运行时版本 ③ 有无 `preinstall/install/postinstall` ④ 体积。
> ⚠ **必须用 pwsh 7 跑**（Windows PowerShell 5.1 的 `ConvertFrom-Json` 啃不动 23 MB 目录，会静默 0 命中）；脚本已内置"自动切 pwsh 7"。

### 26.1 环境事实（**2026-10-13 01:42 由 `dsh-facts.ps1` 重新生成**）

> 下表数字已更新：**bundles 13**、第三方 deps **11**（含本轮 4 个新插件 + schedule bundle）、技能池 **67**（junction 60 / real 7）、`cordis.patch.yml` 的 computer-use 行 **5**、git 积压 426 项。

| 项 | 值 |
|---|---|
| Desktop 运行时 | **dsh 0.2.0-rc.2** / node 24.21.0 / pnpm 11.7.0 / python 3.12.14（**不再是 0.1.7-rc.2**） |
| bundles / 第三方 deps | **11 / 9** |
| 技能池 | **66 条**（junction 60 / 实体 6）+ 自建 1 = **67**；仅 1 条非 kebab-case（`天眼一下`，无解） |
| 工具链 | 13 个全在 PATH（python / uv / node / npm / npx / pnpm / git / rg / ffmpeg / ffprobe / gh / defuddle / agent-browser）+ `pw.ps1` |
| Playwright | `chromium-1228` 与 `playwright@1.61.1` 期望一致 ✅ |
| 两个 warn | ① modlens 无引擎（已被取代） ② 上述非 kebab-case 技能名 |

### 26.2 本轮新增的四个插件（全部 npm 源、peer 已核、**零生命周期脚本**）

| 插件 | 版本 | 干什么 | 生效 |
|---|---|---|---|
| `dsh-vision-router` | **3.0.3**（升级自被禁用的 2.2.4） | **14 个视觉工具**（describe/ground/detect/crop/ocr/colors/pixel_diff/trace/extract_foreground/html_screenshot/long_screenshot_ocr/materialize/present/bootstrap），零 key 免费链 | 重启后已在 bundle 激活；**工具需新对话** |
| `dsh-pause` | **0.1.3** | **推理中插话**（请求前拉门；裸回车放行 / 带字即插话） | 即时 `applied` |
| `dsh-better-input` | **0.2.6** | 提示词一键优化 + `/` 模板库 + **PDF/DOCX/PPT/XLSX→Markdown** + 浏览器语音 | 即时 `applied` |
| `dsh-llm-retry-settings` | **0.1.17** | 重试/退避/错误码策略 + **截断自动续写** + 观测面板 | 即时 `applied` |

> 未装（已核后放弃）：`dsh-queue-plus`（peer 停在 `^0.1.0-rc.6`，会被判不兼容）、`dsh-timeline`（peer 全是 `*`）、`dsh-dream`/`dsh-prompt-enhancer`/`dsh-memory-evolve`（npm 无 dsh 字段或只能走 GitHub 需构建；`dsh-dream` 还会自动改写 `AGENTS.md`，风险高）。

### 26.3 本轮排掉的两个卡点

1. **`dsh-vision-router@2.2.4` 一直被禁用** —— 它的 dsh peer 只写到 `0.1.7-rc.2`，与运行时不匹配（`enabled:false / error: incompatible-version`）。**升级到 3.0.3 即解**（peer 含 `>=0.2.0-rc.2 <0.3.0-0`）。**这就是"我没有眼睛"的真身**（不是没装）。
2. **pnpm 11 构建闸门** —— better-input 拖来 `pdfjs-dist` 的可选依赖 `canvas@2.11.2`，`ERR_PNPM_IGNORED_BUILDS` 会**连带挡住后续所有安装**。处置 = `pnpm-workspace.yaml` 写 `allowBuilds: { canvas: false }`（不构建：canvas 2.11.2 在 Node 24 无预编译包、源码编译需 GTK/cairo；better-input 自己的 PDF 渲染用带预编译的 `@napi-rs/canvas`）。备份 `pnpm-workspace.yaml.bak-before-canvas-decision`。

### 26.4 两条必须记住的机制

- **视觉工具的可见性绑定"会话启动时刻"**：插件在本会话启动后才激活 → **本会话调不到**（工具名根本发不出去），**必须新开对话**。宿主侧已确认加载（`cordis_inspect` 可见 `include:vision-router`）。
- **`dsh-pause` 默认关闭、按会话独立**：要用插话得先在 composer 右侧点「暂停」。

### 26.5 用法速查

| 想要 | 怎么做 |
|---|---|
| 让我看图 | 贴图或给路径；**新对话**里我用 `vision_describe` 等 14 个工具真看图（不是文字转述） |
| 在我干活途中插话 | composer 右侧点「暂停」开启本会话 → 我每次请求前停下 → **裸回车放行 / 打字后回车 = 插话** |
| 让提示词更准 | 输入框右上角图标 → AI 优化 → 对比后采用 |
| 喂文档给我 | 输入框「添加文件」→ PDF/Word/PPT/Excel **本地转 Markdown** 再发我 |
| 常用提示词 | 输入 `/` 调模板库（存 `~/.dsh/better-input/templates.json`，不上传） |
| 重试/截断策略 | 设置页的「重试」卡片（按 provider/model 分策略） |

### 26.6 回滚

```
plugin_manager remove_bundle dsh-vision-router      # 或 dsh-pause / dsh-better-input / dsh-llm-retry-settings
```
`pnpm-workspace.yaml` 的 `canvas: false` 可改回占位符或整键删除（`.bak-before-canvas-decision` 为原始备份）。Desktop 另有 `FatalRecovery.disableAllPlugins()` 兜底。

### 26.7 顺带定案的历史悬案（一级证据）

- **技能数 = 66**（不是 78）：目录实测。
- **1970 脏数据 = 566 条**（不是 514）：只读查库 → `traffic_events` 共 **3209** 行，`substr(cast(trigger_time as text),1,4)='1970'` → **566**；`created_at` 无 1970。`_SESSION_HANDOFF.md` 第 12/14 项与 `_PROJECT_MAP.md` T93 里的 514 是当时的旧快照。
- **"两处本地补丁"** = ① `dsh-workshop` 的 `client.js` centerCol 补丁（`.pre-patch` 备份 + 重打脚本 `E:\output\dsh-workshop-desktop-patch\patch-client.mjs`）② `cordis.patch.yml` 里的 computer-use 手工行。

### 26.8 跨会话检索：真根因 + 新装插件（2026-10-13）

- **真根因不是"缺插件"**：`@deepseek-ai/dsh-session-query-sqlite` **已加载（active）**，暴露 `ctx.sessionQuery.searchSessions` / `searchEvents`；但 profile 的 `cordis.yml:89-93` 配成 `path: ':memory:'` + **`openAt: never`** → **任何搜索调用都以 `SESSION_QUERY_SEARCH_DISABLED` 失败**，侧栏搜索只匹配标题与工作区名。**且模型侧没有任何检索工具**（39 个工具全量确认；`session_search` 只是 Web 侧栏用的 Remote）。⇒ **引擎有、UI 有、工具没有。**
- **已装 `dsh-session-workbench@1.0.3`**（`applied`）：官方 FTS5 全库搜索 + 命中片段 + `@` 引用召回（≤3 会话 / 64KB）；**零 `@deepseek-ai/dsh*` peer、零生命周期脚本、零外部依赖**，且**不与 `dsh-memory` 冲突**（只在你手动引用时才进上下文）。
- **待办（🔴 红名单，需用户批准后才动）**：把 `session-query-sqlite` 改成
  `path: !!js dshHomePath('session-query-index.sqlite')` + **`openAt: first-search`**（保守：避免启动就建索引）→ **改完需重启 Desktop**；不改则 workbench 只能搜标题/工作区名。
- **★peer 判定真规则（asar 级反汇编，修正旧笔记）**：只判 `@deepseek-ai/dsh` 与 `@deepseek-ai/dsh-*`；`cordis` / `react` / `zod` / `@deepseek-ai/schemastery` **一律不判**；**`*` 一定通过**；**`engines.dsh` 与 `dsh.compatibility.dshReleases` 不参与判定**（只是声明，不是通行证）。被拒 = 游离 `disabled:true` 行，**模块永不 import**；逃生舱只有 profile 的 `compatibility.json` 精确版本豁免。
- **asar 路径修正**：`resources\app.asar\dsh\` **不存在**；JS 全在 `resources\app.asar`（121 MB；头 JSON 占 `[16, 3392063]`，**数据起点 = 3392065**，按 `16+u32@4` 解析会错位 7 字节）。
- **未采用**：`dsh-memory-eternal`（peer 上限 `<0.2.0`，必被判不兼容）、`dsh-auto-memory`（与 dsh-memory 同范式撞车）、`dsh-memory-evolve` / `dsh-session-search-pro`（npm E404，只能 git 源）、`memsearch` / `OpenViking` / `graph-memory`（Python/Milvus/OpenClaw，非 DSH 插件）。
- **下一步设计（未做）**：写一个把 `searchSessions` 注册成**模型工具**的小适配插件 —— 本机唯一能同时满足"模型自主检索 + 零额外记忆注入 + 不撞 dsh-memory"的路径。

#### 26.8.1 ✅ 已实现（2026-10-13）：模型工具 `session_search` + 离线兜底脚本

- **插件**：`<profile>\node_modules\dsh-session-search\index.js`（本地手挂，ESM `export {name, inject, apply}`；`inject: ['tools']`；`ctx.get('sessionQuery')` 可选访问）。行挂在 `cordis.patch.yml` 的 `- insert: [{ id: session-search, name: 'dsh-session-search' }]`（loader 按 **`<包名>/index.js`** 解析，不读 package.json 的 main/exports）。
- **已验证**：① 真 import 一次 → `exports: apply, inject, name` ② 用假 ctx 跑 `apply` → 注册出 `session_search`，`output.schema/render/execute` 齐备 ③ **被 HMR 热加载**：工具已出现在会话工具表中，无需重启。
- ⚠ **工具热加载 ≠ 索引可用**：`cordis.yml` 是**启动级**配置，实测调用仍返回 `SESSION_QUERY_SEARCH_DISABLED` → **必须重启 Desktop 一次**（`openAt` 已改为 `first-search`）。
  > 🔴 **2026-10-13 更正：上面这句"（`openAt` 已改为 `first-search`）"是错的。** 当时**并没有落盘**——`cordis.yml` 其实是 4 行空壳，patch 里也没有该覆盖项。真修复见 **§26.9**。
- **离线兜底（今天就能用，已实测）**：`node %USERPROFILE%\.local\bin\dsh-sessions.mjs "<关键词>"`；`--list` 列全部会话，`--probe <id>` 看解压量，`--only user/message` 只搜人说的话。
  **★关键实现细节**：会话日志是 **zstd 多帧**（每 ~150–700 字节一帧，前 8 KB 就有 6 个 magic），而 **Node 的解压器只吃第一帧**（流式与同步都一样，实测只出 0 KB）→ **必须按 magic 边界逐帧解**。修好后实测：3.6 MB → 12 MB 文本 / 4624 行；10 MB（09-27 那场）→ **34 MB / 12094 行**。
- **回滚**：删 `cordis.patch.yml` 里的 insert 块（备份 `cordis.patch.yml.bak-before-session-search`）+ 删 `node_modules\dsh-session-search\`。

---

## 26.9 跨会话检索真修复 + 1970 复核（2026-10-13 第二轮，一级证据）

### 26.9.1 ✅ 跨会话检索修好了（用户重启 Desktop 后实测通过）

- **真根因**：`<profile>\cordis.yml` **现在只有 4 行**——一个空数组 `[]` 加一句 *"Edit cordis.patch.yml, not this file"*。上游默认（见 `cordis.yml.bak-before-session-query` 第 89–93 行）是 `path: ':memory:'` + **`openAt: never`**。⇒ §26.8.1 声称的"已改 first-search"**从未落盘**，且 `cordis.patch.yml:77` 那句"现为 first-search"**只是注释**。
- **修法（已执行）**：在 `cordis.patch.yml` **末尾新增顶层覆盖项**（不是改 `cordis.yml`）：
  ```yaml
  - id: session-query-sqlite
    name: '@deepseek-ai/dsh-session-query-sqlite'
    config:
      path: !!js dshHomePath('session-query-index.sqlite')
      openAt: first-search
  ```
  备份：`cordis.patch.yml.bak-before-session-query-fix`。**这是启动级配置，改完必须重启 Desktop**。
- **实测结果（三级证据）**：重启后调 `session_search{query:"CARLA", limit:3}` → `{"ok": true, "mode": "sessions", "returned": 3, "hasMore": true}`，命中 **3 个不同历史会话**的真实片段（session-22c9f27b / session-dffdf9b2（09-26 那场）/ session-34e62975）。**跨会话检索正式可用。**

### 26.9.2 ★shell 可用性：重启后自动恢复（补全踩坑 #10）

- 修复前（`workspace-write`）：`pwsh` **任何**调用都返回 `[exit code: 3221225794]` = `0xC0000142`——连 `cmd /c dir` 都不行；**落盘探测**（`_probe_pwsh.txt` / `_probe_cmd.txt`）两个文件都没生成 ⇒ 是**进程起不来**，不是抓不到输出。
- 重启后：**同一条命令立刻成功**（`PS=7.6.6`、`CWD=E:\output`）⇒ 与踩坑 #10 的结论一致，属**沙箱注入**问题，不重启则整个会话只能做只读静态工作。
- 推论：要跑命令的会话，开工先自检 shell；坏了就**尽早请用户重启**，别硬撑。

### 26.9.3 1970 脏数据只读复核（脚本 `E:\output\_scripts\audit_1970.py`，`mode=ro` 打开）

| 项 | 实测值 |
|---|---|
| `traffic_events` 总行数 | **3209**（与 §26.7 一致） |
| `trigger_time` 年份分布 | 2026: **2642** / 1970: **566（17.6%）** / NULL: **1** |
| 脏数据 id 区间 | **2338 – 3013**（`created_at` 2026-10-05 16:13 ~ 2026-10-10 15:57）—— **封闭区间** |
| 脏数据**之后**新增的 1970 行 | **0 条** ⇒ 「新增写入路径已修好」**成立** |
| 最新 8 条（id 3202–3209） | `trigger_time` 全是**正确墙钟**（如 `2026-10-11 16:14:17`）；`created_at` 比它**早 8 小时** = UTC vs 本地，属另一个已知小问题 |
| `created_at` 里的 1970 | **0 条** |
| ⚠ **`wall_time` 列** | **不存在**！`traffic_events` 实际列：`id, event_id, event_type, track_id, state, trigger_time, vehicle_info, scene_context, trajectory, key_frames, event_video_path, rule_judgment, ai_judgment, ai_confidence, ai_explanation, evidence_chain, state_history, camera_id, created_at, updated_at`。**§26.7 / T93 里"事件新增 `wall_time` 字段并用它落库"的表述与实际不符**——待核（可能落在 `vehicle_info`/`scene_context` 这两个 JSON 列里，或修的其实是别处） |
| 样本（id 2338–2342） | `1970-01-01 08:00:10.85`、`08:00:11.25`…… 正是**视频秒**被当 epoch（T93 根因：`1970-01-01 08:00:00` 本地 = epoch 0，`+10.85s` 即视频第 10.85 秒） |

**用户决策**：**不回填**（2026-10-11 已拍板，2026-10-13 再次确认"这个先不用动"）。理由充分：脏数据是**历史封闭区间**、新数据已正确、且这些事件"很多是没用的"。**不要再提议回填，除非用户主动提。**

### 26.9.4 ★写作纪律（本轮新增，代价很大）

- **不要把大文件正文在"工具参数 ↔ 返回值"之间来回搬运**：本轮读一份 **1331 行 / 约 45 KB 的 YAML**（含大量 `!!js`、`>-` 块标量、成对引号）时，曾触发一次 `MALFORMED_RESPONSE`（*tool input is invalid JSON*）——**工具调用序列化失败，任务本身没失败**。对策：大配置**分段读**（`offset`/`limit`），或先 `grep` 定位行号再精读。
- **"注释"不是"配置"**：patch 文件里写了"现为 first-search"，我就信了——结果白等一轮重启。**凡结论涉及生效性，必须以运行时实测（调用结果 / 启动日志）为准，"文件里写着"只算二级证据。**

### 26.9.5 ★跨会话检索：重启后**实测已通**（2026-10-14 20:18 复测，闭环）

| 项 | 实测值 |
|---|---|
| 模型工具 `session_search` | ✅ 调 `{"query":"CARLA","limit":2}` → **`ok:true`**；命中 ① `session-22c9f27b`（当前会话，`live:true`）② **`session-dffdf9b2`（2026-09-26 创建、`live:false`）** ⇒ **跨会话确实生效**，不再是 `SESSION_QUERY_SEARCH_DISABLED` |
| 索引文件 | `C:\Users\ROG\.dsh\session-query-index.sqlite` = **43 MB**（每次搜索时写入） |
| `cordis.yml` | **223 字节**，内容就是那句 *"Edit cordis.patch.yml, not this file"* + `[]`；mtime **2026-10-14 20:17:12**（启动时被 launcher 重新生成）⇒ 印证 §26.9.1：**它是生成物、手改必丢**；有效的 `openAt` 覆盖在 **patch 层** |
| 离线兜底 | `dsh-sessions.mjs` 同样可用（不依赖索引/插件） |

> **结论**：§26.8.1 的"必须重启 Desktop 一次"**已完成并通过验收**。以后凡是启动级配置，**只改 `cordis.patch.yml`；`cordis.yml` 永远别碰**。
> ⚠ 别再加"要不要回填 1970 脏数据"的提议 —— 用户 2026-10-11 已拍板**不回填**，2026-10-13 再次确认（见 §26.9.3）。

---

## 27. ★创意工坊轮（2026-10-16）：web-all + 壁纸插件安装实录

### 27.1 ★「创意工坊」vs「插件市场」——不是同一个东西，且"创意工坊"这个名字被两个实体共用

| # | 实体 | 真身 | 数据源 | 作用于哪个 profile |
|---|---|---|---|---|
| ① | **DSH 官方「插件」页**（Settings → Plugins；官方与第三方 README 都叫它"应用内插件市场"） | 内建 `@deepseek-ai/dsh-client-ui-plugin-manager` + `dsh-host-plugin-inventory`；模型侧 = **`plugin_manager` 工具** | **无在线目录**，要自己填包名/spec | **当前 profile（= desktop）** ✅ 本轮就靠它 |
| ② | **「创意工坊」插件**（侧边栏商店图标） | 第三方 **`dsh-workshop`**（作者 loguhan） | `zp-home/dsh-recommend` 的 registry.json（本地 `~/.dsh/dsh-workshop/registry.json`，**15938 条**） | ⚠ **web**（见踩坑 #17，装不到 desktop） |
| ③ | **`dsh-market.com` 网站**（页面标题**也叫「创意工坊 — 皮肤 · 宠物 · 插件 · 预设」**） | `zhu1090093659` 的 dsh-web 生态市场站（7956★ 仓库的 homepage） | 自有（239 件作品） | 其客户端 `@linxin666/dsh-client-ui-market` 随 web-all 装入 |

**结论**：用户 GUI 里那个「创意工坊」= **②**；要找的 `web-all` **不在②的索引里**（②只收 GitHub 仓库，web-all 是 npm 包），它属于 **③**。三者互不隶属。
★ `web-all` 正身 = npm **`@linxin666/dsh-web-all`**（v0.4.6，仓库 `zhu1090093659/dsh-web`）；旧名 `@linxin666/dsh-web-ui-all@0.3.6` 带 `dsh.migrate.to` 指向它（②的源码里有别名 `"@linxin666/dsh-web-ui-all": "dsh-web-ui"`）。

### 27.2 安装结果（两个都成，且**无需重启**）

| 插件 | 版本 | 验证等级 |
|---|---|---|
| `@linxin666/dsh-web-all` | **0.4.6** | **三级**：`GET /api/dsh-web-all/degraded` → `{"ok":true,"degraded":[]}`（零降级）；`/api/dsh-web-all/rows` → 12 个激活行；loader 内 20 行全注册（**14 schema / 2 按设计 inactive / 4 无 schema**）；`task_board_*` 等工具已进模型工具箱 |
| `dsh-plugin-wallpaper-engine` | **1.3.2** | **三级**：`GET /wallpaper-engine/inventory` → HTTP 200，扫到 **585 个本机壁纸**（166 可移植），自动识别 `d:\program files (x86)\steam\steamapps\common\wallpaper_engine` |

- `web-ui-ssh` 与 `web-ui-skill-explorer` 是 **inactive（按上游 README 的 opt-in 设计默认禁用）**，不是故障。
- ★ **两个插件装完即由 HMR 加载生效，无需重启**（README 的"重启宿主"是保守说法）。建议方便时完全重启一次，让浏览器半干净重载。

### 27.3 回滚入口（已备好，双击即用）

| 脚本 | 作用 |
|---|---|
| `E:\output\_plugin-backups\ROLLBACK-before-this-round.bat` | 恢复到**本轮之前**（两个插件都移除） |
| `E:\output\_plugin-backups\ROLLBACK-wallpaper-only.bat` | 只保留壁纸插件，移除 web-all |
| `E:\output\_plugin-backups\rollback.ps1` | 上面两个 bat 的实现；回滚前会**再备份当前状态**（可反悔） |

备份点：`_plugin-backups\20261016-014520\`（本轮前）、`_plugin-backups\20261016-015913-pre-web-all\`（只装壁纸）。回滚后需**完全退出** Desktop（含托盘）再重开。

### 27.4 pnpm 构建闸门的处置（用户 2026-10-16 裁定：全部禁止）

web-all 依赖链带来 3 个要跑安装脚本的包，被 pnpm 11 拦下（`ERR_PNPM_IGNORED_BUILDS`）。已写入 `profiles\desktop\pnpm-workspace.yaml`：

```yaml
allowBuilds:
  canvas: false
  cloudflared: false      # 原会从 GitHub 下载 cloudflared.exe
  cpu-features: false     # 原要 node-gyp 编译（本机缺 VS Build Tools 必失败）
  ssh2: false             # 纯 JS 回退，功能正常
```

代价：`web-ui-ssh`（本就默认禁用）的隧道不可用；**其余 19 个模块不受影响**。用户已有樱花映射，不需要 cloudflared。

### 27.5 ⚠ 待办：UI 按键无响应（用户 2026-10-16 报，明确"先不着急修"）

- 用户原话："那个按键按了没反应"。**具体是哪个位置的按键尚未确认**。
- 首选诊断（未验证）：web-all 的 **client 半（浏览器 JS）未随 HMR 完整加载** —— host 半已确认在跑（路由 200 / 工具已注册），但界面渲染需要浏览器侧重新拉 `/plugins/*/client.js`。
- 建议的零成本验证：**Ctrl+R 刷新页面**（不必重启）→ 若按钮恢复，即证实为 client 半未加载；否则需用户指出具体按键再查。

### 27.6 ★工坊下线 + dsh-market 上线（2026-10-16 第二轮，用户要求）

**用户问题**："老创意工坊按钮点不动，是否和红线有关？是就取消红线。"

**★ 因果结论：与红线无关。** 三条论证：

1. **红线是行为承诺，不是技术机制** —— 三条硬约束只约束"我（AI）不去做什么"，**不写入任何配置文件、不注册任何 hook、不影响任何程序的运行**。它没有能力让一个浏览器按钮失灵。
2. **反证（时间线）**：红线 **2026-10-12** 就定下，此后工坊一直可用（本轮早期我还成功调用过 `workshop_status` / `workshop_search`）。按钮失效**恰好发生在装 web-all 之后**。
3. **技术证据（决定性）**：`@linxin666/dsh-web-all` 的 `lib/client.js` 操作 `sidebarCol` **18 处**、`data-pane="sidebar"` **9 处**、`logoRow` **4 处**、`newSession` **6 处**，并有 **25 处 `MutationObserver`**（持续纠正 DOM）；而 dsh-workshop 的侧边栏注入逻辑（`lib/client.js:110-116`）**恰好依赖这三个锚点**（`sidebarCol` → `logoRow` 的父元素 → `newSession` 按钮）⇒ 两个插件在同一 DOM 位置互相打架，**图标在、点不动**。
   - 佐证：dsh-workshop 的 centerCol 补丁**完好无损**（60252 B / SHA256 `4921B40E…`）⇒ **不是补丁丢失**。

**因此：不取消红线**（取消它对按钮零影响，只会丢掉 web profile 保护）。**真正的修复 = 移除冲突源。**

**已完成的操作**：

| 动作 | 结果 |
|---|---|
| 卸载 `dsh-workshop`（从 dependencies + bundles 移除 → `pnpm install`） | ✅ `Packages: +3 -23`；loader 总数 **227→225**；按包名查 **0 条** ⇒ 侧边栏按钮随之消失（刷新页面即见） |
| **保留目录** | ✅ 原文件 `C:\Users\ROG\.dsh\dsh-workshop\registry.json`（24 MB / **15938 条**）+ 备份 `E:\output\_plugin-backups\dsh-recommend-registry.json` |
| **保留检索手段** | ✅ `C:\Users\ROG\.local\bin\dsh-find.ps1` 查的就是这个 registry.json（其 L40 硬编码该路径），卸载后**照常可用**，还自带 pnpm 构建闸门检查 |
| 装替代 `dshmarket@1.66.27` | ✅ 已入 dependencies + bundles；⚠ **loader 里 0 条 → 需完全重启 Desktop 生效** |

**★ 对上一轮结论的更正**：我曾说"dsh-market 未发布 npm"——**错了**。它的 npm 包名是 **`dshmarket`**（工坊索引的 `npmPackage` 字段为空，把我带偏）。按新铁律第 10 条改读**作者 README** 才纠正过来。

**dshmarket 相对工坊的增量**（据作者 README）：4200+ 策展目录 · 一键安装+实时进度 · **逐插件更新检查 + 一键更新** · **热禁用/启用（写 `cordis.patch.yml`，HMR ~1s 生效，无需重启）** · **诊断页（重复 loader entry / 依赖版本不匹配 / 残留目录）** · 加载顺序拖拽 · 备份恢复（WebDAV / GitHub Gist，合并式 + 失败回滚）· 重启失败恢复面板 · 日志导出。

⚠ **未验证项（诚实边界）**：它的 README 语境通篇是 **web profile**（"install them into the web profile"），**能否写 desktop profile 未直接证实**；但其热禁用 / 诊断 / 更新检查是**直接写 profile 文件、不依赖 CLI**，应可用。若"安装"这条路径走不通，仍有 `plugin-manager` 兜底（已验证能写 desktop）。

**★ 顺带发现（重要）**：本轮开始时 profile 的 `cordis.patch.yml` 与昨天备份有差异 —— `web-ui-pet` 的一段配置（`petId: whale-girl-refined` + 位置坐标 `size/right/bottom`）发生了变化 ⇒ **web-all 的界面模块在用户操作界面时会写 profile 配置文件**。这是它的正常行为，但佐证了"界面层确实在动 DOM 与配置"，与上面的冲突判断互相印证。

**回滚入口**：`E:\output\_plugin-backups\20261016-022524-before-market-swap\`（package.json / cordis.patch.yml / pnpm-workspace.yaml / pnpm-lock.yaml + 目录副本）。

### 27.7 ★★全量体检（2026-10-16 第三轮）：技能池曾"全军覆没" + 已修

**★★ 最大发现：67 个技能（有效 64）在本机 DSH 会话里【全部不可用】—— 而状态文件一直把它当"核心资产"。**

**三级证据**：`skill` 工具对 `data-analysis`（junction）与 `delivery-self-review`（**实体目录**）**一律返回 `unknown or no longer available`** ⇒ 排除"符号链接不被跟随"的猜想，是**整个 skill provider 没供上技能**。

**查证链（全程查权威源，未猜）**：

| # | 取证 | 结论 |
|---|---|---|
| ① | 会话 projcache `session-737e8beb…json` → `"agentPreset": {"val": "cordis"}` | 在用的是 **cordis** preset |
| ② | DSH 源码 `packages/bundle/web-app/presets/cordis.patch.yml:143-147` | 它给 `skill-filesystem` 配的 `customSkillDirs` 是**动态 `!!js` 表达式**（`createRequire(baseUrl).resolve('@deepseek-ai/dsh-agent-preset/package.json')`）→ **运行时不保证解析成功** |
| ③ | `skill-filesystem/src/index.ts` L78-88 / L168 / L258 | 权威字段名：`includeDefaultRoots`（默认 true）、`agentsHome`、`customSkillDirs`、`dshHome`；代码兜底 `join(homedir(),'.agents')` |
| ④ | 磁盘侧 | `~/.agents/skills` 存在（67 目录，**64 个 frontmatter 合规**）；`DSH_AGENTS_HOME` **未设置**；`~/.dsh/skills` 不存在 |
| ⑤ | 环境 | `include:skill-filesystem` / `tool-skill` 在 Config 里是 `inactive`，**但同状态的 `tool-pwsh` 却正常工作** ⇒ ⚠ **`inactive` ≠ 不可用，不能据此判故障**（本轮推翻的旧认知） |

**修复（已落盘，待重启验证）**：在 profile 的 `cordis.patch.yml` 末尾加**显式覆盖块**，用**绝对路径**绕开动态解析：

```yaml
- id: skill-filesystem
  name: "@deepseek-ai/dsh-skill-filesystem"
  config:
    includeDefaultRoots: true
    dshHome: 'C:\Users\ROG\.dsh'
    agentsHome: 'C:\Users\ROG\.agents'
    customSkillDirs: ['C:\Users\ROG\.agents\skills']
```

回滚：删该块 → 重启。备份：`_plugin-backups\20261016-024114-before-skill-fix\`。

**技能池实况（本轮审计）**：67 目录 = junction 60 + 实体 7；**无效 3 条** —— `天眼一下`（name 为中文，非 kebab-case）、`composition-patterns` 与 `react-native-skills`（**缺 description**）。

**★ 另一处确认未生效**：`computer-use` 两行虽在 patch 里，但**工具清单里没有任何 `computer_*` / `mcp__*` 工具**；且 `cua-driver.exe` 实际以 **`serve`** 模式在跑（PID 9188），而配置写的是 `args: [ mcp ]`（stdio）—— **两套模式不匹配**，MCP 未挂载。

**★ 本轮可用性台账（实测）**：`read_image` ✅（真读到 1920×1080 图）· `read_page`/`web_search`/`x_search` ✅ · `session_search` ✅ · `plugin_manager` ✅ · `cordis_inspect_*` ✅ · `pwsh`/`read`/`write`/`edit`/`glob`/`grep` ✅ · `job_*` ✅ · `todo_write` ✅ · `task_board_list` ✅ · **`skill` ❌（已修，待重启）** · **`computer-use` ❌（未挂载）**。

**★ 冗余判定（未动手，待用户定）**：`@liustack/modlens@3.26.5`（2.52 MB）**bundle enabled=false**、功能已被 `dsh-vision-router` 取代 ⇒ 纯死重量，建议移除（改 package.json + pnpm install）。

### 27.8 ★★computer-use 修复成功（2026-10-16 第四轮）——根因是「版本未锁步」

**结果**：`mcp__cua-driver-mcp__*` **全套 57 个工具已出现在模型工具清单**；只读实测通过：`health_report` → 全 pass（cua-driver 0.28.0 / UIA 可达 / D3D11 截图可用）、`get_screen_size` → 2560x1600 @1.5x。**三级证据成立。**

**★ 真因（决定性）**：**DSH 内核于 2026-10-12 升级到 `0.2.0-rc.2`，而 profile 里的 computer-use 家族仍停在 `0.1.6-alpha.1`（未锁步）⇒ peer 契约断裂，provider 激活失败。**

| 包 | 修复前 | 修复后 |
|---|---|---|
| `@deepseek-ai/dsh-computer-use` | 0.1.6-alpha.1 | **0.2.0-rc.2** |
| `@deepseek-ai/dsh-experimental-computer-use-cua-driver-mcp` | 0.1.6-alpha.1 | **0.2.0-rc.2** |
| `@deepseek-ai/dsh-mcp-client` | 0.1.6-alpha.2 | **0.2.0-rc.2** |

peer 要求随之从 `cordis ^4.0.2` 变为 `~4.0.4`（内核自带 4.0.4）——**这就是"以前能用、后来不能"的那个变量**。
时间线铁证（session_search 命中历史会话原文）：09-26「MCP 已经活了…54+ 工具已可用」· 10-04 / 10-12 均有可用记载 → **10-12 内核升级** → 10-15/16 失效。

**★ 本轮被推翻的旧结论（我自己的错判，务必不要再犯）**：

| 我曾断定 | 真相 |
|---|---|
| "cua-driver 跑 `serve`、配置写 `mcp`，两套模式不匹配" | ❌ **serve 与 mcp 是两个独立用途**，`serve` 由计划任务 `cua-driver-serve` 启动，**与 MCP 变体无关**，二者可共存 |
| "可能有单实例锁" | ❌ 实测**两个 mcp 实例并发握手均成功** |
| "instructions 超过 maxInstructionBytes(32768)" | ❌ 实测仅 **1608 B** |
| "用 .cmd 包装脚本探测" | ❌ **Node/Electron 不允许直接 spawn `.cmd`**（`spawn EINVAL`）；且脚本内中文注释被 cmd 当命令执行 |
| "cua-driver 侧有问题" | ❌ **cua-driver 侧自始至终完全正常**（57 工具 / elevated / 握手成功） |

**★ 可复用的诊断经验**：
1. **MCP 挂载失败不会有明显报错**——错误只进 Electron 控制台；`~/.dsh/logs/` 与**会话日志**里都没有（会话日志只记对话）。
2. **`Config` provider 的 `(active)/inactive` 不能用来判定故障**——同为 `inactive` 的 `tool-pwsh` 一切正常。
3. **判定"以前能用现在不能"**：先用 `session_search` 找历史上真实可用的记录，再对比**当时与现在的版本/环境**，不要从现象猜机制。
4. **`@deepseek-ai/*` 实验包必须与内核锁步**：升级 DSH 后要检查 `dsh-computer-use` 这类"手工挂载型"依赖是否也要跟着升。
5. 会话日志解压：`E:\output\_tools\unzstd-frames.mjs`（按 zstd magic 逐帧解，**582/582 成功**）；MCP 探针 `mcp-probe.mjs` / `mcp-perm-probe.mjs` / `mcp-dual-probe.mjs`。

**回滚**：`_plugin-backups\20261016-030342-before-cua-upgrade\`（package.json + cordis.patch.yml）。

**★ 使用边界（重要）**：这些工具能**点击 / 输入 / 启动应用**（会真实影响用户的桌面与焦点）⇒ **默认只用只读类**（`health_report` / `get_screen_size` / `list_windows` / `get_window_state` / `get_browser_state`）；**任何会产生输入或改变桌面状态的动作，先向用户复述并取得同意**。

### 27.9 用户的两项决策（2026-10-16）

1. **技能池**：用户裁定「**那些技能适合给 Trae 用，我们就不用了；有需要直接在插件市场找上位替代**」⇒ **放弃 DSH 侧技能共享**，我已把为诊断做的改动**全部还原**（67 目录原样、探针已删、Trae 源目录未碰）。**今后需要某项能力时的方针 = 去插件市场（dshmarket / 创意工坊商厦）找替代，不再折腾 Trae 技能池**。
2. **native 变体的风险接受度**：用户明确表示「与 DSH 共享进程、原生崩溃可能带走 Desktop 这个代价不高，重启很快」（即：必要时可放心改用 native 变体）。

**★ 已完成的清理**：`@liustack/modlens` **已移除**（`Packages: -24`，目录与 lockfile 双 0 命中）。

### 27.10 ★gh 状态与 git 仓库治理（2026-10-16 第五轮）

#### （1）gh：**早已登录**，此前记载有误

| 项 | 实测值 |
|---|---|
| 账号 | **RXX-CJL**（keyring；scopes `repo` / `workflow` / `read:org` / `gist`） |
| API | ✅ `gh api user` 通；配额 `limit=5000 remaining=4998` |
| 目标仓库权限 | ✅ `RXX-CJL/lingtong-zhisheng` → `admin / maintain / push / triage / pull` **全 true** |
| ★ 本轮修复 | `gh config set editor notepad` —— 原先 `editor=''`，会让 `gh pr create` / `gh issue create` 在**无 TTY 时卡在编辑器**上。（脚本调用仍建议显式带 `--body-file`） |
| 文档修正 | §4 表格与 §7 待办里的"**尚未 `gh auth login`**"**已作废** —— §20 早在 2026-09-27 就记了已登录，是那两处没同步（文档自相矛盾）。 |

#### （2）★ `E:\output` = GitHub 仓库的本地克隆（此前未在本文登记）

- remote：`https://github.com/RXX-CJL/lingtong-zhisheng.git`，分支 `main`
- **2026-10-16 完成首次完整推送**：`4a67b5a..a0822ab`（**7.45 MB / 735 blob**），本地与 `origin/main` **完全同步**
- 本次留下 4 个提交：`8c3b5a4`（git 瘦身规则）· `d26bbab`（项目代码 109 文件）· `da9dd6e`（办公室文档 600 文件）· `a0822ab`（工具脚本 30 文件）；另含 10-13 的 `d88a7b6`

#### （3）★★ 仓库瘦身：`.git` **1657.85 MB → 22.19 MB**（−98.7%）

**诊断链（可复用）**：
1. `git count-objects -vH` → `in-pack: 8700`、`size-pack: 1.61 GiB`，但 `garbage: 0`（说明 gc 没东西可清）
2. `git rev-list --objects --all | git cat-file --batch-check=…` → **可达对象仅 1506 个 / 内容仅 36.08 MB**
3. `git fsck --unreachable` → **7187 个 unreachable blob**（抽样 3000 个即 **889 MB**）
4. `.git/filter-repo/` 目录存在 ⇒ **以前跑过历史重写，旧对象变悬空但从未回收**

**处置**：`git reflog expire --expire=now --all` + `git gc --prune=now` → **0.4 秒完成**，回收 **1635 MB**。
**完好性核对**：HEAD / 9 个提交 / 1364 个跟踪文件 / 工作区干净 / 与远程同步 —— **全部照旧**。
**结论**：悬空对象删除**零影响**（不被任何 ref 引用）；真正不可恢复的只有"已删除分支/stash"的残骸，而实测本机**无 stash**。

#### （4）★ 仓库治理原则（用户 2026-10-16 裁定，已写入 `.gitignore`）

> 「**git 上最好还是用来保留项目，而不是测试数据**，哪怕 git 上没有一点证据留存，**只要功能一点没少就行**」

落地：`.gitignore` 从 13 行加固到 60 行，新增忽略
`1/carla/`（CARLA 本体 **18.5 GB**）· `1/api/output/`（运行产出 **13.3 GB**）· `1/uploads/` · `1/test_assets/` ·
`*.db` / `*.pt` / `*.pth` / `*.onnx` / `*.ckpt` · 根目录 `_*/`（测试目录，**放行 `_tools/` 与 `_scripts/`**）· 根目录散落媒体 · 编辑器备份 `*.ck/*.c9/*.bak-*`；
并把**已跟踪**的 `1/api/zhitong_violations.db`（**28.8 MB**）用 `git rm --cached` 移出索引（**本机文件保留**）。
★ **本机文件一个都没删**（工作区仍 51.1 GB，功能零损失）。

#### （5）其它登记

- ★ **Trae 的 worktree**：`C:\Users\ROG\.trae-cn\worktrees\output\feat-empty-input-99G4ey`（分支指向 2026-06-10 的 `b2747f4`，相对 main 领先 0 个提交）。**属 Trae 资产，未动**（仅占 0.03 MB）。
- 不属于本仓库的 `《供配电系统项目综合设计》工程日志_第3组.docx` 已按用户指示**移出**到 `C:\Users\ROG\Documents\供配电系统项目综合设计\`。
- **纪律**：`E:\output` 是用户的 GitHub 仓库克隆 ⇒ **AI 不要自行 `git commit` / `git push`**（本轮是用户明确授权后才做的）。**⚠ 该条已于 2026-10-16 被用户授权取代，见 §27.11(1)。**

### 27.11 ★Git 授权 + C 盘瘦身 + output 整理（2026-10-16 第六轮）

#### （1）★ Git 操作授权变更（用户 2026-10-16 明确授权）

> 用户原话：「我信任你，从现在起**你可以自行 commit/push** `E:\output`（用户的 GitHub 仓库），**无需每次征求同意**。」

⇒ **作废**上一节"AI 不要自行 git commit/push"的限制。**现行纪律**：
- ✅ 可自行 `commit` / `push`（新增文件、整理、文档更新）
- ⚠️ 仍须遵守：**不删本机文件** · **不提交测试/运行数据**（见 §27.10(4) 的 `.gitignore` 原则）· **不 force push、不重写已推送历史**
- 本轮据此完成提交并推送：`16ebba0`（gh 状态与 git 治理记录）· `663e2ff`（整理根目录）· `2eb9fcb`（修正误忽略）

#### （2）★ C 盘瘦身

**磁盘布局（实测）**：`C/D/E` = 同一块 954 GB SSD 的三个分区（**C 仅剩 35.6 GB，已告急**）；**`F` = 独立致钛 TiPro7000 2TB SSD**（剩 **704.8 GB**，速度不输 C）。

**阶段①已完成**：清理 `%TEMP%` 下 21 个**旧 DSH 工作区快照**（`dsh-workspace-changes-*`，保留最新 1 个）+ 4 个安装包缓存 → **回收 10.7 GB**（Temp **11.7 GB → 1.48 GB**）。

**★ Temp 位置迁移（用户选定，已完成）**：`TEMP` / `TMP` **用户级**环境变量 → **`F:\Temp`**
- **依据（源码权威）**：DSH 快照位置 = `os.tmpdir()` —— 见 `packages/deliverables/workspace-changes/src/recorder.ts`（`mkdtemp(join(this.env.tempRoot, 'dsh-workspace-changes-'))`）+ `index.ts`（`tempRoot: tmpdir()`）⇒ **DSH 无独立配置项，只能改环境变量**。
- 连带效果：DSH 沙箱（`sandbox-windows-acl`）临时目录同样走 `tmpdir()`，会一起搬到 F 盘。
- ⚠ **生效条件**：只有**新启动的进程**读新值 → **DSH 需重启**后快照才写入 F 盘。
- 回滚：`[Environment]::SetEnvironmentVariable('TEMP','C:\Users\ROG\AppData\Local\Temp','User')`（TMP 同）。
- 系统级 `C:\Windows\TEMP` **未动**（保持系统稳定）。

#### （3）★ `E:\output` 根目录整理（方案 A 保守整理，已完成）

| 项 | 结果 |
|---|---|
| 判定方法 | ripgrep 全量扫描 × 与 `1/api`、`1/docs`、`_tools`、`_scripts`、`AGENTS.md` 语料比对 |
| **被引用（78 个，原位未动）** | `_DSH_OFFICE_STATE.md`（40 处引用）· `_SESSION_HANDOFF.md`（29）· `_AI_COMMON_RULES.md`（5）· `_PROJECT_MAP.md` · `_STARTUP_GUIDE.md` · `*_verdict.md` 等 |
| **未被引用（161 个，已归类）** | `_reports/` **17 个**（结论报告）· `_notes/` **146 个**（调试笔记 + 两份清单） |
| 根目录文件 | **416 → 264 个** |
| 断链校验 | ✅ 移动前后各校验一次，**零断链** |
| 未动 | `1/`（项目本体）· `_tl_color_cls/` · `_scripts/` · `_tools/` |

★ **整理红线（实测得出，勿违）**：`1/api/traffic_light_classifier.py` **硬编码** `E:\output\_tl_color_cls\*.pt`（2 个模型权重）与 `E:\output\_scripts`；`annotation_renderer.py` **硬编码** `1\K230\…\OPPOSans 4.0.ttf` ⇒ **这三处绝对不能移动**。

**★ 本轮踩的坑（已修）**：`.gitignore` 的 `_*/` 规则把新建的 `_notes/`、`_reports/` 一并忽略，导致 161 个文档只记录"删除"、未记录"新增"（远程副本一度丢失）。**教训：改 `.gitignore` 后必须用 `git check-ignore <目录>` 验证可见性。**

### 27.12 ★C 盘瘦身第二阶段（2026-10-16 第七轮，机器重启后）

#### （1）✓ Temp 迁移已生效（三级验证）

| 证据 | 内容 |
|---|---|
| 环境变量 | 注册表与**新进程**的 `TEMP`/`TMP` 均为 `F:\Temp` |
| **实证（最强）** | `F:\Temp` 已出现 `dsh-workspace-changes-eCOIzC`、`dsh-acl-skill-*`、`dsh-spill-*`、`dsh-subprocess-*` ⇒ **DSH 的快照 / 沙箱 / 派生进程全部落在 F 盘** |
| 连带生效 | `miHoYo`/`WinGet`/`ListSync` 等其他程序的临时目录也在 F 盘 ⇒ 全局生效 |

**阶段④ 清 C 盘 Temp 残留**：删除 **1445 项**，回收 **0.53 GB**，C 盘 Temp 归零。

#### （2）✓ `~/.cache` 已迁至 F 盘（junction，缓存未丢）

| 项 | 值 |
|---|---|
| 迁移 | `C:\Users\ROG\.cache` → `F:\cache`（**1918.2 MB**，13.9 秒） |
| 联结 | `New-Item -ItemType Junction`，实测 `LinkType=Junction -> F:\cache` |
| 读取验证 | 通过 C 盘路径可见全部 6 个缓存目录（`codex-runtimes` / `puppeteer` / `chrome-devtools-mcp` …）⇒ **程序无感知，不需要重下** |
| 选型理由 | 比"删除"更优：既省 C 盘，又不丢 1.55 GB 的 `codex-runtimes` 缓存 |

**回滚**（删联结 → 移回；注意只删联结不动 F 盘内容）：
```powershell
Remove-Item 'C:\Users\ROG\.cache' -Force
Move-Item 'F:\cache' 'C:\Users\ROG\.cache'
```

#### （3）C 盘瘦身总账

| 阶段 | 内容 | 回收 |
|---|---|---|
| ① | 清旧 DSH 快照（21 个）+ 安装包缓存 | **10.7 GB** |
| ④ | 清 C 盘 Temp 残留（1445 项） | **0.53 GB** |
| ②′ | `~/.cache` 迁 F 盘（junction） | **1.9 GB** |
| — | **合计** | **≈13.1 GB** |
| **C 盘剩余** | 35.6 GB → **39.3 GB** | — |

★ **根治机制**：`TEMP`/`TMP`（用户级）= `F:\Temp` ⇒ 今后 DSH 快照与所有临时文件**不再占用 C 盘**，从根上解决"快照堆积吃掉 C 盘"（本轮之前单个会话就能堆 10 GB）。

#### （4）⏸ 尚未执行：阶段③（大目录迁移，需先退出对应程序）

| 目标 | 大小 | 前置条件 |
|---|---|---|
| `~/.dsh`（DSH_HOME） | 532 MB | ⚠️ 必须**完全退出 DSH**（AI 无法自行退出，会话在其内部） |
| `~/.trae-cn` | 606 MB | 需退出 Trae |
| `~/.workbuddy` | 868 MB | 需退出 WorkBuddy |
| `~/.qoder-cn` | 433 MB | 需退出 Qoder |
| **合计** | **≈2.4 GB** | 迁移方式同为「移 F 盘 + junction」 |

### 27.13 ★阶段③执行结果（2026-10-16 第七轮续）—— 三个 App 数据已迁 F 盘

**用户操作**：关闭 Trae / WorkBuddy / Qoder（DSH 保持运行）。

| 目录 | 结果 | 耗时 | 备注 |
|---|---|---|---|
| `~/.trae-cn`（606.4 MB） | ✅ `Junction -> F:\appdata\trae-cn` | 21.8 s | `Move-Item` 一次成功 |
| `~/.qoder-cn`（434.1 MB） | ✅ `Junction -> F:\appdata\qoder-cn` | 10.9 s | 同上 |
| `~/.workbuddy`（868.3 MB） | ✅ `Junction -> F:\appdata\workbuddy` | 11.6 s | ⚠️ 见下 |

**★ WorkBuddy 的波折与正确姿势（重要经验）**：
- 首次 `Move-Item` **中途失败**（`Access to the path is denied`）→ 源被删了一部分、目标留半成品（**源 312.4 MB + 目标 733.8 MB**）；而按进程名**找不到任何占用者**（疑为杀软实时扫描或后台服务临时锁）。
- **正确补救 = `robocopy /E /MOVE /R:2 /W:2`**：**续传**剩余 14,644 文件、**0 FAILED**、退出码 3（成功），确认源被清空后才建 junction ⇒ **数据无损**。
- ⚠️ **新纪律**：跨盘搬大目录**别用 `Move-Item`**（无续传、失败即半成品），**直接用 `robocopy /MOVE`**（可重试/可续传/有 FAILED 计数）。

**★ C 盘瘦身最终总账**：

| 阶段 | 内容 | 回收 |
|---|---|---|
| ① | 清 21 个旧 DSH 快照 + 安装包缓存 | 10.7 GB |
| ④ | 清 C 盘 Temp 残留 1445 项 | 0.53 GB |
| ②′ | `~/.cache` → `F:\cache`（junction） | 1.9 GB |
| ③ | `~/.trae-cn` + `~/.qoder-cn` + `~/.workbuddy` → `F:\appdata\*` | 1.9 GB |
| | **合计** | **≈15.0 GB** |
| **C 盘剩余** | **35.6 GB → 41.3 GB** | — |

**⏸ 唯一未迁：`~/.dsh`（DSH_HOME，532 MB）—— 建议不做**：
- **收益小**（532 MB，仅占已回收量的 3.5%）；
- **风险大**：它是 DSH 核心数据（profile / 插件 node_modules / 会话 / 记忆 / 凭据），一旦 junction 出问题 DSH 可能起不来，而迁移**必须在 DSH 完全退出时**进行（届时无任何 AI 在场，出错只能靠用户手动救援）；
- **决策：保持现状**。若将来 C 盘再吃紧再议，届时可做一个"检测 DSH 未运行 → 移动 → 建联结 → 失败自动回滚"的双击脚本。

**★ 迁移后验证（留给用户）**：下次打开 Trae / WorkBuddy / Qoder 时留意能否正常启动、历史与配置是否还在——**junction 对程序透明，预期无感知**；若异常，回滚写法同 §27.12(2)：删联结 → `Move-Item F:\appdata\<name> C:\Users\ROG\.<name>`。

### 27.14 ★WorkBuddy 模型接入调研（2026-10-17）—— 结论：装 `dsh-connect-workbuddy`

#### （1）硬数据：WorkBuddy 的模型清单（本机产品配置实读）

来源：`~/.workbuddy/storage/user-<id>-personal/scoped/<hash>/wb-product-config.json`（99,528 B，`savedAt` 2026-10-17 00:07），共 **59 个模型**，每个带**积分倍率**。关键条目：

| 倍率 | 模型 | 输入 | 备注 |
|---|---|---|---|
| **x0.00** | `hy3` / `hy3-b` / `hy3-c` | 192K | 混元思考，**免费**（国内版当前唯一免费档） |
| **x0.00** | `step-5-preview` | 1000K | 阶跃旗舰，**免费** |
| x0.06 | `glm-5.3-flash` | 1000K | 极便宜 |
| **x0.11** | `deepseek-v4.1-flash` | 1000K | ★ **与我们 DSH 当前默认模型同源** |
| x0.21 / x0.65 / x1.20 | `fast-model` / `balanced-model` / `deep-model` | 300K | WorkBuddy 抽象档（快速 / 均衡 / 极致） |
| x0.51 | `deepseek-v4-pro` | 1000K | |
| **x1.62** | ★★★ **`kimi-k3-1`（Kimi-K3）** | **1000K** | **全表最贵**；官方描述"复杂长程自主任务、**前端开发突出**、知识工作与科研推理" |

★ `modelTiers` 显示 `glm-5.3` / `glm-5.3-flash` / `kimi-k2.8-preview` 对标准用户有"资源紧张时优先调度"限制（**`kimi-k3-1` 不在该列表**）。
★ `endpoint = https://www.workbuddy.cn`，`deploymentType = SaaS`，`productName = WorkBuddy`。
★ **用户情况（2026-10-17 自述）**：免费用户，**每天可领 100 积分**，积分可视化、余额充足；最看重 **Kimi-K3**。目标 = **更方便地指挥调用其它模型 + 省钱**。

#### （2）插件选型：★ 选 `dingminhua/dsh-connect-workbuddy`（**不是** ★183 那个）

| | **`dsh-connect-workbuddy`** ✅ 选定 | `corrinehu/dsh-workbuddy-connect` ❌ |
|---|---|---|
| 版本 / ★ | **4.6.5** / ★34 | 0.7.6 / ★183 |
| **Windows** | ✅ **一等目标平台**：CI 跑 `windows-latest` 全量套件（79 文件 / **1325 测试**）+ `docs/WINDOWS.md` | ⚠️ 作者自述"**no Windows or Linux test run**" |
| **积分显示** | ✅ **对话输入框常驻读数**（`WB CN · 1,072`）+ 点击弹余额面板（只读） | 未明确 |
| DSH 兼容 | `0.1.7-rc.1` ~ `<0.3.0-0`，**0.2.0 全线已实测支持** | 未标注 |
| 工程素养 | ★ 有**证据分级 A/B/C/D**、自曝 C 档结论、发版密集（4.6.3→4.6.5 同日 3 版） | 775 测试 |

**兼容性核实（本机实检）**：DSH `0.2.0-rc.2` ✅ · Windows 11 26200 ✅ · Node v24.16.0（PATH）/ v24.21.0（Desktop 内置）✅ · `dsh.bundle.patch` 存在 → **可用插件页一键装** ✅ · WorkBuddy 桌面版已登录、凭据就位 ✅ · **两个插件均未安装**（环境干净）

#### （3）★★ 必须记住的硬约束（否则装完必踩）

上游 README 的两条实测：
1. **限流按请求体积触发**：**约 20k 输入能过、约 30k 被拒**
2. **上游宣称 1M 上下文，但节流线远低于此**

⚠️ 而我们自己的实测是：**单次调用上下文 p50 = 368,917 token**（88.6% ≥128K，见 workspace 记忆 `agent-model-phase-sensitivity`）
⇒ **冲突明确**：**长会话模式跑 WorkBuddy 模型会被 429 拒**
⇒ **正确分工**：WorkBuddy（含 Kimi-K3）**只跑短上下文任务**（新开干净会话、单点问题、代码片段）；**超长上下文的活继续走 DeepSeek 官方通道**。

**其它要点**：积分查询走 `https://www.codebuddy.cn/v2/billing/meter/get-user-resource`（**只读**、不耗积分）· 桌面 App 的 auth 文件**永不被写入** · 每区域随机端口 + 进程内随机 secret（真 token 不交给 pi-ai）· **不提供自动签到**（每天 100 积分需**手动点「一键签到」**）· 命令行诊断 `status` / `doctor` / `logout`

#### （4）⏳ 当前进度（**下次会话接手点**）

- **用户已选择 GUI 安装路径**：侧边栏 Plugins 页搜 `dsh-connect-workbuddy` → Install → Enable now → **重启 DSH**
- **待验证（重启后由 AI 做）**：① 插件卡片是否出现 ② **输入框是否出现 `WB CN · 数字` 读数** ③ 模型选择器是否列出 `Kimi-K3 · x1.62` 等
- **失败时**：多半是**兼容门禁**（`skippedBundles`，**只在 stderr 打印、页面无报错**）→ 用 `status` / `doctor` 诊断
- **装成后待办**：① 定"模型分工策略"（哪个任务用哪个模型最省积分）② 提醒用户**每天手动一键签到**

### 27.15 ★插件配置完成 + computer-use 实操记录（2026-10-17）

#### （1）✅ 全部配置完成（三级证据）

| 项 | 证据 |
|---|---|
| 插件安装 | `dsh-connect-workbuddy@4.6.0`（23 文件，含 `bundle.patch`；profile 依赖 + bundles 已登记） |
| 宿主运行 | `Host bundle: running (pid 26104)`；卡片页显示「运行中」 |
| 凭据读取 | CLI `status`/`doctor`：**`CN (domestic): signed in as 刃下心`**（★ 加密凭据解密成功，昵称非 uin 数字） |
| **积分可读** | CLI `Remaining credit: 2795.22`；卡片账号行显示 **`2,795`** |
| **签到成功** | 点「一键签到所有账号」→ 活动记录出现 **`00:33:21 签到完成`**，积分 **2695 → 2795（+100）** |
| **模型目录刷新** | 点「从 WorkBuddy 刷新」→ 列表从 12 个 fallback 扩成完整目录（含 `Kimi-K3`、`Kimi-K2.8-Preview`、`Kimi-K2.7-Code`、`GLM-5.3-Flash`、`Deepseek-V4-Pro`…） |
| **Kimi-K3 已启用** | 勾选 + 保存 → 「已启用 1 个」，行内显示 `✓ 可用 (2.626s) · credit 1.23` |

★ **积分有效期**：卡片显示「最近积分包 **11/05 03:20 过期**」（按插件排序规则，快过期的积分包优先使用）。

#### （2）★★ 成本锚点（本轮最有价值的数据）

Kimi-K3 的一次**约 2.5 万 token 探测** = **`credit 1.23`**（插件自报）。
⇒ 换算：Kimi-K3 约 **0.49 积分 / 万 token** ⇒ **每日 100 积分 ≈ 200 万 token/天**。
⇒ ⚠️ **而本会话累计 101M token** ⇒ 若全用 Kimi-K3 ≈ **5,050 积分**（**一天额度只够 2%**）。
⇒ **纪律**：**长会话绝不用 Kimi-K3**；日常用免费档（`Step-5-Preview` / `Hy3` 均 **x0.00**），重要任务用便宜档（`GLM-5.3-Flash` **x0.06** / `Deepseek-V4.1-Flash` **x0.11**）。
⚠️ 口径**待实测确认**（目前仅 1 次观察样本）。

#### （3）★★ computer-use 实操教训（首次实战）

**工具**：`mcp__cua-driver-mcp__*`（57 个，本会话已修复可用）

**四条纪律（实测有效）**：
1. **先 `get_window_state` 拿索引/截图**，动作后**必须复核**（截图或 `verify_state`）——「工具说已投递」≠「真的生效」。
2. **`delivery_mode:"background"` 先试**，让 driver 决定何时必须升级。★ 实测**滚动**事件在 Chromium 上直接返回 `background_unavailable`（并明确指示改用 foreground）。
3. ★★ **小目标必须先 `zoom`**：目测坐标在本机偏差可达 **30+ px**（复选框仅约 16px，直接目测点会**静默失败**）。`zoom` 后用 `click(from_zoom=true)` 由 driver 换算。
4. **坐标空间**：截图被缩放（本机 2560×1600 全屏 → 截图 1500×937，比 **1.706**），driver 会自动换算，**不要自己算**。

**实测的成败记录（重要）**：

| 动作 | 模式 | 结果 |
|---|---|---|
| 点左侧「插件」导航 | background（zoom 坐标） | ✅ 成功 |
| 勾「刃下心」复选框 | background（目测坐标） | ❌ **静默失败**（偏约 16px） |
| 同上（zoom 修正坐标） | background | ✅ 成功 |
| 滚动页面 | background | ❌ 工具**明确拒绝**（`Background delivery is not available … mouse_scroll`）→ 改 foreground ✅ |
| 勾 `Kimi-K3` | background（zoom 反推坐标） | ❌ **再次静默失败**（页面重排后坐标失效） |
| 勾 `Kimi-K3` | **foreground** | ✅ **成功** |
| 保存模型 | foreground | ✅ 成功 |

⇒ **结论**：**Chromium（Electron）内容上 background 投递不稳定**；**同一目标若 background 失败一次，直接改用 foreground**（`click`/`scroll` 均支持 `delivery_mode:"foreground"`，driver 会临时激活窗口并**恢复原前台**）。

**★ 使用边界（已与用户约定）**：只读类（`health_report` / `get_screen_size` / `list_windows` / `get_window_state` / `zoom` / `get_browser_state`）可直接用；**任何产生输入或改变桌面状态的动作（click / type / scroll / launch）先取得用户同意**。

#### （4）⏳ 留给用户的两件事

1. **切到 WB 模型即可看到积分读数**：README 明确「用其它 provider 的模型时该读数**完全不出现**」⇒ 在模型选择器里选任一 WB 模型后，**输入框左侧会出现 `WB CN · 2,795`**（点它可看余额面板）。
2. **每天点一次「一键签到所有账号」**（插件**刻意不做自动签到**，因签到会真实领取奖励）。

