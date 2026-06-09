$pythonPath = "C:\Users\ROG\AppData\Local\Programs\Python\Python312"
$scriptsPath = "C:\Users\ROG\AppData\Local\Programs\Python\Python312\Scripts"

Write-Host "=== Python环境修复 ==="
Write-Host "Python路径: $pythonPath"
Write-Host "Scripts路径: $scriptsPath"
Write-Host ""

if (-not (Test-Path $pythonPath)) {
    Write-Host "错误: Python路径不存在!" -ForegroundColor Red
    exit 1
}

Write-Host "1. 更新用户级环境变量..."
$currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($currentPath -notlike "*Python312*") {
    $newPath = "$pythonPath;$scriptsPath;$currentPath"
    [Environment]::SetEnvironmentVariable("PATH", $newPath, "User")
    Write-Host "用户级PATH已更新" -ForegroundColor Green
} else {
    Write-Host "Python已在用户级PATH中" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "2. 更新系统级环境变量..."
try {
    $systemPath = [Environment]::GetEnvironmentVariable("PATH", "Machine")
    if ($systemPath -notlike "*Python312*") {
        $newSystemPath = "$pythonPath;$scriptsPath;$systemPath"
        [Environment]::SetEnvironmentVariable("PATH", $newSystemPath, "Machine")
        Write-Host "系统级PATH已更新" -ForegroundColor Green
    } else {
        Write-Host "Python已在系统级PATH中" -ForegroundColor Yellow
    }
} catch {
    Write-Host "系统级更新失败（可能需要管理员权限）" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== 操作完成 ==="
Write-Host "请关闭所有终端并重新打开"
Write-Host "验证命令: python --version"
Write-Host "验证命令: pip --version"