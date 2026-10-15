// Scan a large binary/text file for patterns, streaming (zero deps).
// Usage: node find-in-asar.mjs <file> <pattern1> [pattern2 ...]
import { createReadStream } from 'node:fs'

const [, , file, ...patterns] = process.argv
if (!file || patterns.length === 0) {
  console.error('usage: node find-in-asar.mjs <file> <pattern...>')
  process.exit(2)
}
const bps = patterns.map((p) => ({ p, b: Buffer.from(p, 'utf8') }))
const MAXWIN = Number(process.env.MAXWIN ?? 3)
const CHUNK = 8 << 20
const OVERLAP = 4096
const hits = new Map(patterns.map((p) => [p, 0]))
const samples = new Map()

let carry = Buffer.alloc(0)
let offset = 0
const stream = createReadStream(file, { highWaterMark: CHUNK })

stream.on('data', (chunk) => {
  const buf = Buffer.concat([carry, chunk])
  const base = offset - carry.length
  for (const { p, b } of bps) {
    let idx = 0
    while ((idx = buf.indexOf(b, idx)) !== -1) {
      hits.set(p, hits.get(p) + 1)
      const arr = samples.get(p) ?? []
      if (arr.length < MAXWIN) {
        const s = Math.max(0, idx - 160)
        const e = Math.min(buf.length, idx + 240)
        arr.push({ at: base + idx, text: buf.subarray(s, e).toString('latin1').replace(/\0/g, '·') })
        samples.set(p, arr)
      }
      idx += b.length
    }
  }
  offset = base + buf.length
  carry = buf.subarray(Math.max(0, buf.length - OVERLAP))
})

stream.on('end', () => {
  console.log(`file: ${file}`)
  console.log(`size: ${offset} bytes\n`)
  for (const p of patterns) {
    const n = hits.get(p)
    console.log(`--- "${p}" -> ${n} hit(s)`)
    for (const s of samples.get(p) ?? []) {
      console.log(`    @${s.at}: ...${s.text}...\n`)
    }
  }
})
