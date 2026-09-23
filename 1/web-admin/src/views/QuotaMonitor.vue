<template>
  <div class="quota-monitor">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>API 额度监控</span>
        </div>
      </template>

      <!-- 说明提示 -->
      <el-alert
        title="额度说明"
        type="warning"
        :closable="false"
        show-icon
        style="margin-bottom: 20px"
      >
        <template #default>
          <p>阿里云 DashScope 官方没有"查余额"的稳定公开 API；</p>
          <p>DeepSeek 官方也没有统一的"查额度"接口；</p>
          <p>本系统因此采用"本地累计调用次数 + 心跳验证 API Key 是否有效"的方式，实际账单以阿里云/DeepSeek 控制台为准。</p>
        </template>
      </el-alert>

      <!-- 两个并排卡片 -->
      <el-row :gutter="20">
        <!-- DashScope 卡片 -->
        <el-col :xs="24" :sm="12">
          <el-card shadow="hover" class="provider-card">
            <template #header>
              <div class="provider-header">
                <span><el-icon color="#ff6600"><Key /></el-icon> 阿里云 DashScope（豆包大模型）</span>
              </div>
            </template>
            
            <div class="provider-content">
              <!-- API Key 输入 -->
              <el-form label-width="80px" size="small">
                <el-form-item label="API Key">
                  <el-input
                    v-model="dashscopeKey"
                    type="password"
                    show-password
                    placeholder="输入 API Key"
                    style="width: 100%"
                  />
                </el-form-item>
                <el-form-item>
                  <el-button
                    type="primary"
                    :loading="dashscopeSaving"
                    @click="handleSaveDashScope"
                  >
                    保存 & 心跳测试
                  </el-button>
                </el-form-item>
              </el-form>
              
              <el-divider />
              
              <!-- 当前状态 -->
              <div v-if="dashscopeConfig" class="status-info">
                <el-descriptions :column="1" border size="small">
                  <el-descriptions-item label="当前 Key">
                    <code>{{ dashscopeConfig.api_key || '未设置' }}</code>
                  </el-descriptions-item>
                  <el-descriptions-item label="累计调用次数">
                    <el-tag>{{ dashscopeConfig.call_count || 0 }}</el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="最后心跳">
                    <span v-if="dashscopeConfig.last_heartbeat_at">
                      {{ dashscopeConfig.last_heartbeat_at }}
                      <el-tag
                        :type="dashscopeConfig.last_ok ? 'success' : 'danger'"
                        style="margin-left: 8px"
                      >
                        {{ dashscopeConfig.last_ok ? '成功' : '失败' }}
                      </el-tag>
                    </span>
                    <span v-else>未测试</span>
                  </el-descriptions-item>
                </el-descriptions>
                
                <!-- 错误信息 -->
                <el-alert
                  v-if="dashscopeConfig.last_error"
                  :title="dashscopeConfig.last_error"
                  type="error"
                  :closable="false"
                  show-icon
                  style="margin-top: 12px"
                />
                
                <!-- 手动刷新按钮 -->
                <el-button
                  type="default"
                  :loading="dashscopeHeartbeating"
                  @click="handleHeartbeatDashScope"
                  style="margin-top: 12px"
                >
                  <el-icon><Refresh /></el-icon> 手动刷新
                </el-button>
              </div>
            </div>
          </el-card>
        </el-col>

        <!-- DeepSeek 卡片 -->
        <el-col :xs="24" :sm="12">
          <el-card shadow="hover" class="provider-card">
            <template #header>
              <div class="provider-header">
                <span><el-icon color="#0066cc"><Key /></el-icon> DeepSeek</span>
              </div>
            </template>
            
            <div class="provider-content">
              <!-- API Key 输入 -->
              <el-form label-width="80px" size="small">
                <el-form-item label="API Key">
                  <el-input
                    v-model="deepseekKey"
                    type="password"
                    show-password
                    placeholder="输入 API Key"
                    style="width: 100%"
                  />
                </el-form-item>
                <el-form-item>
                  <el-button
                    type="primary"
                    :loading="deepseekSaving"
                    @click="handleSaveDeepSeek"
                  >
                    保存 & 心跳测试
                  </el-button>
                </el-form-item>
              </el-form>
              
              <el-divider />
              
              <!-- 当前状态 -->
              <div v-if="deepseekConfig" class="status-info">
                <el-descriptions :column="1" border size="small">
                  <el-descriptions-item label="当前 Key">
                    <code>{{ deepseekConfig.api_key || '未设置' }}</code>
                  </el-descriptions-item>
                  <el-descriptions-item label="累计调用次数">
                    <el-tag>{{ deepseekConfig.call_count || 0 }}</el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="最后心跳">
                    <span v-if="deepseekConfig.last_heartbeat_at">
                      {{ deepseekConfig.last_heartbeat_at }}
                      <el-tag
                        :type="deepseekConfig.last_ok ? 'success' : 'danger'"
                        style="margin-left: 8px"
                      >
                        {{ deepseekConfig.last_ok ? '成功' : '失败' }}
                      </el-tag>
                    </span>
                    <span v-else>未测试</span>
                  </el-descriptions-item>
                </el-descriptions>
                
                <!-- 错误信息 -->
                <el-alert
                  v-if="deepseekConfig.last_error"
                  :title="deepseekConfig.last_error"
                  type="error"
                  :closable="false"
                  show-icon
                  style="margin-top: 12px"
                />
                
                <!-- DeepSeek 接口预留说明 -->
                <el-alert
                  title="DeepSeek 接口预留说明"
                  type="info"
                  :closable="false"
                  show-icon
                  style="margin-top: 12px"
                >
                  DeepSeek 云端分析接口暂未接入，当前云端分析统一使用豆包大模型。
                  此处配置 DeepSeek Key 仅作为预留，待接入后可切换使用。
                </el-alert>
                
                <!-- 手动刷新按钮 -->
                <el-button
                  type="default"
                  :loading="deepseekHeartbeating"
                  @click="handleHeartbeatDeepSeek"
                  style="margin-top: 12px"
                >
                  <el-icon><Refresh /></el-icon> 手动刷新
                </el-button>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getQuota, setKey, heartbeat } from '../api'
