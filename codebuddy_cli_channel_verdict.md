# CodeBuddy CLI 派活通道 — 打通结论（verdict）

- **日期**：2026-10-16（凌晨 00:55 开工 → 01:15 打通，约 20 分钟）
- **会话**：本会话（DSH Desktop，文件策略已提权为 `danger-full-access`）
- **一句话结论**：**CodeBuddy CLI 第三条 AI 派活通道已打通并三级验证通过**（`codebuddy -p "…"` → exit 0 / 12.7 秒 / 真实回答）。根因不是网络、不是代理、不是端口，而是 **CLI 侧从来没有自己的登录凭据**；完成一次官方 `/login`（Chinese Site）后凭据落盘，有效期至 **2026-11-13**。

---

## 1. 最终可用状态（三级证据）

| 项 | 值 | 证据等级 |
|---|---|---|
| 可执行 | `codebuddy -p "…"`（全局 npm 包） | 一级（命令结果） |
| TEST A：默认派活 | `Reply with exactly: CBC_CHANNEL_OK` → **`CBC_CHANNEL_OK`**，exit **0**，**12.7 秒** | 三级（真实行为） |
| TEST B：只读+JSON | 问".md 文件数量" → **`45`**（真的调用了 `Glob` 工具扫盘）；exit 0、26 秒、8 turns、input 29,239 token | 三级（真实行为） |
| TEST C：指定模型 | `--model deepseek-v3-2-volc` → **`MODEL_OK`**，exit 0，6.4 秒 | 三级（真实行为） |
| 凭据落盘 | `%LOCALAPPDATA%\CodeBuddyExtension\Data\Public\auth\Tencent-Cloud.coding-copilot.info`（3479 B, 01:14:06） | 二级（文件状态） |
| 有效期 | `expiresAt = 1794503645581` → **2026-11-13 01:14:05**；scope 含 `offline_access`（可刷新） | 二级 |

**工具**：`E:\output\_tools\codebuddy.ps1`（参数：`-Prompt` `-Model` `-Json` `-WorkDir` `-Effort` `-ReadOnlyTools` `-TimeoutSec`）

---

## 2. 根因链（全部来自 CodeBuddy CLI **自己写的日志**与二进制内字符串）

### 2.1 现象
```
codebuddy -p "任务"  →  Authentication required. Please use /login command to sign in to your account
```

### 2.2 真实根因（分三层，逐层排除）

| 层 | 观察 | 结论 |
|---|---|---|
| 网络/代理 | `[ProxyResolver] OS proxy detected: 127.0.0.1:7897`、`endpoint=https://www.workbuddy.cn` 均正常解析 | ❌ 不是网络问题 |
| 会话 vs 凭据 | `[AuthDoInitProbe] stage=afterRestore hasSession=true hasAccessToken=false`；`uid=b9969747-…` | 会话在、**凭据不在** |
| 刷新结果 | `[AuthRefresh] failed: [AxiosError: ... status code 401]`、`retry=false, sessionPreserved=true` | 无 token 可刷新 |
| **凭据存储** | `~\.codebuddy\auth\` **不存在**；而 `%LOCALAPPDATA%\CodeBuddyExtension\Data\Public\auth\` 下**只有桌面端的 `workbuddy-desktop.info`** | **CLI 侧从未登录过** |
| 桌面端注入 | `[CredentialBootstrap] route:"standalone", policy:"unset", runtimeStatus:"disabled"` vs 桌面端 daemon `policy:"fields", runtimeStatus:"ready"` | 桌面端**设计上不**把凭据给独立 CLI |

**一句话根因**：桌面端（provider `workbuddy-desktop`）与 CLI（provider `Tencent-Cloud.coding-copilot`）是**两套独立凭据**；独立运行的 CLI 既没有自己的凭据，也不会拿到桌面端那把 at-rest 钥匙（`credentialProtectionBootstrap.symmetricKey` 只经 sidecar socket 下发，不落盘）。

### 2.3 曾被误判/需更正的点
- ❌ "CLI 凭据存在 `~\.codebuddy\auth\`" —— **错**。真实位置是 `%LOCALAPPDATA%\CodeBuddyExtension\Data\Public\auth\`（与桌面端同目录、**不同文件名/provider**）。
- ❌ "桌面端登录态不共享给 CLI" —— 表述不准。准确说法：**共享同一个 `auth` 目录，但各用各的 provider 条目**；桌面端的 `workbuddy-desktop.info` 对本 CLI 无意义。
- ⚠️ 本机 WorkBuddy 内嵌的 `lite-wb` 变体被设了 `CODEBUDDY_FORCE_HEADLESS_BUNDLE=1`，**没有 TUI**（所以没有 `/login` 入口）→ 必须用 **npm 官方完整包**。

---

## 3. 打通步骤（可复现）

```powershell
# 1) 装官方完整包（本机 2.168.0；内嵌的 lite-wb 无 TUI）
npm install -g @tencent-ai/codebuddy-code@latest

