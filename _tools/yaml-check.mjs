import yaml from 'js-yaml'
import { readFileSync } from 'node:fs'
const custom = new yaml.Type('tag:yaml.org,2002:js', { kind: 'scalar', construct: d => '<<js>>' })
const SCHEMA = yaml.DEFAULT_SCHEMA.extend([custom])
const p = 'C:\\Users\\ROG\\.dsh\\profiles\\desktop\\cordis.patch.yml'
try {
  const doc = yaml.load(readFileSync(p, 'utf8'), { schema: SCHEMA })
  console.log('  YAML 解析成功，顶层条目数 = ' + (Array.isArray(doc) ? doc.length : 'not-array'))
  const ins = doc.find(e => e && Array.isArray(e.insert))
  if (ins) { console.log('  computer-use insert 块如下:'); for (const r of ins.insert) console.log('    - id=' + r.id + '  name=' + r.name + '  config=' + JSON.stringify(r.config)) }
  else console.log('  ★ 未找到 insert 块！')
} catch (e) { console.log('  ★ YAML 解析失败: ' + e.message) }
