import { spawn } from 'node:child_process';
const exe = 'C:\\Users\\ROG\\.local\\bin\\cua-driver\\cua-driver.exe';
const p = spawn(exe, ['mcp'], { stdio: ['pipe','pipe','pipe'], windowsHide: true });
let buf = '';
const send = (o) => p.stdin.write(JSON.stringify(o) + '\n');
p.stdout.on('data', d => { buf += d.toString() });
p.stderr.on('data', () => {});
send({ jsonrpc:'2.0', id:1, method:'initialize', params:{ protocolVersion:'2024-11-05', capabilities:{}, clientInfo:{ name:'dsh', version:'1.0' } } });
setTimeout(() => {
  buf = '';
  send({ jsonrpc:'2.0', id:2, method:'tools/call', params:{ name:'get_screen_size', arguments:{} } });
  send({ jsonrpc:'2.0', id:3, method:'tools/call', params:{ name:'list_windows', arguments:{} } });
  setTimeout(() => {
    for (const line of buf.split('\n').filter(Boolean)) {
      try { const j = JSON.parse(line);
        const txt = (j.result?.content || []).map(x => x.text).filter(Boolean).join('\n');
        if (j.id === 2) console.log('[screen] ' + txt.slice(0, 300));
        if (j.id === 3) {
          let arr; try { arr = JSON.parse(txt) } catch { arr = null }
          if (Array.isArray(arr)) {
            console.log('[windows] ' + arr.length + ' total');
            arr.forEach(w => console.log('   ' + String(w.app||w.process_name||'?').padEnd(26) + '| ' + String(w.title||'').slice(0,50)));
          } else console.log('[windows raw] ' + txt.slice(0, 900));
        }
      } catch {}
    }
    try { p.kill() } catch {};
    process.exit(0);
  }, 5000);
}, 2500);