// Drive any CLI inside a REAL pseudo-terminal using WorkBuddy's bundled @lydell/node-pty.
// Purpose: verify the official CodeBuddy CLI TUI can boot (=> /login is reachable).
//
// Usage:
//   node cbc-pty.mjs <script.json>
// script.json:
//   { "cli": "C:/path/to/bin/codebuddy.js", "args": ["--foo"], "cwd": "E:\\output",
//     "env": {"K":"V"}, "steps": [ {"waitMs":4000,"send":"/login","enter":true} ], "totalMs": 45000 }
import { createRequire } from 'node:module'
import { readFileSync, existsSync } from 'node:fs'

const require = createRequire('F:/AI/WorkBuddy/resources/app.asar.unpacked/cli/package.json')
const pty = require('@lydell/node-pty')

const scriptPath = process.argv[2]
const cfg = scriptPath
  ? JSON.parse(readFileSync(scriptPath, 'utf8'))
  : { steps: [{ waitMs: 8000 }], totalMs: 15000 }

const DEFAULT_CLI = 'F:/AI/WorkBuddy/resources/app.asar.unpacked/cli/bin/codebuddy'
const cli = cfg.cli ?? DEFAULT_CLI
if (!existsSync(cli)) {
  console.error(`[FATAL] cli not found: ${cli}`)
  process.exit(2)
}

const p = pty.spawn(process.execPath, [cli, ...(cfg.args ?? [])], {
  name: 'xterm-256color',
  cols: 150,
  rows: 45,
  cwd: cfg.cwd ?? 'E:\\output',
  env: {
    ...process.env,
    TERM: 'xterm-256color',
    FORCE_COLOR: '0',
    NO_COLOR: '1',
    ...(cfg.env ?? {}),
  },
})

let buf = ''
p.onData((d) => {
  buf += d
  process.stdout.write(d)
})
p.onExit(({ exitCode, signal }) => {
  console.log(`\n\n[[PTY EXIT code=${exitCode} signal=${signal} capturedChars=${buf.length}]]`)
  process.exit(0)
})

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

for (const step of cfg.steps ?? []) {
  await sleep(step.waitMs ?? 2000)
  if (step.send !== undefined) {
    console.log(`\n[[SEND]] ${JSON.stringify(step.send)} enter=${step.enter !== false}`)
    p.write(step.send + (step.enter === false ? '' : '\r'))
  }
  if (step.note) console.log(`[[NOTE]] ${step.note}`)
}

await sleep(cfg.totalMs ?? 10000)
console.log('\n[[DONE waiting; killing pty]]')
try { p.kill() } catch {}
await sleep(800)
process.exit(0)
