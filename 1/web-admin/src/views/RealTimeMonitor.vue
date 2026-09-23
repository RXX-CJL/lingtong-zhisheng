<template>
  <div class="realtime-monitor">
    <div class="monitor-header">
      <div class="header-left">
        <el-icon size="28" class="header-icon"><VideoCamera /></el-icon>
        <div class="header-title">
          <h2>实时监控</h2>
          <span class="subtitle">前端摄像头 + 后端YOLO检测 + 行为分析</span>
        </div>
      </div>
      <div class="header-right">
        <el-button type="primary" @click="startDetection" :disabled="isRunning">
          <el-icon><VideoPlay /></el-icon>
          开始检测
        </el-button>
        <el-button type="danger" @click="stopDetection" :disabled="!isRunning">
          <el-icon><Stopwatch /></el-icon>
          停止检测
        </el-button>
      </div>
    </div>

    <!-- M10: 顶部行为统计条 -->
    <div class="behavior-stats-bar">
      <div class="stat-pill">
        <span class="pill-label">平均 FPS</span>
        <span class="pill-value">{{ (status.avg_fps || 0).toFixed(1) }}</span>
      </div>
      <div class="stat-pill">
        <span class="pill-label">已确认违规</span>
        <span class="pill-value confirmed">{{ status.confirmed_count || 0 }}</span>
      </div>
      <div class="stat-pill">
        <span class="pill-label">待确认</span>
        <span class="pill-value pending">{{ status.pending_count || 0 }}</span>
      </div>
      <div class="stat-pill">
        <span class="pill-label">追踪目标</span>
        <span class="pill-value tracking" :class="{ active: trackingInfo.is_tracking }">
          {{ trackingInfo.is_tracking ? `ID:${trackingInfo.track_id}` : '无' }}
        </span>
      </div>
      <div class="stat-pill">
        <span class="pill-label">场景模式</span>
        <el-select
          v-model="currentSceneMode"
          size="small"
          style="width: 130px"
          @change="handleSceneModeChange"
        >
          <el-option label="交通模式" value="traffic" />
          <el-option label="城管模式" value="urban_management" />
          <el-option label="治安模式" value="public_security" />
          <el-option label="全量模式" value="all" />
        </el-select>
      </div>
      <div class="stat-pill tracking-controls">
        <el-button size="small" type="warning" plain :disabled="!trackingInfo.is_tracking" @click="handleStopTracking">
          <el-icon><CircleClose /></el-icon>
          取消追踪
        </el-button>
        <el-button size="small" :disabled="!isRunning" @click="handlePrevTrack">
          <el-icon><ArrowLeft /></el-icon>
          上一目标
        </el-button>
        <el-button size="small" :disabled="!isRunning" @click="handleNextTrack">
          下一目标
          <el-icon><ArrowRight /></el-icon>
        </el-button>
      </div>
    </div>

    <div class="monitor-body">
      <div class="video-section">
        <div class="video-wrapper">
          <video 
            ref="videoRef" 
            class="video-source"
            autoplay
            muted
            playsinline
            :style="{ opacity: isRunning ? 1 : 0 }"
          />
          <canvas ref="captureCanvas" class="capture-canvas" />
          <canvas ref="drawCanvas" class="draw-canvas" />
          <div v-if="!isRunning" class="video-placeholder">
            <el-icon size="64" class="placeholder-icon"><VideoCamera /></el-icon>
            <p>点击"开始检测"查看实时画面</p>
            <p class="hint">前端摄像头 + 后端YOLO检测 + 识别框叠加 + 行为分析</p>
          </div>
          
          <div class="violation-badge" v-if="currentViolation" :class="getViolationClass(currentViolation)">
            <el-icon><Warning /></el-icon>
            <span>{{ currentViolation.violation_type_cn }}</span>
            <span class="confidence">{{ (currentViolation.confidence * 100).toFixed(0) }}%</span>
          </div>
          
          <div class="fps-overlay">
            <span class="fps-value">{{ currentFps.toFixed(1) }} FPS</span>
          </div>
          
          <div class="track-info" v-if="trackedVehicles.length > 0">
            <span>追踪: {{ trackedVehicles.length }} 辆</span>
          </div>

          <!-- M10: 追踪目标红色脉动指示器 -->
          <div
            v-if="trackingInfo.is_tracking && trackingInfo.focus_indicator"
            class="tracking-indicator"
            :style="{
              left: ((trackingInfo.focus_indicator.target_center_x || 0) / Math.max(trackingInfo.focus_indicator.frame_width || 1, 1) * 100) + '%',
              top: ((trackingInfo.focus_indicator.target_center_y || 0) / Math.max(trackingInfo.focus_indicator.frame_height || 1, 1) * 100) + '%'
            }"
          >
            <div class="pulse-ring"></div>
            <div class="pulse-ring delay"></div>
            <div class="pulse-core"></div>
            <div class="track-label">追踪 ID:{{ trackingInfo.track_id }}</div>
          </div>

          <!-- M10: 追踪画中画小窗 -->
          <div class="pip-window" v-if="trackingInfo.is_tracking && pipImageUrl">
            <div class="pip-header">
              <span class="pip-title">
                <el-icon><Aim /></el-icon>
                追踪放大 ID:{{ trackingInfo.track_id }}
              </span>
              <el-icon class="pip-close" @click="handleStopTracking"><CircleClose /></el-icon>
            </div>
            <img :src="pipImageUrl" class="pip-image" alt="tracking crop" />
            <div class="pip-meta">
              <span>变焦: {{ (trackingInfo.focus_indicator?.zoom_level || 1.0).toFixed(1) }}x</span>
              <span>裁剪: {{ trackingInfo.focus_indicator?.crop_size?.[0] || 0 }}×{{ trackingInfo.focus_indicator?.crop_size?.[1] || 0 }}</span>
            </div>
          </div>
        </div>
        
        <div class="video-controls">
          <el-select v-model="cameraIndex" placeholder="选择摄像头" class="camera-select">
            <el-option v-for="cam in cameras" :key="cam.index" :label="`摄像头 ${cam.index}`" :value="cam.index" />
          </el-select>
          <el-button type="warning" @click="handleForceCloudConsult" :disabled="!isRunning">
            <el-icon><Cloudy /></el-icon>
            强制云端咨询
          </el-button>
          <el-button type="success" @click="toggleAudio" :disabled="!isRunning">
            <el-icon>{{ isAudioEnabled ? Mic : Mute }}</el-icon>
            {{ isAudioEnabled ? '关闭语音' : '开启语音' }}
          </el-button>
        </div>
      </div>

      <div class="info-section">
        <div class="info-card">
          <div class="card-header">
            <el-icon><TrendCharts /></el-icon>
            <span>检测状态</span>
          </div>
          <div class="status-grid">
            <div class="status-item">
              <span class="status-label">帧率</span>
              <span class="status-value">{{ currentFps.toFixed(1) }} FPS</span>
            </div>
            <div class="status-item">
              <span class="status-label">处理帧</span>
              <span class="status-value">{{ status.processed_frames }}</span>
            </div>
            <div class="status-item">
              <span class="status-label">违规数</span>
              <span class="status-value highlight">{{ status.violation_count }}</span>
            </div>
            <div class="status-item">
              <span class="status-label">状态</span>
              <span :class="['status-value', isRunning ? 'online' : 'offline']">
                {{ isRunning ? '运行中' : '已停止' }}
              </span>
            </div>
            <div class="status-item">
              <span class="status-label">追踪数</span>
              <span class="status-value">{{ trackedVehicles.length }}</span>
            </div>
            <div class="status-item">
              <span class="status-label">缓存帧</span>
              <span class="status-value">{{ status.cache_size || 0 }}</span>
            </div>
          </div>
        </div>

        <div class="info-card">
          <div class="card-header">
            <el-icon><Setting /></el-icon>
            <span>检测参数</span>
          </div>
          <div class="params-grid">
            <div class="param-item">
              <label>置信度阈值</label>
              <el-slider 
                v-model="detectParams.confidence" 
                :min="0.1" 
                :max="0.9" 
                :step="0.05"
                :disabled="!isRunning"
              />
              <span class="param-value">{{ detectParams.confidence.toFixed(2) }}</span>
            </div>
            <div class="param-item">
              <label>IOU阈值</label>
              <el-slider 
                v-model="detectParams.iou" 
                :min="0.1" 
                :max="0.9" 
                :step="0.05"
                :disabled="!isRunning"
              />
              <span class="param-value">{{ detectParams.iou.toFixed(2) }}</span>
            </div>
            <div class="param-item">
              <label>检测间隔</label>
              <el-slider 
                v-model="detectParams.interval" 
                :min="200" 
                :max="2000" 
                :step="100"
                :disabled="!isRunning"
                @change="onIntervalChange"
              />
              <span class="param-value">{{ detectParams.interval }}ms</span>
            </div>
          </div>
        </div>

        <div class="info-card">
          <div class="card-header">
            <el-icon><Warning /></el-icon>
            <span>行为分析</span>
            <span class="detect-count">{{ behaviors.length }}</span>
          </div>
          <div class="behavior-list" v-if="behaviors.length > 0">
            <div v-for="(b, idx) in behaviors.slice(0, 8)" :key="idx" class="behavior-item">
              <span class="bh-icon" :class="b.is_violation ? 'violation' : 'normal'"></span>
              <span class="bh-name">{{ b.behavior_type_cn || b.behavior_type }}</span>
              <span class="bh-vehicle">车{{ b.vehicle_id }}</span>
              <span class="bh-conf">{{ (b.confidence * 100).toFixed(0) }}%</span>
            </div>
          </div>
          <div v-else class="empty-behavior">
            <el-icon><CircleCheck /></el-icon>
            <span>暂无行为分析数据</span>
          </div>
        </div>

        <div class="info-card">
          <div class="card-header">
            <el-icon><Filter /></el-icon>
            <span>目标筛选</span>
          </div>
          <div class="filter-tags">
            <el-tag 
              v-for="cat in detectionCategories" 
              :key="cat.value"
              :class="['filter-tag', selectedCategories.includes(cat.value) ? 'active' : '']"
              @click="toggleCategory(cat.value)"
            >
              {{ cat.label }}
            </el-tag>
          </div>
          <div class="quick-filters">
            <el-button size="small" @click="selectAllCategories">全选</el-button>
            <el-button size="small" @click="clearAllCategories">清除</el-button>
          </div>
        </div>

        <div class="info-card">
          <div class="card-header">
            <el-icon><Search /></el-icon>
            <span>检测目标</span>
            <span class="detect-count">{{ latestDetections.length }}</span>
          </div>
          <div class="detection-list" v-if="filteredDetections.length > 0">
            <div v-for="(det, idx) in filteredDetections.slice(0, 8)" :key="idx" class="detection-item">
              <span class="det-icon" :style="{ background: getDetectionColor(det.class_name) }"></span>
              <span class="det-name">{{ det.class_name_cn || det.class_name }}</span>
              <span class="det-confidence">{{ (det.confidence * 100).toFixed(0) }}%</span>
            </div>
          </div>
          <div v-else class="empty-detection">
            <el-icon><InfoFilled /></el-icon>
            <span>暂无检测目标</span>
          </div>
        </div>

        <div class="info-card violation-alerts">
          <div class="card-header">
            <el-icon><Bell /></el-icon>
            <span>违规告警</span>
            <span class="alert-count">{{ violationHistory.length }}</span>
          </div>
          <div class="violation-list">
            <div v-for="(vio, idx) in violationHistory.slice(0, 10)" :key="idx" class="violation-item">
              <div class="vio-badge" :class="getViolationClass(vio)">
                {{ vio.violation_type_cn }}
              </div>
              <span class="vio-time">{{ formatTime(vio.timestamp) }}</span>
              <span class="vio-conf">{{ (vio.confidence * 100).toFixed(0) }}%</span>
            </div>
          </div>
          <div v-if="violationHistory.length === 0" class="empty-violation">
            <el-icon><CircleCheck /></el-icon>
            <span>暂无违规告警</span>
          </div>
        </div>

        <div class="info-card">
          <div class="card-header">
            <el-icon><Clock /></el-icon>
            <span>检测记录</span>
            <span class="detect-count">{{ detectionHistory.length }}</span>
          </div>
          <div class="history-list">
            <div v-for="(record, idx) in detectionHistory.slice(0, 10)" :key="idx" class="history-item">
              <span class="history-time">{{ formatTime(record.timestamp) }}</span>
              <span class="history-dets">{{ record.detection_count }}个目标</span>
              <span v-if="record.violation_count > 0" class="history-violations">{{ record.violation_count }}违规</span>
            </div>
          </div>
          <div v-if="detectionHistory.length === 0" class="empty-history">
            <el-icon><InfoFilled /></el-icon>
            <span>暂无检测记录</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, onBeforeUnmount } from 'vue';
