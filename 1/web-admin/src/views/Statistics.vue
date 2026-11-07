<template>
  <div class="statistics">
    <el-tabs v-model="activeTab" type="card" class="main-tabs">
      <el-tab-pane label="综合统计" name="overview">
    <!-- 日期筛选 -->
    <el-card shadow="hover" class="filter-card">
      <el-form :inline="true">
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            @change="loadData"
          />
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 图表区 -->
    <el-row :gutter="20" class="chart-row">
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>违规类型统计</span>
            </div>
          </template>
          <div ref="barChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>审核状态分布</span>
            </div>
          </template>
          <div ref="pieChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>每日趋势</span>
            </div>
          </template>
          <div ref="areaChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 详细数据表格 -->
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>详细数据</span>
        </div>
      </template>
      <el-table :data="tableData" stripe style="width: 100%">
        <el-table-column prop="date" label="日期" width="160" />
        <el-table-column prop="count" label="当日违规数" />
      </el-table>
    </el-card>
      </el-tab-pane>
      <el-tab-pane label="协作统计" name="collab">
        <CollabStats />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getStatisticsOverview, getDailyStats, getTypeDistribution } from '../api'
import { getTypeName, getStatusName } from '../utils/format'
import { registerZtTheme, ZT_THEME_NAME } from '../utils/echarts-theme'
import CollabStats from './CollabStats.vue'

const activeTab = ref('overview')

const dateRange = ref([])
const tableData = ref([])
const barChartRef = ref(null)
const pieChartRef = ref(null)
const areaChartRef = ref(null)

let barChart = null
let pieChart = null
let areaChart = null

onMounted(async () => {
  await nextTick()
  initCharts()
  await loadData()
})

async function loadData() {
  try {
    // 获取统计概览（类型分布、状态分布）
    const overviewRes = await getStatisticsOverview()
    const overview = overviewRes.data || {}
    
    const byTypeRaw = (overview.by_type || []).reduce((acc, item) => {
      acc[item.violation_type] = item.count
      return acc
    }, {})
    
    const byStatusRaw = (overview.by_status || []).reduce((acc, item) => {
      acc[item.status] = item.count
      return acc
    }, {})

    // 获取每日趋势
    const days = dateRange.value.length ? Math.min(90, Math.floor((new Date(dateRange.value[1]) - new Date(dateRange.value[0])) / (1000 * 60 * 60 * 24)) + 1) : 7
    const dailyRes = await getDailyStats(days)
    const byDateRaw = (dailyRes.data?.daily || []).reduce((acc, item) => {
      acc[item.date] = item.count
      return acc
    }, {})

    // 类型统计：字典 → 数组
    const byType = Object.entries(byTypeRaw).map(([type, count]) => ({
      violation_type: type,
      count
    }))

    // 日期统计：字典 → 数组并排序
    const byDate = Object.entries(byDateRaw)
      .map(([date, count]) => ({ date, count }))
      .sort((a, b) => a.date.localeCompare(b.date))

    // 按类型柱状图
    barChart?.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: byType.map(item => getTypeName(item.violation_type)) },
      yAxis: { type: 'value' },
      series: [{ type: 'bar', data: byType.map(item => item.count) }]
    })

    // 状态分布饼图
    pieChart?.setOption({
      tooltip: { trigger: 'item' },
      legend: { bottom: 0 },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        data: [
          { name: '待审核', value: byStatusRaw.pending || 0 },
          { name: '已确认', value: byStatusRaw.confirmed || 0 },
          { name: '已驳回', value: byStatusRaw.rejected || 0 }
        ]
      }]
    })

    // 每日趋势面积图
    areaChart?.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: byDate.map(item => item.date) },
      yAxis: { type: 'value' },
      series: [{
        type: 'line',
        smooth: true,
        areaStyle: { opacity: 0.3 },
        data: byDate.map(item => item.count)
      }]
    })

    // 详细数据表格
    tableData.value = byDate
  } catch (err) {
    console.error('获取统计数据失败', err)
  }
}

function initCharts() {
  registerZtTheme(echarts)
  if (barChartRef.value) {
    barChart = echarts.init(barChartRef.value, ZT_THEME_NAME)
  }
  if (pieChartRef.value) {
    pieChart = echarts.init(pieChartRef.value, ZT_THEME_NAME)
  }
  if (areaChartRef.value) {
    areaChart = echarts.init(areaChartRef.value, ZT_THEME_NAME)
  }

  window.addEventListener('resize', () => {
    barChart?.resize()
    pieChart?.resize()
    areaChart?.resize()
  })
}
</script>

<style scoped lang="scss">
.statistics {
  .filter-card {
    margin-bottom: 20px;
  }

  .chart-row {
    margin-bottom: 20px;
  }

  .chart-container {
    height: 300px;
  }

  .card-header {
    font-weight: 600;
  }
}
</style>