# DSH 办公室 — 状态与操作手册（单一事实源）

> **用途**：DSH 会话没有持久记忆。这份文件就是我的"长期记忆"。
> **新会话开工第一件事：读这个文件**，不要重新摸索、不要重复踩坑。
> **最后更新**：**2026-10-12（工作室升级轮）** —— 本轮改写了头部 + §5（新增踩坑 #10）+ §9（标注作废），并在文末新增 **§26**（全部新事实）。
> ⚠ **§1、§2、§3 的旧数字已作废**（运行时写 0.1.7-rc.2、技能写 78、插件表缺 4 个）—— **一律以 §26 为准**；§4、§6~§8、§10~§25 仍是 2026-09-27 ~ 10-03 的旧内容，引用前先核对。
> **维护约定**：每次改动办公室后更新本文；事实变更就改，不要另建文件。
> **共同规则（2026-10-12 起）**：所有 AI 共用的协作规则、暂定分工与权限边界在 `E:\output\_AI_COMMON_RULES.md` —— **开工先读它**，再读本文。

---

## 0. 三条硬约束（来自用户，不可违反）

1. **绝不修改** `C:\Users\ROG\.dsh\profiles\web`（旧 Web 备用环境，保持可用）。
2. **绝不修改** `E:\deepseek-harness`（DSH 源码仓库，只读）。
3. **所有安装目标都是 Desktop Profile**：`C:\Users\ROG\.dsh\profiles\desktop`。

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
| 本机硬件 | **Intel Core i9-14900HX（Raptor Lake）**，`platform.exe --is-aipc` → **0**（不是 AIPC，无 Intel NPU） |

---

## 2. 已装插件（Desktop Profile）

`package.json` 的 `dependencies` + `dsh.profile.bundles`：

| 组件 | 版本 / commit | 状态 |
|---|---|---|
| `dsh-workshop` | `github:loguhan/dsh-workshop#cf36f61f708100d9f2c67db3a1722a8b85b53757` | ✅ 创意工坊（侧边栏可用） |
| `@liustack/modlens` | `3.26.5`（npm） | ✅ 工具 `modlens_read_image` 已注册；**还需配视觉引擎** |
| `@liustack/modsearch` | `5.10.5`（npm） | ✅ 工具 `read_page` / `x_search` 已注册 |
| `dsh-whale-widget` | `github:MeteorNOX/DeepSeek-Balance-Whale-Widget#e8c107be8...`（= v0.3.16） | ✅ 已安装（挂件需重启 Desktop 才可见） |

**注意**：Desktop Profile 里还有两个 Desktop 自加的 bundle：`@deepseek-ai/dsh-experimental-auto-review`、`@deepseek-ai/dsh-experimental-agent-team-profile`（不是第三方）。

**安装途径（唯一可用）**：桌面**侧边栏 → Plugins（插件）页**。
> CLI **不可用**：`dsh plugin --profile desktop …` 会被硬编码拒绝
> （`apps/cli/src/args.ts:83` `rejectElectronProfile` → *"profile desktop is managed exclusively by the Electron application"*）。

**已应用的两处本地补丁（会随重装失效，需重打）**：

| 文件 | 补丁 | 备份 | 重打命令 |
|---|---|---|---|
| `profiles\desktop\node_modules\dsh-workshop\lib\client.js` | 中央列选择器补 `centerCol`（DSH 0.1.7 把 `[data-pane="conversation"]` 换成 CSS Module `*_centerCol`，否则面板不挂载） | `client.js.pre-patch` | `E:\node.exe E:\output\dsh-workshop-desktop-patch\patch-client.mjs C:\Users\ROG\.dsh\profiles\desktop` |

补丁后 `client.js` = 60252 字节 / SHA256 `4921B40E3B905020…`（与旧 Web Profile 已验证版一致）。

---

## 3. 共享技能池（核心资产）

**位置**：`C:\Users\ROG\.agents\skills\`
**为什么是这里**：`skill-filesystem` 的用户级根之一（另一根是 `C:\Users\ROG\.dsh\skills`，当前不存在）。**运行时热加载**——新增技能无需重启 Desktop，实测目录会实时刷新。

**来源与方式**：
- 用 **junction** 链接 `C:\Users\ROG\.trae-cn\skills\*`（Trae 用户级技能池）→ Trae 更新即同步，零副本。
- 例外：`dashboard-page` / `doc-page` / `ppt-page` 用**真实副本**（见"踩坑 #4"）。
- 上游独立安装的 3 个：`ui-ux-pro-max`（`nextlevelbuilder/ui-ux-pro-max-skill@823b0a14d3`，73 文件）、`web-design-guidelines`、`writing-guidelines`（均 `vercel-labs/agent-skills@063bee94c3`）。

**规模**：**66 条**（★2026-10-12 实测定案；本行旧值"约 78"是错的）+ 自建 1 条 = **67**，见 **§26.1 / §26.7**。

**已剔除（不要重新链回来）**：`local-asr`、`local-computer-use`、`local-img2img`、`local-mineru`、`local-ocr-npu`、`local-realtime-translator`、`local-screenshot-qa`、`local-tts`、`local-txt2img`、`local-vram`
→ 原因：**本机非 Intel AIPC**，`platform.exe --is-aipc` 返回 0，这些技能首行校验就 `exit 1`。它们依赖 cp311 wheel + Intel NPU + 约 3 GB 模型，本机无法使用。**不要误以为我有本地 OCR/视觉/计算机操作能力。**

**当前刻意未装**（与 DSH 内置重复）：`search`（= 我的 grep/glob/read）、`general_purpose_task`（= `subagent`）。

---

## 4. 工具链现状

| 工具 | 状态 | 说明 |
|---|---|---|
| ffmpeg / ffprobe | ✅ 已可用 | shim 在 `C:\Users\ROG\.local\bin\{ffmpeg,ffprobe}.cmd`，指向 Playwright 自带静态构建 `%LOCALAPPDATA%\ms-playwright\ffmpeg-1011\ffmpeg-win64.exe`（n7.0.1）。**零下载**。注意该目录只有 ffmpeg，`ffprobe.cmd` 指向的 `ffprobe-win64.exe` 可能不存在 → 用到 ffprobe 时先验证 |
| gh | ✅ 2.101.0 | winget 安装到 `C:\Program Files\GitHub CLI\gh.exe`；因注册表 PATH 需重启进程才生效，另建 shim `C:\Users\ROG\.local\bin\gh.cmd` 桥接。**尚未 `gh auth login`** |
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
| 6 | `gh auth login` | 需用户交互 |
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

### 26.1 环境事实（一级证据：`dsh-office.ps1` → `ok=45 warn=2 fail=0`）

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
