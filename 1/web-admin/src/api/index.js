import axios from 'axios'
import { ElMessage } from 'element-plus'
import logger from '../utils/logger'

// 统一的 axios 拦截器：记录日志 + 记录耗时 + 失败自动打 warn/error
function installLoggingInterceptors(instance, tagName, baseURL) {
  instance.interceptors.request.use(config => {
    config.__zt_startedAt = Date.now()
    logger.tag(tagName).debug(
      `REQ  ${config.method?.toUpperCase() || 'GET'} ${config.url}`,
      { baseURL: baseURL || config.baseURL || '' }
    )
    return config
  })
  instance.interceptors.response.use(
    res => {
      const started = res.config && res.config.__zt_startedAt
      const ms = started ? Date.now() - started : -1
      const status = res.status
      const body = res.data
      // body 里的 success=false 视为业务失败，打 warn
      const businessOk = !(body && typeof body === 'object' && 'success' in body && body.success === false)
      const data = body && typeof body === 'object'
        ? { success: body.success, code: body.code, message: (body.message || '').slice(0, 200) }
        : { rawType: typeof body }
      if (businessOk) {
        logger.tag(tagName).debug(
          `RESP ${status} ${res.config.method?.toUpperCase() || 'GET'} ${res.config.url} cost=${ms}ms`,
          data
        )
      } else {
        logger.tag(tagName).warn(
          `RESP business-fail ${status} ${res.config.url} cost=${ms}ms`,
          data
        )
      }
      return res.data
    },
    err => {
      const cfg = err && err.config
      const started = cfg && cfg.__zt_startedAt
      const ms = started ? Date.now() - started : -1
      const status = err && err.response ? err.response.status : 'NO_RESP'
      const method = cfg ? (cfg.method || 'GET').toUpperCase() : 'GET'
      const url = cfg ? cfg.url : '(unknown)'
      logger.tag(tagName).error(
        `HTTP FAIL ${status} ${method} ${url} cost=${ms}ms`,
        { message: err?.message || '', code: err?.code || '' }
      )
      ElMessage.error(err.message || '请求失败')
      return Promise.reject(err)
    }
  )
}

const request = axios.create({
  baseURL: '/api',
  timeout: 15000
})
installLoggingInterceptors(request, 'axios', '/api')

// 实时检测专用实例：直连后端，绕过 Vite 代理
// 原因：Vite 代理在转发 MJPEG 流时会阻塞后续请求
const BACKEND_DIRECT_URL = window.location.protocol + '//' + window.location.hostname + ':8001'
const realtimeRequest = axios.create({
  baseURL: BACKEND_DIRECT_URL + '/api',
  timeout: 15000
})
installLoggingInterceptors(realtimeRequest, 'axios-rt', BACKEND_DIRECT_URL + '/api')

// ============== 违规管理 ==============
export const getList = (params) => {
  return request.get('/violations/list', { params })
}

export const getDetail = (id) => {
  return request.get(`/violations/${id}`)
}

// M04: 按车牌号查询历史违规
export const getByPlate = (plateNumber, params = {}) => {
  return request.get(`/violations/plate/${encodeURIComponent(plateNumber)}`, { params })
}

// M04: 拼接车牌小图访问 URL
export const getPlateImageUrl = (plateImagePath) => {
  if (!plateImagePath) return ''
  return `/api/violations/plate-image/file?path=${encodeURIComponent(plateImagePath)}`
}

export const update = (id, data) => {
  return request.put(`/violations/${id}`, data)
}

export const remove = (id) => {
  return request.delete(`/violations/${id}`)
}

export const getStats = () => {
  return request.get('/violations/statistics/summary')
}

export const submitViolation = (data) => {
  return request.post('/violations/submit', data)
}

export const batchSubmit = (data) => {
  return request.post('/violations/batch', data)
}

export const reanalyze = (id) => {
  return request.put(`/violations/${id}/reanalyze`)
}

export const uploadFileForAi = (formData, onProgress) => {
  return axios.post('/api/violations/upload-multipart', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
    onUploadProgress: (e) => {
      if (onProgress && e.total) {
        onProgress(Math.round(e.loaded * 100 / e.total))
      }
    }
  }).then(res => res.data)
}

// ============== 统计分析 ==============
export const getStatisticsOverview = () => {
  return request.get('/statistics/overview')
}

export const getDailyStats = (days = 7) => {
  return request.get('/statistics/daily', { params: { days } })
}

export const getTypeDistribution = (period = 'all') => {
  return request.get('/statistics/type-distribution', { params: { period } })
}

export const getHourlyDistribution = () => {
  return request.get('/statistics/hourly')
}

// ============== 设备管理 ==============
export const getDeviceList = (params) => {
  return request.get('/devices/list', { params })
}

export const getDeviceDetail = (deviceId) => {
  return request.get(`/devices/${deviceId}`)
}

export const registerDevice = (data) => {
  return request.post('/devices/register', data)
}

export const updateDevice = (deviceId, data) => {
  return request.put(`/devices/${deviceId}`, data)
}

export const deleteDevice = (deviceId) => {
  return request.delete(`/devices/${deviceId}`)
}

export const deviceHeartbeat = (data) => {
  return request.post('/devices/heartbeat', data)
}

export const getDeviceViolations = (deviceId, limit = 50) => {
  return request.get(`/devices/${deviceId}/violations`, { params: { limit } })
}

