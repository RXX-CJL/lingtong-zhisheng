<template>
  <div class="settings-page">
    <el-card>
      <template #header>
        <span>系统设置</span>
      </template>

      <el-tabs v-model="activeTab">
        <!-- AI模型配置 -->
        <el-tab-pane label="AI模型配置" name="ai">
          <div class="tab-content">
            <el-form :model="aiConfig" label-width="160px">
              <el-form-item label="默认模型" required>
                <el-select v-model="aiConfig.defaultModel" placeholder="请选择模型">
                  <el-option label="Claude 3.5 Sonnet" value="claude-3.5-sonnet" />
                  <el-option label="智谱Glm-4V" value="glm-4v" />
                  <el-option label="DeepSeek-V2" value="deepseek-v2" />
                  <el-option label="Qwen-VL" value="qwen-vl" />
                </el-select>
              </el-form-item>

              <el-form-item label="检测阈值">
                <el-slider v-model="aiConfig.threshold" :min="0" :max="1" :step="0.01" />
                <span>{{ aiConfig.threshold.toFixed(2) }}</span>
              </el-form-item>

              <el-form-item label="超时时间(秒)">
                <el-input-number v-model="aiConfig.timeout" :min="5" :max="60" />
              </el-form-item>

              <el-form-item label="启用AI审核">
                <el-switch v-model="aiConfig.enableAiReview" />
              </el-form-item>

              <el-form-item label="启用兜底模型">
                <el-switch v-model="aiConfig.enableFallback" />
              </el-form-item>

              <el-form-item label="重试次数">
                <el-input-number v-model="aiConfig.retryCount" :min="0" :max="5" />
              </el-form-item>

              <el-form-item label="API Key管理">
                <el-button type="primary" @click="showApiKeyDialog = true">管理API Key</el-button>
              </el-form-item>

              <el-form-item>
                <el-button type="primary" @click="saveAiConfig">保存配置</el-button>
              </el-form-item>
            </el-form>

            <!-- 模型状态 -->
            <div class="model-status">
              <h4>模型服务状态</h4>
              <div class="status-list">
                <div class="status-item">
                  <span class="status-name">Claude 3.5 Sonnet</span>
                  <el-tag type="success">在线</el-tag>
                  <span class="status-latency">延迟: 95ms</span>
                </div>
                <div class="status-item">
                  <span class="status-name">智谱Glm-4V</span>
                  <el-tag type="success">在线</el-tag>
                  <span class="status-latency">延迟: 120ms</span>
                </div>
                <div class="status-item">
                  <span class="status-name">DeepSeek-V2</span>
                  <el-tag type="success">在线</el-tag>
                  <span class="status-latency">延迟: 85ms</span>
                </div>
                <div class="status-item">
                  <span class="status-name">Qwen-VL</span>
                  <el-tag type="warning">离线</el-tag>
                  <span class="status-latency">-</span>
                </div>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <!-- 通知设置 -->
        <el-tab-pane label="通知设置" name="notification">
          <div class="tab-content">
            <el-form :model="notificationConfig" label-width="160px">
              <el-form-item label="启用违规通知">
                <el-switch v-model="notificationConfig.enableViolationNotify" />
              </el-form-item>

              <el-form-item label="通知方式">
                <el-checkbox-group v-model="notificationConfig.notifyMethods">
                  <el-checkbox label="站内消息" value="internal" />
                  <el-checkbox label="短信通知" value="sms" />
                  <el-checkbox label="邮件通知" value="email" />
                </el-checkbox-group>
              </el-form-item>

              <el-form-item label="通知阈值">
                <el-select v-model="notificationConfig.notifyThreshold">
                  <el-option label="高置信度(>90%)" value="high" />
                  <el-option label="中置信度(>70%)" value="medium" />
                  <el-option label="全部违规" value="all" />
                </el-select>
              </el-form-item>

              <el-form-item label="每日通知上限">
                <el-input-number v-model="notificationConfig.dailyLimit" :min="1" :max="1000" />
              </el-form-item>

              <el-form-item label="告警声音">
                <el-switch v-model="notificationConfig.enableSound" />
              </el-form-item>

              <el-form-item label="违规类型通知">
                <el-checkbox-group v-model="notificationConfig.notifyTypes">
                  <el-checkbox label="未戴头盔" value="no_helmet" />
                  <el-checkbox label="闯红灯" value="red_light" />
                  <el-checkbox label="逆行" value="retrograde" />
                  <el-checkbox label="超速" value="speeding" />
                </el-checkbox-group>
              </el-form-item>

              <el-form-item>
                <el-button type="primary" @click="saveNotificationConfig">保存配置</el-button>
              </el-form-item>
            </el-form>
          </div>
        </el-tab-pane>

        <!-- M07: 场景模式（插件管理） -->
        <el-tab-pane label="场景模式" name="scene">
          <div class="tab-content">
            <el-form label-width="160px">
              <el-form-item label="场景模式">
                <el-select v-model="sceneMode" placeholder="请选择场景模式" style="width: 240px" @change="handleSceneModeChange">
                  <el-option
                    v-for="mode in sceneModes"
                    :key="mode.value"
                    :label="mode.label"
                    :value="mode.value"
                  />
                </el-select>
                <el-button type="primary" style="margin-left: 12px" @click="applySceneMode">应用</el-button>
                <el-tag v-if="currentSceneModeCn" type="success" effect="plain" style="margin-left: 12px">
                  当前: {{ currentSceneModeCn }}
                </el-tag>
              </el-form-item>

              <el-form-item label="已启用插件">
                <div class="plugin-list">
                  <el-tag
                    v-for="p in plugins"
                    :key="p.scenario_name"
                    :type="p.enabled ? 'success' : 'info'"
                    effect="plain"
                    class="plugin-tag"
                  >
                    {{ scenarioCn(p.scenario_name) }}
                    <span class="plugin-status">{{ p.enabled ? '已启用' : '已禁用' }}</span>
                  </el-tag>
                  <span v-if="!plugins.length" class="empty-tip">暂无已加载插件</span>
                </div>
              </el-form-item>

              <el-form-item label="插件单独控制">
                <el-table :data="plugins" stripe size="small" v-loading="pluginsLoading">
                  <el-table-column prop="scenario_name" label="场景标识" width="180">
                    <template #default="{ row }">
                      <span>{{ row.scenario_name }}</span>
                      <span class="scenario-cn"> ({{ scenarioCn(row.scenario_name) }})</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="initialized" label="初始化" width="100">
                    <template #default="{ row }">
                      <el-tag :type="row.initialized ? 'success' : 'info'" size="small">
                        {{ row.initialized ? '是' : '否' }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="可检测类型" min-width="220">
                    <template #default="{ row }">
                      <el-tag
                        v-for="t in row.detectable_types"
                        :key="t"
                        size="small"
                        effect="plain"
                        style="margin-right: 4px"
                      >
                        {{ t }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="启用" width="100">
                    <template #default="{ row }">
                      <el-switch
                        :model-value="row.enabled"
                        @change="(val) => handlePluginSwitch(row, val)"
                      />
                    </template>
                  </el-table-column>
                </el-table>
              </el-form-item>
            </el-form>
          </div>
        </el-tab-pane>

        <!-- 用户管理 -->
        <el-tab-pane label="用户管理" name="user">
          <div class="tab-content">
            <div class="user-header">
              <el-button type="primary" @click="showAddUserDialog = true">
                <el-icon><Plus /></el-icon> 添加用户
              </el-button>
            </div>

            <el-table :data="users" v-loading="loading" stripe>
              <el-table-column prop="id" label="ID" width="80" />
              <el-table-column prop="username" label="用户名" width="120" />
              <el-table-column prop="name" label="姓名" width="100" />
              <el-table-column prop="email" label="邮箱" width="180" />
              <el-table-column prop="role" label="角色" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.role === 'admin' ? 'danger' : 'success'">
                    {{ row.role === 'admin' ? '管理员' : '操作员' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="100">
                <template #default="{ row }">
                  <el-switch v-model="row.status" @change="toggleUserStatus(row)" />
                </template>
              </el-table-column>
              <el-table-column prop="created_at" label="创建时间" width="180">
                <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
              </el-table-column>
              <el-table-column label="操作" width="180">
                <template #default="{ row }">
                  <el-button size="small" @click="editUser(row)">编辑</el-button>
                  <el-button size="small" type="danger" @click="deleteUser(row)" v-if="row.role !== 'admin'">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
        <el-tab-pane label="设备管理" name="devices">
          <DeviceList />
        </el-tab-pane>
        <el-tab-pane label="API 额度" name="quota">
          <QuotaMonitor />
        </el-tab-pane>
        <el-tab-pane label="系统日志" name="log">
          <SystemLog />
        </el-tab-pane>
        <el-tab-pane label="关于" name="about">
          <About />
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- API Key管理对话框 -->
    <el-dialog v-model="showApiKeyDialog" title="API Key管理" width="500px" @open="loadApiKeys">
      <el-form :model="apiKeyForm" label-width="120px">
        <el-form-item label="Claude API Key">
          <el-input v-model="apiKeyForm.claudeKey" type="password" show-password />
        </el-form-item>
        <el-form-item label="智谱API Key">
          <el-input v-model="apiKeyForm.zhipuKey" type="password" show-password />
        </el-form-item>
        <el-form-item label="DeepSeek API Key">
          <el-input v-model="apiKeyForm.deepseekKey" type="password" show-password />
        </el-form-item>
        <el-form-item label="Qwen API Key">
          <el-input v-model="apiKeyForm.qwenKey" type="password" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="danger" text @click="clearApiKeys">清除已保存的API Key</el-button>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showApiKeyDialog = false">取消</el-button>
        <el-button type="primary" @click="saveApiKey">保存</el-button>
      </template>
    </el-dialog>

    <!-- 添加用户对话框 -->
    <el-dialog v-model="showAddUserDialog" :title="editingUser ? '编辑用户' : '添加用户'" width="500px">
      <el-form :model="userForm" label-width="100px">
        <el-form-item label="用户名" required>
          <el-input v-model="userForm.username" />
        </el-form-item>
        <el-form-item label="姓名" required>
          <el-input v-model="userForm.name" />
        </el-form-item>
        <el-form-item label="邮箱" required>
          <el-input v-model="userForm.email" />
        </el-form-item>
        <el-form-item label="密码" :required="!editingUser">
          <el-input v-model="userForm.password" type="password" />
          <span v-if="editingUser" class="el-form-item__error">不填则保持原密码</span>
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="userForm.role">
            <el-option label="管理员" value="admin" />
            <el-option label="操作员" value="operator" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddUserDialog = false">取消</el-button>
        <el-button type="primary" @click="saveUser">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { getModels, switchModel, unloadModel, initModels, getPerformance, resetPerformance } from '@/api'
import { getPlugins, switchPlugin, setSceneMode, getSceneModes } from '@/api'
import DeviceList from './DeviceList.vue'
import QuotaMonitor from './QuotaMonitor.vue'
import SystemLog from './SystemLog.vue'
import About from './About.vue'

const loading = ref(false)
const activeTab = ref('ai')
const showApiKeyDialog = ref(false)
const showAddUserDialog = ref(false)
const editingUser = ref(null)

// M07: 场景模式相关
const sceneMode = ref('all')
const sceneModes = ref([])
const plugins = ref([])
const pluginsLoading = ref(false)

const SCENARIO_CN_MAP = {
  traffic: '交通',
  urban_management: '城管',
  public_security: '治安'
}

const currentSceneModeCn = computed(() => {
  const m = sceneModes.value.find(item => item.value === sceneMode.value)
  return m ? m.label : ''
})

const scenarioCn = (name) => SCENARIO_CN_MAP[name] || name

const loadSceneModes = async () => {
  try {
    const res = await getSceneModes()
    if (res.success) {
      sceneModes.value = res.scene_modes || []
    }
  } catch (err) {
    console.error('获取场景模式列表失败', err)
  }
}

const loadPlugins = async () => {
  pluginsLoading.value = true
  try {
    const res = await getPlugins()
    if (res.success) {
      plugins.value = res.plugins || []
      // 反推当前场景模式：根据启用的插件集合匹配预设
      const enabled = new Set(res.enabled_scenarios || [])
      const presets = res.scene_presets || {}
      const matched = Object.entries(presets).find(([_, arr]) => {
        const target = new Set(arr)
        if (target.size !== enabled.size) return false
        for (const s of enabled) if (!target.has(s)) return false
        return true
      })
      if (matched) sceneMode.value = matched[0]
    }
  } catch (err) {
    console.error('获取插件列表失败', err)
  } finally {
    pluginsLoading.value = false
  }
}

const handleSceneModeChange = (val) => {
  // 仅更新本地选择，需点击"应用"才下发
}

const applySceneMode = async () => {
  try {
    const res = await setSceneMode(sceneMode.value)
    if (res.success) {
      ElMessage.success(res.message || `已切换到 ${res.scene_mode_cn}`)
      await loadPlugins()
    } else {
      ElMessage.error(res.message || '切换失败')
    }
  } catch (err) {
    ElMessage.error('切换场景模式失败')
  }
}

const handlePluginSwitch = async (row, val) => {
  try {
    const res = await switchPlugin(row.scenario_name, val)
    if (res.success) {
      ElMessage.success(res.message)
      await loadPlugins()
    } else {
      ElMessage.error(res.message || '切换失败')
    }
  } catch (err) {
    ElMessage.error('切换插件失败')
  }
}

const aiConfig = reactive({
  defaultModel: 'glm-4v',
  threshold: 0.5,
  timeout: 30,
  enableAiReview: true,
  enableFallback: true,
  retryCount: 2
})

const notificationConfig = reactive({
  enableViolationNotify: true,
  notifyMethods: ['internal', 'sms'],
  notifyThreshold: 'high',
  dailyLimit: 100,
  enableSound: true,
  notifyTypes: ['no_helmet', 'red_light']
})

const apiKeyForm = reactive({
  claudeKey: '',
  zhipuKey: '',
  deepseekKey: '',
  qwenKey: ''
})

const userForm = reactive({
  username: '',
  name: '',
  email: '',
  password: '',
  role: 'operator'
})

const users = ref([
  { id: 1, username: 'admin', name: '管理员', email: 'admin@example.com', role: 'admin', status: true, created_at: '2026-01-01 00:00:00' },
  { id: 2, username: 'operator', name: '操作员', email: 'operator@example.com', role: 'operator', status: true, created_at: '2026-01-15 10:30:00' },
  { id: 3, username: 'monitor', name: '监控员', email: 'monitor@example.com', role: 'operator', status: false, created_at: '2026-02-20 14:00:00' }
])

const modelStatus = ref({})
const performanceStats = ref({})
const modelLoading = ref(false)

const loadModelStatus = async () => {
  modelLoading.value = true
  try {
    const res = await getModels()
    if (res.success) {
      modelStatus.value = res.data
    }
  } catch (err) {
    console.error('获取模型状态失败', err)
  } finally {
    modelLoading.value = false
  }
}

const loadPerformance = async () => {
  try {
    const res = await getPerformance()
    if (res.success) {
      performanceStats.value = res.data
    }
  } catch (err) {
    console.error('获取性能统计失败', err)
  }
}

const handleSwitchModel = async (modelKey) => {
  try {
    const res = await switchModel(modelKey)
    if (res.success) {
      ElMessage.success(res.message)
      loadModelStatus()
    } else {
      ElMessage.error(res.message)
    }
  } catch (err) {
    ElMessage.error('切换模型失败')
  }
}

const handleUnloadModel = async (modelKey) => {
  try {
    await ElMessageBox.confirm(`确定卸载模型 ${modelKey}?`, '警告', { type: 'warning' })
    const res = await unloadModel(modelKey)
    if (res.success) {
      ElMessage.success(res.message)
      loadModelStatus()
    }
  } catch (err) {
    if (err !== 'cancel') ElMessage.error('卸载失败')
  }
}

const handleInitModels = async () => {
  try {
    const res = await initModels()
    if (res.success) {
      ElMessage.success(res.message)
      loadModelStatus()
    }
  } catch (err) {
    ElMessage.error('初始化模型失败')
  }
}

const handleResetPerformance = async () => {
  try {
    await ElMessageBox.confirm('确定重置性能统计?', '警告', { type: 'warning' })
    const res = await resetPerformance()
    if (res.success) {
      ElMessage.success(res.message)
      loadPerformance()
    }
  } catch (err) {
    if (err !== 'cancel') ElMessage.error('重置失败')
  }
}

onMounted(() => {
  loadModelStatus()
  loadPerformance()
  loadApiKeys()
  loadSceneModes()
  loadPlugins()
})

const saveAiConfig = () => {
  ElMessage.success('AI模型配置保存成功')
}

const saveNotificationConfig = () => {
  ElMessage.success('通知设置保存成功')
}

const loadApiKeys = () => {
  const saved = localStorage.getItem('apiKeys')
  if (saved) {
    try {
      const keys = JSON.parse(saved)
      apiKeyForm.claudeKey = keys.claudeKey || ''
      apiKeyForm.zhipuKey = keys.zhipuKey || ''
      apiKeyForm.deepseekKey = keys.deepseekKey || ''
      apiKeyForm.qwenKey = keys.qwenKey || ''
    } catch (e) {
      console.error('解析保存的API Key失败', e)
    }
  }
}

const saveApiKey = () => {
  localStorage.setItem('apiKeys', JSON.stringify({
    claudeKey: apiKeyForm.claudeKey,
    zhipuKey: apiKeyForm.zhipuKey,
    deepseekKey: apiKeyForm.deepseekKey,
    qwenKey: apiKeyForm.qwenKey
  }))
  ElMessage.success('API Key保存成功')
  showApiKeyDialog.value = false
}

const clearApiKeys = () => {
  localStorage.removeItem('apiKeys')
  apiKeyForm.claudeKey = ''
  apiKeyForm.zhipuKey = ''
  apiKeyForm.deepseekKey = ''
  apiKeyForm.qwenKey = ''
  ElMessage.success('已清除保存的API Key')
}

const saveUser = () => {
  if (editingUser.value) {
    const index = users.value.findIndex(u => u.id === editingUser.value.id)
    if (index !== -1) {
      users.value[index] = { ...users.value[index], ...userForm }
    }
    ElMessage.success('用户信息更新成功')
  } else {
    users.value.unshift({
      id: Date.now(),
      ...userForm,
      status: true,
      created_at: new Date().toLocaleString('zh-CN')
    })
    ElMessage.success('用户添加成功')
  }
  showAddUserDialog.value = false
  editingUser.value = null
  Object.keys(userForm).forEach(k => userForm[k] = '')
}

const editUser = (row) => {
  editingUser.value = row
  userForm.username = row.username
  userForm.name = row.name
  userForm.email = row.email
  userForm.role = row.role
  userForm.password = ''
  showAddUserDialog.value = true
}

const deleteUser = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除用户 ${row.name}?`, '警告', { type: 'warning' })
    users.value = users.value.filter(u => u.id !== row.id)
    ElMessage.success('用户删除成功')
  } catch (err) {
    if (err !== 'cancel') ElMessage.error('删除失败')
  }
}

const toggleUserStatus = (row) => {
  ElMessage.success(row.status ? '用户已启用' : '用户已禁用')
}

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}
</script>

<style scoped>
.settings-page { padding: 20px; }
.tab-content { padding: 20px 0; }

.user-header {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 20px;
}

.model-status {
  margin-top: 30px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;

  h4 { margin: 0 0 16px; font-size: 15px; }
}

.status-list {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);

  .status-name { font-weight: 500; }
  .status-latency { font-size: 13px; color: #999; }
}

/* M07: 场景模式样式 */
.plugin-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.plugin-tag {
  padding: 6px 12px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.plugin-status {
  font-size: 12px;
  opacity: 0.75;
}

.scenario-cn {
  color: #999;
  font-size: 12px;
}

.empty-tip {
  color: #999;
  font-size: 13px;
}
</style>