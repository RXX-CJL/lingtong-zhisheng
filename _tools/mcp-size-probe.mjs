import { spawn } from 'node:child_process'
const exe = 'C:\\Users\\ROG\\.local\\bin\\cua-driver\\cua-driver.exe'
const p = spawn(exe, ['mcp'], { stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true })
let buf = ''
const logs = []
p.stdout.on('data', d => {
  buf += d.toString(); let i
  while ((i = buf.indexOf('\n')) >= 0) { const l = buf.slice(0, i).trim(); buf = buf.slice(i + 1); if (!l) continue; try { logs.push(JSON.parse(l)) } catch {} }
})
p.stderr.on('data', () => {})
setTimeout(() => { try { p.stdin.write(JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'initialize', params: { protocolVersion: '2024-11-05', capabilities: {}, clientInfo: { name: 'probe', version: '1' } } }) + '\n') } catch {} }, 400)
setTimeout(() => {
  const init = logs.find(m => m.id === 1)
  const inst = (init && init.result && init.result.instructions) || ''
  const bytes = Buffer.byteLength(inst, 'utf8')
  console.log('instructions 字符数        = ' + inst.length)
  console.log('instructions UTF-8 字节数  = ' + bytes)
  console.log('maxInstructionBytes 默认   = 32768')
  console.log('★ 是否超限                 = ' + (bytes > 32768 ? 'YES —— 超限！' : 'no'))
  console.log('超限倍数                   = ' + (bytes / 32768).toFixed(2) + 'x')
  console.log('')
  console.log('--- instructions 尾部 500 字 ---')
  console.log(inst.slice(-500))
  try { p.kill() } catch {}
  process.exit(0)
}, 4500)
