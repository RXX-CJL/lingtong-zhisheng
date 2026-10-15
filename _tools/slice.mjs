// Dump source slices around byte offsets in a large bundle.
// Usage: node slice.mjs <file> <offset1> [offset2 ...] [--before=1200] [--after=3000]
import { open } from 'node:fs/promises'

const args = process.argv.slice(2)
const file = args.shift()
const offsets = []
let before = 1200
let after = 3000
for (const a of args) {
  const m = /^--(before|after)=(\d+)$/.exec(a)
  if (m) { if (m[1] === 'before') before = +m[2]; else after = +m[2]; continue }
  offsets.push(+a)
}
if (!file || offsets.length === 0) {
  console.error('usage: node slice.mjs <file> <offset...> [--before=N] [--after=N]')
  process.exit(2)
}
const fh = await open(file, 'r')
for (const off of offsets) {
  const start = Math.max(0, off - before)
  const len = before + after
  const buf = Buffer.alloc(len)
  const { bytesRead } = await fh.read(buf, 0, len, start)
  console.log(`\n${'='.repeat(30)} offset ${off} (window ${start}..${start + bytesRead}) ${'='.repeat(30)}`)
  console.log(buf.subarray(0, bytesRead).toString('utf8'))
}
await fh.close()
