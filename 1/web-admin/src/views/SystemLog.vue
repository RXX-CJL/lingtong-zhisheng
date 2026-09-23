<template>
  <div class="system-log">
    <div class="log-header">
      <h2 class="page-title">
        <el-icon class="title-icon"><Document /></el-icon>
        系统日志（前端）
      </h2>
      <div class="title-sub">
        记录前端运行时状态：接口请求/错误、路由跳转、console 输出、JS 崩溃等。
        最多保留 {{ MAX }} 条，2MB 时自动截断。刷新页面不丢失。
      </div>
    </div>

    <!-- 工具栏 -->
    <el-card class="toolbar" shadow="never">
      <div class="toolbar-row">
        <el-select v-model="fLevel" placeholder="级别" clearable class="t-item" style="width:140px">
          <el-option v-for="lv in LEVEL_ORDER" :key="lv" :label="lv" :value="lv" />
        </el-select>
        <el-select v-model="fTag" placeholder="标签" clearable class="t-item" filterable style="width:160px">
          <el-option v-for="t in tagChoices" :key="t" :label="t" :value="t" />
        </el-select>
        <el-input v-model="fKeyword" placeholder="关键字（匹配 message）" clearable class="t-item flex1" />
        <el-select v-model="fLimit" placeholder="条数" class="t-item" style="width:130px">
          <el-option :value="100" label="最近 100 条" />
          <el-option :value="500" label="最近 500 条" />
          <el-option :value="1000" label="最近 1000 条" />
          <el-option :value="0" label="全部" />
        </el-select>
        <el-button @click="refresh" :icon="Refresh">刷新</el-button>
        <el-button @click="doExport" :icon="Download" type="primary">导出 JSON</el-button>
        <el-popconfirm
          title="确认清空全部前端日志？（不可恢复）"
          confirm-button-text="清空"
          cancel-button-text="取消"
          @confirm="doClear"
        >
          <template #reference>
            <el-button :icon="Delete" type="danger">清空</el-button>
          </template>
        </el-popconfirm>
      </div>
      <div class="stats-row">
        <el-tag type="info">总数 {{ totalSize }}</el-tag>
        <el-tag type="primary">筛选后 {{ filtered.length }}</el-tag>
        <el-tag type="danger">ERROR/FATAL {{ errorCount }}</el-tag>
        <el-tag type="warning">WARN {{ warnCount }}</el-tag>
        <el-tag v-if="storageBytes" :type="storageBytes > 1.5e6 ? 'danger' : 'success'">
          localStorage 大小 {{ formatKB(storageBytes) }}
        </el-tag>
        <el-tag type="info" effect="plain" v-if="tailOfStorage">
          落盘状态：{{ tailOfStorage.savedAt }} / {{ tailOfStorage.items }} 条
        </el-tag>
        <el-spacer />
        <el-switch
          v-model="autoRefresh"
          active-text="自动刷新(2s)"
          inactive-text="手动"
        />
      </div>
    </el-card>

    <!-- 列表 -->
    <el-card class="list-card" shadow="never">
      <el-empty v-if="filtered.length === 0" description="没有符合条件的日志" />
      <div v-else class="log-list">
        <div
          v-for="item in filtered"
          :key="item.seq"
          class="log-item"
          :class="'lv-' + item.level.toLowerCase()"
        >
          <div class="log-meta">
            <el-tag size="small" class="lv-tag" :type="levelTypeMap[item.level] || 'info'">{{ item.level }}</el-tag>
            <el-tag size="small" effect="plain" class="tag-tag" v-if="item.tag">{{ item.tag }}</el-tag>
            <span class="seq">#{{ item.seq }}</span>
            <span class="time">{{ item.t }}</span>
            <span class="url" v-if="item.url">{{ item.url }}</span>
          </div>
          <div class="log-msg">
            {{ item.message }}
          </div>
          <div class="log-extra" v-if="item.err || item.extra">
            <el-collapse v-if="item.err">
              <el-collapse-item title="错误详情 (Error)" name="err">
                <pre class="pre-block">{{ formatErr(item.err) }}</pre>
              </el-collapse-item>
            </el-collapse>
            <el-collapse v-if="item.extra">
              <el-collapse-item title="附加数据 (extra)" name="extra">
                <pre class="pre-block">{{ formatExtra(item.extra) }}</pre>
              </el-collapse-item>
            </el-collapse>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Download, Delete, Document } from '@element-plus/icons-vue'
import logger from '../utils/logger'

const MAX = 2000
const LEVEL_ORDER = logger.LEVEL_ORDER

const fLevel = ref(null)
const fTag = ref(null)
const fKeyword = ref('')
const fLimit = ref(500)
const autoRefresh = ref(true)

const items = ref([])
const totalSize = ref(0)
const storageBytes = ref(0)
const tailOfStorage = ref(null)

let timer = null

const levelTypeMap = {
  DEBUG: 'info',
  INFO:  'success',
  WARN:  'warning',
  ERROR: 'danger',
  FATAL: 'danger',
}

