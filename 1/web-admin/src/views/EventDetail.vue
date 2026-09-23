<template>
  <div class="event-detail" v-if="detail">
    <!-- 顶部摘要横幅 -->
    <el-alert
      :type="bannerType"
      :closable="false"
      show-icon
      class="state-banner"
    >
      <template #title>
        <div class="banner-title">
          <strong>{{ bannerTitle }}</strong>
          <span class="banner-sub">
            · 事件类型：
            <TypeTag :type="detail.event_type" />
            · 车辆 ID：#{{ detail.track_id ?? '-' }}
            · 当前状态：
            <el-tag :type="getStateTagType(detail.state)" size="small" effect="dark">
              {{ getStateLabel(detail.state) }}
            </el-tag>
          </span>
        </div>
      </template>
    </el-alert>

    <el-row :gutter="20">
      <!-- 左侧：事件视频 + 关键帧画廊 -->
      <el-col :span="14">
        <el-card shadow="hover" class="video-card">
          <template #header>
            <div class="card-header">
              <span>
                <el-icon><VideoPlay /></el-icon> 事件视频
              </span>
              <el-button type="primary" link @click="handleOpenVideoInNewTab">
                <el-icon><FullScreen /></el-icon> 新窗口播放
              </el-button>
            </div>
          </template>

          <div class="video-container" v-loading="loadingFrames">
            <video
              v-if="videoUrl"
              :src="videoUrl"
              controls
              autoplay
              loop
              muted
              playsinline
              class="event-video"
              @error="handleVideoError"
            />
            <div v-else class="no-video">
              <el-icon size="48"><VideoCamera /></el-icon>
              <p>事件视频尚未生成</p>
              <p class="video-hint">事件录制完成后将自动生成</p>
            </div>
            <div v-if="videoError" class="video-error">
              <el-icon color="#f56c6c" size="32"><Warning /></el-icon>
              <p>视频加载失败</p>
              <p class="video-hint">{{ videoError }}</p>
            </div>
          </div>

          <!-- 关键帧画廊 -->
          <div class="key-frames-gallery">
            <div class="gallery-header">
              <span>关键帧（{{ keyFrames.length }} 张）</span>
              <el-tag v-if="keyFrames.length > 0" size="small" type="success">
                已加载
              </el-tag>
              <el-tag v-else size="small" type="info">无</el-tag>
            </div>
            <div v-if="keyFrames.length > 0" class="gallery-list">
              <div
                v-for="(frame, index) in keyFrames"
                :key="index"
                class="gallery-item"
              >
                <el-image
                  :src="getFrameDisplayUrl(frame)"
                  fit="cover"
                  class="frame-thumb"
                  :preview-src-list="keyFramePreviewList"
                  :initial-index="index"
                  preview-teleported
                >
                  <template #error>
                    <div class="frame-load-failed">
                      <el-icon><Picture /></el-icon>
                      <span>加载失败</span>
                    </div>
                  </template>
                </el-image>
                <div class="frame-meta">帧 {{ index + 1 }}</div>
                <div class="frame-path" :title="frame">{{ truncatePath(frame) }}</div>
              </div>
            </div>
            <el-empty v-else description="无关键帧" :image-size="80" />
          </div>
        </el-card>

        <!-- 证据链时间线 -->
        <el-card shadow="hover" class="timeline-card">
          <template #header>
            <div class="card-header">
              <span>
                <el-icon><Clock /></el-icon> 证据链时间线
              </span>
            </div>
          </template>

          <el-timeline v-if="evidenceTimeline.length > 0">
            <el-timeline-item
              v-for="(item, index) in evidenceTimeline"
              :key="index"
              :timestamp="item.time"
              :type="item.type"
              :icon="item.icon"
            >
              <div class="timeline-content">
                <span class="timeline-action">{{ item.action }}</span>
                <span v-if="item.description" class="timeline-desc">{{ item.description }}</span>
              </div>
            </el-timeline-item>
          </el-timeline>
          <el-empty v-else description="无状态历史记录" :image-size="80" />
        </el-card>
      </el-col>

      <!-- 右侧：车辆信息 + 场景上下文 + AI 结果 + 人工复核 -->
      <el-col :span="10">
        <el-card shadow="hover" class="info-card">
          <template #header>
            <div class="card-header">
              <span>事件信息</span>
              <el-tag :type="getStateTagType(detail.state)" effect="dark">
                {{ getStateLabel(detail.state) }}
              </el-tag>
            </div>
          </template>

          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="事件 ID" :span="2">
              <span class="event-id-text">{{ detail.event_id }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="事件类型">
              <TypeTag :type="detail.event_type" />
            </el-descriptions-item>
            <el-descriptions-item label="车辆 ID">
              #{{ detail.track_id ?? '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="触发时间">
              {{ formatTriggerTime(detail.trigger_time) }}
            </el-descriptions-item>
            <el-descriptions-item label="创建时间">
              {{ formatTriggerTime(detail.created_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="摄像头">
              {{ detail.camera_id || 'default' }}
            </el-descriptions-item>
            <el-descriptions-item label="AI 置信度">
              <span v-if="typeof detail.ai_confidence === 'number' && detail.ai_confidence > 0">
                {{ (detail.ai_confidence * 100).toFixed(2) }}%
              </span>
              <span v-else>-</span>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <!-- 车辆信息卡片 -->
        <el-card shadow="hover" class="vehicle-card">
          <template #header>
            <div class="card-header">
              <span>
                <el-icon color="#0066CC"><Key /></el-icon> 车辆信息
              </span>
            </div>
          </template>

          <div v-if="hasVehicleInfo" class="vehicle-info">
            <div class="plate-display">
              <span :class="['plate-tag-large', getPlateColorClass(vehicleInfo.plate_color)]">
                {{ vehicleInfo.plate_number || '未识别' }}
              </span>
            </div>
            <el-descriptions :column="2" border size="small" class="vehicle-desc">
              <el-descriptions-item label="车辆类型">
                {{ vehicleInfo.class_name || vehicleInfo.vehicle_type || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="车牌颜色">
                {{ getPlateColorText(vehicleInfo.plate_color) }}
              </el-descriptions-item>
              <el-descriptions-item label="车牌置信度">
                {{ formatConfidence(vehicleInfo.plate_confidence) }}
              </el-descriptions-item>
              <el-descriptions-item label="车辆置信度">
                {{ formatConfidence(vehicleInfo.confidence) }}
              </el-descriptions-item>
              <el-descriptions-item label="Track ID" :span="2">
                #{{ detail.track_id ?? '-' }}
              </el-descriptions-item>
            </el-descriptions>
          </div>
          <el-empty v-else description="无车辆信息" :image-size="60" />
        </el-card>

        <!-- 场景上下文 -->
        <el-card shadow="hover" class="scene-card">
          <template #header>
            <div class="card-header">
              <span>
                <el-icon color="#fa8c16"><Location /></el-icon> 场景上下文
              </span>
            </div>
          </template>

          <div v-if="hasSceneContext">
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="信号灯状态">
                <el-tag
                  v-if="sceneContext.traffic_light_state"
                  :type="getTrafficLightTagType(sceneContext.traffic_light_state)"
                  size="small"
                >
                  {{ getTrafficLightText(sceneContext.traffic_light_state) }}
                </el-tag>
                <span v-else>-</span>
              </el-descriptions-item>
              <el-descriptions-item label="车道 ID">
                {{ sceneContext.lane_id || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="停止线关系" :span="2">
                <el-tag
                  v-if="sceneContext.stop_line_relation"
                  :type="getStopLineTagType(sceneContext.stop_line_relation)"
                  size="small"
                >
                  {{ getStopLineText(sceneContext.stop_line_relation) }}
                </el-tag>
                <span v-else>-</span>
              </el-descriptions-item>
            </el-descriptions>
            <!-- 轨迹折线图（简易） -->
            <div v-if="trajectory.length > 1" class="trajectory-chart">
              <div class="chart-title">车辆轨迹（{{ trajectory.length }} 点）</div>
              <svg :viewBox="`0 0 ${chartWidth} ${chartHeight}`" class="trajectory-svg">
                <polyline
                  :points="trajectoryPoints"
                  fill="none"
                  stroke="#409eff"
                  stroke-width="2"
                />
                <circle
                  v-for="(p, idx) in trajectoryPointsArr"
                  :key="idx"
                  :cx="p.x"
                  :cy="p.y"
                  :r="idx === 0 ? 5 : (idx === trajectoryPointsArr.length - 1 ? 5 : 3)"
                  :fill="idx === 0 ? '#52c41a' : (idx === trajectoryPointsArr.length - 1 ? '#f56c6c' : '#409eff')"
                />
              </svg>
              <div class="chart-legend">
                <span><span class="dot dot-start"></span> 起点</span>
                <span><span class="dot dot-end"></span> 终点</span>
              </div>
            </div>
          </div>
          <el-empty v-else description="无场景上下文" :image-size="60" />
        </el-card>

        <!-- AI 分析结果 -->
        <el-card shadow="hover" class="ai-result-card">
          <template #header>
            <div class="card-header">
              <span>
                <el-icon color="#722ed1"><Cpu /></el-icon> AI 分析结果
              </span>
              <el-tag v-if="aiJudgment" size="small" :type="getAiJudgmentTagType(aiJudgment)">
                {{ getAiJudgmentText(aiJudgment) }}
              </el-tag>
            </div>
          </template>

          <div v-if="detail.ai_explanation" class="ai-explanation">
            <div class="section-label">AI 分析说明：</div>
            <pre class="explanation-text">{{ detail.ai_explanation }}</pre>
          </div>

          <el-collapse v-if="aiTraceData">
            <el-collapse-item name="ai-trace-detail">
              <template #title>
                <span class="collapse-title">查看 ai_trace v3 详情</span>
              </template>
              <div class="ai-trace-content">
                <div v-if="aiTraceData.yolo" class="trace-section">
                  <div class="section-label">🎯 YOLO 本地检测</div>
                  <pre class="trace-json">{{ JSON.stringify(aiTraceData.yolo, null, 2) }}</pre>
                </div>
                <div v-if="aiTraceData.doubao" class="trace-section">
                  <div class="section-label">🔍 豆包视觉模型</div>
                  <pre class="trace-json">{{ JSON.stringify(aiTraceData.doubao, null, 2) }}</pre>
                </div>
                <div v-if="aiTraceData.deepseek" class="trace-section">
                  <div class="section-label">🧠 DeepSeek 逻辑审核</div>
                  <pre class="trace-json">{{ JSON.stringify(aiTraceData.deepseek, null, 2) }}</pre>
                </div>
                <div v-if="aiTraceData.final" class="trace-section">
                  <div class="section-label">✅ 最终裁决</div>
                  <pre class="trace-json">{{ JSON.stringify(aiTraceData.final, null, 2) }}</pre>
                </div>
              </div>
            </el-collapse-item>
          </el-collapse>

          <el-empty
            v-if="!detail.ai_explanation && !aiTraceData"
            description="尚未进行 AI 分析"
            :image-size="60"
          />
        </el-card>

        <!-- 本地规则判断 -->
        <el-card v-if="ruleJudgment" shadow="hover" class="rule-card">
          <template #header>
            <div class="card-header">
              <span>
                <el-icon color="#1890ff"><SetUp /></el-icon> 本地规则判断
              </span>
            </div>
          </template>
          <pre class="rule-json">{{ JSON.stringify(ruleJudgment, null, 2) }}</pre>
        </el-card>

        <!-- 人工复核操作区 -->
        <el-card shadow="hover" class="review-card">
          <template #header>
            <div class="card-header">
              <span>
                <el-icon color="#f56c6c"><EditPen /></el-icon> 人工复核
              </span>
              <el-tag v-if="detail.state === 'confirmed'" type="success" size="small">
                已确认违法
              </el-tag>
              <el-tag v-else-if="detail.state === 'rejected'" type="info" size="small">
                已排除
              </el-tag>
            </div>
          </template>

          <el-form :model="reviewForm" label-width="80px">
            <el-form-item label="复核人">
              <el-input v-model="reviewForm.reviewer" placeholder="如 commander" clearable />
            </el-form-item>
            <el-form-item label="复核意见">
              <el-input
                v-model="reviewForm.comment"
                type="textarea"
                :rows="3"
                placeholder="可填写复核说明（可选）"
              />
            </el-form-item>
            <el-form-item>
              <el-button
                type="success"
                :loading="reviewing"
                :disabled="detail.state === 'confirmed'"
                @click="handleReview(true)"
              >
                <el-icon><Check /></el-icon> 确认违法
              </el-button>
              <el-button
                type="danger"
                :loading="reviewing"
                :disabled="detail.state === 'rejected'"
                @click="handleReview(false)"
              >
                <el-icon><Close /></el-icon> 排除事件
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>
  </div>

  <!-- 加载状态 -->
  <div v-else-if="loading" class="loading">
    <el-icon class="is-loading"><Loading /></el-icon>
    加载中...
  </div>

  <!-- 错误状态 -->
  <div v-else class="error">
    <el-empty description="事件不存在或加载失败" />
    <el-button type="primary" @click="$router.back()">返回列表</el-button>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getEventDetail,
  getEventFrames,
  getEventVideoUrl,
  getEventFrameUrl,
  reviewEvent
} from '../api'
import { formatDate } from '../utils/format'
import TypeTag from '../components/TypeTag.vue'
import {
  VideoPlay,
  VideoCamera,
  FullScreen,
  Warning,
  Clock,
  Key,
  Location,
  Cpu,
  EditPen,
  Check,
  Close,
  Loading,
  Picture,
  SetUp
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const loadingFrames = ref(false)
const reviewing = ref(false)
const detail = ref(null)
const keyFrames = ref([])
const videoError = ref('')

const reviewForm = reactive({
  reviewer: 'commander',
  comment: ''
})

// ==================== 派生数据 ====================

// 视频 URL
const videoUrl = computed(() => {
  if (!detail.value?.event_id) return ''
  return getEventVideoUrl(detail.value.event_id)
})

// 关键帧预览大图列表
const keyFramePreviewList = computed(() => {
  return keyFrames.value.map(f => getEventFrameUrl(f)).filter(Boolean)
})

// 车辆信息（graceful degradation）
const vehicleInfo = computed(() => {
  if (!detail.value?.vehicle_info) return {}
  try {
    return typeof detail.value.vehicle_info === 'string'
      ? JSON.parse(detail.value.vehicle_info)
      : detail.value.vehicle_info
  } catch {
    return {}
  }
})

const hasVehicleInfo = computed(() => Object.keys(vehicleInfo.value).length > 0)

// 场景上下文
const sceneContext = computed(() => {
  if (!detail.value?.scene_context) return {}
  try {
    return typeof detail.value.scene_context === 'string'
      ? JSON.parse(detail.value.scene_context)
      : detail.value.scene_context
  } catch {
    return {}
  }
})

const hasSceneContext = computed(() => Object.keys(sceneContext.value).length > 0)

// 轨迹数据
const trajectory = computed(() => {
  if (!detail.value?.trajectory) return []
  try {
    const t = typeof detail.value.trajectory === 'string'
      ? JSON.parse(detail.value.trajectory)
      : detail.value.trajectory
    return Array.isArray(t) ? t : []
  } catch {
    return []
  }
})

// 轨迹折线图坐标点（自动归一化）
const chartWidth = 300
const chartHeight = 200

const trajectoryPointsArr = computed(() => {
  if (trajectory.value.length < 2) return []
  const pts = trajectory.value.map(p => {
    if (Array.isArray(p)) return { x: p[0], y: p[1] }
    if (typeof p === 'object') return { x: p.x, y: p.y }
    return null
  }).filter(Boolean)
  if (pts.length < 2) return []

  const xs = pts.map(p => Number(p.x)).filter(Number.isFinite)
  const ys = pts.map(p => Number(p.y)).filter(Number.isFinite)
  if (xs.length < 2 || ys.length < 2) return []

  const minX = Math.min(...xs), maxX = Math.max(...xs)
  const minY = Math.min(...ys), maxY = Math.max(...ys)
  const rangeX = maxX - minX || 1
  const rangeY = maxY - minY || 1

  const padding = 20
  return pts.map(p => ({
    x: padding + (Number(p.x) - minX) / rangeX * (chartWidth - 2 * padding),
    y: padding + (Number(p.y) - minY) / rangeY * (chartHeight - 2 * padding)
  }))
})

const trajectoryPoints = computed(() =>
  trajectoryPointsArr.value.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
)

// 本地规则判断
const ruleJudgment = computed(() => {
  if (!detail.value?.rule_judgment) return null
  try {
    return typeof detail.value.rule_judgment === 'string'
      ? JSON.parse(detail.value.rule_judgment)
      : detail.value.rule_judgment
  } catch {
    return null
  }
})

// AI 判断（ai_trace v3）
const aiJudgment = computed(() => {
  if (!detail.value?.ai_judgment) return null
  try {
    return typeof detail.value.ai_judgment === 'string'
      ? JSON.parse(detail.value.ai_judgment)
      : detail.value.ai_judgment
  } catch {
    return null
  }
})

const aiTraceData = computed(() => {
  // 优先使用 ai_judgment 字段，其次尝试 evidence_chain.ai_judgment
  if (aiJudgment.value) return aiJudgment.value
  const evidence = detail.value?.evidence_chain
  if (evidence?.ai_judgment) {
    return evidence.ai_judgment
  }
  return null
})

// 顶部横幅
const bannerTitle = computed(() => {
  switch (detail.value?.state) {
    case 'confirmed': return '✅ 事件已确认为违法'
    case 'rejected': return '✓ 事件已排除'
    case 'manual_review': return '⚠ 需人工复核'
    case 'pending_ai': return '⏳ 等待云端 AI 分析'
    case 'ai_reviewed': return '🎯 AI 分析已完成'
    case 'recording': return '🎥 正在录制事件视频'
    case 'triggered': return '⚡ 已触发疑似事件'
    case 'detecting': return '· 持续检测中'
    default: return '事件详情'
  }
})

const bannerType = computed(() => {
  switch (detail.value?.state) {
    case 'confirmed': return 'success'
    case 'rejected': return 'info'
    case 'manual_review': return 'warning'
    case 'pending_ai': return 'warning'
    case 'ai_reviewed': return 'primary'
    case 'recording':
    case 'triggered':
      return 'warning'
    default: return 'info'
  }
})

// 证据链时间线（从 state_history 构建）
const evidenceTimeline = computed(() => {
  const events = []

  // 1) 解析 state_history
  let history = []
  if (detail.value?.state_history) {
    try {
      history = typeof detail.value.state_history === 'string'
        ? JSON.parse(detail.value.state_history)
        : detail.value.state_history
    } catch {}
  }
  if (!Array.isArray(history)) history = []

  for (const h of history) {
    if (!h || typeof h !== 'object') continue
    events.push({
      time: formatDate(h.timestamp) || '-',
      type: getStateTimelineType(h.new_state),
      action: `状态变更：${getStateLabel(h.old_state)} → ${getStateLabel(h.new_state)}`,
      description: h.reason || ''
    })
  }

  // 2) 如果没有 state_history，至少显示创建/触发
  if (events.length === 0) {
    if (detail.value?.created_at) {
      events.push({
        time: formatDate(detail.value.created_at),
        type: 'primary',
        action: '事件创建',
        description: '系统自动创建事件记录'
      })
    }
    if (detail.value?.trigger_time && formatDate(detail.value.trigger_time) !== formatDate(detail.value.created_at)) {
      events.push({
        time: formatDate(detail.value.trigger_time),
        type: 'warning',
        action: '事件触发',
        description: '规则引擎判定满足触发条件'
      })
    }
  }

  // 3) AI 分析节点
  if (aiJudgment.value) {
    events.push({
      time: '-',
      type: 'primary',
      action: '云端 AI 分析完成',
      description: detail.value.ai_explanation
        ? `说明：${detail.value.ai_explanation.slice(0, 80)}${detail.value.ai_explanation.length > 80 ? '...' : ''}`
        : ''
    })
  }

  // 4) 终态节点
  if (detail.value?.state === 'confirmed') {
    events.push({
      time: '-',
      type: 'success',
      action: '✅ 已确认违法',
      description: ''
    })
  } else if (detail.value?.state === 'rejected') {
    events.push({
      time: '-',
      type: 'info',
      action: '✓ 已排除事件',
      description: ''
    })
  }

  return events
})

// ==================== 状态标签辅助函数 ====================

const stateLabelMap = {
  'detecting': '检测中',
  'triggered': '已触发',
  'recording': '录制中',
  'pending_ai': '待AI分析',
  'ai_reviewed': 'AI已分析',
  'confirmed': '已确认',
  'rejected': '已排除',
  'manual_review': '待人工复核'
}

const stateTagTypeMap = {
  'detecting': 'info',
  'triggered': 'warning',
  'recording': 'warning',
  'pending_ai': 'primary',
  'ai_reviewed': 'primary',
  'confirmed': 'success',
  'rejected': 'info',
  'manual_review': 'danger'
}

function getStateLabel(state) {
  return stateLabelMap[state] || state || '-'
}

function getStateTagType(state) {
  return stateTagTypeMap[state] || 'info'
}

function getStateTimelineType(state) {
  switch (state) {
    case 'confirmed': return 'success'
    case 'rejected': return 'info'
    case 'manual_review': return 'danger'
    case 'pending_ai':
    case 'ai_reviewed': return 'primary'
    case 'triggered':
    case 'recording': return 'warning'
    default: return 'info'
  }
}

// 车牌颜色
function getPlateColorClass(color) {
  const map = {
    'blue': 'plate-blue',
    'green': 'plate-green',
    'yellow': 'plate-yellow',
    'unknown': 'plate-unknown'
  }
  return map[color] || 'plate-unknown'
}

function getPlateColorText(color) {
  const map = {
    'blue': '蓝色车牌',
    'green': '绿色车牌（新能源）',
    'yellow': '黄色车牌',
    'unknown': '未知颜色'
  }
  return map[color] || '未知颜色'
}

function formatConfidence(conf) {
  if (conf === null || conf === undefined || conf === '') return '-'
  const num = Number(conf)
  if (Number.isNaN(num)) return '-'
  // 0~1 转百分比，>1 视为已是百分比
  const percent = num <= 1 ? num * 100 : num
  return percent.toFixed(2) + '%'
}

function formatTriggerTime(t) {
  if (!t) return ''
  return formatDate(t)
}

// 信号灯状态
function getTrafficLightTagType(state) {
  const map = { 'red': 'danger', 'green': 'success', 'yellow': 'warning' }
  return map[state] || 'info'
}

function getTrafficLightText(state) {
  const map = { 'red': '红灯', 'green': '绿灯', 'yellow': '黄灯' }
  return map[state] || state || '-'
}

// 停止线关系
function getStopLineTagType(rel) {
  const map = { 'before': 'success', 'after': 'danger', 'crossing': 'warning' }
  return map[rel] || 'info'
}

function getStopLineText(rel) {
  const map = { 'before': '停止线前', 'after': '已越过停止线', 'crossing': '正在越线' }
  return map[rel] || rel || '-'
}

// AI 判断结果
function getAiJudgmentTagType(ai) {
  const final = ai?.final
  const judg = final?.judgment || final?.decision || ai?.decision
  if (judg === 'confirmed' || judg === '确认违规' || judg === true) return 'danger'
  if (judg === 'rejected' || judg === '未确认违规' || judg === false) return 'success'
  return 'warning' // uncertain
}

function getAiJudgmentText(ai) {
  const final = ai?.final
  const judg = final?.judgment || final?.decision || ai?.decision
  if (judg === 'confirmed' || judg === '确认违规' || judg === true) return 'AI 确认违法'
  if (judg === 'rejected' || judg === '未确认违规' || judg === false) return 'AI 排除'
  if (judg === 'uncertain' || judg === '不确定') return 'AI 不确定'
  return 'AI 已分析'
}

// 关键帧 URL 构造
function getFrameDisplayUrl(frame) {
  // 如果是字符串路径，使用 getEventFrameUrl；如果是对象，尝试取 path 字段
  if (typeof frame === 'string') return getEventFrameUrl(frame)
  if (frame && typeof frame === 'object') {
    return getEventFrameUrl(frame.path || frame.url || frame.image_path || '')
  }
  return ''
}

function truncatePath(path) {
  if (!path) return ''
  const str = typeof path === 'string' ? path : JSON.stringify(path)
  if (str.length <= 40) return str
  return '...' + str.slice(-37)
}

function handleVideoError(e) {
  videoError.value = '视频文件不存在或格式不支持'
  console.warn('[EventDetail] 视频加载失败', e)
}

function handleOpenVideoInNewTab() {
  if (!videoUrl.value) {
    ElMessage.warning('事件视频尚未生成')
    return
  }
  window.open(videoUrl.value, '_blank')
}

// ==================== 生命周期 ====================

onMounted(async () => {
  await loadDetail()
  await loadFrames()
})

async function loadDetail() {
  loading.value = true
  try {
    const eventId = route.params.id
    const res = await getEventDetail(eventId)
    if (res.success === false) {
      ElMessage.error(res.message || '事件详情加载失败')
      detail.value = null
      return
    }
    detail.value = res.data || res
  } catch (err) {
    console.error('[EventDetail] 加载事件详情失败', err)
    ElMessage.error('加载事件详情失败')
    detail.value = null
  } finally {
    loading.value = false
  }
}

async function loadFrames() {
  if (!detail.value?.event_id) return
  loadingFrames.value = true
  try {
    const res = await getEventFrames(detail.value.event_id)
    if (res.success !== false) {
      keyFrames.value = res.key_frames || []
    } else {
      keyFrames.value = []
    }
  } catch (err) {
    console.warn('[EventDetail] 加载关键帧失败', err)
    keyFrames.value = []
  } finally {
    loadingFrames.value = false
  }
}

async function handleReview(confirmed) {
  if (!detail.value?.event_id) return

  const action = confirmed ? '确认违法' : '排除事件'
  try {
    await ElMessageBox.confirm(
      `确定要${action}吗？此操作将更新事件状态。`,
      '人工复核确认',
      {
        confirmButtonText: `确定${action}`,
        cancelButtonText: '取消',
        type: confirmed ? 'warning' : 'info'
      }
    )
  } catch {
    return // 用户取消
  }

  reviewing.value = true
  try {
    const res = await reviewEvent(detail.value.event_id, {
      confirmed,
      reviewer: reviewForm.reviewer || 'commander',
      comment: reviewForm.comment || ''
    })
    if (res.success === false) {
      ElMessage.error(res.message || `复核失败`)
      return
    }
    ElMessage.success(`${action}成功`)
    // 更新本地状态
    detail.value.state = confirmed ? 'confirmed' : 'rejected'
    // 重新加载详情以同步最新数据
    await loadDetail()
  } catch (err) {
    console.error('[EventDetail] 人工复核失败', err)
    ElMessage.error(`复核失败：${err.message || '未知错误'}`)
  } finally {
    reviewing.value = false
  }
}
</script>

<style scoped lang="scss">
.event-detail {
  .state-banner {
    margin-bottom: 20px;

    .banner-title {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .banner-sub {
      font-size: 13px;
      color: #606266;
      display: flex;
      align-items: center;
      gap: 4px;
      flex-wrap: wrap;
    }
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 500;

    span {
      display: flex;
      align-items: center;
      gap: 6px;
    }
  }

  .video-card {
    margin-bottom: 20px;

    .video-container {
      min-height: 320px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #000;
      border-radius: 6px;
      overflow: hidden;
      position: relative;
    }

    .event-video {
      width: 100%;
      max-height: 500px;
      display: block;
    }

    .no-video,
    .video-error {
      color: #999;
      text-align: center;
      padding: 80px 20px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;

      p {
        margin: 4px 0;
      }

      .video-hint {
        font-size: 12px;
        color: #666;
      }
    }
  }

  .key-frames-gallery {
    margin-top: 20px;
    padding-top: 16px;
    border-top: 1px solid #f0f0f0;

    .gallery-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
      font-weight: 500;
    }

    .gallery-list {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
      gap: 12px;
    }

    .gallery-item {
      border: 1px solid #ebeef5;
      border-radius: 6px;
      overflow: hidden;
      background: #fafafa;

      .frame-thumb {
        width: 100%;
        height: 100px;
        display: block;
        cursor: pointer;
      }

      .frame-load-failed {
        width: 100%;
        height: 100px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: #c0c4cc;
        background: #f5f7fa;
        gap: 4px;

        span {
          font-size: 11px;
        }
      }

      .frame-meta {
        padding: 4px 8px;
        font-size: 12px;
        font-weight: 500;
        color: #303133;
        background: #fff;
      }

      .frame-path {
        padding: 2px 8px 6px;
        font-size: 10px;
        color: #909399;
        background: #fff;
        word-break: break-all;
        font-family: 'Consolas', 'Monaco', monospace;
      }
    }
  }

  .timeline-card {
    .timeline-content {
      display: flex;
      flex-direction: column;
      gap: 4px;

      .timeline-action {
        font-weight: 500;
        color: #303133;
        font-size: 14px;
      }

      .timeline-desc {
        font-size: 12px;
        color: #909399;
        line-height: 1.5;
      }
    }
  }

  .info-card,
  .vehicle-card,
  .scene-card,
  .ai-result-card,
  .rule-card,
  .review-card {
    margin-bottom: 20px;
  }

  .event-id-text {
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 12px;
    color: #606266;
    word-break: break-all;
  }

  // 车辆信息卡片
  .vehicle-info {
    .plate-display {
      margin-bottom: 12px;
      text-align: center;
    }

    .plate-tag-large {
      display: inline-block;
      padding: 6px 16px;
      border-radius: 6px;
      font-family: 'Consolas', 'Monaco', monospace;
      font-weight: 700;
      font-size: 18px;
      letter-spacing: 2px;
      min-width: 160px;
      text-align: center;
    }

    .plate-blue {
      background: #0066CC;
      color: #fff;
      border: 2px solid #004499;
    }

    .plate-green {
      background: #009933;
      color: #000;
      border: 2px solid #006622;
    }

    .plate-yellow {
      background: #FFCC00;
      color: #000;
      border: 2px solid #CC9900;
    }

    .plate-unknown {
      background: #f0f0f0;
      color: #606266;
      border: 2px solid #dcdfe6;
    }
  }

  // 轨迹图
  .trajectory-chart {
    margin-top: 16px;
    padding: 12px;
    background: #f5f7fa;
    border-radius: 6px;

    .chart-title {
      font-size: 13px;
      font-weight: 500;
      color: #606266;
      margin-bottom: 8px;
    }

    .trajectory-svg {
      width: 100%;
      height: 200px;
      background: #fff;
      border-radius: 4px;
      border: 1px solid #ebeef5;
    }

    .chart-legend {
      display: flex;
      gap: 16px;
      margin-top: 8px;
      font-size: 12px;
      color: #606266;

      .dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 4px;
      }

      .dot-start { background: #52c41a; }
      .dot-end { background: #f56c6c; }
    }
  }

  // AI 分析结果
  .ai-explanation {
    margin-bottom: 12px;

    .section-label {
      font-size: 13px;
      font-weight: 500;
      color: #606266;
      margin-bottom: 6px;
    }

    .explanation-text {
      margin: 0;
      background: #f8f9fa;
      padding: 12px;
      border-radius: 6px;
      font-size: 13px;
      line-height: 1.7;
      white-space: pre-wrap;
      word-break: break-all;
      color: #333;
      border: 1px solid #ebeef5;
      max-height: 300px;
      overflow-y: auto;
    }
  }

  .ai-trace-content {
    .trace-section {
      margin-bottom: 12px;

      .section-label {
        font-size: 13px;
        font-weight: 500;
        margin-bottom: 6px;
        color: #606266;
      }

      .trace-json {
        margin: 0;
        background: #1e1e1e;
        color: #d4d4d4;
        padding: 10px;
        border-radius: 4px;
        font-family: 'Monaco', 'Menlo', monospace;
        font-size: 11px;
        line-height: 1.5;
        overflow-x: auto;
        max-height: 240px;
        overflow-y: auto;
      }
    }
  }

  .collapse-title {
    font-size: 13px;
    color: #606266;
  }

  // 规则判断 JSON
  .rule-json {
    margin: 0;
    background: #f8f9fa;
    padding: 12px;
    border-radius: 6px;
    font-family: 'Monaco', 'Menlo', monospace;
    font-size: 12px;
    line-height: 1.5;
    overflow-x: auto;
    max-height: 280px;
    overflow-y: auto;
    color: #333;
  }
}

.loading,
.error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 100px 0;
  color: #999;
  gap: 16px;
}

.loading .el-icon {
  font-size: 32px;
}
</style>
