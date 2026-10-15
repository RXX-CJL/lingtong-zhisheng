<!--
  测速标定 + 信号灯 ROI 参数面板（2026-10-06 由 DSH 新建）

  ## 为什么要有这个面板（用户目标：闯红灯识别在管理端落地）
  · 后端 2026-10-06 已做到"车道级（受控方向）灯态"：只统计人工标注
    `traffic_light_roi` 内的信号灯。实测 4 轮：每循环恰好 1 次真违规、0 误报、
    判色 95.6%~97%；**不标 ROI** 时退回"画面里任意一盏灯" → 每循环误报 5~7 次。
    → 也就是说：**管理端不提供 ROI 标注，这个能力就没法在换视频后复用。**
  · 同理 `stop_line_y`（停止线）换视频必须重标，否则闯红灯判据位置是错的。
  · 测速标定：`camera_height_m` 是**离路面**高度、`fov_deg` 是**水平**视场角，
    口径错一点比例尺就整体偏 10~40%。

  ## 与后端的分工（不重复造轮子）
  · 参数合理性判断**全部交给后端** `POST /api/scene/calibration-preview`
    （返回地平线行 horizon_y / 可解像素比例 solvable_ratio / 逐行 ppm /
     告警 warnings / 两点地面距离 pair_distances / 点误差 point_errors）。
  · 本组件**不自己重算几何**，只做交互与展示 —— 避免前后端两套公式漂移。

  ## 落盘字段（全部在 scene_annotation._ALLOWED_KEYS 白名单内）
  · traffic_light_roi  [[x1,y1,x2,y2], ...]  控制被拍方向的信号灯区域
  · stop_line_y        int                    停止线像素行
  · camera_height_m    离路面高度(米)
  · camera_pitch_deg   俯角，向下为负
  · fov_deg            水平视场角
  · camera_yaw_deg     偏航角
  · ground_points      [{u,v,x,y} × ≥4]      人工点选的已知地面坐标
  · frame_width / frame_height / speed_limit / road_direction
