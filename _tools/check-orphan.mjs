import { execFileSync } from 'node:child_process'
const ps = 'Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name | ConvertTo-Json -Depth 3'
const all = JSON.parse(execFileSync('powershell', ['-NoProfile', '-Command', ps], { encoding: 'utf8', maxBuffer: 16 * 1024 * 1024 }))
const arr = Array.isArray(all) ? all : [all]
const byPid = new Map(arr.map(p => [p.ProcessId, p]))
for (const pid of [32932, 11620]) {
  const p = byPid.get(pid)
  if (!p) { console.log(pid + ' 已不存在'); continue }
  const parent = byPid.get(p.ParentProcessId)
  console.log('PID ' + pid + ' (' + p.Name + ')')
  console.log('   PPID ' + p.ParentProcessId + ' → ' + (parent ? '活着: ' + parent.Name : '【已死】孤儿进程'))
}