import { Key, Refresh } from '@element-plus/icons-vue'

const dashscopeKey = ref('')
const deepseekKey = ref('')
const dashscopeConfig = ref(null)
const deepseekConfig = ref(null)

const dashscopeSaving = ref(false)
const deepseekSaving = ref(false)
const dashscopeHeartbeating = ref(false)
const deepseekHeartbeating = ref(false)

onMounted(() => {
  loadQuota()
})

async function loadQuota() {
  try {
    const res = await getQuota()
    if (res.success && res.data) {
      dashscopeConfig.value = res.data.dashscope
      deepseekConfig.value = res.data.deepseek
    }
  } catch (err) {
    console.error('获取额度信息失败', err)
  }
}

async function handleSaveDashScope() {
  if (!dashscopeKey.value) {
    ElMessage.warning('请输入 API Key')
    return
  }
  
  dashscopeSaving.value = true
  try {
    const res = await setKey('dashscope', { api_key: dashscopeKey.value })
    if (res.success) {
      ElMessage.success(res.message)
      dashscopeKey.value = ''
      await loadQuota()
    } else {
      ElMessage.error(res.message || '保存失败')
    }
  } catch (err) {
    console.error('保存失败', err)
    ElMessage.error('保存失败')
  } finally {
    dashscopeSaving.value = false
  }
}

async function handleSaveDeepSeek() {
  if (!deepseekKey.value) {
    ElMessage.warning('请输入 API Key')
    return
  }
  
  deepseekSaving.value = true
  try {
    const res = await setKey('deepseek', { api_key: deepseekKey.value })
    if (res.success) {
      ElMessage.success(res.message)
      deepseekKey.value = ''
      await loadQuota()
    } else {
      ElMessage.error(res.message || '保存失败')
    }
  } catch (err) {
    console.error('保存失败', err)
    ElMessage.error('保存失败')
  } finally {
    deepseekSaving.value = false
  }
}

async function handleHeartbeatDashScope() {
  dashscopeHeartbeating.value = true
  try {
    const res = await heartbeat('dashscope')
    if (res.success) {
      ElMessage.success('心跳验证成功')
    } else {
      ElMessage.error(res.message || '心跳验证失败')
    }
    await loadQuota()
  } catch (err) {
    console.error('心跳验证失败', err)
    ElMessage.error('心跳验证失败')
  } finally {
    dashscopeHeartbeating.value = false
  }
}

async function handleHeartbeatDeepSeek() {
  deepseekHeartbeating.value = true
  try {
    const res = await heartbeat('deepseek')
    if (res.success) {
      ElMessage.success('心跳验证成功')
    } else {
      ElMessage.error(res.message || '心跳验证失败')
    }
    await loadQuota()
  } catch (err) {
    console.error('心跳验证失败', err)
    ElMessage.error('心跳验证失败')
  } finally {
    deepseekHeartbeating.value = false
  }
}
</script>

<style scoped lang="scss">
.quota-monitor {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .provider-card {
    margin-bottom: 20px;

    .provider-header {
      font-weight: 600;
    }

    .provider-content {
      .status-info {
        code {
          background: #f5f5f5;
          padding: 2px 6px;
          border-radius: 3px;
          font-family: monospace;
        }
      }
    }
  }
}
</style>
