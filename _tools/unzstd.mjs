import { createReadStream, createWriteStream } from 'node:fs'
import { createZstdDecompress } from 'node:zlib'
import { pipeline } from 'node:stream/promises'
const src = process.argv[2], dst = process.argv[3]
try {
  await pipeline(createReadStream(src), createZstdDecompress(), createWriteStream(dst))
  console.log('解压完成 -> ' + dst)
} catch (e) { console.log('解压出错: ' + e.message) }
