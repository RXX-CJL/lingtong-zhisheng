import { spawn } from 'node:child_process'
const exe = 'C:\\Users\\ROG\\.local\\bin\\cua-driver\\cua-driver.exe'
const p = spawn(exe, ['mcp'], { stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true })
let buf = ''
const logs = []
const send = o => { try { p.stdin.write(JSON.stringify(o) + '\n') } catch {} }
const pump = d => {
  buf += d.toString()
  let i
  while ((i = buf.indexOf('\n')) >= 0) {
    const line = buf.slice(0, i).trim(); buf = buf.slice(i + 1)
    if (!line) continue
    try { logs.push(JSON.parse(line)) } catch {}
  }
}
p.stdout.on('data', pump)
p.stderr.on('data', () => {})
p.on('error', e => console.log('SPAWN_ERR ' + e.message))
setTimeout(() => send({ jsonrpc: '2.0', id: 1, method: 'initialize', params: { protocolVersion: '2024-11-05', capabilities: {}, clientInfo: { name: 'dsh-probe', version: '1' } } }), 400)
setTimeout(() => { send({ jsonrpc: '2.0', method: 'notifications/initialized' }); send({ jsonrpc: '2.0', id: 2, method: 'tools/list', params: {} }) }, 1600)
setTimeout(() => {
  const t = logs.find(m => m.id === 2)
  if (t && t.result && t.result.tools) {
    console.log('工具数 = ' + t.result.tools.length)
    console.log('工具名: ' + t.result.tools.map(x => x.name).join(', '))
  } else { console.log('tools/list 无返回') }
  send({ jsonrpc: '2.0', id: 3, method: 'tools/call', params: { name: 'check_permissions', arguments: { prompt: false } } })
}, 3200)
setTimeout(() => {
  const perm = logs.find(m => m.id === 3)
  console.log('=== check_permissions(prompt:false) 结果 ===')
  console.log(perm ? JSON.stringify(perm).slice(0, 2000) : '(无返回)')
  try { p.kill() } catch {}
  process.exit(0)
}, 8000)
