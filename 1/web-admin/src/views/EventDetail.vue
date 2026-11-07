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
              <div class="video-header-actions">
                <el-radio-group v-model="playMode" size="small">
                  <el-radio-button value="original">原始证据</el-radio-button>
                  <el-radio-button value="analysis">分析回放</el-radio-button>
                </el-radio-group>
                <el-button type="primary" link @click="handleOpenVideoInNewTab">
                  <el-icon><FullScreen /></el-icon> 新窗口播放
                </el-button>
              </div>
            </div>
          </template>

          <div class="video-container" ref="videoContainerRef" v-loading="loadingFrames">
            <video
              v-if="videoUrl"
              ref="videoRef"
              :src="videoUrl"
              controls
              autoplay
              loop
              muted
              playsinline
              class="event-video"
              @error="handleVideoError"
              @loadedmetadata="handleVideoMetadata"
              @timeupdate="handleVideoTimeUpdate"
              @seeked="handleVideoTimeUpdate"
            />
            <!-- 分析回放叠加层：
                 1) 新事件（有逐帧 sidecar）：SVG 绘制真实 bbox/track_id（来源：本地 YOLO/Tracking）
                 2) 旧事件（无 sidecar）：诚实降级，仅事件级中文标注，不伪造框 -->
            <div v-if="playMode === 'analysis' && videoUrl && !videoError" class="video-overlay">
              <template v-if="replayReady">
                <svg
                  class="replay-svg"
                  :style="replaySvgStyle"
                  :viewBox="`0 0 ${replayData.video_width} ${replayData.video_height}`"
                >
                  <g
                    v-for="v in currentReplayVehicles"
                    :key="v.track_id"
                    :class="['replay-veh', { selected: selectedVehicleId === v.track_id, dim: selectedVehicleId !== null && selectedVehicleId !== v.track_id }]"
                  >
                    <rect
                      :x="v.bbox[0]"
                      :y="v.bbox[1]"
                      :width="v.bbox[2] - v.bbox[0]"
                      :height="v.bbox[3] - v.bbox[1]"
                    />
                    <text :x="v.bbox[0] + 6" :y="Math.max(v.bbox[1] - 8, 22)" class="replay-label">
                      ID {{ v.track_id }}{{ isEventTrack(v) ? ' · ' + violationCN : '' }}
                    </text>
                  </g>
                </svg>
                <div class="overlay-note">
                  <div>
                    本地 YOLO/Tracking 真实检测框 · 帧 {{ currentFrameIndex + 1 }}/{{ replayData.frame_count }}
                    · 检测状态更新 {{ replayObservationStats.updateCount }}/{{ replayObservationStats.total }} 帧（无插值）
                  </div>
                  <div class="ol-sub">
                    <span :class="['fresh-dot', currentFrameIsNewObservation ? 'fresh' : 'reused']"></span>
                    <template v-if="currentFrameIsNewObservation">本帧为新观测</template>
                    <template v-else>
                      本帧沿用上一观测<template v-if="currentObservedAgeText"> · 观测于 {{ currentObservedAgeText }} 前</template>
                    </template>
                    <template v-if="currentFrameStale"> · 检测已过期</template>
                    <template v-if="currentSourceTimeText"> · 源时间 {{ currentSourceTimeText }}s（仅诊断）</template>
                  </div>
                </div>
              </template>
              <div v-else-if="replayState === 'loading'" class="overlay-note">逐帧回放数据加载中…</div>
              <template v-else>
                <div
                  v-if="selectedVehicle"
                  class="overlay-badge"
                  :style="{ borderLeftColor: getTypeColor(selectedVehicle.eventType) }"
                >
                  ID {{ selectedVehicle.trackId }} · {{ selectedVehicle.violationCN }}
                </div>
                <div class="overlay-note">逐帧检测框数据未采集 · 仅事件级标注</div>
              </template>
            </div>
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

          <!-- TASK-COORD-009B：媒体时间轴诊断（仅分析回放且有 sidecar 时出现） -->
          <el-alert
            v-if="playMode === 'analysis' && replayReady && timelineMismatch"
            type="error"
            :closable="false"
            show-icon
            class="timeline-alert"
            title="媒体时间异常：视频时长与检测数据时间跨度偏差超过 10%"
            :description="`视频实际时长 ${timelineMismatch.media.toFixed(2)}s，sidecar 播放时间跨度 ${timelineMismatch.sidecar.toFixed(2)}s，偏差 ${(timelineMismatch.ratio * 100).toFixed(1)}%。检测框仍按 sidecar 媒体时间取帧，未做静默归一化；请核对后端录制/采集帧率链路。`"
          />
          <el-alert
            v-if="playMode === 'analysis' && replayReady && sourceTimelineInfo"
            type="warning"
            :closable="false"
            show-icon
            class="timeline-alert"
            title="源时间与媒体时间不一致：回放存在慢放/快放"
            :description="`检测数据源时间跨度 ${sourceTimelineInfo.source.toFixed(2)}s，媒体时长 ${sourceTimelineInfo.media.toFixed(2)}s，回放倍率约 ${sourceTimelineInfo.slowmo.toFixed(2)}×${sourceTimelineInfo.sourceFps ? `（源帧率 ${sourceTimelineInfo.sourceFps} fps）` : ''}。源时间仅作诊断，不参与取帧。`"
          />

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

      <!-- 右侧：车辆信息面板 + 事件信息 + 场景上下文 + AI 判定与人工复核 -->
      <el-col :span="10">
        <!-- 车辆信息面板（点击选中后与视频叠加层联动高亮；事件级数据，无逐帧框） -->
        <el-card shadow="hover" class="vehicle-card">
          <template #header>
            <div class="card-header">
              <span>
                <el-icon color="#0066CC"><Key /></el-icon> 车辆信息
              </span>
              <el-tag v-if="selectedVehicle" size="small" type="success" effect="dark">
                已选中 ID {{ selectedVehicle.trackId }}
              </el-tag>
            </div>
          </template>

          <!-- 逐帧回放：当前帧车辆列表（随播放更新；数据来自本地 YOLO/Tracking sidecar） -->
          <div v-if="replayReady" class="frame-vehicle-list">
            <div class="fvl-title">
              当前帧车辆（{{ currentReplayVehicles.length }}）· 随播放更新
            </div>
            <div class="fvl-fresh" title="全片中检测状态相对上一帧真实发生变化的帧数；沿用最近推理结果的帧不计为新观测">
              检测状态更新 {{ replayObservationStats.updateCount }}/{{ replayObservationStats.total }} 帧
              <span class="fvl-fresh-sub">
                （{{ isTimeBasedFrameIndex ? '按 sidecar time 最近邻取帧' : '旧 sidecar：按 index/fps 取帧' }}，无插值）
              </span>
            </div>
            <div class="fvl-fresh">
              <span v-if="currentFrameIsNewObservation" class="fresh-tag new">本帧为新观测</span>
              <span v-else class="fresh-tag reused">
                本帧沿用上一观测<template v-if="currentObservedAgeText"> · 观测于 {{ currentObservedAgeText }} 前</template>
              </span>
              <span v-if="currentFrameStale" class="fresh-tag stale">检测已过期</span>
            </div>
            <div v-if="currentSourceTimeText" class="fvl-fresh fvl-time-diag">
              源时间 {{ currentSourceTimeText }}s · 媒体时间 {{ currentMediaTime.toFixed(2) }}s（源时间仅诊断，取帧用媒体时间）
            </div>
            <div v-if="currentReplayVehicles.length === 0" class="fvl-empty">当前帧未检测到车辆</div>
            <div
              v-for="v in currentReplayVehicles"
              :key="v.track_id"
              :class="['fvl-item', { selected: selectedVehicleId === v.track_id }]"
              @click="handleSelectVehicle(v.track_id)"
            >
              <span class="fvl-id">ID {{ v.track_id }}</span>
              <span class="fvl-class">{{ CLASS_CN[v.class_name] || v.class_name || '未知' }}</span>
              <span class="fvl-speed">{{ formatPxSpeed(v.speed_px) }}</span>
              <span class="fvl-dir">{{ DIRECTION_CN[v.direction] || v.direction || '-' }}</span>
              <el-tag v-if="isEventTrack(v)" size="small" type="danger" effect="dark">本事件</el-tag>
            </div>
            <div class="fvl-note">速度为像素速度（px/s，非 km/h）；云端 AI 结论见下方判定区</div>
          </div>

          <div v-if="eventVehicle" class="vehicle-panel">
            <div
              :class="['vehicle-item', { selected: selectedVehicle }]"
              @click="handleSelectVehicle(eventVehicle.trackId)"
            >
              <div class="vehicle-item-head">
                <span class="vehicle-id">ID {{ eventVehicle.trackId }}</span>
                <TypeTag :type="eventVehicle.eventType" />
              </div>
              <div class="vehicle-fields">
                <div class="vehicle-field">
                  <span class="vf-label">类型</span>
                  <span class="vf-value">{{ eventVehicle.classCN }}</span>
                </div>
                <div class="vehicle-field">
                  <span class="vf-label">速度</span>
                  <span class="vf-value">{{ eventVehicle.speedText }}</span>
                </div>
                <div class="vehicle-field">
                  <span class="vf-label">车牌</span>
                  <span class="vf-value">{{ eventVehicle.plate }}</span>
                </div>
                <div class="vehicle-field">
                  <span class="vf-label">方向</span>
                  <span class="vf-value">{{ eventVehicle.directionCN }}</span>
                </div>
                <div class="vehicle-field">
                  <span class="vf-label">违规</span>
                  <span class="vf-value">{{ eventVehicle.violationCN }}</span>
                </div>
                <div class="vehicle-field">
                  <span class="vf-label">置信度</span>
                  <span class="vf-value">{{ eventVehicle.confidenceText }}</span>
                </div>
                <div class="vehicle-field">
                  <span class="vf-label">状态</span>
                  <span class="vf-value">
                    <el-tag :type="getStateTagType(detail.state)" size="small" effect="dark">
                      {{ getStateLabel(detail.state) }}
                    </el-tag>
                  </span>
                </div>
              </div>
              <div class="vehicle-speed-note">像素速度（非 km/h，仅供排查）：{{ pixelSpeedText }}</div>
            </div>
          </div>
          <el-empty v-else description="无车辆信息" :image-size="60" />
        </el-card>

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
              {{ aiConfidenceText }}
            </el-descriptions-item>
          </el-descriptions>
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

        <!-- AI 判定与人工复核状态（单独分区显示） -->
        <el-card shadow="hover" class="ai-result-card">
          <template #header>
            <div class="card-header">
              <span>
                <el-icon color="#722ed1"><Cpu /></el-icon> AI 判定与人工复核
              </span>
              <el-tag v-if="hasAiTrace" size="small" :type="getAiJudgmentTagType(aiTraceData)">
                {{ aiVerdictText }}
              </el-tag>
              <el-tag v-else size="small" type="warning">待 AI 分析</el-tag>
            </div>
          </template>

          <!-- 状态摘要：AI 判定 / AI 置信度 / 人工复核状态 -->
          <div class="ai-status-grid">
            <div class="ai-status-item">
              <span class="as-label">AI 判定</span>
              <span class="as-value">{{ aiVerdictText }}</span>
            </div>
            <div class="ai-status-item">
              <span class="as-label">AI 置信度</span>
              <span class="as-value">{{ aiConfidenceText }}</span>
            </div>
            <div class="ai-status-item">
              <span class="as-label">人工复核状态</span>
              <span class="as-value">
                <el-tag :type="getStateTagType(detail.state)" size="small" effect="dark">
                  {{ getStateLabel(detail.state) }}
                </el-tag>
              </span>
            </div>
          </div>

          <div v-if="detail.ai_explanation" class="ai-explanation">
            <div class="section-label">AI 分析说明：</div>
            <pre class="explanation-text">{{ detail.ai_explanation }}</pre>
          </div>

          <el-collapse v-if="hasAiTrace">
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
            v-if="!detail.ai_explanation && !hasAiTrace"
            description="待 AI 分析"
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
import { ref, reactive, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getEventDetail,
  getEventFrames,
  getEventReplay,
  getEventVideoUrl,
  getEventFrameUrl,
  reviewEvent
} from '../api'
import { formatDate, getTypeName, getTypeColor } from '../utils/format'
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

