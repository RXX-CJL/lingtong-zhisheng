<template>
  <div class="live-page">
    <!-- ===== 顶部：状态条 ===== -->
    <div class="live-bar">
      <div class="bar-left">
        <span class="dot" :class="status.running ? 'on' : 'off'"></span>
        <span class="bar-title">实时监测</span>
        <span class="bar-meta">{{ status.running ? '检测中' : '未启动' }}</span>
        <span class="bar-meta">已处理 {{ status.processed_frames || 0 }} 帧</span>
        <span class="bar-meta">位姿 {{ status.current_fps || 0 }} fps</span>
        <span class="bar-meta" v-if="tlStats.total">
          红绿灯 检出{{ tlStats.total }} / 判色{{ tlStats.cnn + tlStats.hsv }}
          <b v-if="tlStats.none_dropped">· 拒识{{ tlStats.none_dropped }}</b>
        </span>
        <!-- ★灯态作用域（2026-10-06 由 DSH 新增）：后端 /status 一直在返回
             traffic_light_scope，但前端此前一个字都没用。scope=frame 意味着
             灯态取的是"画面里任意一盏灯" —— 那正是 O19 每循环误报 5~7 次的根因；
             用户不标 ROI 就永远看不见这件事，所以这里做成一眼可辨的警告。 -->
        <span v-if="lightScope" class="bar-meta scope"
              :class="'scope--' + lightScope"
              :title="scopeTip">
          灯态：{{ scopeCn }}
          <template v-if="status.traffic_light_matched != null">
            ·ROI内 {{ status.traffic_light_matched }} 盏
          </template>
        </span>
      </div>
      <div class="bar-right">
        <el-select v-model="sourceKind" size="small" style="width:120px" @change="onSourceKindChange">
          <el-option label="视频文件" value="file" />
          <el-option label="摄像头/流" value="stream" />
          <el-option label="本机摄像头" value="camera" />
        </el-select>
        <!-- ★2026-10-06 由 DSH 新增提示：用户反馈"管理端没有给我用来测试视频的入口"，
             其实入口就是这里 —— 但只写"绝对路径"太隐晦。现在明确告知：
             **按路径直接读原文件，不限大小、不复制**（演示视频 1.1 GB 就是这么跑的）。 -->
        <!-- ⚠ 注意：v-if/v-else 必须成对写在**同一层**。
             第一版把 v-if 写在 tooltip 内部的 el-input 上、v-else 留在外面，
             Vue 编译器直接报 Invalid end tag（跨组件边界的条件链不合法）。 -->
        <el-tooltip v-if="sourceKind !== 'camera'" placement="bottom" effect="dark" :show-after="200">
          <template #content>
            <div style="max-width:340px;line-height:1.75">
              <b>测试视频就填这里</b>：后端按<b>绝对路径</b>直接读原文件<br />
              · 不限大小（1156 MB 的演示视频就是这么跑的）<br />
              · 不复制文件、不占额外磁盘<br />
              · 也可以填 http:// 或 rtsp:// 流地址
            </div>
          </template>
          <el-input v-model="sourceValue" size="small"
                    style="width:320px" :placeholder="sourceKind === 'stream' ? 'http://192.168.1.5:8080/video' : '视频绝对路径（不限大小，悬停看说明）'" />
        </el-tooltip>
        <el-input v-else v-model.number="cameraIndex" size="small" style="width:80px" placeholder="索引" />
        <el-button size="small" type="primary" :loading="busy" @click="startDetection">开始</el-button>
        <el-button size="small" :disabled="!status.running" @click="stopDetection">停止</el-button>
        <!-- ★2026-10-09 由 DSH 新增：「同步为正在运行的源」。
             存在的意义：输入框与"正在跑的源"谁说了算曾经是混乱的 ——
             标定面板跟着输入框走，于是"在错画面上标、存到错的视频"。
             现在面板只认"正在跑的源"，这个按钮用来把输入框也对齐过去。 -->
        <el-button size="small" :disabled="!runningSource" @click="syncSourceToRunning"
                   title="把输入框改成后端当前正在运行的数据源">⟲ 同步运行源</el-button>
        <el-button size="small" @click="openSceneDialog">场景标注</el-button>
        <!-- ★标定面板入口（2026-10-06 由 DSH 新增）—— 信号灯 ROI 是闯红灯判定的前提 -->
        <el-button size="small" :type="roiMissing ? 'warning' : 'default'"
                   @click="calDlg = true">
          {{ roiMissing ? '⚠ 测速标定/信号灯ROI（未标）' : '测速标定/信号灯ROI' }}
        </el-button>
      </div>
      <!-- ★2026-10-09 由 DSH 新增：**"当前生效源"一眼可见 + 不一致时红警告**。
           用户此前的困境："输入框总是自己跳变成这个 B 站录制的视频，导致我根本
           没法自己校验" —— 根因是界面上**没有任何地方**告诉他后端到底在跑哪个源。
           现在顶栏第二行直接写出来；两者不一致就整条变红并给出同步按钮。 -->
      <div class="src-bar" :class="{ bad: sourceMismatch }">
        <template v-if="sourceMismatch">
          ⚠ <b>输入框的源 ≠ 后端正在运行的源</b> —— 检测跑的仍是下面这个，
          点「开始」才会换源；标定面板已按"正在运行的源"工作（避免在错画面上标）。
        </template>
        <template v-else-if="!runningSource">
          ○ 后端当前<b>没有正在运行的源</b>（点「开始」后这里会显示实际生效的源）
        </template>
        <template v-else>
          ● 当前生效源
        </template>
        <code v-if="runningSource" class="src-path" :title="runningSource">{{ runningSource }}</code>
        <el-button v-if="sourceMismatch" size="small" text type="danger"
                   @click="syncSourceToRunning">把输入框同步为它</el-button>
      </div>
    </div>

    <!-- ===== 主体：三栏裸眼 3D ===== -->
    <div class="stage">
      <!-- 左栏：未违规车辆（向中央倾斜） -->
      <section class="panel panel--left">
        <header class="panel-head">
          <span class="ph-title">正常通行</span>
          <span class="ph-count">{{ vehicles.clean.length }}</span>
        </header>
        <div class="panel-body">
          <div v-if="!vehicles.clean.length" class="empty">暂无目标</div>
          <transition-group name="slide-left" tag="div">
            <div v-for="v in vehicles.clean" :key="v.track_id" class="vcard vcard--ok">
              <div class="vc-top">
                <span class="vc-id">ID{{ v.track_id }}</span>
                <span class="vc-type">{{ v.class_name_cn || v.class_name }}</span>
              </div>
              <div class="vc-metrics">
                <span class="vc-speed" v-if="v.speed_px != null">{{ v.speed_px.toFixed(1) }}<i>px/s</i></span>
                <span class="vc-speed muted" v-else>—</span>
                <span class="vc-dir">{{ dirCn(v.direction) }}</span>
              </div>
              <!-- 真实车速 + 可信度（2026-10-03 由 DSH 新增；数据来自后端 speed_calibration） -->
              <div class="vc-speedkm" v-if="v.speed_kmh != null">
                <span class="vc-kmh">{{ v.speed_kmh }}<i>km/h</i></span>
                <span class="vc-badge" :class="speedBadgeClass(v.speed_confidence)">
                  {{ speedConfCn(v.speed_confidence) }}
                </span>
                <span class="vc-badge warn" v-if="v.speed_quality && v.speed_quality !== 'ok'">
                  {{ v.speed_quality === 'sparse' ? '采样稀疏' : '轨迹断裂' }}
                </span>
              </div>
              <div class="vc-plate" v-if="v.plate">{{ v.plate }}</div>
            </div>
          </transition-group>
        </div>
      </section>

      <!-- 中栏：视频处理效果 -->
      <section class="panel panel--center">
        <div class="video-wrap" ref="videoWrap">
          <img :src="streamUrl" class="video-img" ref="videoImg" alt="实时检测画面"
               @error="onStreamError" @load="onStreamLoad" />
          <div v-if="!streamOk" class="video-mask">
            <p>视频流未就绪</p>
            <p class="hint">请先选择数据源并点击「开始」</p>
          </div>
          <!-- 聚焦小窗（2026-10-04 由 DSH 二次改造，用户要求）：
               用户原话："聚焦小窗口的显示内容直接引用检测框里的内容的就行了"
               -> 不再请求独立的 /zoom-frame 接口，而是**直接裁切实时流里该车辆的
                  检测框区域**，保证"小窗内容 == 画面上框住的那辆车"。
               实现：违规发生时把已绘制的一帧画到 canvas，再按 bbox 裁切并放大，
                  作为静态快照展示（避免 MJPEG 的 <img> 尝试二次解码导致闪烁）。
               位置：右下角画中画，占主画面约 15%，不遮挡监控。 -->
          <transition name="zoom">
            <div v-if="zoomSnap && focusPip" class="zoom-pip">
              <img :src="zoomSnap" class="zoom-pip-img" alt="聚焦目标" />
              <span class="zoom-pip-cap">
                <b>ID{{ zoomInfo.id }}</b>
                <template v-if="zoomInfo.type"> · {{ zoomInfo.type }}</template>
                <template v-if="zoomInfo.violation"> · {{ zoomInfo.violation }}</template>
              </span>
            </div>
          </transition>
          <!-- 全屏按钮（2026-10-04 由 DSH 新增，用户要求"视频右下角设置一个全屏"）-->
          <button class="fs-btn" :title="isFs ? '退出全屏 (Esc)' : '全屏查看细节'"
                  @click="toggleFullscreen">
            <span v-if="!isFs">⛶</span><span v-else>✕</span>
          </button>
          <div class="video-badge" v-if="status.running">
            <span class="rec-dot"></span> LIVE
          </div>
        </div>
      </section>

      <!-- 右栏：违规车辆（向中央倾斜） -->
      <section class="panel panel--right">
        <header class="panel-head">
          <span class="ph-title">违规告警</span>
          <span class="ph-count danger">{{ vehicles.violators.length }}</span>
        </header>
        <div class="panel-body">
          <div v-if="!vehicles.violators.length" class="empty">暂无违规</div>
          <transition-group name="slide-right" tag="div">
            <div v-for="v in vehicles.violators" :key="v.track_id" class="vcard vcard--bad">
              <div class="vc-top">
                <span class="vc-id">ID{{ v.track_id }}</span>
                <span class="vc-type">{{ v.class_name_cn || v.class_name || '—' }}</span>
                <!-- ★2026-10-10 由 DSH 新增：车辆已驶出画面、但违规仍在有效期内。
                     背景（用户反馈"告警栏很慢、来不及反应"）：违规车闯过停止线后很快
                     驶出画面，原实现会让这条告警**立刻消失**（实测右栏只存在 2.9 秒，
                     而前端 1.5 秒才轮询一次 -> 稍不走运就整段错过）。
                     现在后端保留到 TTL 结束并标 stale=True，这里如实标注，
                     避免用户以为"画面里正在违规的就是它"。 -->
                <span v-if="v.stale" class="vc-stale" title="该车已驶出画面；这条告警在有效期内仍保留">已离开画面</span>
                <!-- ★2026-10-10 由 DSH 新增：这条是"重复出现"（跨圈抑制命中）。
                     背景：`loop_dedup_sec` 为了不重复存证据，会把同一车同一位置的违规
                     在窗口内压掉；但**告警栏不该因此长时间空着**（用户实测右栏空 129 秒，
                     而画面里车在闯红灯）。现在抑制只作用于"存证据/计费"，展示照常刷新，
                     并如实标注为重复，避免与"新违规"混淆。 -->
                <span v-else-if="v.repeat" class="vc-stale vc-repeat" title="同一辆车在同一位置再次违规；为不重复存证/计费，本次只提示不重新取证">重复出现</span>
              </div>
              <div class="vc-violation">{{ v.primary_violation }}</div>
              <div class="vc-metrics">
                <span class="vc-speed" v-if="v.speed_px != null">{{ v.speed_px.toFixed(1) }}<i>px/s</i></span>
                <span class="vc-dir">{{ dirCn(v.direction) }}</span>
                <span class="vc-conf">{{ ((v.confidence || 0) * 100).toFixed(0) }}%</span>
              </div>
              <div class="vc-plate" v-if="v.plate">{{ v.plate }}</div>
            </div>
          </transition-group>
        </div>
      </section>
    </div>

    <!-- ===== 控制台 ===== -->
    <div class="console">
      <div class="con-row">
        <span class="con-label">检测项</span>
        <el-checkbox v-for="t in typeList" :key="t.key" v-model="settings.enabled_types[t.key]"
                     :label="t.cn" size="small" @change="pushSettings" />
      </div>
      <div class="con-row">
        <span class="con-label">置信度门槛</span>
        <el-slider v-model="confDefault" :min="0.3" :max="0.95" :step="0.05"
                   style="width:260px" @change="pushSettings" show-input size="small" />
        <span class="con-tip">数值越高越保守，误报越少</span>
      </div>
      <div class="con-row">
        <span class="con-label">确认时长</span>
        <el-slider v-model="holdSec" :min="0" :max="5" :step="0.5" style="width:180px"
                   @change="pushSettings" show-input size="small" />
        <span class="con-label">冷却期</span>
        <el-slider v-model="cooldownSec" :min="0" :max="60" :step="1" style="width:180px"
                   @change="pushSettings" show-input size="small" />
        <!-- ★云端 AI 复核总开关（2026-10-06 由 DSH 新增）
             用户原话："管理端的云端 ai 复核功能需要添加一个开关，不然现在会一直花没必要的钱。"
             与左边那个「云端复核」**不是一回事**：
               左边 cloud_consult = 逐帧咨询（process_frame 里的 consult_cloud_dual）
               这个 cloud_review  = 事件级复核（每条违规事件打豆包+Claude+DeepSeek）
             关掉后事件转「待人工复核」，不产生任何云调用。 -->
        <el-tooltip placement="top" effect="dark">
          <template #content>
            <div style="max-width:320px;line-height:1.7">
              <b>事件级云端 AI 复核</b><br />
              开：每条违规事件调用豆包视觉（3~5 关键帧）+ DeepSeek 二级验证
              （配了 Claude key 还会多一次）<br />
              关：不调用任何云 API，事件转「待人工复核」，<br />
              在事件中心点一下即可确认/排除
            </div>
          </template>
          <el-checkbox v-model="settings.cloud_review" size="small"
                       :disabled="!cloudSynced"
                       @change="pushCloudReview"
                       :class="{ 'ck-warn': !settings.cloud_review }">
            云端AI复核{{ settings.cloud_review ? '（计费）' : '（已关·转人工）' }}
          </el-checkbox>
        </el-tooltip>
        <!-- ★2026-10-09：逐帧咨询改为**单独推送**（原来 @change="pushSettings" 走连带推送，
             一旦内存值与后端不一致就会把它静默改掉）；同步失败时置灰。 -->
        <el-checkbox v-model="settings.cloud_consult" size="small"
                     :disabled="!cloudSynced"
                     @change="pushCloudConsult">逐帧咨询</el-checkbox>
        <span v-if="!cloudSynced" class="bar-meta ck-warn" style="font-size:12px"
              title="后端未返回云端开关的真实值（读取失败或字段缺失）——为避免误改，已置灰；可点上方「刷新」或重开本页">云端开关未同步·已置灰</span>
        <!-- 聚焦小窗开关（2026-10-04 由 DSH 新增）：觉得碍眼可一键关闭 -->
        <el-checkbox v-model="focusPip" size="small">聚焦小窗</el-checkbox>
        <!-- 标注分级显示（2026-10-04 由 DSH 新增）：车辆多时可降到极简档避免遮挡 -->
        <span class="con-label">标注</span>
        <el-select v-model="displayMode" size="small" style="width:104px" @change="pushDisplayMode">
          <el-option label="极简(仅ID)" value="minimal" />
          <el-option label="标准(+速度)" value="standard" />
          <el-option label="详细(全部)" value="full" />
          <el-option label="仅框线" value="off" />
        </el-select>
      </div>
    </div>

    <!-- ===== 证据抓拍墙 ===== -->
    <div class="wall">
      <header class="wall-head">
        <span class="wall-title">违规抓拍证据</span>
        <span class="wall-sub">原始整帧 · 未裁剪放大（保证证据链完整）</span>
        <span class="wall-count" v-if="evidenceTotal">共 {{ evidenceTotal }} 张</span>
        <el-button size="small" text @click="loadEvidence">刷新</el-button>
      </header>
      <div class="wall-grid">
        <div v-if="!evidence.length" class="empty">暂无抓拍</div>
        <!-- ★2026-10-10 由 DSH 扩展：抓拍证据补上**关键信息**
             （用户要求"最好要有违法时间等关键信息"）。
             原先只有 类型 + 紧凑时间戳（20261010 221353），看不出"什么时候违的、哪辆车"。
             现在每张卡片显示：违法类型 / **违法时间(YYYY-MM-DD HH:MM:SS)** / 车辆ID / 置信度。
             `violation_at` 来自数据库（精确落库时间），拿不到时退回文件名的抓拍时间。 -->
        <a v-for="e in evidence" :key="e.name" class="shot" :href="e.url" target="_blank" rel="noopener">
          <img :src="e.url" loading="lazy" alt="证据" />
          <span class="shot-cap">{{ e.label }}</span>
          <span class="shot-time">{{ e.violation_at || e.captured_at_disp || e.time }}</span>
          <span class="shot-meta">
            <template v-if="e.track_id != null">ID{{ e.track_id }}</template>
            <template v-if="e.confidence != null"> · {{ (e.confidence * 100).toFixed(0) }}%</template>
            <template v-if="e.plate_number"> · {{ e.plate_number }}</template>
          </span>
        </a>
      </div>
    </div>

    <!-- ===== 场景标注对话框（2026-10-04 由 DSH 重构，支持多类型区域 + 相机参数）===== -->
    <el-dialog v-model="sceneDlg" title="场景标注（区域手绘 + 相机参数）"
               width="1180px" :close-on-click-modal="false" top="4vh">
      <div class="scene-tip">
        选择<b>区域类型</b> → 在画面上<b>依次点击多边形的各个角点</b>（≥3 个）→ 点「添加到列表」。
        可连续标注多个区域。<b>禁停区</b>与<b>相机参数</b>是违停判定与测速准确的前提。
      </div>

      <div class="scene-body">
        <!-- 左侧：画布 -->
        <div class="scene-left">
          <div class="scene-toolbar">
            <span class="st-label">区域类型</span>
            <el-select v-model="zoneType" size="small" style="width:132px">
              <el-option v-for="z in ZONE_TYPES" :key="z.key"
                         :label="z.label" :value="z.key" />
            </el-select>
            <el-button size="small" @click="aiDetect" :loading="aiBusy">AI 检测斑马线</el-button>
            <el-button size="small" :disabled="!points.length" @click="undoPoint">撤销点</el-button>
            <el-button size="small" :disabled="!points.length" @click="clearPoints">清空点</el-button>
            <span class="scene-count">{{ points.length }} 点</span>
          </div>
          <div class="scene-canvas" ref="canvasWrap">
            <img :src="firstFrameUrl" class="scene-img" ref="sceneImg" @click="onCanvasClick"
                 alt="标注画布" />
            <svg class="scene-svg" :viewBox="`0 0 ${frameW} ${frameH}`" preserveAspectRatio="none">
              <!-- 已保存的区域 -->
              <polygon v-for="(z, zi) in zones" :key="'z' + zi"
                       :points="polyStr(z.points)"
                       :class="'poly poly--' + z.type" />
              <!-- 正在绘制的 -->
              <polygon v-if="points.length >= 3" :points="polygonPoints" class="poly poly--draw" />
              <polyline v-else-if="points.length === 2" :points="polygonPoints" class="poly-line" />
              <circle v-for="(p, i) in points" :key="'p' + i" :cx="p[0]" :cy="p[1]" r="7" class="pt" />
            </svg>
          </div>
        </div>

        <!-- 右侧：区域列表 + 相机参数 -->
        <div class="scene-right">
          <div class="sr-block">
            <div class="sr-title">
              已标注区域 <span class="sr-count">{{ zones.length }}</span>
            </div>
            <div class="zone-list">
              <div v-if="!zones.length" class="empty">暂无区域，请在左侧绘制</div>
              <div v-for="(z, zi) in zones" :key="'zl' + zi" class="zone-item">
                <span class="zi-dot" :class="'dot--' + z.type"></span>
                <span class="zi-name">{{ zoneLabel(z.type) }}</span>
                <span class="zi-pts">{{ z.points.length }} 点</span>
                <el-button size="small" text type="danger" @click="removeZone(zi)">删除</el-button>
              </div>
            </div>
            <el-button size="small" :disabled="points.length < 3" type="primary"
                       plain style="width:100%;margin-top:6px" @click="addZone">
              添加到列表（当前 {{ points.length }} 点）
            </el-button>
          </div>

          <div class="sr-block">
            <div class="sr-title">相机参数 <span class="sr-hint">测速准确的前提</span></div>
            <div class="cam-form">
              <div class="cf-row">
                <span class="cf-label">安装高度</span>
                <el-input-number v-model="cam.height" :min="1" :max="60" :step="0.5"
                                 size="small" controls-position="right" style="width:104px" />
                <span class="cf-unit">米</span>
              </div>
              <div class="cf-row">
                <span class="cf-label">俯角</span>
                <el-input-number v-model="cam.pitch" :min="-89" :max="-1" :step="1"
                                 size="small" controls-position="right" style="width:104px" />
                <span class="cf-unit">度（向下为负）</span>
              </div>
              <div class="cf-row">
                <span class="cf-label">视场角</span>
                <el-input-number v-model="cam.fov" :min="20" :max="120" :step="1"
                                 size="small" controls-position="right" style="width:104px" />
                <span class="cf-unit">度</span>
              </div>
              <div class="cf-presets">
                <el-button size="small" text @click="applyPreset('pole8')">路口立杆 8m/-20°</el-button>
                <el-button size="small" text @click="applyPreset('pole6')">低杆 6m/-15°</el-button>
                <el-button size="small" text @click="applyPreset('high12')">高杆 12m/-28°</el-button>
              </div>
              <div class="cf-note" v-if="ppmPreview">
                该参数下 ppm：<b>{{ ppmPreview.low }}</b>（画面下方）~ <b>{{ ppmPreview.high }}</b>（远处）
              </div>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="sceneDlg = false">取消</el-button>
        <el-button type="primary" :loading="saveBusy" @click="saveScene">
          保存全部（{{ zones.length }} 个区域 + 相机参数）
        </el-button>
      </template>
    </el-dialog>

    <!-- ===== 测速标定 + 信号灯 ROI 面板（2026-10-06 由 DSH 新建）=====
         拆成独立组件而不是继续往这个对话框里堆：原「场景标注」弹窗已有
         多边形区域 + 相机参数两件事，再塞 ROI 框选/停止线/地面点/参数校验
         会变成一个 400 行模板的巨型组件，改一处怕动全身。 -->
    <!-- ★★2026-10-09 由 DSH 修正（设计单 §12.5 根因 A 的修法 2）：
         `:source` 由 **输入框文本** 改为 **calSrc = 后端正在跑的源**。
         这是"标定没起作用"最直接的一条根因 —— 面板原先跟着输入框走，
         而输入框会被刷新重置成硬编码的旧视频，于是：
           面板显示旧视频首帧 -> 用户在**错画面**上画 ROI -> 保存到**错的视频**。
         现在面板的预览源与保存目标**必然一致**（都取 runningSource）。
         `:source-mismatch` / `:input-source` 用于面板内的红警告 + 禁止保存。 -->
    <CalibrationPanel v-model="calDlg" :source="calSrc"
                      :running-source="runningSource"
                      :input-source="sourceValue"
                      :source-mismatch="sourceMismatch"
                      :frame-width="frameW" :frame-height="frameH"
                      @saved="onCalibrationSaved" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'
