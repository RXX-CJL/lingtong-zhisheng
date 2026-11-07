# common.ps1 — DSH 更新工具包共用函数（由各脚本 dot-source 引入）
$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

$script:KitDir     = Split-Path -Parent $PSScriptRoot
$script:ProfileDir = 'C:\Users\ROG\.dsh\profiles\desktop'
$script:BackupRoot = 'E:\output\_plugin-backups'
$script:LogDir     = Join-Path $KitDir 'logs'

function Show-Header([string]$Title) {
  Write-Host ''
  Write-Host ('=' * 64) -ForegroundColor DarkGray
  Write-Host "  $Title" -ForegroundColor White
  Write-Host ('=' * 64) -ForegroundColor DarkGray
}

function Write-Step([string]$Text) { Write-Host ''; Write-Host "[$Text]" -ForegroundColor Cyan }
function Write-Ok([string]$Text)   { Write-Host "  [OK] $Text" -ForegroundColor Green }
function Write-Warn2([string]$Text){ Write-Host "  [!] $Text" -ForegroundColor Yellow }
function Write-Err2([string]$Text) { Write-Host "  [X] $Text" -ForegroundColor Red }

function Get-DshProcesses {
  @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -like '*DeepSeek*' })
}

function Assert-DshStopped {
  while ($true) {
    $procs = Get-DshProcesses
    if ($procs.Count -eq 0) { Write-Ok 'DSH 未运行'; return }
    $list = ($procs | ForEach-Object { "$($_.ProcessName)($($_.Id))" }) -join ', '
    Write-Warn2 "检测到 DSH 仍在运行：$list"
    Write-Host '  请完全退出 DSH（含托盘图标），然后按 Enter 重新检测（输入 Q 退出）...' -ForegroundColor Yellow
    $ans = Read-Host
    if ($ans -eq 'Q' -or $ans -eq 'q') { throw '用户取消：DSH 未关闭' }
  }
}

function New-ProfileBackup([string]$Tag) {
  $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
  $dir = Join-Path $BackupRoot "$stamp-$Tag"
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  $files = @('cordis.patch.yml', 'package.json', 'cordis.yml', 'pnpm-lock.yaml')
  foreach ($f in $files) {
    $src = Join-Path $ProfileDir $f
    if (Test-Path $src) { Copy-Item $src (Join-Path $dir $f) -Force }
  }
  return $dir
}

function Write-KitLog([string]$Line) {
  New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
  $file = Join-Path $LogDir ((Get-Date -Format 'yyyyMMdd') + '.log')
  Add-Content -Path $file -Value ('[{0}] {1}' -f (Get-Date -Format 'HH:mm:ss'), $Line) -Encoding utf8
}

function Get-CompatBlockText {
  $nl = "`r`n"
  (@(
    ''
    '# ══════════════════════════════════════════════════════════════════════════'
    '# 0.2.1 兼容层（勿删）'
    '# DSH 0.2.1 把 connection 的依赖改为 [webStartup]，服务 webRuntime 改名 webApp；'
    '# 但 @hr98w/dsh-memory@0.1.4 与 dsh-vision-router@3.0.3 的 bundle patch 仍写死'
    '# inject: [webRuntime, webServer]，会把官方依赖覆盖回去导致启动失败。'
    '# 本 profile 层（最后应用）把它压回官方值。证据：'
    '# asar/dsh/node_modules/@deepseek-ai/dsh-web-app/cordis.patch.yml'
    '# ══════════════════════════════════════════════════════════════════════════'
    '- id: connection'
    "  name: '@deepseek-ai/dsh-client-connection'"
    '  inject: [webStartup]'
  ) -join $nl) + $nl
}

function Test-CompatBlock([string]$Path) {
  if (-not (Test-Path $Path)) { return $false }
  $text = [System.IO.File]::ReadAllText($Path)
  return ($text.Contains('- id: connection') -and $text.Contains('inject: [webStartup]'))
}

function Add-CompatBlockIfMissing([string]$Path) {
  if (Test-CompatBlock $Path) { Write-Ok '兼容层已存在'; return }
  $text = [System.IO.File]::ReadAllText($Path)
  $nl = if ($text.Contains("`r`n")) { "`r`n" } else { "`n" }
  $block = Get-CompatBlockText
  if ($nl -eq "`n") { $block = $block.Replace("`r`n", "`n") }
  [System.IO.File]::WriteAllText($Path, $text.TrimEnd() + $nl + $block, [System.Text.UTF8Encoding]::new($false))
  Write-Ok '已追加兼容层'
}