// 内联中文映射（车辆类型 / 方向 / 违规兜底），避免修改 utils/format.js
const CLASS_CN = {
  car: '轿车',
  motorcycle: '摩托车',
  truck: '卡车',
  bus: '公交车',
  bicycle: '自行车',
  person: '行人',
  unknown: '未知'
}
const DIRECTION_CN = {
  right: '向右',
  left: '向左',
  up: '向上',
  down: '向下',
  unknown: '未知'
}
// 违规类型中文名已统一到 utils/format.js 的 TYPE_MAP（2026-10-23 由 DSH 删除本地映射补丁）
// 历史教训：这里曾用 4 条局部映射掩盖 format.js 缺 5 类的根因，导致其他页面仍漏英文

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const loadingFrames = ref(false)
const reviewing = ref(false)
const detail = ref(null)
const keyFrames = ref([])
const videoError = ref('')

// 视频回放模式：original=原始证据 / analysis=分析回放（有 sidecar 显示真实逐帧框，否则事件级降级）
const playMode = ref('original')
// 当前选中的车辆 ID（事件级与逐帧回放共用；多车辆时扩展为列表）
const selectedVehicleId = ref(null)

// ==================== TASK-COORD-007：逐帧回放（真实检测框） ====================
const videoRef = ref(null)
const videoContainerRef = ref(null)
// replayState: none=未加载 / loading / ready / unavailable（旧事件无 sidecar，诚实降级）
const replayState = ref('none')
const replayData = ref(null)
const currentFrameIndex = ref(-1)
// 视频内容在容器中的实际显示矩形（处理 object-fit: contain 的 letterbox 偏移）
const videoRect = reactive({ left: 0, top: 0, width: 0, height: 0 })
let replayRafId = 0

