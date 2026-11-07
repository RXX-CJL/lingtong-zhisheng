param([string]$From = '')

. (Join-Path $PSScriptRoot 'common.ps1')

Show-Header 'DSH 更新后 · 恢复之前的配置'
Write-KitLog 'restore: start'

Assert-DshStopped

if ([string]::IsNullOrWhiteSpace($From)) {
  $From = Get-ChildItem $BackupRoot -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like '*-before-update' } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1 -ExpandProperty FullName
}
if ([string]::IsNullOrWhiteSpace($From) -or -not (Test-Path $From)) {
  Write-Err2 '找不到 before-update 备份'
  Write-Host '  请先双击「1-更新前-备份」，或用 -From 指定备份目录。' -ForegroundColor Yellow
  exit 1
}

Write-Step '1/4 找到备份'
Write-Ok $From

Write-Step '2/4 备份当前状态（可回退）'
$safety = New-ProfileBackup 'before-restore'
Write-Ok "已备份到 $safety"

Write-Step '3/4 恢复 profile 文件'
foreach ($f in @('cordis.patch.yml', 'package.json', 'cordis.yml')) {
  $src = Join-Path $From $f
  $dst = Join-Path $ProfileDir $f
  if (Test-Path $src) { Copy-Item $src $dst -Force; Write-Ok "恢复 $f" }
  else { Write-Warn2 "备份中没有 $f，跳过" }
}

Write-Step '4/4 确保 0.2.1 兼容层'
Add-CompatBlockIfMissing (Join-Path $ProfileDir 'cordis.patch.yml')

$pkg = Get-Content (Join-Path $ProfileDir 'package.json') -Raw | ConvertFrom-Json
Write-Ok "bundles 数量：$($pkg.dsh.profile.bundles.Count)"
Write-KitLog "restore: from=$From bundles=$($pkg.dsh.profile.bundles.Count)"

Write-Host ''
Write-Host '完成。现在重新打开 DSH。' -ForegroundColor Green
Write-Host '若仍启动失败：点崩溃界面的「禁用第三方插件」，或双击「3-紧急-精简配置」。' -ForegroundColor Yellow