# 2) 在真实终端（有 TTY）里跑一次，完成登录
codebuddy
#   首次会问 "Do you trust the files in this folder?" → 回车选 1（信任 E:/output）
#   然后输入：/login
#   选择：Log in via Chinese Site（默认高亮，直接回车）
#   浏览器完成腾讯账号授权（uid b9969747-…，桌面端同一账号）

# 3) 验证
codebuddy -p "Reply with exactly: CBC_CHANNEL_OK"
```

**登录过程的日志铁证**：
```
01:11:33 [AuthenticationManager] [487265362d74a634f8591d3ab76176c4] Start login...
01:11:33 [ExternalLinkAuthenticationProvider] Opening auth URL:
         https://copilot.tencent.com/login?platform=CLI&state=a401f1c6-…&version=2.168.0
01:12:12 [CloudPreProductProvider] remote config became loadable (first login), triggering product sync
01:12:12 [AuthRefresh] skipped: reason=success-cooldown, remainingMs=29975     ← 不再是 401
```

---

## 4. 能力与用法（实测）

| 能力 | 用法 | 备注 |
|---|---|---|
| 非交互派活 | `codebuddy -p "任务"` | 等价 `codex exec` |
| 结构化输出 | `--output-format json`（还有 `stream-json`） | 返回 `result`/`num_turns`/`duration_ms`/`usage`/`session_id`/`total_cost_usd` |
| **模型可选** | `--model auto\|glm-5.1\|glm-5v-turbo\|glm-5.0(-turbo)\|glm-4.7\|kimi-k2.5\|minimax-m2.7\|deepseek-v3-2-volc` | 免费档实际可选 9 个（`--help` 为准） |
| 推理强度 | `--effort minimal…max` | 6 档 |
| 工具集收窄 | `--tools "Read,Grep,Glob"` | ⚠️ 收窄过头会让它想用 Bash 时被拒（实测报 `Tool "Bash" does not exist in the current tool set`） |
| 权限 | `-y/--dangerously-skip-permissions`、`--permission-mode`、`--allowedTools/--disallowedTools` | |
| 后台会话 | `--bg` + `ps/attach/logs/kill` | |
| 服务化 | `--serve`（Web UI + REST API + ACP/SSE）、`--acp` | |
| 会话管理 | `-c`（续最近）、`-r <id>`、`--session-id` | |
| 结构化校验 | `--json-schema` | |

**分工建议（与 Codex CLI 互补）**：
- **Codex CLI** → `gpt-5.6-luna`（ChatGPT 账号额度）
- **CodeBuddy** → 多模型（GLM / Kimi / MiniMax / DeepSeek-V3.2 / 混元），**可按任务切换第二意见**
- 派活工具：`E:\output\_tools\codebuddy.ps1`

---

## 5. 被推翻 / 更正的旧结论

| 旧结论（`_DSH_OFFICE_STATE.md` §1.2） | 现结论 |
|---|---|
| "CLI 侧未登录 → `-p` 返回 Authentication required" | ✅ 仍成立，但**已解决**：完成一次官方登录即可 |
| "桌面端登录态**不共享**给 CLI" | **需精确化**：两者**共用** `%LOCALAPPDATA%\CodeBuddyExtension\Data\Public\auth\` 目录，但各用**独立 provider 条目**（`workbuddy-desktop` vs `Tencent-Cloud.coding-copilot`）；桌面端条目对 CLI 无效 |
| 隐含："修 CLI 得复用它桌面端的凭据" | **错**。正确路径是让 CLI **自己登录一次**，不必（也无法）解密桌面端凭据 |
| 旧启动器 `E:\output\_tools\codebuddy.cmd`（指向 WorkBuddy 内嵌 lite-wb） | **已不足**：该变体被强制 headless（`CODEBUDDY_FORCE_HEADLESS_BUNDLE=1`）、无 TUI、无 `/login`。改用 npm 官方包 + `codebuddy.ps1` |

---

## 6. 副产品：摸清的 WorkBuddy 内部机制（供以后参考）

| 机制 | 事实 |
|---|---|
| 进程树 | `28640 WorkBuddy.exe`（主）→ `3288 daemon-app-server-entry.js --stdio`（daemon）→ `2740 WorkBuddy.exe …cli\bin\codebuddy --prewarm --prewarm-id wb-pool-…`（CLI sidecar 池，pool_size=1） |
| at-rest 加密 | `keyblob`（336 B）→ `{version:1, keyId, slots:[{type:"static-v1", protectorKeyId, wrapped}]}`；`keyId = sha256(masterKey).hex[:16]`；加密 = `aes-256-gcm`，envelope `{suite,keyId,nonce,authTag,ciphertext}` |
| 钥匙来源 | 随机 32 字节主密钥，经 **Electron 主进程 → sidecar socket** 下发（`CODEBUDDY_SIDECAR_CREDENTIAL_BOOTSTRAP_SOCKET`）；**不落盘、无 DPAPI**（bundle 内 `CryptUnprotectData`/`dpapi` 零命中） |
| 策略开关 | `WORKBUDDY_AT_REST_ENCRYPTION=off\|fields\|files` |
| 桌面端凭据 | `workbuddy-desktop.info`：明文 `uid`/`uin`，`accessToken`/`refreshToken` 等标 `$wbEncrypted` 加密；有效期至 2026-11-12 |
| 活着的命名管道 | `\\.\pipe\codebuddy-prewarm-wb-pool-1792083187767-5ded9b`（prewarm CLI）、`\\.\pipe\wbipc-…`、`\\.\pipe\workbuddy-pac-3288-…`（`WORKBUDDY_PAC_RPC_TOKEN`） |
| prewarm 派活协议 | 私有 ndjson + 激活协调器，**未逆向**（性价比低，走官方 CLI 更快） |

⚠️ **安全提示**：`~\.workbuddy\keyblob` 与 `CodeBuddyExtension\…\auth\*.info` 是凭据资产，**不要外传、不要提交到仓库**。本次全程只在本机读写，未外发。

---

## 7. 复现与验证脚本

```powershell
# 通道健康检查（秒级）
codebuddy -p "Reply with exactly: CBC_CHANNEL_OK" --output-format text

