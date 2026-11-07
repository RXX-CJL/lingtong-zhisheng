import { spawn } from 'node:child_process';
import fs from 'node:fs';
const exe = 'C:\\Users\\ROG\\.local\\bin\\cua-driver\\cua-driver.exe';
const p = spawn(exe, ['mcp'], { stdio: ['pipe','pipe','pipe'], windowsHide: true });
let buf = '';
const send = (o) => p.stdin.write(JSON.stringify(o) + '\n');
p.stdout.on('data', d => { buf += d.toString() });
p.stderr.on('data', () => {});
send({ jsonrpc:'2.0', id:1, method:'initialize', params:{ protocolVersion:'2024-11-05', capabilities:{}, clientInfo:{ name:'dsh', version:'1.0' } } });
setTimeout(() => {
  buf = '';
  send({ jsonrpc:'2.0', id:2, method:'tools/list', params:{} });
  setTimeout(() => {
    for (const line of buf.split('\n').filter(Boolean)) {
      try { const j = JSON.parse(line); if (j.id !== 2) continue;
        const tools = (j.result?.tools || []).map(t => t.name);
        console.log('TOOLS(' + tools.length + '): ' + tools.join(', '));
      } catch {}
    }
    try { p.kill() } catch {};
    process.exit(0);
  }, 4000);
}, 2500);