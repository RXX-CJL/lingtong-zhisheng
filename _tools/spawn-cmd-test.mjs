import { spawn } from 'node:child_process'
const p = spawn('E:\\output\\_tools\\cua-driver-mcp.cmd', ['mcp'], { stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true })
p.on('error', e => console.log('  ★ spawn 报错: ' + e.code + ' / ' + e.message))
p.on('exit', c => console.log('  退出 code=' + c))
setTimeout(() => { console.log('  (3 秒后) 日志文件是否生成: ' + (require('node:fs').existsSync('E:\\output\\_cua-mcp-launch.log'))); try { p.kill() } catch {}; process.exit(0) }, 3000)
