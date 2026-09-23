<template>
  <div class="violation-detail" v-if="detail">
    <!-- AI 决策摘要横幅（仅 v3 版本显示） -->
    <div v-if="processedData?.showBanner" class="ai-summary-banner">
      <!-- 样式 A：双模型一致 -->
      <el-alert
        v-if="processedData.ruleUsed === 'both_agree'"
        type="success"
        :closable="false"
        show-icon
      >
        <template #title>
          <div class="summary-title">
            <strong>✅ AI 一致判断：{{ processedData.final?.decision || '—' }}</strong>
          </div>
          <div class="summary-content">
            <div class="content-grid">
              <div class="grid-item">
                <span class="label">豆包视觉模型</span>
                <span class="value">置信度 {{ processedData.final?.doubao_confidence || '—' }}%</span>
              </div>
              <div class="grid-item" v-if="processedData.final?.deepseek_confidence">
                <span class="label">DeepSeek 逻辑审核</span>
                <span class="value">置信度 {{ processedData.final?.deepseek_confidence }}%</span>
              </div>
            </div>
            <div class="final-confidence">
              <strong>系统最终置信度：{{ processedData.final?.final_confidence || '—' }}%</strong>
            </div>
          </div>
        </template>
      </el-alert>

      <!-- 样式 B：双模型不一致 -->
      <el-alert
        v-else-if="processedData.ruleUsed === 'disagreement_pending'"
        type="warning"
        :closable="false"
        show-icon
        class="inconsistent-alert"
      >
        <template #title>
          <div class="summary-title inconsistent-title">
            <strong>⚠️ 双模型意见不一致，建议人工复核</strong>
          </div>
          <div class="summary-content">
            <div class="model-comparison">
              <div class="model-item">
                <span class="model-label">豆包判断：</span>
                <el-tag size="small" type="success">{{ processedData.doubao?.decision || '—' }}</el-tag>
                <span class="confidence">置信度 {{ processedData.doubao?.confidence || '—' }}%</span>
              </div>
              <div class="model-item" v-if="processedData.deepseek">
                <span class="model-label">DeepSeek 判断：</span>
                <el-tag size="small" type="warning">{{ processedData.deepseek?.decision || '—' }}</el-tag>
                <span class="confidence">置信度 {{ processedData.deepseek?.confidence || '—' }}%</span>
              </div>
            </div>
            <div class="risk-level" v-if="processedData.deepseek?.risk_level">
              <el-tag :type="getRiskTagType(processedData.deepseek.risk_level)" size="small">
                DeepSeek 风险评估：{{ processedData.deepseek.risk_level }}
              </el-tag>
            </div>
            <div class="system-note">
              <el-tag type="warning" size="small">系统已自动标记为「待人工审核」</el-tag>
            </div>
          </div>
        </template>
      </el-alert>

      <!-- 样式 C：仅 DeepSeek -->
      <el-alert
        v-else-if="processedData.ruleUsed === 'deepseek_only'"
        type="warning"
        :closable="false"
        show-icon
      >
        <template #title>
          <div class="summary-title">
            <strong>ⓘ 豆包未返回 · 本次由 DeepSeek 独立识别</strong>
          </div>
          <div class="summary-content">
            <div class="content-grid single">
              <div class="grid-item">
                <span class="label">DeepSeek 判断</span>
                <span class="value">{{ processedData.deepseek?.decision || '—' }} · 置信度 {{ processedData.deepseek?.confidence || '—' }}%</span>
              </div>
            </div>
            <div class="system-note">
              <el-tag type="warning" size="small">系统状态：已标记为「待人工审核」</el-tag>
            </div>
            <div v-if="processedData.deepseek?.warning" class="warning-text">
              <el-alert
                :title="processedData.deepseek.warning"
                type="warning"
                :closable="false"
                show-icon
              />
            </div>
          </div>
        </template>
      </el-alert>

      <!-- 样式 D：全部失败 -->
      <el-alert
        v-else-if="processedData.ruleUsed === 'all_failed'"
        type="error"
        :closable="false"
        show-icon
      >
        <template #title>
          <div class="summary-title">
            <strong>❌ 所有云端 AI 均不可用</strong>
          </div>
          <div class="summary-content">
            <p>仅保留 YOLO 本地检测，无法自动判断，请管理员人工审核</p>
          </div>
        </template>
      </el-alert>
    </div>

    <el-row :gutter="20">
      <!-- 左侧：图片预览 -->
      <el-col :span="10">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>违规图片</span>
              <el-button type="primary" link @click="handlePreview">
                <el-icon><FullScreen /></el-icon> 放大查看
              </el-button>
            </div>
          </template>
          <div class="image-container">
            <el-image
              v-if="imageUrl"
              :src="imageUrl"
              fit="contain"
              class="detail-image"
              :preview-src-list="[imageUrl]"
              preview-teleported
            >
              <template #error>
                <div class="image-load-failed">
                  <el-icon size="32" color="#f56c6c"><Warning /></el-icon>
                  <p>图片加载失败</p>
                  <p class="image-path">{{ imageUrl }}</p>
                </div>
              </template>
            </el-image>
            <div v-else class="no-image">暂无图片</div>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：字段信息 -->
      <el-col :span="14">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>违规详情</span>
            </div>
          </template>

          <el-descriptions :column="2" border>
            <el-descriptions-item label="ID">{{ detail.id }}</el-descriptions-item>
            <el-descriptions-item label="违规类型">
              <TypeTag :type="detail.violation_type" />
            </el-descriptions-item>
            <el-descriptions-item label="置信度">
              <ConfidenceBar :value="detail.confidence" style="width: 120px" />
            </el-descriptions-item>
            <el-descriptions-item label="审核状态">
              <StatusBadge :status="detail.status" />
            </el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ detail.created_at }}</el-descriptions-item>
            <el-descriptions-item label="云端校验">
              <el-badge v-if="detail.cloud_validated" type="success" text="云端已确权" />
              <el-icon v-else color="#999"><Close /></el-icon>
            </el-descriptions-item>
            <el-descriptions-item label="跟踪ID">{{ detail.track_id || '-' }}</el-descriptions-item>
            <el-descriptions-item label="检测位置" :span="2">
              {{ locationText }}
            </el-descriptions-item>
          </el-descriptions>

          <!-- M04: 车牌信息卡片 -->
          <div class="plate-info-card" v-if="detail.plate_number">
            <h4>
              <el-icon color="#0066CC"><Key /></el-icon>
              车牌信息
              <el-tag size="small" type="success" effect="plain" style="margin-left: 8px">
                多帧确认: {{ detail.confirmed_frames || 0 }} 帧
              </el-tag>
            </h4>
            <div class="plate-info-content">
              <div class="plate-image-section">
                <el-image
                  v-if="plateImageUrl"
                  :src="plateImageUrl"
                  fit="contain"
                  class="plate-image"
                  :preview-src-list="[plateImageUrl]"
                  preview-teleported
                >
                  <template #error>
                    <div class="plate-image-failed">车牌图加载失败</div>
                  </template>
                </el-image>
                <div v-else class="no-plate-image">无车牌图片</div>
              </div>
              <div class="plate-meta-section">
                <div class="plate-number-display">
                  <span :class="['plate-tag-large', getPlateColorClass(detail.plate_color)]">
                    {{ detail.plate_number }}
                  </span>
                </div>
                <el-descriptions :column="1" border size="small" class="plate-desc">
                  <el-descriptions-item label="车牌号">{{ detail.plate_number }}</el-descriptions-item>
                  <el-descriptions-item label="车牌颜色">
                    <el-tag size="small" :type="getPlateColorTagType(detail.plate_color)">
                      {{ getPlateColorText(detail.plate_color) }}
                    </el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="识别置信度">
                    {{ formatPlateConfidence(detail.plate_confidence) }}
                  </el-descriptions-item>
                  <el-descriptions-item label="确认帧数">
                    {{ detail.confirmed_frames || 0 }} 帧
                  </el-descriptions-item>
                </el-descriptions>
                <el-button
                  type="primary"
                  size="small"
                  plain
                  @click="handleSearchByPlate"
                  style="margin-top: 12px"
                >
                  <el-icon><Search /></el-icon>
                  查询此车牌历史违规
                </el-button>
              </div>
            </div>
          </div>

          <!-- 云端分析结果 -->
          <div v-if="detail.cloud_result" class="analysis-section">
            <h4>
              <el-icon color="#10B981"><Key /></el-icon>
              豆包大模型分析结果
              <el-tag size="small" effect="plain" style="margin-left: 8px">🎯 视觉模型</el-tag>
            </h4>
            <el-card class="analysis-card">
              <p class="analysis-text">{{ detail.cloud_result }}</p>
            </el-card>
          </div>

          <!-- DeepSeek 审核报告 -->
          <div class="analysis-section">
            <h4>
              <el-icon color="#8B5CF6"><Cpu /></el-icon>
              DeepSeek 逻辑审核报告
              <el-tag 
                size="small" 
                :type="deepseekReport ? 'success' : 'info'"
                style="margin-left: 8px"
              >
                {{ deepseekReport ? '已执行' : '未执行' }}
              </el-tag>
            </h4>
            <el-collapse>
              <el-collapse-item name="deepseek-report">
                <template #title>
                  <span v-if="deepseekReport">查看 DeepSeek 审核报告</span>
                  <span v-else class="no-report">本次分析 DeepSeek 不可用或未返回</span>
                </template>
                <div v-if="deepseekReport" class="deepseek-report-content">
                  <pre class="report-text">{{ deepseekReport }}</pre>
                </div>
                <div v-else class="no-report-placeholder">
                  <el-empty description="DeepSeek 审核报告不可用" :image-size="80" />
                </div>
              </el-collapse-item>
            </el-collapse>
          </div>

          <!-- YOLO检测结果 -->
          <div v-if="yoloResult" class="analysis-section">
            <h4>
              <el-icon color="#1890ff"><Search /></el-icon>
              YOLOv8 检测结果
            </h4>
            <el-card class="analysis-card">
              <pre class="yolo-result">{{ formatYoloResult }}</pre>
              <div v-if="(Array.isArray(yoloResult) && yoloResult.length > 0) || (yoloResult.detections && yoloResult.detections.length)" class="detection-list">
                <div 
                  v-for="(det, index) in (Array.isArray(yoloResult) ? yoloResult : yoloResult.detections)" 
                  :key="index" 
                  class="detection-item"
                >
                  <span class="det-class">{{ det.class_name }}</span>
                  <span class="det-conf">置信度: {{ (det.confidence * 100).toFixed(1) }}%</span>
                </div>
              </div>
            </el-card>
          </div>

          <!-- 附加信息 -->
          <div class="additional-info" v-if="additionalInfo.length">
            <h4>附加信息</h4>
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item
                v-for="[key, value] in additionalInfo"
                :key="key"
                :label="key"
              >
                {{ value }}
              </el-descriptions-item>
            </el-descriptions>
          </div>

          <!-- AI 推理结构化展示 -->
          <div class="ai-trace-section" v-if="processedData?.aiTrace">
            <h4>
              <el-icon color="#722ed1"><Cpu /></el-icon>
              AI 推理详情
            </h4>
            <el-collapse>
              <!-- 面板1：YOLO 本地检测 -->
              <el-collapse-item name="yolo">
                <template #title>
                  <div class="panel-title">
                    <span>🎯 YOLO 本地对象检测</span>
                    <el-tag
                      size="small"
                      :type="processedData.yolo?.success ? 'success' : 'danger'"
                    >
                      {{ processedData.yolo?.success ? '✅ 成功' : '❌ 失败' }}
                    </el-tag>
                  </div>
                </template>
                <div class="panel-content">
                  <div v-if="processedData.yolo?.success" class="yolo-summary">
                    <div class="summary-row">
                      <span class="label">对象总数：</span>
                      <span class="value">{{ processedData.yolo?.object_count || 0 }} 个</span>
                    </div>
                    <div v-if="processedData.yolo?.detections?.length" class="detection-list">
                      <div
                        v-for="(det, index) in processedData.yolo?.detections"
                        :key="index"
                        class="detection-item"
                      >
                        <span class="det-icon">•</span>
                        <span class="det-class">{{ det.class_name }}</span>
                        <span class="det-conf">置信度 {{ det.confidence }}%</span>
                      </div>
                    </div>
                    <el-collapse>
                      <el-collapse-item name="yolo-json">
                        <template #title>
                          <span class="debug-toggle">查看原始数据（供调试）</span>
                        </template>
                        <pre class="raw-json">{{ processedData.yoloRawJson }}</pre>
                      </el-collapse-item>
                    </el-collapse>
                  </div>
                  <div v-else class="no-data">YOLO 检测未成功执行</div>
                </div>
              </el-collapse-item>

              <!-- 面板2：豆包视觉模型 -->
              <el-collapse-item name="doubao">
                <template #title>
                  <div class="panel-title">
                    <span>🔍 豆包视觉模型</span>
                    <el-tag
                      v-if="processedData.doubao"
                      size="small"
                      :type="getDoubaoStatusType(processedData.doubao.status)"
                    >
                      {{ processedData.doubao.status_text }}
                    </el-tag>
                  </div>
                </template>
                <div class="panel-content">
                  <div v-if="processedData.doubao">
                    <div class="doubao-summary">
                      <div class="summary-row">
                        <span class="label">判断结果：</span>
                        <el-tag :type="processedData.doubao.is_violation ? 'danger' : 'success'" size="small">
                          {{ processedData.doubao.decision || '—' }}
                        </el-tag>
                        <span class="confidence">置信度 {{ processedData.doubao.confidence || '—' }}%</span>
                      </div>
                    </div>
                    <div v-if="processedData.doubao.raw_text" class="raw-text-section">
                      <div class="section-label">完整推理文本：</div>
                      <pre class="raw-text">{{ processedData.doubao.raw_text }}</pre>
                    </div>
                  </div>
                  <div v-else class="no-data">豆包分析未返回数据</div>
                </div>
              </el-collapse-item>

              <!-- 面板3：DeepSeek AI -->
              <el-collapse-item name="deepseek">
                <template #title>
                  <div class="panel-title">
                    <span>🧠 DeepSeek AI</span>
                    <el-tag
                      v-if="processedData.deepseek"
                      size="small"
                      :type="processedData.deepseek.role === 'logic_audit' ? 'primary' : 'warning'"
                    >
                      {{ processedData.deepseek.role_text }}
                    </el-tag>
                  </div>
                </template>
                <div class="panel-content">
                  <div v-if="processedData.deepseek">
                    <div class="deepseek-summary">
                      <div class="summary-row">
                        <span class="label">判断结果：</span>
                        <el-tag size="small">{{ processedData.deepseek.decision || '—' }}</el-tag>
                        <span class="confidence">置信度 {{ processedData.deepseek.confidence || '—' }}%</span>
                      </div>
                      <div class="summary-row" v-if="processedData.deepseek.risk_level">
                        <span class="label">风险等级：</span>
                        <el-tag :type="getRiskTagType(processedData.deepseek.risk_level)" size="small">
                          {{ processedData.deepseek.risk_level }}
                        </el-tag>
                      </div>
                      <div class="summary-row" v-if="processedData.deepseek.agree_with_doubao !== undefined">
                        <span class="label">是否同意豆包：</span>
                        <el-tag :type="processedData.deepseek.agree_with_doubao ? 'success' : 'warning'" size="small">
                          {{ processedData.deepseek.agree_with_doubao ? '是' : '否' }}
                        </el-tag>
                      </div>
                    </div>

                    <!-- DeepSeek 警告信息（醒目展示） -->
                    <div v-if="processedData.deepseek.warning" class="warning-section">
                      <el-alert
                        :title="processedData.deepseek.warning"
                        type="warning"
                        :closable="false"
                        show-icon
                      />
                    </div>

                    <!-- DeepSeek 完整文本 -->
                    <div v-if="processedData.deepseek.raw_text" class="raw-text-section">
                      <div class="section-label">DeepSeek 完整回答：</div>
                      <pre class="raw-text">{{ processedData.deepseek.raw_text }}</pre>
                    </div>
                  </div>
                  <div v-else class="no-data">DeepSeek 分析未返回数据</div>
                </div>
              </el-collapse-item>

              <!-- 面板4：上传元信息 -->
              <el-collapse-item name="meta">
                <template #title>
                  <div class="panel-title">
                    <span>📄 上传元信息</span>
                  </div>
                </template>
                <div class="panel-content">
                  <div class="meta-grid">
                    <div class="meta-item" v-if="processedData.meta?.source">
                      <span class="meta-label">上传来源</span>
                      <span class="meta-value">{{ processedData.meta.source }}</span>
                    </div>
                    <div class="meta-item" v-if="processedData.meta?.user_note">
                      <span class="meta-label">用户备注</span>
                      <span class="meta-value">{{ processedData.meta.user_note }}</span>
                    </div>
                    <div class="meta-item" v-if="processedData.meta?.original_filename">
                      <span class="meta-label">原始文件名</span>
                      <span class="meta-value">{{ processedData.meta.original_filename }}</span>
                    </div>
                    <div class="meta-item" v-if="processedData.meta?.analysis_note">
                      <span class="meta-label">分析备注</span>
                      <span class="meta-value">{{ processedData.meta.analysis_note }}</span>
                    </div>
                    <div class="meta-item" v-if="processedData.meta?.reanalysis_note">
                      <span class="meta-label">重新分析备注</span>
                      <span class="meta-value">{{ processedData.meta.reanalysis_note }}</span>
                    </div>
                  </div>
                  <div v-if="!processedData.meta" class="no-data">无上传元信息</div>
                </div>
              </el-collapse-item>
            </el-collapse>
          </div>

          <!-- 状态操作按钮组 -->
          <div class="action-buttons">
            <el-button
              :type="detail.status === 'pending' ? 'primary' : 'default'"
              @click="handleSetStatus('pending')"
            >
              待审核
            </el-button>
            <el-button
              :type="detail.status === 'confirmed' ? 'success' : 'default'"
              @click="handleSetStatus('confirmed')"
            >
              已确认
            </el-button>
            <el-button
              :type="detail.status === 'rejected' ? 'info' : 'default'"
              @click="handleSetStatus('rejected')"
            >
              已驳回
            </el-button>
            <el-button
              type="warning"
              @click="handleReanalyze"
              :loading="reanalyzing"
            >
              <el-icon><Refresh /></el-icon>
              重新分析
            </el-button>
          </div>

          <!-- 历史操作记录时间线 -->
          <div class="timeline-section">
            <h4>
              <el-icon color="#1890ff"><Clock /></el-icon>
              操作历史记录
            </h4>
            <el-timeline>
              <el-timeline-item
                v-for="(item, index) in historyTimeline"
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
          </div>
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
    <el-empty description="加载失败，请返回重试" />
    <el-button type="primary" @click="$router.back()">返回列表</el-button>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getDetail, update, reanalyze, getPlateImageUrl } from '../api'
