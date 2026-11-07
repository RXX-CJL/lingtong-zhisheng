[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Continue'
$targets = @(32932, 11620)
foreach ($t in $targets) {
  $proc = Get-Process -Id $t -ErrorAction SilentlyContinue
  if ($null -eq $proc) {
    Write-Output ("PID " + $t + " -> already gone")
    continue
  }
  try {
    $proc.Kill()
    $proc.WaitForExit(3000) | Out-Null
    Write-Output ("PID " + $t + " -> KILLED")
  } catch {
    Write-Output ("PID " + $t + " -> FAILED: " + $_.Exception.GetType().Name + " " + $_.Exception.Message)
  }
}
Start-Sleep -Milliseconds 1200
foreach ($t in $targets) {
  if (Get-Process -Id $t -ErrorAction SilentlyContinue) {
    Write-Output ("PID " + $t + " -> STILL ALIVE")
  } else {
    Write-Output ("PID " + $t + " -> CONFIRMED GONE")
  }
}