-->
<template>
  <el-dialog
    :model-value="modelValue"
    title="测速标定 + 信号灯 ROI"
    width="1280px"
    top="3vh"
    class="cal-dialog"
    :close-on-click-modal="false"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <!-- ★★2026-10-09 由 DSH 新增：**源不一致红警告 + 禁止保存**（设计单 §12.5 修法 2）
         为什么必须在面板内部再拦一道：这一面板的操作全部以"画面上看到的东西"为准，
         一旦画面对应的源与保存目标的源不是同一个，用户做的所有标定都是废的
         （实测就发生过：在旧 B 站视频的首帧上画 ROI，存到了那个旧视频里）。 -->
    <div v-if="!source" class="cal-alert bad">
      ⛔ <b>没有可标定的源</b>：后端当前没有正在运行的源，输入框也是空的。
      请先在顶栏填一个视频路径并点「开始」，或点「⟲ 同步运行源」。
    </div>
    <div v-else-if="mismatch" class="cal-alert bad">
      ⚠ <b>输入框的源与后端正在运行的源不一致</b><br />
      <span class="mono">本面板（画面与保存目标）用的是：{{ source }}</span><br />
      <span class="mono">输入框里写的是：{{ inputSource }}</span><br />
      为避免"在错的画面上标、存到错的视频"，<b>已禁止保存</b>。<br />
      请二选一：① 回顶栏点「⟲ 同步运行源」；② 点「开始」让后端切到输入框那个源，
      然后重开本面板（届时画面才是你要标的那一个）。
      <el-checkbox v-model="forceSave" size="small" style="margin-top:6px">
        我确认就是要给下面这个源做标定（它当前没在运行）：<span class="mono">{{ source }}</span>
      </el-checkbox>
    </div>
    <div v-else class="cal-alert ok">
      ● 标定目标 = 后端正在运行的源：<span class="mono">{{ source }}</span>
      <span class="muted">（保存后**无需重启检测**，后端按文件 mtime 热重载，下一帧即生效）</span>
    </div>

    <div class="cal-tip">
      ① 先点 <b>信号灯 ROI</b>，在画面上<b>拖出一个框</b>把"管你这个方向"的那盏灯圈住
      （画面里往往有好几盏灯，圈错等于按别人的灯判你闯红灯）；
      ② 再点 <b>停止线</b>，在停止线上点一下取该行 y；
      ③ 填相机参数或用 <b>地面标定点</b>；
      ④ 点 <b>校验参数</b> 看后端反馈。
    </div>

    <div class="cal-body">
      <!-- ================= 左：画布 ================= -->
      <div class="cal-left">
        <div class="cal-toolbar">
          <el-radio-group v-model="mode" size="small">
            <el-radio-button value="roi">信号灯 ROI（拖框）</el-radio-button>
            <el-radio-button value="stopline">停止线（点一下）</el-radio-button>
            <el-radio-button value="ground">地面标定点（点一下）</el-radio-button>
            <el-radio-button value="measure">量距离（点两下）</el-radio-button>
          </el-radio-group>
          <el-button size="small" :disabled="!pairs.length" @click="clearMeasure">清空量距</el-button>
        </div>

        <div class="cal-canvas" ref="wrap">
          <img :src="firstFrameUrl" class="cal-img" ref="imgEl"
               :style="{ cursor: mode === 'roi' ? 'crosshair' : 'crosshair' }"
               @mousedown="onDown" @mousemove="onMove" @mouseup="onUp"
               alt="标定画布" />
          <svg class="cal-svg" :viewBox="`0 0 ${fw} ${fh}`" preserveAspectRatio="none">
            <!-- 信号灯 ROI -->
            <rect v-for="(r, i) in rois" :key="'r' + i"
                  :x="r[0]" :y="r[1]" :width="r[2] - r[0]" :height="r[3] - r[1]"
                  class="g-roi" />
            <rect v-if="dragRect" :x="dragRect[0]" :y="dragRect[1]"
                  :width="dragRect[2] - dragRect[0]" :height="dragRect[3] - dragRect[1]"
                  class="g-roi g-roi--draw" />
            <!-- 停止线 -->
            <line v-if="stopLineY != null" :x1="0" :y1="stopLineY" :x2="fw" :y2="stopLineY"
                  class="g-stop" />
            <!-- 地面标定点（已填米制坐标的显示编号） -->
            <g v-for="(p, i) in groundPoints" :key="'g' + i">
              <circle :cx="p.u" :cy="p.v" r="8" class="g-gpt" />
              <text :x="p.u + 12" :y="p.v - 10" class="g-gpt-t">{{ i + 1 }}</text>
            </g>
            <!-- 量距 -->
            <line v-if="pairs.length" :x1="pairs[0][0]" :y1="pairs[0][1]"
                  :x2="pairs[0][2]" :y2="pairs[0][3]" class="g-measure" />
            <circle v-for="(p, i) in measurePts" :key="'m' + i" :cx="p[0]" :cy="p[1]"
                    r="7" class="g-mpt" />
          </svg>
        </div>
        <div class="cal-hint">
          画面 {{ fw }}×{{ fh }} · 模式：<b>{{ modeCn }}</b>
          <span v-if="mode === 'ground'">（每点一下加一个点，右侧填它对应的真实米制坐标）</span>
          <span v-if="lastPt" class="cal-last">
            最近落点 px(<b>{{ lastPt[0] }}</b>, <b>{{ lastPt[1] }}</b>)
            <template v-if="lastMode">{{ lastMode }}</template>
          </span>
        </div>
      </div>

      <!-- ================= 右：参数 ================= -->
      <div class="cal-right">
        <!-- 信号灯 ROI -->
        <div class="blk">
          <div class="blk-t">
            信号灯 ROI <span class="tag">{{ rois.length }}</span>
            <el-button size="small" text type="danger" :disabled="!rois.length"
                       @click="rois = []">全清</el-button>
          </div>
          <div v-if="!rois.length" class="warn-line">
            ⚠ 未标注：灯态会取"画面里任意一盏灯"，闯红灯判定不可信（实测每循环误报 5~7 次）
          </div>
          <div v-for="(r, i) in rois" :key="'rl' + i" class="li">
            <span class="mono">[{{ r.map(v => Math.round(v)).join(', ') }}]</span>
            <el-button size="small" text type="danger" @click="rois.splice(i, 1)">删</el-button>
          </div>
        </div>

        <!-- 停止线 -->
        <div class="blk">
          <div class="blk-t">停止线</div>
          <div class="row">
            <span class="lb">y 行</span>
            <el-input-number v-model="stopLineY" :min="0" :max="fh" :step="1" size="small"
                             controls-position="right" style="width:110px" />
            <el-button size="small" text :disabled="stopLineY == null"
                       @click="stopLineY = null">清除</el-button>
          </div>
          <div class="note">换视频必须重标（车辆 bbox 底边越过该行即视为越线）</div>
        </div>

        <!-- 相机参数 -->
        <div class="blk">
          <div class="blk-t">相机参数 <span class="hint">测速准确的前提</span></div>
          <div class="row">
            <span class="lb">离路面高度</span>
            <el-input-number v-model="cam.camera_height_m" :min="0.5" :max="80" :step="0.1"
                             size="small" controls-position="right" style="width:110px" />
            <span class="un">米</span>
          </div>
          <div class="row">
            <span class="lb">俯角</span>
            <el-input-number v-model="cam.camera_pitch_deg" :min="-89" :max="10" :step="0.1"
                             size="small" controls-position="right" style="width:110px" />
            <span class="un">度（向下为负）</span>
          </div>
          <div class="row">
            <span class="lb">水平视场角</span>
            <el-input-number v-model="cam.fov_deg" :min="5" :max="170" :step="0.1"
                             size="small" controls-position="right" style="width:110px" />
            <span class="un">度（不是对角！）</span>
          </div>
          <div class="row">
            <span class="lb">偏航角</span>
            <el-input-number v-model="cam.camera_yaw_deg" :min="-360" :max="360" :step="0.1"
                             size="small" controls-position="right" style="width:110px" />
            <span class="un">度（仅影响横向定位）</span>
          </div>
          <div class="note">
            高度填的是<b>离路面</b>高度（不是海拔）；视场角填<b>水平</b>值，
            监控相机手册常给对角值，直接填会让比例尺整体偏 10~20%。
          </div>
        </div>

        <!-- 地面标定点 -->
        <div class="blk">
          <div class="blk-t">
            地面标定点 <span class="tag">{{ groundPoints.length }}</span>
            <el-button size="small" text type="danger" :disabled="!groundPoints.length"
                       @click="groundPoints = []">全清</el-button>
          </div>
          <div class="note">
            不知道相机参数时可用：在画面上点 ≥4 个<b>已知实际坐标</b>的地面点
            （斑马线端点 / 车道线交点 / 井盖中心），再填它的米制 x,y。
            与相机参数同时给出会**自动交叉校核**。
          </div>
          <div v-for="(p, i) in groundPoints" :key="'gp' + i" class="gp-row">
            <span class="gp-idx">{{ i + 1 }}</span>
            <span class="mono">px({{ Math.round(p.u) }},{{ Math.round(p.v) }})</span>
            <el-input-number v-model="p.x" :step="0.1" size="small" placeholder="x 米"
                             controls-position="right" style="width:92px" />
            <el-input-number v-model="p.y" :step="0.1" size="small" placeholder="y 米"
                             controls-position="right" style="width:92px" />
            <span v-if="p.error_m != null" class="gp-err">误差 {{ p.error_m }} m</span>
            <el-button size="small" text type="danger" @click="groundPoints.splice(i, 1)">删</el-button>
          </div>
        </div>

        <!-- 校验结果 -->
        <div class="blk">
          <div class="blk-t">
            参数校验
            <el-button size="small" type="primary" plain :loading="busy" @click="runPreview">
              校验参数
            </el-button>
          </div>
          <div v-if="previewErr" class="err-line">{{ previewErr }}</div>
          <template v-if="pv">
            <div class="pv-grid">
              <div class="pv-k">标定来源</div>
              <div class="pv-v">
                <el-tag :type="pv.calibrated ? 'success' : 'warning'" size="small">
                  {{ methodCn(pv.method) }}
                </el-tag>
                <span class="mono">{{ pv.method }}</span>
              </div>
              <div class="pv-k">地平线行</div>
              <div class="pv-v">
                <b>{{ horizonText }}</b>
                <span class="note-inline">（画面高 {{ fh }}；俯角填错时这个数会跑到画面外）</span>
              </div>
              <div class="pv-k">可解像素比例</div>
              <div class="pv-v">
                <b :class="solvableClass">{{ pv.solvable_ratio }}</b>
                <span class="note-inline">（参数填反会明显下降，正常应接近 1）</span>
              </div>
            </div>
            <div v-if="pv.warnings && pv.warnings.length" class="warn-box">
              <div v-for="(w, i) in pv.warnings" :key="'w' + i">⚠ {{ w }}</div>
            </div>
            <div v-if="pv.rows" class="rows">
              <div class="rows-t">逐行 ppm（像素/米）与地面距离</div>
              <table class="rows-tb">
                <thead><tr><th>行 y</th><th>ppm</th><th>前向 m</th><th>横向 m</th><th>可解</th></tr></thead>
                <tbody>
                  <tr v-for="(v, k) in pv.rows" :key="k">
                    <td class="mono">{{ k }}</td>
                    <td class="mono">{{ v.ppm }}</td>
                    <td class="mono">{{ v.ground_m_forward ?? '—' }}</td>
                    <td class="mono">{{ v.ground_m_right ?? '—' }}</td>
                    <td>{{ v.ok ? '✓' : '✗' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-if="pv.pair_distances && pv.pair_distances.length" class="warn-box ok-box">
              <div v-for="(d, i) in pv.pair_distances" :key="'pd' + i">
                量距 {{ i + 1 }}：{{ d.ground_distance_m ?? '不可解' }} m
                <span v-if="d.ppm" class="note-inline">（{{ d.pixel_distance }}px → {{ d.ppm }} px/m；
                  若这是标准车道宽，应接近 3.75 m）</span>
              </div>
            </div>
            <div v-if="pv.info && pv.info.note" class="note">{{ pv.info.note }}</div>
          </template>
          <div v-else class="note">点「校验参数」后在这里看到后端反馈（地平线 / ppm / 告警）。</div>
        </div>

        <!-- 其它 -->
        <div class="blk">
          <div class="blk-t">其它</div>
          <div class="row">
            <span class="lb">限速</span>
            <el-input-number v-model="speedLimit" :min="5" :max="200" :step="5" size="small"
                             controls-position="right" style="width:110px" />
            <span class="un">km/h</span>
          </div>
          <div class="row">
            <span class="lb">行驶方向</span>
            <el-select v-model="roadDirection" size="small" clearable placeholder="不设置（推荐）"
                       style="width:170px">
              <el-option label="不设置（判不准就不判）" value="" />
              <el-option label="朝画面里（纵深机位）" value="up" />
              <el-option label="朝画面外（纵深机位）" value="down" />
              <el-option label="向左" value="left" />
              <el-option label="向右" value="right" />
            </el-select>
          </div>
          <div class="note">
            纵深机位（车朝画面里驶离）下"画面左右"推不出车道方向，
            逆行判定会误报 —— 所以建议留空，让系统"判不准就不判"。
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <span class="foot-note">{{ footNote }}</span>
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="saving" :disabled="blocked" @click="save">
        {{ blocked ? '先处理源不一致' : '保存标定' }}
      </el-button>    </template>
  </el-dialog>
</template>

<script setup>
/* eslint-disable no-unused-vars */
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  // ★2026-10-09 由 DSH 修正：`source` 的语义明确为**后端正在运行的源**
  //   （由 LiveMonitor 的 calSrc 传入：runningSource 优先，其次才是输入框）。
  //   面板的画面预览、读取配置、保存、参数校验**全部**用这一个值 —— 保证
  //   "看到的画面"与"存到哪里"永远一致（这正是上一轮 bug 的核心）。
  source: { type: String, default: '' },
  // 后端正在跑的源（可能为空 = 没在跑）+ 输入框里的源：仅用于**红警告与保存闸门**
  runningSource: { type: String, default: '' },
  inputSource: { type: String, default: '' },
  sourceMismatch: { type: Boolean, default: false },
  frameWidth: { type: Number, default: 1280 },
  frameHeight: { type: Number, default: 720 },
})
const emit = defineEmits(['update:modelValue', 'saved'])

