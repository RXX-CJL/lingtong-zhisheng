[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# 固定图标仓库（F 盘，符合软件不放 C 盘的规矩）
$store = "F:\AI\Desktop-Icons"
New-Item -ItemType Directory -Force -Path $store | Out-Null

$pkg = Get-AppxPackage -Name "OpenAI.Codex"
$src = Join-Path $pkg.InstallLocation "app\resources\icon-chatgpt.ico"
$dst = Join-Path $store "ChatGPT.ico"
Copy-Item $src $dst -Force
Write-Output ("已固化图标 -> " + $dst)
Write-Output ("存在 = " + (Test-Path $dst) + "  大小 = " + (Get-Item $dst).Length + " bytes")

# 指向固定位置
$lnk = "C:\Users\ROG\Desktop\ChatGPT.lnk"
$s = New-Object -ComObject WScript.Shell
$sc = $s.CreateShortcut($lnk)
$sc.IconLocation = $dst + ",0"
$sc.Save()

$s2 = New-Object -ComObject WScript.Shell
$sc2 = $s2.CreateShortcut($lnk)
Write-Output ""
Write-Output "=== 最终 IconLocation ==="
Write-Output ("  " + $sc2.IconLocation)
Write-Output ("  路径存在 = " + (Test-Path ($sc2.IconLocation -replace ",0$","")))
Write-Output ("  已脱离版本号 = " + (-not ($sc2.IconLocation -match "WindowsApps")))