import { ElMessage } from 'element-plus';
import { VideoCamera, VideoPlay, Stopwatch, Cloudy, Warning, TrendCharts, Search, Bell, InfoFilled, CircleCheck, Setting, Filter, Clock, Mic, Mute, Aim, CircleClose, ArrowLeft, ArrowRight } from '@element-plus/icons-vue';
import { getRealtimeCameraList, detectFrame, forceCloudConsult, startTracking, stopTracking, getTrackingStatus, setSceneMode } from '../api';
import { acquireCameraLock, releaseCameraLock, isCameraLockedByOther, onCameraLockChanged } from '../utils/camera_mutex';

const BACKEND_URL = window.location.protocol + '//' + window.location.hostname + ':8001';

const isRunning = ref(false);
const cameraIndex = ref(0);
const cameras = ref([]);
const currentFps = ref(0);
const status = ref({
  processed_frames: 0,
  violation_count: 0,
  cache_size: 0,
  avg_fps: 0,
  pending_count: 0,
  confirmed_count: 0
});
const currentViolation = ref(null);
const latestDetections = ref([]);
const violationHistory = ref([]);
const resultImageUrl = ref('');
const trackedVehicles = ref([]);
const isAudioEnabled = ref(false);
const behaviors = ref([]);
const behaviorStats = ref({
  total_behaviors: 0,
  violation_behaviors: 0,
  behavior_counts: {},
  tracked_vehicles: 0
});

