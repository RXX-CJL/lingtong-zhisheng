<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stat-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon bg-blue">
            <el-icon size="28"><Document /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-num">{{ stats.total || 0 }}</div>
            <div class="stat-label">总违规数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon bg-orange">
            <el-icon size="28"><Plus /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-num">{{ stats.today || 0 }}</div>
            <div class="stat-label">今日新增</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon bg-purple">
            <el-icon size="28"><Calendar /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-num">{{ stats.thisMonth || 0 }}</div>
            <div class="stat-label">本月违规</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon bg-yellow">
            <el-icon size="28"><Clock /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-num">{{ stats.pending || 0 }}</div>
            <div class="stat-label">待审核</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon bg-green">
            <el-icon size="28"><CircleCheck /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-num">{{ stats.confirmed || 0 }}</div>
            <div class="stat-label">已确认</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon bg-cyan">
            <el-icon size="28"><Monitor /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-num">{{ stats.onlineDevices || 0 }}</div>
            <div class="stat-label">设备在线数</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" class="chart-row">
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>违规类型分布</span>
            </div>
          </template>
          <div ref="pieChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>近7天趋势</span>
              <el-select v-model="trendDays" size="small" @change="loadStats">
                <el-option label="近7天" :value="7" />
                <el-option label="近30天" :value="30" />
              </el-select>
            </div>
          </template>
          <div ref="lineChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>设备违规排行 TOP10</span>
            </div>
          </template>
          <div ref="barChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 最新违规滚动列表 -->
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card shadow="hover" class="pending-card">
          <template #header>
            <div class="card-header">
              <span>最新待审核</span>
              <el-button type="primary" link @click="$router.push('/violations')">
                查看全部 <el-icon><ArrowRight /></el-icon>
              </el-button>
            </div>
          </template>
          <el-table :data="pendingList" stripe style="width: 100%">
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column label="类型" width="120">
              <template #default="{ row }">
                <TypeTag :type="row.violation_type" />
              </template>
            </el-table-column>
            <el-table-column label="置信度" width="150">
              <template #default="{ row }">
                <ConfidenceBar :value="row.confidence" />
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="时间" />
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button type="primary" link @click="$router.push(`/violations/${row.id}`)">
                  查看
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover" class="recent-card">
          <template #header>
            <div class="card-header">
              <span>实时违规记录</span>
              <el-button type="primary" link @click="$router.push('/violations')">
                查看全部 <el-icon><ArrowRight /></el-icon>
              </el-button>
            </div>
          </template>
          <div class="scroll-list">
            <div
              v-for="item in recentList"
              :key="item.id"
              class="scroll-item"
              @click="$router.push(`/violations/${item.id}`)"
            >
              <el-image
                v-if="getThumbnail(item.image_path)"
                :src="getThumbnail(item.image_path)"
                class="scroll-thumb"
                fit="cover"
              />
              <div class="scroll-info">
                <div class="scroll-top">
                  <TypeTag :type="item.violation_type" :size="small" />
                  <span class="scroll-conf">{{ formatConfidence(item.confidence) }}</span>
                </div>
                <div class="scroll-time">{{ item.created_at }}</div>
              </div>
              <el-tag :type="getStatusTagType(item.status)" size="small">
                {{ getStatusLabel(item.status) }}
              </el-tag>
            </div>
            <div v-if="recentList.length === 0" class="empty-scroll">
              <el-empty description="暂无违规记录" :image-size="40" />
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { getStats, getList } from '../api'
import { formatDate, getTypeName } from '../utils/format'
import TypeTag from '../components/TypeTag.vue'
import ConfidenceBar from '../components/ConfidenceBar.vue'

const stats = ref({})
const pendingList = ref([])
const recentList = ref([])
const trendDays = ref(7)
const pieChartRef = ref(null)
const lineChartRef = ref(null)
const barChartRef = ref(null)
let pieChart = null
let lineChart = null
let barChart = null
let refreshTimer = null

onMounted(async () => {
  await nextTick()
  initCharts()
  await loadStats()
  await loadPendingList()
  await loadRecentList()
  
  refreshTimer = setInterval(() => {
    loadRecentList()
  }, 30000)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
  pieChart?.dispose()
  lineChart?.dispose()
  barChart?.dispose()
})

async function loadStats() {
  try {
    const res = await getStats()
    const byType = res.by_type || {}
    const byStatus = res.by_status || {}
    const byDate = res.by_date || {}

    const typeArray = Object.entries(byType).map(([type, count]) => ({
      violation_type: type,
      count
    }))

    const dateArray = Object.entries(byDate)
      .map(([date, count]) => ({ date, count }))
      .sort((a, b) => a.date.localeCompare(b.date))

    const todayStr = new Date().toISOString().slice(0, 10)
    const todayCount = byDate[todayStr] || 0

    const monthStr = todayStr.slice(0, 7)
    const thisMonth = Object.entries(byDate)
      .filter(([date]) => date.startsWith(monthStr))
      .reduce((sum, [, count]) => sum + count, 0)

    stats.value = {
      total: res.total_count || 0,
      today: todayCount,
      thisMonth,
      pending: byStatus.pending || 0,
      confirmed: byStatus.confirmed || 0,
      rejected: byStatus.rejected || 0,
      onlineDevices: res.online_devices || 0,
      by_type: typeArray,
      by_date: dateArray
    }

    updateCharts(typeArray, dateArray)
  } catch (err) {
    console.error('获取统计数据失败', err)
    stats.value = { total: 0, today: 0, thisMonth: 0, pending: 0, confirmed: 0, onlineDevices: 0, by_type: [], by_date: [] }
  }
}

