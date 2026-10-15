// Minimal compatibility patch for the installed dsh-workshop client bundle.
//
// Problem: DSH 0.1.7-alpha.2 replaced the old `[data-pane="conversation"]`
// central area with a CSS-Module `CenterColumn` (class contains "centerCol",
// hash prefix varies per build), so conversationColumn() returned undefined and
// the workshop panel never mounted.
//
// Scope (deliberately limited):
//   1. the central-area locator used by conversationColumn()
//   2. the matching TAKEOVER_STYLE selectors
// Nothing else is touched.
//
// Idempotent: re-running after a successful patch reports "already patched".

import { readFileSync, writeFileSync, copyFileSync, existsSync } from 'node:fs';

const TARGET = 'C:/Users/ROG/.dsh/profiles/web/node_modules/dsh-workshop/lib/client.js';

// Five independent hooks, each pinned to a structural fact rather than to
// "the next div", so no hook can over-match:
//   [data-pane="conversation"|'conversation']  legacy DSH shells
//   [class*="centerCol"|"center-col"]          DSH 0.1.7 CSS-Module CenterColumn
//   [data-center-col]                          attribute variant of the same column
//   [data-dsh-frame] > [data-pane='sidebar']:not([data-rightbar-col]) + div:not([data-rightbar-col])
//                                              structural fallback: the sidebar's
//                                              next sibling that is not the right
//                                              column, keyed on the stable
//                                              data-rightbar-col marker
const SELECTOR_VALUE =
  "[data-pane=\\\"conversation\\\"], [data-pane='conversation'], [class*=\\\"centerCol\\\"], [class*=\\\"center-col\\\"], [data-center-col], [data-dsh-frame] > [data-pane='sidebar']:not([data-rightbar-col]) + div:not([data-rightbar-col])";

const ESCAPED_DQUOTE = '\\"';
const OLD_SELECTOR = `const CONVERSATION_COLUMN_SELECTOR = "[data-pane=${ESCAPED_DQUOTE}conversation${ESCAPED_DQUOTE}]";`;
const NEW_SELECTOR = `const CONVERSATION_COLUMN_SELECTOR = "${SELECTOR_VALUE}";`;

// The stylesheet template literal is rewritten to interpolate the same selector
// constant, so the two cannot drift apart again. `TEMPLATE_INTERP` is the
// literal two-character sequence the generated bundle must contain.
const TEMPLATE_INTERP = '${CONVERSATION_COLUMN_SELECTOR}';
const OLD_STYLE = [
  'const TAKEOVER_STYLE = `',
  "[data-pane='conversation'] {",
  '  position: relative;',
  '}',
  '[data-dsh-workshop-view] {',
  '  position: absolute;',
  '  inset: 0;',
  '  display: none;',
  '  z-index: 5;',
  '}',
  'html[data-dsh-workshop-active]:not([data-dsh-taskboard-active]):not([data-dsh-ssh-active]) [data-dsh-workshop-view] {',
  '  display: block;',
  '}',
  "html[data-dsh-workshop-active]:not([data-dsh-taskboard-active]):not([data-dsh-ssh-active]) [data-pane='conversation'] > :not([data-dsh-workshop-view]) {",
  '  display: none;',
  '}',
  '`;',
].join('\n');

const NEW_STYLE = [
  'const TAKEOVER_STYLE = `',
  `${TEMPLATE_INTERP} {`,
  '  position: relative;',
  '}',
  '[data-dsh-workshop-view] {',
  '  position: absolute;',
  '  inset: 0;',
  '  display: none;',
  '  z-index: 5;',
  '}',
  'html[data-dsh-workshop-active]:not([data-dsh-taskboard-active]):not([data-dsh-ssh-active]) [data-dsh-workshop-view] {',
  '  display: block;',
  '}',
  `html[data-dsh-workshop-active]:not([data-dsh-taskboard-active]):not([data-dsh-ssh-active]) ${TEMPLATE_INTERP} > :not([data-dsh-workshop-view]) {`,
  '  display: none;',
  '}',
  '`;',
].join('\n');

const PATCHED_MARKER = '[class*=\\"centerCol\\"]';

const original = readFileSync(TARGET, 'utf8');

if (original.includes(PATCHED_MARKER)) {
  console.log('already patched - nothing to do');
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

const sidecar = `${TARGET}.pre-patch`;
if (!existsSync(sidecar)) copyFileSync(TARGET, sidecar);
writeFileSync(TARGET, patched, 'utf8');

console.log('patched OK');
console.log('  bytes:', original.length, '->', patched.length);
console.log('  centerCol selector occurrences:', countOf(patched, PATCHED_MARKER));
console.log('  stylesheet interpolations:', countOf(patched, TEMPLATE_INTERP));
console.log('  sidecar backup:', sidecar, existsSync(sidecar) ? '(present)' : '(MISSING)');