// M10: 追踪相关状态
const trackingInfo = ref({
  is_tracking: false,
  track_id: null,
  focus_indicator: null
});
const pipImageUrl = ref('');
const currentSceneMode = ref('all');
let trackingPollInterval = null;
let currentTrackIndex = 0;

const detectParams = ref({
  confidence: 0.5,
  iou: 0.45,
  interval: 500
});

const detectionCategories = ref([
  { label: '车辆', value: 'vehicle' },
  { label: '行人', value: 'person' },
  { label: '头盔', value: 'helmet' },
  { label: '红绿灯', value: 'traffic_light' },
  { label: '车道线', value: 'lane_line' }
]);

const selectedCategories = ref(['vehicle', 'person', 'helmet', 'traffic_light', 'lane_line']);

const detectionHistory = ref([]);

const videoRef = ref(null);
const captureCanvas = ref(null);
const drawCanvas = ref(null);

let mediaStream = null;
let detectInterval = null;
let lastFrameTime = 0;
let currentDetections = [];

const filteredDetections = computed(() => {
  if (selectedCategories.value.length === 0) return latestDetections.value;
  
  const categoryMap = {
    'vehicle': ['car', 'motorcycle', 'truck', 'bus', 'bicycle'],
    'person': ['person', 'rider', 'motorcyclist', 'cyclist'],
    'helmet': ['helmet', 'no_helmet'],
    'traffic_light': ['traffic_light', 'red_light', 'green_light', 'yellow_light'],
    'lane_line': ['lane_line', 'road_line', 'white_line', 'yellow_line']
  };
  
  const allowedClasses = new Set();
  selectedCategories.value.forEach(cat => {
    (categoryMap[cat] || []).forEach(cls => allowedClasses.add(cls));
  });
  
  return latestDetections.value.filter(det => allowedClasses.has(det.class_name));
});

