# 四个候选插件评估（2026-10-17）

> 环境：DSH Desktop **0.2.1-rc.2**，Desktop profile，当前 16 个 bundle
> 评估口径：**是否解决我们的真实痛点**（上下文 368K/步、缓存重读成本、工具失败重试），以及**风险/成本**
> 证据等级：包元数据与源码为一级（实际下载解压）；收益估算为二级（作者实测 + 我们的环境参数推算）

## 结论速览

| 插件 | 真实包 | 结论 | 一句话 |
|---|---|---|---|
| `dsh-batch-tool-calls` | npm **1.1.2**（liancha22） | ✅ **推荐装** | 纯 systemPrompt 提示段，逼模型一步多发工具，直击"每步重读 368K" |
| `dsh-tool-retry` | npm **`@canglongcl/dsh-tool-retry` 0.2.1** | ❌ **实测不兼容 0.2.1（已排除）** | 安装后被 HMR 加载，`tools/post-execute` 访问 0.2.1 已不存在的字段，**导致所有工具调用崩**；见踩坑 #21 |
| `dsh-ops` | npm **0.3.0**（T-Auto） | ⚠️ **不推荐** | 与官方文件/终端工具重复，还改 `pwsh-sandbox` 路径，风险大于收益 |
| `dsh-tool-turbo` | **GitHub only** `Electricitysheep/dsh-tool-turbo` 0.1.0 | ❌ **暂不装** | private、未构建、peer 不兼容 0.2.1、无设置界面、默认降档违背 max 偏好 |

---

## 1. `dsh-batch-tool-calls@1.1.2` ✅

**它做什么**：往宿主 `systemPrompt` 注册一段**静态提示**（order 9500），要求"互不依赖的侦查调用一次发 3–6 个"；压缩后在下一次 `agent/pre-step` 补一条几十 token 的提醒。

**为什么对我们有用**：
- 我们的单步成本极高（p50 **368,917 token/步**，99.3% 缓存命中）。**步数 = 钱**，即使缓存价也按步重读。
- 作者用真实会话统计：长编码会话 244 步中 **172 步只发 1 个工具调用**（70%），平均 1.26 次/步。
- 按我们环境粗算：若把 70% 的单调用步压到 2–3 次/步，**步数约减 30–40%**，缓存重读同步减少；墙钟时间也受益。

**API 兼容（0.2.1 实测）**：
- `systemPrompt.section()` ✅（0.2.1 `dsh-system-prompt/lib/index.js:253`）
- `session/event` + `compaction/end` ✅（日志事件）
- `agent/pre-step` ✅（0.2.1 源码 `packages/core/agent-loop/src/agent.ts:277`）
- **纯 `insert`，不覆盖任何官方行**

**成本**：静态段约 **250 token/步**（常量，前缀稳定，不破坏缓存）；压缩后提醒 ~几十 token，可关。

**可调**：`minCalls`/`maxCalls`/`mentionShell`/`reassertAfterCompaction`/`reassertEverySteps`/`language`。

**风险**：低。它只是提示，不改工具清单、不改并发上限、不改缓存策略。最坏情况是模型偶尔仍串行。

---

## 2. `@canglongcl/dsh-tool-retry@0.2.1` ✅

**它做什么**：每个模型直发工具调用都 checkpoint 到 OS temp；失败时注入一条最小提示（含 call id），native 模式提供 **`editPreviousToolCalling`** 工具——改参数后直接重放，不用重新生成整段调用。

**为什么对我们有用**：
- 我们确实会遇到工具失败：pwsh 超时、编码错误、参数写错、路径不存在。**每次失败重生成 = 重复输出整段参数**（几百到上千 token）。
- checkpoint 文件**不注入上下文**，模型只有在选择读时才付费。

**API 兼容（0.2.1 实测）**：
- `systemPrompt.tools()` ✅（0.2.1 `dsh-system-prompt/lib/index.js:299`）
- `tools/post-execute` ✅（0.2.1 `packages/core/tools/src/index.ts:176`）
- `editPreviousToolCalling` 在包里存在 ✅
- **纯 `insert`，不覆盖官方行**

**成本**：静态段 **~100–180 token/步** + 每次失败 **~20–40 token**；**+1 个工具 schema**。

