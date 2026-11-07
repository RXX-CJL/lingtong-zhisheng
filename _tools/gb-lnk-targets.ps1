[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$s = New-Object -ComObject WScript.Shell
$names = @("CC Switch","ChatGPT","Cloudflare","draw.io","DroidCamApp","Plain Craft Launcher 2","Radmin.exe","无畏契约WeGame版","电源-平衡模式","电源-高性能模式")
foreach ($n in $names) {
  $p = "C:\Users\ROG\Desktop\$n.lnk"
  if (Test-Path $p) {
    $sc = $s.CreateShortcut($p)
    Write-Output ($n + "`t" + $sc.TargetPath + "`t" + $sc.Arguments)
  }
}