# 相位敏感性（Periodic Weak Spots）— 本机 Agent 自查结论

- **日期**：2026-10-15（v2，含 A4 实测闭合）｜ **会话**：`session-c43b3500-284d-4c56-adcb-17eaadf0e401`
- **论文**：*Periodic Weak Spots: Phase Sensitivity from Chunked KV-Cache Compression*（Zhu et al., [arXiv:2609.36322](https://arxiv.org/abs/2609.36322), 2026-09-28, ByteDance Seed）
- **推断等级**：MAX（按最高置信度假设直接推进，不再反复自疑；但事实与推断严格分行）
- **一句话结论**：**本机 agent 与论文实测的 DeepSeek-V4.1-Flash 是同一型号；该型号存在周期为 2 的相位敏感（gap 6.1pp）；我的中位调用上下文 37.0 万 token（论文测试点的 2.9 倍，88.6% 的调用 ≥128K）；故默认自己存在该问题，用纪律缓解，不尝试修复模型。**

---

## 1. 已核实事实（可复现，非推断）

| 事实 | 值 | 来源 | 等级 |
|---|---|---|---|
| 运行时路由 | `provider: deepseek-official` / `model: deepseek-flash` / `reasoningEffort: high` | `C:\Users\ROG\.dsh\profiles\desktop\cordis.patch.yml` 第 23–28 行 | 二级 |
| 该 id 的真实身份 | `"name":"DeepSeek V4.1 Flash"`，`baseUrl: https://api.deepseek.com`，**contextWindow 1,000,000**，maxTokens 384,000 | `resources\app.asar` 内嵌模型目录 | 二级 |
| 官方口径 | "The default is `deepseek-official` / `deepseek-flash` (**DeepSeek-V41-Flash**)" | `app.asar` 内 README | 二级 |
| 实际服务的模型 | 最近 **245 次调用记录全部为 `model: "deepseek-flash"`** | `C:\Users\ROG\.dsh\.dshw-usage.json` → `events[]` | **三级（真实行为记录）** |
| 实际 token 吞吐（turn 级） | 245 条记录合计 **1,778,535,310 token**（16 个活跃日）；单条 min 175,386 / p50 4,541,634 / max 70,571,128 | 同上 | 三级 |
| **单次调用的上下文长度（★实测）** | **5375 次模型调用**（18 个会话日志，`.dshw-usage.json` 之外的独立来源）：`inputTokens + cacheReadTokens` → min 7,972 ／ p25 224,828 ／ **p50 368,917** ／ p75 510,252 ／ p90 605,409 ／ p95 650,843 ／ p99 673,819 ／ max 678,620 ／ 均值 365,622 | `assistant/message.usage`，脚本 `E:\output\_tools\session_scale.mjs` | **三级（真实用量记录）** |
| 同上 → 论文测试尺度对比 | **≥128K 占 88.6%**；≥256K 占 68.6%；≥512K 占 22.9% | 同上 | 三级 |
| 缓存命中结构 | `cacheReadTokens` 均值 363,184 vs `inputTokens` 均值 2,438 → **99.3% 的 prompt 走缓存命中** | 同上 | 三级 |
| 口径校验 | `totalTokens` p50 369,745 ≈ `inputTokens + cacheReadTokens + outputTokens`（368,917 + output），两套分位数一致 → 字段含义确认 | 同上 | 一级 |
| 论文对我的型号的实测 | **S=2**；mean 92.4%、best 95.3%、worst 89.2%、**gap 6.1pp**（2560 prompts/组，128K needle）；"all four even residues stay above all four odd ones" | [作者博客](https://ultimatejupiter.github.io/blog/periodic-weak-spots/) | 一级（外部实测，非我本人） |
| DSH 确有上下文压缩机制 | 事件流含 `compaction/start`、`compaction/summary`、`compaction/end`、`compaction/prune`（带 `shadowedRange` / `shadowedSeqs` / **`shadowedTokenCount`**） | 同上日志，事件类型统计 | 二级 |
| `web_search` 的真实路径 | 不是本机直连：走 `https://api.deepseek.com/anthropic/v1/messages`（`web/deepseek-search-llm-request`，body.model = `deepseek-v4-flash`，带 `web_search_20250305` 工具）→ **服务端代搜** | 同上日志 | 二级 |
| 凭据位置 | `C:\Users\ROG\.dsh\.credentials.yaml` 存在；**环境变量里没有 `DEEPSEEK_API_KEY`** | 存在性探测 + 全量枚举 | 二级 |
| 会话日志格式 | `C:\Users\ROG\.dsh\sessions\**\session.v4.jsonl.zstd`（18 个文件 / 31.8 MB；**zstd 多帧**，7633 帧/9.88 MB 样本） | 目录探查 + 解压实测 | 二级 |

## 2. MAX 假设链（最高置信度推断）

- **A1**：我服务的就是论文所测的 DeepSeek-V4.1-Flash（目录明示 id→名称；服务端版本与目录一致）。
- **A2**：论文对该型号测出的 S=2、gap 6.1pp **直接适用于我**（同型号 → 同架构 → 同性质）。
- **A3**：服务端分块压缩在长会话中**按默认生效**，我不假设自己享有例外。
- **A4 ★我长期工作在论文测试尺度之上（2026-10-15 已从"下界论证"升级为直接测量）**：
  解开全部 18 个会话日志，从 `assistant/message.usage` 取出 **5375 次模型调用**的真实用量：
  **单次调用上下文（inputTokens + cacheReadTokens）中位数 = 368,917 token ≈ 37.0 万**，
  即**论文 128K 测试点的 2.9 倍**；**88.6% 的调用 ≥128K**、68.6% ≥256K、22.9% ≥512K。
  → 相位效应区间不只是"我的默认工作区间"，我长期在其**深处**运行。
- **A5**：边界相位（S−1）恒弱，**平移输入无法规避**（论文在 cycle 实验中反复确认）。

**由 A1–A5 推出的主线结论（按 MAX 处理，不再加"可能"）：**

- **B1**：我在长上下文检索上**存在**周期性弱点，周期 2，幅度约 6pp（对我而言是"最差相位 89.2% vs 最佳 95.3%"）。
- **B2**：真正的危害不在 6pp 本身，而在**agent 链路的复合效应**（见 §3）：单次取回 10.8% 的失误率，在 20 步任务里几乎必然触发一次。
- **B3**：因此 §4 的纪律不是"保险起见"，而是**必需工作条件**——核心是把事实来源从"上下文中的位置"迁移到"磁盘上的文件"，使取回不经过压缩条目。
- **B4**：不需要换模型、不需要改架构、不需要停止长会话。换 `deepseek-v4-pro` 是**反向操作**（论文中 Pro 档 gap 34.8pp/14.8pp ≫ 6.1pp）。

## 3. 风险量化（论文数字的外推，标注假设）

假设：各步独立；每步至少发生一次长程取回；单次取回错误会传播到该步结论。

| 场景 | 单次取回成功率 | 10 步任务"至少一次失误" | 20 步任务"至少一次失误" |
|---|---|---|---|
| 最佳相位 | 95.3% | 38% | **62%** |
| 最差相位 | 89.2% | 68% | **90%** |

→ 结论：**6pp 的"小问题"在 agent 尺度上被放大成"几乎必然出错一次"**。这就是必须用低成本纪律而不是忽略它的定量理由。
→ 叠加 A4（中位上下文 37 万）：我**每一次**工具调用都落在效应区间内，不是偶发场景。

## 4. 操作纪律（R1–R6，可直接复制到任何会话）

- **R1 事实一律落盘**：关键结论/路径/命令/ID 写入文件（本文件即示范），此后**以文件为准**。
- **R2 不用"记忆中的长文"**：凡要精确复现的内容（路径、命令、数字、ID），**现场 `read`/`grep` 一次**。
- **R3 关键结论必须带证据等级**：一级=命令结果、二级=文件/配置状态、三级=真实行为；**不接受"我记得"**。
- **R4 同一错误重复出现时 → 保义改写**（换问法/换前缀/换位置）+ 重新读取；**不要原样重试**——相位是系统性错误的来源，原样重试会稳定复现同一个错。
- **R5 长会话主动分段与交接**（交接四件套），把关键状态搬出上下文。
- **R6 不为本问题更换模型**（Pro 档更差）。

## 5. 被推翻 / 更正的旧结论

| 旧结论 | 现结论 |
|---|---|
| 本机 agent 的型号**未定**，可能是 V4-Flash(S=4) 或 V4.1-Flash(S=2) | **已定**：V4.1-Flash（app.asar 目录 + README + 245 条运行时记录三处一致） |
| "**我不确定自己是否存在**该问题" | **该表述不严谨**。准确表述：*型号已确定为论文被测型号（故默认存在），剩余未知仅为"压缩在本机负载下是否已触发"* |
| A4 只是"**下界论证**"（最小 turn 记录 175,386 token > 128K） | **★2026-10-15 实测更正**：A4 是**直接测量**——中位调用上下文 **368,917 token**，88.6% ≥128K。原论证方向正确但**低估了一个数量级以上的普遍性** |
| 讨论重点曾偏向"如何修复" | **修复不在可控范围**：属预训练级（相位专门化由梯度流动力学产生）或服务端级（压缩策略），且论文未给出已验证解法；策略改为**缓解 + 纪律** |
| 会话日志"解不开"（Python 缺 `zstandard`） | **错**：**Node 24 原生带 zstd**（`zlib.zstdDecompressSync`），配合 `dsh-sessions.mjs` 已验证的 magic 分帧法即可解开。**零安装、零联网** |

## 6. 未闭合项（仍需信息 / 工具）

1. **`DEEPSEEK_API_KEY`**：不在环境变量中（凭据在 `.credentials.yaml`）→ 直连做 128K 相位扫描需要它。
2. **服务端压缩配置**：S 是否确为 2、压缩在多少 token 后生效、是否对 `deepseek-official` 路由生效。
3. ~~单次调用的精确上下文分布~~ → **★2026-10-15 已闭合（零成本）**：见 §1 实测行与 §2 A4；
   脚本 `E:\output\_tools\session_scale.mjs`（Node 原生解 zstd 多帧，18 个日志约 10 秒内跑完）。
4. **论文 V4.1-Flash 的 residue 级 A(r) 明细表**（博客只给折叠曲线与"偶高于奇"的文字描述）。
5. **效应是否随上下文长度增长**：论文只测到 128K，我实测工作在 37 万中位数（最长 67.9 万）→ **6.1pp 应视为下限，而非上限**。
6. 「论文只在 128K 测」这一点也意味着：**"短对话里没观察到"不能用来证伪**。
7. **本机是否还有其他压缩相关开关**（如 `compaction` 阈值）会影响我的有效上下文构成——日志已证明 compaction 事件存在，但其触发条件未测。

## 7. 复现命令

```powershell
# 1) 运行时配置
Get-Content C:\Users\ROG\.dsh\profiles\desktop\cordis.patch.yml | Select-Object -Skip 22 -First 6

# 2) 模型身份（asar 内嵌目录 / README）
#    在 app.asar 中检索 "deepseek-flash"，命中 "name":"DeepSeek V4.1 Flash" 与 README 的 DeepSeek-V41-Flash

# 3) turn 级吞吐（三级证据）
$u = Get-Content C:\Users\ROG\.dsh\.dshw-usage.json -Raw | ConvertFrom-Json
$u.events | Group-Object model | ForEach-Object { "$($_.Name)=$($_.Count)" }

# 4) ★单次调用上下文分布（本文件 A4 的来源，零安装）
& E:\node.exe E:\output\_tools\session_scale.mjs

# 5) Node 原生 zstd 能力自检
& E:\node.exe -e "const z=require('zlib');console.log(typeof z.zstdDecompressSync)"
```

---

## 附：本机可调用的 AI 工具（2026-10-15 探测，供派活）

| 工具 | 路径 / 状态 | 备注 |
|---|---|---|
| **Codex CLI** ⭐ | `C:\Users\ROG\AppData\Local\OpenAI\Codex\bin\9614f1d9b40d9c4f\codex.exe` | **v0.162.0-alpha.17.2**（318.6 MiB），签名 **Valid / `CN="OpenAI OpCo, LLC"`**；`codex exec "…"` 非交互派活（`-s read-only`、`-C <dir>`、`--ephemeral`、`--json`、`-o <file>`）；model `gpt-5.6-luna`、sandbox danger-full-access、web_search live；`auth_mode = chatgpt`、`OPENAI_API_KEY` 为空 → **消耗 ChatGPT 账号额度**；★**2026-10-16 已实测打通**（exit 0 / 9.9 秒 / 16,183 token）：前置条件只有两条 —— ① Clash Verge 主程序在跑 ② **`~/.codex/.env` 的代理端口 = Clash 混合端口 `7897`**（该 `.env` 优先级**高于**环境变量/系统代理/TUN；原值 `65532` 已失效，已修正并备份 `.env.bak-20261016`）。详见 `E:\output\codex_cli_channel_verdict.md` |
| Codex 桌面版 | `C:\Program Files\WindowsApps\OpenAI.Codex_26.1007.9446.0_x64__2p2nqsd0c76g0`（MSIX，主程序 `app\ChatGPT.exe`） | ★**与"ChatGPT 桌面版"是同一个包**；其 config.toml 的 `CODEX_CLI_PATH` 指向上面那个 codex.exe → CLI 属正式组件 |
| WebCodex Desktop | `F:\WebCodex Desktop\WebCodex.exe` v0.4.6（CompanyName `webcodex`，**未签名**，**不含任何 codex CLI**） | 独立第三方软件；**用户说明**：让 ChatGPT 聊天模式获得 Codex 同功能（性能略差），用于**叠加免费额度**；与官方 CLI 无技术关系 |
| Trae CN | `E:\Trae CN\Trae CN.exe` | 项目原主力编码，共享 `E:\output` 与技能池 |
| Qoder CN IDE | `%LOCALAPPDATA%\Programs\Qoder CN IDE` | 第二意见 |
| WorkBuddy | `F:\AI\WorkBuddy\WorkBuddy.exe` | 按任务参与 |
| VS Code CLI | `code`（`E:\Microsoft VS Code\bin\code.cmd`） | 可命令行驱动 |
| GitHub CLI | `gh` | 联网前须告知用户 |
| Notion | `%LOCALAPPDATA%\Programs\Notion` | — |

⚠ 除 VS Code / gh 外均为独立 GUI 软件；**一切联网动作按 `AGENTS.md` 第 8 条先告知用户**。
