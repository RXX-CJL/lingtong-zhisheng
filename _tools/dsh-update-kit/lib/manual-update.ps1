# manual-update.ps1 — DSH Desktop 手动静默更新（绕过应用内更新器的「必须优雅关闭」门）
#
# 为什么需要它：应用内更新在 quitAndInstall 之前会调用 host.stop(requireGraceful)，
# 要求 Host 收到 shutdown 后 10 秒内退出。若 Host 还持有活跃句柄（长驻子进程 / 未关闭
# 连接等）就不退出，主进程判定 "graceful deadline exceeded" → 拒绝安装：
#   "Host did not complete graceful task teardown (exit null, signal SIGTERM,
#    shutdown acknowledged true, graceful deadline exceeded true)"
# 本脚本改成：先自己把 DSH 关干净（优雅 → 超时强杀整棵树），再用 electron-updater
# 用的同一个静默参数 /S 跑已下载的安装包，最后校验并重新启动。
#
# 用法：双击同目录的 4-手动更新-静默安装.bat
# 加 -DryRun 只体检不动手。加 -NoLaunch 装完不自动启动。

param(
  [switch]$DryRun,
  [switch]$NoLaunch
)

$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$KitDir     = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$LogDir     = Join-Path $KitDir 'logs'
$ProfileDir = 'C:\Users\ROG\.dsh\profiles\desktop'
$UpdaterDir = Join-Path $env:LOCALAPPDATA '@deepseek-aidsh-desktop-updater\pending'
$ExeName    = 'DeepSeek Harness.exe'
$GracefulMs = 15000

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogFile = Join-Path $LogDir ('manual-update-{0}.log' -f (Get-Date -Format 'yyyyMMdd-HHmmss'))

function Log([string]$Text) {
  $line = '[{0}] {1}' -f (Get-Date -Format 'HH:mm:ss'), $Text
  Write-Host $Text
  Add-Content -LiteralPath $LogFile -Value $line -Encoding utf8
}
function Ok([string]$t)   { Log ("  [OK] " + $t) }
function Warn([string]$t) { Log ("  [!] " + $t) }
function Bad([string]$t)  { Log ("  [X] " + $t) }
function Step([string]$t) { Log ''; Log ("== " + $t + " ==") }

function Get-DshMainProcess {
  Get-CimInstance Win32_Process -Filter ("Name = '{0}'" -f $ExeName) -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -notmatch '--type=' -and $_.CommandLine -match 'dsh-desktop-host' } |
    Select-Object -First 1
}
function Get-DshProcesses {
  @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -like '*DeepSeek Harness*' })
}
function Get-InstalledVersion {
  $roots = @(
    'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall',
    'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall',
    'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall'
  )
  foreach ($r in $roots) {
    foreach ($k in (Get-ChildItem $r -ErrorAction SilentlyContinue)) {
      $p = Get-ItemProperty $k.PSPath -ErrorAction SilentlyContinue
      if ($p.DisplayName -match 'DeepSeek') {
        return [pscustomobject]@{ Version = $p.DisplayVersion; Location = $p.InstallLocation }
      }
    }
  }
  return $null
}

Log '============================================================'
Log '  DSH Desktop 手动静默更新'
Log '============================================================'
Log ("日志：{0}" -f $LogFile)
if ($DryRun) { Warn 'DryRun：只体检，不关进程、不安装' }

# ── 1. 找到已下载的安装包 ─────────────────────────────────────────
Step '1/6 检查已下载的更新包'
$infoPath = Join-Path $UpdaterDir 'update-info.json'
if (-not (Test-Path $infoPath)) { Bad ("找不到 {0} —— 请先在应用内点『检查更新』让它下载完" -f $infoPath); exit 1 }
$info = Get-Content -LiteralPath $infoPath -Raw | ConvertFrom-Json
$installer = Join-Path $UpdaterDir $info.fileName
if (-not (Test-Path $installer)) { Bad ("安装包不存在：{0}" -f $installer); exit 1 }
Ok ("安装包：{0}" -f $installer)
$size = (Get-Item $installer).Length
Ok ("大小：{0:N0} 字节" -f $size)

Step '1b/6 校验安装包完整性（sha512）'
$sha = [System.Security.Cryptography.SHA512]::Create()
$fs = [System.IO.File]::OpenRead($installer)
try { $hash = [Convert]::ToBase64String($sha.ComputeHash($fs)) } finally { $fs.Dispose(); $sha.Dispose() }
if ($hash -eq $info.sha512) { Ok 'sha512 与 update-info.json 一致' }
else { Bad 'sha512 不匹配 —— 安装包损坏，请重新下载，已中止'; Log ("  期望 " + $info.sha512); Log ("  实际 " + $hash); exit 1 }

$current = Get-InstalledVersion
if ($current) { Ok ("当前安装：{0} @ {1}" -f $current.Version, $current.Location) }
else { Warn '未能从注册表读到当前版本（继续）' }

# ── 2. 备份 profile 配置 ─────────────────────────────────────────
Step '2/6 备份 profile 三件套'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backup = Join-Path (Join-Path 'E:\output\_plugin-backups' $stamp) 'before-manual-update'
New-Item -ItemType Directory -Force -Path $backup | Out-Null
foreach ($f in @('cordis.patch.yml', 'package.json', 'cordis.yml', 'pnpm-lock.yaml')) {
  $src = Join-Path $ProfileDir $f
  if (Test-Path $src) { Copy-Item $src (Join-Path $backup $f) -Force }
}
Ok ("已备份到 {0}" -f $backup)

