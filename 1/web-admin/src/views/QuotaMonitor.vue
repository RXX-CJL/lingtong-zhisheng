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
                <span><el-icon color="#ff6600"><Key /></el-icon> 阿里云 DashScope（通义千问）</span>
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
                
                <!-- DeepSeek 配置说明 -->
                <el-alert
                  title="DeepSeek 配置说明"
                  type="info"
                  :closable="false"
                  show-icon
                  style="margin-top: 12px"
                >
                  本页仅管理 DeepSeek API Key 的连通性与本地调用计数；是否用于事件复核，以系统当前实际配置和调用链为准。
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

      <!-- 通用云端 AI API 配置预留：当前仅展示设计，不保存配置、不调用外部服务 -->
      <el-card shadow="never" class="future-api-card">
        <template #header>
          <div class="card-header">
            <span>通用云端 AI API 配置（预留）</span>
            <el-tag type="info">尚未接入</el-tag>
          </div>
        </template>

        <el-alert
          title="当前仅预留配置界面，不会保存信息或发起 API 调用。请勿在此输入真实 API Key。"
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 18px"
        />

        <el-form label-width="130px" size="small" disabled>
          <el-row :gutter="16">
            <el-col :xs="24" :md="12">
              <el-form-item label="服务商标识">
                <el-input placeholder="接入时配置，例如 provider-id" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :md="12">
              <el-form-item label="模型标识">
                <el-input placeholder="接入时配置，例如 model-id" />
              </el-form-item>
            </el-col>
            <el-col :xs="24">
              <el-form-item label="API Base URL">
                <el-input placeholder="接入时配置服务商 API 地址（建议 HTTPS）" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :md="12">
              <el-form-item label="API Key">
                <el-input type="password" placeholder="接入后由后端安全保存，不向前端回传明文" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :md="12">
              <el-form-item label="月度预算上限">
                <el-input placeholder="接入后配置；需由后端执行预算限制" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :md="12">
              <el-form-item label="统计周期">
                <el-input placeholder="预留：按月统计调用量与费用" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :md="12">
              <el-form-item label="调用策略">
                <el-input placeholder="预留：按需触发、周期任务或事件复核" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item>
            <el-button type="primary" disabled>保存配置</el-button>
            <el-button disabled>测试连接</el-button>
          </el-form-item>
        </el-form>

        <p class="future-api-note">
          后续接入时，将通过独立后端适配器实现配置保存、连接验证、调用统计和预算检查；此预留区目前不代表这些能力已经实现。
        </p>
      </el-card>
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
  .future-api-card {
    margin-top: 20px;

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
    }

    .future-api-note {
      margin: 4px 0 0;
      color: var(--el-text-color-secondary);
      font-size: 12px;
      line-height: 1.6;
    }
  }

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