import CalibrationPanel from './CalibrationPanel.vue'

const API_BASE = import.meta.env.VITE_API_BASE || ''
const streamUrl = ref((API_BASE || '') + '/api/realtime/stream?_=' + Date.now())
const streamOk = ref(false)

const status = ref({})
const tlStats = ref({})
const vehicles = reactive({ clean: [], violators: [], traffic_lights: [] })
const evidence = ref([])
const evidenceTotal = ref(0)

const sourceKind = ref('file')
// ★★2026-10-09 由 DSH 修正（设计单 §12.5 根因 A）：**干掉硬编码的默认源**。
//
// 原来这里写死 'E:\\output\\1\\test_assets\\traffic_videos\\ea1ca6cb….mp4'
// （一个 B 站测试视频），后果链：
//   ① 用户无论输入什么，**刷新页面就被重置回那个旧视频**
//      （用户原话："输入框总是自己跳变成这个 B 站录制的视频，导致我根本没法自己校验"）；
//   ② 标定面板的 source 跟着这个输入框走 -> 用户在**错误的画面**上画 ROI；
//   ③ 保存时用的是同一个错源 -> **标定存到了错的视频上**。
// 实测证据（_uicheck\diag-calib-source.mjs）：后端在跑 _dual_cam_demo\…mkv，
//   页面输入框却是 ea1ca6cb…mp4，面板首帧 1280x576（旧视频）而非 1920x1080。
//
// 现在的优先级：localStorage 里"上次用过的源" -> 空。
// **绝不写死任何视频路径**。页面挂载后再由 /status 的 video_path 接管
// （见 syncFromStatus / runningSource）。
const SOURCE_LS_KEY = 'zt_live_source_v1'
const sourceValue = ref(localStorage.getItem(SOURCE_LS_KEY) || '')
const cameraIndex = ref(0)
const busy = ref(false)

