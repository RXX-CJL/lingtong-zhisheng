// 临时探针：监听 127.0.0.1:65532，观察 codex 到底往这个端口发什么
// 用途：判定 65532 是「代理端口」还是「codex 自己的本地服务端口」
import net from 'node:net';

const PORT = 65532;
const srv = net.createServer((sock) => {
  const peer = `${sock.remoteAddress}:${sock.remotePort}`;
  console.log(`[连接] ${new Date().toISOString()} 来自 ${peer}`);
  let first = true;
  sock.on('data', (d) => {
    if (first) {
      first = false;
      console.log(`[数据] ${d.length} 字节: ${JSON.stringify(d.toString('latin1').slice(0, 240))}`);
    }
  });
  sock.on('error', () => {});
});

srv.on('error', (e) => {
  console.log(`[监听失败] ${e.message}`);
  process.exit(1);
});

srv.listen(PORT, '127.0.0.1', () => console.log(`[监听中] 127.0.0.1:${PORT}`));
setTimeout(() => {
  console.log('[结束] 超时退出');
  process.exit(0);
}, 40000);