/** 源不一致时必须显式确认才允许保存（默认禁止 —— 用户已定口径） */
const forceSave = ref(false)

/** 规范化比较：后端按原始字符串算 sha1，这里只判断"看起来是不是同一个源" */
function normSrc(s) {
  return String(s || '').trim().replace(/\\/g, '/').toLowerCase()
}
/** 真正的不一致 = 父组件判定"输入框 ≠ 正在运行的源"（sourceMismatch），
 *  且面板实际用的源确实不是输入框那个（= 后端在跑 A，用户输入框写 B）。
 *  判据数据全部来自后端 /status，不在前端重复推导。 */
const mismatch = computed(() => {
  if (!props.source) return false                  // 空源走另一条提示
  if (props.sourceMismatch) return true
  if (props.runningSource && normSrc(props.source) !== normSrc(props.runningSource)) return true
  return false
})
const blocked = computed(() => (!props.source || mismatch.value) && !forceSave.value)

/** 面板实际使用的源（永远是 props.source；保留这个计算属性是为了让
 *  "不允许多来源"这件事在代码里显式可见，而不是散落在各处用错变量） */
const effectiveSource = computed(() => props.source)

const API_BASE = import.meta.env.VITE_API_BASE || ''
const imgEl = ref(null)
const wrap = ref(null)