const settings = reactive({
  enabled_types: { wrong_way: true, red_light: true, illegal_parking: true, lane_departure: true, no_helmet: true, speeding: true },
  cloud_consult: true,
  // ★事件级云端 AI 复核总开关（2026-10-06 由 DSH 新增，默认开=保持原行为）
  cloud_review: true,
})
// ★★2026-10-09 由 DSH 新增：**云端开关是否已与后端同步**。
// 上面两个默认值只是"占位"，真正生效的值必须来自后端（loadSettings）；
// 同步失败时把控件置灰，避免"界面显示的值"与"后端的值"不一致后又把错的值推回去
// （这正是"开关自动打开"的另一半原因）。
const cloudSynced = ref(false)
const typeList = [
  { key: 'wrong_way', cn: '逆行' }, { key: 'red_light', cn: '闯红灯' },
  { key: 'illegal_parking', cn: '违停' }, { key: 'lane_departure', cn: '压线' },
  { key: 'no_helmet', cn: '未戴头盔' }, { key: 'speeding', cn: '超速' },
]
const confDefault = ref(0.65)
const holdSec = ref(1.5)
const cooldownSec = ref(8)

// 聚焦小窗：静态快照（dataURL）+ 目标信息（2026-10-04 由 DSH 重写）
// 内容直接来自"检测框区域"的裁切放大，不再请求独立接口。
const zoomSnap = ref('')
const zoomInfo = ref({ id: '', type: '', violation: '' })
// 聚焦小窗开关（2026-10-04 由 DSH 新增）：默认开启，可关闭以免干扰观察
const focusPip = ref(true)
// 标注分级显示（2026-10-04 由 DSH 新增）
// 车辆多时画面会被检测框与标签淹没，极简档只画 ID + 方向箭头，
// 其余信息（速度/车牌/违规类型）由左栏卡片承载。
const displayMode = ref('minimal')
const sceneDlg = ref(false)
// ★测速标定 + 信号灯 ROI 面板（2026-10-06 由 DSH 新增）
const calDlg = ref(false)
const roiMissing = ref(false)
// 运行时的灯态作用域（只用于状态条徽标，**不回写** roiMissing，见 refresh() 里的注释）
const lightScope = ref('')

// ============================================================================
// ★★2026-10-09 由 DSH 新增：**"正在跑的源"必须可观测、且是标定的唯一依据**
//    （设计单 §12.5 根因 A 的修法 0~4）
//
// 核心原则一句话：**标定面板的源 = 后端正在跑的源，不是输入框里的文本**。
//   输入框只是"下次点开始时要用的源"，两者在没人点「开始」时天然可以不相等；
//   而"在错画面上标、存到错的视频"正是因为这个区分缺失。
// ============================================================================
/** 后端当前真正在跑的源（文件路径 或 流地址），来自 /api/realtime/status */
const runningSource = computed(() => status.value?.video_path || status.value?.source_url || '')
/** 规范化后比较（后端按原始字符串算 sha1，所以这里只做"看起来是不是同一个"的提示 */
function normSrc(s) {
  return String(s || '').trim().replace(/\\/g, '/').toLowerCase()
}
/** 输入框的源 != 正在跑的源 -> 红警告（此时"开始"会把源换掉，标定也就存到别处） */
const sourceMismatch = computed(() =>
  !!sourceValue.value && !!runningSource.value &&
  normSrc(sourceValue.value) !== normSrc(runningSource.value))
/** ★标定面板真正使用的源：优先"正在跑的源"。
 *  这样"面板显示的画面"与"保存的目标"必然一致 —— 根治"在错画面上标"。 */
const calSrc = computed(() => runningSource.value || sourceValue.value)

/** 把输入框对齐到"正在跑的源"（用户点「同步」按钮时调用；挂载时也自动对齐一次） */
function syncSourceToRunning() {
  if (runningSource.value) {
    sourceValue.value = runningSource.value
    ElMessage.success('已同步为当前正在运行的源')
  } else {
    ElMessage.warning('后端当前没有正在运行的源（先点「开始」）')
  }
}

// 记住"上次用过的源"：刷新后不再跳回某个写死的视频（但绝不写死默认值）
watch(sourceValue, (v) => {
  try {
    if (v) localStorage.setItem(SOURCE_LS_KEY, v)
    else localStorage.removeItem(SOURCE_LS_KEY)
  } catch (e) { /* 隐私模式下 localStorage 可能不可用，忽略 */ }
})

// ============================================================================
// ★★2026-10-11 由 DSH 新增：**WebSocket 推送 -> 立刻刷新违规告警**
//
// 用户问："速度还是比视频左上角出现的检测要慢一些，这是为什么？明明用的是同一个代码"
// 原因不是同一段代码，而是**两条不同的链路**：
//   · 画面左上角的标注：检测那一帧**直接画在图上**，编成 JPEG 进 MJPEG 流（20fps 持续推）
//     -> 判定成立后下一个流帧就能看到，追加延迟 ≈ 0
//   · 右栏告警：写进 `_recent_violations` 缓存，前端**定时去问**（轮询）
//     -> 追加延迟 = 一次轮询周期的等待（平均 T/2、最坏 T）
// 实测（`_scripts\_measure_alert_latency.py`）：**后端 -> 接口的延迟是 0ms**，
//   也就是说慢的那部分**全部**来自轮询等待（当时 T=800ms -> 平均多等 400ms）。
// 修法：项目**本来就有** `/api/realtime/violations/stream` 这个 WebSocket 在推违规事件
//   （后端 `_push_violation_event`，但前端从来没人接）。
//   这里把它接上，**收到推送就立刻拉一次数据**（不是把数据从推送里解出来 —— 保持
//   单一数据源 `/vehicles`，避免两套解析逻辑漂移）。轮询仍然保留作为兜底。
// ============================================================================
let ws = null
let wsRetry = null
let wsPing = null
let wsRefreshTimer = null
// ★2026-10-11：端到端延迟埋点（用 window.__alertLatency 读）
let pendingPushAt = null
let pendingPushN = 0
let pendingServerAt = null
let lastPushAt = 0
try { window.__alertLatency = [] } catch (e) { /* ignore */ }

