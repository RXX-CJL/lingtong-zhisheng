[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Output "=== lnk 里写的那个 ico 还在吗 ==="
$p = "C:\Program Files\WindowsApps\OpenAI.Codex_26.1023.6621.0_x64__2p2nqsd0c76g0\app\resources\icon-chatgpt.ico"
Write-Output ("Exists = " + (Test-Path $p))

Write-Output ""
Write-Output "=== WindowsApps 里实际有哪些 OpenAI.Codex 版本 ==="
Get-ChildItem "C:\Program Files\WindowsApps" -Directory -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -like "OpenAI.Codex*" } |
  ForEach-Object { Write-Output ("  " + $_.Name) }

Write-Output ""
Write-Output "=== 已安装的 ChatGPT/Codex 包（按用户）==="
Get-AppxPackage -Name "*OpenAI*" | ForEach-Object {
  Write-Output ("  Name        = " + $_.Name)
  Write-Output ("  Version     = " + $_.Version)
  Write-Output ("  InstallLoc  = " + $_.InstallLocation)
  Write-Output ("  PackageFamilyName = " + $_.PackageFamilyName)
}