const fw = ref(props.frameWidth || 1280)
const fh = ref(props.frameHeight || 720)

const mode = ref('roi')
const modeCn = computed(() => ({
  roi: '信号灯 ROI（拖框）',
  stopline: '停止线（点一下）',
  ground: '地面标定点（点一下）',
  measure: '量距离（点两下）',
}[mode.value] || mode.value))

const rois = ref([])                 // [[x1,y1,x2,y2], ...]
const stopLineY = ref(null)
const groundPoints = ref([])         // [{u,v,x,y,error_m}]
const measurePts = ref([])           // [[u,v], ...]
const pairs = ref([])                // [[u1,v1,u2,v2]]
const lastPt = ref(null)             // 最近一次落点（像素），供当场核对换算
const lastMode = ref('')

const cam = reactive({
  camera_height_m: null, camera_pitch_deg: null,
  fov_deg: null, camera_yaw_deg: null,
})
const speedLimit = ref(60)
const roadDirection = ref('')

const busy = ref(false)
const saving = ref(false)
const pv = ref(null)
const previewErr = ref('')

const firstFrameUrl = computed(() =>
  `${API_BASE}/api/scene/first-frame?source=${encodeURIComponent(effectiveSource.value)}&_=${Date.now()}`)

const solvableClass = computed(() => {
  const r = Number(pv.value?.solvable_ratio ?? 0)
  if (r >= 0.95) return 'ok'
  if (r >= 0.7) return 'warn'
  return 'bad'
})

