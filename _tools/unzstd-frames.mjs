import { readFileSync, writeFileSync } from 'node:fs'
import { zstdDecompressSync } from 'node:zlib'
const [,, src, dst] = process.argv
const raw = readFileSync(src)
const positions = []
for (let i = 0; i < raw.length - 4; i++) {
  if (raw[i] === 0x28 && raw[i + 1] === 0xB5 && raw[i + 2] === 0x2F && raw[i + 3] === 0xFD) positions.push(i)
}
let out = '', ok = 0, fail = 0
for (let k = 0; k < positions.length; k++) {
  const start = positions[k]
  const end = k + 1 < positions.length ? positions[k + 1] : raw.length
  try {
    out += zstdDecompressSync(raw.subarray(start, end)).toString('utf8')
    ok++
  } catch { fail++ }
}
writeFileSync(dst, out, 'utf8')
console.log('帧总数 = ' + positions.length + '   成功 = ' + ok + '   失败(可能是误判magic) = ' + fail)
console.log('解出明文 = ' + out.length + ' 字节')
