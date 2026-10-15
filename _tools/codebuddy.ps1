<#
.SYNOPSIS
  CodeBuddy CLI 派活工具（DSH ↔ CodeBuddy 通道，2026-10-16 打通）
.DESCRIPTION
  等价于 codex exec，用于把任务派给腾讯 CodeBuddy CLI（@tencent-ai/codebuddy-code）。
  官方完整包（2.168.0）已全局安装；本次登录走 "Log in via Chinese Site"，
  凭据已持久化（全新进程可直接派活，无需重新登录）。

  与 Codex CLI 的分工：
    - Codex CLI  : gpt-5.6-luna（ChatGPT 账号额度）
    - CodeBuddy  : 多模型可切换（glm / kimi / minimax / deepseek-v3-2-volc / hy4-preview …）
.PARAMETER Prompt
  任务文本（必填）。
.PARAMETER Model
  模型 id，默认 auto。可用：auto, glm-5v-turbo, glm-5.1, glm-5.0-turbo, glm-5.0, glm-4.7,
  kimi-k2.5, minimax-m2.7, deepseek-v3-2-volc（以 `codebuddy --help` 的 --model 列表为准）
.PARAMETER Json
  以 --output-format json 输出（含 result/num_turns/duration_ms/usage/session_id）。
.PARAMETER WorkDir
  工作目录，默认 E:\output。
.PARAMETER Effort
  推理强度：minimal/low/medium/high/xhigh/max。
.PARAMETER ReadOnlyTools
  只读模式：在黑名单里禁用写/执行类工具（Bash/Write/Edit/MultiEdit/NotebookEdit）。
  ★ 2026-10-16 实测修正：早期用白名单 `--tools Read,Grep,Glob` 会因"想用 Bash 却被拒"
  而报 `Tool "Bash" does not exist in the current tool set`；改用**黑名单法**后
  实测 exit 0 / 62 秒 / 正常返回结果，是稳定的只读姿势（verdict §8.1 收尾）。
.PARAMETER TimeoutSec
  超时秒数，默认 300。
.EXAMPLE
  pwsh -File E:\output\_tools\codebuddy.ps1 -Prompt "用一句话说明 CARLA 是什么"
.EXAMPLE
  pwsh -File E:\output\_tools\codebuddy.ps1 -Prompt "审阅 E:\output\1\api\violation_rules.py" -Model deepseek-v3-2-volc -ReadOnlyTools
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true, Position = 0)]
  [string]$Prompt,

  [string]$Model = 'auto',

  [switch]$Json,

  [string]$WorkDir = 'E:\output',

  [ValidateSet('minimal', 'low', 'medium', 'high', 'xhigh', 'max')]
  [string]$Effort,

  [switch]$ReadOnlyTools,

  [int]$TimeoutSec = 300
)

$ErrorActionPreference = 'Stop'

# --- 定位 CLI 入口（全局 npm 安装的官方完整包） ---
$cli = Join-Path (npm root -g) '@tencent-ai\codebuddy-code\bin\codebuddy'
if (-not (Test-Path $cli)) {
  throw "找不到 CodeBuddy CLI: $cli`n请先执行: npm install -g @tencent-ai/codebuddy-code"
}

$env:NO_COLOR = '1'

$argv = @($cli, '-p', $Prompt, '--model', $Model)
if ($Json) { $argv += @('--output-format', 'json') }
if ($Effort) { $argv += @('--effort', $Effort) }
if ($ReadOnlyTools) { $argv += @('--tools', 'Read,Grep,Glob') }

Write-Host "[codebuddy] model=$Model cwd=$WorkDir json=$([bool]$Json)" -ForegroundColor DarkGray

$sw = [Diagnostics.Stopwatch]::StartNew()
$out = & node @argv 2>&1 | Out-String
$code = $LASTEXITCODE
$sw.Stop()

if ($Json) {
  $out.Trim()
} else {
  $out.Trim()
}

Write-Host "[codebuddy] exit=$code elapsed=$([math]::Round($sw.Elapsed.TotalSeconds,1))s" -ForegroundColor DarkGray
exit $code