const loadCameras = async () => {
  try {
    const res = await getRealtimeCameraList();
    if (res.success) {
      cameras.value = res.cameras || [];
    }
  } catch (error) {
    console.error('获取摄像头列表失败:', error);
  }
};

const CAMERA_OWNER = 'RealTimeMonitor';

const startDetection = async () => {
  // ============ 摄像头互斥：先拿锁 ============
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
    reason: '实时监控页面 getUserMedia',
    path: '/realtime'
  });
  if (!locked) {
    ElMessage.warning('摄像头被其它页面占用，请稍后再试（或关闭其它浏览器标签）。');
    return;
  }
  try {
    const constraints = {
      video: {
        deviceId: cameras.value[cameraIndex.value]?.deviceId || undefined,
        width: { ideal: 1280 },
        height: { ideal: 720 },
        facingMode: 'environment'
      },
      audio: false
    };

    mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
    if (!videoRef.value) throw new Error('video元素未就绪');
    videoRef.value.srcObject = mediaStream;

    // 关键修复：部分浏览器 autoplay+muted 仍不会自动起播，显式 play + 等待 loadedmetadata
    try {
      await videoRef.value.play();
    } catch (playErr) {
      console.warn('video.play() 被拦截，稍后重试:', playErr);
    }

    // 等待视频元数据就绪（确保 videoWidth / videoHeight 可用）
    const metaReady = new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error('视频元数据加载超时(3s)，请检查摄像头是否被其它程序占用')), 3000);
      videoRef.value.addEventListener('loadedmetadata', () => {
        clearTimeout(timeout);
        // 再给一帧时间，确保首帧渲染出来
        setTimeout(resolve, 100);
      }, { once: true });
      // 部分浏览器 loadedmetadata 已触发过但未注册监听，兜底检查
      if (videoRef.value.readyState >= 1 && videoRef.value.videoWidth > 0) {
        clearTimeout(timeout);
        setTimeout(resolve, 100);
      }
    });
    try {
      await metaReady;
    } catch (metaErr) {
      ElMessage.warning(metaErr.message || '视频加载缓慢，已继续启动检测');
    }

    isRunning.value = true;
    lastFrameTime = performance.now();
    startDetectPolling();
    ElMessage.success('检测已启动（前端摄像头 + 后端YOLO）');
  } catch (error) {
    console.error('启动检测失败:', error);
    ElMessage.error('启动检测失败: ' + (error.message || error));
    isRunning.value = false;
    // 清理占用的摄像头
    if (mediaStream) {
      mediaStream.getTracks().forEach(track => track.stop());
      mediaStream = null;
    }
    // 关键：拿了锁但实际打开失败 -> 必须释放
    releaseCameraLock(CAMERA_OWNER);
  }
};

const stopDetection = () => {
  isRunning.value = false;
  resultImageUrl.value = '';

  if (mediaStream) {
    mediaStream.getTracks().forEach(track => track.stop());
    mediaStream = null;
  }

  stopDetectPolling();
  currentViolation.value = null;
  
  ElMessage.success('检测已停止');
};

const startDetectPolling = () => {
  detectInterval = setInterval(() => {
    captureAndDetect();
  }, detectParams.value.interval);
};

const stopDetectPolling = () => {
  if (detectInterval) {
    clearInterval(detectInterval);
    detectInterval = null;
  }
};

const onIntervalChange = () => {
  if (isRunning.value) {
    stopDetectPolling();
    startDetectPolling();
    ElMessage.info(`检测间隔已调整为 ${detectParams.value.interval}ms`);
  }
};

const captureAndDetect = async () => {
  if (!videoRef.value || !captureCanvas.value || !isRunning.value) return;
  
  try {
    const video = videoRef.value;
    const canvas = captureCanvas.value;
    
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    const frameBase64 = canvas.toDataURL('image/jpeg', 0.8).split(',')[1];
    
    const res = await detectFrame(frameBase64);
    if (res.success) {
      const now = performance.now();
      currentFps.value = 1000 / (now - lastFrameTime);
      lastFrameTime = now;
      
      status.value = {
        processed_frames: res.processed_count || 0,
        violation_count: res.violation_count || 0,
        cache_size: res.cache_size || 0,
        avg_fps: res.avg_fps || status.value.avg_fps || 0,
        pending_count: res.pending_count || 0,
        confirmed_count: res.confirmed_count || 0
      };
      
      currentDetections = res.detections || [];
      trackedVehicles.value = res.tracked_vehicles || [];
      behaviors.value = res.behaviors || [];
      drawDetectionBoxes();
      
      const allViolations = [];
      if (res.behaviors) {
        res.behaviors.forEach(b => {
          if (b.is_violation) {
            allViolations.push({
              violation_type_cn: b.behavior_type_cn || b.behavior_type,
              confidence: b.confidence,
              vehicle_id: b.vehicle_id,
              timestamp: new Date().toISOString()
            });
          }
        });
      }
      if (res.violations) {
        res.violations.forEach(v => {
          if (v.source !== 'behavior_engine') {
            allViolations.push({
              violation_type_cn: v.violation_type_cn || v.violation_type,
              confidence: v.confidence,
              vehicle_id: null,
              timestamp: new Date().toISOString()
            });
          }
        });
      }
      
      detectionHistory.value.unshift({
        timestamp: new Date().toISOString(),
        detection_count: res.detections?.length || 0,
        violation_count: allViolations.length
      });
      if (detectionHistory.value.length > 50) {
        detectionHistory.value.pop();
      }
      
      if (allViolations.length > 0) {
        currentViolation.value = allViolations[0];
        violationHistory.value.unshift(allViolations[0]);
        if (violationHistory.value.length > 50) {
          violationHistory.value.pop();
        }
        
        if (isAudioEnabled.value) {
          speakViolation(allViolations[0]);
        }
      } else {
        currentViolation.value = null;
      }
      
      latestDetections.value = res.detections || [];
    }
  } catch (error) {
    console.error('帧检测失败:', error);
  }
};

