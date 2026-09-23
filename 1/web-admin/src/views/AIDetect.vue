<template>
  <div class="ai-detect">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>智瞳灵声 · 智能识别（AI 审核）</span>
        </div>
      </template>

      <el-tabs v-model="activeTab" type="card">
        <el-tab-pane label="文件上传" name="upload">
          <div class="upload-section">
            <el-upload
              ref="uploadRef"
              :auto-upload="false"
              :limit="1"
              :on-change="handleFileChange"
              :on-exceed="handleExceed"
              drag
              accept=".jpg,.jpeg,.png,.mp4,.avi"
            >
              <el-icon class="el-icon--upload"><upload-filled /></el-icon>
              <div class="el-upload__text">
                拖拽文件到此处，或<em>点击上传</em>
              </div>
              <template #tip>
                <div class="el-upload__tip">
                  支持 jpg/jpeg/png 图片，mp4/avi 视频（建议小于 10MB）
                </div>
              </template>
            </el-upload>

            <div class="options-row">
              <el-form :inline="true">
                <el-form-item label="违规类型">
                  <el-select v-model="violationType" placeholder="选择违规类型" style="width: 200px">
                    <el-option label="闯红灯" value="red_light" />
                    <el-option label="未戴头盔" value="no_helmet" />
                    <el-option label="逆行" value="wrong_way" />
                    <el-option label="违规停车" value="illegal_parking" />
                    <el-option label="压线行驶" value="lane_departure" />
                    <el-option label="超速" value="speeding" />
                  </el-select>
                </el-form-item>
                <el-form-item label="用户备注">
                  <el-input
                    v-model="userNote"
                    type="textarea"
                    :rows="2"
                    placeholder="可选：添加备注信息"
                    style="width: 300px"
                  />
                </el-form-item>
              </el-form>
            </div>

            <div class="action-row">
              <el-button
                type="primary"
                size="large"
                :loading="analyzing"
                :disabled="!selectedFile"
                @click="handleAnalyze"
              >
                <el-icon><VideoCamera /></el-icon>
                {{ analyzing ? '分析中...' : '开始分析' }}
              </el-button>
              <el-progress
                v-if="analyzing && uploadProgress > 0"
                :percentage="uploadProgress"
                style="width: 200px; margin-left: 20px"
              />
            </div>
          </div>

          <div v-if="result" class="result-section">
            <el-divider>分析结果</el-divider>
            
            <el-row :gutter="20">
              <el-col :span="10">
                <el-card shadow="hover">
                  <template #header>
                    <span>图片预览</span>
                  </template>
                  <el-image
                    v-if="previewUrl"
                    :src="previewUrl"
                    fit="contain"
                    style="width: 100%; max-height: 400px"
                    :preview-src-list="[previewUrl]"
                    preview-teleported
                  />
                  <div v-else class="no-preview">
                    <el-icon size="48"><VideoPlay /></el-icon>
                    <p>视频文件（首帧已提取）</p>
                  </div>
                </el-card>
              </el-col>

              <el-col :span="14">
                <el-card shadow="hover" class="result-card">
                  <template #header>
                    <div class="card-header">
                      <span><el-icon color="#1890ff"><Cpu /></el-icon> 本地 AI（YOLOv8）检测结果</span>
                      <span v-if="result.ai_trace" class="duration">
                        耗时: {{ result.ai_trace.yolo_duration_ms }} ms
                      </span>
                    </div>
                  </template>
                  
                  <div v-if="yoloDetections && yoloDetections.length > 0">
                    <el-table :data="yoloDetections" stripe size="small">
                      <el-table-column prop="class_name" label="对象类型" width="150" />
                      <el-table-column label="置信度" width="120">
                        <template #default="{ row }">
                          {{ (row.confidence * 100).toFixed(1) }}%
                        </template>
                      </el-table-column>
                      <el-table-column label="坐标">
                        <template #default="{ row }">
                          {{ formatBbox(row.bbox) }}
                        </template>
                      </el-table-column>
                    </el-table>
                  </div>
                  <el-empty v-else description="未检测到相关对象" :image-size="60" />
                </el-card>

                <el-card shadow="hover" class="result-card">
                  <template #header>
                    <div class="card-header">
                      <span><el-icon color="#52c41a"><Key /></el-icon> 云端 AI（豆包大模型）分析</span>
                      <span v-if="result.ai_trace" class="duration">
                        耗时: {{ result.ai_trace.doubao_duration_ms }} ms
                      </span>
                    </div>
                  </template>
                  
                  <div v-if="result.cloud_result">
                    <el-descriptions :column="2" border size="small">
                      <el-descriptions-item label="是否确认违规">
                        <el-tag :type="result.cloud_validated ? 'success' : 'info'">
                          {{ result.cloud_validated ? '是' : '否' }}
                        </el-tag>
                      </el-descriptions-item>
                      <el-descriptions-item label="最终置信度">
                        {{ (result.confidence * 100).toFixed(1) }}%
                      </el-descriptions-item>
                    </el-descriptions>
                    
                    <div class="doubao-text">
                      <el-collapse>
                        <el-collapse-item title="豆包完整回答" name="1">
                          <pre>{{ result.cloud_result }}</pre>
                        </el-collapse-item>
                      </el-collapse>
                    </div>
                  </div>
                  <el-empty v-else description="云端分析未执行或失败" :image-size="60" />
                </el-card>

                <div class="result-actions">
                  <el-button type="success" @click="handleSave">
                    <el-icon><Check /></el-icon>
                    保存为违规记录
                  </el-button>
                  <el-button type="warning" @click="handleReanalyze">
                    <el-icon><Refresh /></el-icon>
                    重新分析
                  </el-button>
                </div>
              </el-col>
            </el-row>
          </div>
        </el-tab-pane>

        <el-tab-pane label="实时摄像头" name="realtime">
          <div class="realtime-section">
            <el-row :gutter="20" class="realtime-controls">
              <el-col :span="6">
                <el-form-item label="选择摄像头">
                  <div class="camera-select-wrapper">
                    <el-select v-model="selectedCameraIndex" placeholder="请选择摄像头" style="width: calc(100% - 48px)" :disabled="cameraList.length === 0">
                      <el-option
                        v-for="cam in cameraList"
                        :key="cam.index"
                        :label="cam.label"
                        :value="cam.index"
                      />
                    </el-select>
                    <el-button
                      type="primary"
                      size="small"
                      :icon="Refresh"
                      @click="loadCameraList"
                      style="width: 40px"
                    />
                  </div>
                  <div v-if="cameraList.length === 0" class="camera-empty-tip">
                    <el-icon size="14"><Warning /></el-icon>
                    <span>未检测到可用摄像头，请检查摄像头连接</span>
                  </div>
                </el-form-item>
              </el-col>
              <el-col :span="18">
                <div class="realtime-buttons">
                  <el-button
                    type="primary"
                    :loading="realtimeLoading"
                    :disabled="selectedCameraIndex === null || isDetecting"
                    @click="handleStartDetection"
                  >
                    <el-icon><VideoCamera /></el-icon>
                    开始检测
                  </el-button>
                  <el-button
                    type="danger"
                    :loading="realtimeLoading"
                    :disabled="!isDetecting"
                    @click="handleStopDetection"
                  >
                    <el-icon><VideoPause /></el-icon>
                    停止检测
                  </el-button>
                  <el-button
                    type="warning"
                    :loading="consulting"
                    :disabled="!isDetecting"
                    @click="handleCloudConsult"
                  >
                    <el-icon><Cloudy /></el-icon>
                    云端复核
                  </el-button>
                </div>
              </el-col>
            </el-row>

            <div v-if="isDetecting" class="video-container">
              <div class="video-wrapper">
                <img
                  :src="videoStreamUrl"
                  class="video-stream"
                  alt="实时视频流"
                  crossorigin="anonymous"
                  @load="handleVideoLoad"
                  @error="handleVideoError"
                />
                <div v-if="!videoLoaded" class="video-loading">
                  <el-icon size="48"><Loading /></el-icon>
                  <p>{{ videoError ? videoError : '正在连接摄像头...' }}</p>
                </div>
              </div>
              <div class="video-status-bar">
                <span class="status-item">帧率: {{ statusData.current_fps.toFixed(1) }} FPS</span>
                <span class="status-item">总帧数: {{ statusData.total_frames }}</span>
                <span class="status-item">处理帧数: {{ statusData.processed_frames }}</span>
              </div>
            </div>

            <div v-else class="video-placeholder-large">
              <el-icon size="64"><VideoPlay /></el-icon>
              <p>请选择摄像头并点击"开始检测"查看实时画面</p>
            </div>

            <div v-if="isDetecting" class="status-panel">
              <el-card shadow="hover">
                <template #header>
                  <span>检测状态</span>
                </template>
                <el-descriptions :column="3" border size="small">
                  <el-descriptions-item label="状态">
                    <el-tag type="success">检测中</el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="当前摄像头">
                    {{ selectedCameraIndex }}
                  </el-descriptions-item>
                  <el-descriptions-item label="FPS">
                    {{ statusData.current_fps.toFixed(1) }}
                  </el-descriptions-item>
                  <el-descriptions-item label="总帧数">
                    {{ statusData.total_frames }}
                  </el-descriptions-item>
                  <el-descriptions-item label="处理帧数">
                    {{ statusData.processed_frames }}
                  </el-descriptions-item>
                  <el-descriptions-item label="违规数">
                    <el-tag :type="statusData.violation_count > 0 ? 'danger' : 'info'">
                      {{ statusData.violation_count }}
                    </el-tag>
                  </el-descriptions-item>
                </el-descriptions>
              </el-card>
            </div>

            <div v-if="consultResult" class="consult-result">
              <el-card shadow="hover">
                <template #header>
                  <span>云端复核结果</span>
                </template>
                <el-descriptions :column="2" border size="small">
                  <el-descriptions-item label="复核类型">
                    {{ consultResult.violation_type_cn || consultResult.violation_type }}
                  </el-descriptions-item>
                  <el-descriptions-item label="耗时">
                    {{ consultResult.duration_ms }} ms
                  </el-descriptions-item>
                  <el-descriptions-item label="DeepSeek确认">
                    <el-tag :type="consultResult.deepseek_result?.is_violation_confirmed ? 'danger' : 'success'">
                      {{ consultResult.deepseek_result?.is_violation_confirmed ? '是' : '否' }}
                    </el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="置信度">
                    {{ (consultResult.deepseek_result?.confidence_adjusted || 0) * 100 }}%
                  </el-descriptions-item>
                </el-descriptions>
                <div v-if="consultResult.deepseek_result?.result_text" class="consult-text">
                  <el-collapse>
                    <el-collapse-item title="DeepSeek 完整回答" name="1">
                      <pre>{{ consultResult.deepseek_result.result_text }}</pre>
                    </el-collapse-item>
                  </el-collapse>
                </div>
              </el-card>
            </div>
          </div>
        </el-tab-pane>
        <el-tab-pane label="精度验证" name="trace">
          <AITrace />
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { uploadFileForAi, getRealtimeCameraList, startRealtimeDetection, stopRealtimeDetection, getRealtimeStatus, forceCloudConsult } from '../api'
import { acquireCameraLock, releaseCameraLock, isCameraLockedByOther } from '../utils/camera_mutex'
import AITrace from './AITrace.vue'
import {
  UploadFilled,
  VideoCamera,
  VideoPlay,
  Cpu,
  Key,
  Check,
  Refresh,
  VideoPause,
  Cloudy,
  Loading
} from '@element-plus/icons-vue'

