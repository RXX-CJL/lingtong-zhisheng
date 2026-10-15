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
            <!-- ★★2026-10-06 由 DSH 改写：这一栏原来是**纯装饰**。
                 用户原话："我发现系统设置里面有启动AI审核和启动兜底模型的开关，
                 是我想象的那个关了就不收费了吗？"
                 核实结论（代码级）：
                   · 原来的 saveAiConfig() 只弹一句"保存成功"，**没有任何 API 调用**，
                     默认模型/阈值/超时/重试次数全在组件内存里，刷新即丢；
                   · "启用AI审核"是假的 —— 真开关在实时监测页，现接到这里；
                   · "启用兜底模型"是假的，而且**后端根本没有这个功能**
                     （只在代码里存在自动降级：判色 CNN 失败→HSV、
                       云端 Claude 失败→豆包、车牌模型缺失→借用 yolov8s，
                       都是内部机制，不是开关）。
                 所以本栏改为：**只放真实生效的开关 + 如实标注未实现项**。 -->
            <el-alert type="warning" :closable="false" show-icon style="margin-bottom:16px">
              <template #title>本页有两个"云端花钱入口"，都能在这里真实开关</template>
              <div class="alert-body">
                关掉后**不会产生任何云端费用**，但事件需要人工复核。逐条说明见下方每项的注解。
              </div>
            </el-alert>

            <el-form label-width="180px">
              <el-form-item label="事件级云端AI复核">
                <el-switch v-model="rt.cloud_review" @change="pushRuntimeSetting('cloud_review')" />
                <el-tag :type="rt.cloud_review ? 'danger' : 'success'" size="small" style="margin-left:10px">
                  {{ rt.cloud_review ? '开 — 每次违规事件都会调用云端（计费）' : '关 — 事件转「待人工复核」，零云调用' }}
                </el-tag>
              </el-form-item>
              <div class="field-note">
                开：每条违规事件调用**豆包视觉**（3~5 关键帧）+ **DeepSeek** 二级验证
                （配了 Claude key 还会多一次），按 ai_trace v3 交叉验证后自动判 confirmed/rejected。
                <br />关：事件进入「待人工复核」，在 <b>交通事件</b> 页点确认/排除即可。
                <span class="warn-text">这是最大的一笔开销来源。</span>
              </div>

              <el-form-item label="逐帧云端咨询">
                <el-switch v-model="rt.cloud_consult" @change="pushRuntimeSetting('cloud_consult')" />
                <el-tag :type="rt.cloud_consult ? 'warning' : 'success'" size="small" style="margin-left:10px">
                  {{ rt.cloud_consult ? '开 — 本地判不准时逐帧问云端' : '关 — 不逐帧咨询' }}
                </el-tag>
              </el-form-item>
              <div class="field-note">
                开：检测循环遇到"本地规则拿不准"的帧时，抽帧问云端（异步，不阻塞检测）。
                <br />与上面那项是**两条独立的计费支路**，可分别关闭。
              </div>

              <el-form-item label="未标定的超速也送云端复核">
                <el-switch v-model="rt.cloud_review_uncalibrated"
                           @change="pushRuntimeSetting('cloud_review_uncalibrated')" />
              </el-form-item>
              <div class="field-note">
                <span class="warn-text">建议保持关闭。</span>
                实测：云端视觉模型明确回复"仅凭静态图像无法判定是否超速" ——
                送审只会白烧 token 并产生 rejected（历史上 364 条事件因此被判 rejected）。
                已标定的超速不受此项影响，会正常送审。
              </div>

              <el-form-item label="违规确认时长(秒)">
                <el-input-number v-model="rt.hold_sec" :min="0" :max="10" :step="0.5"
                                 @change="pushRuntimeSetting('hold_sec')" />
                <span class="unit-hint">越大越保守，误报越少、上报越慢（默认 1.5）</span>
              </el-form-item>

              <el-form-item label="同类违规冷却期(秒)">
                <el-input-number v-model="rt.cooldown_sec" :min="0" :max="120" :step="1"
                                 @change="pushRuntimeSetting('cooldown_sec')" />
                <span class="unit-hint">同一类违规在此时间内不重复上报（默认 8）</span>
              </el-form-item>

              <el-form-item label="画面标注档位">
                <el-select v-model="rt.display_mode" style="width:200px"
                           @change="pushRuntimeSetting('display_mode')">
                  <el-option label="极简（仅 ID）" value="minimal" />
                  <el-option label="标准（+速度）" value="standard" />
                  <el-option label="详细（全部）" value="full" />
                  <el-option label="仅框线" value="off" />
                </el-select>
              </el-form-item>

              <el-form-item>
                <el-button @click="loadRuntimeSettings" :loading="rtLoading">重新读取后端当前值</el-button>
                <span class="unit-hint">本栏开关**改一下即生效**（不用点保存）</span>
              </el-form-item>
            </el-form>

            <!-- 未实现项：如实标注，不再摆假开关 -->
            <el-divider content-position="left">以下项后端尚未实现（已从"假开关"改为如实标注）</el-divider>
            <div class="unimpl">
              <div class="unimpl-item">
                <b>默认模型选择</b>（原下拉框：Claude / 智谱 / DeepSeek / Qwen）——
                后端没有"选一个默认模型"的概念：事件复核是**固定并行**调豆包 + DeepSeek，
                不是可切换的单模型。需要切换请改用 <code>api/.env</code> 里的 Key。
              </div>
              <div class="unimpl-item">
                <b>超时时间 / 重试次数</b> —— 后端用的是 <code>config.py</code> 的
                <code>API_TIMEOUT</code> / <code>API_RETRY_TIMES</code>（环境变量），
                没有运行时接口，页面上改不了也不生效。
              </div>
              <div class="unimpl-item">
                <b>启用兜底模型</b> —— 后端**不存在**这个功能。代码里只有自动降级，
                不是开关：判色 CNN 不可用 → HSV（<code>traffic_light_classifier.py:198</code>）；
                云端 Claude 失败 → 豆包（<code>cloud_collaborator.py:216</code>）；
                车牌模型缺失 → 借用 yolov8s（<code>image_recognizer.py:270</code>）。
              </div>
            </div>

            <el-form label-width="180px" style="margin-top:16px">
              <el-form-item label="API Key管理">
                <el-button type="primary" @click="showApiKeyDialog = true">管理API Key</el-button>
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
// api 即 index.js 的默认导出（axios 实例，baseURL=/api），用于运行时设置接口
import api, { getModels, switchModel, unloadModel, initModels, getPerformance, resetPerformance } from '@/api'
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