const toggleAudio = () => {
  isAudioEnabled.value = !isAudioEnabled.value;
  ElMessage.info(isAudioEnabled.value ? '语音播报已开启' : '语音播报已关闭');
};

const speakViolation = (violation) => {
  if ('speechSynthesis' in window) {
    const utterance = new SpeechSynthesisUtterance(`检测到${violation.violation_type_cn}，置信度${(violation.confidence * 100).toFixed(0)}%`);
    utterance.lang = 'zh-CN';
    utterance.rate = 1.0;
    window.speechSynthesis.speak(utterance);
  }
};

const toggleCategory = (value) => {
  const index = selectedCategories.value.indexOf(value);
  if (index > -1) {
    selectedCategories.value.splice(index, 1);
  } else {
    selectedCategories.value.push(value);
  }
};

const selectAllCategories = () => {
  selectedCategories.value = detectionCategories.value.map(cat => cat.value);
};

const clearAllCategories = () => {
  selectedCategories.value = [];
};

const drawDetectionBoxes = () => {
  if (!drawCanvas.value || !videoRef.value) return;
  
  const canvas = drawCanvas.value;
  const video = videoRef.value;
  
  const wrapper = canvas.parentElement;
  const wrapperWidth = wrapper.clientWidth;
  const wrapperHeight = wrapper.clientHeight;
  
  canvas.width = wrapperWidth;
  canvas.height = wrapperHeight;
  
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  
  const scaleX = wrapperWidth / (video.videoWidth || 640);
  const scaleY = wrapperHeight / (video.videoHeight || 480);
  const scale = Math.min(scaleX, scaleY);
  
  const offsetX = (wrapperWidth - (video.videoWidth || 640) * scale) / 2;
  const offsetY = (wrapperHeight - (video.videoHeight || 480) * scale) / 2;
  
  const detToTrack = new Map();
  trackedVehicles.value.forEach(track => {
    const bboxStr = (track.bbox || []).join(',');
    detToTrack.set(bboxStr, track);
  });
  
  for (const det of currentDetections) {
    const bbox = det.bbox || [0, 0, 0, 0];
    const class_name = det.class_name || '';
    const class_name_cn = det.class_name_cn || class_name;
    const confidence = det.confidence || 0;

    const x1 = bbox[0] * scale + offsetX;
    const y1 = bbox[1] * scale + offsetY;
    const x2 = bbox[2] * scale + offsetX;
    const y2 = bbox[3] * scale + offsetY;

    // M10: bbox 颜色优先按"该车辆违规类型"着色，未违规时按检测类别色
    const bboxStr = bbox.join(',');
    const track = detToTrack.get(bboxStr);
    let color = getDetectionColor(class_name);
    let violationTag = '';
    if (track && track.id !== undefined) {
      const vType = getVehicleViolationType(track.id);
      if (vType) {
        color = getViolationColor(vType);
        violationTag = `[${vType}]`;
      }
    }
    ctx.strokeStyle = color;
    ctx.lineWidth = 3;
    ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

    let label = `${class_name_cn} ${(confidence * 100).toFixed(0)}%`;
    if (track && track.id !== undefined) {
      label = `ID:${track.id} ${class_name_cn}${violationTag}`;
    }
    
    ctx.fillStyle = color;
    ctx.font = 'bold 14px Arial';
    const labelWidth = ctx.measureText(label).width;
    
    ctx.fillRect(x1, y1 - 22, labelWidth + 8, 20);
    ctx.fillStyle = '#fff';
    ctx.font = '12px Arial';
    ctx.fillText(label, x1 + 4, y1 - 6);
    
    if (track) {
      const speed = track.speed || 0;
      const direction = track.direction || '';
      if (speed > 0 || direction) {
        let infoText = '';
        if (speed > 0) infoText += `${speed.toFixed(0)}km/h`;
        if (direction) infoText += ` ${direction}`;
        
        if (infoText) {
          ctx.fillStyle = '#1890ff';
          ctx.font = 'bold 12px Arial';
          const infoWidth = ctx.measureText(infoText).width;
          ctx.fillRect(x1, y1 + (y2 - y1) - 18, infoWidth + 6, 16);
          ctx.fillStyle = '#fff';
          ctx.font = '11px Arial';
          ctx.fillText(infoText, x1 + 3, y1 + (y2 - y1) - 6);
        }
      }
    }
  }
};

const handleForceCloudConsult = async () => {
  try {
    const res = await forceCloudConsult();
    console.log('云端咨询结果:', res);
  } catch (error) {
    console.error('云端咨询失败:', error);
  }
};

const getViolationClass = (vio) => {
  if (!vio) return '';
  const conf = vio.confidence || 0;
  if (conf >= 0.75) return 'high';
  if (conf >= 0.4) return 'medium';
  return 'low';
};

