/**
 * 前端日志系统 utils/logger.js
 * ----------------------------------------------------------------
 * 用途：方便日常网页端维护 & 找 bug（用户要求的"有没有日志之类记录"）
 *
 * 功能：
 *  1. 带级别的日志 API：log.debug / info / warn / error / fatal / tag('xxx').debug(...)
 *  2. 环形缓冲区（默认 2000 条，超过后老的自动丢弃）
 *  3. 劫持 console.*（不影响原输出，同时记录到日志缓冲区）
 *  4. 捕获全局 window.onerror + unhandledrejection（JS 运行时崩溃、未处理 Promise 拒绝）
 *  5. 捕获 Vue 应用 errorHandler 错误（在 main.js 调用 installVueErrorHandler(app) 启用）
 *  6. localStorage 持久化：刷新页面不丢日志。体积超上限后按旧est 50%裁切。
 *  7. 导出 JSON / 清空 / 查询 API，供 SystemLog.vue 使用
 *
 * 用法：
 *   import logger from '@/utils/logger'
 *   logger.info('模块A初始化OK', { version })
 *   logger.tag('axios').warn('请求慢', { url, ms })
 *   logger.error('启动失败', new Error('xxx'))
 *   // 查看所有日志
 *   logger.query({ level: 'warn', keyword: 'camera' })
 *   // 导出
 *   logger.exportAsJsonDownload()
 */

const LOG_STORAGE_KEY = 'zt_frontend_logs_v1'
const LOG_MAX_ENTRIES = 2000
const PERSIST_THROTTLE_MS = 500
const PERSIST_SIZE_WARN_BYTES = 2 * 1024 * 1024 // 2MB 后警告并截断

const LEVELS = { DEBUG: 10, INFO: 20, WARN: 30, ERROR: 40, FATAL: 50 }
const LEVEL_ORDER = ['DEBUG', 'INFO', 'WARN', 'ERROR', 'FATAL']

/**
 * ★★2026-10-10 由 DSH 新增：**循环引用安全的 JSON 序列化**。
 *
 * 真实事故（用户 2026-10-10 反馈）：在 /settings 页点「导出」报
 *   TypeError: Converting circular structure to JSON
 *     --> starting at object with constructor 'Object'
 *     |     property 'component' -> object with constructor 'Object'
 *     --- property 'vnode' closes the circle
 *
 * 根因链（**两层都错，都要修**）：
 *   ① push() 里对不可序列化的对象只做 `try { JSON.stringify(a) } catch { extra = a }`
 *      —— 把**原始对象**（此处是带组件实例的 Vue VNode / 传入的组件 props）
 *      原封不动存进环形缓冲区，**等于存了一颗定时炸弹**；
 *   ② exportAsJsonDownload() / persistNow() 再对它 JSON.stringify -> 抛错。
 *      导出是显式报错（用户看得见）；而 persistNow 的错**被 try/catch 静默吞掉**
 *      -> localStorage 里那条记录永远存不下来（刷新即丢），且**没有任何提示**。
 *
 * 修法：任何要落盘/导出的对象都先过这里 —— 遇到循环引用或 DOM/组件对象就
 * 替换成可读的占位符，而不是抛错；**保证"导出一定成功"**（日志工具连导出都失败
 * 就等于没有）。
 */
function _safeJson(value, space = 0) {
  const seen = new WeakSet()
  try {
    return JSON.stringify(value, function (key, val) {
      try {
        if (typeof val === 'bigint') return String(val) + 'n'
        if (typeof val === 'function') return '[Function]'
        if (val && typeof val === 'object') {
          // ★★绝对不要在这里用 `instanceof` / `Object.getPrototypeOf` / `constructor`！
          // 本项目的 payload（axios 响应、Vue 组件实例、被打上 Vue 响应式的对象）
          // 很可能是 **Proxy**，而 Vue 的 getPrototypeOf 陷阱在"目标对象不可扩展"时会
          // **直接抛 TypeError**，导致**每一个对象**都掉进 catch -> 整个负载变成
          // "[Unserializable]"（2026-10-10 实测：导出只有 18 字节）。
          // 这里一律只用"读属性"做鸭子类型判断 —— get 陷阱是安全的。
          const nodeName = val.nodeName
          if (typeof nodeName === 'string' && typeof val.nodeType === 'number') {
            return `[DOM ${nodeName}]`
          }
          const el = val.$el
          const vnode = val.$ && val.$.vnode
          if (el || vnode !== undefined) return '[VueComponent]'
          if (seen.has(val)) return '[Circular]'
          seen.add(val)
        }
        return val
      } catch (_) {
        return '[Unserializable]'
      }
    }, space)
  } catch (_) {
    // ★绝不让"序列化失败"升级成"导出失败"：退化成纯字符串
    try { return String(value) } catch (__) { return '[Unserializable]' }
  }
}