// ★2026-10-06 由 DSH 删除：原 aiConfig（默认模型 / 检测阈值 / 超时 / 启用AI审核 /
// 启用兜底模型 / 重试次数）是**纯装饰** —— 没有对应后端字段，saveAiConfig() 只弹提示。
// 留着它会让后来者以为这些设置真的生效。已由下面的 rt（真运行时设置）+ 模板里的
// "未实现项"说明取代。

/**
 * ★运行时设置（2026-10-06 由 DSH 新增）—— 这些是**真的接后端**的开关。
 *
 * 背景：本页原来的 aiConfig（默认模型/阈值/超时/启用AI审核/启用兜底模型/重试次数）
 * 是**纯装饰**：saveAiConfig() 只弹一句"保存成功"，没有任何 API 调用，
 * 刷新即丢，后端完全不知道。用户问"关了就不收费了吗"——答案是当时**照收**。
 *
 * 现在改为：读写 /api/realtime/settings，改一下立刻生效。
 *   cloud_review             事件级云端复核（每条违规打豆包+DeepSeek）★最大开销
 *   cloud_consult            逐帧咨询（本地不确定时逐帧问云端）
 *   cloud_review_uncalibrated 未标定的超速是否也送审（建议关）
 *   hold_sec / cooldown_sec  确认时长 / 同类违规冷却期
 *   display_mode             画面标注档位
 */
const rt = reactive({
  cloud_review: true,
  cloud_consult: true,
  cloud_review_uncalibrated: false,
  hold_sec: 1.5,
  cooldown_sec: 8,
  display_mode: 'minimal',
})
const rtLoading = ref(false)

async function loadRuntimeSettings() {
  rtLoading.value = true
  try {
    const r = await api.get('/realtime/settings')
    const d = r?.data?.data || r?.data
    if (d) {
      rt.cloud_review = d.cloud_review !== false
      rt.cloud_consult = d.cloud_consult !== false
      rt.cloud_review_uncalibrated = d.cloud_review_uncalibrated === true
      rt.hold_sec = d.hold_sec ?? rt.hold_sec
      rt.cooldown_sec = d.cooldown_sec ?? rt.cooldown_sec
      rt.display_mode = d.display_mode || rt.display_mode
    }
  } catch (e) {
    ElMessage.error('读取运行时设置失败：' + (e?.response?.data?.detail || e.message))
  } finally { rtLoading.value = false }
}

/** 只推这一项（不连带其它设置），并按后端回读值回写，杜绝"界面关了后端还开着" */
async function pushRuntimeSetting(key) {
  try {
    const r = await api.post('/realtime/settings', { [key]: rt[key] })
    const d = r?.data?.data || r?.data
    if (d && d[key] !== undefined) rt[key] = d[key]
    if (key === 'cloud_review') {
      ElMessage({
        type: rt.cloud_review ? 'warning' : 'success',
        message: rt.cloud_review
          ? '已开启事件级云端 AI 复核：每条违规事件都会调用云端，会计费'
          : '已关闭事件级云端 AI 复核：事件转「待人工复核」，不再产生云端费用',
        duration: 4000,
      })
    } else {
      ElMessage.success('已生效')
    }
  } catch (e) {
    ElMessage.error('设置失败：' + (e?.response?.data?.detail || e.message))
    await loadRuntimeSettings()   // 失败则回读真实状态
  }
}

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
  loadRuntimeSettings()      // ★2026-10-06 由 DSH 新增：读出后端真实的云端开关值
})

// ★2026-10-06 由 DSH 删除 saveAiConfig()：这是**假存根**（只弹提示、不调接口）。
// 用户正是被它误导："启动AI审核 / 启动兜底模型 …关了就不收费了吗？"
// —— 当时关了照收。真开关见 loadRuntimeSettings / pushRuntimeSetting。

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

/* ---------- AI 运行时设置栏（2026-10-06 由 DSH 新增） ---------- */
.alert-body { font-size: 12px; line-height: 1.7; }
.field-note {
  margin: -8px 0 18px 180px;
  font-size: 12px;
  color: var(--zt-text-muted, #909399);
  line-height: 1.75;
}
.field-note code,
.unimpl-item code {
  background: #f5f7fa; border-radius: 3px; padding: 0 4px;
  font-family: Consolas, Monaco, monospace; font-size: 11px;
}
.warn-text { color: #e6a23c; font-weight: 600; }
.unit-hint { margin-left: 10px; font-size: 12px; color: #909399; }
.unimpl { font-size: 12px; color: #909399; line-height: 1.8; }
.unimpl-item {
  margin-bottom: 8px; padding: 8px 10px;
  background: #fafafa; border-left: 3px solid #dcdfe6; border-radius: 3px;
}
.unimpl-item b { color: #606266; }

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