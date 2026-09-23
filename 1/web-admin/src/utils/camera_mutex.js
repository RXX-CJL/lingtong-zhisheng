/**
 * 摄像头互斥锁（前端侧）
 * ----------------------------------
 * 防止两个监控页面（/realtime 和 /ai-detect）同时打开同一个物理摄像头：
 *   - 浏览器 getUserMedia /ai-detect 后端 cv2 都依赖硬件独占
 *   - 任何一方启动前必须 acquire(owner)
 *   - 离开页面 / 停止检测 必须 release(owner)
 *   - 通过 localStorage + 'storage' 事件实现跨标签页同步
 *
 * 用法：
 *   import { acquireCameraLock, releaseCameraLock, isCameraLockedByOther } from '@/utils/camera_mutex'
 *
 *   const ok = acquireCameraLock({
 *     owner: 'RealTimeMonitor',          // 模块名（自己选一个稳定字符串）
 *     reason: '用户点击开始检测',          // 可选：说明占用原因
 *     path: '/realtime'                   // 可选：哪条路由占用
 *   })
 *   if (!ok) { ElMessage.warning('另一个页面正在使用摄像头，请先关闭。') }
 *
 *   onUnmounted(() => releaseCameraLock('RealTimeMonitor'))
 */

const LOCK_KEY = 'zt_camera_lock_v1'
const LOCK_TTL_MS = 5 * 60 * 1000 // 5 分钟兜底过期（防止崩溃后永久占用）

function _now() { return Date.now() }

function _read() {
  try {
    const raw = localStorage.getItem(LOCK_KEY)
    if (!raw) return null
    const data = JSON.parse(raw)
    // 自动清理过期锁
    if (data.expireAt && data.expireAt < _now()) {
      localStorage.removeItem(LOCK_KEY)
      return null
    }
    return data
  } catch (_) {
    return null
  }
}

function _write(data) {
  try {
    if (data === null) {
      localStorage.removeItem(LOCK_KEY)
    } else {
      localStorage.setItem(LOCK_KEY, JSON.stringify(data))
    }
  } catch (_) { /* localStorage 禁用 */ }
}

/**
 * 尝试获取摄像头锁
 * @param {{owner:string, reason?:string, path?:string}} info  owner 必须唯一（模块名）
 * @returns {boolean} true = 拿到锁；false = 被别人占用
 */
export function acquireCameraLock(info) {
  if (!info || typeof info.owner !== 'string' || !info.owner) {
    return false
  }
  const existing = _read()
  const now = _now()
  if (existing && existing.owner !== info.owner) {
    // 已经被别人占用（非过期，_read 里已过滤） → 拒绝
    return false
  }
  _write({
    owner: info.owner,
    reason: info.reason || '',
    path: info.path || (typeof location !== 'undefined' ? location.pathname : ''),
    acquiredAt: now,
    expireAt: now + LOCK_TTL_MS,
    tabId: _selfTabId()
  })
  return true
}

/**
 * 释放摄像头锁。只有 owner 自己能释放。
 */
export function releaseCameraLock(owner) {
  if (!owner) return
  const existing = _read()
  if (!existing) return
  if (existing.owner !== owner && existing.tabId !== _selfTabId()) {
    // 非自己的锁，不越权释放
    return
  }
  _write(null)
}

/** 当前摄像头是否被 *其它* 页面占用（用于 UI 提示） */
export function isCameraLockedByOther(selfOwner) {
  const data = _read()
  if (!data) return null
  if (selfOwner && data.owner === selfOwner) return null
  return {
    owner: data.owner,
    reason: data.reason,
    path: data.path,
    acquiredAt: data.acquiredAt,
    howLongAgoMs: _now() - data.acquiredAt
  }
}

/** 读取当前锁的快照（调试用） */
export function peekCameraLock() {
  return _read()
}

/**
 * 监听（跨 tab）锁被抢事件：
 *   当你已经拿到锁，但另一页面强行通过页面关闭等方式让本标签页失效时，
 *   仍然用 storage 事件通知。真实 acquire 本身是强互斥的，
 *   这里主要用于当对方 *释放* 了锁之后我们可以在 UI 上更新状态。
 * @param {(snapshot)=>void} cb
 * @returns {()=>void} unsub 取消订阅
 */
export function onCameraLockChanged(cb) {
  function handler(e) {
    if (e.key !== LOCK_KEY) return
    cb(_read())
  }
  window.addEventListener('storage', handler)
  return () => window.removeEventListener('storage', handler)
}

// ---- tab id（同一 tab 内稳定） ----
let _tabIdCache = null
function _selfTabId() {
  if (_tabIdCache) return _tabIdCache
  try {
    let v = sessionStorage.getItem('zt_tab_id')
    if (!v) {
      v = 'tab_' + Math.random().toString(36).slice(2, 10)
      sessionStorage.setItem('zt_tab_id', v)
    }
    _tabIdCache = v
    return v
  } catch (_) {
    return 'tab_unknown'
  }
}
