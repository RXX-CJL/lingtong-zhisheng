# DSH 插件与技能清单（可分发版）

> **用途**：给另一位用户查阅——想知道「这台机器上的 DSH 装了什么、有什么本事、我该怎么装」。
> **核对时间**：2026-10-18 ｜ **核对方式**：直接读磁盘与配置，不靠记忆
> **核对源**：
> - 插件：`C:\Users\ROG\.dsh\profiles\desktop\package.json` + `cordis.patch.yml` + `node_modules\<包名>\package.json`（逐个读版本与描述）
> - 技能：`C:\Users\ROG\.agents\skills`（67 个目录）、`C:\Users\ROG\.dsh\skills`（3 个）、Desktop 运行时内置 `resources\runtime\office-skills`（7 个）
> **一句话结论**：
> - 插件：**17 个 npm 依赖**（其中 2 个因缺 `dsh.bundle.patch` 需手工挂载）+ **1 个内核自带的检索工具手工挂载** = **20 项在跑**
> - 技能：**77 个目录 → 76 个有效**（`天眼一下` 因命名不合规未加载）

---

## 阅读指南

| 你想干什么 | 看哪一节 |
|---|---|
| 想知道这台机装了哪些插件、各自干什么 | [第一部分 · 插件](#第一部分插件清单) |
| 想按用途找一项技能 | [第二部分 · 技能](#第二部分技能清单) |
| 想把东西搬到自己机器上 | [第三部分 · 安装与迁移](#第三部分给另一位用户的安装指引) |

**⚠ 先分清两类东西——它们的分发方式完全不同**：

| | 插件（Plugin） | 技能（Skill） |
|---|---|---|
| 形态 | npm 包，有 `dsh.bundle` 补丁 | 一个含 `SKILL.md` 的目录 |
| 安装 | `npm install` 或插件市场点一下 | 把整个目录复制进技能池 |
| 生效 | 多数需重启 Desktop | 热加载，下一个会话即可用 |
| 依赖 | 内核版本 + `dsh.bundle.patch` | 部分需要外部 CLI（已逐条标注） |

---

# 第一部分：插件清单

## 1.1 已装插件总表（Desktop Profile，共 17 个 npm 依赖）

按用途分四组。**「包名」列可直接用于 `npm install`**。

### A. 能力增强——让 Agent 多做几件事（7 个）

| # | 包名 | 版本 | 功能说明 |
|---|---|---|---|
| 1 | `@liustack/modsearch` | 5.10.5 | **联网搜索**。给没有原生联网能力的模型补上 web 搜索、X（推特）搜索、网页正文抓取三个工具。开箱即用，无需注册或 API Key（Firecrawl 免费额度 1000 次/月）。本会话的 `web_search` / `read_page` / `x_search` 来自它。 |
| 2 | `dsh-vision-router` | 3.0.3 | **给纯文本模型装眼睛**。内置免费视觉链路 + 像素级工具，让只能读文字的模型也能看图。⚠ 默认会把图片发往远程视觉服务商，要纯本地需显式配置。 |
| 3 | `@deepseek-ai/dsh-computer-use` | 0.2.0-rc.2 | **电脑操作（命名 provider 注册）**。computer-use 能力的基础注册层，真正驱动在下一行的 MCP 包。**无 bundle 补丁，必须手工挂载**。 |
| 4 | `@deepseek-ai/dsh-experimental-computer-use-cua-driver-mcp` | 0.2.0-rc.2 | **电脑操作的实际驱动**。经 stdio 连一个独立的 Cua Driver 可执行文件，让 Agent 能看屏幕、点鼠标、敲键盘。依赖外部程序 `cua-driver.exe`（v0.28.0，提供 57 个工具）。**无 bundle 补丁，必须手工挂载**。 |
| 5 | `@hr98w/dsh-memory` | 0.1.4 | **长期记忆**。仿 Claude Code / Codex 的持久记忆：跨会话记住偏好、项目事实、踩坑记录。分「全局记忆」与「工作区记忆」两个作用域，会话自动注入。写记忆走 `memory_update` 工具，不手改文件。 |
| 6 | `dsh-session-workbench` | 1.0.3 | **会话工作台**。会话库全文搜索历史对话，一键以 `@引用` 召回给 AI；另有会话视图管理（标签栏显示/隐藏、排序）。 |
| 7 | `dsh-batch-tool-calls` | 1.1.2 | **批量工具调用**。让 Agent 在一个步骤里并发发起互不依赖的工具调用，减少步数、降低提示缓存重读量。省钱 + 提速。 |

### B. 模型接入与推理控制（3 个）

| # | 包名 | 版本 | 功能说明 |
|---|---|---|---|
| 8 | `dsh-connect-workbuddy` | 4.6.0 | **把本机登录的 WorkBuddy 模型接进 DSH**。附带只读积分概览与模型管理面板（Hy4 preview / Hy3 / Step-5-Preview / Space-Bunny 等档位）。本机当前默认模型 `workbuddy/deepseek-v4.1-flash` 就是走它。 |
| 9 | `dsh-llm-retry-settings` | 0.1.17 | **LLM 自动重试设置卡**。可调重试次数/退避/抖动，勾选 25 个错误码（也能自己输），可按 provider/model 单独设策略；回答被输出 token 上限截断时自动续写且提示词可改；内置重试观测面板，改完实时生效。 |
| 10 | `dsh-pause` | 0.1.3 | **「暂停」插话器**。Agent 完成一轮工具交互、即将发出下一次模型请求之前暂停，保持输入框可用；人按回车放行并可附带补充文字。**不打断任何在途 API 调用**，模型上下文始终完整无感知。 |

### C. 输入与交互体验（3 个）

| # | 包名 | 版本 | 功能说明 |
|---|---|---|---|
| 11 | `dsh-better-input` | 0.2.6 | **输入增强四合一**：文件转 Markdown（PDF/Word 等）、本地文件输入、提示词优化（polish + optimize 双通道，走 deepseek-flash）、语音输入（最长 120 秒）。 |
| 12 | `@linxin666/dsh-web-all` | 0.4.6 | **DSH Web UI 全家桶聚合包**。一次性带齐 task-board / git-graph / pet / remote-web-ui / web-ui-settings / skin-center / community-plugins / compat 桥接层（compat 已并入本包，无需另装）。本会话的任务看板来自它。 |
| 13 | `dsh-plugin-wallpaper-engine` | 1.3.2 | **壁纸引擎**。把本机的 Wallpaper Engine 壁纸渲染到聊天界面背后——Scene / Web 走内置 WebWallGL 实时渲染，Video 直接播放；配 iOS 风液态玻璃、模糊/蒙版/边框/透明度可调、自定义字体与光标，连设置窗口也做了液态玻璃改造。本机扫到 585 个可用壁纸。**要求内核 ≥ 0.1.5**。 |

### D. 界面装饰与市场（4 个）

| # | 包名 | 版本 | 功能说明 |
|---|---|---|---|
| 14 | `dshmarket` | 1.66.27 | **可视化插件市场**。在 DSH 内部浏览、搜索、一键安装社区插件。不用命令行就能逛和装。 |
| 15 | `dsh-whale-widget` | 0.3.16 | **DeepSeek 余额小鲸鱼**。右下角挂件显示余额/今日已用/峰谷定价；支持自定义泡泡点击序列（文本/余额/今日/峰谷/图片/随机语句，可加权并列）、逐行样式与字体、悬浮快捷编辑、音效与每轮消耗显示、自定义角色与动图。**装自 GitHub 源**（`github:MeteorNOX/DeepSeek-Balance-Whale-Widget`），非 npm 官方包。 |
| 16 | `dsh-pet` | 0.3.7 | **桌宠·蓝色大肥鱼**（当前启用的那一个）。玩魔方、吃零食、打盹、在桌面溜达；你忙时跟着忙前忙后，还会帮你打理余额钱包，闲下来碎碎念、陪你唠嗑。 |
| 17 | `@linxin666/dsh-pet` | 0.4.7 | **桌宠·多角色注册版**（**已禁用**）。registry 驱动的浮动宠物，支持每只单独命名、抚摸/喂食互动、好感度积分。现被 `dsh-pet` 取代，但仍是 `@linxin666/dsh-web-all` 的依赖，**只禁行不删包**。 |

## 1.2 内核自带 bundle（4 个，无需安装）

以下由 DSH 内核随包提供，出现在 `dsh.profile.bundles` 里但不是我们装的：

| 包名 | 作用 |
|---|---|
| `@deepseek-ai/dsh-base` | 基础运行时（工具、会话、配置加载） |
| `@deepseek-ai/dsh-web-app` | Web GUI 主体 |
| `@deepseek-ai/dsh-experimental-auto-review` | 实验性自动审查 |
| `@deepseek-ai/dsh-experimental-agent-team-profile` | Agent Team（队友/子代理编排） |

## 1.3 手工挂载项（3 项，不在 npm 依赖里）

这些是通过 `cordis.patch.yml` 的 `insert` 块手动接进加载器的，**光 `npm install` 不会生效**：

| 挂载 id | 包名 | 为什么手工 |
|---|---|---|
| `computer-use` | `@deepseek-ai/dsh-computer-use` | 无 `dsh.bundle.patch`，插件页拒绝安装 |
| `computer-use-cua-driver-mcp` | `@deepseek-ai/dsh-experimental-computer-use-cua-driver-mcp` | 同上；另需绝对路径指向 `cua-driver.exe` |
| `session-query-tool` | `@deepseek-ai/dsh-tool-session-query` | 内核自带包，补一个跨会话检索入口 |

## 1.4 装插件的五条硬规矩（血泪版）

1. **装前必查 `dsh.bundle.patch`**：包里没有这个字段，装完不生效，只能像 §1.3 那样手工挂 `cordis.patch.yml`。
2. **桌面版只能走侧边栏 Plugins 页**：`dsh plugin --profile desktop` 会被硬编码拒绝。
3. **配置改 `cordis.patch.yml`，不要改 `cordis.yml`**：后者是 launcher 生成物，手改会消失。
4. **启动级配置要重启 Desktop**：HMR 不会热加载 `cordis.yml` 层（如 §1.3 的 session-query 索引配置）。
5. **部分插件装完立即生效无需重启**（如 `@linxin666/dsh-web-all`、壁纸插件），部分必须重启——拿不准就重启一次。

---

# 第二部分：技能清单

## 2.0 总览

| 来源 | 数量 | 位置 | 分发方式 |
|---|---|---|---|
| 共享技能池（开源技能集） | 67 个目录 / **66 个有效** | `~/.agents/skills` | 复制目录 |
| 本机自建 | 3 个 | `~/.dsh/skills` | 复制目录（**含本机专有事实，别人需改写**） |
| Desktop 运行时内置 | 7 个 | `resources/runtime/office-skills` | 装 DSH Desktop 即有 |
| **会话实际可用** | **76 个**（66 + 3 + 7） | — | — |

> **⚠ 67 个目录只有 66 个生效**：`天眼一下` 的 frontmatter `name` 是中文，不符合 kebab-case 规则，DSH 静默不加载。**技能名必须是 kebab-case，且必须能解析出 `description`，否则不出现**——这是踩过的坑。
>
> 下方 2.1–2.12 逐条列出 **77 条** = 76 条可用 + 1 条未生效（天眼一下，已标注）。
> 其中 `delivery-self-review` 虽为本机撰写，但放在共享技能池 `~/.agents/skills`，故计入 66 之内。

### 2.0.1 ⚠ 目录名 ≠ 技能名（9 处，找文件时看这里）

技能在会话里以 `SKILL.md` 的 `name:` 字段出现，**磁盘目录名可能不同**。下列 9 个目录名与技能名不一致：

| 磁盘目录名 | 实际技能名 |
|---|---|
| `composition-patterns` | `vercel-composition-patterns` |
| `react-best-practices` | `vercel-react-best-practices` |
| `react-native-skills` | `vercel-react-native-skills` |
| `knowledge-capture` | `notion-knowledge-capture` |
| `meeting-intelligence` | `notion-meeting-intelligence` |
| `research-documentation` | `notion-research-documentation` |
| `spec-to-implementation` | `notion-spec-to-implementation` |
| `hook-analyzer-skill` | `hook-analyzer` |
| `report-generator-skill` | `report-generator` |

> 复制技能时**以目录名为准**（整个目录搬走即可）；在对话里**以技能名为准**（`skill` 工具按 name 加载）。

## 2.1 本机自建技能（4 个）

> 这四条是**为本机量身写的**，含具体路径、端口、账号习惯。**别人拿去必须改写**，不能直接用。
> 存放位置：前三个在 `~/.dsh/skills`；`delivery-self-review` 在共享池 `~/.agents/skills`（故也计入上面 66 个之内）。

| 技能 | 功能说明 |
|---|---|
| `dsh-delegation-channels` | **本机算力路由手册**——一件事该交给谁做：DSH 内置 DeepSeek、WorkBuddy 各档模型（免费档/便宜档/Kimi-K3）、本地 CLI 通道（Codex / Qoder / CodeBuddy / gh）、以及只能靠人传话的软件（Trae / WorkBuddy GUI）。任务需要换模型、派活、外包、省钱选档，或提到 Codex/Qoder/CodeBuddy/积分/额度/429 时读它。 |
| `dsh-office-ops` | **DSH「办公室」运维手册**——改 profile / `cordis.patch.yml`、装卸插件、备份与回滚、重启与救援、磁盘与 junction 纪律、文档落点。任务涉及改 DSH 环境、装/卸/更新插件、把东西搬到 F 盘、重启 Desktop、排查「改了不生效」时读它。 |
| `zht-project-playbook` | **智瞳灵声（CityGuardian 交管系统）项目作业手册**——端口、启动/重启脚本、配置校验三字段、素材口径、读状态的坑、CARLA 硬知识、用户红线。涉及智瞳项目、后端 8001、前端 5173、检测/测速/红绿灯/违停/事件视频，或提到「演示/管理端/标注/标定」时读它。**纯私有项目技能，对外分发无意义**。 |
| `delivery-self-review` | **交付前自审清单**——给出最终答复、写交接文档、或做完多文件/环境类改动收尾之前，逐条核对：证据等级、路径真实性、推断与事实的分界、入口链是否接上、旧字符串是否扫干净、可回滚性、给用户的操作四件套。**这条通用性最强，推荐别人抄走**。 |

## 2.2 Office 文档处理（7 个，Desktop 运行时内置）

> 装 DSH Desktop 即有；CLI 版或别的客户端未必带，需确认 `resources/runtime/office-skills` 存在。
> 共同依赖：`load_workspace_dependencies` 返回的捆绑 Python（含 python-docx / python-pptx / openpyxl 等），以及 LibreOffice Kit sidecar。

| 技能 | 功能说明 |
|---|---|
| `office` | **Office 任务总路由**。收到 Office 相关任务先加载它，由它判断该走哪个子技能；单独做渲染/导出 PDF/重算只需直接调对应操作技能。 |
| `office-docx` | **Word 文档**。创建、读取、编辑、校验 `.docx`，用 `python-docx`。 |
| `office-xlsx` | **Excel 工作簿**。读取、创建、编辑、校验 `.xlsx`，含数据与公式。 |
| `office-pptx` | **PowerPoint 演示文稿**。创建、读取、编辑、校验 `.pptx`。 |
| `office-export-pdf` | **导出 PDF**。用 LibreOffice Kit 把 Office 文档转成用户要求的 PDF。 |
| `office-render` | **渲染成图 / 版面检查**。把文档渲成图片以核对视觉版面是否错位、溢出。 |
| `office-recalculate` | **重算表格公式**。刷新电子表格的公式缓存并验证计算结果是否正确。 |

## 2.3 文档撰写、规划与工程流程（12 个）

| 技能 | 功能说明 |
|---|---|
| `doc-coauthoring` | **文档协作流程**。带你走一套结构化写作工作流，产出文档、提案、技术规格、决策文档；重点在高效转移上下文、迭代打磨、并验证「读者能读懂」。提到写文档/提案/规格/草稿时用它。 |
| `writing-plans` | **写实施计划**。手上有需求或规格、准备动代码之前，先把多步任务拆成可执行的计划文档。 |
| `executing-plans` | **执行计划**。按已写好的实施计划在新的会话里逐步落地，并在每个检查点接受复核。 |
| `brainstorming` | **创意前置探索**。**任何创作类工作之前必用**——做功能、建组件、加能力、改行为之前，先把用户意图、需求和设计探清楚，再动手实现。 |
| `test-driven-development` | **测试驱动开发**。实现任何功能或修 bug 之前，先写测试。含「测试反模式」清单。 |
| `internal-comms` | **内部沟通文案**。按公司偏好的格式写各类内部沟通：状态汇报、给管理层的更新、3P（Progress/Plan/Problem）更新、公司简报、FAQ、事故复盘、项目更新。 |
| `consulting-analysis` | **咨询级研究报告**。分两阶段：① 先出结构化分析框架（章节骨架 + 数据查询需求 + 分析逻辑）；② 数据收集完成后成稿。覆盖市场分析、消费者洞察、品牌分析、财务分析、行业研究、竞争情报、投资尽调。 |
| `security-best-practices` | **安全最佳实践审查**。按语言/框架给安全审查与改进建议。**仅支持 Python / JavaScript / TypeScript / Go**，且仅在用户明确要求安全审查时触发，不做普通代码审查。 |
| `git-commit` | **提交助手**。分析改动自动判定 type 与 scope，生成 conventional commit 消息，智能分组暂存；支持交互式补 type/scope/description。触发词含 `/commit`。 |
| `gh-cli` | **GitHub CLI 全量参考**。仓库、Issue、PR、Actions、Projects、Releases、Gist、Codespaces、组织、扩展——命令行里做 GitHub 各类操作。 |
| `writing-guidelines` | **写作规范审查**。按 Writing Guidelines 检查文档与散文：文风、语气、声音是否合规。触发词：review my docs / check writing style / audit prose / review docs voice and tone。 |
| `mcp-builder` | **写 MCP 服务器**。指导创建高质量 Model Context Protocol 服务器，把外部 API/服务包装成 LLM 可用的工具；Python（FastMCP）与 Node/TypeScript（MCP SDK）双路线。 |

## 2.4 页面、报告与演示产出（8 个）

| 技能 | 功能说明 |
|---|---|
| `doc-page` | **可打印文档页**。做报告、表单、日程、简历、备忘录、记录的精致 A4 版面，需要时可导出 PDF 或 DOCX。 |
| `report-page` | **有据可查的报告页**。产出可编辑的静态 HTML 报告/备忘录/研究笔记/运营更新/数据解读页，带干净的文档阅读体验，可选 ECharts 图表。 |
| `dashboard-page` | **本地离线 ECharts 仪表盘**。KPI 面板、时间控件、可审计的数据来源弹窗，可选由自动化产出的每日数据快照。稳定、离线可用。 |
| `slides` | **PPTX 演示文稿**。用 PptxGenJS + 捆绑版面助手 + 渲染校验做 `.pptx`：新建整套 deck、从截图/PDF/参考稿复刻、改内容且保持可编辑、加图表/图示/视觉元素、诊断版面溢出与字体替换。 |
| `ppt-page` | **网页版 PPT 画廊**。把幻灯片大纲/文章/截图/图片/现有 deck 变成单文件 HTML：垂直单列卡片流、卡片下方说明文字、全局页间距与说明开关、隐藏式缩放控件、全屏演示快捷键、悬停才出现的页码角标。 |
| `canvas-design` | **平面视觉作品**。用设计哲学做 `.png` 与 `.pdf` 的视觉艺术——海报、艺术图、静态设计稿。 |
| `theme-factory` | **主题工厂**。给各类产物（幻灯片、文档、报告、HTML 落地页等）套统一主题；内置 10 套预设配色/字体，也能现场生成新主题。 |
| `brand-guidelines` | **Anthropic 品牌规范**。把官方品牌色与字体应用到任何产物上；需要「Anthropic 风格」或公司品牌/设计标准时用它。 |

## 2.5 前端、设计与 UI 质量（12 个）

| 技能 | 功能说明 |
|---|---|
| `frontend-design` | **有辨识度的生产级前端**。做 Web 组件、页面、artifact、海报、应用（网站、落地页、仪表盘、React 组件、HTML/CSS 布局、美化现有 UI），产出有设计感、避开「AI 味」的代码。 |
| `frontend-skill` | **强视觉表达界面**。面向落地页、网站、应用、原型、演示、游戏 UI，强调克制的构图、图片主导的层级、连贯的内容结构、有品位的动效，避免满屏卡片与弱品牌感。 |
| `web-artifacts-builder` | **复杂多组件 HTML artifact**。用 React + Tailwind + shadcn/ui 等现代前端技术栈做需要状态管理、路由或组件库的复杂产物——不是给单文件简单 HTML 用的。 |
| `shadcn` | **shadcn/ui 组件管理**。加组件、搜组件、修问题、调样式、做组合；读项目上下文与组件文档；支持 registry、preset、`--preset` 代码，以及任何有 `components.json` 的项目。 |
| `ui-ux-pro-max` | **UI/UX 设计智能库**。设计与评审 Web / 移动 / 桌面界面时用（页面、组件、设计系统、可访问性、交互、响应式布局、排版、配色、图表）。本地可检索数据：79 种风格（50 种在用）、192 套产品配色与推理档、74 组字体搭配、119 条 UX 准则、105 个图标、17 个 GSAP 预设、25 种图表、22 个技术栈。 |
| `web-design-guidelines` | **Web 界面规范审查**。按 Web Interface Guidelines 检查 UI 代码：可访问性、设计审计、UX 审计、与最佳实践比对。 |
| `vercel-composition-patterns` | **React 组合模式**。重构布尔 prop 泛滥的组件、建可复用组件库、设计可扩展 API；覆盖复合组件、render props、context provider、组件架构，含 React 19 API 变化。 |
| `vercel-react-best-practices` | **React / Next.js 性能规范**（Vercel 工程团队出品）。写、审、改 React/Next.js 代码时保证最优性能模式：组件、页面、数据获取、打包优化、性能改进。 |
| `vercel-react-native-skills` | **React Native / Expo 最佳实践**。做高性能移动端：列表性能、动画（Reanimated）、图片与媒体、原生模块与字体、monorepo 结构。 |
| `algorithmic-art` | **算法艺术**。用 p5.js 做带种子随机与交互参数探索的算法艺术、生成艺术、流场、粒子系统。 |
| `figma` | **Figma 直连**。用 Figma MCP server 取设计上下文、截图、变量、资源，并把 Figma 节点翻译成生产代码；涉及 Figma URL、节点 ID、设计转代码、Figma MCP 排障时用。**需要 Figma MCP server**。 |
| `gsap` | **GSAP 动画参考**。`gsap.to/from/fromTo`、缓动、stagger、defaults、时间轴（位置参数、标签、嵌套、播放控制）、性能（transform、will-change、quickTo）。写 HyperFrames 合成时用。 |

## 2.6 数据与可视化（3 个）

| 技能 | 功能说明 |
|---|---|
| `chart-visualization` | **智能图表生成**。用户要可视化数据时，从 **26 种图表类型**里自动挑最合适的一种，按详细规格抽取参数，用 JavaScript 脚本生成图表图片。 |
| `data-analysis` | **表格数据分析**。用户上传 Excel（`.xlsx`/`.xls`）或 CSV 要做统计、汇总、透视、SQL 查询、结构化探索时用；支持多工作表、聚合、过滤、连接，结果可导出 CSV/JSON/Markdown。 |
| `json-canvas` | **JSON Canvas 文件**。创建与编辑 `.canvas`：节点、连线、分组、连接关系。做可视化画布、思维导图、流程图（Obsidian Canvas 格式）。 |

## 2.7 视频、动画与多媒体（11 个）

| 技能 | 功能说明 |
|---|---|
| `hyperframes` | **HTML 视频合成总纲**。做视频合成、动画、片头卡、叠加层、字幕、旁白、音频反应视觉、场景转场；含字幕与语音同步、文本高亮动画（马克笔扫过、手绘圈、爆裂线、涂鸦、草图）、场景间转场。 |
| `hyperframes-cli` | **HyperFrames 命令行工作流**。`npx hyperframes` 的 init / lint / inspect / preview / render，以及环境排障（doctor、browser、info、upgrade）。 |
| `hyperframes-media` | **素材预处理**。文本转语音旁白（Kokoro）、音视频转写（Whisper）、抠背景做透明叠加层（u2net）；也讲怎么把三者串起来（TTS → 转写 → 字幕）。**每个命令首次运行会各自下载模型**。 |
| `hyperframes-registry` | **registry 区块与组件**。`hyperframes add` 安装区块/组件、接到 `index.html`、处理 `hyperframes.json`；含安装位置、子合成接线、组件片段合并、registry 发现机制。 |
| `byted-seedance-video-generate` | **Seedance 视频生成**（火山引擎）。从文本提示、图片或参考素材生成视频。 |
| `byted-seedream-image-generate` | **Seedream 图像生成**（火山引擎）。从文本提示生成高质量图片，支持多种艺术风格与宽高比。 |
| `byted-mediakit-shared` | **mediakit-cli 音视频处理**。音频/视频加工、剪辑、图像处理；部分能力同时支持云端与本地模式；含环境检查、初始化配置、命令结构、鉴权配置、异步任务响应与错误处理。 |
| `hook-analyzer` | **视频前三秒钩子分析**。从分镜拆解结果里提取前三秒分镜数据，为「钩子吸引力」评估提供结构化上下文。跑 `scripts/analyze_hook_segments.py`，输出前三秒分镜数量、总时长、每个分镜详情（含关键帧 URL）。 |
| `report-generator` | **视频分析报告生成**。整合分镜拆解数据 + 钩子分析结果，产出 Markdown 专业分析报告：基本信息、前三秒钩子分析、分镜概览、BGM 分析、场景分析。跑 `scripts/generate_report.py`。 |
| `douyin-interact-creation` | **抖音互动空间 H5 创作**。做或升级 `interact_creation` 离线 H5 体验：单文件 `index.html` 或可上传的 `.zip`，**零网络依赖**。 |
| `douyin-interactive-content-publish` | **抖音互动空间一键发布**。上传 zip + 图标创建/更新互动空间应用，自动生成名称与描述。触发词：发布/提交/上传互动空间、一键发布、上传游戏包、提审。 |

## 2.8 浏览器、桌面与测试自动化（5 个）

| 技能 | 功能说明 |
|---|---|
| `agent-browser` | **浏览器自动化 CLI**。开网页、填表单、点按钮、截图、抓数据、测 Web 应用、自动化任何浏览器任务。**需先装 `npm i -g agent-browser` 并跑 `agent-browser install` 下载 Chrome**。 |
| `webapp-testing` | **本地 Web 应用测试**。基于 Playwright：验证前端功能、调试 UI 行为、截浏览器图、看浏览器日志。**需 Playwright**。 |
| `dogfood` | **系统性找茬（QA）**。系统探索并测试一个 Web 应用找 bug、UX 问题；产出带完整复现证据的结构化报告——逐步截图、复现视频、详细复现步骤，可直接交给责任团队。**基于 agent-browser**。 |
| `electron` | **Electron 桌面应用自动化**。通过 Chrome DevTools Protocol 用 agent-browser 操控 VS Code、Slack、Discord、Figma、Notion、Spotify 等桌面应用：连接运行中的应用、控制原生应用、测 Electron 应用。**基于 agent-browser**。 |
| `screenshot` | **系统截图**。用户明确要桌面/系统截图（全屏、指定应用或窗口、像素区域）时用；或工具级截图能力不可用、需要操作系统级抓屏时用。 |

## 2.9 知识库：Notion 与 Obsidian（8 个）

> **Notion 系 5 个**共用前置：`npm i -g ntn@latest`（Notion CLI）或对应 MCP。
> **Obsidian 系 3 个**需要本机装 Obsidian CLI。

| 技能 | 功能说明 |
|---|---|
| `notion-cli` | **Notion CLI（`ntn`）**。调 Notion API、管理 worker、上传文件、建页面、查数据库；任何涉及 `ntn` 命令的任务。CLI 自文档化——优先 `ntn api ls` / `--help` / `--docs` / `--spec` 现场查，别靠记忆。 |
| `notion-knowledge-capture` | **对话转知识页**。把聊天里的讨论与洞察整理成结构化 Notion 页面：提炼观点与决策，按规范排版，存进 wiki 或数据库并做好分类与互链，方便日后检索。 |
| `notion-meeting-intelligence` | **会议材料准备**。从 Notion 收集上下文、补充调研，产出「对内预读」+「对外议程」两份文档并存回 Notion。 |
| `notion-research-documentation` | **Notion 内研究成稿**。跨工作区搜索多个页面，综合成一份完整研究报告存为新页面——把散落信息变成带引用、可执行的结构化报告。 |
| `notion-spec-to-implementation` | **规格转任务**。把产品/技术规格页拆成 Notion 里可执行的具体任务：实施计划、清晰任务、验收标准、进度跟踪。 |
| `obsidian-cli` | **Obsidian 命令行**。读/建/搜/管笔记、任务、属性；也支持插件与主题开发（重载插件、跑 JavaScript、抓错误、截图、查 DOM）。 |
| `obsidian-bases` | **Obsidian Bases（`.base`）**。建改视图、过滤、公式、汇总；做数据库式笔记视图、表格视图、卡片视图。 |
| `obsidian-markdown` | **Obsidian 风格 Markdown**。wikilink、嵌入、callout、属性（properties）等 Obsidian 特有语法。 |

## 2.10 部署与云服务（2 个）

| 技能 | 功能说明 |
|---|---|
| `iga-pages` | **IGA Pages 部署**。部署前端与全栈项目：预览部署、一键上线拿链接、写 API 与后端服务。触发词：deploy / publish / push live / 部署到 IGA Pages。 |
| `byted-bp-cdn-pagesdeploy` | **字节 BytePlus Edge Pages 部署**。一键把静态站部署到 BytePlus Edge Pages：自动建项目、更新部署、绑自定义域名、CDN 加速；**给没有 BytePlus 账号的新用户带引导**。 |

## 2.11 支付接入（2 个）

| 技能 | 功能说明 |
|---|---|
| `alipay-payment-integration` | **支付宝接入**。全场景产品选型与集成指导：当面付、订单码、App 支付、JSAPI、手机网站、电脑网站、预授权、商家扣款。覆盖 SDK 选择（通用版/Easy 版）、加签方式、代码示例。⚠ 文档为在线动态链接，接入前需先抓最新在线文档。 |
| `douyinpay-payment-integration` | **抖音支付接入**。端到端：产品选型（APP/JSAPI/H5/Native）、前置准备、服务端 SDK（Go/Java/PHP）、签名验签、代码生成、接入质量校验；含退款、账单、回调通知、证书管理、错误码排查。自带 `search_docs.sh` 文档检索。 |

## 2.12 其他实用工具（3 个）

| 技能 | 功能说明 |
|---|---|
| `defuddle` | **网页正文提取**。用 Defuddle CLI 从网页抽干净 Markdown，去掉导航与杂项以省 token。**用户给 URL 要读要分析时优先用它代替 WebFetch**。需 `npm i -g defuddle`。 |
| `redis-development` | **Redis 最佳实践**。数据结构、Redis Query Engine（RQE）、RedisVL 向量搜索、LangCache 语义缓存、性能优化。 |
| `天眼一下` | **天眼查企业数据查询**（⚠ **当前未生效**）。用本地 `tyc` 命令查企业主体核验、合作方/客户/供应商风险、股东与实控人、受益所有人、关联关系、司法诉讼、执行失信、行政处罚、经营真实性、招投标、资质许可、知识产权、董监高、历史沿革、行业企业发现、商查摘要。需 `npm i -g tyc-cli` + `tyc login`。**因 `name` 是中文不符合 kebab-case，DSH 未加载它**；要用得先把 name 改成英文短横线格式。 |

---

# 第三部分：给另一位用户的安装指引

## 3.1 插件怎么装

**路线 A · 图形界面（推荐，尤其桌面版）**
打开 DSH 侧边栏 → **Plugins** 页 → 搜索包名 → 安装 → 按提示重启。
若已装 `dshmarket`，也可以直接用它逛市场、点一下装。

**路线 B · 命令行（仅限非桌面 profile）**
```
npm install <包名>
```
⚠ 桌面版 `dsh plugin --profile desktop` 会被**硬编码拒绝**，必须走 GUI。

**装完不生效的三步排查**
1. 包里有 `dsh.bundle.patch` 吗？没有 → 得手工挂 `cordis.patch.yml`。
2. 改的是 `cordis.patch.yml` 而不是 `cordis.yml` 吗？
3. 是启动级配置吗？是 → 重启 Desktop。

**本清单里需要额外准备外部程序的插件**

| 插件 | 额外依赖 |
|---|---|
| `@deepseek-ai/dsh-experimental-computer-use-cua-driver-mcp` | `cua-driver.exe`（独立可执行文件，通过 stdio MCP 连接）；本机版本 v0.28.0，路径 `C:\Users\ROG\.local\bin\cua-driver\cua-driver.exe` |
| `dsh-plugin-wallpaper-engine` | 内核 ≥ 0.1.5；本机壁纸来 Wallpaper Engine 安装 |
| `dsh-connect-workbuddy` | 本机需已登录 WorkBuddy 客户端 |

## 3.2 技能怎么装

技能**不是 npm 包**，就是一个目录：

```
<技能池>/<技能目录>/
  SKILL.md          ← 必需，frontmatter 要有 name + description
  scripts/ ...      ← 可选，技能自己的脚本
  references/ ...   ← 可选，参考文档
```

**落地位置**（按作用域选一个）：
- 全局共享池：`~/.agents/skills/`（本机 66 个有效技能在这，多款 AI 工具共用）
- DSH 专属：`~/.dsh/skills/`（本机 3 个自建技能在这）

**三条硬性规则**
1. `SKILL.md` 的 frontmatter `name:` **必须是 kebab-case**（本机 `天眼一下` 就因此失效）。
2. 必须能解析出 `description`，否则不出现。
3. 技能**热加载**——放进去，下个会话就能用，不用重启。

## 3.3 这 76 个技能的来源，别人去哪拿

| 来源 | 技能 | 获取线索 |
|---|---|---|
| **Anthropic 官方技能集** | canvas-design、brand-guidelines、algorithmic-art、theme-factory、slides、internal-comms、mcp-builder、web-artifacts-builder、webapp-testing、frontend-design、figma、screenshot、security-best-practices 等（目录内含 `LICENSE.txt`） | Anthropic 官方 skills 仓库 |
| **Vercel 工程技能** | `vercel-composition-patterns`、`vercel-react-best-practices`、`vercel-react-native-skills`（目录名分别是 composition-patterns / react-best-practices / react-native-skills，含 `metadata.json` 标注 author=vercel、version 1.0.0） | Vercel 官方技能仓库 |
| **Notion 官方技能** | `notion-*` 五个（目录名 knowledge-capture / meeting-intelligence / research-documentation / spec-to-implementation） | Notion 官方 / MCP 生态 |
| **字节系（ByteDance / 火山引擎 / 抖音）** | byted-* 三个、douyin-* 三个、douyinpay-payment-integration | 火山引擎 / 抖音开放平台 |
| **支付宝** | alipay-payment-integration | 支付宝开放平台 |
| **第三方开源** | agent-browser、defuddle、hyperframes-*、ui-ux-pro-max、chart-visualization、dashboard-page、report-page、doc-page、ppt-page、apify 系等 | 各自 npm / GitHub |
| **Obsidian 社区** | obsidian-cli、obsidian-bases、obsidian-markdown、json-canvas | Obsidian 社区生态 |
| **本机自建** | dsh-delegation-channels、dsh-office-ops、zht-project-playbook、delivery-self-review | **无外部来源，需向作者索取**；且前三个含本机专有路径，别人必须改写 |

> **诚实提醒**：这 76 个技能里，**只有 4 个是本机原创**，其余都是公开技能集的集合。别人不必「下载我们的技能」，按上表去各家官方仓库取同款更靠谱。真正值得参考的是**我们怎么组织它们**（分类、池位置、常驻指令配合），以及 `delivery-self-review` 这类自建清单。

## 3.4 技能与外部 CLI 的依赖对照

装技能前先备好这些外部命令，否则技能里写的命令跑不起来：

| 技能 | 需要的外部命令 |
|---|---|
| `agent-browser` / `dogfood` / `electron` | `npm i -g agent-browser` + `agent-browser install` |
| `webapp-testing` | Playwright |
| `defuddle` | `npm i -g defuddle` |
| `gh-cli` | `gh` |
| `notion-cli` | `npm i -g ntn@latest` |
| `shadcn` | `npx shadcn@latest`（按需） |
| `hyperframes` / `-cli` / `-media` | `npx hyperframes` |
| `byted-mediakit-shared` | `npm i -g @volcengine/mediakit-cli` |
| `iga-pages` | `npm i -g @iga-pages/cli@latest` |
| `天眼一下` | `npm i -g tyc-cli` + `tyc login` |
| `office-*`（7 个） | DSH 捆绑 Python + LibreOffice Kit sidecar |
| `mcp-builder` | `npx @modelcontextprotocol/inspector`（联调时） |

---

## 附：本清单的核对边界

| 项 | 是否核实 |
|---|---|
| 插件包名、版本、描述 | ✅ 逐个读 `node_modules/<包>/package.json` |
| 哪些插件有 `dsh.bundle.patch` | ✅ 读 `package.json` 的 `dsh` 字段 |
| 手工挂载项 | ✅ 读 `cordis.patch.yml` 的 `insert` 块与 `disabled` 标记 |
| 技能目录数与 frontmatter | ✅ 逐个读 `SKILL.md` 头部 |
| 「67 个目录 → 66 个有效」 | ✅ 会话技能目录实收 76 = 66 + 3 + 7，`天眼一下` 缺席 |
| 各技能外部 CLI 依赖 | ⚠ **部分**——只抓了 SKILL.md 里显式出现的 `npm i` / `npx` / `pip install` 行，未逐条实跑验证 |
| 插件功能描述 | ⚠ 取自各包自己的 `description` 字段，**未逐个实测行为** |