const router = useRouter()

const BACKEND_URL = window.location.protocol + '//' + window.location.hostname + ':8001'

const activeTab = ref('upload')

const uploadRef = ref(null)
const selectedFile = ref(null)
const violationType = ref('lane_departure')
const userNote = ref('')
const analyzing = ref(false)
const uploadProgress = ref(0)
const result = ref(null)
const savedId = ref(null)

const cameraList = ref([])
const selectedCameraIndex = ref(null)
const isDetecting = ref(false)
const realtimeLoading = ref(false)
const consulting = ref(false)
const videoLoaded = ref(false)
const videoError = ref('')
const videoStreamUrl = ref('')
const statusData = ref({
  running: false,
  camera_index: 0,
  frame_rate: 3,
  current_fps: 0,
  total_frames: 0,
  processed_frames: 0,
  violation_count: 0,
  processing: false,
  cache_size: 0
})
const consultResult = ref(null)

let statusTimer = null

const previewUrl = computed(() => {
  if (!selectedFile.value) return ''
  const file = selectedFile.value.raw
  if (file.type.startsWith('image/')) {
    return URL.createObjectURL(file)
  }
  return ''
})

const yoloDetections = computed(() => {
  if (!result.value?.yolo_detection_result) return []
  const data = result.value.yolo_detection_result
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.detections)) return data.detections
  return []
})

