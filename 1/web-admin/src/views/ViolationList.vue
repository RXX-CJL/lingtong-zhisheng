<template>
  <div class="violation-list">
    <el-tabs v-model="activeTab" type="card" class="main-tabs">
      <el-tab-pane label="违规列表" name="list">
    <!-- 快速状态筛选 -->
    <div class="quick-filter">
      <el-button-group>
        <el-button
          :type="quickStatus === 'all' ? 'primary' : ''"
          @click="handleQuickStatusChange('all')"
        >
          全部
        </el-button>
        <el-button
          :type="quickStatus === 'confirmed' ? 'primary' : ''"
          @click="handleQuickStatusChange('confirmed')"
        >
          ✅ 已确认违规
        </el-button>
        <el-button
          :type="quickStatus === 'pending_review' ? 'primary' : ''"
          @click="handleQuickStatusChange('pending_review')"
          class="warning-button"
        >
          ⚠ 待人工审核
        </el-button>
        <el-button
          :type="quickStatus === 'pending' ? 'primary' : ''"
          @click="handleQuickStatusChange('pending')"
        >
          待审核
        </el-button>
      </el-button-group>
    </div>

    <!-- 搜索筛选区 -->
    <el-card shadow="hover" class="search-card">
      <el-form :inline="true" :model="searchForm">
        <el-form-item label="违规类型">
          <el-select v-model="searchForm.violation_type" placeholder="全部类型" clearable style="width: 150px">
            <el-option label="闯红灯" value="red_light" />
            <el-option label="未戴头盔" value="no_helmet" />
            <el-option label="逆行" value="wrong_way" />
            <el-option label="违规停车" value="illegal_parking" />
            <el-option label="压线行驶" value="lane_departure" />
            <el-option label="超速" value="speeding" />
          </el-select>
        </el-form-item>
        <el-form-item label="审核状态">
          <el-select v-model="searchForm.status" placeholder="全部状态" clearable style="width: 120px">
            <el-option label="待审核" value="pending" />
            <el-option label="已确认" value="confirmed" />
            <el-option label="已驳回" value="rejected" />
          </el-select>
        </el-form-item>
        <!-- M04: 车牌号搜索框 -->
        <el-form-item label="车牌号">
          <el-input
            v-model="searchForm.plate_number"
            placeholder="如 京A12345"
            clearable
            style="width: 150px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 240px"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon> 查询
          </el-button>
          <el-button @click="handleReset">
            <el-icon><Refresh /></el-icon> 重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 工具栏 -->
    <el-card shadow="hover" class="table-card">
      <template #header>
        <div class="toolbar">
          <span>违规记录列表</span>
          <div>
            <el-button type="success" :disabled="!selectedRows.length" @click="handleBatchConfirm">
              <el-icon><Check /></el-icon> 批量确认
            </el-button>
            <el-button type="danger" :disabled="!selectedRows.length" @click="handleBatchDelete">
              <el-icon><Delete /></el-icon> 批量删除
            </el-button>
          </div>
        </div>
      </template>

      <!-- 表格 -->
      <el-table
        v-loading="loading"
        :data="tableData"
        stripe
        style="width: 100%"
        :row-class-name="getRowClassName"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="50" />
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column label="缩略图" width="100">
          <template #default="{ row }">
            <el-image
              v-if="getThumbnail(row.image_path)"
              :src="getThumbnail(row.image_path)"
              fit="cover"
              class="thumbnail"
              :preview-src-list="[getThumbnail(row.image_path)]"
            />
            <span v-else class="no-image">-</span>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="120">
          <template #default="{ row }">
            <TypeTag :type="row.violation_type" />
          </template>
        </el-table-column>
        <!-- M04: 车牌号列 + 颜色小标签 -->
        <el-table-column label="车牌号" width="160">
          <template #default="{ row }">
            <div v-if="row.plate_number" class="plate-cell">
              <span :class="['plate-tag', getPlateColorClass(row.plate_color)]">
                {{ row.plate_number }}
              </span>
              <span v-if="row.confirmed_frames > 0" class="confirmed-frames">
                {{ row.confirmed_frames }}帧
              </span>
            </div>
            <span v-else class="no-plate">-</span>
          </template>
        </el-table-column>
        <el-table-column label="置信度" width="180">
          <template #default="{ row }">
            <div class="confidence-cell">
              <span class="confidence-value">{{ formatConfidence(row.confidence) }}</span>
              <el-badge
                v-if="row.status === 'pending_review'"
                value="🛡"
                class="review-indicator"
                type="danger"
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column label="设备位置" width="180">
          <template #default="{ row }">
            {{ getLocationText(row) }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" />
        <el-table-column label="状态" width="140">
          <template #default="{ row }">
            <el-tag
              :type="getStatusTagType(row.status)"
              :effect="row.status === 'pending_review' ? 'dark' : 'light'"
              :class="{ 'status-bold': row.status === 'pending_review' }"
            >
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="云端校验" width="120">
          <template #default="{ row }">
            <el-icon v-if="row.cloud_validated" color="#52c41a"><Check /></el-icon>
            <el-icon v-else color="#999"><Close /></el-icon>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="handleView(row)">查看</el-button>
            <el-button type="warning" link @click="handleReanalyze(row)" :loading="reanalyzingId === row.id">重新分析</el-button>
            <el-button type="success" link @click="handleConfirm(row)" v-if="row.status === 'pending'">确认</el-button>
            <el-button type="danger" link @click="handleReject(row)" v-if="row.status === 'pending'">驳回</el-button>
            <el-button type="danger" link @click="handleDelete(row)">删除</el-button>
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
      </el-tab-pane>
      <el-tab-pane label="交通事件" name="events">
        <EventCenter />
      </el-tab-pane>
      <el-tab-pane label="申诉管理" name="appeals">
        <AppealList />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getList, update, remove, reanalyze } from '../api'