/** 地平线的**可读**表达（2026-10-06 由 DSH 新增）
 *
 * 几何事实：horizon_y = H/2 + f·tan(pitch)。俯角较大时 tan 为负，
 * 结果会是**负数** —— 那不是错误，而是"地平线在画面上方之外"。
 * 演示机位实测：H=576、fov=90、pitch=-23.445 -> 288 - 231 = -10.5。
 * 直接显示 -10.5 会让人以为参数填错了，所以翻译成人话。
 */
const horizonText = computed(() => {
  const v = pv.value?.horizon_y
  if (v === null || v === undefined) return '—'
  const n = Number(v)
  if (n < 0) return `画面外上方 ${Math.abs(n)}px`
  if (n > fh.value) return `画面外下方 ${(n - fh.value).toFixed(0)}px`
  return `${n}px`
})

const footNote = computed(() => {  const n = []
  if (rois.value.length) n.push(`ROI ${rois.value.length} 个`)
  if (stopLineY.value != null) n.push(`停止线 y=${stopLineY.value}`)
  if (cam.camera_height_m != null) n.push('相机参数')
  if (groundPoints.value.length >= 4) n.push(`地面点 ${groundPoints.value.length}`)
  return n.length ? `将保存：${n.join(' / ')}` : '⚠ 尚未标注任何内容，保存后不会改变闯红灯判据'
})

/* ---------------- 画布坐标换算 ---------------- */
function toImg(ev) {
  // 加固：点击可能落在图片的子节点/紧邻元素上，统一向上找 .cal-img，
  // 避免"差几像素就点空"（实测踩过：点到了图片下方那一行提示文字）
  let img = ev.currentTarget || imgEl.value
  if (img && img.classList && !img.classList.contains('cal-img')) {
    img = img.querySelector?.('.cal-img') || img.closest?.('.cal-canvas')?.querySelector('.cal-img') || imgEl.value
  }
  if (!img) return null
  const r = img.getBoundingClientRect()
  const nw = img.naturalWidth || fw.value
  const nh = img.naturalHeight || fh.value
  if (nw !== fw.value || nh !== fh.value) { fw.value = nw; fh.value = nh }
  const x = (ev.clientX - r.left) / r.width * nw
  const y = (ev.clientY - r.top) / r.height * nh
  return [Math.round(x), Math.round(y)]
}

/* ---------------- 交互 ---------------- */
let dragging = false
let dragStart = null
const dragRect = ref(null)