/** 会话窗口：把任意值变成**一段必然可显示、可导出**的文本 */
function _safeStr(value, maxLen = 4000) {
  try {
    const s = _safeJson(value)
    if (typeof s === 'string') return s.length > maxLen ? s.slice(0, maxLen) + '…[truncated]' : s
  } catch (_) { /* fallthrough */ }
  try { return String(value).slice(0, maxLen) } catch (_) { return '[unprintable]' }
}

function tsIso() {
  try { return new Date().toISOString() } catch (_) { return String(Date.now()) }
}
function timeMs() { return Date.now() }

class RingBuffer {
  constructor(max) { this.max = max; this.items = [] }
  push(entry) {
    this.items.push(entry)
    if (this.items.length > this.max) {
      // 一次丢 1/4，避免每次 push 都移位
      const drop = Math.ceil(this.max / 4)
      this.items.splice(0, drop)
    }
  }
  getAll() { return this.items }
  size() { return this.items.length }
  clear() { this.items = [] }
}

const buffer = new RingBuffer(LOG_MAX_ENTRIES)
let nextSeq = 1

// ---- 持久化：节流写入 localStorage ----
let persistTimer = null
let dirty = false
function schedulePersist() {
  dirty = true
  if (persistTimer) return
  persistTimer = setTimeout(() => {
    persistTimer = null
    if (!dirty) return
    persistNow()
  }, PERSIST_THROTTLE_MS)
}

function persistNow() {
  try {
    // ★2026-10-10：改用 _safeJson —— 万一缓冲区里混进了带循环引用的对象
    // （旧版本写进去的历史记录、或将来别处误传），也不会让**落盘静默失败**。
    const payload = _safeJson({
      savedAt: tsIso(),
      items: buffer.getAll()
    })
    if (payload.length > PERSIST_SIZE_WARN_BYTES) {
      // 超限：丢弃前一半，再写
      const all = buffer.getAll()
      buffer.clear()
      all.slice(Math.floor(all.length / 2)).forEach(e => buffer.push(e))
      const retry = _safeJson({ savedAt: tsIso(), items: buffer.getAll() })
      localStorage.setItem(LOG_STORAGE_KEY, retry)
    } else {
      localStorage.setItem(LOG_STORAGE_KEY, payload)
    }
    dirty = false
  } catch (e) {
    // localStorage 禁用 / 超容量，不影响业务
    if (e && e.name === 'QuotaExceededError') {
      try { localStorage.removeItem(LOG_STORAGE_KEY) } catch (_) { /* noop */ }
    }
  }
}

// 启动时加载上次留存的日志
function loadPersisted() {
  try {
    const raw = localStorage.getItem(LOG_STORAGE_KEY)
    if (!raw) return
    const parsed = JSON.parse(raw)
    if (parsed && Array.isArray(parsed.items)) {
      parsed.items.forEach(it => buffer.push(it))
      // 补齐 seq 上限
      if (buffer.size() > 0) {
        const maxSeq = buffer.getAll().reduce((m, x) => Math.max(m, x.seq || 0), 0)
        nextSeq = maxSeq + 1
      }
    }
  } catch (_) { /* ignore */ }
}
loadPersisted()

