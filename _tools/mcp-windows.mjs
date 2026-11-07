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
  send({ jsonrpc:'2.0', id:2, method:'tools/call', params:{ name:'list_windows', arguments:{} } })
  setTimeout(() => {
    for (const line of buf.split('\n').filter(Boolean)) {
      try {
        const j = JSON.parse(line)
        if (j.id !== 2) continue
        const txt = (j.result?.content || []).map(x => x.text).filter(Boolean).join('\n')
        // 尝试解析成 JSON 拿前几个窗口
        try {
          const arr = JSON.parse(txt)
          console.log('窗口总数:', arr.length)
          arr.slice(0, 14).forEach(w => {
            console.log('  pid=' + String(w.pid ?? '?').padEnd(7) +
                        (w.app || w.process_name || '?').toString().padEnd(22) +
                        '| ' + (w.title || '').toString().slice(0, 52))
          })
        } catch {
          console.log(txt.slice(0, 1400))
        }
      } catch {}
    }
    try { p.kill() } catch {}
    process.exit(0)
  }, 5000)
}, 3000)