function onDown(ev) {
  const p = toImg(ev)
  if (!p) return
  // 先清后设：保证 .cal-last 每次都重新渲染（只赋新数组时，
  // 若上一帧 DOM 已复用，读数会显得"停在第一次"）
  lastPt.value = null
  lastPt.value = p
  lastMode.value = modeCn.value
  if (mode.value === 'roi') {
    dragging = true
    dragStart = p
    dragRect.value = [p[0], p[1], p[0], p[1]]
    ev.preventDefault()
  } else if (mode.value === 'stopline') {
    stopLineY.value = p[1]
    ElMessage.success(`停止线已设为 y=${p[1]}`)
  } else if (mode.value === 'ground') {
    groundPoints.value.push({ u: p[0], v: p[1], x: null, y: null, error_m: null })
  } else if (mode.value === 'measure') {
    measurePts.value.push(p)
    if (measurePts.value.length >= 2) {
      const [a, b] = measurePts.value.slice(-2)
      pairs.value.push([a[0], a[1], b[0], b[1]])
      measurePts.value = []
      ElMessage.info('已添加一段量距，点「校验参数」看实际米数')
    }
  }
}

function onMove(ev) {
  if (!dragging || !dragStart) return
  const p = toImg(ev)
  if (!p) return
  dragRect.value = [
    Math.min(dragStart[0], p[0]), Math.min(dragStart[1], p[1]),
    Math.max(dragStart[0], p[0]), Math.max(dragStart[1], p[1]),
  ]
}

function onUp() {
  if (!dragging) return
  dragging = false
  const r = dragRect.value
  dragRect.value = null
  dragStart = null
  if (!r) return
  if (r[2] - r[0] < 4 || r[3] - r[1] < 4) return   // 误点，忽略
  rois.value.push(r)
  ElMessage.success(`已添加信号灯 ROI [${r.map(v => Math.round(v)).join(', ')}]`)
}

function clearMeasure() { pairs.value = []; measurePts.value = [] }

/* ---------------- 载入 / 保存 ---------------- */
function applyConfig(cfg) {
  const c = cfg || {}
  rois.value = Array.isArray(c.traffic_light_roi)
    ? c.traffic_light_roi.filter(r => Array.isArray(r) && r.length >= 4)
        .map(r => [Number(r[0]), Number(r[1]), Number(r[2]), Number(r[3])])
    : []
  stopLineY.value = (c.stop_line_y === undefined || c.stop_line_y === null)
    ? null : Number(c.stop_line_y)
  groundPoints.value = Array.isArray(c.ground_points)
    ? c.ground_points.map(p => ({
        u: Number(p.u), v: Number(p.v),
        x: p.x === undefined || p.x === null ? null : Number(p.x),
        y: p.y === undefined || p.y === null ? null : Number(p.y),
        error_m: null,
      }))
    : []
  cam.camera_height_m = numOrNull(c.camera_height_m)
  cam.camera_pitch_deg = numOrNull(c.camera_pitch_deg)
  cam.fov_deg = numOrNull(c.fov_deg)
  cam.camera_yaw_deg = numOrNull(c.camera_yaw_deg)
  speedLimit.value = numOrNull(c.speed_limit) ?? 60
  roadDirection.value = c.road_direction || ''
  if (c.frame_width) fw.value = Number(c.frame_width)
  if (c.frame_height) fh.value = Number(c.frame_height)
}
function numOrNull(v) {
  return (v === undefined || v === null || v === '') ? null : Number(v)
}

async function load() {
  if (!props.source) return
  try {
    const r = await api.get('/scene/config', { params: { source: effectiveSource.value } })
    const d = r?.data?.data || r?.data || {}
    applyConfig(d)                     // GET /scene/config 的 data 就是配置对象（扁平）
  } catch (e) { /* 首次使用没有配置 */ }
}

function buildConfig() {
  const cfg = {
    traffic_light_roi: rois.value.length
      ? rois.value.map(r => r.map(v => Math.round(v))) : null,
    stop_line_y: stopLineY.value == null ? null : Math.round(stopLineY.value),
    frame_width: Math.round(fw.value),
    frame_height: Math.round(fh.value),
    speed_limit: speedLimit.value,
    road_direction: roadDirection.value || null,
  }
  // 相机参数：只有真的填了才写，避免把"null"写进白名单字段
  for (const k of ['camera_height_m', 'camera_pitch_deg', 'fov_deg', 'camera_yaw_deg']) {
    cfg[k] = cam[k] === null ? null : Number(cam[k])
  }
  // 地面点：必须 x/y 都填了才有意义
  const gp = groundPoints.value.filter(p => p.x !== null && p.y !== null)
  cfg.ground_points = gp.length ? gp.map(p => ({
    u: Math.round(p.u), v: Math.round(p.v), x: Number(p.x), y: Number(p.y),
  })) : null
  return cfg
}

