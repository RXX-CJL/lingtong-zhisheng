<template>
  <div class="appeal-list">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>申诉管理</span>
        </div>
      </template>

      <!-- 统计卡片 -->
      <el-row :gutter="20" class="stat-row">
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card pending">
            <div class="stat-num">{{ stats.pending || 0 }}</div>
            <div class="stat-label">待处理</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card reviewing">
            <div class="stat-num">{{ stats.reviewing || 0 }}</div>
            <div class="stat-label">审核中</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card approved">
            <div class="stat-num">{{ stats.approved || 0 }}</div>
            <div class="stat-label">已通过</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card rejected">
            <div class="stat-num">{{ stats.rejected || 0 }}</div>
            <div class="stat-label">已驳回</div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 筛选条件 -->
      <el-form :inline="true" class="filter-form">
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable>
            <el-option label="待处理" value="pending" />
            <el-option label="审核中" value="reviewing" />
            <el-option label="已通过" value="approved" />
            <el-option label="已驳回" value="rejected" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadAppeals">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 申诉列表 -->
      <el-table :data="appeals" v-loading="loading" stripe>
        <el-table-column prop="violation_id" label="违规ID" width="100" />
        <el-table-column prop="reason" label="申诉理由" min-width="200" show-overflow-tooltip />
        <el-table-column prop="contact" label="联系方式" width="150" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="申诉时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="result" label="处理结果" width="150" show-overflow-tooltip />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="showDetail(row)">详情</el-button>
            <el-button 
              v-if="row.status === 'pending'" 
              size="small" 
              type="primary" 
              @click="processAppealAction(row, 'approved')"
            >通过</el-button>
            <el-button 
              v-if="row.status === 'pending'" 
              size="small" 
              type="danger" 
              @click="processAppealAction(row, 'rejected')"
            >驳回</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 申诉详情对话框 -->
    <el-dialog v-model="showDetailDialog" title="申诉详情" width="700px">
      <el-descriptions :column="2" border v-if="currentAppeal">
        <el-descriptions-item label="违规ID">{{ currentAppeal.violation_id }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(currentAppeal.status)">{{ getStatusText(currentAppeal.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="申诉理由" :span="2">{{ currentAppeal.reason }}</el-descriptions-item>
        <el-descriptions-item label="联系方式">{{ currentAppeal.contact || '-' }}</el-descriptions-item>
        <el-descriptions-item label="申诉时间">
          {{ formatTime(currentAppeal.created_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="证据图片" :span="2">
          <div v-if="currentAppeal.evidence_urls?.length">
            <el-image 
              v-for="(url, idx) in currentAppeal.evidence_urls" 
              :key="idx"
              :src="url"
              :preview-src-list="currentAppeal.evidence_urls"
              style="width: 100px; height: 100px; margin-right: 10px;"
              fit="cover"
            />
          </div>
          <span v-else>-</span>
        </el-descriptions-item>
        <el-descriptions-item label="处理结果" :span="2">
          {{ currentAppeal.result || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="处理时间" :span="2">
          {{ formatTime(currentAppeal.processed_at) }}
        </el-descriptions-item>
      </el-descriptions>

      <!-- 关联违规详情 -->
      <el-divider v-if="currentViolation" />
      <div v-if="currentViolation">
        <h4>关联违规信息</h4>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="违规类型">{{ currentViolation.violation_type }}</el-descriptions-item>
          <el-descriptions-item label="置信度">{{ (currentViolation.confidence * 100).toFixed(1) }}%</el-descriptions-item>
          <el-descriptions-item label="违规时间" :span="2">
            {{ formatTime(currentViolation.timestamp) }}
          </el-descriptions-item>
        </el-descriptions>
        <div v-if="currentViolation.image_path" style="margin-top: 15px;">
          <el-image 
            :src="currentViolation.image_path" 
            style="max-width: 100%; max-height: 300px;"
            fit="contain"
          />
        </div>
      </div>

      <template #footer>
        <el-button @click="showDetailDialog = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 处理申诉对话框 -->
    <el-dialog v-model="showProcessDialog" title="处理申诉" width="500px">
      <el-form :model="processForm" label-width="100px">
        <el-form-item label="处理结果">
          <el-radio-group v-model="processForm.status">
            <el-radio label="approved">通过</el-radio>
            <el-radio label="rejected">驳回</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注">
          <el-input 
            v-model="processForm.result" 
            type="textarea" 
            :rows="3"
            placeholder="请输入处理备注"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showProcessDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmProcess" :loading="submitting">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAppealList, getAppealDetail, getAppealStats, processAppeal } from '@/api'

const loading = ref(false)
const submitting = ref(false)
const appeals = ref([])
const stats = ref({})
const filters = reactive({ status: '' })
const showDetailDialog = ref(false)
const showProcessDialog = ref(false)
const currentAppeal = ref(null)
const currentViolation = ref(null)

const processForm = reactive({
  status: '',
  result: ''
})

const loadAppeals = async () => {
  loading.value = true
  try {
    const params = {}
    if (filters.status) params.status = filters.status
    
    const res = await getAppealList(params)
    if (res.success) {
      appeals.value = res.data.appeals || []
    }
  } catch (err) {
    ElMessage.error('加载申诉列表失败')
  } finally {
    loading.value = false
  }
}

const loadStats = async () => {
  try {
    const res = await getAppealStats()
    if (res.success) {
      stats.value = res.data
    }
  } catch (err) {
    console.error('加载统计失败', err)
  }
}

const resetFilters = () => {
  filters.status = ''
  loadAppeals()
}

const showDetail = async (row) => {
  try {
    const res = await getAppealDetail(row.violation_id)
    if (res.success) {
      currentAppeal.value = res.data.appeal
      currentViolation.value = res.data.violation
      showDetailDialog.value = true
    }
  } catch (err) {
    ElMessage.error('加载详情失败')
  }
}

const processAppealAction = (row, status) => {
  currentAppeal.value = row
  processForm.status = status
  processForm.result = ''
  showProcessDialog.value = true
}

const confirmProcess = async () => {
  if (!processForm.result) {
    ElMessage.warning('请输入处理备注')
    return
  }
  
  submitting.value = true
  try {
    const res = await processAppeal(currentAppeal.value.violation_id, processForm)
    if (res.success) {
      ElMessage.success('处理成功')
      showProcessDialog.value = false
      loadAppeals()
      loadStats()
    } else {
      ElMessage.error(res.message || '处理失败')
    }
  } catch (err) {
    ElMessage.error('处理失败')
  } finally {
    submitting.value = false
  }
}

const getStatusType = (status) => {
  const map = { 
    pending: 'warning', 
    reviewing: 'primary', 
    approved: 'success', 
    rejected: 'danger' 
  }
  return map[status] || 'info'
}

const getStatusText = (status) => {
  const map = { 
    pending: '待处理', 
    reviewing: '审核中', 
    approved: '已通过', 
    rejected: '已驳回' 
  }
  return map[status] || status
}

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

onMounted(() => {
  loadAppeals()
  loadStats()
})
</script>

<style scoped>
.appeal-list { padding: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.stat-row { margin-bottom: 20px; }
.stat-card { text-align: center; padding: 10px; }
.stat-card.pending { border-left: 4px solid #E6A23C; }
.stat-card.reviewing { border-left: 4px solid #409EFF; }
.stat-card.approved { border-left: 4px solid #67C23A; }
.stat-card.rejected { border-left: 4px solid #F56C6C; }
.stat-num { font-size: 28px; font-weight: bold; }
.stat-label { color: #909399; margin-top: 5px; }
.filter-form { margin-bottom: 20px; }
</style>
