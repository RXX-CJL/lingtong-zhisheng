[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PATH = "E:" + [char]92 + ";" + $env:PATH
if (-not (Test-Path "E:" + [char]92 + "output" + [char]92 + "1" + [char]92 + "web-admin")) { Write-Output "MISSING"; exit 1 }
$wd = "E:" + [char]92 + "output" + [char]92 + "1" + [char]92 + "web-admin"
$exe = "E:" + [char]92 + "node.exe"
$argList = @("node_modules" + [char]92 + "vite" + [char]92 + "bin" + [char]92 + "vite.js", "--host", "127.0.0.1", "--port", "5173")
$p = Start-Process -FilePath $exe -ArgumentList $argList -WorkingDirectory $wd -PassThru -WindowStyle Hidden
Write-Output ("STARTED PID=" + $p.Id)
