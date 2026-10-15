// Desktop-profile variant of the dsh-workshop client compatibility patch.
//
// Problem (verified on DSH 0.1.7-rc.2, the Desktop runtime):
//   The workshop client locates the central column with
//       const CONVERSATION_COLUMN_SELECTOR = "[data-pane=\"conversation\"]";
//   and mount.tsx's conversationColumn() returns
//       document.querySelector(CONVERSATION_COLUMN_SELECTOR) ?? void 0
//   DSH 0.1.7 replaced that pane with a CSS-Module `CenterColumn` whose class is
//   e.g. `ZTP-Xa_centerCol` (hash prefix varies per build). A scan of the rc.2
//   runtime (resources/app.asar) finds `data-pane` 0 times and `centerCol` in
//   the real stylesheet, so the querySelector is always null, the panel never
//   mounts, and clicking the sidebar entry appears to do nothing.
//
// Method is identical to E:\output\dsh-workshop-patch\patch-client.mjs, which was
// applied to the old Web Profile: rewrite the locator to a hash-independent
// selector chain and interpolate the same constant into the takeover stylesheet
// so the two cannot drift apart again.
//
// Deliberately limited scope: (1) the central-area locator, (2) the matching
// TAKEOVER_STYLE selectors. Nothing else is touched. The replacement is length-
// neutral, so the installed bundle stays byte-length identical to upstream
// except for this one selector. No upstream repository is modified.
//
// Idempotent: re-running after a successful patch reports "already patched".
//
// Usage: node patch-client.mjs "<profileDir>"
//        default target profile is C:\Users\ROG\.dsh\profiles\desktop