const replayReady = computed(() => replayState.value === 'ready' && !!replayData.value)

// 当前帧车辆（过滤无有效 bbox 的条目；不补造任何数据）
const currentReplayVehicles = computed(() => {
  if (!replayReady.value) return []
  const frames = replayData.value.frames || []
  if (!frames.length) return []
  const idx = Math.min(Math.max(currentFrameIndex.value, 0), frames.length - 1)
  const list = (frames[idx] && frames[idx].vehicles) || []
  return list.filter(v => v && Array.isArray(v.bbox) && v.bbox.length === 4
    && v.bbox.every(n => Number.isFinite(Number(n))))
})

// SVG 定位：精确覆盖视频内容区域（剔除 letterbox 黑边）
const replaySvgStyle = computed(() => ({
  left: `${videoRect.left}px`,
  top: `${videoRect.top}px`,
  width: `${videoRect.width}px`,
  height: `${videoRect.height}px`
}))

// ==================== TASK-COORD-009B：时间轴选帧 / 观测新鲜度 / 媒体时间诊断 ====================
// 播放器报告的真实媒体时长（loadedmetadata）；未就绪为 null
const mediaDuration = ref(null)
// 最近一次同步用的播放器媒体时间（供界面诊断文本响应式展示）
const currentMediaTime = ref(0)