async function save() {
  // ★2026-10-09 由 DSH 新增：**保存闸门**（设计单 §12.5 修法 2）。
  // 用户已定口径：不一致时红警告 + 禁止保存，另有"我确认要标这个源"的显式勾选可越过。
  // 这里做二次拦截（按钮已 disabled，但回车/程序化触发也要挡住）—— 本项目教训：
  // 只在 UI 层拦一道，换个入口就绕过去了。
  if (blocked.value) {
    ElMessage.error(props.source
      ? '源不一致：请回顶栏点「⟲ 同步运行源」，或勾选"我确认要标这个源"'
      : '没有可标定的源：请先在顶栏启动一个视频/流')
    return
  }
  saving.value = true
  try {
    const r = await api.post('/scene/config', {
      source: effectiveSource.value, config: buildConfig(), annotated_by: 'manual',
    })
    const d = r?.data?.data || r?.data
    ElMessage.success('标定已保存' + (d?.traffic_light_roi?.length
      ? `（信号灯 ROI ${d.traffic_light_roi.length} 个）` : '（未含信号灯 ROI）'))
    emit('saved', d)
    emit('update:modelValue', false)
  } catch (e) {
    ElMessage.error('保存失败：' + (e?.response?.data?.detail || e.message))
  } finally { saving.value = false }
}

/* ---------------- 调后端校验（几何全部交给后端） ---------------- */
async function runPreview() {
  busy.value = true
  previewErr.value = ''
  try {
    const cfg = buildConfig()
    // 不含相机参数时后端会退回 assumed_lanes —— 如实展示，不假装已标定
    const body = {
      source: effectiveSource.value,
      frame_width: cfg.frame_width,
      frame_height: cfg.frame_height,
      config: cfg,
      pairs: pairs.value.length ? pairs.value : null,
      points: groundPoints.value.map(p => ({ u: Math.round(p.u), v: Math.round(p.v), x: p.x, y: p.y })),
    }
    const r = await api.post('/scene/calibration-preview', body)
    const d = r?.data?.data || r?.data
    pv.value = d || null
    // 把点误差写回列表，方便逐个核对
    const errs = d?.point_errors || []
    errs.forEach((it, i) => {
      if (groundPoints.value[i]) groundPoints.value[i].error_m = it.error_m ?? null
    })
  } catch (e) {
    pv.value = null
    previewErr.value = '校验失败：' + (e?.response?.data?.detail || e.message)
  } finally { busy.value = false }
}

function methodCn(m) {
  const s = String(m || '')
  if (s.startsWith('camera_geometry')) return '已标定（相机几何）'
  if (s.startsWith('ground_homography')) return '已标定（地面单应）'
  if (s.startsWith('explicit_ppm')) return '已标定（手工 ppm）'
  if (s === 'assumed_lanes') return '未标定（按车道数粗估）'
  if (s === 'unavailable') return '不可用'
  return s || '未知'
}

watch(() => props.modelValue, (v) => {
  if (v) {
    pv.value = null; previewErr.value = ''; forceSave.value = false; load()
  }
})
// ★2026-10-09 由 DSH 新增：**源在打开期间变了就重新载入**。
// 场景：用户开着面板，同时在顶栏点了「开始」切换到另一个视频 ——
// 此时面板画面/参数必须跟着换，否则又变成"看着 A、标着 B"。
watch(() => props.source, (v, ov) => {
  if (props.modelValue && v && v !== ov) {
    pv.value = null; previewErr.value = ''; forceSave.value = false; load()
  }
})
onMounted(() => { if (props.modelValue) load() })

defineExpose({ applyConfig, buildConfig })
</script>

<style scoped>
/* ★2026-10-09 由 DSH 新增：源状态提示条（不一致时必须一眼看到，默认禁止保存） */
.cal-alert {
  font-size: 12px; line-height: 1.75; border-radius: 6px;
  padding: 7px 10px; margin-bottom: 8px; border: 1px solid transparent;
}
.cal-alert.bad { color: #b91c1c; background: rgba(239, 68, 68, .10);
  border-color: rgba(239, 68, 68, .45); }
