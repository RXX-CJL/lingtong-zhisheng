<template>
  <div class="ai-trace">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>精度验证 · AI 分析结果总览</span>
        </div>
      </template>

      <!-- 筛选条 -->
      <el-form :inline="true" class="filter-form">
        <el-form-item label="违规类型">
          <el-select v-model="filters.violation_type" placeholder="全部类型" clearable style="width: 150px">
            <el-option label="闯红灯" value="red_light" />
            <el-option label="未戴头盔" value="no_helmet" />
            <el-option label="逆行" value="wrong_way" />
            <el-option label="违规停车" value="illegal_parking" />
            <el-option label="压线行驶" value="lane_departure" />
            <el-option label="超速" value="speeding" />
          </el-select>
        </el-form-item>
        <el-form-item label="是否已确认">
          <el-select v-model="filters.cloud_validated" placeholder="全部" clearable style="width: 120px">
            <el-option label="已确认" :value="true" />
            <el-option label="未确认" :value="false" />
          </el-select>
        </el-form-item>
        <el-form-item label="置信度范围">
          <el-slider
            v-model="filters.confidence_range"
            range
            :min="0"
            :max="100"
            style="width: 200px"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">
            <el-icon><Search /></el-icon> 查询
          </el-button>
          <el-button @click="handleReset">
            <el-icon><Refresh /></el-icon> 重置
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 批量操作 -->
      <div class="batch-actions">
        <el-button
          type="warning"
          :disabled="!selectedRows.length"
          :loading="batchReanalyzing"
          @click="handleBatchReanalyze"
        >
          <el-icon><Refresh /></el-icon>
          批量重新分析
        </el-button>
        <span v-if="selectedRows.length" class="selection-info">
          已选择 {{ selectedRows.length }} 条记录
        </span>
      </div>

      <!-- 主表格 -->
      <el-table
        v-loading="loading"
        :data="tableData"
        stripe
        @selection-change="handleSelectionChange"
        @row-click="handleRowClick"
      >
        <el-table-column type="selection" width="50" />
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column label="类型" width="120">
          <template #default="{ row }">
            <TypeTag :type="row.violation_type" />
          </template>
        </el-table-column>
        <el-table-column label="最终置信度" width="120">
          <template #default="{ row }">
            <ConfidenceBar :value="row.confidence" />
          </template>
        </el-table-column>
        <el-table-column label="YOLO 命中对象数" width="140">
          <template #default="{ row }">
            {{ getYoloCount(row) }}
          </template>
        </el-table-column>
        <el-table-column label="豆包是否确认违规" width="140">
          <template #default="{ row }">
            <el-tag v-if="row.cloud_validated" type="success">是</el-tag>
            <el-tag v-else type="info">否</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="当前状态" width="100">
          <template #default="{ row }">
            <StatusBadge :status="row.status" />
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click.stop="handleViewDetail(row)">
              查看详情
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
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getList, reanalyze } from '../api'
import { formatDate } from '../utils/format'
import TypeTag from '../components/TypeTag.vue'
import StatusBadge from '../components/StatusBadge.vue'
import ConfidenceBar from '../components/ConfidenceBar.vue'
import { Search, Refresh } from '@element-plus/icons-vue'

const router = useRouter()

const loading = ref(false)
const batchReanalyzing = ref(false)
const tableData = ref([])
const selectedRows = ref([])

const filters = reactive({
  violation_type: '',
  cloud_validated: null,
  confidence_range: [0, 100]
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

onMounted(() => {
  loadData()
})

async function loadData() {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize,
      violation_type: filters.violation_type || undefined,
      status: undefined
    }
    const res = await getList(params)
    
    // 前端过滤
    let items = (res.items || []).map(item => ({
      ...item,
      created_at: formatDate(item.created_at)
    }))
    
    // 置信度过滤
    items = items.filter(item => {
      const conf = (item.confidence || 0) * 100
      return conf >= filters.confidence_range[0] && conf <= filters.confidence_range[1]
    })
    
    // cloud_validated 过滤
    if (filters.cloud_validated !== null) {
      items = items.filter(item => item.cloud_validated === filters.cloud_validated)
    }
    
    tableData.value = items
    pagination.total = items.length
  } catch (err) {
    console.error('获取列表失败', err)
  } finally {
    loading.value = false
  }
}

function handleReset() {
  filters.violation_type = ''
  filters.cloud_validated = null
  filters.confidence_range = [0, 100]
  pagination.page = 1
  loadData()
}

function handleSelectionChange(selection) {
  selectedRows.value = selection
}

function getYoloCount(row) {
  if (!row.yolo_detection_result?.detections) return 0
  return row.yolo_detection_result.detections.length
}

function handleRowClick(row) {
  router.push(`/violations/${row.id}`)
}

function handleViewDetail(row) {
  router.push(`/violations/${row.id}`)
}

async function handleBatchReanalyze() {
  if (!selectedRows.value.length) return
  
  // 只对"待审核"生效
  const pendingRows = selectedRows.value.filter(r => r.status === 'pending')
  if (!pendingRows.length) {
    ElMessage.warning('没有待审核的记录可以重新分析')
    return
  }
  
  batchReanalyzing.value = true
  let successCount = 0
  let failCount = 0
  
  for (const row of pendingRows) {
    try {
      const res = await reanalyze(row.id)
      if (res.success) {
        successCount++
      } else {
        failCount++
      }
    } catch (err) {
      failCount++
    }
  }
  
  batchReanalyzing.value = false
  selectedRows.value = []
  
  if (successCount > 0) {
    ElMessage.success(`成功重新分析 ${successCount} 条记录`)
  }
  if (failCount > 0) {
    ElMessage.warning(`${failCount} 条记录重新分析失败`)
  }
  
  loadData()
}
</script>

<style scoped lang="scss">
.ai-trace {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .filter-form {
    margin-bottom: 20px;
  }

  .batch-actions {
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 12px;

    .selection-info {
      font-size: 13px;
      color: #666;
    }
  }

  .pagination {
    margin-top: 20px;
    display: flex;
    justify-content: flex-end;
  }
}
</style>