// sidecar 帧是否携带可用于选帧的媒体时间轴 frames[].time
// （v1/v2 均有；旧 sidecar 缺该字段时为 null → 回退 round(t*fps)）
const replayFrameTimes = computed(() => {
  if (!replayReady.value) return null
  const frames = replayData.value.frames || []
  if (!frames.length) return null
  const times = []
  for (const f of frames) {
    const t = f && f.time
    if (typeof t !== 'number' || !Number.isFinite(t)) return null
    times.push(t)
  }
  return times
})

const isTimeBasedFrameIndex = computed(() => replayFrameTimes.value !== null)

// 单帧检测状态签名：排序后的 (track_id, 整数化 bbox) 集合
// 口径与 008A/008B 审计一致；仅用于判断“真实观测是否变化”，不做任何插值/补造
function frameStateSignature(frame) {
  const veh = (frame && Array.isArray(frame.vehicles)) ? frame.vehicles : []
  const parts = []
  for (const v of veh) {
    if (!v || !Array.isArray(v.bbox) || v.bbox.length !== 4) continue
    const box = v.bbox.map(n => Math.round(Number(n)))
    if (box.some(n => !Number.isFinite(n))) continue
    parts.push(`${v.track_id ?? ''}@${box.join(',')}`)
  }
  parts.sort()
  return parts.join('|')
}

// 全片观测新鲜度统计：updateCount = 相对上一帧出现新检测状态的帧数（首帧计 1 次）
// 沿用最近一次推理结果的帧不计为新观测，避免把静态框伪装成逐帧新检测
const replayObservationStats = computed(() => {
  if (!replayReady.value) return { updateCount: 0, runCount: 0, total: 0, flags: [] }
  const frames = replayData.value.frames || []
  const flags = new Array(frames.length).fill(false)
  let prevSig = null
  let updateCount = 0
  frames.forEach((f, i) => {
    const sig = frameStateSignature(f)
    if (i === 0 || sig !== prevSig) {
      flags[i] = true
      updateCount += 1
    }
    prevSig = sig
  })
  return { updateCount, runCount: updateCount, total: frames.length, flags }
})

const currentReplayFrame = computed(() => {
  if (!replayReady.value) return null
  const frames = replayData.value.frames || []
  if (!frames.length) return null
  const idx = Math.min(Math.max(currentFrameIndex.value, 0), frames.length - 1)
  return frames[idx] || null
})

