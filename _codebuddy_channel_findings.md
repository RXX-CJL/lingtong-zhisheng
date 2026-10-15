# CodeBuddy CLI 通道打通 — 阶段性发现（事实落盘，R1）

- **时间**：2026-10-16 00:5x（会话开工 30 分钟内）
- **状态**：根因已定位（三级证据），**待执行登录**；执行前需文件策略提权
- **证据来源**：CodeBuddy CLI **自己写的日志**（非推断）

---

## 1. 根因（三级证据链）

日志文件：`C:\Users\ROG\.codebuddy\logs\2026-10-15\output__402116e503f05353ea0e7c738483ca0d.log`
（文件名日期 10-15，内容实际是 **2026/10/16 00:50:27 ~ 00:51:23**，三个 PID 连续尝试：21992 / 28868 / 30940）

| # | 时刻 | 原始证据 | 含义 |
|---|---|---|---|
| ① | — | `C:\Users\ROG\.codebuddy\auth\` **目录不存在**（glob 返回 No files found） | CLI **从未**成功保存过凭据 |
| ② | 00:51:00.432 | `[AuthDoInitProbe] stage=afterRestore ... hasSession=true hasAccessToken=false` | 会话记录在，**access token 不在** |
| ③ | 00:51:00.432 | `stage=fastPathBeforeEmit ... uid=b9969747-4a6c-4adf-aab2-873689715ed5 hasAccessToken=false` | uid **与 WorkBuddy 桌面端登录账号一致** |
| ④ | 00:51:00.432 | `[AuthRefresh] started: trigger=immediate` | 自动尝试刷新 |
| ⑤ | 00:51:01.994 | `[AuthenticationManager] [AxiosError: Request failed with status code 401] [AuthRefresh] failed: kind=transient, durationMs=1565, retry=false, sessionPreserved=true` | **刷新被 401 拒绝，且不重试** |
| ⑥ | 00:51:02.008 | `AuthenticationRequiredError: Authentication required. Please use /login command to sign in to your account` | **最终结果：必须 /login** |
| ⑦ | 00:50:27.523 | `[CredentialBootstrap] CBC receiver {... "route":"standalone","policy":"unset","readyConfig":"disabled", ... "runtimeStatus":"disabled","wholeFileProtectionReady":false}` | **桌面端凭据注入通道是 disabled** → CLI 拿不到桌面端登录态（与旧结论一致） |
| ⑧ | 00:50:27.523 | `[FileAuthenticationStorage] [AtRestEncryption] unavailable adapter=credential-fields resource=auth/workbuddy-desktop.info operation=read category=missing-key role=cbc; continuing` | 凭据文件 = `~\.codebuddy\auth\workbuddy-desktop.info`，**missing-key** |

**一句话根因**：`~\.codebuddy\auth\workbuddy-desktop.info` 不存在（从未生成）+ 桌面端 CredentialBootstrap 为 disabled
→ CLI 无 token 可刷新 → 401 → 要求 `/login`。

**排除项（都已正常，别再排查）**：
- ✅ 代理：`[ProxyResolver] OS proxy detected: 127.0.0.1:7897 bypass=[...]`（Clash 混合端口，正常）
- ✅ 网络端点：`endpoint=https://www.workbuddy.cn`，`[ModelsProductProvider]`、`[GalileoService]` 均正常解析
- ✅ 参数/启动：`-p` 与交互式都能正常启动、正常退出（`ProcessExit exit | code=0`）
- ✅ 桌面端登录态：uid `b9969747-…` 被 CLI 正确识别（只是没有 token）

**噪音（不影响主因，勿误判）**：日志里几十条 `[cbc-kw=AUTH] Failed to read settings file for scope user: ENOENT`，属 settings 文件缺失告警。

---

## 2. 已探明的 CodeBuddy CLI 事实

| 项 | 值 | 来源 |
|---|---|---|
| 启动器 | `E:\output\_tools\codebuddy.cmd`（已存在，内含必需环境变量 `CODEBUDDY_FORCE_LITE_WB_BUNDLE=1`） | 文件直读 |
| 真实 CLI 入口 | `F:\AI\WorkBuddy\resources\app.asar.unpacked\cli\bin\codebuddy` | 启动器内容 |
| 包身份 | `@genie/agent-cli`；**npm 发布名 = `@tencent-ai/codebuddy-code`，版本 `2.161.0`** | `cli\package.json` 的 `publishConfig.customPackage` |
| 本机 variant | 只有 `dist\codebuddy-lite-wb.mjs`（故必须设 FORCE 变量） | 旧结论 + 启动器注释 |
| 认证类型 | `account-scoped-external-link`，label `TencentCloud`，`tokenHeader=Authorization`/`bearerToken`，`platform=workbuddy`，`prefixPath=/plugin` | `cli\product.json` 的 `authentication` 段 |
| 端点 | `https://www.workbuddy.cn`（official 列表含 `copilot.tencent.com`、`www.codebuddy.ai` 等） | `cli\product.json` |
| 可用模型（部分） | `auto`(默认) / `deepseek-v4.1-flash` / `deepseek-v4-pro` / `glm-5.3(-flash/-flashx)` / `kimi-k3-2` / `kimi-k2.8-preview` / `minimax-m3-pay` / `hy4-preview` / `hy3-x`… | `cli\product.json` 的 `models` |
| 功能开关（服务端下发） | `Skills=true`、`WebSearch=true`、`WebFetch=true`、`Task=true`、`ImageGen=true`、`VideoGen=true`、`ScheduledTasks=true`、`MemoryManagement=true`、`InternationalLogin=true`、`SwitchBySession=true`；`SkillManage=false` | 日志 line 124 |
| 本机会话记录 | `~\.codebuddy\projects\e-output\01a14079-6c3e-703d-b8fd-71e269e5b33e.jsonl`（工作区 `e:\output`，昨晚 00:50 那轮） | 目录探查 |

---

## 3. 下一步（按顺序）

1. **提权**：文件策略 `workspace-write` → `danger-full-access`
   （理由：踩坑 #10 —— 受限策略下 pwsh 一律 `0xC0000142`，没有 shell 就无法执行任何 CLI 命令）
2. **跑一次性登录**：`codebuddy.cmd` 交互式 → `/login`（需确认是否需要你在浏览器点授权）
3. **验证（三级证据）**：非交互派活 `codebuddy.cmd -p "..."` → 期望 exit 0 + 真实回答
4. 通过后，把 `codebuddy.cmd` 升级为正式派活工具（对齐 codex 的用法：`-s`/`-C`/`--output-format json`）

## 4. 未定项

- `/login` 的确切形态（纯终端 / 浏览器 OAuth 回调）→ 提权后跑一次就知道了
- 是否有 API key 直连旁路（用户侧信息，已询问）

---

## 5. 环境阻碍（本轮实测）

| 项 | 结果 |
|---|---|
| `pwsh -Command "$PSVersionTable..."` | **`[exit code: 3221225794]`** = `0xC0000142`（DLL 初始化失败） |
| 判据 | 与状态文件**踩坑 #10** 完全一致：受限文件策略下沙箱注入层失败，与 pwsh 本身无关 |
| 影响 | 本轮**无法执行任何 shell 命令**（node / npm / CLI 全部不可用），只能做只读文件工作 |