import { formatDate } from '../utils/format'
import TypeTag from '../components/TypeTag.vue'
import StatusBadge from '../components/StatusBadge.vue'
import ConfidenceBar from '../components/ConfidenceBar.vue'
import {
  Search,
  Refresh,
  FullScreen,
  Close,
  Loading,
  Cpu,
  Warning,
  Key,
  Clock
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const reanalyzing = ref(false)
const detail = ref(null)

// ==================== 数据预处理 ====================
const processedData = computed(() => {
  if (!detail.value) return null

  // 解析 additional_info
  let additionalInfo = null
  if (detail.value?.additional_info) {
    try {
      additionalInfo = typeof detail.value.additional_info === 'string'
        ? JSON.parse(detail.value.additional_info)
        : detail.value.additional_info
    } catch {
      additionalInfo = {}
    }
  }

  // 提取 ai_trace
  const aiTrace = additionalInfo?.ai_trace || detail.value?.ai_trace || null

  // 兼容旧扁平格式 ai_trace（旧记录用 doubao_raw_text / deepseek_decision 等扁平 key）
  const normalizedTrace = (() => {
    if (!aiTrace) return null
    // 如果已有嵌套 doubao/deepseek/final，直接返回（v3 新格式）
    if (aiTrace.doubao && aiTrace.deepseek && aiTrace.final) {
      return aiTrace
    }
    // 否则把旧扁平格式转成嵌套格式
    return {
      version: aiTrace.version || 'v3_old',
      mode: aiTrace.deepseek ? 'doubao+deepseek_audit' : 'unknown',
      rule_used: aiTrace.rule_used || (aiTrace.needs_human_review ? 'disagreement_pending' : 'both_agree'),
      started_at: aiTrace.started_at || '',
      finished_at: aiTrace.finished_at || '',
      total_duration_ms: aiTrace.total_duration_ms || 0,
      yolo: {
        success: aiTrace.yolo_raw?.success !== false,
        message: aiTrace.yolo_raw?.message || '',
        object_count: aiTrace.yolo_raw?.detections?.length || 0,
        detections: (aiTrace.yolo_raw?.detections || []).map(d => ({
          class_name: d.class_name || d.class || '未知',
          confidence: typeof d.confidence === 'number' ? d.confidence : 0
        }))
      },
      doubao: {
        success: aiTrace.doubao_decision !== undefined && aiTrace.doubao_decision !== '失败',
        status: aiTrace.doubao_decision === '失败' ? 'failed' : 'success',
        decision: aiTrace.doubao_decision === '确认违规',
        confidence: typeof aiTrace.doubao_confidence === 'number' ? aiTrace.doubao_confidence : null,
        raw_text: aiTrace.doubao_raw_text || null,
        duration_ms: aiTrace.doubao_duration_ms || 0
      },
      deepseek: {
        success: aiTrace.deepseek_decision !== undefined,
        role: 'logic_audit',
        decision: aiTrace.deepseek_decision === '确认违规' ? true : (aiTrace.deepseek_decision === '未确认违规' ? false : null),
        confidence: typeof aiTrace.deepseek_confidence === 'number' ? aiTrace.deepseek_confidence : null,
        risk_level: aiTrace.deepseek_risk_level || 'medium',
        agree_with_doubao: typeof aiTrace.deepseek_doubao_match === 'boolean' ? aiTrace.deepseek_doubao_match : null,
        warning: null,
        raw_text: aiTrace.deepseek_raw_text || null,
        duration_ms: aiTrace.deepseek_duration_ms || 0
      },
      final: {
        decision: aiTrace.final_decision === '确认违规' ? '确认违规' : '未确认违规',
        confidence: typeof aiTrace.final_confidence === 'number' ? aiTrace.final_confidence : 0,
        needs_human_review: !!aiTrace.needs_human_review,
        rule_used: aiTrace.rule_used || (aiTrace.needs_human_review ? 'disagreement_pending' : 'both_agree')
      }
    }
  })()

  // 判断是否显示横幅（v3 版本才显示横幅；旧格式用 fallback 样式）
  const showBanner = (normalizedTrace?.version === 'v3') || (normalizedTrace?.version === 'v3_old')

  // 提取各部分数据（使用规范化后的 trace）
  const doubao = normalizedTrace?.doubao || null
  const deepseek = normalizedTrace?.deepseek || null
  const final = normalizedTrace?.final || {}

  // YOLO 数据处理
  let yolo = null
  let yoloRawJson = ''
  if (aiTrace?.yolo) {
    yolo = {
      success: aiTrace.yolo.success !== false,
      object_count: aiTrace.yolo.object_count || aiTrace.yolo.detections?.length || 0,
      detections: (aiTrace.yolo.detections || []).map(d => ({
        class_name: d.class_name || d.class || '未知',
        confidence: d.confidence ? (d.confidence * 100).toFixed(1) : '0.0',
        bbox: d.bbox // 保留但不直接展示
      }))
    }
    yoloRawJson = JSON.stringify(aiTrace.yolo, null, 2)
  } else if (detail.value?.yolo_detection_result) {
    // 兼容旧格式：从 yolo_detection_result 提取
    try {
      const yoloResult = typeof detail.value.yolo_detection_result === 'string'
        ? JSON.parse(detail.value.yolo_detection_result)
        : detail.value.yolo_detection_result
      if (yoloResult?.detections) {
        yolo = {
          success: yoloResult.success !== false,
          object_count: yoloResult.detections.length,
          detections: yoloResult.detections.map(d => ({
            class_name: d.class_name || d.class || '未知',
            confidence: d.confidence ? (d.confidence * 100).toFixed(1) : '0.0',
            bbox: d.bbox
          }))
        }
        yoloRawJson = JSON.stringify(yoloResult, null, 2)
      }
    } catch {}
  }

  // 豆包数据处理
  let doubaoProcessed = null
  if (doubao) {
    // 兼容：旧格式 doubao.decision 是 boolean，新格式是字符串
    const rawDecision = doubao.decision
    const isBoolDecision = typeof rawDecision === 'boolean'
    const decisionStr = isBoolDecision
      ? (rawDecision ? '是违规' : '不是违规')
      : rawDecision
    const isViolation = isBoolDecision
      ? rawDecision
      : (decisionStr?.includes('违规') || decisionStr?.includes('是') || decisionStr === 'confirm_violation')
    doubaoProcessed = {
      decision: formatDecision(decisionStr),
      confidence: typeof doubao.confidence === 'number' ? Math.round(doubao.confidence * 100) : null,
      raw_text: doubao.raw_text || null,
      status: doubao.status || 'success',
      status_text: getDoubaoStatusText(doubao.status),
      is_violation: isViolation
    }
  }

  // DeepSeek 数据处理
  let deepseekProcessed = null
  if (deepseek) {
    // 兼容：旧格式 deepseek.decision 是 boolean，新格式是字符串
    const rawDsDecision = deepseek.decision
    const isBoolDsDecision = typeof rawDsDecision === 'boolean'
    const dsDecisionStr = isBoolDsDecision
      ? (rawDsDecision ? '是违规' : '不是违规')
      : rawDsDecision
    deepseekProcessed = {
      decision: formatDecision(dsDecisionStr),
      confidence: typeof deepseek.confidence === 'number' ? Math.round(deepseek.confidence * 100) : null,
      risk_level: deepseek.risk_level || null,
      warning: deepseek.warning || null,
      raw_text: deepseek.raw_text || null,
      role: deepseek.role || 'logic_audit',
      role_text: deepseek.role === 'vision' ? '独立视觉识别' : '逻辑审核',
      agree_with_doubao: deepseek.agree_with_doubao
    }
  }

  // 最终决策
  const ruleUsed = final.rule_used || normalizedTrace?.rule_used || 'unknown'

  // 上传元信息（排除 ai_trace 相关字段）
  const meta = {}
  if (additionalInfo) {
    const excludeKeys = ['ai_trace', 'yolo', 'doubao', 'deepseek', 'final', 'source', 'user_note']
    Object.keys(additionalInfo).forEach(key => {
      if (!excludeKeys.includes(key) && additionalInfo[key] !== null && additionalInfo[key] !== undefined) {
        meta[key] = additionalInfo[key]
      }
    })
    // 中文映射
    if (additionalInfo.source) meta.source = additionalInfo.source
    if (additionalInfo.user_note) meta.user_note = additionalInfo.user_note
    if (additionalInfo.original_filename) meta.original_filename = additionalInfo.original_filename
    if (additionalInfo.analysis_note) meta.analysis_note = additionalInfo.analysis_note
    if (additionalInfo.reanalysis_note) meta.reanalysis_note = additionalInfo.reanalysis_note
  }

  return {
    aiTrace: normalizedTrace,
    showBanner,
    ruleUsed,
    final,
    doubao: doubaoProcessed,
    deepseek: deepseekProcessed,
    yolo,
    yoloRawJson,
    meta: Object.keys(meta).length ? meta : null,
    needsHumanReview: normalizedTrace?.final?.needs_human_review ?? additionalInfo?.needs_human_review ?? false,
    deepseekAudit: additionalInfo?.deepseek_audit || normalizedTrace?.deepseek?.raw_text || null
  }
})

// 格式化决策文本
function formatDecision(decision) {
  if (!decision) return '—'
  if (decision === 'confirm_violation' || decision.includes('违规') || decision === '是') return '是违规'
  if (decision === 'no_violation' || decision === '不是') return '不是违规'
  if (decision === 'uncertain' || decision === '不确定') return '不确定'
  return decision
}

// 获取豆包状态文本
function getDoubaoStatusText(status) {
  const statusMap = {
    'success': '成功',
    'timeout': '超时',
    'failed': '失败'
  }
  return statusMap[status] || '成功'
}

// 获取豆包状态标签类型
function getDoubaoStatusType(status) {
  const typeMap = {
    'success': 'success',
    'timeout': 'warning',
    'failed': 'danger'
  }
  return typeMap[status] || 'info'
}

// 获取风险等级标签类型
function getRiskTagType(riskLevel) {
  const riskMap = {
    'high': 'danger',
    '高风险': 'danger',
    'medium': 'warning',
    '中风险': 'warning',
    'low': 'success',
    '低风险': 'success'
  }
  return riskMap[riskLevel] || 'info'
}

// ==================== 原有计算属性 ====================
const imageUrl = computed(() => {
  if (!detail.value?.image_path) return ''
  const raw = detail.value.image_path
  const normalized = raw.replace(/\\/g, '/')
  const clean = normalized.replace(/^\/+/, '').replace(/^uploads\//, '')
  return '/uploads/' + clean
})

// M04: 车牌图片 URL
const plateImageUrl = computed(() => {
  if (!detail.value?.plate_image_path) return ''
  return getPlateImageUrl(detail.value.plate_image_path)
})

// M04: 车牌颜色对应 CSS 类名
function getPlateColorClass(color) {
  const map = {
    'blue': 'plate-blue',
    'green': 'plate-green',
    'yellow': 'plate-yellow',
    'unknown': 'plate-unknown'
  }
  return map[color] || 'plate-unknown'
}

// M04: 车牌颜色对应的标签类型
function getPlateColorTagType(color) {
  const map = {
    'blue': 'primary',
    'green': 'success',
    'yellow': 'warning',
    'unknown': 'info'
  }
  return map[color] || 'info'
}

// M04: 车牌颜色中文文本
function getPlateColorText(color) {
  const map = {
    'blue': '蓝色车牌',
    'green': '绿色车牌（新能源）',
    'yellow': '黄色车牌',
    'unknown': '未知颜色'
  }
  return map[color] || '未知颜色'
}

// M04: 格式化车牌置信度
function formatPlateConfidence(conf) {
  if (conf === null || conf === undefined) return '-'
  return (conf * 100).toFixed(2) + '%'
}

// M04: 跳转到列表页并按车牌查询
function handleSearchByPlate() {
  if (!detail.value?.plate_number) return
  router.push({
    path: '/violations',
    query: { plate_number: detail.value.plate_number }
  })
}

const locationText = computed(() => {
  const pos = detail.value?.position
  if (!pos) return '-'
  try {
    const p = typeof pos === 'string' ? JSON.parse(pos) : pos
    return `x:${Math.round(p.x)}, y:${Math.round(p.y)}, w:${Math.round(p.w)}, h:${Math.round(p.h)}`
  } catch {
    return '-'
  }
})

const additionalInfo = computed(() => {
  if (!detail.value?.additional_info) return []
  try {
    const info = typeof detail.value.additional_info === 'string'
      ? JSON.parse(detail.value.additional_info)
      : detail.value.additional_info
    return Object.entries(info)
  } catch {
    return []
  }
})

const yoloResult = computed(() => {
  if (!detail.value?.yolo_detection_result) return null
  try {
    let result = detail.value.yolo_detection_result
    if (typeof result === 'string') {
      result = JSON.parse(result)
    }
    if (Array.isArray(result)) return result
    return result?.detections ? result : null
  } catch {
    return null
  }
})

const formatYoloResult = computed(() => {
  if (!yoloResult.value) return ''
  if (Array.isArray(yoloResult.value)) {
    return JSON.stringify({detections: yoloResult.value}, null, 2)
  }
  return JSON.stringify(yoloResult.value, null, 2)
})

const aiTrace = computed(() => {
  if (detail.value?.ai_trace) {
    return detail.value.ai_trace
  }
  if (!detail.value?.additional_info) return null
  try {
    const info = typeof detail.value.additional_info === 'string'
      ? JSON.parse(detail.value.additional_info)
      : detail.value.additional_info
    return info.ai_trace || null
  } catch {
    return null
  }
})

const deepseekReport = computed(() => {
  if (!detail.value?.additional_info) return null
  try {
    const info = typeof detail.value.additional_info === 'string'
      ? JSON.parse(detail.value.additional_info)
      : detail.value.additional_info
    return info.deepseek_audit || null
  } catch {
    return null
  }
})

const historyTimeline = computed(() => {
  const events = []
  
  if (detail.value?.created_at) {
    events.push({
      time: detail.value.created_at,
      type: 'primary',
      action: '违规记录创建',
      description: '系统自动创建违规检测记录'
    })
  }
  
  const aiTrace = processedData.value?.aiTrace
  if (aiTrace?.yolo?.success) {
    events.push({
      time: formatDate(aiTrace.started_at),
      type: 'info',
      action: 'YOLO检测完成',
      description: `检测到 ${aiTrace.yolo.object_count} 个对象`
    })
  }
  
  if (aiTrace?.doubao?.status === 'success') {
    events.push({
      time: '-',
      type: 'warning',
      action: '豆包视觉分析完成',
      description: `判断结果：${aiTrace.doubao.decision === true ? '是违规' : '不是违规'}，置信度 ${aiTrace.doubao.confidence}%`
    })
  }
  
  if (aiTrace?.deepseek?.success) {
    events.push({
      time: '-',
      type: 'danger',
      action: 'DeepSeek逻辑审核完成',
      description: `判断结果：${aiTrace.deepseek.decision === true ? '确认违规' : '未确认'}，风险等级：${aiTrace.deepseek.risk_level}`
    })
  }
  
  if (detail.value?.cloud_validated) {
    events.push({
      time: '-',
      type: 'success',
      action: '云端验证完成',
      description: '云端AI验证结果已确认'
    })
  }
  
  if (detail.value?.status === 'confirmed') {
    events.push({
      time: formatDate(detail.value.updated_at),
      type: 'success',
      action: '状态变更：已确认违规',
      description: '管理员确认此违规有效'
    })
  } else if (detail.value?.status === 'rejected') {
    events.push({
      time: formatDate(detail.value.updated_at),
      type: 'info',
      action: '状态变更：已驳回',
      description: '管理员判定为误判'
    })
  }
  
  return events.sort((a, b) => {
    if (a.time === '-' || b.time === '-') return 0
    return b.time.localeCompare(a.time)
  })
})

// ==================== 生命周期 ====================
onMounted(async () => {
  await loadDetail()
})

async function loadDetail() {
  loading.value = true
  try {
    const id = route.params.id
    const res = await getDetail(id)
    detail.value = {
      ...res,
      created_at: formatDate(res.created_at)
    }
  } catch (err) {
    console.error('获取详情失败', err)
    ElMessage.error('加载违规详情失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

function handlePreview() {
  if (imageUrl.value) {
    window.open(imageUrl.value)
  }
}

async function handleSetStatus(status) {
  if (detail.value.status === status) return
  try {
    await update(detail.value.id, { status })
    ElMessage.success('状态更新成功')
    detail.value.status = status
  } catch (err) {
    console.error('更新状态失败', err)
  }
}

async function handleReanalyze() {
  reanalyzing.value = true
  try {
    const res = await reanalyze(detail.value.id)
    if (res.success) {
      ElMessage.success('重新分析完成')
      await loadDetail()
    } else {
      ElMessage.error(res.message || '重新分析失败')
    }
  } catch (err) {
    console.error('重新分析失败', err)
    ElMessage.error('重新分析失败')
  } finally {
    reanalyzing.value = false
  }
}
</script>

<style scoped lang="scss">
.violation-detail {
  .ai-summary-banner {
    margin-bottom: 20px;

    :deep(.el-alert) {
      border-radius: 8px;
      border: none;

      .el-alert__title {
        font-size: 14px;
        line-height: 1.8;
      }
    }

    .inconsistent-alert {
      background: linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%);
      border: 2px solid #F59E0B;
      box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
    }

    .summary-title {
      margin-bottom: 8px;
      font-size: 16px;
    }

    .summary-content {
      display: flex;
      flex-direction: column;
      gap: 8px;
      font-size: 13px;

      .el-divider {
        margin: 0 4px;
      }
    }

    .content-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 16px;
      margin-bottom: 12px;

      &.single {
        grid-template-columns: 1fr;
      }

      .grid-item {
        display: flex;
        flex-direction: column;
        gap: 4px;

        .label {
          font-size: 12px;
          color: #909399;
          font-weight: 500;
        }

        .value {
          font-size: 14px;
          color: #303133;
        }
      }
    }

    .final-confidence {
      padding-top: 8px;
      border-top: 1px solid rgba(255, 255, 255, 0.3);
      font-size: 14px;
    }

    .model-comparison {
      display: flex;
      align-items: center;
      gap: 16px;
      flex-wrap: wrap;

      .model-item {
        display: flex;
        align-items: center;
        gap: 6px;

        .model-label {
          font-weight: 500;
          color: #606266;
        }

        .confidence {
          color: #666;
          font-size: 12px;
        }
      }
    }

    .risk-level {
      margin-top: 8px;
    }

    .system-note {
      margin-top: 8px;
    }

    .warning-text {
      margin-top: 12px;

      :deep(.el-alert) {
        border-radius: 6px;
      }
    }

    .suggestion {
      color: #F59E0B;
      font-weight: 500;
    }
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  /* M04: 车牌信息卡片 */
  .plate-info-card {
    margin-top: 20px;
    padding: 16px;
    background: linear-gradient(135deg, #f0f9ff 0%, #e6f4ff 100%);
    border: 1px solid #bae0ff;
    border-radius: 8px;

    h4 {
      margin: 0 0 12px;
      font-size: 15px;
      display: flex;
      align-items: center;
      gap: 8px;
      color: #0066CC;
    }

    .plate-info-content {
      display: flex;
      gap: 20px;
      align-items: flex-start;
    }

    .plate-image-section {
      flex: 0 0 200px;

      .plate-image {
        width: 200px;
        height: 80px;
        border-radius: 4px;
        border: 1px solid #d9d9d9;
        background: #fff;
      }

      .plate-image-failed {
        width: 200px;
        height: 80px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #999;
        font-size: 12px;
        border: 1px solid #d9d9d9;
        border-radius: 4px;
        background: #fafafa;
      }

      .no-plate-image {
        width: 200px;
        height: 80px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #999;
        font-size: 12px;
        border: 1px dashed #d9d9d9;
        border-radius: 4px;
        background: #fafafa;
      }
    }

    .plate-meta-section {
      flex: 1;

      .plate-number-display {
        margin-bottom: 12px;
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

      .plate-desc {
        margin-top: 8px;
      }
    }
  }

  .image-container {
    min-height: 300px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .detail-image {
    width: 100%;
    max-height: 500px;
  }

  .no-image {
    color: #999;
    text-align: center;
    padding: 100px 0;
  }

  .image-load-failed {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 80px 12px;
    color: #f56c6c;
    text-align: center;

    p {
      margin: 8px 0 0;
      font-size: 14px;
    }

    .image-path {
      color: #999;
      font-size: 12px;
      font-family: monospace;
      word-break: break-all;
    }
  }

  .analysis-section {
    margin-top: 20px;
    padding-top: 20px;
    border-top: 1px solid #f0f0f0;

    h4 {
      margin: 0 0 12px;
      font-size: 15px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .analysis-card {
      .analysis-text {
        margin: 0;
        line-height: 1.8;
        color: #333;
        white-space: pre-wrap;
      }
    }

    .deepseek-report-content {
      background: #f8f9fa;
      border-radius: 4px;
      padding: 12px;

      .report-text {
        margin: 0;
        font-family: 'Monaco', 'Menlo', monospace;
        font-size: 13px;
        line-height: 1.6;
        white-space: pre-wrap;
        word-break: break-all;
        color: #333;
      }
    }

    .no-report {
      color: #999;
      font-size: 13px;
    }

    .no-report-placeholder {
      padding: 20px 0;
    }

    :deep(.el-collapse) {
      border: 1px solid #ebeef5;
      border-radius: 4px;

      .el-collapse-item__header {
        background: #fafafa;
        padding: 0 16px;
        font-size: 14px;
      }

      .el-collapse-item__content {
        padding: 16px;
      }
    }
  }

  .additional-info {
    margin-top: 20px;
    padding-top: 20px;
    border-top: 1px solid #f0f0f0;

    h4 {
      margin: 0 0 16px;
      font-size: 16px;
    }
  }

  .ai-trace-section {
    margin-top: 20px;
    padding-top: 20px;
    border-top: 1px solid #f0f0f0;

    h4 {
      margin: 0 0 16px;
      font-size: 16px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    // 面板标题样式
    .panel-title {
      display: flex;
      align-items: center;
      gap: 10px;
      width: 100%;
      font-weight: 500;
    }

    // 面板内容样式
    .panel-content {
      .summary-row {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 12px;

        .label {
          font-weight: 500;
          color: #606266;
          min-width: 80px;
        }

        .confidence {
          color: #909399;
          font-size: 13px;
        }
      }

      .no-data {
        color: #909399;
        text-align: center;
        padding: 20px 0;
        font-size: 14px;
      }
    }

    // YOLO 检测样式
    .yolo-summary {
      .detection-list {
        margin: 12px 0;
        padding: 12px;
        background: #f5f7fa;
        border-radius: 6px;

        .detection-item {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 4px 0;
          color: #303133;

          .det-icon {
            color: #409eff;
            font-weight: bold;
          }

          .det-class {
            font-weight: 500;
          }

          .det-conf {
            color: #909399;
            font-size: 13px;
          }
        }
      }

      .debug-toggle {
        color: #909399;
        font-size: 12px;
        font-weight: normal;
      }

      .raw-json {
        background: #1e1e1e;
        color: #d4d4d4;
        padding: 12px;
        border-radius: 4px;
        font-family: 'Monaco', 'Menlo', monospace;
        font-size: 12px;
        line-height: 1.5;
        overflow-x: auto;
        max-height: 300px;
        overflow-y: auto;
        margin: 12px 0 0;
      }
    }

    // 豆包模型样式
    .doubao-summary {
      margin-bottom: 12px;
    }

    // DeepSeek 样式
    .deepseek-summary {
      margin-bottom: 12px;
    }

    .warning-section {
      margin: 12px 0;

      :deep(.el-alert) {
        border-radius: 6px;
      }
    }

    // 原始文本样式
    .raw-text-section {
      margin-top: 16px;

      .section-label {
        font-size: 13px;
        color: #606266;
        margin-bottom: 8px;
        font-weight: 500;
      }

      .raw-text {
        background: #f8f9fa;
        padding: 12px;
        border-radius: 6px;
        font-size: 13px;
        line-height: 1.7;
        white-space: pre-wrap;
        word-break: break-all;
        color: #333;
        border: 1px solid #ebeef5;
        max-height: 400px;
        overflow-y: auto;
      }
    }

    // 上传元信息样式
    .meta-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 16px;

      .meta-item {
        display: flex;
        flex-direction: column;
        gap: 4px;

        .meta-label {
          font-size: 12px;
          color: #909399;
          font-weight: 500;
        }

        .meta-value {
          font-size: 14px;
          color: #303133;
          word-break: break-all;
        }
      }
    }

    // 折叠面板样式
    :deep(.el-collapse) {
      border: 1px solid #ebeef5;
      border-radius: 8px;
      overflow: hidden;

      .el-collapse-item {
        border-bottom: 1px solid #ebeef5;

        &:last-child {
          border-bottom: none;
        }

        &__header {
          background: #fafafa;
          padding: 12px 16px;
          font-size: 14px;
          font-weight: 500;

          &:hover {
            background: #f0f0f0;
          }
        }

        &__wrap {
          border-bottom: none;
        }

        &__content {
          padding: 16px;
          background: #fff;
        }
      }
    }

    .trace-summary {
      margin-top: 16px;
      padding-top: 12px;
      border-top: 1px dashed #e8e8e8;
    }
  }

  .action-buttons {
    margin-top: 24px;
    padding-top: 20px;
    border-top: 1px solid #f0f0f0;
    display: flex;
    gap: 12px;
  }

  .timeline-section {
    margin-top: 20px;
    padding-top: 20px;
    border-top: 1px solid #f0f0f0;

    h4 {
      margin: 0 0 16px;
      font-size: 16px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    :deep(.el-timeline) {
      padding-left: 0;

      .el-timeline-item {
        padding-bottom: 16px;

        &:last-child {
          padding-bottom: 0;
        }

        &__content {
          padding: 0;
        }

        &__timestamp {
          font-size: 12px;
          color: #909399;
        }
      }
    }

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
}

.loading,
.error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 100px 0;
  color: #999;
}

.loading .el-icon {
  font-size: 32px;
  margin-bottom: 16px;
}
</style>