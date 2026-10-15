# Qoder CN CLI 派活通道 — 打通结论（verdict）

- **日期**：2026-10-16（01:22 开工 → 01:35 打通并三级验证，约 13 分钟）
- **会话**：本会话（DSH Desktop，文件策略 `danger-full-access`）
- **一句话结论**：**Qoder CN CLI 是第四条 AI 派活通道，已打通并三级验证通过**（`qoderclicn -p "…"` → exit 0 / 11.9 秒 / 真实回答；带工具任务返回真实扫盘结果 4044）。
  ★ **附带的最大收获**：Qoder CLI **开箱即用、零配置自动加载共享技能池 `~/.agents/skills`**（实测 **67/67 全部识别**），这是四条通道里**第一条原生吃我们技能资产的通道**。

---

## 1. 最终可用状态（三级证据）

| 项 | 值 | 证据等级 |
|---|---|---|
| 可执行 | `qoderclicn -p "…"`（npm 全局包 `@qodercn-ai/qoderclicn@1.1.72`） | 一级（命令结果） |
| TEST A：纯文本派活 | `Reply with exactly: QODER_CHANNEL_OK` → **`QODER_CHANNEL_OK`**，exit **0**，**11.9 秒** | 三级（真实行为） |
| TEST B：带工具只读任务 | "统计 E:\output 下 .md 文件数" → **`4044`**（num_turns=2、`permission_denials: []`、15 秒） | 三级（真实行为） |
| ★ 交叉验证 | PowerShell 独立扫描 `E:\output` 递归 .md 数 = **4044**（与 CLI 答案一致） | 一级 |
| TEST C：JSON 输出 | `-o json` → `result` / `num_turns` / `duration_ms` / **`total_credits`** / `session_id` / `context_usage_ratio` | 三级 |
| 封装工具 | `E:\output\_tools\qoder.ps1`（`-Prompt` `-Model` `-Json` `-WorkDir` `-Effort` `-ReadOnly` `-Yolo` `-TimeoutSec`）→ 修正后复测 `QODER_PS1_V2_OK` + `4044` 双通过 | 三级 |
| 凭据落盘 | `~\.qoder-cn\.auth\user`（1324 B, 01:25:52） | 二级（文件状态） |
| 技能加载 | `qoderclicn skills list` → **67 行来自 `C:\Users\ROG\.agents\skills\*`**、51 行来自 Qoder 插件市场、2 行其他 | 三级（真实行为） |
| 可用模型 | **15 个**：Auto / Fast / Qwen3.8-Max / Qwen3.8-Flash / Qwen3.7-Max / Qwen3.7-Plus / Qwen3.7-Flash / DeepSeek-V4-Pro / DeepSeek-Flash / GLM-5.3 / GLM-5.3-Flash / GLM-5.2 / Kimi-K3 / Kimi-K2.8-Preview / MiniMax-M2.7 | 一级（`--list-models`） |

---

## 2. ★两个必须记住的坑（都是实测踩出来的）

### 2.1 命令名遮蔽：`qodercn` 被 npm 版抢走

| 事实 | 说明 |
|---|---|
| npm 包提供**两个** bin | `qodercn` → `bundle/qodercn-npm-dispatcher.cjs`；`qoderclicn` → `bundle/qoderclicn.js` |
| PATH 顺序 | npm 全局 bin `%APPDATA%\npm` 在 **第 39 位**，Qoder CN IDE 壳在 **第 47/48 位** → **npm 版赢** |
| 后果 | 用户/工具敲 `qodercn .` 想开 IDE，实际会启动 CLI agent |
| 处置（已做） | 把 npm 生成的 `qodercn` / `qodercn.cmd` / `qodercn.ps1` 改名为 `*.npm-disabled-qodercli` → `where qodercn` 已回到 IDE 壳，`qoderclicn` 正常 |
| ⚠ 复发条件 | **npm 升级/重装该包会重建这三个 shim**，遮蔽会回来 → 重跑同一条改名命令即可 |

### 2.2 ★参数顺序铁律：`-p` 是布尔开关，prompt 是**位置参数**

