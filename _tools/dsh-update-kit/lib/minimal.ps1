. (Join-Path $PSScriptRoot 'common.ps1')

Show-Header 'DSH 紧急恢复 · 精简配置（只保留官方基础）'
Write-KitLog 'minimal: start'

Assert-DshStopped

Write-Step '1/3 备份当前状态'
$dir = New-ProfileBackup 'before-minimal'
Write-Ok "已备份到 $dir"

Write-Step '2/3 重置 bundles'
$pkgPath = Join-Path $ProfileDir 'package.json'
$pkg = Get-Content $pkgPath -Raw | ConvertFrom-Json
$pkg.dsh.profile.bundles = @('@deepseek-ai/dsh-base', '@deepseek-ai/dsh-web-app')
$json = $pkg | ConvertTo-Json -Depth 10
[System.IO.File]::WriteAllText($pkgPath, $json + "`n", [System.Text.UTF8Encoding]::new($false))
Write-Ok 'bundles = @deepseek-ai/dsh-base, @deepseek-ai/dsh-web-app'

Write-Step '3/3 完成'
Write-KitLog "minimal: backup=$dir"
Write-Host '现在重新打开 DSH 应能正常启动（第三方插件不加载）。' -ForegroundColor Green
Write-Host '要恢复插件：等 DSH 稳定后完全退出，再双击「2-更新后-恢复」。' -ForegroundColor Yellow
