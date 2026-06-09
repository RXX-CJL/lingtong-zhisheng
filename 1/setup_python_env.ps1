Write-Host "=============================================="
Write-Host "      Python环境变量配置脚本"
Write-Host "=============================================="
Write-Host ""

$pythonPath = "C:\Users\ROG\AppData\Local\Programs\Python\Python312"
$scriptsPath = "C:\Users\ROG\AppData\Local\Programs\Python\Python312\Scripts"

Write-Host "Python安装路径: $pythonPath"
Write-Host "Scripts路径: $scriptsPath"
Write-Host ""

if (-not (Test-Path $pythonPath)) {
    Write-Host "错误: Python路径不存在!" -ForegroundColor Red
    exit 1
}

Write-Host "正在配置用户级环境变量..."
$currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")

if ($currentPath -notlike "*Python312*") {
    $newPath = $currentPath + ";" + $pythonPath + ";" + $scriptsPath
    [Environment]::SetEnvironmentVariable("PATH", $newPath, "User")
    Write-Host "✅ 用户级环境变量已更新" -ForegroundColor Green
} else {
    Write-Host "✅ Python已在用户级PATH中" -ForegroundColor Green
}

Write-Host ""
Write-Host "正在配置系统级环境变量..."
$systemPath = [Environment]::GetEnvironmentVariable("PATH", "Machine")

if ($systemPath -notlike "*Python312*") {
    $newSystemPath = $systemPath + ";" + $pythonPath + ";" + $scriptsPath
    try {
        [Environment]::SetEnvironmentVariable("PATH", $newSystemPath, "Machine")
        Write-Host "✅ 系统级环境变量已更新" -ForegroundColor Green
    } catch {
        Write-Host "⚠ 系统级环境变量更新失败（可能需要管理员权限）" -ForegroundColor Yellow
        Write-Host "   请手动以管理员身份运行此脚本或手动配置"
    }
} else {
    Write-Host "✅ Python已在系统级PATH中" -ForegroundColor Green
}

Write-Host ""
Write-Host "=============================================="
Write-Host "配置完成!"
Write-Host ""
Write-Host "注意："
Write-Host "1. 请关闭当前终端并重新打开"
Write-Host "2. 或重启电脑以确保环境变量生效"
Write-Host "3. 验证命令: python --version 和 pip --version"
Write-Host "=============================================="