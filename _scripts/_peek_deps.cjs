// 取候选项目的依赖声明，判断落地成本
const { execFileSync } = require('child_process');

const TARGETS = [
  ['szad670401/HyperLPR', '9307450f7b7915be18f23a539ec05b41fe6629f4', ['requirements.txt', 'README.md', 'setup.py']],
  ['sirius-ai/LPRNet_Pytorch', '7c976664b3f3879efabeaff59c7a117e49d5f29e', ['requirements.txt', 'README.md']],
  ['we0091234/Chinese_license_plate_detection_recognition', '670b765c09fff11850a7b1c542787ad66c24ae50', ['requirements.txt', 'README.md']],
];

const get = (url) => {
  try {
    return execFileSync('curl', ['-sL', '--max-time', '30', '--proxy', 'http://127.0.0.1:7897', url],
      { encoding: 'utf8', timeout: 40000 });
  } catch (e) { return ''; }
};

for (const [repo, sha, files] of TARGETS) {
  console.log('='.repeat(76));
  console.log(`  ${repo}  @${sha.slice(0, 10)}`);
  console.log('='.repeat(76));
  for (const f of files) {
    const url = `https://cdn.jsdelivr.net/gh/${repo}@${sha}/${f}`;
    const t = get(url);
    if (!t || t.includes('Couldn\'t find')) { console.log(`  --- ${f}: 取不到`); continue; }
    if (f === 'requirements.txt') {
      console.log(`  --- ${f} (${t.length} 字节):`);
      t.split('\n').filter(l => l.trim()).slice(0, 20).forEach(l => console.log('      ' + l.trim()));
    } else {
      const lines = t.split('\n');
      const key = lines.filter(l => /pip install|依赖|requirement|python |torch|opencv|车牌|license|识别率|准确率|accuracy/i.test(l)).slice(0, 10);
      console.log(`  --- ${f} 关键行:`);
      key.forEach(l => console.log('      ' + l.trim().slice(0, 120)));
    }
  }
  console.log();
}
