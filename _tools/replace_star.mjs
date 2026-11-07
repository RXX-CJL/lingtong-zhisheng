
import fs from 'node:fs';
const P = 'F:/AI/DSH-HQ/prototypes/memory-galaxy-3d.html';
const lines = fs.readFileSync(P, 'utf8').split('\n');
// 定位：从「── 星球本体：带光照的球体」到它对应的闭合 }
let start = -1, end = -1;
for (let i = 0; i < lines.length; i++) {
  if (lines[i].includes('── 星球本体：带光照的球体')) { start = i; break; }
}
if (start < 0) { console.log('找不到起点'); process.exit(1); }
// 从 start 往后找「边缘轮廓」之后的独占一行 '    }'
for (let i = start; i < start + 140; i++) {
  if (lines[i].includes('ctx.lineWidth = 0.7; ctx.stroke();') ) {
    // 下一行应该是 '      }' 然后是 '    }'
    for (let j = i; j < i + 5; j++) {
      if (lines[j].trim() === '}' && lines[j].startsWith('    }')) { end = j; break; }
    }
    break;
  }
}
if (end < 0) { console.log('找不到终点'); process.exit(1); }
console.log('替换行范围: ' + (start + 1) + ' .. ' + (end + 1) + '  (共 ' + (end - start + 1) + ' 行)');
const repl = fs.readFileSync('E:/output/_tools/star_body.txt', 'utf8').split('\n');
const out = [...lines.slice(0, start), ...repl, ...lines.slice(end + 1)];
fs.writeFileSync(P, out.join('\n'));
console.log('新文件行数: ' + out.length);
