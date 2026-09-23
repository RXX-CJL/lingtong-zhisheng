<template>
  <div class="event-center">
    <!-- 顶部统计卡片：当前活跃事件数 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card stat-active">
          <div class="stat-value">{{ activeCount }}</div>
          <div class="stat-label">活跃事件</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card stat-pending">
          <div class="stat-value">{{ pendingAiCount }}</div>
          <div class="stat-label">待 AI 分析</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card stat-review">
          <div class="stat-value">{{ manualReviewCount }}</div>
          <div class="stat-label">待人工复核</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card stat-confirmed">
          <div class="stat-value">{{ confirmedCount }}</div>
          <div class="stat-label">已确认违法</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 快速状态筛选 -->
    <div class="quick-filter">
      <el-button-group>
        <el-button
          v-for="opt in stateOptions"
          :key="opt.value"
          :type="searchForm.state === opt.value ? 'primary' : ''"
          @click="handleQuickState(opt.value)"
        >
          {{ opt.label }}
        </el-button>
      </el-button-group>
    </div>

    <!-- 搜索筛选区 -->
    <el-card shadow="hover" class="search-card">
      <el-form :inline="true" :model="searchForm">
        <el-form-item label="事件类型">
          <el-select v-model="searchForm.event_type" placeholder="全部类型" clearable style="width: 160px">
            <el-option label="闯红灯" value="red_light" />
            <el-option label="未戴头盔" value="no_helmet" />
            <el-option label="逆行" value="wrong_way" />
            <el-option label="违规停车" value="illegal_park" />
            <el-option label="压线行驶" value="lane_departure" />
            <el-option label="超速" value="speeding" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.state" placeholder="全部状态" clearable style="width: 140px">
            <el-option
              v-for="opt in stateOptions.filter(o => o.value !== 'all')"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="摄像头">
          <el-input v-model="searchForm.camera_id" placeholder="如 default" clearable style="width: 140px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon> 查询
          </el-button>
          <el-button @click="handleReset">
            <el-icon><Refresh /></el-icon> 重置
          </el-button>
          <el-button type="success" @click="loadData">
            <el-icon><RefreshRight /></el-icon> 刷新
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 事件列表表格 -->
    <el-card shadow="hover" class="table-card">
      <template #header>
        <div class="toolbar">
          <span>交通事件列表（共 {{ pagination.total }} 条）</span>
          <el-tag v-if="lastSyncAt" size="small" type="info">
            最近同步：{{ lastSyncAt }}
          </el-tag>
        </div>
      </template>

      <el-table
        v-loading="loading"
        :data="tableData"
        stripe
        style="width: 100%"
        :row-class-name="getRowClassName"
        @row-click="handleView"
        highlight-current-row
      >
        <el-table-column prop="event_id" label="事件 ID" width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="event-id">{{ row.event_id || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="120">
          <template #default="{ row }">
            <TypeTag :type="row.event_type" />
          </template>
        </el-table-column>
        <el-table-column label="车辆 ID" width="100">
          <template #default="{ row }">
            <span class="track-id">#{{ row.track_id ?? '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="车牌号" width="160">
          <template #default="{ row }">
            <span v-if="getPlateNumber(row)" class="plate-tag" :class="getPlateColorClass(getVehicleField(row, 'plate_color'))">
              {{ getPlateNumber(row) }}
            </span>
            <span v-else class="no-plate">-</span>
          </template>
        </el-table-column>
        <el-table-column label="摄像头" width="120">
          <template #default="{ row }">
            {{ row.camera_id || 'default' }}
          </template>
        </el-table-column>
        <el-table-column label="触发时间" width="180">
          <template #default="{ row }">
            {{ formatTriggerTime(row.trigger_time) || formatTriggerTime(row.created_at) || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="AI 置信度" width="160">
          <template #default="{ row }">
            <div class="confidence-cell">
              <el-progress
                v-if="typeof row.ai_confidence === 'number' && row.ai_confidence > 0"
                :percentage="Math.round(row.ai_confidence * 100)"
                :color="getConfidenceColor(row.ai_confidence)"
                :stroke-width="14"
                :text-inside="true"
                style="width: 120px"
              />
              <span v-else class="no-data">-</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="140">
          <template #default="{ row }">
            <el-tag :type="getStateTagType(row.state)" effect="dark">
              {{ getStateLabel(row.state) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click.stop="handleView(row)">
              <el-icon><View /></el-icon> 详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadData"
          @current-change="loadData"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getEventList, getActiveEvents } from '../api'
import { formatDate, getTypeName } from '../utils/format'
import TypeTag from '../components/TypeTag.vue'
import {
  Search,
  Refresh,
  RefreshRight,
  View
} from '@element-plus/icons-vue'

const router = useRouter()

const loading = ref(false)
const tableData = ref([])
const activeEvents = ref([])
const lastSyncAt = ref('')
const pollingTimer = ref(null)

const searchForm = reactive({
  event_type: '',
  state: 'all',
  camera_id: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 状态选项（8 状态 + 全部）
const stateOptions = [
  { value: 'all', label: '全部' },
  { value: 'detecting', label: '检测中' },
  { value: 'triggered', label: '已触发' },
  { value: 'recording', label: '录制中' },
  { value: 'pending_ai', label: '待 AI 分析' },
  { value: 'ai_reviewed', label: 'AI 已分析' },
  { value: 'confirmed', label: '已确认' },
  { value: 'rejected', label: '已排除' },
  { value: 'manual_review', label: '待人工复核' }
]

// 状态标签文本映射
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

// 状态标签类型映射（颜色）
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

// 统计指标（基于活跃事件 + 当前列表）
const activeCount = computed(() => activeEvents.value.length)
const pendingAiCount = computed(() =>
  activeEvents.value.filter(e => e.state === 'pending_ai').length
)
const manualReviewCount = computed(() =>
  tableData.value.filter(e => e.state === 'manual_review').length
)
const confirmedCount = computed(() =>
  tableData.value.filter(e => e.state === 'confirmed').length
)

// 车牌颜色对应 CSS 类名
function getPlateColorClass(color) {
  const map = {
    'blue': 'plate-blue',
    'green': 'plate-green',
    'yellow': 'plate-yellow',
    'unknown': 'plate-unknown'
  }
  return map[color] || 'plate-unknown'
}

// 从 vehicle_info JSON 中提取字段（graceful degradation）
function getVehicleField(row, field) {
  if (!row?.vehicle_info) return ''
  try {
    const info = typeof row.vehicle_info === 'string'
      ? JSON.parse(row.vehicle_info)
      : row.vehicle_info
    return info?.[field] || ''
  } catch {
    return ''
  }
}

function getPlateNumber(row) {
  return getVehicleField(row, 'plate_number') || ''
}

function getConfidenceColor(conf) {
  if (conf >= 0.85) return '#52c41a'
  if (conf >= 0.6) return '#faad14'
  return '#ff4d4f'
}

function formatTriggerTime(t) {
  if (!t) return ''
  return formatDate(t)
}

function getRowClassName({ row }) {
  if (row.state === 'manual_review') return 'manual-review-row'
  if (row.state === 'confirmed') return 'confirmed-row'
  if (row.state === 'rejected') return 'rejected-row'
  return ''
}

function handleQuickState(value) {
  searchForm.state = value
  pagination.page = 1
  loadData()
}

function handleSearch() {
  pagination.page = 1
  loadData()
}

function handleReset() {
  searchForm.event_type = ''
  searchForm.state = 'all'
  searchForm.camera_id = ''
  pagination.page = 1
  loadData()
}

function handleView(row) {
  if (!row?.event_id) {
    ElMessage.error('事件 ID 缺失，无法打开详情')
    return
  }
  router.push(`/events/${encodeURIComponent(row.event_id)}`)
}

// 加载事件列表
async function loadData() {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      size: pagination.pageSize,
      state: searchForm.state && searchForm.state !== 'all' ? searchForm.state : undefined,
      camera_id: searchForm.camera_id || undefined
    }
    const res = await getEventList(params)
    if (res.success === false) {
      ElMessage.error(res.message || '获取事件列表失败')
      tableData.value = []
      pagination.total = 0
    } else {
      tableData.value = res.data || []
      pagination.total = res.total || 0
    }
    lastSyncAt.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
  } catch (err) {
    console.error('[EventCenter] 获取事件列表失败', err)
    tableData.value = []
    pagination.total = 0
  } finally {
    loading.value = false
  }
}

// 加载活跃事件（用于顶部统计）
async function loadActiveEvents() {
  try {
    const res = await getActiveEvents()
    if (res.success !== false) {
      activeEvents.value = res.data || []
    }
  } catch (err) {
    // graceful degradation：静默失败
    console.warn('[EventCenter] 获取活跃事件失败', err)
  }
}

// 启动轮询（每 5 秒刷新活跃事件）
function startPolling() {
  stopPolling()
  pollingTimer.value = setInterval(() => {
    loadActiveEvents()
  }, 5000)
}

function stopPolling() {
  if (pollingTimer.value) {
    clearInterval(pollingTimer.value)
    pollingTimer.value = null
  }
}

onMounted(() => {
  loadData()
  loadActiveEvents()
  startPolling()
})

onBeforeUnmount(() => {
  stopPolling()
})
</script>

<style scoped lang="scss">
.event-center {
  .stats-row {
    margin-bottom: 16px;

    .stat-card {
      text-align: center;
      padding: 8px 0;

      .stat-value {
        font-size: 28px;
        font-weight: 700;
        line-height: 1.2;
      }

      .stat-label {
        margin-top: 4px;
        font-size: 13px;
        color: #909399;
      }

      &.stat-active .stat-value { color: #409eff; }
      &.stat-pending .stat-value { color: #722ed1; }
      &.stat-review .stat-value { color: #f56c6c; }
      &.stat-confirmed .stat-value { color: #52c41a; }
    }
  }

  .quick-filter {
    margin-bottom: 16px;
    padding: 12px 16px;
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);

    :deep(.el-button-group) {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;

      .el-button {
        border-radius: 4px;
        font-weight: 500;
        transition: all 0.3s;
        padding: 8px 14px;

        &:not(.is-active) {
          background: #fff;
          border-color: #dcdfe6;
          color: #606266;

          &:hover {
            color: #409eff;
            border-color: #c6e2ff;
            background: #ecf5ff;
          }
        }
      }
    }
  }

  .search-card {
    margin-bottom: 16px;
  }

  .table-card {
    :deep(.el-card__header) {
      padding: 16px 20px;
    }
  }

  .toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .pagination {
    margin-top: 20px;
    display: flex;
    justify-content: flex-end;
  }

  .event-id {
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 12px;
    color: #606266;
  }

  .track-id {
    font-family: 'Consolas', 'Monaco', monospace;
    color: #409eff;
    font-weight: 500;
  }

  .plate-tag {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-weight: 600;
    font-size: 13px;
    letter-spacing: 1px;
    min-width: 90px;
    text-align: center;
  }

  .plate-blue {
    background: #0066CC;
    color: #fff;
    border: 1px solid #004499;
  }

  .plate-green {
    background: #009933;
    color: #000;
    border: 1px solid #006622;
  }

  .plate-yellow {
    background: #FFCC00;
    color: #000;
    border: 1px solid #CC9900;
  }

  .plate-unknown {
    background: #f0f0f0;
    color: #606266;
    border: 1px solid #dcdfe6;
  }

  .no-plate {
    color: #999;
    font-size: 12px;
  }

  .confidence-cell {
    display: flex;
    align-items: center;
  }

  .no-data {
    color: #999;
    font-size: 12px;
  }

  // 行样式
  :deep(.manual-review-row) {
    background-color: #FFF1F0 !important;

    &:hover > td {
      background-color: #FFE7E5 !important;
    }
  }

  :deep(.confirmed-row) {
    background-color: #F6FFED !important;

    &:hover > td {
      background-color: #EBF8E5 !important;
    }
  }

  :deep(.rejected-row) {
    opacity: 0.7;
  }
}
</style>