const currentFrameIsNewObservation = computed(() => {
  const stats = replayObservationStats.value
  const idx = currentFrameIndex.value
  if (idx < 0 || idx >= stats.flags.length) return null
  return stats.flags[idx]
})

// 本帧检测结果的真实观测年龄（秒，v2 sidecar 字段；缺失为 null，不猜测）
const currentObservedAgeText = computed(() => {
  const f = currentReplayFrame.value
  const age = f && f.observed_age_sec
  if (typeof age !== 'number' || !Number.isFinite(age) || age < 0) return ''
  return age >= 1 ? `${age.toFixed(2)}s` : `${Math.round(age * 1000)}ms`
})

const currentFrameStale = computed(() => currentReplayFrame.value?.stale === true)

// 源媒体时间仅作诊断展示，绝不替代播放器 currentTime 参与选帧
const currentSourceTimeText = computed(() => {
  const t = currentReplayFrame.value?.source_time
  return (typeof t === 'number' && Number.isFinite(t)) ? t.toFixed(2) : ''
})

// sidecar 声明的播放时间跨度：优先 v2 顶层 media_duration_sec，否则 frame_count/fps
const sidecarMediaDuration = computed(() => {
  if (!replayReady.value) return null
  const d = replayData.value
  if (typeof d.media_duration_sec === 'number' && Number.isFinite(d.media_duration_sec) && d.media_duration_sec > 0) {
    return d.media_duration_sec
  }
  const frames = d.frames || []
  const fps = Number(d.fps)
  if (frames.length > 0 && fps > 0) return frames.length / fps
  return null
})

// 媒体时长（播放器实测）vs sidecar 播放时间跨度；偏差 >10% 明确报警，不做静默归一化
const timelineMismatch = computed(() => {
  const m = mediaDuration.value
  const s = sidecarMediaDuration.value
  if (m === null || s === null || m <= 0 || s <= 0) return null
  const ratio = Math.abs(m - s) / Math.max(m, s)
  if (ratio <= 0.10) return null
  return { media: m, sidecar: s, ratio }
})

// 源时间跨度 vs 媒体时长（v2 才有）：用于揭示慢放/快放，纯诊断
const sourceTimelineInfo = computed(() => {
  if (!replayReady.value) return null
  const d = replayData.value
  const src = (typeof d.source_duration_sec === 'number' && Number.isFinite(d.source_duration_sec))
    ? d.source_duration_sec : null
  const media = sidecarMediaDuration.value
  if (src === null || media === null || src <= 0 || media <= 0) return null
  const ratio = Math.abs(media - src) / Math.max(media, src)
  if (ratio <= 0.10) return null
  return {
    source: src,
    media,
    slowmo: media / src,
    sourceFps: (typeof d.source_fps === 'number' && Number.isFinite(d.source_fps)) ? d.source_fps : null
  }
})

function isEventTrack(v) {
  return detail.value && v.track_id != null
    && Number(v.track_id) === Number(detail.value.track_id)
}

function formatPxSpeed(s) {
  return typeof s === 'number' && Number.isFinite(s) ? `${s.toFixed(1)} px/s` : '未采集'
}

// 计算视频内容矩形：video 元素盒尺寸 vs intrinsic 尺寸，按 contain 缩放并居中
function updateVideoRect() {
  const v = videoRef.value
  if (!v || !v.videoWidth || !v.videoHeight) return
  const ew = v.clientWidth || 0
  const eh = v.clientHeight || 0
  if (!ew || !eh) return
  const scale = Math.min(ew / v.videoWidth, eh / v.videoHeight)
  const dw = v.videoWidth * scale
  const dh = v.videoHeight * scale
  // video 的 offsetParent 是 .video-container（position: relative）
  videoRect.left = (v.offsetLeft || 0) + (ew - dw) / 2
  videoRect.top = (v.offsetTop || 0) + (eh - dh) / 2
  videoRect.width = dw
  videoRect.height = dh
}

