<template>
  <div class="disagreement-list">
    <!-- 筛选区 -->
    <el-card shadow="hover" class="filter-card">
      <el-form :inline="true" :model="searchForm">
        <el-form-item label="违规类型">
          <el-select
            v-model="searchForm.violation_type"
            placeholder="全部类型"
            clearable
            style="width: 150px"
          >
            <el-option label="闯红灯" value="red_light" />
            <el-option label="未戴头盔" value="no_helmet" />
            <el-option label="逆行" value="wrong_way" />
            <el-option label="违规停车" value="illegal_parking" />
            <el-option label="压线行驶" value="lane_departure" />
            <el-option label="超速" value="speeding" />
          </el-select>
        </el-form-item>
        <el-form-item label="裁决结果">
          <el-select
            v-model="searchForm.judgment_result"
            placeholder="全部"
            clearable
            style="width: 140px"
          >
            <el-option label="待定" value="pending" />
            <el-option label="支持本地" value="uphold" />
            <el-option label="驳回本地" value="overturn" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 分歧案例表格 -->
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>分歧案例列表</span>
          <el-tag type="warning">共 {{ pagination.total }} 条</el-tag>
        </div>
      </template>

      <el-table
        v-loading="loading"
        :data="tableData"
        stripe
        style="width: 100%"
        :empty-text="loading ? '加载中...' : '暂无分歧案例'"
      >
        <el-table-column prop="session_id" label="会话ID" width="200" show-overflow-tooltip />
        <el-table-column label="违规类型" width="120">
          <template #default="{ row }">
            <TypeTag :type="row.violation_type" />
          </template>
        </el-table-column>
        <el-table-column label="本地置信度" width="160">
          <template #default="{ row }">
            <ConfidenceBar :value="row.local_confidence" style="width: 110px" />
          </template>
        </el-table-column>
        <el-table-column label="最终置信度" width="160">
          <template #default="{ row }">
            <ConfidenceBar :value="row.final_confidence" style="width: 110px" />
          </template>
        </el-table-column>
        <el-table-column label="裁决结果" width="120">
          <template #default="{ row }">
            <el-tag :type="getJudgmentTagType(row.judgment_result)">
              {{ getJudgmentText(row.judgment_result) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="320" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="handleViewDetail(row)">查看详情</el-button>
            <el-button type="success" link @click="handleQuickResolve(row, 'uphold')">支持</el-button>
            <el-button type="danger" link @click="handleQuickResolve(row, 'overturn')">驳回</el-button>
            <el-button type="warning" link @click="handleQuickResolve(row, 'pending')">待定</el-button>
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

    <!-- 详情对话框 -->
    <el-dialog
      v-model="detailVisible"
      title="分歧案例详情"
      width="85%"
      top="5vh"
      destroy-on-close
    >
      <div v-loading="detailLoading">
        <div v-if="detail" class="detail-content">
          <el-row :gutter="20">
            <!-- 左侧：图片 -->
            <el-col :xs="24" :md="10">
              <el-card shadow="never">
                <template #header>
                  <span>违规图片</span>
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
                      <div class="image-failed">
                        <p>图片加载失败</p>
                        <p class="image-path">{{ imageUrl }}</p>
                      </div>
                    </template>
                  </el-image>
                  <div v-else class="no-image">暂无图片</div>
                </div>
              </el-card>
            </el-col>

            <!-- 右侧：判断对比 -->
            <el-col :xs="24" :md="14">
              <el-card shadow="never" class="compare-card">
                <template #header>
                  <span>本地判断 vs 云端判断</span>
                </template>

                <el-row :gutter="16">
                  <el-col :span="12">
                    <div class="judge-block local">
                      <div class="judge-title">本地判断（YOLO）</div>
                      <div class="judge-row">
                        <span class="label">判断结果：</span>
                        <el-tag :type="detail.local_judgment ? 'danger' : 'success'" size="small">
                          {{ detail.local_judgment ? '违规' : '未违规' }}
                        </el-tag>
                      </div>
                      <div class="judge-row">
                        <span class="label">置信度：</span>
                        <ConfidenceBar :value="detail.local_confidence" style="width: 120px" />
                      </div>
                      <div class="judge-row" v-if="detail.local_classes">
                        <span class="label">检测对象：</span>
                        <span class="value-text">{{ detail.local_classes }}</span>
                      </div>
                    </div>
                  </el-col>
                  <el-col :span="12">
                    <div class="judge-block cloud">
                      <div class="judge-title">云端判断（AI 协作）</div>
                      <div class="judge-row">
                        <span class="label">判断结果：</span>
                        <el-tag :type="detail.cloud_judgment ? 'danger' : 'success'" size="small">
                          {{ detail.cloud_judgment ? '违规' : '未违规' }}
                        </el-tag>
                      </div>
                      <div class="judge-row">
                        <span class="label">置信度：</span>
                        <ConfidenceBar :value="detail.final_confidence" style="width: 120px" />
                      </div>
                      <div class="judge-row" v-if="detail.cloud_reason">
                        <span class="label">云端理由：</span>
                        <span class="value-text reason-text">{{ detail.cloud_reason }}</span>
                      </div>
                    </div>
                  </el-col>
                </el-row>

                <!-- 分歧描述 -->
                <div class="disagreement-info">
                  <el-alert
                    type="warning"
                    :closable="false"
                    show-icon
                  >
                    <template #title>
                      <strong>分歧说明：</strong>{{ detail.disagreement_type || '本地与云端判断结果不一致' }}
                    </template>
                  </el-alert>
                </div>

                <!-- 基本信息 -->
                <el-descriptions :column="2" border size="small" class="basic-info">
                  <el-descriptions-item label="会话ID">{{ detail.session_id }}</el-descriptions-item>
                  <el-descriptions-item label="违规类型">
                    <TypeTag :type="detail.violation_type" />
                  </el-descriptions-item>
                  <el-descriptions-item label="创建时间">{{ detail.created_at }}</el-descriptions-item>
                  <el-descriptions-item label="当前裁决">
                    <el-tag :type="getJudgmentTagType(detail.judgment_result)" size="small">
                      {{ getJudgmentText(detail.judgment_result) }}
                    </el-tag>
                  </el-descriptions-item>
                </el-descriptions>
              </el-card>
            </el-col>
          </el-row>

          <!-- 裁决历史 -->
          <el-card shadow="never" class="history-card">
            <template #header>
              <span>裁决历史记录</span>
            </template>
            <el-timeline v-if="history.length">
              <el-timeline-item
                v-for="(item, idx) in history"
                :key="idx"
                :timestamp="item.created_at"
                :type="getJudgmentTagType(item.judgment_result)"
              >
                <div class="history-content">
                  <el-tag :type="getJudgmentTagType(item.judgment_result)" size="small">
                    {{ getJudgmentText(item.judgment_result) }}
                  </el-tag>
                  <span class="history-operator">操作人：{{ item.operator || '系统' }}</span>
                  <span class="history-note" v-if="item.note">备注：{{ item.note }}</span>
                </div>
              </el-timeline-item>
            </el-timeline>
            <el-empty v-else description="暂无裁决历史" :image-size="80" />
          </el-card>

          <!-- 裁决操作 -->
          <div class="resolve-actions">
            <el-input
              v-model="resolveNote"
              placeholder="裁决备注（可选）"
              style="width: 360px"
            />
            <el-button type="success" :loading="resolving" @click="submitResolve('uphold')">
              支持本地
            </el-button>
            <el-button type="danger" :loading="resolving" @click="submitResolve('overturn')">
              驳回本地
            </el-button>
            <el-button type="warning" :loading="resolving" @click="submitResolve('pending')">
              标记待定
            </el-button>
          </div>
        </div>
        <el-empty v-else-if="!detailLoading" description="加载失败，请重试" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
import { formatDate } from '../utils/format'
import TypeTag from '../components/TypeTag.vue'
import ConfidenceBar from '../components/ConfidenceBar.vue'

const API_BASE = 'http://localhost:8001'

const loading = ref(false)
const tableData = ref([])

const searchForm = reactive({
  violation_type: '',
  judgment_result: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

// 详情对话框
const detailVisible = ref(false)
const detailLoading = ref(false)
const detail = ref(null)
const history = ref([])
const resolveNote = ref('')
const resolving = ref(false)
const currentSessionId = ref(null)

// 裁决结果映射
const judgmentTextMap = {
  pending: '待定',
  uphold: '支持本地',
  overturn: '驳回本地'
}

const judgmentTagTypeMap = {
  pending: 'warning',
  uphold: 'success',
  overturn: 'danger'
}

function getJudgmentText(result) {
  return judgmentTextMap[result] || result || '待定'
}

function getJudgmentTagType(result) {
  return judgmentTagTypeMap[result] || 'info'
}

// 图片 URL
const imageUrl = computed(() => {
  if (!detail.value?.image_path) return ''
  const raw = detail.value.image_path
  const normalized = raw.replace(/\\/g, '/')
  const clean = normalized.replace(/^\/+/, '').replace(/^uploads\//, '')
  return '/uploads/' + clean
})

// 加载列表
async function loadData() {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize,
      violation_type: searchForm.violation_type || undefined,
      judgment_result: searchForm.judgment_result || undefined
    }
    const res = await axios.get(`${API_BASE}/api/cloud/disagreements`, { params })
    const data = res.data || {}
    tableData.value = (data.items || []).map(item => ({
      ...item,
      created_at: formatDate(item.created_at)
    }))
    pagination.total = data.total || 0
  } catch (err) {
    console.error('获取分歧列表失败', err)
    ElMessage.error('获取分歧列表失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.page = 1
  loadData()
}

function handleReset() {
  searchForm.violation_type = ''
  searchForm.judgment_result = ''
  pagination.page = 1
  loadData()
}

// 查看详情
async function handleViewDetail(row) {
  detailVisible.value = true
  detail.value = null
  history.value = []
  resolveNote.value = ''
  currentSessionId.value = row.session_id
  detailLoading.value = true
  try {
    const res = await axios.get(`${API_BASE}/api/cloud/collab-detail/${row.session_id}`)
    const data = res.data || {}
    detail.value = {
      ...data,
      created_at: formatDate(data.created_at)
    }
    history.value = (data.history || []).map(item => ({
      ...item,
      created_at: formatDate(item.created_at)
    }))
  } catch (err) {
    console.error('获取详情失败', err)
    ElMessage.error('获取详情失败')
  } finally {
    detailLoading.value = false
  }
}

// 表格内快速裁决
async function handleQuickResolve(row, result) {
  try {
    await ElMessageBox.confirm(
      `确定要将此案例裁决为「${getJudgmentText(result)}」吗？`,
      '裁决确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    await axios.post(`${API_BASE}/api/cloud/resolve-disagreement`, {
      session_id: row.session_id,
      judgment_result: result
    })
    ElMessage.success('裁决成功')
    loadData()
  } catch (err) {
    if (err === 'cancel') return
    console.error('裁决失败', err)
    ElMessage.error('裁决失败')
  }
}

// 详情对话框内提交裁决
async function submitResolve(result) {
  if (!currentSessionId.value) return
  resolving.value = true
  try {
    await axios.post(`${API_BASE}/api/cloud/resolve-disagreement`, {
      session_id: currentSessionId.value,
      judgment_result: result,
      note: resolveNote.value || undefined
    })
    ElMessage.success('裁决成功')
    // 重新加载详情
    await handleViewDetail({ session_id: currentSessionId.value })
    // 刷新列表
    loadData()
  } catch (err) {
    console.error('裁决失败', err)
    ElMessage.error('裁决失败')
  } finally {
    resolving.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped lang="scss">
.disagreement-list {
  .filter-card {
    margin-bottom: 16px;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 600;
  }

  .pagination {
    margin-top: 20px;
    display: flex;
    justify-content: flex-end;
  }

  // 详情对话框内容
  .detail-content {
    .image-container {
      min-height: 240px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #fafafa;
      border-radius: 4px;
    }

    .detail-image {
      width: 100%;
      max-height: 360px;
    }

    .no-image {
      color: #999;
      text-align: center;
      padding: 80px 0;
    }

    .image-failed {
      color: #f56c6c;
      text-align: center;
      padding: 80px 0;

      p {
        margin: 6px 0;
      }

      .image-path {
        color: #999;
        font-size: 12px;
        font-family: monospace;
        word-break: break-all;
      }
    }

    .compare-card {
      margin-bottom: 16px;
    }

    .judge-block {
      padding: 16px;
      border-radius: 8px;
      height: 100%;
      box-sizing: border-box;

      &.local {
        background: #fff7e6;
        border: 1px solid #ffd591;
      }

      &.cloud {
        background: #e6fffb;
        border: 1px solid #87e8de;
      }

      .judge-title {
        font-weight: 600;
        font-size: 14px;
        margin-bottom: 12px;
        color: #303133;
      }

      .judge-row {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 10px;
        font-size: 13px;

        .label {
          color: #606266;
          min-width: 80px;
          flex-shrink: 0;
        }

        .value-text {
          flex: 1;
          color: #303133;
          line-height: 1.6;
        }

        .reason-text {
          font-style: italic;
          color: #531dab;
        }
      }
    }

    .disagreement-info {
      margin: 16px 0;
    }

    .basic-info {
      margin-top: 8px;
    }

    .history-card {
      margin-top: 16px;

      .history-content {
        display: flex;
        align-items: center;
        gap: 12px;
        flex-wrap: wrap;

        .history-operator {
          font-size: 13px;
          color: #606266;
        }

        .history-note {
          font-size: 13px;
          color: #909399;
        }
      }
    }

    .resolve-actions {
      margin-top: 20px;
      padding-top: 16px;
      border-top: 1px solid #f0f0f0;
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
    }
  }
}

// 响应式
@media (max-width: 768px) {
  .disagreement-list {
    .detail-content {
      .resolve-actions {
        .el-input {
          width: 100% !important;
        }
      }
    }
  }
}
</style>