// ---- 基础 push API ----
function push(level, tag, args) {
  let message = ''
  let extra = null
  let err = null
  const parts = []
  for (const a of args) {
    if (a instanceof Error) {
      err = {
        name: a.name,
        message: a.message,
        stack: a.stack && String(a.stack).slice(0, 3000)
      }
      parts.push(`${a.name}: ${a.message}`)
    } else if (typeof a === 'string' || typeof a === 'number' || typeof a === 'boolean' || a == null) {
      parts.push(String(a))
    } else {
      // ★★2026-10-10 由 DSH 修正（导出崩溃的根因①）：
      // 旧写法 `const s = JSON.stringify(a)` 在 a 有**循环引用**时直接抛错，
      // 于是走 catch 把**原始对象**存进 extra -> 导出/落盘时才炸。
      // 现在改为「先安全序列化，再决定放 message 还是 extra」，
      // **extra 里永远只存字符串**（可显示、必然可导出、必然可落盘）。
      let s
      try {
        s = _safeJson(a)
      } catch (_) {
        s = null
      }
      if (typeof s !== 'string') s = _safeStr(a)
      if (s.length < 512) parts.push(s)
      else extra = s
    }
  }
  message = parts.join(' ')
  const entry = {
    seq: nextSeq++,
    t: tsIso(),
    ms: timeMs(),
    level,
    tag: tag || null,
    url: (typeof location !== 'undefined' ? location.pathname + location.hash : ''),
    message,
    err: err || undefined,
    extra: extra || undefined
  }
  buffer.push(entry)
  schedulePersist()
  return entry
}

// ---- 带标签的链式调用：logger.tag('axios').warn('xxx') ----
function tag(tagName) {
  const t = String(tagName || '').slice(0, 32)
  return {
    debug: (...a) => push('DEBUG', t, a),
    info:  (...a) => push('INFO',  t, a),
    warn:  (...a) => push('WARN',  t, a),
    error: (...a) => push('ERROR', t, a),
    fatal: (...a) => push('FATAL', t, a),
  }
}

