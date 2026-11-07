[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Output "=== 新版本里 icon-chatgpt.ico 在不在 ==="
$new = "C:\Program Files\WindowsApps\OpenAI.Codex_26.1027.3384.0_x64__2p2nqsd0c76g0"
$ico = Join-Path $new "app\resources\icon-chatgpt.ico"
Write-Output ("  " + $ico)
Write-Output ("  Exists = " + (Test-Path $ico))

Write-Output ""
Write-Output "=== app\resources 下的图标文件 ==="
Get-ChildItem (Join-Path $new "app\resources") -Filter "*.ico" -ErrorAction SilentlyContinue |
  ForEach-Object { Write-Output ("  " + $_.Name + "   " + $_.Length + " bytes") }

Write-Output ""
Write-Output "=== 有无 manifest / logo 资源（Store 包的图标源）==="
Get-ChildItem $new -Filter "AppxManifest.xml" -ErrorAction SilentlyContinue | ForEach-Object { Write-Output ("  " + $_.FullName) }
Get-ChildItem $new -Filter "*.png" -ErrorAction SilentlyContinue | Select-Object -First 8 | ForEach-Object { Write-Output ("  " + $_.Name) }