async function loadPendingList() {
  try {
    const res = await getList({ page: 1, page_size: 5, status: 'pending' })
    pendingList.value = (res.items || []).map(item => ({
      ...item,
      created_at: formatDate(item.created_at)
    }))
  } catch (err) {
    console.error('获取待审核列表失败', err)
  }
}

async function loadRecentList() {
  try {
    const res = await getList({ page: 1, page_size: 10 })
    recentList.value = (res.items || []).map(item => ({
      ...item,
      created_at: formatDate(item.created_at)
    }))
  } catch (err) {
    console.error('获取最新列表失败', err)
  }
}

function updateCharts(typeArray, dateArray) {
  if (pieChart) {
    const pieData = typeArray.map(item => ({
      name: getTypeName(item.violation_type),
      value: item.count
    }))
    pieChart.setOption({
      series: [{ data: pieData }]
    })
  }

  if (lineChart) {
    lineChart.setOption({
      xAxis: { data: dateArray.map(item => item.date) },
      series: [{ data: dateArray.map(item => item.count) }]
    })
  }

  if (barChart) {
    const deviceData = stats.value.by_device || []
    const top10 = deviceData.slice(0, 10).map(d => ({
      name: d.device_name || d.device_id || '未知设备',
      value: d.count || 0
    }))
    
    barChart.setOption({
      xAxis: { data: top10.map(d => d.name) },
      series: [{ data: top10.map(d => d.value) }]
    })
  }
}

function initCharts() {
  if (pieChartRef.value) {
    pieChart = echarts.init(pieChartRef.value)
    pieChart.setOption({
      tooltip: { trigger: 'item' },
      legend: { bottom: 0 },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 2 },
        label: { show: true, fontSize: 12 },
        data: []
      }]
    })
  }

  if (lineChartRef.value) {
    lineChart = echarts.init(lineChartRef.value)
    lineChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: [], boundaryGap: false, axisLabel: { fontSize: 11 } },
      yAxis: { type: 'value', axisLabel: { fontSize: 11 } },
      series: [{ type: 'line', smooth: true, areaStyle: { opacity: 0.3 }, data: [], itemStyle: { color: '#1890ff' } }]
    })
  }

  if (barChartRef.value) {
    barChart = echarts.init(barChartRef.value)
    barChart.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: [], axisLabel: { fontSize: 10, rotate: 30 } },
      yAxis: { type: 'value', axisLabel: { fontSize: 11 } },
      series: [{ type: 'bar', data: [], itemStyle: { borderRadius: [4, 4, 0, 0], color: '#52c41a' } }]
    })
  }

  window.addEventListener('resize', () => {
    pieChart?.resize()
    lineChart?.resize()
    barChart?.resize()
  })
}

function getThumbnail(imagePath) {
  if (!imagePath) return ''
  const normalized = imagePath.replace(/\\/g, '/')
  const clean = normalized.replace(/^\/+/, '').replace(/^uploads\//, '')
  return '/uploads/' + clean
}

function formatConfidence(confidence) {
  if (confidence === null || confidence === undefined) return '-'
  return (confidence * 100).toFixed(1) + '%'
}

function getStatusTagType(status) {
  const map = { pending: 'warning', confirmed: 'success', rejected: 'info' }
  return map[status] || 'info'
}

function getStatusLabel(status) {
  const map = { pending: '待审核', confirmed: '已确认', rejected: '已驳回' }
  return map[status] || status
}
</script>

<style scoped lang="scss">
.dashboard {
  .stat-row {
    margin-bottom: 20px;
  }

  .stat-card {
    display: flex;
    align-items: center;
    padding: 20px;

    .stat-icon {
      width: 60px;
      height: 60px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-right: 16px;
      color: #fff;
    }

    .bg-blue { background: linear-gradient(135deg, #1890ff, #70b5ff); }
    .bg-orange { background: linear-gradient(135deg, #fa8c16, #ffb566); }
    .bg-purple { background: linear-gradient(135deg, #722ed1, #a371f7); }
    .bg-yellow { background: linear-gradient(135deg, #faad14, #ffc53d); }
    .bg-green { background: linear-gradient(135deg, #52c41a, #95d674); }
    .bg-cyan { background: linear-gradient(135deg, #13c2c2, #5cdbd3); }

    .stat-info {
      .stat-num {
        font-size: 32px;
        font-weight: 700;
        color: #333;
      }
      .stat-label {
        font-size: 14px;
        color: #999;
      }
    }
  }

  .chart-row {
    margin-bottom: 20px;
  }

  .chart-container {
    height: 250px;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .pending-card {
    :deep(.el-card__header) {
      padding: 16px 20px;
    }
  }

  .recent-card {
    :deep(.el-card__header) {
      padding: 16px 20px;
    }

    .scroll-list {
      max-height: 350px;
      overflow-y: auto;
      padding-right: 8px;

      &::-webkit-scrollbar {
        width: 4px;
      }

      &::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 2px;
      }

      &::-webkit-scrollbar-thumb {
        background: #c0c4cc;
        border-radius: 2px;
      }
    }

    .scroll-item {
      display: flex;
      align-items: center;
      padding: 12px 0;
      border-bottom: 1px solid #f5f5f5;
      cursor: pointer;
      transition: background 0.2s;

      &:hover {
        background: #fafafa;
      }

      &:last-child {
        border-bottom: none;
      }
    }

    .scroll-thumb {
      width: 50px;
      height: 50px;
      border-radius: 4px;
      margin-right: 12px;
    }

    .scroll-info {
      flex: 1;
      min-width: 0;

      .scroll-top {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 4px;
      }

      .scroll-conf {
        font-size: 12px;
        color: #909399;
      }

      .scroll-time {
        font-size: 12px;
        color: #909399;
      }
    }

    .empty-scroll {
      padding: 40px 0;
    }
  }
}
</style>