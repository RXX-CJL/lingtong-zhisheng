. (Join-Path $PSScriptRoot 'common.ps1')

Show-Header 'DSH 0.2.1 恢复 · 应用预置配置（16 个插件）'
Write-KitLog 'apply-staged: start'

Assert-DshStopped

$kit = Split-Path -Parent $PSScriptRoot
$staged = Join-Path $kit 'staged'
$pairs = @(
  @{ Name = 'cordis.patch.yml'; Src = (Join-Path $staged 'cordis.patch.yml') },
  @{ Name = 'package.json';      Src = (Join-Path $staged 'package.json') }
)

Write-Step '1/4 检查预置文件'
foreach ($p in $pairs) {
  if (-not (Test-Path $p.Src)) { Write-Err2 ("缺少 {0}" -f $p.Src); exit 1 }
  Write-Ok ("找到 {0}" -f $p.Src)
}

Write-Step '2/4 备份当前状态'
$dir = New-ProfileBackup 'before-apply-staged'
Write-Ok "已备份到 $dir"

Write-Step '3/4 应用配置'
foreach ($p in $pairs) {
  Copy-Item $p.Src (Join-Path $ProfileDir $p.Name) -Force
  Write-Ok ("已应用 {0}" -f $p.Name)
}

Write-Step '4/4 校验'
$patchPath = Join-Path $ProfileDir 'cordis.patch.yml'
if (-not (Test-CompatBlock $patchPath)) { Write-Err2 '兼容层缺失，停止'; exit 1 }
Write-Ok '兼容层存在（connection → webStartup）'
$pkg = Get-Content (Join-Path $ProfileDir 'package.json') -Raw | ConvertFrom-Json
Write-Ok ("bundles 数量：{0}" -f $pkg.dsh.profile.bundles.Count)

Write-KitLog "apply-staged: ok bundles=$($pkg.dsh.profile.bundles.Count) backup=$dir"
Write-Host ''
Write-Host '完成。现在重新打开 DSH。' -ForegroundColor Green
Write-Host '若仍启动失败：点崩溃界面「禁用第三方插件」，或双击「3-紧急-精简配置」。' -ForegroundColor Yellow