**注意**：
- `lib/index.js` 打包后 **296 KB**（内含依赖），加载一次，常驻内存可接受。
- Windows 下 `previous/1.json` 别名是内容复制（编辑别名不会同步 by-id，但 native 重放直接编辑 by-id，只影响 PTC 文件工具编辑）。

**风险**：低。失败时是 warning，不影响启动。

---

## 3. `dsh-ops@0.3.0` ⚠️ 不推荐（当前）

**它做什么**：自带 bash 5.3.15 + PowerShell 7.6.6 + 4 个 Rust 文件工具；默认启用 shell 与 file 组件，后台与 PTC 默认关闭。

**为什么不适合我们**：
1. **工具重复**：默认新增 `ops_bash` + 4 个文件工具，而我们已有官方 `pwsh`、`read`/`write`/`edit`、`glob`/`grep`。**两套文件工具并存** → 模型选择混淆 + 工具 schema 增加，与"省 token"目标相反。
2. **改沙箱路径**：Shell 组件会**临时改写 `pwsh-sandbox` 的 PowerShell 7 路径**。我们的会话依赖 `danger-full-access` 下 pwsh 正常工作（踩坑 #10），这条路径动不得。
3. **载荷重**：解压后约 6 MB（bash + pwsh + Rust worker）。
4. **版本口径**：README 明确"目标宿主 DSH 0.2.0-rc.2"，我们是 0.2.1-rc.2；peer optional 不阻塞，但无兼容承诺。
5. **97% token 减免的前提**是"纯 PTC 会话 + 显式启用 `dsh-ops-ptc`"。我们的会话不是 PTC 模式，普通步骤拿不到这个收益。
6. **它解决的是"Windows 下 PowerShell 反复报错"**——我们目前没有这个困扰（实测 pwsh 正常）。

**如果将来要试**：只启用 `dsh-ops-shell` 并关闭 file/background/ptc，且先备份 `cordis.patch.yml`。**不建议现在做。**

---

## 4. `dsh-tool-turbo@0.1.0` ❌ 暂不装

**它做什么**：按轮自动调 `reasoning_effort`——简单工具链降 `low`，重活升 `high`，超大载荷升 `max`。

**为什么不装**：
1. **没有 npm 包**：`private: true`，只能 `git clone` + `npm install` + 构建 + `link:` + `pnpm install` + 重启。**不是插件页一键装**。
2. **入口是未编译的 TS**（`"main": "src/index.ts"`）→ 必须自己构建。
3. **peer 不兼容**：要求 `@deepseek-ai/dsh-agent ^0.1.0-rc.6`（`>=0.1.0-rc.6 <0.2.0`），我们是 **0.2.1-rc.2**。
4. **★10 / v0.1.0 / 设置界面未实现**（roadmap 未完成）→ 只能改代码调 `allowDowngrade`/`baseline`，**用户几乎不写代码**。
5. **行为与你的偏好冲突**：默认 `allowDowngrade: true`，会把简单工具链降到 `low`。你明确要求复杂任务用 `max`，自动降档可能降低质量，且没有 UI 可关。

**结论**：等它发 npm、有设置界面、且 peer 跟上 0.2.x 再评估。

---

## 推荐动作

**先装两个，观察一周：**

```
dsh-batch-tool-calls
@canglongcl/dsh-tool-retry
```

安装位置：桌面侧边栏 → **Plugins（插件）页** → 粘贴上面 spec → 安装 → 按提示重载/重启。

**不建议**：`dsh-ops`、`dsh-tool-turbo`。

**装完验证**：
- 新会话里看是否出现 `editPreviousToolCalling` 工具（retry）
- 观察步数是否下降（可用 `dsh-batch-tool-calls` 自带的 `scripts/step-report.mjs` 读会话日志）
- 若批量提示让模型在需要串行的场景强行并行，把 `minCalls` 调低或 `enabled: false`

## 证据来源

- npm registry 元数据（2026-10-17 实查）：`dsh-batch-tool-calls@1.1.2`、`dsh-ops@0.3.0`、`@canglongcl/dsh-tool-retry@0.2.1`
- 包内 `cordis.patch.yml` 与 README（tarball 解压实读）
- 0.2.1 asar 源码：`dsh-system-prompt/lib/index.js`（section/tools 方法）、`app.asar` 内 `dsh-web-app` patch
- `E:\deepseek-harness` 源码：`agent/pre-step`、`tools/post-execute` 事件定义
