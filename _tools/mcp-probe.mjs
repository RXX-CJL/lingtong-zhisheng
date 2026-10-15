import { spawn } from 'node:child_process'
const exe = 'C:\\Users\\ROG\\.local\\bin\\cua-driver\\cua-driver.exe'
const p = spawn(exe, ['mcp'], { stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true })
let out = '', err = ''
p.stdout.on('data', d => { out += d.toString() })
p.stderr.on('data', d => { err += d.toString() })
p.on('error', e => console.log('SPAWN_ERROR: ' + e.message))
const init = { jsonrpc: '2.0', id: 1, method: 'initialize', params: { protocolVersion: '2024-11-05', capabilities: {}, clientInfo: { name: 'dsh-probe', version: '1.0' } } }
try { p.stdin.write(JSON.stringify(init) + '\n') } catch (e) { console.log('WRITE_ERROR: ' + e.message) }
setTimeout(() => {
  console.log('=== MCP initialize 应答（前 1200 字） ===')
  console.log(out.slice(0, 1200) || '(无 stdout 输出)')
  if (err) { console.log('=== stderr（前 600 字） ==='); console.log(err.slice(0, 600)) }
  try { p.kill() } catch {}
  process.exit(0)
}, 4000)