function wsUrl() {
  // ★2026-10-11：**直连后端**，不走 Vite 代理。
  //   原因（实测）：`vite.config.js` 的 `/api` 代理**没有开 `ws: true`**，
  //   所以 WebSocket 的 upgrade 请求不会被转发 -> 前端 `new WebSocket('/api/...')`
  //   连不上（CDP 里只能看到 2 个连接、没有第三个），告警就只能靠轮询。
  //   改代理配置需要重启 dev server（会打断用户），而项目里**本来就有直连先例**
  //   （`api/index.js` 的 `realtimeRequest` 就是直连 `:8001`），所以这里同样直连。
  //   可用 VITE_WS_BASE 覆盖（生产环境部署时按实际后端地址填）。
  const direct = import.meta.env.VITE_WS_BASE || 'http://127.0.0.1:8001'
  const u = new URL(direct, window.location.origin)
  u.protocol = u.protocol === 'https:' ? 'wss:' : 'ws:'
  u.pathname = '/api/realtime/violations/stream'
  u.search = ''
  return u.toString()
}

function connectViolationWs() {
  try {
    ws = new WebSocket(wsUrl())
  } catch (e) {
    console.warn('[LiveMonitor] 违规推送连接失败（继续用轮询兜底）:', e && e.message)
    scheduleWsRetry()
    return
  }
  ws.onopen = () => {
    console.log('[LiveMonitor] 违规推送已连接：', wsUrl(), '（收到推送会立刻刷新告警，不用等轮询）')
    // 后端循环里 await receive_text()，定期 ping 一下保持连接活跃
    clearInterval(wsPing)
    wsPing = setInterval(() => {
      try { if (ws && ws.readyState === 1) ws.send('ping') } catch (e) { /* ignore */ }
    }, 20000)
  }
  ws.onmessage = (ev) => {
    let msg = null
    try { msg = JSON.parse(ev.data) } catch (e) { return }
    if (!msg || msg.event !== 'violation_detected') return
    // ★★2026-10-11 由 DSH 修改：**去掉 150ms 去抖，收到推送立刻刷新**。
    //
    // 用户的问题很关键："我感觉现在这个（去抖）好像没有用了吧？
    //   左边都不需要这个，因为只要告警卡片出现并停留就只算作一次不就行了？"
    // 先澄清概念（避免为错误的理由改代码）：
    //   · **同一辆车 + 同一条违规只出一张卡片**，这是后端 `_push_recent_violations`
    //     用 `(violation_type, track_id)` 做键**合并**实现的，**与去抖无关**；
    //   · 去抖（debounce）唯一的作用是："多条推送在极短时间内到达时只发一次请求"，
    //     即**省请求**，不影响计数、也不影响卡片停留。
    // 但它确实是我**随手定的 150ms、没有实测依据**，而用户明确感觉它没用 ——
    //   它的收益（省掉并发请求）远小于代价（每次都慢 150ms，占了端到端延迟的一大半：
    //   实测推送->DOM = 152~277ms，其中 150ms 就是它）。
    // 所以改为**直接刷新**；若将来出现"连续推送打爆请求"，再按需加回（并说明依据）。
    pendingPushAt = performance.now()
    pendingPushN = (msg.violations || []).length
    // ★2026-10-11：服务端发出时刻（epoch ms），用于把端到端延迟拆成两半
    pendingServerAt = (typeof msg.pushed_at === 'number') ? msg.pushed_at : null
    refresh()
  }
  ws.onclose = () => {
    clearInterval(wsPing)
    wsPing = null
    scheduleWsRetry()
  }
  ws.onerror = () => {
    console.warn('[LiveMonitor] 违规推送连接出错，3 秒后重试（期间靠轮询）:', wsUrl())
    try { ws.close() } catch (e) { /* ignore */ }
  }
}

function scheduleWsRetry() {
  clearTimeout(wsRetry)
  wsRetry = setTimeout(() => { if (!ws || ws.readyState > 1) connectViolationWs() }, 3000)
}

function closeViolationWs() {
  clearTimeout(wsRetry)
  clearTimeout(wsRefreshTimer)
  clearInterval(wsPing)
  wsPing = null
  try { if (ws) { ws.onclose = null; ws.close() } } catch (e) { /* ignore */ }
  ws = null
}

/** ★页面挂载后**自动对齐一次**"正在跑的源"（设计单 §12.5 修法 1）
 *
 *  为什么只自动做一次：第一次 /status 回来时如果后端确实在跑某个文件源，
 *  那它才是"用户当时看到的画面"，输入框理应对齐它；但**不能每 1.5 秒都强行
 *  覆盖**用户正在输入的内容（那会变成另一种"输入框自己跳变"）。
 *  之后若后端换了源（或用户手改了输入框），靠 sourceMismatch 红警告提示，
 *  由用户点「同步」按钮决定 —— 决定权交给用户，但**不许静默漂移**。
 */
let didAutoSync = false
async function syncFromStatusOnce() {
  if (didAutoSync) return
  try {
    const r = await api.get('/realtime/status')
    const st = r?.data?.data || r?.data || {}
    const run = st.video_path || st.source_url || ''
    if (run) {
      didAutoSync = true
      sourceValue.value = run
      if (st.source_kind === 'stream') sourceKind.value = 'stream'
    }
  } catch (e) { /* 后端没起：保持输入框现状（localStorage 里的上次值） */ }
}
const aiBusy = ref(false)
const points = ref([])
const frameW = ref(1280)
const frameH = ref(576)
const sceneImg = ref(null)
const firstFrameUrl = computed(() =>
  `${API_BASE}/api/scene/first-frame?source=${encodeURIComponent(sourceValue.value)}&_=${Date.now()}`)
const polygonPoints = computed(() => points.value.map(p => `${p[0]},${p[1]}`).join(' '))

/** 灯态作用域 -> 中文（2026-10-06 由 DSH 新增）
 *  取值来自后端 realtime_detector._light_scope：
 *    roi      = 只统计人工标注 traffic_light_roi 内的灯（**唯一可信**）
 *    frame    = 未标注 ROI，退回"画面里任意一盏灯" → 闯红灯判定不可信
 *    roi_miss = 标了 ROI 但本帧 ROI 内没判出灯（不退回全画面，符合设计）
 */
const scopeCn = computed(() => ({
  roi: '车道级(ROI)',
  frame: '全画面未标定',
  roi_miss: 'ROI内未检出',
}[lightScope.value] || lightScope.value || '未启动'))

const scopeTip = computed(() => ({
  roi: '灯态取自人工标注的信号灯 ROI —— 受控方向正确，闯红灯判定可信。',
  frame: '⚠ 未标注「信号灯 ROI」（或检测未启动，后端固定报 frame）：'
       + '灯态会取画面里任意一盏灯（红>绿>黄），横向车道的红灯会被当成本方向的 —— '
       + '实测每循环误报 5~7 次。请点右上角「测速标定/信号灯ROI」把受控方向那盏灯圈出来。',
  roi_miss: '已标注 ROI，但本帧 ROI 内没判出灯（远处小灯偶发漏检）。'
          + '按设计不退回全画面，因此本帧灯态可能为空。',
}[status.value.traffic_light_scope] || ''))

// 面板打开时才知道有没有标 ROI：从场景标注接口读一次（不阻塞主流程）
const checkingRoi = ref(false)

let timer = null
let zoomTimer = null

function dirCn(d) {
  // 2026-10-03 由 DSH 修正：原来对未识别值直接回显英文（界面出现 "unknown"）
  const m = {
    up: '向上', down: '向下', left: '向左', right: '向右',
    stationary: '静止', still: '静止',
    unknown: '方向待定', '': '方向待定',
  }
  if (d === null || d === undefined) return '方向待定'
  return m[String(d).toLowerCase()] || '方向待定'
}

function onStreamLoad() { streamOk.value = true }
function onStreamError() { streamOk.value = false }

/** 测速可信度 -> 中文（2026-10-03 由 DSH 新增）
 *  后端 speed_calibration 的 confidence 取值：
 *    calibrated / low_samples / low_quality / assumed / unavailable
 */
function speedConfCn(c) {
  const m = {
    calibrated: '已标定',
    low_samples: '采样少',
    low_quality: '质量差',
    assumed: '未标定',
    unavailable: '不可用',
  }
  return m[String(c || '').toLowerCase()] || '未标定'
}

/** 测速可信度 -> 徽标配色类 */
function speedBadgeClass(c) {
  const k = String(c || '').toLowerCase()
  if (k === 'calibrated') return 'ok'
  if (k === 'assumed') return 'assumed'
  return 'warn'
}

async function refresh() {
  try {
    const [s, v] = await Promise.all([
      api.get('/realtime/status').catch(() => null),
      api.get('/realtime/vehicles').catch(() => null),
    ])
    if (s?.data?.data) {
      status.value = s.data.data
      tlStats.value = s.data.data.traffic_light_stats || {}
    } else if (s?.data) {
      status.value = s.data
      tlStats.value = s.data.traffic_light_stats || {}
    }
    // ★2026-10-06 由 DSH 修正：这里原来直接写 roiMissing，而 /status 在**未启动检测**时
    //   固定返回 traffic_light_scope="frame"，于是每 1.5 秒的轮询都会把
    //   loadRoiState() 得出的"该源尚未标注 ROI"结论**覆盖成 false**
    //   -> 按钮永远不显示"未标"警告（实测：接口明说 roi=0，按钮却一直是默认态）。
    //   现在拆成两个独立状态：
    //     roiMissing  —— 只由"该源的场景标注里有没有 traffic_light_roi"决定（loadRoiState）
    //     lightScope  —— 运行时的灯态作用域（只喂给状态条徽标，不再回写按钮）
    //
    // ★★2026-10-09 由 DSH 修复：**`sc` 从来没有被定义过**（未定义变量）。
    //   JS 抛 ReferenceError -> 被本函数末尾的 `catch { /* 静默 */ }` 吞掉 ->
    //   **从这一行往下的代码全部不执行**，包括 /realtime/vehicles 的赋值与
    //   聚焦小窗，于是"左右分流车辆栏"永远空、灯态徽标永远不亮。
    //   这是一次"静默 catch + 未定义变量"叠加的隐形回归（本级教训：兜底必须可观测）。
    const sc = status.value?.traffic_light_scope || ''
    lightScope.value = sc
    const d = v?.data?.data || v?.data
    if (d) {
      vehicles.clean = d.clean || []
      vehicles.violators = d.violators || []
      vehicles.traffic_lights = d.traffic_lights || []
      // ★2026-10-11：推送 -> DOM 的端到端延迟埋点（见 connectViolationWs 的说明）
      if (pendingPushAt != null && vehicles.violators.length) {
        const ms = performance.now() - pendingPushAt
        // 关键：`refresh()` 只把数据写进响应式状态，DOM 要等**下一次渲染**才变。
        // 所以这里再挂一个 rAF + 0ms 宏任务，等到真正渲染完再结算。
        const pushAt = pendingPushAt
        pendingPushAt = null
        requestAnimationFrame(() => setTimeout(() => {
          try {
            const el = document.querySelector('.panel--right .ph-count')
            const shown = el ? el.textContent.trim() : '?'
            const nowMs = Date.now()
            const nowPerf = performance.now()
            const rec = {
              // 前端侧：浏览器收到推送 -> DOM 出现卡片
              pushToDomMs: Math.round(nowPerf - pushAt),
              // 服务端侧：后端发出推送 -> 此刻（含网络 + 前端处理）
              serverToDomMs: pendingServerAt != null ? (nowMs - pendingServerAt) : null,
              shown, pushed: pendingPushN, t: new Date().toISOString(),
            }
            if (window.__alertLatency) {
              window.__alertLatency.push(rec)
              if (window.__alertLatency.length > 50) window.__alertLatency.shift()
            }
            // 控制台也打一条，方便人工边看边核对
            console.log('[告警延迟] 前端侧 %dms%s', rec.pushToDomMs,
              rec.serverToDomMs != null ? `，服务端起算 ${rec.serverToDomMs}ms` : '')
          } catch (e) { /* ignore */ }
        }, 0))
      }
      // 有违规 -> 抓取该车辆检测框区域的快照（仅展示层）
      // ★2026-10-10：跳过 stale（已离开画面）的条目 —— 它此刻已不在流里，
      //   裁切只会得到"框住空白/别的车"的图，正是用户说的"无意义的取证"观感。
      const liveViolator = vehicles.violators.find(x => !x.stale)
      if (liveViolator && !zoomSnap.value) triggerZoom(liveViolator)
    }
  } catch (e) { /* 静默：轮询失败不打扰用户 */ }
}