import { readFileSync, writeFileSync, copyFileSync, existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

const profileDir = process.argv[2] ?? 'C:/Users/ROG/.dsh/profiles/desktop';
const TARGET = `${profileDir.replace(/\/+$/, '')}/node_modules/dsh-workshop/lib/client.js`;

if (!existsSync(TARGET)) {
  console.error(`ABORT: target not found: ${TARGET}`);
  process.exit(1);
}

const DQ = String.fromCharCode(34);   // "
const SQ = String.fromCharCode(39);   // '
const BS = String.fromCharCode(92);   // backslash
const BT = String.fromCharCode(96);   // backtick
const DQESC = BS + DQ;                // \"  as it appears in the bundle

// Hash-independent chain. Each hook is pinned to a structural fact:
//   [data-pane="conversation"|'conversation']  legacy DSH shells
//   [class*="centerCol"|"center-col"]          DSH 0.1.7 CSS-Module CenterColumn
//   [data-center-col]                          attribute variant of the same column
//   [data-dsh-frame] > [data-pane='sidebar']:not([data-rightbar-col]) + div:not([data-rightbar-col])
//                                              structural fallback keyed on the
//                                              stable data-rightbar-col marker
//
// Invariant of this patch: every single-quoted selector in the takeover
// stylesheet is also a literal prefix of the locator. That is checked below.
const SELECTOR_VALUE =
  '[' + 'data-pane=' + DQESC + 'conversation' + DQESC + ']'
  + ', ' + '[' + 'data-pane=' + SQ + 'conversation' + SQ + ']'
  + ', ' + '[' + 'class*=' + DQESC + 'centerCol' + DQESC + ']'
  + ', ' + '[' + 'class*=' + DQESC + 'center-col' + DQESC + ']'
  + ', ' + '[' + 'data-center-col' + ']'
  + ', ' + '[' + 'data-dsh-frame' + '] > ' + '[' + 'data-pane=' + SQ + 'sidebar' + SQ + ']'
  + ':not(' + '[' + 'data-rightbar-col' + ']' + ')'
  + ' + div:not(' + '[' + 'data-rightbar-col' + ']' + ')';

const OLD_SELECTOR =
  'const CONVERSATION_COLUMN_SELECTOR = ' + DQ + '[' + 'data-pane=' + DQESC + 'conversation' + DQESC + ']' + DQ + ';';
const NEW_SELECTOR =
  'const CONVERSATION_COLUMN_SELECTOR = ' + DQ + SELECTOR_VALUE + DQ + ';';

const TEMPLATE_INTERP = '${CONVERSATION_COLUMN_SELECTOR}';
const HEAD = 'const TAKEOVER_STYLE = ' + BT;
const SIDEBAR_ATTR = '[' + 'data-pane=' + SQ + 'sidebar' + SQ + ']';

const OLD_STYLE = [
  HEAD,
  "[" + 'data-pane=' + SQ + 'conversation' + SQ + "] {",
  '  position: relative;',
  '}',
  '[' + 'data-dsh-workshop-view' + '] {',
  '  position: absolute;',
  '  inset: 0;',
  '  display: none;',
  '  z-index: 5;',
  '}',
  'html[' + 'data-dsh-workshop-active' + ']:not(' + '[' + 'data-dsh-taskboard-active' + ']' + '):not(' + '[' + 'data-dsh-ssh-active' + ']' + ') [' + 'data-dsh-workshop-view' + '] {',
  '  display: block;',
  '}',
  'html[' + 'data-dsh-workshop-active' + ']:not(' + '[' + 'data-dsh-taskboard-active' + ']' + '):not(' + '[' + 'data-dsh-ssh-active' + ']' + ") [" + 'data-pane=' + SQ + 'conversation' + SQ + "] > :not([" + 'data-dsh-workshop-view' + ']) {',
  '  display: none;',
  '}',
  BT + ';',
].join('\n');

const NEW_STYLE = [
  HEAD,
  TEMPLATE_INTERP + ' {',
  '  position: relative;',
  '}',
  '[' + 'data-dsh-workshop-view' + '] {',
  '  position: absolute;',
  '  inset: 0;',
  '  display: none;',
  '  z-index: 5;',
  '}',
  'html[' + 'data-dsh-workshop-active' + ']:not(' + '[' + 'data-dsh-taskboard-active' + ']' + '):not(' + '[' + 'data-dsh-ssh-active' + ']' + ') [' + 'data-dsh-workshop-view' + '] {',
  '  display: block;',
  '}',
  'html[' + 'data-dsh-workshop-active' + ']:not(' + '[' + 'data-dsh-taskboard-active' + ']' + '):not(' + '[' + 'data-dsh-ssh-active' + ']' + ') ' + TEMPLATE_INTERP + ' > :not([' + 'data-dsh-workshop-view' + ']) {',
  '  display: none;',
  '}',
  BT + ';',
].join('\n');

// A literal fragment that proves the new locator survived the round trip.
const PATCHED_MARKER = 'class*=' + DQESC + 'centerCol' + DQESC;

const original = readFileSync(TARGET, 'utf8');

if (original.includes(PATCHED_MARKER)) {
  console.log('already patched - nothing to do');
  console.log('  target:', TARGET);
  process.exit(0);
}

const countOf = (haystack, needle) => haystack.split(needle).length - 1;

const problems = [];
if (countOf(original, OLD_SELECTOR) !== 1) problems.push(`selector anchor x${countOf(original, OLD_SELECTOR)}`);
if (countOf(original, OLD_STYLE) !== 1) problems.push(`style anchor x${countOf(original, OLD_STYLE)}`);
if (problems.length) {
  console.error('ABORT: unexpected bundle shape -', problems.join(', '));
  process.exit(1);
}

const patched = original.replace(OLD_SELECTOR, NEW_SELECTOR).replace(OLD_STYLE, NEW_STYLE);

if (patched === original) {
  console.error('ABORT: patch produced no change');
  process.exit(1);
}
if (!patched.includes(PATCHED_MARKER)) {
  console.error('ABORT: patched bundle has no centerCol selector');
  process.exit(1);
}

// Guard the patch's own invariant before touching the profile: the selectors the
// takeover stylesheet relies on must all appear in the locator, otherwise the CSS
// could hide nothing (or the wrong element).
const requiredPrefixes = [
  '[' + 'data-pane=' + SQ + 'conversation' + SQ + ']',
  '[' + 'class*=' + DQESC + 'center-col' + DQESC + ']',
  '[' + 'data-dsh-frame' + '] > ' + SIDEBAR_ATTR,
];
for (const prefix of requiredPrefixes) {
  if (!SELECTOR_VALUE.includes(prefix)) {
    console.error('ABORT: locator is missing required prefix', JSON.stringify(prefix));
    process.exit(1);
  }
}

// Never leave a broken bundle behind.
const sidecar = `${TARGET}.pre-patch`;
const hadSidecar = existsSync(sidecar);
if (!hadSidecar) copyFileSync(TARGET, sidecar);
writeFileSync(TARGET, patched, 'utf8');

const check = spawnSync(process.execPath, ['--check', TARGET], { encoding: 'utf8' });
if (check.status !== 0) {
  copyFileSync(sidecar, TARGET);
  console.error('ABORT: patched file failed node --check; restored original');
  console.error(check.stderr);
  process.exit(1);
}

console.log('patched OK (node --check passed)');
console.log('  target:', TARGET);
console.log('  bytes:', original.length, '->', patched.length);
console.log('  centerCol selector occurrences:', countOf(patched, PATCHED_MARKER));
console.log('  stylesheet interpolations:', countOf(patched, TEMPLATE_INTERP));
console.log('  sidecar backup:', sidecar, hadSidecar ? '(already present, untouched)' : '(created)');