// ============== 申诉管理 ==============
export const submitAppeal = (data) => {
  return request.post('/appeals/submit', data)
}

export const getAppealList = (params) => {
  return request.get('/appeals/list', { params })
}

export const getAppealDetail = (violationId) => {
  return request.get(`/appeals/${violationId}`)
}

export const processAppeal = (violationId, data) => {
  return request.put(`/appeals/${violationId}/process`, data)
}

export const getAppealStats = () => {
  return request.get('/appeals/statistics/summary')
}

// ============== 系统管理 ==============
export const getQuota = () => {
  return request.get('/system/quota')
}

export const setKey = (provider, data) => {
  return request.put(`/system/quota/${provider}`, data)
}

export const heartbeat = (provider) => {
  return request.post(`/system/quota/${provider}/heartbeat`)
}

// ============== 模型管理 ==============
export const getModels = () => {
  return request.get('/system/models')
}

export const switchModel = (modelKey) => {
  return request.post('/system/models/switch', { model_key: modelKey })
}

export const unloadModel = (modelKey) => {
  return request.delete(`/system/models/${modelKey}`)
}

export const initModels = () => {
  return request.post('/system/models/init')
}

export const getPerformance = () => {
  return request.get('/system/performance')
}

export const resetPerformance = () => {
  return request.post('/system/performance/reset')
}

// ============== 实时检测 ==============
// 使用直连后端的 realtimeRequest，避免 Vite 代理阻塞问题
export const getRealtimeCameraList = () => {
  return realtimeRequest.get('/realtime/camera/list')
}

export const startRealtimeDetection = (cameraIndex) => {
  return realtimeRequest.post('/realtime/start', { camera_index: cameraIndex })
}

export const stopRealtimeDetection = () => {
  return realtimeRequest.post('/realtime/stop')
}

export const getRealtimeStatus = () => {
  return realtimeRequest.get('/realtime/status')
}

export const forceCloudConsult = () => {
  return realtimeRequest.post('/realtime/consult')
}

// 单帧快照接口（用于前端轮询渲染，兼容所有浏览器）
// Chrome/Edge 对 multipart/x-mixed-replace MJPEG 流支持不完整，
// 改用 snapshot 轮询（每 100ms 请求一帧 base64 JPEG）确保画面正常显示
export const getRealtimeSnapshot = () => {
  return realtimeRequest.get('/realtime/snapshot')
}

export const detectFrame = (frameBase64) => {
  return realtimeRequest.post('/realtime/detect-frame', { frame: frameBase64 })
}

// ============== M07: 规则引擎插件管理 ==============
// 获取所有已加载插件及启用状态
export const getPlugins = () => {
  return realtimeRequest.get('/realtime/plugins')
}

// 启用/禁用单个插件
export const switchPlugin = (scenarioName, enabled) => {
  return realtimeRequest.post('/realtime/plugins/switch', { scenario_name: scenarioName, enabled })
}

// 按预设场景模式批量切换（traffic / urban_management / public_security / all）
export const setSceneMode = (sceneMode) => {
  return realtimeRequest.post('/realtime/plugins/scene-mode', { scene_mode: sceneMode })
}

// 获取可用场景模式列表（供下拉框使用）
export const getSceneModes = () => {
  return realtimeRequest.get('/realtime/plugins/scene-modes')
}

// ============== M09/M10: 软件虚拟追踪 ==============
export const startTracking = (trackId) => {
  return realtimeRequest.post(`/realtime/tracking/start?track_id=${trackId}`)
}

export const stopTracking = () => {
  return realtimeRequest.post('/realtime/tracking/stop')
}

export const getTrackingStatus = () => {
  return realtimeRequest.get('/realtime/tracking/status')
}

// ============== M08: 交通事件中心 ==============
// 事件列表（分页+状态筛选）
export const getEventList = (params) => {
  return realtimeRequest.get('/realtime/events', { params })
}

// 当前活跃事件列表（state 不是 confirmed/rejected）
export const getActiveEvents = () => {
  return realtimeRequest.get('/realtime/events/active')
}

// 事件详情（含完整证据链）
export const getEventDetail = (eventId) => {
  return realtimeRequest.get(`/realtime/events/${encodeURIComponent(eventId)}`)
}

// 事件关键帧列表
export const getEventFrames = (eventId) => {
  return realtimeRequest.get(`/realtime/events/${encodeURIComponent(eventId)}/frames`)
}

// 人工复核事件（confirmed=true 确认违法 / false 排除事件）
export const reviewEvent = (eventId, data) => {
  return realtimeRequest.post(
    `/realtime/events/${encodeURIComponent(eventId)}/review`,
    data
  )
}

// 事件视频可播放 URL（直连后端，<video> 标签 src 直接使用）
export const getEventVideoUrl = (eventId) => {
  return `${BACKEND_DIRECT_URL}/api/realtime/events/${encodeURIComponent(eventId)}/video`
}

// 事件关键帧图片 URL（关键帧路径在服务端 event-videos 静态目录下时可直接拼接）
export const getEventFrameUrl = (framePath) => {
  if (!framePath) return ''
  const normalized = String(framePath).replace(/\\/g, '/')
  // 已经是完整 URL，直接返回
  if (/^https?:\/\//i.test(normalized)) return normalized
  // 绝对路径或带前导斜杠 → 拼到后端根
  const clean = normalized.replace(/^\/+/, '')
  return `${BACKEND_DIRECT_URL}/${clean}`
}

export default request