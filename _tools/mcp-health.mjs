import { spawn } from 'node:child_process'
const exe = 'C:\\Users\\ROG\\.local\\bin\\cua-driver\\cua-driver.exe'
const p = spawn(exe, ['mcp'], { stdio: ['pipe','pipe','pipe'], windowsHide: true })
let buf = ''
const send = (o) => p.stdin.write(JSON.stringify(o) + '\n')
p.stdout.on('data', d => { buf += d.toString() })
p.stderr.on('data', () => {})

send({ jsonrpc:'2.0', id:1, method:'initialize', params:{ protocolVersion:'2024-11-05', capabilities:{}, clientInfo:{ name:'dsh', version:'1.0' } } })

setTimeout(() => {
  buf = ''
  send({ jsonrpc:'2.0', id:2, method:'tools/call', params:{ name:'health_report', arguments:{} } })
  setTimeout(() => {
    for (const line of buf.split('\n').filter(Boolean)) {
      try {
        const j = JSON.parse(line)
        if (j.id === 2) {
          const c = j.result?.content || []
          const txt = c.map(x => x.text).filter(Boolean).join('\n')
          console.log('=== health_report ===')
          console.log(txt.slice(0, 1200) || JSON.stringify(j).slice(0, 800))
        }
      } catch {}
    }
    try { p.kill() } catch {}
    process.exit(0)
  }, 5000)
}, 3000)
