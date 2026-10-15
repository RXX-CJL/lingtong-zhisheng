import { spawn } from 'node:child_process'
const exe = 'C:\\Users\\ROG\\.local\\bin\\cua-driver\\cua-driver.exe'
const mk = tag => {
  const p = spawn(exe, ['mcp'], { stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true })
  let buf = '', err = ''
  p.stdout.on('data', d => { buf += d.toString() })
  p.stderr.on('data', d => { err += d.toString() })
  p.on('error', e => console.log('[' + tag + '] SPAWN_ERR ' + e.message))
  p.on('exit', c => console.log('[' + tag + '] ★ 进程退出 code=' + c))
  setTimeout(() => { try { p.stdin.write(JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'initialize', params: { protocolVersion: '2024-11-05', capabilities: {}, clientInfo: { name: tag, version: '1' } } }) + '\n') } catch (e) { console.log('[' + tag + '] 写失败 ' + e.message) } }, 400)
  setTimeout(() => {
    const ok = buf.includes('"result"')
    console.log('[' + tag + '] 握手 ' + (ok ? '★ 成功' : '✗ 失败') + '   stdout=' + buf.length + 'B')
    if (err.trim()) console.log('[' + tag + '] stderr: ' + err.trim().slice(0, 300))
  }, 4800)
  return p
}
console.log('=== 实例 A 启动 ===')
const a = mk('A')
setTimeout(() => { console.log('=== 实例 B 启动（模拟 DSH 的第二次启动） ==='); const b = mk('B') }, 900)
setTimeout(() => {
  console.log('=== 当前 cua-driver 进程数 ===')
  process.exit(0)
}, 6200)
