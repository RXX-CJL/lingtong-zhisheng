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
    const payload = JSON.stringify({
      savedAt: tsIso(),
      items: buffer.getAll()
    })
    if (payload.length > PERSIST_SIZE_WARN_BYTES) {
      // 超限：丢弃前一半，再写
      const all = buffer.getAll()
      buffer.clear()
      all.slice(Math.floor(all.length / 2)).forEach(e => buffer.push(e))
      const retry = JSON.stringify({ savedAt: tsIso(), items: buffer.getAll() })
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
      try {
        const s = JSON.stringify(a)
        if (s.length < 512) parts.push(s); else extra = a
      } catch (_) {
        extra = a
      }
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
      const payload = JSON.stringify({
        exportedAt: tsIso(),
        href: typeof location !== 'undefined' ? location.href : '',
        ua: typeof navigator !== 'undefined' ? navigator.userAgent : '',
        total: buffer.size(),
        items: buffer.getAll()
      }, null, 2)
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