function handleFileChange(file) {
  selectedFile.value = file
  result.value = null
  savedId.value = null
}

function handleExceed(files) {
  ElMessage.warning('一次只能上传一个文件')
}

function formatBbox(bbox) {
  if (!bbox || bbox.length < 4) return '-'
  return `(${bbox[0].toFixed(0)}, ${bbox[1].toFixed(0)}) - (${bbox[2].toFixed(0)}, ${bbox[3].toFixed(0)})`
}

async function handleAnalyze() {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }

  analyzing.value = true
  uploadProgress.value = 0
  result.value = null

  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value.raw)
    formData.append('violation_type', violationType.value)
    formData.append('user_note', userNote.value)
    formData.append('run_ai', 'true')

    const res = await uploadFileForAi(formData, (progress) => {
      uploadProgress.value = progress
    })

    if (res.success) {
      result.value = res.data
      savedId.value = res.data.id
      ElMessage.success('分析完成')
    } else {
      ElMessage.error(res.message || '分析失败')
    }
  } catch (err) {
    console.error('分析失败', err)
    ElMessage.error('分析失败，请检查网络连接')
  } finally {
    analyzing.value = false
    uploadProgress.value = 0
  }
}

async function handleSave() {
  if (savedId.value) {
    ElMessage.success('已保存为违规记录')
    router.push(`/violations/${savedId.value}`)
  } else {
    ElMessage.warning('请先执行分析')
  }
}