if ($DryRun) {
  Step 'DryRun 结束'
  Ok '体检全部通过。去掉 -DryRun 或直接双击 .bat 即可真正更新。'
  exit 0
}

# ── 3. 关掉 DSH（优雅 → 超时强杀整棵树）──────────────────────────
Step '3/6 关闭 DSH'
$main = Get-DshMainProcess
if ($main) {
  Log ("  主进程 PID {0}，发送 WM_CLOSE（优雅关闭）..." -f $main.ProcessId)
  $null = taskkill /PID $main.ProcessId 2>&1
} else {
  Warn '未发现运行中的主进程（可能已退出）'
}
$deadline = (Get-Date).AddMilliseconds($GracefulMs)
while ((Get-Date) -lt $deadline) {
  if ((Get-DshProcesses).Count -eq 0) { break }
  Start-Sleep -Milliseconds 400
}
$left = Get-DshProcesses
if ($left.Count -eq 0) {
  Ok 'DSH 已优雅退出'
} else {
  Warn ("仍有 {0} 个进程存活，强制结束进程树" -f $left.Count)
  if ($main) { $null = taskkill /F /T /PID $main.ProcessId 2>&1 }
  Start-Sleep -Seconds 2
  $still = Get-DshProcesses
  if ($still.Count -gt 0) {
    foreach ($p in $still) { $null = taskkill /F /PID $p.Id 2>&1 }
    Start-Sleep -Seconds 2
  }
  if ((Get-DshProcesses).Count -eq 0) { Ok '已强制结束' }
  else { Bad '仍有进程无法结束 —— 请在任务管理器里手动结束后重跑本脚本'; exit 1 }
}

# ── 4. 静默安装 ─────────────────────────────────────────────────
Step '4/6 静默安装（NSIS /S，与应用内更新器同参数）'
Log ("  启动：{0} /S" -f $installer)
$proc = Start-Process -FilePath $installer -ArgumentList '/S' -PassThru -Wait
Log ("  安装器退出码：{0}" -f $proc.ExitCode)
if ($proc.ExitCode -ne 0) { Bad '安装器返回非 0，更新可能失败，已中止'; exit 1 }

$after = Get-InstalledVersion
if (-not $after) { Bad '安装后读不到注册表版本 —— 安装可能未生效'; exit 1 }
Ok ("安装后版本：{0} @ {1}" -f $after.Version, $after.Location)
if ($current -and $after.Location -ne $current.Location) {
  Warn ("安装位置发生变化：{0} → {1}" -f $current.Location, $after.Location)
}

# ── 5. 校验 profile 与兼容层 ────────────────────────────────────
Step '5/6 校验 profile 配置与启动兼容层'
$patchPath = Join-Path $ProfileDir 'cordis.patch.yml'
if (-not (Test-Path $patchPath)) { Bad ("profile patch 不存在：{0}" -f $patchPath); exit 1 }
$patchText = [System.IO.File]::ReadAllText($patchPath)
$hasCompat = ($patchText.Contains('- id: connection') -and $patchText.Contains('inject: [webStartup]'))
$hasFallback = $patchText.Contains('desktop-exit-fallback')
if ($hasCompat) { Ok 'connection → webStartup 兼容层存在' } else { Warn '兼容层缺失（若新版官方又改了依赖，启动会失败）' }
if ($hasFallback) { Ok 'desktop-exit-fallback 兜底插件行存在' } else { Warn '兜底插件行缺失（应用内更新仍会报优雅关闭失败）' }

$asar = Join-Path $after.Location 'resources\app.asar'
if (Test-Path $asar) {
  $bytes = [System.IO.File]::ReadAllBytes($asar)
  $needle = [System.Text.Encoding]::UTF8.GetBytes('inject: [webStartup]')
  $found = $false
  for ($i = 0; $i -le $bytes.Length - $needle.Length; $i++) {
    if ($bytes[$i] -ne $needle[0]) { continue }
    $hit = $true
    for ($j = 1; $j -lt $needle.Length; $j++) { if ($bytes[$i + $j] -ne $needle[$j]) { $hit = $false; break } }
    if ($hit) { $found = $true; break }
  }
  if ($found) { Ok '新版本 app.asar 仍声明 inject: [webStartup]（兼容层继续有效）' }
  else { Warn '新版本 app.asar 里找不到 inject: [webStartup] —— 官方可能又改了 connection 依赖，启动前请留意' }
}

# ── 6. 重启 ─────────────────────────────────────────────────────
if ($NoLaunch) {
  Step '6/6 已按要求跳过启动'
  Ok '更新完成。请手动打开 DSH。'
  exit 0
}
Step '6/6 重新启动 DSH'
$exe = Join-Path $after.Location $ExeName
if (-not (Test-Path $exe)) { Bad ("找不到主程序：{0}" -f $exe); exit 1 }
Start-Process -FilePath $exe -WorkingDirectory $after.Location
Start-Sleep -Seconds 3
if ((Get-DshProcesses).Count -gt 0) { Ok 'DSH 已启动' } else { Warn '未见进程，请手动双击快捷方式' }

Log ''
Log '============================================================'
Log ('  完成。版本 {0}' -f $after.Version)
Log ('  回滚：把 {0} 里的三件套复制回 profile 目录' -f $backup)
Log '============================================================'