/** 聚焦小窗：**直接裁切检测框区域**（2026-10-04 由 DSH 重写，用户要求）
 *
 * 用户原话："聚焦小窗口的显示内容直接引用检测框里的内容的就行了"
 *
 * 原实现请求 /api/realtime/zoom-frame（后端按 track_id 重新取帧裁切），
 * 问题：① 小窗内容与画面上框住的区域可能不一致（时间差）
 *       ② 多一次 HTTP 往返
 * 现改为：把**已经绘制好的一帧**（就是画面上正在显示的那帧）画到 canvas，
 *        再按该车辆的 bbox 裁切并放大 -> 保证小窗内容 == 画面框住的内容。
 *
 * 注意：流是 MJPEG（每帧独立编码），若直接对 <img> 做 canvas 抽样在部分
 * 场景会因二次解码而闪；因此这里**一次采样后转为静态快照**展示，
 * 不逐帧重绘，既稳定又省 CPU。
 */
function captureBBoxSnapshot(target) {
  const img = videoImg.value
  if (!img) return null
  const nw = img.naturalWidth, nh = img.naturalHeight
  if (!nw || !nh) return null
  const bb = target.bbox
  if (!Array.isArray(bb) || bb.length < 4) return null
  const sx = Math.max(0, Math.floor(bb[0]))
  const sy = Math.max(0, Math.floor(bb[1]))
  const sw = Math.max(1, Math.floor(bb[2] - bb[0]))
  const sh = Math.max(1, Math.floor(bb[3] - bb[1]))
  if (sx >= nw || sy >= nh) return null
  const cw = Math.min(sw, nw - sx), ch = Math.min(sh, nh - sy)
  if (cw < 8 || ch < 8) return null

  // 输出：放大到固定高度 240px，最多 2 倍（避免过度插值变糊）
  const scale = Math.min(2.0, Math.max(1.0, 240 / ch))
  const ow = Math.round(cw * scale), oh = Math.round(ch * scale)
  // 外扩一点边距，让目标不贴边（更像"抓拍特写"）
  const pad = 0.18
  const px = Math.max(0, Math.floor(sx - cw * pad))
  const py = Math.max(0, Math.floor(sy - ch * pad))
  const pw = Math.min(nw - px, Math.ceil(cw * (1 + pad * 2)))
  const ph = Math.min(nh - py, Math.ceil(ch * (1 + pad * 2)))

  try {
    const cv = document.createElement('canvas')
    cv.width = ow; cv.height = oh
    const ctx = cv.getContext('2d')
    ctx.imageSmoothingEnabled = true
    ctx.imageSmoothingQuality = 'high'
    ctx.drawImage(img, px, py, pw, ph, 0, 0, ow, oh)
    return cv.toDataURL('image/jpeg', 0.88)
  } catch (e) {
    // 跨域污染等异常 -> 退回不改小窗（不抛错打断主流程）
    return null
  }
}

/** 聚焦小窗：仅作用于展示层，落盘证据始终是原始整帧 */
function triggerZoom(target) {
  if (!focusPip.value || !target) return
  const snap = captureBBoxSnapshot(target)
  if (!snap) return
  zoomSnap.value = snap
  zoomInfo.value = {
    id: target.track_id,
    type: target.class_name_cn || target.class_name || '',
    violation: target.primary_violation || '',
  }
  clearTimeout(zoomTimer)
  zoomTimer = setTimeout(() => { zoomSnap.value = '' }, 1600)   // 定格后收起
}

// ---------- 全屏（2026-10-04 由 DSH 新增，用户要求）----------
const videoWrap = ref(null)
const videoImg = ref(null)
const isFs = ref(false)

function toggleFullscreen() {
  const el = videoWrap.value
  if (!el) return
  try {
    if (!document.fullscreenElement) {
      (el.requestFullscreen ? el.requestFullscreen() : el.webkitRequestFullscreen?.())
    } else {
      (document.exitFullscreen ? document.exitFullscreen() : document.webkitExitFullscreen?.())
    }
  } catch (e) {
    ElMessage.warning('该浏览器不支持全屏')
  }
}

function onFsChange() {
  isFs.value = !!document.fullscreenElement
}

async function startDetection() {
  busy.value = true
  try {
    const payload = {}
    if (sourceKind.value === 'camera') payload.camera_index = Number(cameraIndex.value) || 0
    else payload.video_path = sourceValue.value
    const response = await api.post('/realtime/start', payload)
    const result = response?.data
    if (!result?.success) {
      throw new Error(result?.message || '后端未确认启动成功')
    }
    ElMessage.success('检测已启动')
    streamUrl.value = (API_BASE || '') + '/api/realtime/stream?_=' + Date.now()
    streamOk.value = false
  } catch (e) {
    ElMessage.error('启动失败：' + (e?.response?.data?.message || e?.response?.data?.detail || e.message))
  } finally { busy.value = false }
}

async function stopDetection() {
  try { await api.post('/realtime/stop'); ElMessage.info('已停止') } catch (e) { /* ignore */ }
}

async function pushSettings() {
  try {
    // ★★2026-10-09 由 DSH 修复：**不再连带推送两个付费云端开关**。
    //
    // 用户报的现象："两个云端开关有时候会自动打开"。
    // 根因（设计单 §8）：本函数被"检测项勾选 / 置信度滑条 / 确认时长 / 冷却期"
    //   等多处控件调用，而它**顺手把 cloud_consult / cloud_review 也推回后端**
    //   （按**内存里的当前值**）。只要内存里的值不是用户以为的值
    //   （用户在设置页关了、而从没进过本页 -> 本页从未 loadSettings；
    //     或 loadSettings 因超时走了 catch 分支没赋值；或组件默认值是 true），
    //   就会**静默把付费开关打开** —— 每次违规事件都打 2~3 家云 API（真花钱）。
    //   后端侧本来是对的：`update_runtime_settings()` 只更新传入的字段。
    //
    // 现在这两个开关**只由各自的控件单独推送**（见 pushCloudReview / pushCloudConsult）。
    await api.post('/realtime/settings', {
      enabled_types: settings.enabled_types,
      min_confidence: { _default: confDefault.value },
      hold_sec: holdSec.value,
      cooldown_sec: cooldownSec.value,
      display_mode: displayMode.value,
    })
  } catch (e) { /* ignore */ }
}

/** 逐帧云端咨询开关（★2026-10-09 新增：与 cloud_review 拆开，各自单独推送） */
async function pushCloudConsult() {
  try {
    const r = await api.post('/realtime/settings', { cloud_consult: settings.cloud_consult })
    const d = r?.data?.data || r?.data
    if (d && typeof d.cloud_consult === 'boolean') settings.cloud_consult = d.cloud_consult
    ElMessage[settings.cloud_consult ? 'warning' : 'success'](
      settings.cloud_consult ? '已开启逐帧云端咨询（不确定的帧会咨询云端，计费）'
                             : '已关闭逐帧云端咨询')
  } catch (e) {
    ElMessage.error('切换逐帧云端咨询失败：' + (e?.response?.data?.detail || e.message))
    await loadSettings()
  }
}

/** ★云端 AI 复核总开关（2026-10-06 由 DSH 新增）
 *  只改这一项（不连带推其它设置），并按后端返回的实际值回写，
 *  避免"界面显示关了、后端其实还开着"这种最费钱的假象。
 */
async function pushCloudReview() {
  try {
    const r = await api.post('/realtime/settings', { cloud_review: settings.cloud_review })
    const d = r?.data?.data || r?.data
    if (d && typeof d.cloud_review === 'boolean') settings.cloud_review = d.cloud_review
    if (settings.cloud_review) {
      ElMessage.warning('已开启事件级云端 AI 复核：每条违规事件都会产生云端调用（计费）')
    } else {
      ElMessage.success('已关闭事件级云端 AI 复核：事件将转「待人工复核」，不再产生云端费用')
    }
  } catch (e) {
    ElMessage.error('切换云端 AI 复核失败：' + (e?.response?.data?.detail || e.message))
    // 失败则回读真实状态，绝不让界面与后端不一致
    await loadSettings()
  }
}

/** 切换标注档位（2026-10-04 由 DSH 新增）——只改这一项，不连带推其它设置 */async function pushDisplayMode() {
  try {
    const r = await api.post('/realtime/settings', { display_mode: displayMode.value })
    const d = r?.data?.data || r?.data
    if (d && d.display_mode) displayMode.value = d.display_mode
  } catch (e) {
    ElMessage.error('切换标注档位失败')
  }
}

