import { spawn } from 'node:child_process'
const exe = 'C:\\Users\\ROG\\.local\\bin\\cua-driver\\cua-driver.exe'
const p = spawn(exe, ['mcp'], { stdio: ['pipe','pipe','pipe'], windowsHide: true })
let buf = ''
const send = (o) => p.stdin.write(JSON.stringify(o) + '\n')
p.stdout.on('data', d => { buf += d.toString() })
p.stderr.on('data', () => {})
p.on('error', e => console.log('SPAWN_ERROR: ' + e.message))

send({ jsonrpc:'2.0', id:1, method:'initialize', params:{ protocolVersion:'2024-11-05', capabilities:{}, clientInfo:{ name:'dsh', version:'1.0' } } })

setTimeout(() => {
  buf = ''
  send({ jsonrpc:'2.0', id:2, method:'tools/list', params:{} })
  setTimeout(() => {
    // 提取 name + description 摘要
    const lines = buf.split('\n').filter(Boolean)
    for (const line of lines) {
      try {
        const j = JSON.parse(line)
        if (j.id === 2 && j.result && j.result.tools) {
          console.log('工具总数:', j.result.tools.length)
          for (const t of j.result.tools) {
            const desc = (t.description || '').split('\n')[0].slice(0, 95)
            console.log('  ' + t.name.padEnd(26) + ' | ' + desc)
          }
        }
      } catch {}
    }
    try { p.kill() } catch {}
    process.exit(0)
  }, 3500)
}, 3000)
