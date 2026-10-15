// 核实 hyperlpr3 在 PyPI 上的真实情况（版本/依赖/兼容性）
const { execFileSync } = require('child_process');

const get = (url) => {
  try {
    return execFileSync('curl', ['-sL', '--max-time', '40', '--proxy', 'http://127.0.0.1:7897', url],
      { encoding: 'utf8', timeout: 50000 });
  } catch (e) { return ''; }
};

const meta = get('https://pypi.org/pypi/hyperlpr3/json');
if (!meta) { console.log('PyPI 取不到'); process.exit(0); }
let j;
try { j = JSON.parse(meta); } catch (e) { console.log('解析失败'); process.exit(0); }

const info = j.info || {};
console.log('='.repeat(74));
console.log('  hyperlpr3 (PyPI)');
console.log('='.repeat(74));
console.log('  latest       :', info.version);
console.log('  summary      :', (info.summary || '').slice(0, 100));
console.log('  requires_python:', info.requires_python);
console.log('  license      :', (info.license || '').slice(0, 60));
console.log('  home_page    :', info.home_page || info.project_urls && JSON.stringify(info.project_urls).slice(0, 120));
console.log('  requires_dist (依赖):');
(info.requires_dist || []).forEach(d => console.log('      ' + d));
console.log('  可用版本数   :', Object.keys(j.releases || {}).length);
const vers = Object.keys(j.releases || {});
console.log('  最近 6 个版本:', vers.slice(-6).join(', '));
const up = j.releases && j.releases[info.version];
if (up && up[0]) {
  console.log('  最新版上传时间:', up[0].upload_time);
  const wheels = up.filter(f => f.filename.endsWith('.whl')).map(f => f.filename);
  console.log('  wheel 文件   :');
  wheels.slice(0, 8).forEach(w => console.log('      ' + w));
  const win = wheels.filter(w => /win|any/.test(w));
  console.log('  Windows 可用 :', win.length > 0 ? 'YES -> ' + win[0] : 'NO');
}
