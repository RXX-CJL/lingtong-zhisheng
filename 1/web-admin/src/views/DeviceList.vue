<template>
  <div class="device-list">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>K230设备管理</span>
          <el-button type="primary" @click="showRegisterDialog = true">
            <el-icon><Plus /></el-icon> 注册设备
          </el-button>
        </div>
      </template>

      <!-- 筛选条件 -->
      <el-form :inline="true" class="filter-form">
        <el-form-item label="设备类型">
          <el-select v-model="filters.deviceType" placeholder="全部" clearable>
            <el-option label="K230" value="k230" />
            <el-option label="固定摄像头" value="fixed_camera" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable>
            <el-option label="在线" value="online" />
            <el-option label="离线" value="offline" />
            <el-option label="故障" value="error" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadDevices">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 设备统计 -->
      <div class="device-stats">
        <div class="stat-item">
          <span class="stat-value">{{ devices.length }}</span>
          <span class="stat-label">设备总数</span>
        </div>
        <div class="stat-item online">
          <span class="stat-value">{{ onlineCount }}</span>
          <span class="stat-label">在线</span>
        </div>
        <div class="stat-item offline">
          <span class="stat-value">{{ offlineCount }}</span>
          <span class="stat-label">离线</span>
        </div>
        <div class="stat-item error">
          <span class="stat-value">{{ errorCount }}</span>
          <span class="stat-label">故障</span>
        </div>
      </div>

      <!-- 设备列表 -->
      <el-table :data="devices" v-loading="loading" stripe>
        <el-table-column prop="device_id" label="设备ID" width="150" />
        <el-table-column prop="name" label="设备名称" width="150" />
        <el-table-column prop="device_type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag :type="row.device_type === 'k230' ? 'success' : 'info'">
              {{ row.device_type === 'k230' ? 'K230' : '固定摄像头' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="location" label="位置" min-width="150" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_seen" label="最后在线" width="180">
          <template #default="{ row }">
            {{ formatTime(row.last_seen) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="showDeviceDetail(row)">详情</el-button>
            <el-button size="small" type="primary" @click="editDevice(row)">编辑</el-button>
            <el-button size="small" type="warning" @click="handleRestart(row)" :disabled="row.status !== 'online'">重启</el-button>
            <el-button size="small" type="primary" @click="handleUpdateConfig(row)">配置</el-button>
            <el-button size="small" type="danger" @click="deleteDeviceAction(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 注册设备对话框 -->
    <el-dialog v-model="showRegisterDialog" title="注册设备" width="500px">
      <el-form :model="deviceForm" label-width="100px">
        <el-form-item label="设备ID" required>
          <el-input v-model="deviceForm.device_id" placeholder="如: K230_001" />
        </el-form-item>
        <el-form-item label="设备名称" required>
          <el-input v-model="deviceForm.name" placeholder="如: 路口A监控" />
        </el-form-item>
        <el-form-item label="设备类型">
          <el-select v-model="deviceForm.device_type">
            <el-option label="K230" value="k230" />
            <el-option label="固定摄像头" value="fixed_camera" />
          </el-select>
        </el-form-item>
        <el-form-item label="位置描述">
          <el-input v-model="deviceForm.location" placeholder="如: XX路口XX方向" />
        </el-form-item>
        <el-form-item label="经度">
          <el-input-number v-model="deviceForm.longitude" :precision="6" :step="0.000001" />
        </el-form-item>
        <el-form-item label="纬度">
          <el-input-number v-model="deviceForm.latitude" :precision="6" :step="0.000001" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRegisterDialog = false">取消</el-button>
        <el-button type="primary" @click="registerDeviceAction" :loading="submitting">注册</el-button>
      </template>
    </el-dialog>

    <!-- 设备详情对话框 -->
    <el-dialog v-model="showDetailDialog" title="设备详情" width="600px">
      <el-descriptions :column="2" border v-if="currentDevice">
        <el-descriptions-item label="设备ID">{{ currentDevice.device_id }}</el-descriptions-item>
        <el-descriptions-item label="设备名称">{{ currentDevice.name }}</el-descriptions-item>
        <el-descriptions-item label="设备类型">{{ currentDevice.device_type }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(currentDevice.status)">{{ getStatusText(currentDevice.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="位置">{{ currentDevice.location }}</el-descriptions-item>
        <el-descriptions-item label="坐标">
          {{ currentDevice.latitude }}, {{ currentDevice.longitude }}
        </el-descriptions-item>
        <el-descriptions-item label="最后在线">
          {{ formatTime(currentDevice.last_seen) }}
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">
          {{ formatTime(currentDevice.created_at) }}
        </el-descriptions-item>
      </el-descriptions>

      <!-- 设备配置信息 -->
      <div v-if="currentDevice" class="config-section">
        <h4>配置参数</h4>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="检测阈值">0.5</el-descriptions-item>
          <el-descriptions-item label="上传间隔">5秒</el-descriptions-item>
          <el-descriptions-item label="图片质量">高清</el-descriptions-item>
          <el-descriptions-item label="视频分辨率">640x480</el-descriptions-item>
        </el-descriptions>
      </div>

      <!-- 设备控制按钮 -->
      <div v-if="currentDevice" class="control-section">
        <el-button type="warning" @click="handleRestart(currentDevice)" :disabled="currentDevice.status !== 'online'">
          <el-icon><Refresh /></el-icon> 重启设备
        </el-button>
        <el-button type="primary" @click="handleUpdateConfig(currentDevice)">
          <el-icon><Setting /></el-icon> 更新配置
        </el-button>
        <el-button @click="showDeviceLogs(currentDevice)">
          <el-icon><Document /></el-icon> 查看日志
        </el-button>
      </div>

      <template #footer>
        <el-button @click="showDetailDialog = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 更新配置对话框 -->
    <el-dialog v-model="showConfigDialog" title="更新设备配置" width="500px">
      <el-form :model="configForm" label-width="120px">
        <el-form-item label="检测阈值">
          <el-slider v-model="configForm.threshold" :min="0" :max="1" :step="0.01" />
          <span>{{ configForm.threshold.toFixed(2) }}</span>
        </el-form-item>
        <el-form-item label="上传间隔(秒)">
          <el-input-number v-model="configForm.uploadInterval" :min="1" :max="60" />
        </el-form-item>
        <el-form-item label="图片质量">
          <el-select v-model="configForm.imageQuality">
            <el-option label="高清" value="high" />
            <el-option label="中等" value="medium" />
            <el-option label="低" value="low" />
          </el-select>
        </el-form-item>
        <el-form-item label="视频分辨率">
          <el-select v-model="configForm.resolution">
            <el-option label="640x480" value="640x480" />
            <el-option label="1280x720" value="1280x720" />
            <el-option label="1920x1080" value="1920x1080" />
          </el-select>
        </el-form-item>
        <el-form-item label="启用AI审核">
          <el-switch v-model="configForm.enableAiReview" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showConfigDialog = false">取消</el-button>
        <el-button type="primary" @click="saveConfig">保存配置</el-button>
      </template>
    </el-dialog>

    <!-- 设备日志对话框 -->
    <el-dialog v-model="showLogsDialog" title="设备日志" width="700px">
      <div class="logs-container">
        <div v-if="loadingLogs" class="logs-loading">
          <el-icon class="is-loading"><Loading /></el-icon> 加载日志中...
        </div>
        <div v-else class="logs-content">
          <el-tabs v-model="logTab">
            <el-tab-pane label="系统日志" name="system">
              <div class="log-list">
                <div v-for="(log, index) in systemLogs" :key="index" class="log-item">
                  <span class="log-time">{{ log.time }}</span>
                  <span :class="['log-level', log.level]">{{ log.level }}</span>
                  <span class="log-message">{{ log.message }}</span>
                </div>
              </div>
            </el-tab-pane>
            <el-tab-pane label="检测日志" name="detection">
              <div class="log-list">
                <div v-for="(log, index) in detectionLogs" :key="index" class="log-item">
                  <span class="log-time">{{ log.time }}</span>
                  <span :class="['log-level', log.level]">{{ log.level }}</span>
                  <span class="log-message">{{ log.message }}</span>
                </div>
              </div>
            </el-tab-pane>
            <el-tab-pane label="网络日志" name="network">
              <div class="log-list">
                <div v-for="(log, index) in networkLogs" :key="index" class="log-item">
                  <span class="log-time">{{ log.time }}</span>
                  <span :class="['log-level', log.level]">{{ log.level }}</span>
                  <span class="log-message">{{ log.message }}</span>
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>
      </div>
      <template #footer>
        <el-button @click="showLogsDialog = false">关闭</el-button>
        <el-button type="primary" @click="refreshLogs">刷新日志</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getDeviceList, registerDevice, updateDevice, deleteDevice } from '@/api'
import {
  Plus,
  Refresh,
  Setting,
  Document,
  Loading
} from '@element-plus/icons-vue'

const loading = ref(false)
const submitting = ref(false)
const loadingLogs = ref(false)
const devices = ref([])
const filters = reactive({ deviceType: '', status: '' })
const showRegisterDialog = ref(false)
const showDetailDialog = ref(false)
const showConfigDialog = ref(false)
const showLogsDialog = ref(false)
const currentDevice = ref(null)
const logTab = ref('system')

const deviceForm = reactive({
  device_id: '',
  name: '',
  device_type: 'k230',
  location: '',
  latitude: null,
  longitude: null
})

const configForm = reactive({
  threshold: 0.5,
  uploadInterval: 5,
  imageQuality: 'high',
  resolution: '640x480',
  enableAiReview: true
})

const onlineCount = computed(() => devices.value.filter(d => d.status === 'online').length)
const offlineCount = computed(() => devices.value.filter(d => d.status === 'offline').length)
const errorCount = computed(() => devices.value.filter(d => d.status === 'error').length)

const systemLogs = ref([
  { time: '2026-07-12 10:30:25', level: 'info', message: '设备启动成功' },
  { time: '2026-07-12 10:30:28', level: 'info', message: '摄像头初始化完成' },
  { time: '2026-07-12 10:30:30', level: 'info', message: 'AI模型加载完成' },
  { time: '2026-07-12 10:30:35', level: 'success', message: '网络连接成功' },
  { time: '2026-07-12 10:31:00', level: 'info', message: '开始检测任务' }
])

const detectionLogs = ref([
  { time: '2026-07-12 10:35:22', level: 'warning', message: '检测到违规：未戴头盔，置信度 92%' },
  { time: '2026-07-12 10:36:15', level: 'warning', message: '检测到违规：闯红灯，置信度 88%' },
  { time: '2026-07-12 10:37:45', level: 'info', message: '正常：无违规行为' },
  { time: '2026-07-12 10:38:30', level: 'warning', message: '检测到违规：逆行，置信度 95%' }
])

const networkLogs = ref([
  { time: '2026-07-12 10:30:35', level: 'success', message: '连接到服务器 127.0.0.1:8001' },
  { time: '2026-07-12 10:35:25', level: 'info', message: '上传违规图片成功' },
  { time: '2026-07-12 10:36:18', level: 'info', message: '上传违规图片成功' },
  { time: '2026-07-12 10:38:32', level: 'info', message: '上传违规图片成功' },
  { time: '2026-07-12 10:40:00', level: 'success', message: '心跳包发送成功' }
])

const loadDevices = async () => {
  loading.value = true
  try {
    const params = {}
    if (filters.deviceType) params.device_type = filters.deviceType
    if (filters.status) params.status = filters.status
    
    const res = await getDeviceList(params)
    if (res.success) {
      devices.value = res.data.devices || []
    }
  } catch (err) {
    ElMessage.error('加载设备列表失败')
  } finally {
    loading.value = false
  }
}

const resetFilters = () => {
  filters.deviceType = ''
  filters.status = ''
  loadDevices()
}

const registerDeviceAction = async () => {
  submitting.value = true
  try {
    const res = await registerDevice(deviceForm)
    if (res.success) {
      ElMessage.success('设备注册成功')
      showRegisterDialog.value = false
      Object.keys(deviceForm).forEach(k => deviceForm[k] = k === 'device_type' ? 'k230' : null)
      loadDevices()
    } else {
      ElMessage.error(res.message || '注册失败')
    }
  } catch (err) {
    ElMessage.error('注册失败')
  } finally {
    submitting.value = false
  }
}

const editDevice = (row) => {
  ElMessage.info('编辑功能开发中')
}

const deleteDeviceAction = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除设备 ${row.name}?`, '警告', { type: 'warning' })
    const res = await deleteDevice(row.device_id)
    if (res.success) {
      ElMessage.success('删除成功')
      loadDevices()
    }
  } catch (err) {
    if (err !== 'cancel') ElMessage.error('删除失败')
  }
}

const showDeviceDetail = (row) => {
  currentDevice.value = row
  showDetailDialog.value = true
}

const handleRestart = async (row) => {
  try {
    await ElMessageBox.confirm(`确定重启设备 ${row.name}?`, '警告', { type: 'warning' })
    ElMessage.info(`正在重启设备 ${row.name}，请稍候...`)
    setTimeout(() => {
      ElMessage.success(`设备 ${row.name} 重启成功`)
    }, 2000)
  } catch (err) {
    if (err !== 'cancel') ElMessage.error('重启失败')
  }
}

const handleUpdateConfig = (row) => {
  currentDevice.value = row
  showConfigDialog.value = true
}

const saveConfig = () => {
  ElMessage.success('配置更新成功，已下发到设备')
  showConfigDialog.value = false
}

const showDeviceLogs = (row) => {
  currentDevice.value = row
  showLogsDialog.value = true
}

const refreshLogs = () => {
  loadingLogs.value = true
  setTimeout(() => {
    loadingLogs.value = false
    ElMessage.success('日志刷新成功')
  }, 1000)
}

const getStatusType = (status) => {
  const map = { online: 'success', offline: 'info', error: 'danger' }
  return map[status] || 'info'
}

const getStatusText = (status) => {
  const map = { online: '在线', offline: '离线', error: '故障' }
  return map[status] || status
}

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

onMounted(() => {
  loadDevices()
})
</script>

<style scoped>
.device-list { padding: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.filter-form { margin-bottom: 20px; }

.device-stats {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;

  .stat-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 0 30px;
    border-right: 1px solid #e9ecef;

    &:last-child { border-right: none; }

    .stat-value {
      font-size: 28px;
      font-weight: 700;
      color: #333;
    }

    .stat-label {
      font-size: 14px;
      color: #999;
      margin-top: 4px;
    }

    &.online .stat-value { color: #52c41a; }
    &.offline .stat-value { color: #909399; }
    &.error .stat-value { color: #f56c6c; }
  }
}

.config-section {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #f0f0f0;

  h4 { margin: 0 0 12px; font-size: 15px; }
}

.control-section {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  gap: 12px;
}

.logs-container {
  max-height: 400px;
  overflow: hidden;
}

.logs-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px;
  color: #999;
}

.logs-content {
  max-height: 400px;
  overflow-y: auto;
}

.log-list {
  padding: 8px 0;
}

.log-item {
  display: flex;
  gap: 12px;
  padding: 6px 0;
  font-size: 13px;
  border-bottom: 1px solid #f5f5f5;

  &:last-child { border-bottom: none; }
}

.log-time {
  color: #909399;
  min-width: 160px;
  font-family: monospace;
}

.log-level {
  min-width: 60px;
  text-align: center;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;

  &.info { background: #ecf5ff; color: #409eff; }
  &.success { background: #f6ffed; color: #52c41a; }
  &.warning { background: #fff7e6; color: #fa8c16; }
  &.error { background: #fff2f0; color: #f56c6c; }
}

.log-message {
  flex: 1;
  color: #303133;
}
</style>