# 经封装工具派活
pwsh -NoProfile -File E:\output\_tools\codebuddy.ps1 -Prompt "用一句话说明 CARLA 是什么"

# 指定模型 + JSON（含用量）
pwsh -NoProfile -File E:\output\_tools\codebuddy.ps1 -Prompt "回一个数字：1" -Model deepseek-v3-2-volc -Json

# 凭据状态
Get-ChildItem "$env:LOCALAPPDATA\CodeBuddyExtension\Data\Public\auth" | Select-Object Length,LastWriteTime,Name

# 待重登录时（凭据过期 2026-11-13）
codebuddy     # → /login → Log in via Chinese Site
```

## 8. 未闭合项 —— ★ 2026-10-16 01:35 已收尾（三项全部闭合）

| 项 | 收尾结论 | 证据 |
|---|---|---|
| 1. `--tools` 收窄与 Bash 依赖的平衡 | **改用黑名单法**：`--disallowedTools "Bash,Write,Edit,MultiEdit,NotebookEdit"` → **exit 0 / 62 秒 / 正常返回结果**，不再出现 `Tool "Bash" does not exist in the current tool set`。`E:\output\_tools\codebuddy.ps1` 的 `-ReadOnlyTools` 已从白名单改为黑名单 | 三级（真实行为） |
| 2. prewarm sidecar 派活协议未逆向 | **决策：不追**。现有 4 条通道（Codex / CodeBuddy / **Qoder** / 待定 Trae），实测各通道启动仅 10–16 秒；逆向私有 ndjson 协议性价比极低，且有干扰 WorkBuddy 桌面端的风险 | 决策记录 |
| 3. 免费档 `editionType: free` 额度上限未实测 | **结论：本地不可观测**。JSON 里 `total_cost_usd: 0`、`rawUsage.credit: 0`；日志 `[SessionManager][credit] … credit=undefined`；`--help` 无任何 usage/quota/credit 参数 → 只能看服务端账号页。★ 对比：**Qoder CLI 的 `total_credits` 可观测**（单次 0.145–0.773 credits） | 一级（JSON + 日志） |

> 顺带实测到的两个事实：CodeBuddy 默认模型是 **`hy4-preview`**（混元 4 预览，`requestModelName: "Hy4 preview"`）；
> 单次纯文本调用的 prompt_tokens ≈ **24,088**（其中 cache_read 1,408）。
> 详见同目录 `qoder_cli_channel_verdict.md`（第四条通道 + 三条通道的分工全景表）。