async function loadSettings() {
  try {
    const r = await api.get('/realtime/settings')
    const d = r?.data?.data || r?.data
    if (d) {
      if (d.enabled_types) Object.assign(settings.enabled_types, d.enabled_types)
      // ★★2026-10-09 由 DSH 修复（fail-open）：原来写的是 `d.cloud_consult !== false`
      //   —— 字段**缺失**（后端异常/返回空对象）时会当成 true，于是界面显示"已开"，
      //   再叠加 pushSettings 的连带推送就真的把它打开了。
      //   现在：**只有后端明确返回布尔值才回写**；拿不到就保持"未同步"并置灰控件，
      //   绝不猜、绝不默认开。
      if (typeof d.cloud_consult === 'boolean') {
        settings.cloud_consult = d.cloud_consult
        cloudSynced.value = true
      } else {
        cloudSynced.value = false
      }
      if (typeof d.cloud_review === 'boolean') {
        settings.cloud_review = d.cloud_review
        cloudSynced.value = true
      } else {
        cloudSynced.value = false
      }
      confDefault.value = d.min_confidence?._default ?? confDefault.value
      holdSec.value = d.hold_sec ?? holdSec.value
      cooldownSec.value = d.cooldown_sec ?? cooldownSec.value
      if (d.display_mode) displayMode.value = d.display_mode
      if (!cloudSynced.value) {
        console.warn('[LiveMonitor] 云端开关状态未同步（后端未返回布尔值）——已置灰，不会推送')
      }
    } else {
      cloudSynced.value = false
    }
  } catch (e) {
    // ★读取失败绝不 fail-open：置灰 + 不推送（宁可显示"未知"，也不能假装开着/关着）
    cloudSynced.value = false
    console.warn('[LiveMonitor] 读取运行时设置失败，云端开关已置灰：', e && e.message)
  }
}

/** 兼容两种响应结构（2026-10-03 由 DSH 修正）
 *
 * 本项目的 api 实例装有响应拦截器，会把 axios 的 response.data **解包**，
 * 因此 r.data 直接就是后端 JSON（{"success":true,"data":[...],"total":N}）。
 * 但部分调用点（如 realtimeRequest）或未来改动可能不解包，故此处两种都兼容。
 * 之前直接写 r?.data?.data 取到 undefined，导致证据墙恒空。
 */
function unwrapPayload(r) {
  const d = r?.data
  if (d && typeof d === 'object' && !Array.isArray(d) && ('data' in d || 'success' in d)) {
    return d                      // 已解包：{success, data, total}
  }
  if (Array.isArray(d)) return { data: d }
  return (d && typeof d === 'object') ? d : {}
}

async function loadEvidence() {
  try {
    // 数据源改用 /api/realtime/evidence（2026-10-03 由 DSH 修正）
    // 原实现调 /violations/list 且图片路径靠猜，实测抓拍墙恒空。
    const r = await api.get('/realtime/evidence', { params: { limit: 24 } })
    const payload = unwrapPayload(r)
    const rows = Array.isArray(payload.data) ? payload.data : []
    evidence.value = rows.map(x => ({
      name: x.name,
      url: `${API_BASE}${x.url}`,
      label: x.type_cn || x.type || '违规',
      time: String(x.time || '').slice(4),          // 兼容旧显示（紧凑）
      // ★2026-10-10 新增：后端已回带的关键信息
      captured_at_disp: String(x.captured_at || '').replace('T', ' ').slice(0, 19),
      violation_at: x.violation_at ? String(x.violation_at).replace('T', ' ').slice(0, 19) : '',
      track_id: x.track_id,
      confidence: x.confidence,
      plate_number: x.plate_number,
      review_status: x.review_status,
      kb: x.size_kb,
    }))
    evidenceTotal.value = payload.total || rows.length
  } catch (e) {
    evidence.value = []
    evidenceTotal.value = 0
  }
}

function onSourceKindChange() {
  if (sourceKind.value === 'stream' && !/^https?:\/\//.test(sourceValue.value)) {
    sourceValue.value = 'http://192.168.1.5:8080/video'
  }
}

// ===== 测速标定 + 信号灯 ROI（2026-10-06 由 DSH 新增）=====
/** 保存标定后回读一次，让按钮的"未标"警告立刻消失 */
async function onCalibrationSaved(cfg) {
  const n = (cfg?.traffic_light_roi || []).length
  if (n) {
    roiMissing.value = false
    ElMessage.success(`信号灯 ROI 已保存 ${n} 个：闯红灯灯态将只认 ROI 内的灯`)
  } else {
    ElMessage.warning('未保存信号灯 ROI —— 闯红灯判定仍取"画面里任意一盏灯"，不可信')
  }
  await loadRoiState()
}

/** 只读一次场景标注，判断是否已标信号灯 ROI（供按钮提示） */
async function loadRoiState() {
  try {
    // ★2026-10-09 由 DSH 修正：读**正在运行的源**的标注，而不是输入框的源。
    // 否则会出现"按钮说未标、其实运行中的源已标好"（或反过来），
    // 同一个"输入框 ≠ 运行源"的病根。
    const r = await api.get('/scene/config', { params: { source: calSrc.value } })
    const d = r?.data?.data || r?.data || {}
    roiMissing.value = !(Array.isArray(d.traffic_light_roi) && d.traffic_light_roi.length)
  } catch (e) { /* 未标注过：保持原状态 */ }
}

// ★2026-10-09 由 DSH 新增：**源一变就重新判断"ROI 标没标"**。
// 实测踩到：页面挂载时后端还没在跑（runningSource 为空 -> 请求打到空源 ->
// roiMissing=true），之后 /status 回来了、源变成了已标定的演示视频，
// 但按钮**一直停在"⚠（未标）"** —— 又是一次"结论算对了、却没有更新时机"。
watch(calSrc, (v, ov) => {
  if (v && v !== ov) loadRoiState()
})

// ===== 场景标注（2026-10-04 由 DSH 重构：多类型区域 + 相机参数）=====
// 用户原话："导入视频时最关键的斑马线，公路，人行道，可停车，不可停车……
//           最好需要人工手绘的步骤怎么不见了？"
// 另外实测证明：几何测速必须知道相机真实参数，否则偏 2.4 倍甚至算出 158km/h。
const ZONE_TYPES = [
  { key: 'crosswalk',   label: '斑马线',   color: '#22D3EE' },
  { key: 'road',        label: '公路区域', color: '#60A5FA' },
  { key: 'sidewalk',    label: '人行道',   color: '#A78BFA' },
  { key: 'parking',     label: '可停车区', color: '#34D399' },
  { key: 'no_parking',  label: '禁停区',   color: '#F87171' },
]
const zoneType = ref('crosswalk')
const zones = ref([])                       // [{type, points:[[x,y],...]}]
const saveBusy = ref(false)
const cam = reactive({ height: 8.0, pitch: -20.0, fov: 70.0 })
// 已载入的行驶方向（2026-10-06 由 DSH 新增）：保存时沿用而不是硬编码，
// 避免把 scene 里人工/标定得到的 road_direction 冲掉。
const roadDir = ref('')

function zoneLabel(k) {
  const z = ZONE_TYPES.find(t => t.key === k)
  return z ? z.label : k
}
function polyStr(pts) {
  return (pts || []).map(p => `${p[0]},${p[1]}`).join(' ')
}
function addZone() {
  if (points.value.length < 3) { ElMessage.warning('至少需要 3 个点'); return }
  zones.value.push({ type: zoneType.value, points: points.value.map(p => [...p]) })
  points.value = []
  ElMessage.success(`已添加「${zoneLabel(zoneType.value)}」（共 ${zones.value.length} 个区域）`)
}
function removeZone(i) { zones.value.splice(i, 1) }
function applyPreset(k) {
  const p = { pole8: [8, -20, 70], pole6: [6, -15, 70], high12: [12, -28, 70] }
  const v = p[k] || p.pole8
  cam.height = v[0]; cam.pitch = v[1]; cam.fov = v[2]
}

// ppm 预览：让用户当场看到参数是否合理（几何公式与后端一致）
const ppmPreview = computed(() => {
  const H = frameH.value || 576, W = frameW.value || 1280
  const f = W / (2 * Math.tan((cam.fov * Math.PI / 180) / 2))
  const th = cam.pitch * Math.PI / 180
  const cp = Math.cos(th), sp = Math.sin(th)
  const fwdX = cp, fwdZ = sp, upX = -sp, upZ = cp
  function distAt(v) {
    const t = -(v - H / 2) / f
    const dx = fwdX + t * upX, dz = fwdZ + t * upZ
    if (Math.abs(dz) < 1e-9) return null
    const s = -cam.height / dz
    return s > 0 ? Math.abs(s * dx) : null
  }
  function ppmAt(v) {
    const d1 = distAt(v - 1), d2 = distAt(v + 1)
    if (d1 == null || d2 == null) return null
    const dm = Math.abs(d2 - d1)
    return dm > 1e-9 ? 1 / (dm / 2) : null
  }
  const near = ppmAt(H * 0.95), mid = ppmAt(H * 0.5)
  if (!near || !mid) return null
  return { low: near.toFixed(0), high: mid.toFixed(1) }
})

function openSceneDialog() {
  points.value = []
  sceneDlg.value = true
  loadSceneConfig()
}

// 载入已有标注，便于继续编辑（而不是每次从零开始）
async function loadSceneConfig() {
  try {
    const r = await api.get('/scene/config', { params: { source: sourceValue.value } })
    const d = r?.data?.data || r?.data
    const cfg = d?.config || d || {}
    const out = []
    const put = (key, type) => {
      (cfg[key] || []).forEach(poly => {
        if (Array.isArray(poly) && poly.length >= 3) out.push({ type, points: poly })
      })
    }
    put('crosswalk_zones', 'crosswalk')
    put('road_zones', 'road')
    put('sidewalk_zones', 'sidewalk')
    put('parking_zones', 'parking')
    put('no_parking_zones', 'no_parking')
    zones.value = out
    if (cfg.camera_height_m != null) cam.height = Number(cfg.camera_height_m)
    if (cfg.camera_pitch_deg != null) cam.pitch = Number(cfg.camera_pitch_deg)
    if (cfg.fov_deg != null) cam.fov = Number(cfg.fov_deg)
    roadDir.value = cfg.road_direction || ''
    if (out.length) ElMessage.info(`已载入 ${out.length} 个已标注区域`)
  } catch (e) { /* 首次使用时没有配置，忽略 */ }
}

function onCanvasClick(ev) {
  const img = sceneImg.value
  if (!img) return
  const rect = img.getBoundingClientRect()
  const nw = img.naturalWidth || frameW.value
  const nh = img.naturalHeight || frameH.value
  frameW.value = nw; frameH.value = nh
  const x = Math.round((ev.clientX - rect.left) / rect.width * nw)
  const y = Math.round((ev.clientY - rect.top) / rect.height * nh)
  // 多边形不再限制 4 点（公路/人行道等区域需要更多点）；上限 20 防止误点
  if (points.value.length >= 20) {
    ElMessage.warning('单区域最多 20 个点，请先「添加到列表」或清空')
    return
  }
  points.value.push([x, y])
}

