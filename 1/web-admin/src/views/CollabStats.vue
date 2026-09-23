<template>
  <div class="collab-stats" v-loading="loading">
    <!-- 顶部统计卡片 -->
    <el-row :gutter="20" class="stat-row">
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card stat-blue">
          <div class="stat-content">
            <div class="stat-icon">📊</div>
            <div class="stat-info">
              <div class="stat-label">总咨询次数</div>
              <div class="stat-value">{{ stats.total_consultations ?? 0 }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card stat-green">
          <div class="stat-content">
            <div class="stat-icon">✅</div>
            <div class="stat-info">
              <div class="stat-label">确认率</div>
              <div class="stat-value">{{ formatPercent(stats.confirmation_rate) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card stat-yellow">
          <div class="stat-content">
            <div class="stat-icon">⚠</div>
            <div class="stat-info">
              <div class="stat-label">分歧率</div>
              <div class="stat-value">{{ formatPercent(stats.disagreement_rate) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card stat-red">
          <div class="stat-content">
            <div class="stat-icon">🚀</div>
            <div class="stat-info">
              <div class="stat-label">准确率提升</div>
              <div class="stat-value">+{{ formatPercent(stats.accuracy_improvement) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 趋势图区域：每日咨询量（div 柱状图模拟） -->
    <el-card shadow="hover" class="chart-card">
      <template #header>
        <div class="card-header">
          <span>每日咨询量趋势</span>
          <el-tag size="small" type="info">近 {{ dailyTrend.length }} 天</el-tag>
        </div>
      </template>
      <div v-if="dailyTrend.length" class="bar-chart">
        <div class="bar-container">
          <div v-for="(item, idx) in dailyTrend" :key="idx" class="bar-item">
            <div class="bar-wrapper">
              <div
                class="bar"
                :style="{ height: getBarHeight(item.count) + '%' }"
                :title="`${item.date}: ${item.count} 次`"
              ></div>
            </div>
            <div class="bar-label">{{ item.date.slice(5) }}</div>
            <div class="bar-value">{{ item.count }}</div>
          </div>
        </div>
      </div>
      <el-empty v-else description="暂无趋势数据" />
    </el-card>

    <el-row :gutter="20" class="chart-row">
      <!-- 饼图区域：违规类型占比（CSS 比例条模拟） -->
      <el-col :xs="24" :md="12">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <span>各违规类型咨询占比</span>
            </div>
          </template>
          <div v-if="typeDistribution.length" class="pie-list">
            <div v-for="(item, idx) in typeDistribution" :key="idx" class="pie-item">
              <div class="pie-label">
                <span class="pie-color" :style="{ background: getTypeColor(item.violation_type) }"></span>
                <span>{{ getTypeName(item.violation_type) }}</span>
              </div>
              <div class="pie-bar-wrapper">
                <div
                  class="pie-bar"
                  :style="{
                    width: getPiePercent(item.count) + '%',
                    background: getTypeColor(item.violation_type)
                  }"
                ></div>
              </div>
              <div class="pie-value">{{ getPiePercent(item.count) }}%</div>
            </div>
          </div>
          <el-empty v-else description="暂无类型数据" />
        </el-card>
      </el-col>

      <!-- 柱状图：本地 vs 协作后准确率对比 -->
      <el-col :xs="24" :md="12">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <span>本地准确率 vs 协作后准确率</span>
            </div>
          </template>
          <div class="compare-chart">
            <div class="compare-item">
              <div class="compare-label">
                <span class="dot local"></span>
                本地准确率（YOLO）
              </div>
              <div class="compare-bar-wrapper">
                <div
                  class="compare-bar local"
                  :style="{ width: percentOf(stats.local_accuracy) }"
                >
                  <span class="compare-text">{{ formatPercent(stats.local_accuracy) }}</span>
                </div>
              </div>
            </div>
            <div class="compare-item">
              <div class="compare-label">
                <span class="dot collab"></span>
                协作后准确率（端云协同）
              </div>
              <div class="compare-bar-wrapper">
                <div
                  class="compare-bar collab"
                  :style="{ width: percentOf(stats.collab_accuracy) }"
                >
                  <span class="compare-text">{{ formatPercent(stats.collab_accuracy) }}</span>
                </div>
              </div>
            </div>
            <div class="compare-improve" v-if="stats.accuracy_improvement != null">
              <el-tag type="success" effect="dark">
                准确率提升 {{ formatPercent(stats.accuracy_improvement) }}
              </el-tag>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 节省费用估算 -->
    <el-card shadow="hover" class="chart-card cost-card">
      <template #header>
        <div class="card-header">
          <span>节省费用估算</span>
          <el-tag size="small" type="success">累计</el-tag>
        </div>
      </template>
      <el-row :gutter="20" class="cost-row">
        <el-col :xs="24" :sm="8">
          <div class="cost-item">
            <div class="cost-label">人工审核节省</div>
            <div class="cost-value">¥ {{ formatNumber(stats.cost_saved_manual) }}</div>
            <div class="cost-desc">减少人工复核工作量</div>
          </div>
        </el-col>
        <el-col :xs="24" :sm="8">
          <div class="cost-item">
            <div class="cost-label">误判纠正节省</div>
            <div class="cost-value">¥ {{ formatNumber(stats.cost_saved_misjudge) }}</div>
            <div class="cost-desc">避免误判造成的申诉成本</div>
          </div>
        </el-col>
        <el-col :xs="24" :sm="8">
          <div class="cost-item highlight">
            <div class="cost-label">总节省费用</div>
            <div class="cost-value total">¥ {{ formatNumber(stats.cost_saved_total) }}</div>
            <div class="cost-desc">合计节省金额</div>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import { getTypeName, getTypeColor } from '../utils/format'

const API_BASE = 'http://localhost:8001'

const loading = ref(false)
const stats = ref({})

const dailyTrend = computed(() => stats.value.daily_trend || [])
const typeDistribution = computed(() => stats.value.type_distribution || [])

// 柱状图最大值
const maxDailyCount = computed(() => {
  if (!dailyTrend.value.length) return 1
  return Math.max(...dailyTrend.value.map(i => i.count || 0), 1)
})

// 柱状图高度百分比
function getBarHeight(count) {
  if (!count) return 0
  return Math.round((count / maxDailyCount.value) * 100)
}

// 类型占比分母
const totalTypeCount = computed(() => {
  return typeDistribution.value.reduce((sum, item) => sum + (item.count || 0), 0) || 1
})

function getPiePercent(count) {
  if (!count) return 0
  return Math.round((count / totalTypeCount.value) * 100)
}

// 兼容 0-1 小数或 0-100 整数
function toPercentNum(value) {
  if (value === null || value === undefined) return 0
  const num = Number(value)
  if (Number.isNaN(num)) return 0
  if (num > 0 && num <= 1) return num * 100
  return num
}

function formatPercent(value) {
  return toPercentNum(value).toFixed(1) + '%'
}

function percentOf(value) {
  const n = toPercentNum(value)
  return Math.max(0, Math.min(100, n)) + '%'
}

function formatNumber(value) {
  if (value === null || value === undefined) return '0.00'
  return Number(value).toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })
}

async function loadStats() {
  loading.value = true
  try {
    const res = await axios.get(`${API_BASE}/api/cloud/statistics`)
    stats.value = res.data || {}
  } catch (err) {
    console.error('获取协作统计数据失败', err)
    ElMessage.error('获取协作统计数据失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadStats()
})
</script>

<style scoped lang="scss">
.collab-stats {
  .stat-row {
    margin-bottom: 20px;
  }

  .stat-card {
    border-radius: 8px;
    border-left: 4px solid #1a73e8;
    margin-bottom: 16px;
    transition: transform 0.2s;

    &:hover {
      transform: translateY(-2px);
    }

    &.stat-green { border-left-color: #67c23a; }
    &.stat-yellow { border-left-color: #e6a23c; }
    &.stat-red { border-left-color: #f56c6c; }

    .stat-content {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .stat-icon {
      font-size: 32px;
      width: 56px;
      height: 56px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 8px;
      background: #f0f5ff;
      flex-shrink: 0;
    }

    .stat-info {
      flex: 1;
      min-width: 0;
    }

    .stat-label {
      font-size: 13px;
      color: #909399;
      margin-bottom: 6px;
    }

    .stat-value {
      font-size: 24px;
      font-weight: 700;
      color: #303133;
      word-break: break-all;
    }
  }

  .chart-card {
    margin-bottom: 20px;

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-weight: 600;
    }
  }

  .chart-row {
    margin-bottom: 0;
  }

  // 每日咨询量柱状图
  .bar-chart {
    .bar-container {
      display: flex;
      align-items: flex-end;
      gap: 8px;
      height: 260px;
      padding: 16px 8px 4px;
      overflow-x: auto;
    }

    .bar-item {
      flex: 1;
      min-width: 40px;
      display: flex;
      flex-direction: column;
      align-items: center;
      height: 100%;
    }

    .bar-wrapper {
      flex: 1;
      width: 100%;
      display: flex;
      align-items: flex-end;
      justify-content: center;
    }

    .bar {
      width: 70%;
      background: linear-gradient(180deg, #1a73e8 0%, #4d9bf5 100%);
      border-radius: 4px 4px 0 0;
      transition: height 0.4s ease;
      min-height: 2px;
    }

    .bar-label {
      font-size: 12px;
      color: #606266;
      margin-top: 8px;
      white-space: nowrap;
    }

    .bar-value {
      font-size: 11px;
      color: #909399;
      margin-top: 2px;
    }
  }

  // 违规类型占比
  .pie-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 8px 0;
  }

  .pie-item {
    display: flex;
    align-items: center;
    gap: 12px;

    .pie-label {
      display: flex;
      align-items: center;
      gap: 8px;
      width: 120px;
      font-size: 13px;
      color: #303133;
      flex-shrink: 0;
    }

    .pie-color {
      width: 12px;
      height: 12px;
      border-radius: 2px;
      flex-shrink: 0;
    }

    .pie-bar-wrapper {
      flex: 1;
      height: 18px;
      background: #f5f7fa;
      border-radius: 9px;
      overflow: hidden;
    }

    .pie-bar {
      height: 100%;
      border-radius: 9px;
      transition: width 0.4s ease;
    }

    .pie-value {
      width: 50px;
      text-align: right;
      font-size: 13px;
      font-weight: 600;
      color: #303133;
      flex-shrink: 0;
    }
  }

  // 准确率对比
  .compare-chart {
    padding: 24px 16px;

    .compare-item {
      margin-bottom: 24px;

      .compare-label {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 14px;
        color: #606266;
        margin-bottom: 8px;
        font-weight: 500;

        .dot {
          width: 10px;
          height: 10px;
          border-radius: 50%;

          &.local { background: #e6a23c; }
          &.collab { background: #67c23a; }
        }
      }

      .compare-bar-wrapper {
        height: 32px;
        background: #f5f7fa;
        border-radius: 16px;
        overflow: hidden;
      }

      .compare-bar {
        height: 100%;
        border-radius: 16px;
        display: flex;
        align-items: center;
        justify-content: flex-end;
        padding-right: 12px;
        transition: width 0.5s ease;
        min-width: 60px;

        &.local {
          background: linear-gradient(90deg, #e6a23c 0%, #f0c78d 100%);
        }

        &.collab {
          background: linear-gradient(90deg, #67c23a 0%, #95d475 100%);
        }

        .compare-text {
          color: #fff;
          font-weight: 600;
          font-size: 13px;
        }
      }
    }

    .compare-improve {
      margin-top: 16px;
      text-align: center;
    }
  }

  // 节省费用估算
  .cost-card {
    .cost-row {
      margin-top: 8px;
    }

    .cost-item {
      text-align: center;
      padding: 20px 16px;
      border-radius: 8px;
      background: #f8fafc;
      margin-bottom: 16px;

      &.highlight {
        background: linear-gradient(135deg, #f0f9eb 0%, #e1f3d8 100%);
        border: 1px solid #b3e19d;
      }

      .cost-label {
        font-size: 13px;
        color: #909399;
        margin-bottom: 8px;
      }

      .cost-value {
        font-size: 28px;
        font-weight: 700;
        color: #1a73e8;
        margin-bottom: 6px;

        &.total {
          color: #67c23a;
        }
      }

      .cost-desc {
        font-size: 12px;
        color: #909399;
      }
    }
  }
}

// 响应式：小屏调整
@media (max-width: 768px) {
  .collab-stats {
    .stat-card {
      .stat-value {
        font-size: 20px;
      }
    }

    .bar-chart .bar-container {
      height: 220px;
    }
  }
}
</style>