```
Usage: qoderclicn [options] [command] [query...]
Arguments:
  query   Initial prompt.
Options:
  -p, --print   Print response and exit (non-interactive)   ← 注意：不带 <prompt>
```

- **症状**：`qoderclicn -p "<任务>" -m auto -w E:\output -o json` 时，`-m/-w/-o` **被并进 query**，
  模型收到的提示词变成 `"<任务> -m auto -w E:\output -o json"`（实测输出 `QODER_PS1_OK -m auto -w … -o json`）。
- **正确姿势**：**选项一律在前，prompt 永远放最后**
  ```powershell
  qoderclicn -m auto -w E:\output -o json --permission-mode auto -p "<任务>"
  ```
- **教训**：位置参数 + variadic `[query...]` 的 CLI，把 prompt 写在中间就会吞掉后续选项。

> 另一个曾误导排查的假象：封装脚本里 `& qoderclicn @($argv[1..N])` —— PowerShell 的 `@(...)`
> **不是 splatting**，整个数组被当成**单个参数**传给 CLI。正确写法是先把切片存进变量，再 `@变量名`。

---

## 3. 安装与认证（可复现）

```powershell
# 1) 安装（Node >= 20.18.1；本机 node 24.16.0 / npm 11.13.0 通过）
npm install -g @qodercn-ai/qoderclicn      # 实测 10 秒、10 个包、67.9 MB 解包体积
qoderclicn --version                        # → 1.1.72

# 2) 解除遮蔽（保护 IDE 的 qodercn 壳命令）
foreach($n in 'qodercn','qodercn.cmd','qodercn.ps1'){
  Rename-Item "$env:APPDATA\npm\$n" "$n.npm-disabled-qodercli" -Force
}

# 3) 登录（无 TTY 也能跑；NO_BROWSER=1 让它打印 URL 而不是弹窗）
$env:NO_BROWSER='1'; qoderclicn login
#   实测输出：https://qoder.cn/device/selectAccounts?challenge=…&challenge_method=S256&client_id=…
#   → “Waiting for browser authorization…” → “Login successful! Welcome, nick8927545391.”

# 4) 验证
qoderclicn -p "Reply with exactly: QODER_CHANNEL_OK"

# 5) 备选认证（CI / 无浏览器）：PAT
#   README 记的是国际版变量 QODER_PERSONAL_ACCESS_TOKEN（账号页 https://qoder.com/account/integrations）；
#   CN 版按品牌前缀为 QODERCN_PERSONAL_ACCESS_TOKEN（本次未用到，走的是 OAuth）。
```

---

## 4. 能力与用法（实测 + `--help`）

| 能力 | 用法 | 备注 |
|---|---|---|
| 非交互派活 | `qoderclicn -p "<任务>"` | 等价 `codex exec` / `codebuddy -p` |
| 结构化输出 | `-o json` / `text`（另有 stream-json） | 含 **`total_credits`（可观测额度）**、`session_id`、`num_turns`、`context_usage_ratio` |
| 权限模式 | `--permission-mode {default,accept_edits,bypass_permissions,dont_ask,auto}`、`--dangerously-skip-permissions` | ★ **Headless 下权限为 ask 会静默拒绝**，派活必须显式给 `auto` 或跳过 |
| 工具收窄 | `--tools`、`--allowed-tools`、`--disallowed-tools` | 只读姿势同 CodeBuddy：用**黑名单**（禁 Bash/Write/Edit），别用白名单 |
| 模型 | `-m <name>`、`--list-models` | 15 个可选（含 Qwen3.8-Max / DeepSeek-V4-Pro / GLM-5.3 / Kimi-K3） |
| 推理强度 | `--reasoning-effort`、`--thinking`、`--thinking-budget` | |
| ★ 技能 | `skills list/enable/disable/install/link/uninstall` | **`link <path>` 可把任意本地技能目录链进来（源改动即时生效）** |
| 插件 / 钩子 / 智能体 | `plugins`、`hooks`、`agents`、`mcp` | 完整插件化架构 |
| 会话 | `-c`（续最近）、`-r <id>`、`--session-id`、`--list-sessions`、`--fork-session` | |
| 远程 | `--remote`、`--teleport`、`--remote-control` | 云端会话 / 远程执行 |
| 服务化 | ACP（`--help` 列出的 ACP 能力）、`--agent`、`--agents <json>` | 可作智能体服务端接入编辑器 |
| 其它 | `--add-dir`、`--max-turns`（`--help` 未列，见官方文档）、`--worktree`、`--attachment` | |