function undoPoint() { points.value.pop() }
function clearPoints() { points.value = [] }

async function aiDetect() {
  aiBusy.value = true
  try {
    const r = await api.post('/scene/auto-detect', null,
      { params: { source: sourceValue.value, use_current: false } })
    const d = r?.data?.data || r?.data
    const z = d?.crosswalk_zones || []
    if (z.length) {
      points.value = z[0].map(p => [Math.round(p[0]), Math.round(p[1])])
      zoneType.value = 'crosswalk'
      ElMessage.warning('已填入 AI 建议的斑马线，请人工核对后再「添加到列表」')
    } else {
      ElMessage.info('AI 未检测到斑马线，请手动点击角点')
    }
  } catch (e) {
    ElMessage.error('AI 检测失败')
  } finally { aiBusy.value = false }
}

async function saveScene() {
  saveBusy.value = true
  try {
    // 按类型分组（后端 _ALLOWED_KEYS 已包含这些字段）
    const cfg = {
      crosswalk_zones: [], road_zones: [], sidewalk_zones: [],
      parking_zones: [], no_parking_zones: [],
      camera_height_m: cam.height,
      camera_pitch_deg: cam.pitch,
      fov_deg: cam.fov,
      frame_width: frameW.value,
      frame_height: frameH.value,
      // ★2026-10-06 由 DSH 新增：**清除**历史遗留的 pixel_per_meter。
      // 病根链：realtime_detector 的 scene_config 默认塞 `pixel_per_meter: 10`
      // （违停/旧规则兜底用），只要它落在 scene 标注里，就会一路传进
      // SpeedCalibrator 并**抢在相机几何之前**当上标定依据 ——
      // 表现为后台显示"已标定（手工 ppm）"，但地平线/ppm 表/可解比例全空。
      // 本页只负责人手绘区域与相机几何，因此明确清除该字段（传 null 即删除）。
      pixel_per_meter: null,
      // ★2026-10-06 由 DSH 修正：原来硬编码 'south'，会把盘上的 road_direction
      // 覆盖掉（演示视频实测盘上是 'up'）。而且本演示机位是纵深机位，
      // "画面左右"推不出车道方向 —— 逆行判定故意留空（判不准就不判）。
      // 这里改成"沿用已载入的值，没有就不发这个字段"。
      ...(roadDir.value ? { road_direction: roadDir.value } : {}),
    }
    const map = {
      crosswalk: 'crosswalk_zones', road: 'road_zones', sidewalk: 'sidewalk_zones',
      parking: 'parking_zones', no_parking: 'no_parking_zones',
    }
    zones.value.forEach(z => { (cfg[map[z.type]] ||= []).push(z.points) })
    // 有禁停区时同时打开场景级标志（供 violation_rules 参考）
    cfg.is_no_parking_zone = cfg.no_parking_zones.length > 0

    await api.post('/scene/config', {
      source: sourceValue.value,
      config: cfg,
      annotated_by: 'manual',
    })
    const n = zones.value.length
    ElMessage.success(`已保存：${n} 个区域 + 相机参数（${cam.height}m / ${cam.pitch}° / ${cam.fov}°）`)
    sceneDlg.value = false
  } catch (e) {
    ElMessage.error('保存失败：' + (e?.response?.data?.detail || e.message))
  } finally { saveBusy.value = false }
}

onMounted(() => {
  loadSettings()
  refresh()
  loadEvidence()
  loadRoiState()          // 2026-10-06 由 DSH 新增：按钮上标出"信号灯 ROI 未标"
  // ★2026-10-09 由 DSH 新增：把输入框对齐到"后端正在跑的源"（只对齐一次）。
  // 这是"干掉硬编码默认源"后的配套动作 —— 否则用户每次刷新都要手打一遍长路径。
  syncFromStatusOnce()
  // ★2026-10-10 由 DSH 调整：1.5s -> 0.8s。
  //   实测右栏一条违规的可见窗口只有 ~2.9 秒，而 1.5 秒的轮询意味着
  //   "最坏情况整段错过"（用户反馈"来不及反应"）。配合后端保留已离开画面的告警，
  //   这里再把采样周期缩短到 0.8 秒，让告警更快出现。
  timer = setInterval(refresh, 800)
  // ★2026-10-11 由 DSH 新增：接上违规 WebSocket 推送 —— 后端一判定成立就**立刻**刷新，
  //   不再等下一次轮询（实测后端->接口延迟 0ms，慢的全是轮询等待）。
  //   轮询保留作为兜底（断线/后端没推时仍能更新）。
  connectViolationWs()
  // 全屏状态监听（2026-10-04 由 DSH 新增）：让按钮图标随状态切换
  document.addEventListener('fullscreenchange', onFsChange)
})
onUnmounted(() => {
  if (timer) clearInterval(timer)
  if (zoomTimer) clearTimeout(zoomTimer)
  closeViolationWs()
  document.removeEventListener('fullscreenchange', onFsChange)
})
</script>

<style scoped>
.live-page { padding: 12px; display: flex; flex-direction: column; gap: 12px; }

