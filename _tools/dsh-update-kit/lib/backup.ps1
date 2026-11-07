. (Join-Path $PSScriptRoot 'common.ps1')

Show-Header 'DSH 更新前 · 备份当前配置'
Write-KitLog 'backup: start'

Write-Step '1/3 备份 profile 配置'
$dir = New-ProfileBackup 'before-update'
Write-Ok "备份到 $dir"
Get-ChildItem $dir | ForEach-Object { Write-Host ("      {0} ({1} B)" -f $_.Name, $_.Length) }

Write-Step '2/3 检查长驻子进程'
$names = @('cua-driver', 'media-bridge-win32-x64')
$found = @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $names -contains $_.ProcessName })
if ($found.Count -eq 0) {
  Write-Ok '未发现 cua-driver / media-bridge，更新时应能正常关闭'
} else {
  $found | ForEach-Object { Write-Warn2 ("运行中：{0} (PID {1})" -f $_.ProcessName, $_.Id) }
  Write-Host '  它们持有 stdio 管道，会让 DSH 关闭时多卡约 10 秒，拖慢更新安装。' -ForegroundColor Yellow
  Write-Host '  是否现在结束它们？(Y/N，默认 N)' -ForegroundColor Yellow
  $ans = Read-Host
  if ($ans -eq 'Y' -or $ans -eq 'y') {
    foreach ($p in $found) {
      try { Stop-Process -Id $p.Id -Force -ErrorAction Stop; Write-Ok ("已结束 {0}({1})" -f $p.ProcessName, $p.Id) }
      catch { Write-Warn2 ("结束失败：{0}" -f $_.Exception.Message) }
    }
  } else {
    Write-Warn2 '已跳过。更新若卡住，手动关掉壁纸引擎 / computer-use 再试。'
  }
}

Write-Step '3/3 完成'
Write-KitLog "backup: dir=$dir"
Write-Host '现在可以去 DSH 里点「检查更新」。' -ForegroundColor Green
Write-Host '更新完如果启动有问题，先完全退出 DSH，再双击「2-更新后-恢复」。' -ForegroundColor Yellow