**架构判断**：参数集（`-p/--print`、`--permission-mode`、`--allowed-tools`、`--agents`、`--settings`、`--setting-sources`、
`--output-style`、`--max-turns`、`/login` `/logout` 会话命令）与 **Claude Code** 高度同构 → Qoder CN CLI 是
**Claude Code 架构的国产分支**（这也解释了它为什么原生吃 `.agents/skills`：那是 Claude Agent Skills 规范）。

---

## 5. ★技能（skills）生态复用 — 本轮的第二个交付

### 5.1 Qoder CLI：**零配置直接复用我们的 67 个技能**（三级证据）

官方 README 原文：
> 「CLI 默认把 `.agents/skills` 作为兼容来源加载」…「开启时（**默认**），CLI 会加载用户、项目和附加目录中的 `.agents/skills`，
> 监听用户和项目的 `.agents/skills`，并支持工作区子目录的祖先 `.agents/skills` 动态发现。」

开关：`skills.loadFromAgentsDirectory`（默认 `true`，可用 `/settings` 或 `--settings '{"skills":{"loadFromAgentsDirectory":false}}'` 关闭）。

**实测**：`qoderclicn skills list` → 519 行输出，**67/67 共享池技能全部 [Enabled]，零遗漏**；另有 Qoder 插件市场 51 个。