/* ---------- 顶部状态条 ---------- */
.live-bar {
  display: flex; justify-content: space-between; align-items: center; gap: 12px;
  background: var(--zt-surface); border: 1px solid var(--zt-border);
  border-radius: var(--zt-radius); padding: 8px 14px; flex-wrap: wrap;
}
.bar-left { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.bar-right { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.bar-title { font-weight: 600; color: var(--zt-text); }
.bar-meta { font-size: 12px; color: var(--zt-text-muted); }
.dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.dot.on { background: var(--zt-success); box-shadow: 0 0 0 3px rgba(22,163,74,.18); }
.dot.off { background: var(--zt-text-muted); }
/* 云端复核关闭时的醒目提示（2026-10-06 由 DSH 新增） */
.ck-warn :deep(.el-checkbox__label) { color: #b45309; font-weight: 600; }
/* 灯态作用域徽标（2026-10-06 由 DSH 新增）：未标 ROI 必须一眼看出来 */
.bar-meta.scope { padding: 1px 7px; border-radius: 9px; border: 1px solid transparent; }
/* ★2026-10-10 由 DSH 新增：右栏"已离开画面"的违规卡片标记
   背景：违规车驶出画面后告警会保留到 TTL 结束，必须让用户一眼看出
   "这条不是画面里正在违规的那辆车"，否则会造成误判。 */
.vc-stale {
  font-size: 10px; padding: 1px 6px; border-radius: 8px; white-space: nowrap;
  color: #b45309; background: rgba(245, 158, 11, .16);
  border: 1px solid rgba(245, 158, 11, .45);
}
/* "重复出现"：与"已离开画面"同形不同色，避免误读 */
.vc-repeat {
  color: #1d4ed8; background: rgba(59, 130, 246, .14);
  border-color: rgba(59, 130, 246, .42);
}
/* ★2026-10-10：抓拍证据卡片的关键信息行（违法时间由 .shot-time 承载） */
.shot-meta {
  display: block; font-size: 11px; color: var(--zt-text-muted);
  margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.scope--roi { color: var(--zt-success); background: rgba(22, 163, 74, .10);
  border-color: rgba(22, 163, 74, .35); }
.scope--frame { color: #b45309; background: rgba(245, 158, 11, .14);
  border-color: rgba(245, 158, 11, .45); font-weight: 600; }
.scope--roi_miss { color: #b91c1c; background: rgba(239, 68, 68, .12);
  border-color: rgba(239, 68, 68, .4); font-weight: 600; }

/* ★2026-10-09 由 DSH 新增：「当前生效源」条（baseline 独占一行）
   存在意义：界面上必须有一处**直接告诉用户后端在跑哪个视频**，
   否则用户无法自己校验标定到底标到哪去了（这正是上一轮的核心痛点）。 */
.src-bar {
  flex-basis: 100%; margin-top: 6px; padding-top: 6px;
  border-top: 1px dashed var(--zt-border);
  font-size: 12px; color: var(--zt-text-muted);
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
}
.src-bar.bad { color: #b91c1c; font-weight: 600; }
.src-bar .src-path {
  font-family: Consolas, Menlo, monospace; font-size: 11px;
  background: rgba(127, 127, 127, .12); padding: 1px 6px; border-radius: 4px;
  max-width: 62vw; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

/* ---------- 三栏舞台（裸眼 3D） ---------- */
.stage {
  display: grid; grid-template-columns: 1fr 2.1fr 1fr; gap: 26px;
  perspective: 1200px; perspective-origin: 50% 45%;
  align-items: start;
}
.panel {
  background: var(--zt-surface); border: 1px solid var(--zt-border);
  border-radius: var(--zt-radius-lg); overflow: hidden;
  box-shadow: var(--zt-shadow-sm);
  transition: transform .55s var(--zt-ease), box-shadow .55s var(--zt-ease);
  will-change: transform;
}
/* 两侧向中央倾斜（2026-10-03 由 DSH 加大角度：9° -> 16°，包裹感更强） */
.panel--left  { transform: rotateY(16deg) translateZ(-30px) scale(.97); transform-origin: right center; }
.panel--right { transform: rotateY(-16deg) translateZ(-30px) scale(.97); transform-origin: left center; }
.stage:hover .panel--left  { transform: rotateY(11deg) translateZ(-14px) scale(.985); }
.stage:hover .panel--right { transform: rotateY(-11deg) translateZ(-14px) scale(.985); }
.panel--center { transform: translateZ(36px); box-shadow: var(--zt-shadow-lg); }

.panel-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 12px; border-bottom: 1px solid var(--zt-border);
  background: var(--zt-surface-2);
}
.ph-title { font-size: 13px; font-weight: 600; color: var(--zt-text-secondary); }
.ph-count { font-family: var(--zt-font-mono); font-size: 15px; font-weight: 600; color: var(--zt-success); }
.ph-count.danger { color: var(--zt-danger); }
.panel-body { padding: 8px; display: flex; flex-direction: column; gap: 8px;
  max-height: 460px; overflow-y: auto; }

/* 车辆卡片 */
.vcard {
  border: 1px solid var(--zt-border); border-left-width: 3px;
  border-radius: var(--zt-radius-sm); padding: 7px 9px;
  background: var(--zt-surface); transition: all .25s var(--zt-ease);
}
.vcard--ok  { border-left-color: var(--zt-success); }
.vcard--bad { border-left-color: var(--zt-danger); background: var(--zt-danger-soft); }
.vc-top { display: flex; justify-content: space-between; align-items: baseline; gap: 6px; }
.vc-id { font-family: var(--zt-font-mono); font-weight: 700; font-size: 13px; color: var(--zt-text); }
.vc-type { font-size: 12px; color: var(--zt-text-muted); }
.vc-violation {
  margin-top: 3px; font-size: 12px; font-weight: 600; color: var(--zt-danger);
}
.vc-metrics { display: flex; gap: 8px; align-items: baseline; margin-top: 3px; }
.vc-speed { font-family: var(--zt-font-mono); font-size: 12px; color: var(--zt-text-secondary); }
.vc-speed i { font-style: normal; font-size: 10px; color: var(--zt-text-muted); margin-left: 1px; }
.vc-speed.muted { color: var(--zt-text-muted); }
.vc-dir { font-size: 11px; color: var(--zt-text-muted); }
.vc-conf { margin-left: auto; font-family: var(--zt-font-mono); font-size: 12px; color: var(--zt-danger); }
/* 真实车速 + 可信度徽标（2026-10-03 由 DSH 新增） */
.vc-speedkm { display: flex; align-items: center; gap: 6px; margin-top: 4px; }
.vc-kmh { font-family: var(--zt-font-mono); font-size: 13px; font-weight: 600; color: var(--zt-text); }
.vc-kmh i { font-style: normal; font-size: 10px; color: var(--zt-text-muted); margin-left: 1px; }
.vc-badge {
  font-size: 10px; padding: 1px 6px; border-radius: 3px; line-height: 1.6;
  border: 1px solid transparent;
}
.vc-badge.ok { background: rgba(22,163,74,.12); color: #16A34A; border-color: rgba(22,163,74,.35); }
.vc-badge.assumed { background: rgba(217,119,6,.12); color: #D97706; border-color: rgba(217,119,6,.35); }
.vc-badge.warn { background: rgba(220,38,38,.10); color: #DC2626; border-color: rgba(220,38,38,.32); }
.vc-plate {
  margin-top: 4px; display: inline-block; padding: 1px 7px; border-radius: 3px;
  background: #1D4ED8; color: #fff; font-family: var(--zt-font-mono); font-size: 11px; letter-spacing: .5px;
}
.empty { padding: 22px 0; text-align: center; color: var(--zt-text-muted); font-size: 12px; }

/* 动态迁移动画：右侧 -> 消失，左侧 -> 出现 */
.slide-left-enter-active, .slide-right-enter-active { transition: all .45s var(--zt-ease); }
.slide-left-enter-from   { opacity: 0; transform: translateX(-24px); }
.slide-right-enter-from  { opacity: 0; transform: translateX(24px); }

/* ---------- 视频区 ---------- */
.video-wrap { position: relative; background: #0B0D10; min-height: 300px; }
.video-img { display: block; width: 100%; height: auto; }
.video-mask {
  position: absolute; inset: 0; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 6px;
  color: #8A9099; font-size: 13px; background: #0B0D10;
}
.video-mask .hint { font-size: 12px; color: #5A6070; }
.video-badge {
  position: absolute; top: 8px; left: 10px; display: flex; align-items: center; gap: 5px;
  padding: 2px 8px; border-radius: 3px; background: rgba(220,38,38,.88);
  color: #fff; font-size: 11px; font-weight: 600; letter-spacing: .5px;
}
.rec-dot { width: 6px; height: 6px; border-radius: 50%; background: #fff; animation: blink 1.4s infinite; }
@keyframes blink { 0%,100% { opacity: 1 } 50% { opacity: .25 } }

/* 拉近-定格-拉远 图层（仅展示） */
/* 全屏按钮（2026-10-04 由 DSH 新增）：视频右下角，悬停淡入 */
.fs-btn {
  position: absolute; right: 10px; bottom: 10px; z-index: 6;
  width: 32px; height: 32px; border-radius: 6px; cursor: pointer;
  border: 1px solid rgba(255,255,255,.35);
  background: rgba(0,0,0,.45); color: #fff; font-size: 15px; line-height: 1;
  display: flex; align-items: center; justify-content: center;
  opacity: .55; transition: opacity .2s, background .2s, transform .2s;
}
.fs-btn:hover { opacity: 1; background: rgba(0,0,0,.72); transform: scale(1.06); }
/* 全屏时让视频铺满并保持比例 */
.video-wrap:fullscreen { background: #000; display: flex; align-items: center; justify-content: center; }
.video-wrap:fullscreen .video-img { width: 100%; height: 100%; object-fit: contain; }
.video-wrap:fullscreen .zoom-pip { width: 22%; max-width: 460px; right: 20px; bottom: 20px; }
.video-wrap:fullscreen .fs-btn { right: 20px; bottom: 20px; opacity: .8; }
.zoom-pip-cap b { font-weight: 600; }
/* 聚焦小窗（画中画）：右下角，不遮挡主画面（2026-10-04 由 DSH 重写） */
.zoom-pip {
  position: absolute; right: 12px; bottom: 12px;
  width: 30%; max-width: 320px;
  border-radius: 8px; overflow: hidden;
  border: 2px solid rgba(255, 255, 255, .75);
  box-shadow: 0 8px 28px rgba(0, 0, 0, .55);
  pointer-events: none; background: #0B0D10;
}
.zoom-pip-img { display: block; width: 100%; height: auto; }
.zoom-pip-cap {
  position: absolute; left: 0; right: 0; bottom: 0;
  padding: 2px 8px; font-size: 10px; color: #fff;
  background: linear-gradient(transparent, rgba(0, 0, 0, .72));
}
.zoom-enter-active { transition: transform .3s cubic-bezier(.2,.8,.2,1), opacity .3s ease; }
.zoom-leave-active { transition: transform .35s cubic-bezier(.4,0,.8,.2), opacity .35s ease; }
.zoom-enter-from  { transform: scale(.35); opacity: 0; }
.zoom-leave-to    { transform: scale(.35); opacity: 0; }

/* ---------- 控制台 ---------- */
.console {
  background: var(--zt-surface); border: 1px solid var(--zt-border);
  border-radius: var(--zt-radius); padding: 10px 14px;
  display: flex; flex-direction: column; gap: 8px;
}
.con-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.con-label { font-size: 12px; color: var(--zt-text-muted); min-width: 60px; }
.con-tip { font-size: 11px; color: var(--zt-text-muted); }

/* ---------- 证据抓拍墙 ---------- */
.wall {
  background: var(--zt-surface); border: 1px solid var(--zt-border);
  border-radius: var(--zt-radius); padding: 10px 14px;
}
.wall-head { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.wall-title { font-size: 13px; font-weight: 600; color: var(--zt-text); }
.wall-sub { font-size: 11px; color: var(--zt-text-muted); }
.wall-count { font-size: 11px; color: var(--zt-primary); font-weight: 600; }
.wall-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; }
.shot { position: relative; display: block; border-radius: var(--zt-radius-sm); overflow: hidden;
  border: 1px solid var(--zt-border); }
.shot img { display: block; width: 100%; height: 96px; object-fit: cover; }
.shot-cap { position: absolute; top: 4px; left: 4px; padding: 1px 6px; border-radius: 3px;
  background: rgba(220,38,38,.9); color: #fff; font-size: 10px; }
.shot-time { position: absolute; bottom: 4px; right: 4px; font-size: 10px; color: #fff;
  background: rgba(0,0,0,.55); padding: 0 4px; border-radius: 2px; }

/* ---------- 场景标注对话框（2026-10-04 由 DSH 重构）---------- */.scene-body { display: grid; grid-template-columns: 1fr 320px; gap: 14px; }
.scene-left { min-width: 0; }
.scene-toolbar { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
.st-label { font-size: 12px; color: var(--zt-text-muted); }
.scene-right { display: flex; flex-direction: column; gap: 12px; }
.sr-block {
  border: 1px solid var(--zt-border); border-radius: 6px; padding: 10px;
  background: var(--zt-surface-2, rgba(255,255,255,.02));
}
.sr-title { font-size: 13px; font-weight: 600; margin-bottom: 8px; color: var(--zt-text); }
.sr-count { color: var(--zt-brand, #1D4ED8); }
.sr-hint { font-size: 11px; font-weight: 400; color: var(--zt-text-muted); }
.zone-list { max-height: 190px; overflow-y: auto; }
.zone-item {
  display: flex; align-items: center; gap: 6px; padding: 4px 2px;
  font-size: 12px; border-bottom: 1px dashed var(--zt-border);
}
.zi-dot { width: 8px; height: 8px; border-radius: 50%; flex: 0 0 8px; }
.zi-name { flex: 1; color: var(--zt-text); }
.zi-pts { color: var(--zt-text-muted); font-size: 11px; }
.cam-form .cf-row { display: flex; align-items: center; gap: 6px; margin-bottom: 8px; }
.cf-label { font-size: 12px; color: var(--zt-text-muted); width: 52px; }
.cf-unit { font-size: 11px; color: var(--zt-text-muted); }
.cf-presets { display: flex; flex-wrap: wrap; gap: 2px; margin-top: 4px; }
.cf-note {
  margin-top: 8px; font-size: 11px; color: var(--zt-text-muted);
  padding: 6px 8px; border-radius: 4px; background: rgba(29,78,216,.08);
}
/* 各类型区域的描边配色 */
.poly--crosswalk  { stroke: #22D3EE; }
.poly--road       { stroke: #60A5FA; }
.poly--sidewalk   { stroke: #A78BFA; }
.poly--parking    { stroke: #34D399; }
.poly--no_parking { stroke: #F87171; }
.poly--draw       { stroke: #FBBF24; stroke-dasharray: 8 5; }
.dot--crosswalk   { background: #22D3EE; }
.dot--road        { background: #60A5FA; }
.dot--sidewalk    { background: #A78BFA; }
.dot--parking     { background: #34D399; }
.dot--no_parking  { background: #F87171; }
.scene-tip { font-size: 12px; color: var(--zt-text-secondary); margin-bottom: 8px; }
.scene-toolbar { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.scene-count { font-size: 12px; color: var(--zt-text-muted); }
.scene-canvas { position: relative; line-height: 0; border: 1px solid var(--zt-border);
  border-radius: var(--zt-radius-sm); overflow: hidden; }
.scene-img { width: 100%; display: block; cursor: crosshair; }
.scene-svg { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }
.poly { fill: rgba(29,78,216,.22); stroke: #1D4ED8; stroke-width: 3; }
.poly-line { fill: none; stroke: #1D4ED8; stroke-width: 3; stroke-dasharray: 8 6; }
.pt { fill: #fff; stroke: #1D4ED8; stroke-width: 3; }

@media (max-width: 1280px) {
  .stage { grid-template-columns: 1fr; perspective: none; }
  .panel--left, .panel--right, .panel--center { transform: none; }
}
</style>
