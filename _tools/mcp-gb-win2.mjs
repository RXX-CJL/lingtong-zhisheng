import { spawn } from 'node:child_process';
const exe = 'C:\\Users\\ROG\\.local\\bin\\cua-driver\\cua-driver.exe';
const p = spawn(exe, ['mcp'], { stdio: ['pipe','pipe','pipe'], windowsHide: true });
let buf = '';
const send = (o) => p.stdin.write(JSON.stringify(o) + '\n');
const call = (id, name, args) => send({ jsonrpc:'2.0', id, method:'tools/call', params:{ name, arguments: args } });
p.stdout.on('data', d => { buf += d.toString() });
p.stderr.on('data', () => {});
send({ jsonrpc:'2.0', id:1, method:'initialize', params:{ protocolVersion:'2024-11-05', capabilities:{}, clientInfo:{ name:'dsh', version:'1.0' } } });
setTimeout(() => {
  buf = '';
  call(10, 'list_windows', {});
  setTimeout(() => {
    for (const line of buf.split('\n').filter(Boolean)) {
      try { const j = JSON.parse(line); if (j.id !== 10) continue;
        const txt = (j.result?.content || []).map(x => x.text).filter(Boolean).join('\n');
        for (const l of txt.split('\n')) { if (l.includes('pid 25172') || l.includes('GlassBoard')) console.log(l.trim()); }
      } catch {}
    }
    try { p.kill() } catch {};
    process.exit(0);
  }, 5000);
}, 2500);