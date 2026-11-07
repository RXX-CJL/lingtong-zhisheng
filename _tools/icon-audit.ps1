[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$s = New-Object -ComObject WScript.Shell

Write-Output "=== 桌面 lnk 目标一览（前12个）==="
Get-ChildItem "C:\Users\ROG\Desktop\*.lnk" | Select-Object -First 12 | ForEach-Object {
  $sc = $s.CreateShortcut($_.FullName)
  Write-Output ($_.BaseName + "`t| Target=" + $sc.TargetPath + "`t| Args=" + $sc.Arguments + "`t| Icon=" + $sc.IconLocation)
}

Write-Output ""
Write-Output "=== ChatGPT.lnk 详情 ==="
$p = "C:\Users\ROG\Desktop\ChatGPT.lnk"
if (Test-Path $p) {
  $sc = $s.CreateShortcut($p)
  Write-Output ("TargetPath  = [" + $sc.TargetPath + "]")
  Write-Output ("Arguments   = [" + $sc.Arguments + "]")
  Write-Output ("IconLocation= [" + $sc.IconLocation + "]")
  Write-Output ("WorkingDir  = [" + $sc.WorkingDirectory + "]")
  Write-Output ("Size        = " + (Get-Item $p).Length + " bytes")
}