async function handleReanalyze() {
  await handleAnalyze()
}

async function loadCameraList() {
  try {
    const res = await getRealtimeCameraList()
    if (res.success) {
      cameraList.value = res.cameras.filter(c => c.available).map(cam => ({
        ...cam,
        label: cam.index === 0 ? `摄像头 0 - 内置摄像头` : `摄像头 ${cam.index} - 外接设备`
      }))
      if (cameraList.value.length > 0 && selectedCameraIndex.value === null) {
        selectedCameraIndex.value = cameraList.value[0].index
      }
    }
  } catch (err) {
    console.error('加载摄像头列表失败', err)
    ElMessage.warning('加载摄像头列表失败，请检查后端服务')
  }
}

let videoTimeout = null

const CAMERA_OWNER = 'AIDetect';

async function handleStartDetection() {
  if (selectedCameraIndex.value === null) {
    ElMessage.warning('请选择摄像头')
    return
  }

  // ======== 摄像头互斥锁：先拿锁再开后端摄像头 ========
  const occupied = isCameraLockedByOther(CAMERA_OWNER);
  if (occupied) {
    const who = occupied.path || occupied.owner || '另一个页面';
    ElMessage.warning(
      `摄像头正在被占用（${who}，${Math.round(occupied.howLongAgoMs / 1000)}s 前启动）。`
      + '请先在其它页面停止检测后再试。'
    );
    return;
  }
  const locked = acquireCameraLock({
    owner: CAMERA_OWNER,
    reason: 'AI检测页面 cv2.VideoCapture(后端)',
    path: '/ai-detect'
  });
  if (!locked) {
    ElMessage.warning('摄像头被其它页面占用，请稍后再试（或关闭其它浏览器标签）。');
    return;
  }

  realtimeLoading.value = true
  videoLoaded.value = false
  videoError.value = ''

  try {
    const res = await startRealtimeDetection(selectedCameraIndex.value)
    if (res.success) {
      isDetecting.value = true
      videoStreamUrl.value = `${BACKEND_URL}/api/realtime/stream?t=${Date.now()}`
      consultResult.value = null
      ElMessage.success('检测已启动（后端YOLO + MJPEG流）')
      startStatusPolling()

      videoTimeout = setTimeout(() => {
        if (!videoLoaded.value && !videoError.value) {
          videoError.value = '连接超时，请检查后端服务是否正常运行'
          ElMessage.warning('视频流连接超时')
        }
      }, 10000)
    } else {
      // 后端启动失败，释放锁
      releaseCameraLock(CAMERA_OWNER);
      ElMessage.error(res.message || '启动失败')
    }
  } catch (err) {
    releaseCameraLock(CAMERA_OWNER);
    console.error('启动检测失败', err)
    ElMessage.error('启动失败，请检查网络连接')
  } finally {
    realtimeLoading.value = false
  }
}

async function handleStopDetection() {
  if (videoTimeout) {
    clearTimeout(videoTimeout)
    videoTimeout = null
  }
  realtimeLoading.value = true
  try {
    const res = await stopRealtimeDetection()
    if (res.success) {
      isDetecting.value = false
      videoStreamUrl.value = ''
      videoLoaded.value = false
      videoError.value = ''
      stopStatusPolling()
      ElMessage.success('检测已停止')
    } else {
      ElMessage.error(res.message || '停止失败')
    }
  } catch (err) {
    console.error('停止检测失败', err)
    ElMessage.error('停止失败')
  } finally {
    realtimeLoading.value = false
    // 无论成功失败，都释放锁
    releaseCameraLock(CAMERA_OWNER);
  }
}

function handleVideoLoad() {
  videoLoaded.value = true
  videoError.value = ''
  if (videoTimeout) {
    clearTimeout(videoTimeout)
    videoTimeout = null
  }
}