const logger = {
  debug: (...a) => push('DEBUG', null, a),
  info:  (...a) => push('INFO',  null, a),
  warn:  (...a) => push('WARN',  null, a),
  error: (...a) => push('ERROR', null, a),
  fatal: (...a) => push('FATAL', null, a),
  tag,

  /** 查询日志。筛选条件可组合。最新在前。 */
  query({ level = null, tag: tagFilter = null, keyword = null, since = null, limit = null } = {}) {
    let list = buffer.getAll().slice()
    if (level) {
      const min = LEVELS[String(level).toUpperCase()]
      if (Number.isFinite(min)) list = list.filter(x => (LEVELS[x.level] || 0) >= min)
    }
    if (tagFilter) list = list.filter(x => x.tag === tagFilter)
    if (keyword) {
      const k = String(keyword).toLowerCase()
      list = list.filter(x => (x.message || '').toLowerCase().includes(k))
    }
    if (since) {
      const sinceMs = new Date(since).getTime()
      if (Number.isFinite(sinceMs)) list = list.filter(x => x.ms >= sinceMs)
    }
    // 最新在前
    list.reverse()
    if (limit && limit > 0) list = list.slice(0, limit)
    return list
  },

  /** 清空内存 + localStorage */
  clear() {
    buffer.clear()
    try { localStorage.removeItem(LOG_STORAGE_KEY) } catch (_) {}
  },

  /** 日志条数 */
  size() { return buffer.size() },

  /** 导出 JSON 文件下载 */
  exportAsJsonDownload(filename = 'zhitong-frontend-log.json') {
    try {
      // ★2026-10-10：改用 _safeJson（原来直接 JSON.stringify 会因循环引用抛错，
      // 用户点「导出」直接报错，而第 5 项"MJPEG 僵尸流"取证正要靠这份导出）。
      // 另外加一道**兜底**：万一整体序列化仍失败，就逐条导出，**绝不整份丢失**
      // （日志工具的价值就在于"出事时它还能用"，不能反过来成为新的故障点）。
      let payload = null
      try {
        payload = _safeJson({
          exportedAt: tsIso(),
          href: typeof location !== 'undefined' ? location.href : '',
          ua: typeof navigator !== 'undefined' ? navigator.userAgent : '',
          total: buffer.size(),
          items: buffer.getAll()
        }, 2)
      } catch (e1) {
        const lines = buffer.getAll().map(it => {
          try { return _safeJson(it) } catch (_) { return _safeStr(it) }
        })
        payload = _safeJson({
          exportedAt: tsIso(),
          degraded: true,
          reason: String(e1).slice(0, 200),
          total: buffer.size(),
          items: lines
        }, 2)
      }
      const blob = new Blob([payload], { type: 'application/json;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      setTimeout(() => URL.revokeObjectURL(url), 1000)
      return true
    } catch (e) {
      console.error('[logger] 导出失败', e)
      return false
    }
  },

  /** 诊断摘要（★2026-10-10 新增）：一键复制用，只要最关键的信息 */
  diagnosticSummary() {
    const all = buffer.getAll()
    const byLevel = {}
    all.forEach(x => { byLevel[x.level] = (byLevel[x.level] || 0) + 1 })
    const fails = all.filter(x => /FAIL|timeout|超时|失败|ECONN|Network Error/i.test(x.message || ''))
    const tail = fails.slice(-40).map(x => `${x.t} [${x.level}] ${x.tag || '-'} ${(x.message || '').slice(0, 300)}`)
    return [
      `导出时间: ${tsIso()}`,
      `页面: ${typeof location !== 'undefined' ? location.href : ''}`,
      `日志总数: ${all.length}  级别分布: ${_safeJson(byLevel)}`,
      `疑似失败条数: ${fails.length}`,
      '--- 最近 40 条疑似失败（FAIL/timeout/超时/失败） ---',
      ...tail
    ].join('\n')
  },

  /** 立即强制落盘 */
  flush() { persistNow() },

  get LEVELS() { return LEVELS },
  get LEVEL_ORDER() { return LEVEL_ORDER.slice() }
}

export default logger

// =========================================================================
// 以下：自动安装全局 hook（导入即生效）
// =========================================================================

// 1) 劫持 console.*，原输出继续保留，同时写入日志
const _orig = {
  debug: console.debug.bind(console),
  info:  console.info.bind(console),
  log:   console.log.bind(console),
  warn:  console.warn.bind(console),
  error: console.error.bind(console),
}
console.debug = function hookedDebug(...args) { _orig.debug(...args); push('DEBUG', 'console', args) }
console.info  = function hookedInfo(...args)  { _orig.info(...args);  push('INFO',  'console', args) }
console.log   = function hookedLog(...args)   { _orig.log(...args);   push('INFO',  'console', args) }
console.warn  = function hookedWarn(...args)  { _orig.warn(...args);  push('WARN',  'console', args) }
console.error = function hookedError(...args) { _orig.error(...args); push('ERROR', 'console', args) }

// 2) window.onerror
function _onError(msg, src, lineno, colno, err) {
  push('FATAL', 'window.onerror', [
    `msg=${msg} src=${src || ''} line=${lineno} col=${colno}`,
    err || null
  ])
  return false
}
function _onUnhandledRejection(ev) {
  const reason = ev && (ev.reason || ev.detail && ev.detail.reason)
  push('FATAL', 'unhandledrejection', [
    'Unhandled Promise rejection:',
    reason instanceof Error ? reason : (reason != null ? String(reason).slice(0, 1000) : 'null')
  ])
}
if (typeof window !== 'undefined') {
  try {
    window.addEventListener('error', _onError, true)
    window.addEventListener('unhandledrejection', _onUnhandledRejection, true)
  } catch (_) { /* SSR or sandbox */ }
}

// 3) Vue 全局错误（main.js 导入后调用）
export function installVueErrorHandler(app) {
  if (!app || typeof app.config !== 'object') return
  const prev = app.config.errorHandler
  app.config.errorHandler = function ztVueError(err, vm, info) {
    push('FATAL', 'vue', [
      `Vue error: info=${info || ''} component=${vm && vm.$options ? vm.$options.name || '(anon)' : ''}`,
      err instanceof Error ? err : String(err)
    ])
    // 保留之前的 handler（如 Vue SFC / devtool）
    if (typeof prev === 'function') {
      try { prev(err, vm, info) } catch (_) {}
    }
    // 生产环境不抛到 window.onerror 避免重复
    if (prev) return
    // eslint-disable-next-line no-console
    console.error('[Vue error]', err, info)
  }
  logger.info('Logger installVueErrorHandler installed')
}

// 启动时注入一条 session 启动日志
push('INFO', 'session', [
  `Frontend session started. path=${typeof location !== 'undefined' ? location.pathname : ''}`
])