// 由播放时间选择 sidecar 帧：
// - 优先按 frames[].time 取最近邻（非均匀间隔也正确；time 单调非减，二分查找）
// - 旧 sidecar 无 time 字段时回退 round(currentTime*fps)
// 仅选择真实存在的帧，不做 bbox/状态插值
function selectFrameIndexByTime(currentTime) {
  const frames = replayData.value.frames || []
  if (!frames.length) return -1
  const times = replayFrameTimes.value
  let idx
  if (times) {
    const t = Number(currentTime) || 0
    if (t <= times[0]) {
      idx = 0
    } else if (t >= times[times.length - 1]) {
      idx = times.length - 1
    } else {
      let lo = 0
      let hi = times.length - 1
      while (lo < hi) {
        const mid = (lo + hi) >> 1
        if (times[mid] < t) lo = mid + 1
        else hi = mid
      }
      // lo = 第一个 time >= t；在 lo-1 / lo 中取更近者；
      // 等距时取后一帧（与均匀轴旧实现 round(t*fps) 的半程取整行为一致）
      idx = (lo > 0 && Math.abs(times[lo - 1] - t) < Math.abs(times[lo] - t)) ? lo - 1 : lo
    }
  } else {
    const fps = Number(replayData.value.fps) || 10
    idx = Math.round((Number(currentTime) || 0) * fps)
  }
  return Math.min(Math.max(idx, 0), frames.length - 1)
}

function syncReplayFrame(currentTime) {
  if (!replayReady.value) return
  currentMediaTime.value = Number(currentTime) || 0
  currentFrameIndex.value = selectFrameIndexByTime(currentTime)
}

function handleVideoMetadata(e) {
  const v = e?.target || videoRef.value
  if (v && Number.isFinite(Number(v.duration)) && Number(v.duration) > 0) {
    mediaDuration.value = Number(v.duration)
  }
  updateVideoRect()
  if (videoRef.value) syncReplayFrame(videoRef.value.currentTime)
}

function handleVideoTimeUpdate() {
  updateVideoRect()
  if (videoRef.value) syncReplayFrame(videoRef.value.currentTime)
}

// 播放中用 rAF 提升框随帧刷新的流畅度（timeupdate 仅约 4Hz，低于视频 10fps）
function tickReplayLoop() {
  if (replayReady.value && playMode.value === 'analysis' && videoRef.value) {
    syncReplayFrame(videoRef.value.currentTime)
  }
  replayRafId = requestAnimationFrame(tickReplayLoop)
}

async function loadReplay() {
  if (!detail.value?.event_id) return
  replayState.value = 'loading'
  try {
    const res = await getEventReplay(detail.value.event_id)
    if (res && res.success && res.data && Array.isArray(res.data.frames) && res.data.frames.length > 0) {
      replayData.value = res.data
      replayState.value = 'ready'
    } else {
      replayData.value = null
      replayState.value = 'unavailable'
    }
  } catch (err) {
    console.warn('[EventDetail] 逐帧回放数据加载失败', err)
    replayData.value = null
    replayState.value = 'unavailable'
  }
}

watch(playMode, mode => {
  if (mode === 'analysis') {
    nextTick(() => {
      updateVideoRect()
      if (videoRef.value) syncReplayFrame(videoRef.value.currentTime)
    })
  }
})

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

// ==================== 分析回放：车辆信息面板（事件级） ====================

// 违规中文名：统一走 utils/format.js 的 TYPE_MAP，未登记由 getTypeName 兜成「未知类型」
const violationCN = computed(() => {
  const t = detail.value?.event_type || ''
  return getTypeName(t)
})

// 车辆类型中文
const vehicleClassCN = computed(() => {
  const c = vehicleInfo.value.class_name || vehicleInfo.value.vehicle_type || 'unknown'
  return CLASS_CN[c] || c
})

// 行驶方向中文
const directionCN = computed(() => {
  const d = vehicleInfo.value.direction || 'unknown'
  return DIRECTION_CN[d] || d
})

// 权威车速（km/h）：rule_judgment.evidence.real_speed_kmh；无则显示未采集，绝不把 px/s 当 km/h
const realSpeedKmh = computed(() => {
  const v = ruleJudgment.value?.evidence?.real_speed_kmh
  return typeof v === 'number' && Number.isFinite(v) ? v : null
})

const realSpeedText = computed(() => {
  return realSpeedKmh.value !== null ? `${realSpeedKmh.value.toFixed(1)} km/h` : '未采集'
})

// 像素速度（px/s，仅作参考展示并明确标注单位）
const pixelSpeedText = computed(() => {
  const v = vehicleInfo.value.speed
  return typeof v === 'number' && Number.isFinite(v) ? `${v.toFixed(1)} px/s` : '未采集'
})

// 车牌：7/7 事件为空，显示未识别；plate_color/plate_confidence 键不存在，显示未采集
const plateText = computed(() => vehicleInfo.value.plate_number || '未识别')