function handleVideoError() {
  videoError.value = '视频流连接失败，请检查后端服务'
  if (videoTimeout) {
    clearTimeout(videoTimeout)
    videoTimeout = null
  }
}

async function handleCloudConsult() {
  consulting.value = true
  try {
    const res = await forceCloudConsult()
    consultResult.value = res
    if (res.success || res.deepseek_result?.success) {
      ElMessage.success('云端复核完成')
    } else {
      ElMessage.warning('云端复核部分失败，请查看结果')
    }
  } catch (err) {
    console.error('云端复核失败', err)
    ElMessage.error('云端复核失败')
  } finally {
    consulting.value = false
  }
}

function startStatusPolling() {
  stopStatusPolling()
  statusTimer = setInterval(async () => {
    try {
      const res = await getRealtimeStatus()
      if (res.success && res.data) {
        statusData.value = res.data
        if (!videoLoaded.value && res.data.running) {
          videoLoaded.value = true
        }
      }
    } catch (err) {
      console.error('获取状态失败', err)
    }
  }, 1000)
}

function stopStatusPolling() {
  if (statusTimer) {
    clearInterval(statusTimer)
    statusTimer = null
  }
}

onMounted(() => {
  loadCameraList()
})

onBeforeUnmount(() => {
  stopStatusPolling()
  if (videoTimeout) {
    clearTimeout(videoTimeout)
    videoTimeout = null
  }
  if (isDetecting.value) {
    // 页面离开：调用后端停止 + 释放锁（不等待 Promise）
    handleStopDetection().catch(() => {})
  } else {
    releaseCameraLock(CAMERA_OWNER)
  }
})

onUnmounted(() => {
  stopStatusPolling()
  if (videoTimeout) {
    clearTimeout(videoTimeout)
    videoTimeout = null
  }
  if (isDetecting.value) {
    handleStopDetection()
  }
  releaseCameraLock(CAMERA_OWNER)
})
</script>

<style scoped lang="scss">
.ai-detect {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .upload-section {
    .options-row {
      margin-top: 20px;
    }

    .action-row {
      margin-top: 20px;
      display: flex;
      align-items: center;
    }
  }

  .result-section {
    margin-top: 20px;

    .result-card {
      margin-bottom: 20px;

      .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;

        .duration {
          font-size: 12px;
          color: #999;
        }
      }
    }

    .doubao-text {
      margin-top: 16px;

      pre {
        background: #f5f5f5;
        padding: 12px;
        border-radius: 4px;
        font-size: 13px;
        line-height: 1.6;
        white-space: pre-wrap;
        word-break: break-all;
      }
    }

    .result-actions {
      display: flex;
      gap: 12px;
      margin-top: 20px;
    }
  }

  .no-preview {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 60px 0;
    color: #999;

    p {
      margin-top: 12px;
    }
  }

  .realtime-section {
    .realtime-controls {
      margin-bottom: 20px;

      .realtime-buttons {
        display: flex;
        gap: 12px;
      }

      .camera-select-wrapper {
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .camera-empty-tip {
        display: flex;
        align-items: center;
        gap: 4px;
        margin-top: 8px;
        font-size: 12px;
        color: #e6a23c;
      }
    }

    .video-container {
      margin-bottom: 20px;

      .video-wrapper {
        position: relative;
        border-radius: 8px;
        overflow: hidden;
        background: #000;
        max-height: 500px;

        .video-stream {
          width: 100%;
          height: auto;
          max-height: 500px;
          object-fit: contain;
        }

        .video-loading {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          background: rgba(0, 0, 0, 0.7);
          color: #fff;

          p {
            margin-top: 12px;
            color: #f56c6c;
          }
        }
      }

      .video-status-bar {
        display: flex;
        gap: 20px;
        padding: 10px 15px;
        background: #f5f5f5;
        border-radius: 0 0 8px 8px;
        font-size: 13px;
        color: #666;

        .status-item {
          font-weight: 500;
        }
      }
    }

    .video-placeholder-large {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 100px 0;
      color: #999;
      background: #f5f5f5;
      border-radius: 8px;
      margin-bottom: 20px;

      p {
        margin-top: 16px;
        font-size: 16px;
      }
    }

    .status-panel {
      margin-bottom: 20px;
    }

    .consult-result {
      .consult-text {
        margin-top: 16px;

        pre {
          background: #f5f5f5;
          padding: 12px;
          border-radius: 4px;
          font-size: 13px;
          line-height: 1.6;
          white-space: pre-wrap;
          word-break: break-all;
        }
      }
    }
  }
}
</style>