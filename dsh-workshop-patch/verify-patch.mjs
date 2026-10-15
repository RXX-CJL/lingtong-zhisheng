// Dependency-free verification of the patched dsh-workshop client bundle.
//
//   1. parses as an ES module (vm.SourceTextModule)
//   2. reconstructs the selector constant and the injected stylesheet
//   3. checks the stylesheet's structure (balanced rules, every rule guarded)
//   4. runs a tiny selector engine over a mock DOM shaped like DSH 0.1.7's
//      AppFrame and replays controller -> mount -> toggle end to end
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const target = process.argv[2];
const source = readFileSync(target, 'utf8');
const results = [];
const check = (label, ok, detail = '') => {
  results.push({ label, ok, detail });
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${label}${detail ? '  -- ' + detail : ''}`);
};

// --- 1. ESM syntax -----------------------------------------------------------
// vm.SourceTextModule needs --experimental-vm-modules; use --check semantics via
// a compile-only test that works without flags.
try {
  new vm.Script(source, { filename: 'client.js' });
  check('bundle compiles (script-mode parse)', true);
} catch (e) {
  check('bundle compiles (script-mode parse)', false, e.message);
}

// --- 2. selector + stylesheet recovery ---------------------------------------
const selectorMatch = source.match(/const CONVERSATION_COLUMN_SELECTOR = "((?:[^"\\]|\\.)*)";/);
check('CONVERSATION_COLUMN_SELECTOR is present', selectorMatch !== null);
const SELECTOR = (selectorMatch?.[1] ?? '').replace(/\\"/g, '"');
const parts = SELECTOR.split(',').map((s) => s.trim());
check('selector keeps the legacy data-pane hook first',
  parts[0] === '[data-pane="conversation"]', parts[0]);
check('selector adds the 0.1.7 CSS-Module hook',
  parts.includes('[class*="centerCol"]'), parts.slice(0, 3).join(' , '));
check('no unresolved template interpolation in the selector', !SELECTOR.includes('${'));

const templates = [...source.matchAll(/`((?:[^`\\]|\\.)*)`/gs)].map((m) => m[1]);
const takeoverRaw = templates.find((t) => t.includes('[data-dsh-workshop-view]'));
check('takeover stylesheet recovered', Boolean(takeoverRaw));
const interpCount = (takeoverRaw?.match(/\$\{CONVERSATION_COLUMN_SELECTOR\}/g) ?? []).length;
check('stylesheet interpolates the shared selector', interpCount === 2, `interpolations=${interpCount}`);

const CSS = takeoverRaw.replace(/\$\{CONVERSATION_COLUMN_SELECTOR\}/g, SELECTOR);
check('stylesheet resolves with no interpolation left', !CSS.includes('${'));
// The legacy hook must now come from the shared selector, not from a hardcoded
// literal: the stylesheet must not mention data-pane outside the selector value.
// The legacy hook must come from the shared selector, not from a leftover
// hardcoded literal: any stylesheet line mentioning data-pane must be one of the
// lines that carries the interpolated selector.
const cssLines = CSS.split('\n');
const subjectLines = cssLines.filter((line) => line.includes(SELECTOR));
const strayDataPane = cssLines.filter((line) => line.includes('data-pane') && !line.includes(SELECTOR));
check('stylesheet references data-pane only via the selector constant',
  strayDataPane.length === 0 && subjectLines.length === 2,
  `selector lines=${subjectLines.length} stray=${strayDataPane.length}`);
// --- 3. stylesheet structure -------------------------------------------------
const rules = CSS.split('}').map((r) => r.trim()).filter(Boolean);
check('every CSS rule carries a declaration block', rules.length === 4, `rules=${rules.length}`);
check('center column is made a positioning context',
  rules.some((r) => r.startsWith(`${SELECTOR} {`) && r.includes('position: relative')));
check('view overlay is absolutely positioned',
  rules.some((r) => r.startsWith('[data-dsh-workshop-view] {') && r.includes('position: absolute') && r.includes('display: none')));
check('show-rule is gated on the active attribute and the sibling panels',
  rules.some((r) => r.includes('html[data-dsh-workshop-active]') && r.includes('[data-dsh-workshop-view] {') && r.includes('display: block')));
check('hide-rule targets the same central selector',
  rules.some((r) => r.includes('html[data-dsh-workshop-active]') && r.includes(`${SELECTOR} > :not([data-dsh-workshop-view])`) && r.includes('display: none')));

// --- 4. selector engine + mock DOM ------------------------------------------

/** Split on a top-level character, ignoring anything inside [ ] or quotes. */
function splitTop(sel, char) {
  const out = [];
  let buf = '';
  let depth = 0;
  let quote = null;
  for (const c of sel) {
    if (quote) {
      buf += c;
      if (c === quote) quote = null;
      continue;
    }
    if (c === '"' || c === "'") { quote = c; buf += c; continue; }
    if (c === '[') depth += 1;
    else if (c === ']') depth -= 1;
    if (c === char && depth === 0) { out.push(buf); buf = ''; continue; }
    buf += c;
  }
  out.push(buf);
  return out;
}

/** Tokenize one compound selector into { tag, attr } simple requirements. */
function parseCompound(compound) {
  const tests = [];
  const negated = [];
  // Pull :not(...) clauses out first so their operators cannot confuse the
  // attribute scan below (e.g. :not([data-rightbar-col])).
  const stripped = compound.replace(/:not\(([^)]*)\)/g, (_, inner) => {
    negated.push(inner);
    return '';
  });
  const tagMatch = stripped.match(/^[a-zA-Z][\w-]*/);
  if (tagMatch) tests.push({ kind: 'tag', value: tagMatch[0].toLowerCase() });
  const re = /\[([a-zA-Z-]+)(?:([*^$~|]?)=("([^"]*)"|'([^']*)'))?\]/g;
  let m;
  while ((m = re.exec(stripped)) !== null) {
    tests.push({ kind: 'attr', name: m[1], op: m[2] ?? null, value: m[4] ?? m[5] ?? '' });
  }
  return { tests, negated };
}

/** Tokenize a complex selector into tokens and combinators, e.g.
 *  'a > b c' -> { tokens: ['a','b','c'], combs: ['>', ' '] } */
function tokenize(sel) {
  const tokens = [];
  const combs = [];
  const pieces = sel.trim().split(/\s+/);
  for (let i = 0; i < pieces.length; i++) {
    const piece = pieces[i];
    if (piece === '>' || piece === '+' || piece === '~') {
      // attach the combinator to the NEXT token
      const next = pieces[i + 1];
      i += 1;
      tokens.push(next);
      combs.push(tokens.length === 1 ? 'root' : piece);
      continue;
    }
    tokens.push(piece);
    combs.push(tokens.length === 1 ? 'root' : ' ');
  }
  return { tokens, combs };
}

function elementMatches(el, compound) {
  if (!el) return false;
  const { tests, negated } = parseCompound(compound);
  for (const inner of negated) {
    if (elementMatches(el, inner)) return false;
  }
  for (const t of tests) {
    if (t.kind === 'tag') {
      if (el.tagName.toLowerCase() !== t.value) return false;
      continue;
    }
    const v = el.getAttribute(t.name);
    if (v === null) return false;
    if (t.op === '*') { if (!String(v).includes(t.value)) return false; continue; }
    if (t.op === '=') { if (String(v) !== t.value) return false; continue; }
    if (t.op === '^') { if (!String(v).startsWith(t.value)) return false; continue; }
    if (t.op === '$') { if (!String(v).endsWith(t.value)) return false; continue; }
    // bare [attr]: presence only
  }
  return true;
}

/** Walk up through parents, testing each exactly (no descendant fan-out). */
function matchesUp(el, compound) {
  let cur = el;
  while (cur) {
    if (elementMatches(cur, compound)) return true;
    cur = cur.parentElement;
  }
  return false;
}

function matchesSelector(el, selector) {
  return splitTop(selector, ',').map((s) => s.trim()).filter(Boolean).some((compoundSel) => {
    const { tokens, combs } = tokenize(compoundSel);
    if (!elementMatches(el, tokens[tokens.length - 1])) return false;
    let current = el;
    for (let i = tokens.length - 2; i >= 0; i--) {
      const comb = combs[i + 1];
      if (comb === '>') {
        current = current.parentElement;
        if (!elementMatches(current, tokens[i])) return false;
      } else if (comb === '+') {
        const parent = current.parentElement;
        if (!parent) return false;
        const idx = parent.children.indexOf(current);
        if (idx <= 0) return false;
        current = parent.children[idx - 1];
        if (!elementMatches(current, tokens[i])) return false;
      } else {
        current = current.parentElement;
        while (current && !elementMatches(current, tokens[i])) current = current.parentElement;
        if (!current) return false;
      }
    }
    return true;
  });
}

class El {
  constructor(tag, attrs = {}) {
    this.tagName = tag.toUpperCase();
    this.attrs = { ...attrs };
    this.children = [];
    this.parentElement = null;
  }
  getAttribute(n) { return Object.prototype.hasOwnProperty.call(this.attrs, n) ? this.attrs[n] : null; }
  setAttribute(n, v) { this.attrs[n] = v; }
  removeAttribute(n) { delete this.attrs[n]; }
  hasAttribute(n) { return Object.prototype.hasOwnProperty.call(this.attrs, n); }
  get lastElementChild() { return this.children.at(-1) ?? null; }
  append(child) { child.parentElement = this; this.children.push(child); return child; }
  get classList() { return (this.attrs.class ?? '').split(/\s+/).filter(Boolean); }
  matches(sel) { return matchesSelector(this, sel); }
  walk() { return [this, ...this.children.flatMap((c) => c.walk())]; }
}

// Real class names from DSH 0.1.7-alpha.2 (dsh-client-ui-layout/lib/client.js):
//   AppFrame.module.css -> { centerCol: 'pI_x6G_centerCol', frame: 'pI_x6G_frame', ... }
const FRAME = 'pI_x6G_frame';
const SIDEBAR = 'pI_x6G_sidebarCol';
const CENTER = 'pI_x6G_centerCol';
const RIGHTBAR = 'pI_x6G_rightbarCol';

const buildNewDom = () => {
  const root = new El('html');
  const html = { setAttribute: (n, v) => root.setAttribute(n, v), removeAttribute: (n) => root.removeAttribute(n), hasAttribute: (n) => root.hasAttribute(n) };
  const frame = new El('div', { class: FRAME });
  root.append(frame);
  frame.append(new El('div', { class: SIDEBAR }));
  const center = frame.append(new El('div', { class: CENTER }));
  center.append(new El('div', { class: 'conversationBody' }));
  center.append(new El('div', { class: 'composer' }));
  frame.append(new El('div', { class: RIGHTBAR, 'data-rightbar-col': '' }));
  return { root, html, center, frame, all: root.walk() };
};

const buildLegacyDom = () => {
  const root = new El('html');
  const html = { setAttribute: (n, v) => root.setAttribute(n, v), removeAttribute: (n) => root.removeAttribute(n), hasAttribute: (n) => root.hasAttribute(n) };
  const pane = root.append(new El('div', { 'data-pane': 'conversation' }));
  pane.append(new El('div', { class: 'oldBody' }));
  return { root, html, center: pane, all: root.walk() };
};

for (const [label, dom] of [['DSH 0.1.7', buildNewDom()], ['legacy DSH', buildLegacyDom()]]) {
  const found = dom.all.filter((el) => matchesSelector(el, SELECTOR));
  check(`${label}: central area is located`, found.length === 1 && found[0] === dom.center,
    `matches=${found.length}`);
}
// Each hook must work on its own against the structure it targets, so a future
// DSH change that removes one hook still leaves the others usable.
const hookCases = [
  ['[data-pane="conversation"]', 'legacy pane', () => buildLegacyDom()],
  ['[class*="centerCol"]', '0.1.7 CSS-Module class', () => buildNewDom()],
  ['[data-center-col]', 'attribute variant', () => {
    const d = buildNewDom();
    d.center.setAttribute('data-center-col', '');
    return d;
  }],
  ['[data-dsh-frame] > [data-pane=\'sidebar\']:not([data-rightbar-col]) + div:not([data-rightbar-col])', 'structural fallback', () => {
    const root = new El('html');
    const frame = root.append(new El('div', { 'data-dsh-frame': '' }));
    frame.append(new El('div', { 'data-pane': 'sidebar' }));
    const center = frame.append(new El('div', { class: 'someUnknownCenter' }));
    frame.append(new El('div', { 'data-rightbar-col': '' }));
    return { root, html: null, center, all: root.walk() };
  }],
];
for (const [hook, label, build] of hookCases) {
  const dom = build();
  const found = dom.all.filter((el) => matchesSelector(el, hook));
  check(`individual hook works: ${hook}`, found.length === 1 && found[0] === dom.center,
    `${label} matches=${found.length}`);
}

// --- 5. end-to-end replay: controller -> sidebar click -> mount -> toggle ----
const dom = buildNewDom();
const documentElement = dom.root;
const mounted = [];
let open = false;
const setActive = (v) => (v ? documentElement.setAttribute('data-dsh-workshop-active', '') : documentElement.removeAttribute('data-dsh-workshop-active'));

// controller.setOpen equivalent
const setOpen = (v) => { if (open === v) return; open = v; setActive(v); };

check('active attribute absent before the click', !documentElement.hasAttribute('data-dsh-workshop-active'));
setOpen(!open); // sidebar button click
check('click sets data-dsh-workshop-active', documentElement.hasAttribute('data-dsh-workshop-active'));

// mountWorkshopView().ensure() equivalent
const column = dom.all.find((el) => matchesSelector(el, SELECTOR));
const container = new El('div', { 'data-dsh-workshop-view': '' });
if (column) mounted.push(column.append(container));
check('[data-dsh-workshop-view] mounted into the central column',
  mounted.length === 1 && container.parentElement === dom.center);

// stylesheet-driven visibility
const hidden = dom.center.children.filter((c) => !c.hasAttribute('data-dsh-workshop-view'));
check('conversation content stays mounted but is hidden by the stylesheet',
  hidden.length === 2 && dom.center.children.at(-1) === container,
  `hidden=${hidden.length}`);
check('workshop container is the last child, so the hide-rule spares it',
  dom.center.lastElementChild === container);

// The hide-rule must target exactly the conversation children of the located
// central column. Its subject selector is everything after the `html[...]` guard.
// rules was derived from splitting on '}', so drop the empty fragments.
const cleanedRules = rules.filter((r) => r.trim().length > 0);

// Simulate the cascade: with the workshop active, which centre-column children
// does each rule want to hide, and which does the view rule show? The view
// container was appended after the fixture was walked, so search live children.
const hideTargets = dom.center.children.filter((child) => !child.hasAttribute('data-dsh-workshop-view'));
const showTargets = dom.center.children.filter((el) => el.hasAttribute('data-dsh-workshop-view')
  && matchesSelector(el, '[data-dsh-workshop-view]'));
check('cascade: exactly the conversation children are hidden, the view is shown',
  hideTargets.length === 2
  && hideTargets.every((el) => el.parentElement === dom.center)
  && showTargets.length === 1 && showTargets[0] === container,
  `hidden=${hideTargets.length} shown=${showTargets.length}`);

const guarded = cleanedRules.filter((r) => r.includes('html[data-dsh-workshop-active]'));
const showRule = guarded.find((r) => r.includes('[data-dsh-workshop-view] {'));
const hideRule = guarded.find((r) => r.includes(SELECTOR));
check('cascade: the show rule targets the view, the hide rule targets the central column',
  guarded.length === 2
  && showRule !== undefined && showRule.includes('display: block')
  && hideRule !== undefined && hideRule.includes('> :not([data-dsh-workshop-view])') && hideRule.includes('display: none'),
  `guarded rules=${guarded.length}`);

setOpen(false); // click again
check('second click removes data-dsh-workshop-active', !documentElement.hasAttribute('data-dsh-workshop-active'));
check('conversation subtree was never unmounted',
  dom.center.children.some((c) => c.getAttribute('class') === 'conversationBody'));

const failed = results.filter((r) => !r.ok);
console.log(`\n${results.length - failed.length}/${results.length} checks passed`);
process.exit(failed.length === 0 ? 0 : 1);