.cal-alert.ok { color: #15803d; background: rgba(22, 163, 74, .08);
  border-color: rgba(22, 163, 74, .35); }
.cal-alert .mono { font-family: Consolas, Menlo, monospace; font-size: 11px; }
.cal-alert .muted { color: #909399; }
.cal-tip {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
  line-height: 1.7;
}
.cal-body { display: grid; grid-template-columns: 1fr 400px; gap: 14px; }
.cal-left { min-width: 0; }
.cal-toolbar { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
.cal-canvas {
  position: relative; line-height: 0;
  border: 1px solid #dcdfe6; background: #000;
  user-select: none;
}
.cal-img { width: 100%; display: block; }
.cal-svg { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }
.g-roi { fill: rgba(250, 204, 21, .16); stroke: #facc15; stroke-width: 2; }
.g-roi--draw { fill: rgba(250, 204, 21, .3); stroke-dasharray: 6 4; }
.g-stop { stroke: #22d3ee; stroke-width: 2.5; stroke-dasharray: 10 5; }
.g-gpt { fill: rgba(244, 114, 182, .35); stroke: #f472b6; stroke-width: 2.5; }
.g-gpt-t { fill: #f472b6; font-size: 20px; font-weight: 700; }
.g-measure { stroke: #34d399; stroke-width: 2.5; }
.g-mpt { fill: rgba(52, 211, 153, .4); stroke: #34d399; stroke-width: 2.5; }
.cal-hint { font-size: 12px; color: #909399; margin-top: 6px; }
.cal-last { margin-left: 10px; color: #409eff; }
.cal-last b { font-family: Consolas, Monaco, monospace; }

.cal-right { display: flex; flex-direction: column; gap: 10px; max-height: 70vh; overflow-y: auto; }
.blk { border: 1px solid #ebeef5; border-radius: 6px; padding: 10px; }
.blk-t {
  font-size: 13px; font-weight: 600; margin-bottom: 8px;
  display: flex; align-items: center; gap: 8px;
}
.tag {
  background: #f0f2f5; border-radius: 9px; padding: 0 7px;
  font-size: 11px; font-weight: 400; color: #606266;
}
.hint { font-size: 11px; color: #e6a23c; font-weight: 400; }
.row { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.lb { width: 88px; font-size: 12px; color: #606266; flex: none; }
.un { font-size: 11px; color: #909399; }
.note { font-size: 11px; color: #909399; line-height: 1.6; margin-top: 4px; }
.note-inline { font-size: 11px; color: #a8abb2; }
.li { display: flex; align-items: center; justify-content: space-between; font-size: 12px; }
.mono { font-family: Consolas, Monaco, monospace; font-size: 12px; }
.warn-line { font-size: 12px; color: #e6a23c; line-height: 1.6; }
.err-line { font-size: 12px; color: #f56c6c; }
.warn-box {
  margin-top: 8px; padding: 7px 9px; border-radius: 5px;
  background: #fdf6ec; border: 1px solid #f5dab1;
  font-size: 12px; color: #b88230; line-height: 1.7;
}
.ok-box { background: #f0f9eb; border-color: #c2e7b0; color: #529b2e; }
.pv-grid { display: grid; grid-template-columns: 92px 1fr; gap: 5px 8px; font-size: 12px; }
.pv-k { color: #909399; }
.pv-v { display: flex; align-items: center; gap: 6px; }
.pv-v .ok { color: #529b2e; }
.pv-v .warn { color: #e6a23c; }
.pv-v .bad { color: #f56c6c; }
.rows { margin-top: 8px; }
.rows-t { font-size: 12px; color: #606266; margin-bottom: 4px; }
.rows-tb { width: 100%; border-collapse: collapse; font-size: 11px; }
.rows-tb th, .rows-tb td {
  border: 1px solid #ebeef5; padding: 2px 5px; text-align: right;
}
.rows-tb th { background: #fafafa; color: #909399; font-weight: 500; }
.gp-row { display: flex; align-items: center; gap: 6px; margin-bottom: 5px; }
.gp-idx {
  width: 18px; height: 18px; border-radius: 50%; background: #f472b6; color: #fff;
  font-size: 11px; display: flex; align-items: center; justify-content: center; flex: none;
}
.gp-err { font-size: 11px; color: #e6a23c; }
.foot-note { float: left; font-size: 12px; color: #909399; }
</style>
