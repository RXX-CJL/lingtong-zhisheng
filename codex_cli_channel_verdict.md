# Codex CLI 派活通道 — 打通结论（2026-10-16）

- **会话**：DSH Desktop（2026-10-15 深夜 ~ 10-16 00:33）｜ **代价**：约 40 分钟误诊 + 10 分钟定位
- **一句话结论**：**通道已打通并实测成功** —— `codex exec` → **exit 0 / 9.9 秒 / 返回 `CODEX_CLI_OK` / 16,183 token**（三级证据）。
- **根因**：`C:\Users\ROG\.codex\.env` 里写死的旧代理端口 **`65532`**（当前 Clash Verge 用 **`7897`**），
  而该 `.env` 的优先级**高于**环境变量、Windows 系统代理与 TUN 模式。

---

## 1. 事实（可复现）

| 事实 | 值 | 等级 |
|---|---|---|
| 可执行文件 | `C:\Users\ROG\AppData\Local\OpenAI\Codex\bin\9614f1d9b40d9c4f\codex.exe`（318.6 MiB） | 二级 |
| 版本 / 签名 | `codex-cli 0.162.0-alpha.17.2` ／ 签名 `Valid`，`CN="OpenAI OpCo, LLC"` | 一级 |
| 登录方式 | `~/.codex/auth.json`：`auth_mode = chatgpt`、`OPENAI_API_KEY` 为空 → 走 **ChatGPT 账号额度**（非 API 计费） | 二级 |
| 触发失败的配置 | `~/.codex/.env`：`HTTP_PROXY/HTTPS_PROXY=http://127.0.0.1:65532`（该端口无任何服务） | 二级 |
| 失败现象 | 出站连接 `127.0.0.1:65532` 恒为 `SynSent` → `os error 10061` → 日志 `waiting for network` 无限重连 | 一级 |
| **判据证据** | Node 探针监听 65532，抓到 codex 发来 **`CONNECT chatgpt.com:443 HTTP/1.1`**（标准 HTTP 代理请求） | 一级 |
| 修复 | `.env` 端口改为 `7897`；备份在 `C:\Users\ROG\.codex\.env.bak-20261016` | 二级 |
| **验证** | `codex exec -s read-only -C E:\output --ephemeral --color never "只回答一行…"` → **exit 0 / 9.9 秒 / `CODEX_CLI_OK GPT-5` / 16,183 token** | **三级** |

**"ChatGPT 桌面版 / Codex 桌面版"与 CLI 的关系**：二者是同一个 MSIX 包
（`C:\Program Files\WindowsApps\OpenAI.Codex_26.1007.9446.0_x64__2p2nqsd0c76g0`，主程序 `app\ChatGPT.exe`），
其 `config.toml` 里的 `CODEX_CLI_PATH` 就指向上面这个 `codex.exe` → **CLI 是正式组件，不是外挂**。
`WebCodex Desktop`（`F:\WebCodex Desktop\WebCodex.exe`，未签名第三方）**与官方 CLI 无技术关系**，
用户的用法是"让 ChatGPT 聊天模式获得 Codex 同功能、叠加免费额度"。

---

## 2. 可用命令（直接复制）

```powershell
& "C:\Users\ROG\AppData\Local\OpenAI\Codex\bin\9614f1d9b40d9c4f\codex.exe" exec `
  -s read-only -C E:\output --ephemeral --color never "你的任务"
```

- **前置条件**：① Clash Verge 主程序在运行（混合端口 `7897` 有监听）
  ② `~/.codex/.env` 的端口与 Clash 混合端口一致（当前已是 7897）。系统代理/TUN 开不开都可以。
- 可选参数：`-C <目录>` 指定工作根、`--ephemeral` 不留会话、`-o <文件>` 只把最终答复写入文件、
  `--json` 输出 JSONL 事件、`-m <模型>` 换模型。

---

## 3. ★被推翻的旧结论（本次最大的教训）

| 旧结论（本会话中途写下，已作废） | 现结论 |
|---|---|
| "codex 是 Rust，**不读 Windows 系统代理**，所以必须显式设 `HTTPS_PROXY`" | **错**。真正原因是 `~/.codex/.env` 覆盖一切；环境变量、系统代理、TUN 全被它盖掉 |
| "开 TUN 就能解决（网卡级接管）" | **错**。TUN 确实生效了（直连 curl 返回 405 / 0.54 秒为证），codex 仍失败——因为它**根本没在直连**，而是在连代理 65532 |
| "必须先开 VPN / 必须先开系统代理" | **不准确**。最小充分条件是"`.env` 里的代理地址上有服务在监听" |
| "需要打开 ChatGPT 桌面版 / WebCodex 才能用 CLI" | **错**（用户提问时我的回答是对的）：只需磁盘上的凭据 + 可达网络，与 GUI 是否运行无关 |
| 排查顺序：VPN → 系统代理 → 环境变量 → TUN → 防火墙/Defender | **顺序错了**。正解是**第一步就抓 codex 的出站连接**（`Get-NetTCPConnection -OwningProcess <PID>`），10 分钟即可定位 |

> 方法论：**"某程序连不上、curl 却能连"时，先看该程序自己在连哪里，不要从 VPN/代理假设出发。**

---

## 4. 遗留噪音（不影响主流程，可选清理）

1. MCP 鉴权失败：`tldraw` 需 OAuth（`codex-app.tldraw.xyz`）。
2. `chatgpt.com/backend-api/ps/mcp` 经代理返回 **451（法律原因）**，每次启动重试数次、拖慢启动。
3. `codex doctor` 报 `✗ desktop update and runtime CDN is unreachable` —— 该 CDN 域名可能未被 Clash 规则覆盖。

---

## 5. 复现命令

```powershell
# ① 诊断第一步：抓 codex 的出站连接（本次就是靠它破案的）
$exe = "C:\Users\ROG\AppData\Local\OpenAI\Codex\bin\9614f1d9b40d9c4f\codex.exe"
$p = Start-Process -FilePath $exe -ArgumentList @('exec','-s','read-only','-C','E:\output','--ephemeral','回答ok') -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 5
Get-NetTCPConnection -OwningProcess $p.Id | Select-Object RemoteAddress, RemotePort, State
Stop-Process -Id $p.Id -Force

# ② 核对 .env 端口 与 Clash 混合端口 是否一致
Get-Content C:\Users\ROG\.codex\.env
Get-NetTCPConnection -State Listen -LocalPort 7897

# ③ 探针（判据用；抓到 CONNECT 即证明该端口被当作代理）
& E:\node.exe E:\output\_tools\probe65532.mjs
```

---

## 6. 相关文件

| 文件 | 作用 |
|---|---|
| `E:\output\_DSH_OFFICE_STATE.md` §1.1 / 踩坑 #11 | 长期记忆中的权威登记 |
| `E:\output\codex_cli_channel_verdict.md` | 本文件（主题结论） |
| `E:\output\_tools\probe65532.mjs` | 端口探针（判据工具，可复用） |
| `C:\Users\ROG\.codex\.env.bak-20261016` | 修复前备份（回滚用） |
