import { execFileSync } from 'node:child_process'
const ps = 'Get-CimInstance Win32_Process | Where-Object { $_.Name -eq "node.exe" } | Select-Object ProcessId,ParentProcessId,CreationDate,CommandLine | ConvertTo-Json -Depth 3'
const raw = execFileSync('powershell', ['-NoProfile','-Command',ps], { encoding:'utf8', maxBuffer: 8*1024*1024 })
let arr = JSON.parse(raw); if (!Array.isArray(arr)) arr = [arr]
const rows = arr.map(p => {
  const m = String(p.CreationDate).match(/(\d{10})/g)
  const ts = m ? Number(m[0]) : 0
  return { pid: p.ProcessId, ppid: p.ParentProcessId, ts, cmd: String(p.CommandLine||'').replace(/\s+/g,' ') }
}).sort((a,b)=>b.ts-a.ts)
for (const r of rows) {
  const t = r.ts ? new Date(r.ts*1000).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai'}) : '?'
  console.log(r.pid + '  ' + t + '  ' + (r.cmd.slice(0,70) || '(无命令行)'))
}
