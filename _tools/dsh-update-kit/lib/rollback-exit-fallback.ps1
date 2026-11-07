# rollback-exit-fallback.ps1 — 一键移除 desktop-exit-fallback 兜底插件
# 用途：装了兜底插件后若启动异常，跑这个恢复原状（不需要备份文件也能用）
$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$ProfileDir = 'C:\Users\ROG\.dsh\profiles\desktop'
$patchPath  = Join-Path $ProfileDir 'cordis.patch.yml'
$pluginPath = Join-Path $ProfileDir 'desktop-exit-fallback.mjs'

Write-Host ''
Write-Host '=== 回滚 desktop-exit-fallback ===' -ForegroundColor Cyan

if (-not (Test-Path $patchPath)) { Write-Host "[X] 找不到 $patchPath" -ForegroundColor Red; Read-Host "按回车退出"; exit 1 }

$stamp  = Get-Date -Format "yyyyMMdd-HHmmss"
$backup = Join-Path (Join-Path 'E:\output\_plugin-backups' $stamp) 'before-rollback-exit-fallback'
New-Item -ItemType Directory -Force -Path $backup | Out-Null
Copy-Item $patchPath (Join-Path $backup 'cordis.patch.yml') -Force
Write-Host ("  [OK] 已备份当前 patch 到 {0}" -f $backup) -ForegroundColor Green

$text  = [System.IO.File]::ReadAllText($patchPath)
$nl    = if ($text.Contains("`r`n")) { "`r`n" } else { "`n" }
$lines = New-Object System.Collections.Generic.List[string]
foreach ($l in ($text -split "`r?`n")) { $lines.Add($l) }

# 策略：定位引用本插件的 insert 块，把它连同紧邻其上的注释块（连续的 # 行 / 空行）一起删除。
$remove = @{}
for ($i = 0; $i -lt $lines.Count; $i++) {
  if ($lines[$i] -match "^\s*-\s*insert:\s*$") {
    $blockEnd = $i
    for ($j = $i + 1; $j -lt $lines.Count; $j++) {
      if ($lines[$j] -match "^\s+-\s" -or $lines[$j] -match "^\s{4,}\S") { $blockEnd = $j } else { break }
    }
    $blockText = ($lines[$i..$blockEnd] -join "`n")
    if ($blockText -match "desktop-exit-fallback") {
      for ($k = $i; $k -le $blockEnd; $k++) { $remove[$k] = $true }
      $t = $i - 1
      while ($t -ge 0 -and ($lines[$t] -match "^\s*#" -or $lines[$t].Trim() -eq "")) { $remove[$t] = $true; $t-- }
    }
  }
}

$out = New-Object System.Collections.Generic.List[string]
for ($i = 0; $i -lt $lines.Count; $i++) { if (-not $remove.ContainsKey($i)) { $out.Add($lines[$i]) } }
$new = ($out -join $nl).TrimEnd() + $nl
[System.IO.File]::WriteAllText($patchPath, $new, [System.Text.UTF8Encoding]::new($false))
Write-Host ("  [OK] 已移除 {0} 行（insert 块 + 上方注释）" -f $remove.Count) -ForegroundColor Green

if (Test-Path $pluginPath) {
  Remove-Item $pluginPath -Force
  Write-Host '  [OK] 已删除 desktop-exit-fallback.mjs' -ForegroundColor Green
}

# ── 校验 ──
$check = [System.IO.File]::ReadAllText($patchPath)
$hasRef    = $check -match "desktop-exit-fallback"
$hasCompat = ($check -match "inject:\s*\[\s*webStartup\s*\]") -and ($check -match "-\s*id:\s*connection")
Write-Host ''
if (-not $hasRef) { Write-Host "  [OK] 已完全移除插件引用" -ForegroundColor Green }
else            { Write-Host "  [!] 仍有残留引用，请手工检查 cordis.patch.yml" -ForegroundColor Yellow }
if ($hasCompat) { Write-Host "  [OK] 0.2.1 兼容层仍在（启动不受影响）" -ForegroundColor Green }
else            { Write-Host "  [!] 兼容层不见了，启动可能失败！请从备份恢复" -ForegroundColor Red }

Write-Host ''
Write-Host '完成。重新打开 DSH 即可。' -ForegroundColor Green
Read-Host "按回车退出"