const tagChoices = computed(() => {
  const s = new Set()
  items.value.forEach(x => x.tag && s.add(x.tag))
  return Array.from(s).sort()
})

const filtered = computed(() => {
  let list = items.value.slice()
  if (fLevel.value) {
    const min = logger.LEVELS[fLevel.value]
    if (Number.isFinite(min)) list = list.filter(x => (logger.LEVELS[x.level] || 0) >= min)
  }
  if (fTag.value) list = list.filter(x => x.tag === fTag.value)
  if (fKeyword.value) {
    const k = String(fKeyword.value).toLowerCase()
    list = list.filter(x =>
      (x.message || '').toLowerCase().includes(k) ||
      (x.tag || '').toLowerCase().includes(k) ||
      (x.err && (x.err.message || '').toLowerCase().includes(k))
    )
  }
  list.sort((a, b) => b.ms - a.ms)
  if (fLimit.value > 0 && list.length > fLimit.value) list = list.slice(0, fLimit.value)
  return list
})

const errorCount = computed(() =>
  filtered.value.filter(x => x.level === 'ERROR' || x.level === 'FATAL').length
)
const warnCount = computed(() =>
  filtered.value.filter(x => x.level === 'WARN').length
)

function refresh() {
  items.value = logger.query({ limit: null })   // 全部，按倒序
  totalSize.value = logger.size()
  // 估算 localStorage 占用
  try {
    const raw = localStorage.getItem('zt_frontend_logs_v1') || ''
    storageBytes.value = raw.length * 2  // UTF-16 近似
    if (raw) {
      const parsed = JSON.parse(raw)
      tailOfStorage.value = {
        savedAt: parsed.savedAt || '',
        items: Array.isArray(parsed.items) ? parsed.items.length : 0
      }
    } else {
      tailOfStorage.value = null
    }
  } catch (_) {
    storageBytes.value = 0
    tailOfStorage.value = null
  }
}

function doExport() {
  const ok = logger.exportAsJsonDownload()
  ElMessage[ok ? 'success' : 'error'](ok ? '导出已开始下载' : '导出失败')
}
function doClear() {
  logger.clear()
  refresh()
  ElMessage.success('已清空前端日志')
}
function formatErr(err) {
  if (!err) return ''
  return `${err.name || 'Error'}: ${err.message || ''}\n${err.stack || ''}`
}
function formatExtra(e) {
  try { return JSON.stringify(e, null, 2) }
  catch (_) { return String(e) }
}
function formatKB(bytes) {
  if (!Number.isFinite(bytes)) return '0 KB'
  if (bytes > 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
  return (bytes / 1024).toFixed(1) + ' KB'
}

// 自动刷新
watch(autoRefresh, (v) => {
  if (v) {
    if (!timer) timer = setInterval(refresh, 2000)
  } else {
    if (timer) { clearInterval(timer); timer = null }
  }
}, { immediate: true })

onMounted(refresh)
onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<style scoped lang="scss">
.system-log {
  padding: 20px;
  .log-header {
    margin-bottom: 16px;
    .page-title {
      font-size: 22px;
      margin: 0 0 6px 0;
      display: flex; align-items: center; gap: 8px;
      .title-icon { color: #409EFF; }
    }
    .title-sub { color: #909399; font-size: 13px; }
  }

  .toolbar {
    margin-bottom: 16px;
    .toolbar-row {
      display: flex; gap: 10px; align-items: center; flex-wrap: wrap;
      .t-item { }
      .flex1 { min-width: 280px; }
    }
    .stats-row {
      margin-top: 14px;
      display: flex; gap: 8px; align-items: center; flex-wrap: wrap;
    }
  }

  .log-list { max-height: calc(100vh - 360px); overflow-y: auto; }
  .log-item {
    padding: 10px 12px;
    margin-bottom: 8px;
    border-left: 4px solid #DCDFE6;
    background: #FAFAFA;
    border-radius: 4px;
    font-size: 13px;
    &.lv-debug { border-left-color: #909399; background: #FAFBFC; }
    &.lv-info  { border-left-color: #67C23A; }
    &.lv-warn  { border-left-color: #E6A23C; background: #FDF6EC; }
    &.lv-error { border-left-color: #F56C6C; background: #FEF0F0; }
    &.lv-fatal { border-left-color: #C00000; background: #FFEFEF; color: #330000; }

    .log-meta {
      display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
      margin-bottom: 4px;
      .lv-tag { font-weight: 600; }
      .seq { color: #C0C4CC; font-family: monospace; font-size: 12px; }
      .time { color: #909399; font-family: monospace; font-size: 12px; }
      .url { color: #909399; font-size: 12px; }
    }
    .log-msg { color: #303133; word-break: break-word; line-height: 1.5; }
    .log-extra { margin-top: 8px; }
    .pre-block {
      background: #1e1e1e;
      color: #d4d4d4;
      padding: 10px;
      border-radius: 4px;
      font-size: 12px;
      line-height: 1.5;
      overflow: auto;
      max-height: 320px;
      font-family: Consolas, "Courier New", monospace;
    }
  }
}
</style>