// 规则置信度（rule_judgment.confidence，0~1）
const ruleConfidenceText = computed(() => {
  const c = ruleJudgment.value?.confidence
  return typeof c === 'number' && Number.isFinite(c) ? `${(c * 100).toFixed(0)}%` : '未采集'
})

// 事件车辆（当前数据模型为单车辆；selectedVehicle 供叠加层与面板高亮共用）
const eventVehicle = computed(() => {
  if (!hasVehicleInfo.value && detail.value?.track_id == null) return null
  return {
    trackId: detail.value?.track_id ?? vehicleInfo.value.track_id ?? '-',
    classCN: vehicleClassCN.value,
    speedText: realSpeedText.value,
    plate: plateText.value,
    violationCN: violationCN.value,
    confidenceText: ruleConfidenceText.value,
    directionCN: directionCN.value,
    eventType: detail.value?.event_type || ''
  }
})

const selectedVehicle = computed(() => {
  if (!eventVehicle.value) return null
  if (selectedVehicleId.value === null) return eventVehicle.value
  return selectedVehicleId.value === eventVehicle.value.trackId ? eventVehicle.value : null
})

// 点击车辆：事件级选中（无逐帧数据，不绘制框，仅面板/叠加层高亮）
function handleSelectVehicle(trackId) {
  selectedVehicleId.value = trackId
}

// AI 判断（ai_trace v3）；空对象 {} 视为无数据（既有事件 ai_judgment 均为 {}）
const aiJudgment = computed(() => {
  const raw = detail.value?.ai_judgment
  if (!raw) return null
  try {
    const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw
    if (parsed && typeof parsed === 'object' && Object.keys(parsed).length === 0) return null
    return parsed
  } catch {
    return null
  }
})

const aiTraceData = computed(() => {
  // 优先使用 ai_judgment 字段，其次尝试 evidence_chain.ai_judgment
  if (aiJudgment.value) return aiJudgment.value
  const aj = detail.value?.evidence_chain?.ai_judgment
  if (aj && typeof aj === 'object' && Object.keys(aj).length > 0) return aj
  return null
})

const hasAiTrace = computed(() => !!aiTraceData.value)

// AI 判定结论文字（待 AI 分析 / AI 确认违法 / AI 排除 / AI 不确定 / AI 已分析）
const aiVerdictText = computed(() => {
  if (!aiTraceData.value) return '待 AI 分析'
  return getAiJudgmentText(aiTraceData.value)
})

// AI 置信度：缺失或 <=0 时显示 待 AI 分析（避免把 0 显示成 0.00%）
const aiConfidenceText = computed(() => {
  const c = detail.value?.ai_confidence
  return typeof c === 'number' && Number.isFinite(c) && c > 0
    ? formatConfidence(c)
    : '待 AI 分析'
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
  await loadReplay()
  window.addEventListener('resize', updateVideoRect)
  replayRafId = requestAnimationFrame(tickReplayLoop)
})

