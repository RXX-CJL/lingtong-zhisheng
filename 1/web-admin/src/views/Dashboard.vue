<template>
  <div class="dashboard">
    <!-- 统计卡片（2026-10-03 由 DSH 重构：主次分明 + 横向布局，消除"6 个相同方块"的默认感） -->
    <el-row :gutter="16" class="stat-row">
      <!-- 主卡：总违规数（占 2 列，视觉权重最高） -->
      <el-col :xs="24" :sm="24" :md="8" :lg="9">
        <div class="zt-kpi zt-kpi--hero">
          <div class="zt-kpi__head">
            <span class="zt-kpi__label">总违规数</span>
            <span class="zt-kpi__icon kpi-icon--primary">
              <el-icon size="18"><Document /></el-icon>
            </span>
          </div>
          <div class="zt-kpi__value zt-kpi-value">{{ stats.total || 0 }}</div>
          <div class="zt-kpi__foot">
            <span class="kpi-dot kpi-dot--success"></span>已确认 {{ stats.confirmed || 0 }}
          </div>
        </div>
      </el-col>

      <!-- 次卡：4 张紧凑横向卡 -->
      <el-col :xs="12" :sm="12" :md="8" :lg="3">
        <div class="zt-kpi">
          <div class="zt-kpi__row">
            <span class="zt-kpi__icon kpi-icon--warning">
              <el-icon size="16"><Plus /></el-icon>
            </span>
            <span class="zt-kpi__label">今日新增</span>
          </div>
          <div class="zt-kpi__value zt-kpi-value">{{ stats.today || 0 }}</div>
        </div>
      </el-col>

      <el-col :xs="12" :sm="12" :md="8" :lg="3">
        <div class="zt-kpi">
          <div class="zt-kpi__row">
            <span class="zt-kpi__icon kpi-icon--info">
              <el-icon size="16"><Calendar /></el-icon>
            </span>
            <span class="zt-kpi__label">本月违规</span>
          </div>
          <div class="zt-kpi__value zt-kpi-value">{{ stats.thisMonth || 0 }}</div>
        </div>
      </el-col>

      <el-col :xs="12" :sm="12" :md="8" :lg="3">
        <div class="zt-kpi">
          <div class="zt-kpi__row">
            <span class="zt-kpi__icon kpi-icon--pending">
              <el-icon size="16"><Clock /></el-icon>
            </span>
            <span class="zt-kpi__label">待审核</span>
          </div>
          <div class="zt-kpi__value zt-kpi-value">{{ stats.pending || 0 }}</div>
        </div>
      </el-col>

      <el-col :xs="12" :sm="12" :md="8" :lg="3">
        <div class="zt-kpi">
          <div class="zt-kpi__row">
            <span class="zt-kpi__icon kpi-icon--success">
              <el-icon size="16"><CircleCheck /></el-icon>
            </span>
            <span class="zt-kpi__label">已确认</span>
          </div>
          <div class="zt-kpi__value zt-kpi-value">{{ stats.confirmed || 0 }}</div>
        </div>
      </el-col>

      <el-col :xs="12" :sm="12" :md="8" :lg="3">
        <div class="zt-kpi">
          <div class="zt-kpi__row">
            <span class="zt-kpi__icon kpi-icon--online">
              <el-icon size="16"><Monitor /></el-icon>
            </span>
            <span class="zt-kpi__label">设备在线</span>
          </div>
          <div class="zt-kpi__value zt-kpi-value">{{ stats.onlineDevices || 0 }}</div>
        </div>
      </el-col>
    </el-row>
    <!-- 旧版 KPI 卡片已由上方结构替代（2026-10-03 由 DSH 重构） -->

    <!-- 图表区域（2026-10-23 由 DSH 改造）
         类型分布：环形 -> 横向排序条形（7 分类塞进 400x250 的环形是几何必然重叠，调参救不回来）
         状态分布：替换原「设备违规排行 TOP10」空壳卡（后端从未提供该字段） -->
    <el-row :gutter="20" class="chart-row">
      <el-col :span="8">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <div class="card-header__text">
                <span class="card-title">违规类型分布</span>
                <span class="card-subtitle">按数量降序</span>
              </div>
            </div>
          </template>
          <div ref="typeBarChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <div class="card-header__text">
                <span class="card-title">违规趋势</span>
                <span class="card-subtitle">按日统计</span>
              </div>
              <el-select v-model="trendDays" size="small" style="width: 92px" @change="loadStats">
                <el-option label="近7天" :value="7" />
                <el-option label="近30天" :value="30" />
              </el-select>
            </div>
          </template>
          <div ref="lineChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <div class="card-header__text">
                <span class="card-title">审核状态分布</span>
                <span class="card-subtitle">待审核 / 已确认 / 已驳回</span>
              </div>
            </div>
          </template>
          <div ref="statusPieChartRef" class="chart-container chart-container--pie"></div>
          <!-- 小切片无法直标（2 起 vs 3 起几何重叠），用固定图例保证每个状态都可读 -->
          <ul class="status-legend">
            <li v-for="item in statusLegend" :key="item.key" class="status-legend__item">
              <span class="status-legend__dot" :style="{ background: item.color }"></span>
              <span class="status-legend__name">{{ item.name }}</span>
              <span class="status-legend__val">{{ item.value }}</span>
            </li>
          </ul>
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
import { ref, computed, onMounted, nextTick, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { getStats, getList } from '../api'
import { formatDate, getTypeName, TYPE_FALLBACK_COLOR } from '../utils/format'
import { registerZtTheme, ZT_THEME_NAME } from '../utils/echarts-theme'
import TypeTag from '../components/TypeTag.vue'
import ConfidenceBar from '../components/ConfidenceBar.vue'

const stats = ref({})
const pendingList = ref([])
const recentList = ref([])
const trendDays = ref(7)
const typeBarChartRef = ref(null)
const lineChartRef = ref(null)
const statusPieChartRef = ref(null)
let typeBarChart = null
let lineChart = null
let statusPieChart = null
let refreshTimer = null

// 状态分布配色：语义固定，不随主题色板漂移
const STATUS_COLOR = {
  pending: '#F2C14E',
  confirmed: '#16A34A',
  rejected: '#98A2B3'
}
const STATUS_LABEL = {
  pending: '待审核',
  confirmed: '已确认',
  rejected: '已驳回'
}
const STATUS_ORDER = ['pending', 'confirmed', 'rejected']

// 环形卡下方的固定图例（3 项，与环形同序同色）
const statusLegend = computed(() => {
  const m = stats.value.by_status || {}
  return STATUS_ORDER
    .filter(s => (m[s] || 0) > 0)
    .map(s => ({ key: s, name: STATUS_LABEL[s], value: m[s], color: STATUS_COLOR[s] }))
})

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
  typeBarChart?.dispose()
  lineChart?.dispose()
  statusPieChart?.dispose()
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
      by_date: dateArray,
      by_status: byStatus
    }

    updateCharts(typeArray, dateArray, byStatus)
  } catch (err) {
    console.error('获取统计数据失败', err)
    stats.value = { total: 0, today: 0, thisMonth: 0, pending: 0, confirmed: 0, onlineDevices: 0, by_type: [], by_date: [], by_status: {} }
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

// 类型条形图取前 N 类，其余合并「其他」——
// 卡片只有 260px，7 行最舒服；后端将来涨到 11 类也不会撑破版式
const TYPE_TOP_N = 7

// 条形图百分比标签的分母：数据刷新时更新，formatter 闭包读取
let typeTotal = 0

// 占比格式化：有量但四舍五入为 0 时写 <0.1%，不让 1 起显示成 0%
function formatShare(value, total) {
  if (!total || total <= 0) return ''
  const pct = Math.round((value / total) * 1000) / 10
  if (pct === 0 && value > 0) return '<0.1%'
  return pct + '%'
}

function buildTypeRankData(typeArray) {
  const sorted = [...typeArray].sort((a, b) => b.count - a.count)
  const top = sorted.slice(0, TYPE_TOP_N)
  const rest = sorted.slice(TYPE_TOP_N)
  const restCount = rest.reduce((sum, item) => sum + (item.count || 0), 0)

  const rows = top.map(item => ({
    type: item.violation_type,
    name: getTypeName(item.violation_type),
    value: item.count || 0,
    count: item.count || 0
  }))

  if (restCount > 0) {
    rows.push({
      type: '__other__',
      name: '其他',
      value: restCount,
      count: restCount
    })
  }
  return rows
}

// 排名渐变：第 1 名最深、末位最浅，颜色表达"量级次序"而非"类目身份"
// 依据 _ui_optimization_verdict.md §2.3 裁决：条形已编码大小，再上 7 彩会造成颜色竞争注意力
const RANK_GRADIENT = ['#1D4ED8', '#3B6BE0', '#5B8DB8', '#7FA3C6', '#A3B9D4', '#C2D1E3', '#DCE4EF']
const HIGHLIGHT_COLOR = { red_light: '#D14343' }   // 闯红灯唯一高亮

// 名次即数组下标（rows 已降序），高亮类目原样覆盖颜色，不影响其他行的名次取色
function rankColor(row, index) {
  if (HIGHLIGHT_COLOR[row.type]) return HIGHLIGHT_COLOR[row.type]
  if (row.type === '__other__') return TYPE_FALLBACK_COLOR
  return RANK_GRADIENT[Math.min(index, RANK_GRADIENT.length - 1)]
}

function updateCharts(typeArray, dateArray, byStatus) {
  if (typeBarChart) {
    const rows = buildTypeRankData(typeArray)
    typeTotal = rows.reduce((s, r) => s + r.value, 0)
    // yAxis 是 category，必须给数据；inverse:true 让首项（最大值）置顶
    typeBarChart.setOption({
      yAxis: { data: rows.map(r => r.name) },
      series: [{
        data: rows.map((r, i) => ({
          value: r.value,
          count: r.count,
          itemStyle: { color: rankColor(r, i) }
        }))
      }]
    })
  }

  if (lineChart) {
    lineChart.setOption({
      xAxis: { data: dateArray.map(item => item.date) },
      series: [{ data: dateArray.map(item => item.count) }]
    })
  }

  if (statusPieChart) {
    const statusMap = byStatus || {}
    const all = STATUS_ORDER
      .filter(s => (statusMap[s] || 0) > 0)
      .map(s => ({ key: s, name: STATUS_LABEL[s], value: statusMap[s], color: STATUS_COLOR[s] }))
    // 兜底：后端若给出未知状态，也不让环形整体空白
    Object.keys(statusMap).forEach(s => {
      if (!STATUS_ORDER.includes(s) && statusMap[s] > 0) {
        all.push({ key: s, name: getStatusLabel(s), value: statusMap[s], color: TYPE_FALLBACK_COLOR })
      }
    })
    const statusTotal = all.reduce((s, d) => s + d.value, 0)

    // 数值统一由卡片下方固定图例承载（顺序/配色与环形一致），
    // 环内不再直标 —— 3 个状态里两个只有个位数，直标必然叠字
    const pieData = all.map(d => ({
      name: d.name,
      value: d.value,
      itemStyle: { color: d.color }
    }))

    statusPieChart.setOption({
      title: { text: String(statusTotal) },
      series: [{ data: pieData }]
    })
  }
}

function initCharts() {
  // 注册亮色主题（决策 3 选 A）；主题对象幂等注册，重复调用安全
  registerZtTheme(echarts)

  // ① 违规类型分布：横向排序条形图（参数见 _ui_optimization_verdict.md §2.5）
  if (typeBarChartRef.value) {
    typeBarChart = echarts.init(typeBarChartRef.value, ZT_THEME_NAME)
    typeBarChart.setOption({
      tooltip: {
        trigger: 'item',
        formatter: (p) => `${p.name}<br/>${p.data.count} 起（${p.percent ?? ''}）`
      },
      grid: { left: 70, right: 55, top: 8, bottom: 8, containLabel: true },
      xAxis: { type: 'value', show: false },
      yAxis: {
        type: 'category',
        inverse: true,                 // 最大值置顶：ECharts y 类目轴默认自下而上
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { fontSize: 12, color: '#606266', margin: 8 },
        data: []
      },
      series: [{
        type: 'bar',
        barWidth: 16,
        itemStyle: { borderRadius: [0, 3, 3, 0] },
        label: {
          show: true,
          position: 'right',
          distance: 6,
          fontSize: 12,
          color: '#606266',
          // 分母是全部类型的总数（含被并入「其他」的部分），由 updateCharts 更新
          formatter: (p) => formatShare(p.value, typeTotal)
        },
        data: []
      }]
    })
  }

  if (lineChartRef.value) {
    lineChart = echarts.init(lineChartRef.value, ZT_THEME_NAME)
    lineChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 4, right: 12, top: 16, bottom: 4, containLabel: true },
      xAxis: { type: 'category', data: [], boundaryGap: false, axisLabel: { fontSize: 11, hideOverlap: true } },
      yAxis: { type: 'value', axisLabel: { fontSize: 11 } },
      series: [{
        type: 'line',
        smooth: true,
        symbolSize: 5,
        areaStyle: { opacity: 0.16 },
        data: [],
        itemStyle: { color: '#1D4ED8' }
      }]
    })
  }

  // ② 审核状态分布：环形图（3 分类落在设计库"≤5 分类"合规区）
  if (statusPieChartRef.value) {
    statusPieChart = echarts.init(statusPieChartRef.value, ZT_THEME_NAME)
    statusPieChart.setOption({
      // 环心总数：3 个切片加起来要心算，直接把总量放中心
      title: {
        text: '0',
        subtext: '总计',
        left: 'center',
        top: '38%',
        textAlign: 'center',
        textStyle: { fontSize: 22, fontWeight: 600, color: '#101828' },
        subtextStyle: { fontSize: 12, color: '#98A2B3' }
      },
      tooltip: { trigger: 'item', formatter: (p) => `${p.name}　${p.value} 起` },
      // 不设 ECharts legend：数值改由卡片下方 HTML 图例承载（见 template .status-legend）
      series: [{
        type: 'pie',
        radius: ['44%', '64%'],
        center: ['50%', '52%'],
        avoidLabelOverlap: true,
        // by_status 极度倾斜（2695 / 2 / 3）：minAngle 把两个极小片撑到可见角度，
        // 代价是环形不再严格等比 —— 但直接标了数值，读数是准的
        minAngle: 10,
        itemStyle: { borderColor: '#FFFFFF', borderWidth: 2, borderRadius: 3 },
        label: { show: false },
        labelLine: { show: false },
        data: []
      }]
    })
  }

  window.addEventListener('resize', () => {
    typeBarChart?.resize()
    lineChart?.resize()
    statusPieChart?.resize()
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

  /* 旧版 .stat-card 样式已随模板一起删除（2026-10-23）*/

  .chart-row {
    margin-bottom: 20px;
  }

  /* F6：250 -> 260，给 7 行 × 28-30px 留余量 */
  .chart-container {
    height: 260px;
    width: 100%;
  }

  /* 环形卡要腾出图例高度，否则三张卡不等高 */
  .chart-container--pie {
    height: 196px;
  }

  .status-legend {
    list-style: none;
    margin: 0;
    padding: 0 6px;
    display: flex;
    justify-content: center;
    gap: 18px;
    border-top: 1px solid #F0F2F5;
    padding-top: 10px;

    &__item {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      color: #475467;
    }

    &__dot {
      width: 8px;
      height: 8px;
      border-radius: 2px;
      flex: none;
    }

    &__val {
      font-family: var(--zt-font-mono);
      font-variant-numeric: tabular-nums;
      font-weight: 600;
      color: #101828;
    }
  }

  /* 卡片标题区：主标题 + 辅助说明，建立字号层级 */
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
  }

  .card-header__text {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }

  .card-title {
    font-size: 15px;
    font-weight: 600;
    color: #101828;
    line-height: 1.3;
  }

  .card-subtitle {
    font-size: 12px;
    color: #98A2B3;
    line-height: 1.3;
  }

  /* 图表卡：与 KPI 卡统一圆角/描边/阴影语言 */
  :deep(.chart-card) {
    border-radius: 12px;
    border-color: #E4E7EC;
    transition: box-shadow 180ms ease, border-color 180ms ease;

    &:hover {
      border-color: #BFD3FE;
    }

    .el-card__header {
      padding: 14px 18px;
      border-bottom: 1px solid #F0F2F5;
    }

    .el-card__body {
      padding: 8px 12px 10px;
    }
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