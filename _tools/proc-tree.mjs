import { execFileSync } from 'node:child_process'
const ps = 'Get-CimInstance Win32_Process | Where-Object { $_.Name -eq "node.exe" } | Select-Object ProcessId,ParentProcessId,CreationDate,CommandLine | ConvertTo-Json -Depth 3'
const out = execFileSync('powershell', ['-NoProfile', '-Command', ps], { encoding: 'utf8', maxBuffer: 8 * 1024 * 1024 })
let arr = JSON.parse(out)
if (!Array.isArray(arr)) arr = [arr]
for (const p of arr) {
  const cmd = String(p.CommandLine || '').replace(/\s+/g, ' ')
  const mark = cmd.includes('vite') ? '  <== VITE' : ''
  console.log('PID=' + p.ProcessId + '  PPID=' + p.ParentProcessId + '  ' + p.CreationDate + mark)
  console.log('    ' + cmd.slice(0, 140))
}
