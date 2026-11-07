const fs = require('fs');
const p = 'E:/output/1/api/output/event_videos/20261101/evt_10550_6_3934e4.mp4.replay.json';
if (!fs.existsSync(p)) { console.log('replay 不存在'); }
else {
  const j = JSON.parse(fs.readFileSync(p, 'utf8'));
  console.log('keys =', Object.keys(j).join(','));
  console.log('source =', j.source, '| frames =', j.frame_count);
  const f = j.frames || [];
  console.log('frames[0] keys =', f[0] ? Object.keys(f[0]).join(',') : '(空)');
  const s = JSON.stringify(f);
  const cnt = {};
  for (const c of ['red', 'green', 'yellow']) {
    const re = new RegExp('"' + c + '"', 'g');
    const m = s.match(re);
    if (m) cnt[c] = m.length;
  }
  console.log('frames 里颜色计数 =', JSON.stringify(cnt));
}

const dir = 'E:/output/1/api/output/scene_configs';
if (fs.existsSync(dir)) {
  const files = fs.readdirSync(dir);
  console.log('scene_configs 文件数 =', files.length, files.slice(0, 5));
  for (const fn of files.slice(0, 2)) {
    try {
      const j = JSON.parse(fs.readFileSync(dir + '/' + fn, 'utf8'));
      console.log('--- ' + fn + ' ---');
      console.log(JSON.stringify(j).slice(0, 500));
    } catch (e) { console.log(fn, '读失败'); }
  }
} else { console.log('scene_configs 目录不存在'); }