const getDetectionColor = (className) => {
  const colors = {
    'motorcycle': '#1890ff',
    'car': '#1890ff',
    'person': '#52c41a',
    'helmet': '#52c41a',
    'no_helmet': '#ff4d4f',
    'red_light': '#ff4d4f',
    'green_light': '#52c41a',
    'lane_line': '#faad14'
  };
  return colors[className] || '#999';
};

// M10: 违规类型颜色表（与 M05/M07 颜色配置统一）
// 闯红灯=深红, 逆行=橙, 违停=紫, 未戴头盔=青, 占道经营=蓝, 人员聚集=黄
const VIOLATION_COLOR_MAP = {
  'red_light': '#C41E3A',          // 深红
  'wrong_way': '#FF8C00',          // 橙
  'illegal_parking': '#800080',    // 紫
  'no_helmet': '#00BFBF',          // 青
  'speeding': '#DC143C',           // 深红
  'street_stall': '#1890FF',       // 蓝（城管）
  'crowd_gathering': '#FFD700',    // 黄（治安）
  'abnormal_assembly': '#FFD700'   // 黄（治安）
};

const getViolationColor = (violationType) => {
  return VIOLATION_COLOR_MAP[violationType] || '#ff4d4f';
};

// M10: 获取车辆当前违规类型（用于 bbox 着色）
const getVehicleViolationType = (trackId) => {
  if (!behaviors.value) return null;
  const v = behaviors.value.find(b => b.is_violation && b.vehicle_id === trackId);
  return v ? v.behavior_type : null;
};

// M10: 追踪相关方法
const startTrackingPolling = () => {
  if (trackingPollInterval) clearInterval(trackingPollInterval);
  trackingPollInterval = setInterval(async () => {
    if (!trackingInfo.value.is_tracking) {
      // 非追踪状态不拉取裁剪图，但保持一次轻量状态查询
      return;
    }
    try {
      const res = await getTrackingStatus();
      if (res.success) {
        trackingInfo.value = {
          is_tracking: res.is_tracking,
          track_id: res.track_id,
          focus_indicator: res.focus_indicator
        };
        if (res.crop_image_base64) {
          pipImageUrl.value = res.crop_image_base64;
        }
      }
    } catch (err) {
      console.warn('追踪状态查询失败', err);
    }
  }, 500);
};

const stopTrackingPolling = () => {
  if (trackingPollInterval) {
    clearInterval(trackingPollInterval);
    trackingPollInterval = null;
  }
};

const handleStartTracking = async (trackId) => {
  try {
    const res = await startTracking(trackId);
    if (res.success) {
      trackingInfo.value.is_tracking = true;
      trackingInfo.value.track_id = trackId;
      ElMessage.success(res.message || `已锁定追踪目标 ID=${trackId}`);
      startTrackingPolling();
    } else {
      ElMessage.error(res.message || '锁定失败');
    }
  } catch (err) {
    ElMessage.error('启动追踪失败');
  }
};

const handleStopTracking = async () => {
  try {
    const res = await stopTracking();
    if (res.success) {
      trackingInfo.value = { is_tracking: false, track_id: null, focus_indicator: null };
      pipImageUrl.value = '';
      ElMessage.success(res.message || '已取消追踪');
      stopTrackingPolling();
    }
  } catch (err) {
    ElMessage.error('取消追踪失败');
  }
};

const handlePrevTrack = async () => {
  if (trackedVehicles.value.length === 0) {
    ElMessage.info('当前无追踪目标');
    return;
  }
  currentTrackIndex = (currentTrackIndex - 1 + trackedVehicles.value.length) % trackedVehicles.value.length;
  const target = trackedVehicles.value[currentTrackIndex];
  if (target?.id !== undefined) {
    await handleStartTracking(target.id);
  }
};

const handleNextTrack = async () => {
  if (trackedVehicles.value.length === 0) {
    ElMessage.info('当前无追踪目标');
    return;
  }
  currentTrackIndex = (currentTrackIndex + 1) % trackedVehicles.value.length;
  const target = trackedVehicles.value[currentTrackIndex];
  if (target?.id !== undefined) {
    await handleStartTracking(target.id);
  }
};

const handleSceneModeChange = async (val) => {
  try {
    const res = await setSceneMode(val);
    if (res.success) {
      ElMessage.success(res.message || `已切换到 ${val}`);
    } else {
      ElMessage.error(res.message || '切换失败');
    }
  } catch (err) {
    ElMessage.error('切换场景模式失败');
  }
};

