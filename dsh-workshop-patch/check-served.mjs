// Fetch the shell index, find the dsh-workshop bundle URL it advertises, then
// fetch that exact combo URL and check whether it carries the patch.
const base = process.env.DSH_WEB_URL ?? 'http://127.0.0.1:3080';

const indexRes = await fetch(`${base}/`, { redirect: 'manual' });
console.log('GET / ->', indexRes.status, '| content-type:', indexRes.headers.get('content-type'));
const html = await indexRes.text();
console.log('index bytes:', html.length);

const refs = [...html.matchAll(/["'`]([^"'`]*plugins[^"'`]*)["'`]/g)].map((m) => m[1]);
console.log('plugin refs found:', refs.length);
const workshopRefs = refs.filter((r) => r.includes('dsh-workshop'));
console.log('dsh-workshop refs:', JSON.stringify(workshopRefs, null, 2));

// The graph may be fetched separately; look for the boot payload too.
const bootRefs = [...html.matchAll(/dsh-workshop[^"'`,\s]*/g)].map((m) => m[0]);
console.log('raw dsh-workshop tokens:', JSON.stringify([...new Set(bootRefs)].slice(0, 6), null, 2));

for (const ref of workshopRefs.slice(0, 2)) {
  const url = new URL(ref, base).toString();
  const res = await fetch(url);
  const text = await res.text();
  console.log('---');
  console.log('GET', url.replace(base, '').slice(0, 120), '->', res.status, '| bytes:', text.length);
  console.log('  patched centerCol selector present:', text.includes('[class*=\\"centerCol\\"]'));
  console.log('  legacy-only selector present      :', text.includes('"[data-pane=\\"conversation\\"]";'));
}
