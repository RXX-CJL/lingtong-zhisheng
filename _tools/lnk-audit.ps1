[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$s = New-Object -ComObject WScript.Shell
$ok = 0; $dead = 0
Get-ChildItem "C:\Users\ROG\Desktop\*.lnk" | ForEach-Object {
  $t = ""
  try { $t = $s.CreateShortcut($_.FullName).TargetPath } catch { $t = "<err>" }
  if ($t -and (Test-Path $t)) {
    Write-Output ("OK   " + $_.Name)
    $ok++
  } else {
    Write-Output ("DEAD " + $_.Name + "  ->  " + $t)
    $dead++
  }
}
Write-Output ""
Write-Output ("SUMMARY ok=" + $ok + " dead=" + $dead)