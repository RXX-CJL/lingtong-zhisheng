[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$lnk = "C:\Users\ROG\Desktop\ChatGPT.lnk"
Copy-Item $lnk "$lnk.bak-shu" -Force
Write-Output "备份: ChatGPT.lnk.bak-shu"

# 从已安装包里动态取当前 InstallLocation，不写死版本号
$pkg = Get-AppxPackage -Name "OpenAI.Codex"
$ico = Join-Path $pkg.InstallLocation "app\resources\icon-chatgpt.ico"
Write-Output ("新图标 = " + $ico)
Write-Output ("存在 = " + (Test-Path $ico))

if (Test-Path $ico) {
  $s = New-Object -ComObject WScript.Shell
  $sc = $s.CreateShortcut($lnk)
  $old = $sc.IconLocation
  $sc.IconLocation = $ico + ",0"
  $sc.Save()
  Write-Output ""
  Write-Output "=== 写入结果 ==="
  Write-Output ("旧 = " + $old)
  $s2 = New-Object -ComObject WScript.Shell
  $sc2 = $s2.CreateShortcut($lnk)
  Write-Output ("新 = " + $sc2.IconLocation)
  Write-Output ("新路径存在 = " + (Test-Path ($sc2.IconLocation -replace ",0$","")))
} else { Write-Output "新路径也不存在，未改动" }