| 位置 | 路径 | 作用域 |
|---|---|---|
| DSH 共享池（自动加载） | `C:\Users\ROG\.agents\skills\{name}\SKILL.md` | 所有项目（**默认开启**） |
| Qoder 用户级 | `~\.qoder-cn\skills\{name}\SKILL.md` | 当前用户所有项目（**目前不存在**） |
| Qoder 项目级 | `<cwd>\.qoder\skills\{name}\SKILL.md` | 仅当前项目 |
| Qoder 市场/插件 | `~\.qoder-cn\plugins\cache\qoder-marketplace\…\skills\` | 插件自带 |

→ **结论：技能资产在 Qoder 通道上是"即插即用"的，无需复制、无需同步脚本。** 新增技能写进 `~/.agents/skills` 后，
Qoder CLI 会监听并动态发现（子目录的祖先目录也支持）。

### 5.2 Trae：**同格式但不同步**，且独有技能不可用

| 事实 | 值 | 证据 |
|---|---|---|
| Trae 技能目录 | `~\.trae-cn\skills`，**74 个** | 一级（目录枚举） |
| DSH 共享池 | `C:\Users\ROG\.agents\skills`，**67 个** | 一级 |
| 关系 | **不是 junction**（`LinkType` 为空、Attributes 无 ReparsePoint） | 一级（`Get-Item -Force`） |
| 拷贝方向与时间 | Trae 目录创建 **2026-05-08**；池创建 **2026-09-27 02:12** → 池是**从 Trae 拷贝**出来的 | 一级（CreationTime） |
| 内容一致性 | 抽样 3 个同名技能逐文件 MD5 比对**完全一致**（当时拷贝的） | 一级 |
| 之后是否同步演进 | Trae 目录 LastWrite **2026-07-21**、池 LastWrite **2026-10-13** → **两份副本已独立演进** | 一级 |
| Trae 独有 | **10 个**：`local-asr` `local-computer-use` `local-img2img` `local-mineru` `local-ocr-npu` `local-realtime-translator` `local-screenshot-qa` `local-tts` `local-txt2img` `local-vram` | 一级 |
| 池独有 | **3 个**：`delivery-self-review` `ui-ux-pro-max` `writing-guidelines` | 一级 |
| ★ Trae 独有技能可用性 | **全部是 Intel AIPC 专属**，`local-tts/SKILL.md` 原文：「The run.ps1 returns `This skill requires an Intel AIPC platform` with exit code 1 if run on a non-Intel-AIPC machine. **Do NOT try to use this skill again on unsupported hardware.**」 | 一级（文件内容） |
| 本机是否 AIPC | **否**（`platform.exe --is-aipc` → **0**） | 一级（历史实测，§1 环境事实） |

**结论（③ 的评估答复）**：
1. **不要**把那 10 个 `local-*` 同步进 DSH 池 —— 本机非 AIPC，同步进来只会让模型反复尝试并失败（官方明确写"不要再试"）。
2. Trae 侧与池侧是**两份独立副本**，不是共享。要不要建立同步，取决于是否还需要 Trae 侧技能 —— 见 §7 待用户裁定项。
3. Trae 技能是 **marketplace 托管**的（`~\.trae-cn\skill-config.json` 的 `managedSkills` 记录了每个技能的来源与启停），
   手工往 `~\.trae-cn\skills` 放文件可能被 Trae 的同步机制覆盖 → **不建议**用"手工拷贝"做同步。
4. 格式兼容性本身没问题（两边都是 `SKILL.md` + YAML frontmatter，Qoder 已证明这套规范互通），**问题只在"谁来同步"**。

---

## 6. 被推翻 / 更正的旧结论

| 旧结论 | 现结论 |
|---|---|
| `_DSH_OFFICE_STATE.md` §1.2：「Trae `.trae-cn\skills` **74 个已 junction 共享给 DSH**」 | ❌ **不成立**。两边**都不是** junction，是 **2026-09-27 的一次性拷贝**，且此后**各自独立演进**（池已到 10-13，Trae 停在 7-21） |
| §1.2：「Qoder CN … **独立 CLI `qoderclicn` 未安装**」「❌ 当前不能（派活）」 | ✅ **已解决**：npm 包 1.1.72 已装、已登录、派活三级验证通过 |
| §1.2：「Qoder 对 DSH 增量 ☆ 低」 | ❌ **恰恰相反**：它是**第一条原生复用技能池的通道**（67/67 自动加载）+ 15 个模型可选 |
| 用户提供的信息表：`--yolo` 跳过权限 | ⚠️ **实测 `--help` 里没有 `--yolo`**，等价物是 `--dangerously-skip-permissions`（另有 `--permission-mode bypass_permissions`） |
| 用户提供的信息表：模型含 `Qwen3.6-Flash`/`DeepSeek-V4-Flash`/`Kimi-K2.7-Code` | ⚠️ 本账号实测可用的是 **15 个**，名称有出入（有更新的 `GLM-5.3`、`Kimi-K3`、`Qwen3.8-*`）→ **以 `qoderclicn --list-models` 为准** |
| 「`qodercn` 可以用来跑 CLI」 | ⚠️ 装 npm 包后 `qodercn` 会**遮蔽 IDE 壳**；本机已统一改用 **`qoderclicn`** |

---

## 7. 四条 AI 通道分工（更新后的全景）

| 通道 | 入口 | 模型 | 计费 | 技能复用 | 备注 |
|---|---|---|---|---|---|
| **Codex CLI** | `codex exec -s read-only -C E:\output --ephemeral "…"` | `gpt-5.6-luna` | ChatGPT 账号额度 | ❌（不吃 `.agents/skills`） | 需 Clash 7897 + `~\.codex\.env` 端口一致 |
| **CodeBuddy CLI** | `codebuddy -p "…"`（工具 `_tools\codebuddy.ps1`） | GLM / Kimi / MiniMax / DeepSeek-V3.2 / hy4-preview | credits（**本地不可观测**） | ❌ | 凭据有效期至 2026-11-13 |
| **Qoder CN CLI**（新） | `qoderclicn -p "…"`（工具 `_tools\qoder.ps1`） | Qwen3.8-Max / DeepSeek-V4-Pro / GLM-5.3 / Kimi-K3 等 **15 个** | credits（**可观测**：`total_credits`） | ✅ **67/67 自动加载** | 选项在前、prompt 最后 |
| **TRAE CLI**（❌ 终止） | — | — | — | ✅（同规范，但用不上） | ⚠️ **官方限制：仅 TRAE 企业版旗舰版套餐可用**；已复核 1.0/2.0 文档一致，本机账号为免费版 → 结案 |

---

## 8. verdict §8 三项收尾（本轮同时完成，针对 CodeBuddy）

| 原未闭合项 | 收尾结论 | 证据 |
|---|---|---|
| §8.1 `--tools` 收窄与 Bash 依赖的平衡 | **改用黑名单法**：`--disallowedTools "Bash,Write,Edit,MultiEdit,NotebookEdit"` → exit 0 / 62 秒 / 正常返回结果，不再出现 `Tool "Bash" does not exist in the current tool set`。已把 `E:\output\_tools\codebuddy.ps1` 的 `-ReadOnlyTools` 从白名单改为黑名单并更新注释 | 三级（真实行为） |
| §8.2 prewarm sidecar 派活协议未逆向 | **决策：不追**。理由：现在已有 4 条通道（Codex / CodeBuddy / Qoder / 待定 Trae），prewarm 只省"启动开销"（实测各通道启动 10–16 秒，可接受），逆向私有 ndjson 协议性价比极低，且有破坏 WorkBuddy 桌面端的风险 | 决策记录 |
| §8.3 免费档额度上限未实测 | **结论：本地不可观测**。JSON 里 `total_cost_usd: 0`、`rawUsage.credit: 0`、日志 `[SessionManager][credit] … credit=undefined`；`--help` 无任何 usage/quota/credit 参数 → 只能去服务端账号页看。★ 对比：**Qoder CLI 的 `total_credits` 是可观测的**（单次 0.145–0.773 credits） | 一级（JSON + 日志） |

---

## 9. 未闭合项（留给后续）

1. **Qoder 市场技能的"反向复用"**：Qoder 插件市场那 51 个技能（apollo-graphql / alibabacloud-workbench / …）能否
   拷进 `~/.agents/skills` 让 DSH 也用？—— 涉及第三方许可与体积，需先评估收益。
2. **`.qoder-cn\skills` 用户级目录**尚未创建；如果将来想让"只给 Qoder 用、不给 DSH 用"的技能有地方放，可以启用它。
3. **Qoder CLI 的 `--max-turns`、`--settings`、ACP 服务化** 未实测（官方文档有，`--help` 未列全）。
4. **TRAE CLI：已复核确认免费版不可用（2026-10-16 结案）** —— `docs.trae.cn` 的 **1.0 与 2.0 概述页两处一致**写明「仅 TRAE 企业版的旗舰版套餐客户可使用 TRAE CLI」，用户账号为免费版 → **本轮终止**。（替代路线开源 `bytedance/trae-agent` 需 BYOK API key，且不复用 `.agents/skills` 规范，边际价值低于现有 4 条通道，暂不做。）
5. `qodercn` 遮蔽在 **npm 升级后可能复发** → 记入办公室踩坑清单。

---

## 10. 复现与验证命令

```powershell
# 通道健康检查（秒级）
qoderclicn -p "Reply with exactly: QODER_CHANNEL_OK"

# 经封装工具派活（推荐）
pwsh -NoProfile -File E:\output\_tools\qoder.ps1 -Prompt "用一句话说明 CARLA 是什么"

# 只读审阅 + JSON（含 credits 用量）
pwsh -NoProfile -File E:\output\_tools\qoder.ps1 -Prompt "审阅 E:\output\1\api\violation_rules.py 的边界条件" -Model DeepSeek-V4-Pro -ReadOnly -Json

# 技能池是否被 Qoder 认到（应为 67 个 .agents 来源）
qoderclicn skills list | Select-String '\.agents\\skills'

# 凭据状态
Get-ChildItem "$env:USERPROFILE\.qoder-cn\.auth" | Select-Object Name,Length,LastWriteTime

# 遮蔽复查（应只剩 IDE 壳）
where.exe qodercn
```