import { formatDate } from '../utils/format'
import TypeTag from '../components/TypeTag.vue'
import StatusBadge from '../components/StatusBadge.vue'
import ConfidenceBar from '../components/ConfidenceBar.vue'
import EventCenter from './EventCenter.vue'
import AppealList from './AppealList.vue'

const activeTab = ref('list')

const router = useRouter()

const loading = ref(false)
const tableData = ref([])
const selectedRows = ref([])
const dateRange = ref([])
const quickStatus = ref('all')
const reanalyzingId = ref(null)

const searchForm = reactive({
  violation_type: '',
  status: '',
  start_date: '',
  end_date: '',
  // M04: 车牌号搜索
  plate_number: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 状态标签映射
const statusLabels = {
  'confirmed': '✅ 已确认',
  'pending_review': '⚠ 待人工',
  'pending': '· 待审核'
}

// 状态标签类型映射
const statusTagTypes = {
  'confirmed': 'success',
  'pending_review': 'warning',
  'pending': 'info',
  'rejected': 'danger'
}

// 获取状态标签文本
function getStatusLabel(status) {
  return statusLabels[status] || status
}

// 获取状态标签类型
function getStatusTagType(status) {
  return statusTagTypes[status] || 'info'
}

// 格式化置信度（两位小数+百分号）
function formatConfidence(confidence) {
  if (confidence === null || confidence === undefined) return '-'
  return (confidence * 100).toFixed(2) + '%'
}

// M04: 车牌颜色对应 CSS 类名（蓝底白字 / 绿底黑字 / 黄底黑字）
function getPlateColorClass(color) {
  const map = {
    'blue': 'plate-blue',
    'green': 'plate-green',
    'yellow': 'plate-yellow',
    'unknown': 'plate-unknown'
  }
  return map[color] || 'plate-unknown'
}

// 判断是否需要人工审核（防错处理）
function needsHumanReview(row) {
  if (!row?.additional_info) return false
  try {
    const info = typeof row.additional_info === 'string'
      ? JSON.parse(row.additional_info)
      : row.additional_info
    return info?.needs_human_review === true
  } catch {
    return false
  }
}

// 获取行样式类名
function getRowClassName({ row }) {
  if (row.status === 'pending_review') {
    return 'pending-review-row'
  }
  return ''
}

function getThumbnail(imagePath) {
  if (!imagePath) return ''
  const normalized = imagePath.replace(/\\/g, '/')
  const clean = normalized.replace(/^\/+/, '').replace(/^uploads\//, '')
  return '/uploads/' + clean
}

function getLocationText(row) {
  if (row?.additional_info) {
    try {
      const info = typeof row.additional_info === 'string'
        ? JSON.parse(row.additional_info)
        : row.additional_info
      if (info?.location) return info.location
    } catch {}
  }
  if (row?.position) {
    try {
      const pos = typeof row.position === 'string' ? JSON.parse(row.position) : row.position
      if (pos) return `x:${pos.x}, y:${pos.y}`
    } catch {}
  }
  return '-'
}

async function handleReanalyze(row) {
  reanalyzingId.value = row.id
  try {
    const res = await reanalyze(row.id)
    if (res.success) {
      ElMessage.success('重新分析完成')
      loadData()
    } else {
      ElMessage.error(res.message || '重新分析失败')
    }
  } catch (err) {
    console.error('重新分析失败', err)
    ElMessage.error('重新分析失败')
  } finally {
    reanalyzingId.value = null
  }
}

onMounted(() => {
  loadData()
})

async function loadData() {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize,
      violation_type: searchForm.violation_type || undefined,
      status: searchForm.status || undefined,
      start_time: dateRange.value?.[0] || undefined,
      end_time: dateRange.value?.[1] || undefined,
      // M04: 车牌号查询
      plate_number: searchForm.plate_number || undefined
    }
    const res = await getList(params)
    tableData.value = (res.items || []).map(item => ({
      ...item,
      created_at: formatDate(item.created_at)
    }))
    pagination.total = res.total || 0
  } catch (err) {
    console.error('获取列表失败', err)
  } finally {
    loading.value = false
  }
}

// 快速状态筛选处理
function handleQuickStatusChange(value) {
  quickStatus.value = value
  if (value === 'all') {
    searchForm.status = ''
  } else {
    searchForm.status = value
  }
  pagination.page = 1
  loadData()
}

function handleSearch() {
  pagination.page = 1
  loadData()
}

function handleReset() {
  searchForm.violation_type = ''
  searchForm.status = ''
  // M04: 重置车牌号
  searchForm.plate_number = ''
  quickStatus.value = 'all'
  dateRange.value = []
  pagination.page = 1
  loadData()
}

function handleSelectionChange(selection) {
  selectedRows.value = selection
}

function handleView(row) {
  if (!row || row.id === undefined || row.id === null) {
    ElMessage.error('记录 ID 缺失，无法打开详情')
    return
  }
  router.push(`/violations/${row.id}`)
}

async function handleConfirm(row) {
  try {
    await update(row.id, { status: 'confirmed' })
    ElMessage.success('确认成功')
    loadData()
  } catch (err) {
    console.error('确认失败', err)
  }
}

async function handleReject(row) {
  try {
    await update(row.id, { status: 'rejected' })
    ElMessage.success('驳回成功')
    loadData()
  } catch (err) {
    console.error('驳回失败', err)
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm('确定要删除这条记录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await remove(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch (err) {
    if (err !== 'cancel') {
      console.error('删除失败', err)
    }
  }
}

async function handleBatchConfirm() {
  const ids = selectedRows.value.map(row => row.id)
  try {
    for (const id of ids) {
      await update(id, { status: 'confirmed' })
    }
    ElMessage.success('批量确认成功')
    selectedRows.value = []
    loadData()
  } catch (err) {
    console.error('批量确认失败', err)
  }
}

async function handleBatchDelete() {
  const ids = selectedRows.value.map(row => row.id)
  try {
    await ElMessageBox.confirm(`确定要删除选中的 ${ids.length} 条记录吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    for (const id of ids) {
      await remove(id)
    }
    ElMessage.success('批量删除成功')
    selectedRows.value = []
    loadData()
  } catch (err) {
    if (err !== 'cancel') {
      console.error('批量删除失败', err)
    }
  }
}
</script>

<style scoped lang="scss">
.violation-list {
  .quick-filter {
    margin-bottom: 16px;
    padding: 12px 16px;
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);

    :deep(.el-button-group) {
      display: flex;
      gap: 8px;

      .el-button {
        border-radius: 4px;
        font-weight: 500;
        transition: all 0.3s;
        padding: 8px 16px;

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

        &.is-active {
          font-weight: 700;
          box-shadow: 0 2px 8px rgba(64, 158, 255, 0.3);
        }

        &.warning-button {
          &:not(.is-active) {
            border-color: #f5dab1;
            background: #fdf6ec;
            color: #e6a23c;

            &:hover {
              background: #fdf6ec;
              border-color: #f5dab1;
              color: #f56c23;
            }
          }

          &.is-active {
            background: #f56c23;
            border-color: #f56c23;
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

  .thumbnail {
    width: 60px;
    height: 60px;
    border-radius: 4px;
    cursor: pointer;
  }

  .no-image {
    color: #999;
    font-size: 12px;
    line-height: 60px;
    text-align: center;
  }

  /* M04: 车牌号列样式 */
  .plate-cell {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;

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

    .confirmed-frames {
      font-size: 11px;
      color: #909399;
    }
  }

  .no-plate {
    color: #999;
    font-size: 12px;
  }

  // 置信度单元格样式
  .confidence-cell {
    display: flex;
    align-items: center;
    gap: 8px;
    position: relative;

    .confidence-value {
      font-weight: 500;
      color: #303133;
      font-size: 13px;
    }

    .review-indicator {
      :deep(.el-badge__content) {
        font-size: 12px;
        padding: 2px 6px;
        height: auto;
        line-height: 1.2;
      }
    }
  }

  // 状态标签样式
  .el-tag {
    font-weight: 500;
  }

  .status-bold {
    font-weight: 700;
  }

  // 待人工审核行样式
  :deep(.pending-review-row) {
    background-color: #FFF7ED !important;

    &:hover > td {
      background-color: #FFEDD5 !important;
    }
  }
}
</style>