onUnmounted(() => {
  if (replayRafId) cancelAnimationFrame(replayRafId)
  window.removeEventListener('resize', updateVideoRect)
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

    // 分析回放叠加层（事件级中文标注，pointer-events 不拦截视频控制）
    .video-overlay {
      position: absolute;
      inset: 0;
      pointer-events: none;
      z-index: 2;

      .overlay-badge {
        position: absolute;
        top: 12px;
        left: 12px;
        padding: 4px 12px;
        background: rgba(0, 0, 0, 0.62);
        color: #fff;
        font-size: 14px;
        font-weight: 600;
        border-radius: 4px;
        border-left: 4px solid #409eff;
        letter-spacing: 1px;
      }

      .overlay-note {
        position: absolute;
        bottom: 12px;
        left: 12px;
        max-width: calc(100% - 24px);
        padding: 4px 10px;
        background: rgba(0, 0, 0, 0.55);
        color: #e6e6e6;
        font-size: 12px;
        line-height: 1.5;
        border-radius: 4px;

        .ol-sub {
          font-size: 11px;
          opacity: 0.9;
        }

        .fresh-dot {
          display: inline-block;
          width: 7px;
          height: 7px;
          border-radius: 50%;
          margin-right: 4px;

          &.fresh {
            background: #52d681;
            box-shadow: 0 0 4px rgba(82, 214, 129, 0.8);
          }

          &.reused {
            background: #a8abb2;
          }
        }
      }

      // 逐帧回放 SVG 叠加层（真实检测框，TASK-COORD-007）
      .replay-svg {
        position: absolute;
        pointer-events: none;
        overflow: visible;

        .replay-veh {
          rect {
            fill: none;
            stroke: #00e5ff;
            stroke-width: 2.5;
            vector-effect: non-scaling-stroke;
          }

          .replay-label {
            fill: #ffffff;
            font-size: 17px;
            font-weight: 700;
            font-family: 'Microsoft YaHei', 'Consolas', sans-serif;
            paint-order: stroke;
            stroke: rgba(0, 0, 0, 0.78);
            stroke-width: 4px;
          }

          &.selected {
            rect {
              stroke: #ff4d4f;
              stroke-width: 4;
            }

            .replay-label {
              fill: #ffd666;
            }
          }

          &.dim {
            rect {
              stroke: rgba(0, 229, 255, 0.35);
            }

            .replay-label {
              opacity: 0.55;
            }
          }
        }
      }
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

  .timeline-alert {
    margin-top: 12px;
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

  // 车辆信息面板（分析回放联动）
  // 逐帧回放：当前帧车辆列表（随播放更新）
  .frame-vehicle-list {
    margin-bottom: 12px;
    padding: 10px 12px;
    background: #f8fbff;
    border: 1px solid #d6e8ff;
    border-radius: 8px;

    .fvl-title {
      font-size: 13px;
      font-weight: 600;
      color: #1d39c4;
      margin-bottom: 8px;
    }

    .fvl-fresh {
      font-size: 12px;
      color: #303133;
      margin-bottom: 6px;
      line-height: 1.5;

      .fvl-fresh-sub {
        color: #909399;
        font-size: 11px;
      }

      .fresh-tag {
        display: inline-block;
        padding: 1px 8px;
        border-radius: 10px;
        font-size: 11px;
        line-height: 1.6;

        &.new {
          background: #e7f8ef;
          color: #15a059;
          border: 1px solid #a8e3c0;
        }

        &.reused {
          background: #f4f4f5;
          color: #606266;
          border: 1px solid #dcdfe6;
        }

        &.stale {
          margin-left: 6px;
          background: #fef0f0;
          color: #c45656;
          border: 1px solid #fbc4c4;
        }
      }

      &.fvl-time-diag {
        color: #909399;
        font-size: 11px;
      }
    }

    .fvl-empty {
      font-size: 12px;
      color: #909399;
      padding: 6px 0;
    }

    .fvl-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 6px 8px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 13px;
      color: #303133;
      transition: background 0.15s;

      &:hover {
        background: #e8f3ff;
      }

      &.selected {
        background: #ecf5ff;
        outline: 1.5px solid #409eff;
      }

      .fvl-id {
        font-weight: 700;
      }

      .fvl-class,
      .fvl-speed,
      .fvl-dir {
        color: #606266;
      }
    }

    .fvl-note {
      margin-top: 8px;
      font-size: 11px;
      color: #909399;
    }
  }

  .vehicle-panel {
    .vehicle-item {
      border: 2px solid #ebeef5;
      border-radius: 8px;
      padding: 10px 12px;
      cursor: pointer;
      transition: border-color 0.2s, background 0.2s, box-shadow 0.2s;

      &:hover {
        border-color: #c6e2ff;
      }

      &.selected {
        border-color: #409eff;
        background: #ecf5ff;
        box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.15);
      }

      .vehicle-item-head {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;

        .vehicle-id {
          font-weight: 700;
          font-size: 15px;
          color: #303133;
        }
      }

      .vehicle-fields {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 6px 12px;

        .vehicle-field {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 13px;

          .vf-label {
            color: #909399;
            flex-shrink: 0;
          }

          .vf-value {
            color: #303133;
            font-weight: 500;
            word-break: break-all;
          }
        }
      }

      .vehicle-speed-note {
        margin-top: 8px;
        font-size: 11px;
        color: #909399;
      }
    }
  }

  // AI 判定与人工复核状态摘要
  .ai-status-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
    margin-bottom: 12px;

    .ai-status-item {
      display: flex;
      flex-direction: column;
      gap: 6px;
      padding: 8px 10px;
      background: #f8f9fa;
      border: 1px solid #ebeef5;
      border-radius: 6px;

      .as-label {
        font-size: 12px;
        color: #909399;
      }

      .as-value {
        font-size: 14px;
        font-weight: 600;
        color: #303133;
      }
    }
  }

  .video-header-actions {
    display: flex;
    align-items: center;
    gap: 12px;
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
