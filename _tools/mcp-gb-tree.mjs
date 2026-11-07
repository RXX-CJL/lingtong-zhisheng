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
    let gbId = null;
    for (const line of buf.split('\n').filter(Boolean)) {
      try { const j = JSON.parse(line); if (j.id !== 10) continue;
        const txt = (j.result?.content || []).map(x => x.text).filter(Boolean).join('\n');
        console.log(txt.slice(0, 2500));
        const m = txt.match(/GlassBoard[^\n]*window_id:\s*(\d+)/);
        if (m) gbId = m[1];
      } catch {}
    }
    console.log('\n>>> GlassBoard window_id = ' + gbId);
    if (!gbId) { try{p.kill()}catch{}; process.exit(0); }
    buf = '';
    call(20, 'get_accessibility_tree', { window_id: Number(gbId), max_depth: 3 });
    setTimeout(() => {
      for (const line of buf.split('\n').filter(Boolean)) {
        try { const j = JSON.parse(line); if (j.id !== 20) continue;
          const txt = (j.result?.content || []).map(x => x.text).filter(Boolean).join('\n');
          console.log('\n=== ACCESSIBILITY TREE ===');
          console.log(txt.slice(0, 6000));
        } catch {}
      }
      try { p.kill() } catch {};
      process.exit(0);
    }, 8000);
  }, 5000);
}, 2500);