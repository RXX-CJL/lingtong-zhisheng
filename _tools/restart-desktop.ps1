# 重启 DSH Desktop（等价「一键重启」）
# 用途：插件装错 / 界面卡死 / 需要完全重启时。★ 会中断所有正在进行的 DSH 会话。
# 用法：双击同目录的 restart-desktop.bat（必须由用户手动启动，不要从 DSH 会话内调用）。
$ErrorActionPreference = 'Continue'
$exe = 'F:\AI\DeepSeek-Harness\deepseek-harness-dsh-desktop\DeepSeek Harness.exe'

if (-not (Test-Path $exe)) { Write-Host "[!] 找不到 Desktop 主程序: $exe"; Read-Host '按回车退出'; exit 1 }

$main = Get-CimInstance Win32_Process -Filter "Name = 'DeepSeek Harness.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -notmatch '--type=' } |
        Select-Object -First 1

if (-not $main) {
    Write-Host '[i] 未发现运行中的 DSH Desktop，直接启动 ...'
    Start-Process -FilePath $exe -WorkingDirectory (Split-Path $exe)
    Write-Host '[✓] 已完成。'
    Read-Host '按回车退出'
    exit 0
}

$pid0 = $main.ProcessId
Write-Host "[1/3] 正在优雅关闭主进程 PID $pid0（发送 WM_CLOSE，让 Electron 走正常退出流程）..."
taskkill /PID $pid0 2>$null | Out-Null

for ($i = 0; $i -lt 24; $i++) {
    Start-Sleep -Milliseconds 500
    if (-not (Get-Process -Id $pid0 -ErrorAction SilentlyContinue)) { break }
}

if (Get-Process -Id $pid0 -ErrorAction SilentlyContinue) {
    Write-Host '[2/3] 优雅关闭超时（12 秒），强制结束 ...'
    taskkill /F /PID $pid0 2>$null | Out-Null
    Start-Sleep -Seconds 2
} else {
    Write-Host '[2/3] 已正常退出。'
}

Write-Host '[3/3] 正在重新启动 ...'
Start-Process -FilePath $exe -WorkingDirectory (Split-Path $exe)
Start-Sleep -Seconds 3
Write-Host '[✓] 重启流程完成。窗口未出现时，请手动双击桌面快捷方式。'
Read-Host '按回车退出'
