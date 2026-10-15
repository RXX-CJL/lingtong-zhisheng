<#
.SYNOPSIS
  Qoder CN CLI 派活工具（DSH ↔ Qoder 通道，2026-10-16 打通，第四条 AI 通道）
.DESCRIPTION
  等价于 codex exec / codebuddy -p，用于把任务派给 Qoder CN CLI（@qodercn-ai/qoderclicn）。
  ⚠ 命令名避坑：npm 包同时提供 qodercn 与 qoderclicn 两个 bin，其中 qodercn 会
  **遮蔽 Qoder CN IDE 自带的 qodercn 壳命令**（npm bin 在 PATH 更靠前）。
  本工具统一使用 qoderclicn（未遮蔽的那个）；npm 生成的 qodercn 三个 shim 已被
  改名为 *.npm-disabled-qodercli 以保护 IDE 命令。若将来 npm 升级后遮蔽重现，
  重跑同一条改名命令即可。

  与其它通道的分工：
    - Codex CLI   : gpt-5.6-luna（ChatGPT 账号额度）
    - CodeBuddy   : GLM / Kimi / MiniMax / DeepSeek-V3.2（腾讯账号，credits 计费）
    - Qoder CN    : Qwen3.8-Max / DeepSeek-V4-Pro / GLM-5.3 / Kimi-K3 等 15 个（credits 计费）
.PARAMETER Prompt
  任务文本（必填）。
.PARAMETER Model
  模型名，默认 auto。实测账号可用：Auto, Fast, Qwen3.8-Max, Qwen3.8-Flash, Qwen3.7-Max,
  Qwen3.7-Plus, Qwen3.7-Flash, DeepSeek-V4-Pro, DeepSeek-Flash, GLM-5.3, GLM-5.3-Flash,
  GLM-5.2, Kimi-K3, Kimi-K2.8-Preview, MiniMax-M2.7（以 qoderclicn --list-models 为准）。
.PARAMETER Json
  以 -o json 输出（含 result / duration_ms / num_turns / total_credits / session_id）。
.PARAMETER WorkDir
  工作目录（-w），默认 E:\output。
.PARAMETER Effort
  推理强度 --reasoning-effort：low/medium/high/xhigh/max。
.PARAMETER ReadOnly
  只读模式：--permission-mode auto 基础上再禁用写类工具（Bash/Write/Edit）。
  ★ Headless 下若权限为 ask 会被自动拒绝，所以派活必须显式给权限模式。
.PARAMETER Yolo
  完全跳过权限检查（--dangerously-skip-permissions）。仅在可信任务上使用。
.PARAMETER TimeoutSec
  超时秒数，默认 420。
.EXAMPLE
  pwsh -File E:\output\_tools\qoder.ps1 -Prompt "用一句话说明 CARLA 是什么"
.EXAMPLE
  pwsh -File E:\output\_tools\qoder.ps1 -Prompt "审阅 E:\output\1\api\violation_rules.py 的边界条件" -Model DeepSeek-V4-Pro -ReadOnly -Json
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true, Position = 0)]
  [string]$Prompt,

  [string]$Model = 'auto',

  [switch]$Json,

  [string]$WorkDir = 'E:\output',

  [ValidateSet('low', 'medium', 'high', 'xhigh', 'max')]
  [string]$Effort,

  [switch]$ReadOnly,

  [switch]$Yolo,

  [int]$TimeoutSec = 420
)

$ErrorActionPreference = 'Stop'
$env:NO_COLOR = '1'

# ⚠ 参数顺序铁律：`-p/--print` 是**布尔开关**，提示词是**位置参数 query**。
#    实测：prompt 之后出现的选项会被并入 query（原样进提示词）。因此
#    选项一律在前，prompt 永远放最后。
$cliArgs = @('-m', $Model, '-w', $WorkDir)

if ($Yolo) {
  $cliArgs += '--dangerously-skip-permissions'
}
else {
  $cliArgs += @('--permission-mode', 'auto')
}

if ($ReadOnly) { $cliArgs += @('--disallowed-tools', 'Bash,Write,Edit,MultiEdit,NotebookEdit') }
if ($Json) { $cliArgs += @('-o', 'json') }
if ($Effort) { $cliArgs += @('--reasoning-effort', $Effort) }
$cliArgs += @('-p', $Prompt)

# 直接走 bundle 入口（比 npm shim 更可控；shim 在不同 shell 下参数转发有差异）
$js = Join-Path (npm root -g) '@qodercn-ai\qoderclicn\bundle\qoderclicn.js'
if (-not (Test-Path $js)) {
  throw "找不到 Qoder CLI 入口: $js`n请先执行: npm install -g @qodercn-ai/qoderclicn"
}

Write-Host "[qoder] model=$Model cwd=$WorkDir json=$([bool]$Json) readonly=$([bool]$ReadOnly) yolo=$([bool]$Yolo)" -ForegroundColor DarkGray

$sw = [Diagnostics.Stopwatch]::StartNew()
$out = & node $js @cliArgs 2>&1 | Out-String
$code = $LASTEXITCODE
$sw.Stop()

$out.Trim()
Write-Host "[qoder] exit=$code elapsed=$([math]::Round($sw.Elapsed.TotalSeconds,1))s" -ForegroundColor DarkGray
exit $code
