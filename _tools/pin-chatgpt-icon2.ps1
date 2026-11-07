[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$store = "F:\AI\Desktop-Icons"
New-Item -ItemType Directory -Force -Path $store | Out-Null

$pkg = Get-AppxPackage -Name "OpenAI.Codex"
$src = Join-Path $pkg.InstallLocation "app\resources\icon-chatgpt.ico"
$dst = Join-Path $store "ChatGPT.ico"

# 用字节流读写，绕开 EFS 加密标记导致的 Copy-Item 失败
$bytes = [System.IO.File]::ReadAllBytes($src)
[System.IO.File]::WriteAllBytes($dst, $bytes)
Write-Output ("字节数 = " + $bytes.Length)
Write-Output ("目标存在 = " + (Test-Path $dst) + "  大小 = " + (Get-Item $dst).Length)

$lnk = "C:\Users\ROG\Desktop\ChatGPT.lnk"
$s = New-Object -ComObject WScript.Shell
$sc = $s.CreateShortcut($lnk)
$sc.IconLocation = $dst + ",0"
$sc.Save()

$s2 = New-Object -ComObject WScript.Shell
$sc2 = $s2.CreateShortcut($lnk)
Write-Output ""
Write-Output "=== 最终状态 ==="
Write-Output ("  IconLocation = " + $sc2.IconLocation)
$p = $sc2.IconLocation -replace ",0$",""
Write-Output ("  图标文件存在 = " + (Test-Path $p))
Write-Output ("  已脱离 WindowsApps = " + (-not ($p -match "WindowsApps")))
Write-Output ("  目标仍可启动 = " + ($sc2.TargetPath + " " + $sc2.Arguments))