const formatTime = (timestamp) => {
  if (!timestamp) return '';
  const d = new Date(timestamp);
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}:${d.getSeconds().toString().padStart(2, '0')}`;
};

onMounted(() => {
  loadCameras();
});

// 页面卸载 / 切走路由：强制关闭摄像头并释放互斥锁（用户要求"离开页面自动关摄像头"）
onBeforeUnmount(() => {
  if (isRunning.value || mediaStream) {
    stopDetectPolling();
    stopTrackingPolling();
    if (mediaStream) {
      mediaStream.getTracks().forEach(track => track.stop());
      mediaStream = null;
    }
    isRunning.value = false;
    releaseCameraLock(CAMERA_OWNER);
  }
});

onUnmounted(() => {
  stopDetectPolling();
  stopTrackingPolling();
  if (mediaStream) {
    mediaStream.getTracks().forEach(track => track.stop());
    mediaStream = null;
  }
  releaseCameraLock(CAMERA_OWNER);
});
</script>

<style scoped lang="scss">
.realtime-monitor {
  max-width: 1600px;
  margin: 0 auto;
  padding: 20px;
}

.monitor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 16px 20px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;

    .header-icon {
      color: #1890ff;
    }

    .header-title {
      h2 {
        margin: 0;
        font-size: 22px;
        font-weight: 600;
        color: #333;
      }

      .subtitle {
        display: block;
        font-size: 13px;
        color: #999;
        margin-top: 2px;
      }
    }
  }

  .header-right {
    display: flex;
    gap: 12px;
  }
}

.monitor-body {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 20px;
}

.video-section {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

  .video-wrapper {
    position: relative;
    width: 100%;
    aspect-ratio: 16 / 9;
    background: #000;
    border-radius: 8px;
    overflow: hidden;
    margin-bottom: 16px;

    .video-source {
      width: 100%;
      height: 100%;
      object-fit: cover;
      position: absolute;
      top: 0;
      left: 0;
      z-index: 1;
      transition: opacity 0.3s ease;
    }

    .capture-canvas {
      display: none;
    }

    .draw-canvas {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      z-index: 2;
      pointer-events: none;
    }

    .video-placeholder {
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      height: 100%;
      color: #666;
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      z-index: 10;

      .placeholder-icon {
        margin-bottom: 16px;
        opacity: 0.4;
      }

      p {
        margin: 0;
        font-size: 15px;

        &.hint {
          font-size: 13px;
          color: #999;
          margin-top: 8px;
        }
      }
    }

    .violation-badge {
      position: absolute;
      top: 16px;
      left: 16px;
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 16px;
      background: rgba(255, 77, 79, 0.9);
      border-radius: 6px;
      color: #fff;
      font-size: 14px;
      font-weight: 600;
      animation: pulse 1s infinite;
      z-index: 20;

      .confidence {
        font-size: 12px;
        opacity: 0.8;
      }

      &.medium {
        background: rgba(250, 173, 20, 0.9);
      }

      &.low {
        background: rgba(255, 149, 0, 0.9);
        animation: none;
      }
    }

    .fps-overlay {
      position: absolute;
      top: 16px;
      right: 16px;
      padding: 6px 12px;
      background: rgba(0, 0, 0, 0.6);
      border-radius: 4px;
      color: #fff;
      font-size: 12px;
      z-index: 20;

      .fps-value {
        font-weight: 600;
      }
    }

    .track-info {
      position: absolute;
      bottom: 16px;
      left: 16px;
      padding: 6px 12px;
      background: rgba(0, 137, 255, 0.8);
      border-radius: 4px;
      color: #fff;
      font-size: 12px;
      z-index: 20;
    }
  }

  .video-controls {
    display: flex;
    align-items: center;
    gap: 12px;

    .camera-select {
      width: 160px;
    }
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.info-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.info-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

  .card-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 16px;
    font-weight: 600;
    font-size: 15px;
    color: #333;

    .alert-count {
      margin-left: auto;
      font-size: 12px;
      padding: 2px 8px;
      background: #ff4d4f;
      color: #fff;
      border-radius: 10px;
    }
  }

  .status-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;

    .status-item {
      display: flex;
      justify-content: space-between;
      padding: 10px 12px;
      background: #f5f7fa;
      border-radius: 8px;

      .status-label {
        font-size: 13px;
        color: #666;
      }

      .status-value {
        font-size: 15px;
        font-weight: 600;
        color: #333;

        &.highlight {
          color: #ff4d4f;
        }

        &.online {
          color: #52c41a;
        }

        &.offline {
          color: #ff4d4f;
        }
      }
    }
  }

  .detection-list {
    max-height: 200px;
    overflow-y: auto;

    .detection-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 8px 0;
      border-bottom: 1px solid #f0f0f0;

      &:last-child {
        border-bottom: none;
      }

      .det-icon {
        width: 8px;
        height: 8px;
        border-radius: 50%;
      }

      .det-name {
        flex: 1;
        font-size: 13px;
        color: #333;
      }

      .det-confidence {
        font-size: 12px;
        color: #999;
      }
    }

    .empty-detection {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 30px;
      color: #999;

      span {
        margin-top: 8px;
        font-size: 13px;
      }
    }
  }

  &.violation-alerts {
    flex: 1;
    min-height: 200px;

    .violation-list {
      max-height: 250px;
      overflow-y: auto;

      .violation-item {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 0;
        border-bottom: 1px solid #f0f0f0;

        &:last-child {
          border-bottom: none;
        }

        .vio-badge {
          padding: 3px 10px;
          border-radius: 4px;
          font-size: 12px;
          font-weight: 500;
          color: #fff;
          background: #ff4d4f;

          &.medium {
            background: #faad14;
          }

          &.low {
            background: #ff9500;
          }
        }

        .vio-time {
          flex: 1;
          font-size: 12px;
          color: #999;
        }

        .vio-conf {
          font-size: 12px;
          color: #666;
        }
      }

      .empty-violation {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 30px;
        color: #52c41a;

        span {
          margin-top: 8px;
          font-size: 13px;
        }
      }
    }

    .params-grid {
      display: flex;
      flex-direction: column;
      gap: 16px;

      .param-item {
        label {
          display: block;
          font-size: 13px;
          color: #666;
          margin-bottom: 8px;
        }

        .param-value {
          display: block;
          text-align: right;
          font-size: 13px;
          color: #1890ff;
          font-weight: 600;
          margin-top: 4px;
        }
      }
    }

    .filter-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 12px;

      .filter-tag {
        cursor: pointer;
        transition: all 0.2s;

        &:hover {
          opacity: 0.8;
        }

        &.active {
          background: #1890ff;
          border-color: #1890ff;
          color: #fff;
        }
      }
    }

    .quick-filters {
      display: flex;
      gap: 8px;
      justify-content: flex-end;
    }

    .detect-count {
      margin-left: auto;
      font-size: 12px;
      padding: 2px 8px;
      background: #1890ff;
      color: #fff;
      border-radius: 10px;
    }

    .history-list {
      max-height: 180px;
      overflow-y: auto;

      .history-item {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 0;
        border-bottom: 1px solid #f0f0f0;

        &:last-child {
          border-bottom: none;
        }

        .history-time {
          font-size: 12px;
          color: #999;
          min-width: 80px;
        }

        .history-dets {
          flex: 1;
          font-size: 13px;
          color: #333;
        }

        .history-violations {
          font-size: 12px;
          color: #ff4d4f;
          font-weight: 500;
        }
      }

      .empty-history {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 30px;
        color: #999;

        span {
          margin-top: 8px;
          font-size: 13px;
        }
      }
    }

    .behavior-list {
      max-height: 180px;
      overflow-y: auto;

      .behavior-item {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 0;
        border-bottom: 1px solid #f0f0f0;

        &:last-child {
          border-bottom: none;
        }

        .bh-icon {
          width: 8px;
          height: 8px;
          border-radius: 50%;

          &.violation {
            background: #ff4d4f;
          }

          &.normal {
            background: #52c41a;
          }
        }

        .bh-name {
          flex: 1;
          font-size: 13px;
          color: #333;
        }

        .bh-vehicle {
          font-size: 12px;
          color: #1890ff;
          font-weight: 500;
        }

        .bh-conf {
          font-size: 12px;
          color: #999;
        }
      }

      .empty-behavior {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 30px;
        color: #52c41a;

        span {
          margin-top: 8px;
          font-size: 13px;
        }
      }
    }
  }
}

@media (max-width: 1200px) {
  .monitor-body {
    grid-template-columns: 1fr;
  }

  .info-section {
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  }
}

/* ============== M10: 顶部行为统计条 ============== */
.behavior-stats-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  padding: 12px 16px;
  margin-bottom: 16px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

  .stat-pill {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 14px;
    background: linear-gradient(135deg, #f5f7fa 0%, #e8edf3 100%);
    border-radius: 20px;
    font-size: 13px;

    .pill-label {
      color: #666;
    }

    .pill-value {
      font-weight: 600;
      color: #1890ff;
      font-size: 15px;

      &.confirmed { color: #52c41a; }
      &.pending { color: #faad14; }
      &.tracking { color: #999; }
      &.tracking.active { color: #ff4d4f; }
    }
  }

  .tracking-controls {
    margin-left: auto;
    background: transparent;
    padding: 0;
  }
}

/* ============== M10: 追踪红色脉动指示器 ============== */
.tracking-indicator {
  position: absolute;
  transform: translate(-50%, -50%);
  z-index: 6;
  pointer-events: none;
  width: 40px;
  height: 40px;

  .pulse-ring {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 30px;
    height: 30px;
    border: 3px solid #ff4d4f;
    border-radius: 50%;
    animation: pulse-ring-anim 1.4s ease-out infinite;
  }

  .pulse-ring.delay {
    animation-delay: 0.7s;
  }

  .pulse-core {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 12px;
    height: 12px;
    background: #ff4d4f;
    border-radius: 50%;
    box-shadow: 0 0 12px rgba(255, 77, 79, 0.8);
  }

  .track-label {
    position: absolute;
    top: 100%;
    left: 50%;
    transform: translateX(-50%);
    margin-top: 6px;
    padding: 2px 8px;
    background: rgba(255, 77, 79, 0.92);
    color: #fff;
    font-size: 11px;
    border-radius: 4px;
    white-space: nowrap;
  }
}

@keyframes pulse-ring-anim {
  0% {
    width: 12px;
    height: 12px;
    opacity: 1;
  }
  100% {
    width: 50px;
    height: 50px;
    opacity: 0;
  }
}

/* ============== M10: 追踪画中画小窗 ============== */
.pip-window {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 240px;
  background: rgba(0, 0, 0, 0.85);
  border: 2px solid #ff4d4f;
  border-radius: 8px;
  overflow: hidden;
  z-index: 7;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);

  .pip-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 4px 8px;
    background: rgba(255, 77, 79, 0.2);
    color: #fff;
    font-size: 12px;

    .pip-title {
      display: flex;
      align-items: center;
      gap: 4px;
      font-weight: 600;
    }

    .pip-close {
      cursor: pointer;
      color: #fff;
      font-size: 14px;

      &:hover { color: #ff4d4f; }
    }
  }

  .pip-image {
    width: 100%;
    display: block;
    background: #000;
  }

  .pip-meta {
    display: flex;
    justify-content: space-between;
    padding: 4px 8px;
    background: rgba(0, 0, 0, 0.7);
    color: #ddd;
    font-size: 11px;
  }
}
</style>