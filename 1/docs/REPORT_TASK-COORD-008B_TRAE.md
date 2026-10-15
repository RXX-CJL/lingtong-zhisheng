# TASK-COORD-008B 只读审计报告（Trae IDE）

- 任务：实时监控与事件回放前端帧率/时间同步只读审计
- 执行日期：2026-09-26
- 执行者：Trae IDE（只读）
- 复杂度：**L3**（跨文件数据流时序分析，与预期一致）
- 最终判定：**PASS**（审计完成；未修改、未构建、未运行测试）

---

## 0. 执行声明

- 本任务**未修改任何源码、配置、数据库、视频、sidecar、测试、依赖或 Git 状态**；工作区改动与 TASK-COORD-007 结束时完全一致（HEAD `4a67b5a`，`git status` 已留证）。
- **未启动**会写入事件数据的服务，**未重跑**真实视频，**未安装依赖/构建/跑测试**。
- 除任务指定 8 个文件外，为验证根因额外只读查看了 [api/vehicle_tracker.py](file:///E:/output/1/api/vehicle_tracker.py)（追踪器更新语义）与 [api/config.py](file:///E:/output/1/api/config.py)（帧率配置），未修改。
- 量化取证全部为只读操作：cv2 读取既有事件视频、json 读取既有 sidecar、grep 既有后端日志。

## 1. 结论先行

"实时页流畅、回放框帧率低"**主因不在前端帧索引算法、请求节奏或 SVG 渲染，而在后端采集-缓冲-编码的时间契约失配**，前端仅有少量加固空间：

1. **回放慢放约 3 倍（强证据）**：循环缓冲 `add()` 不做帧率限频，视频文件源主循环全速读取；事件 clip 按墙钟 10s 窗口取出的却多达 299 帧，`save_event_video` 固定以 10fps 写出 → 视频声明时长 **29.9s**，内容真实墙钟跨度 ≤10s。
2. **sidecar 检测框在整段回放中几乎静止（强证据）**：3 个新事件 sidecar 各 299 帧，**车辆快照全程仅变化 1 次**（约在第 166→167 帧之间）；同期视频画面在持续变化（抽帧像素差 1.07~11.05/255）。画面动、框不动 → "框帧率低"的直接来源。
3. 前端 `idx = round(currentTime × fps)` 映射在当前链路下与**编码时间轴**对齐（框不与画面错位），但 sidecar 的 `time` 是 `idx/fps` 派生值，**真实采集墙钟时间戳在落盘时被丢弃**，无法事后还原真实时间轴。
4. 实时页之所以"看起来流畅"：检测框由后端画进每张 JPEG（画面/框同源同帧），且 MJPEG 每 50ms 无条件重推最新帧（含重复帧），两层刷新率不可见；回放是视频层与 SVG 层独立刷新，反差被放大。

## 2. 实时识别页数据流（AIDetect.vue）

```
摄像头/视频文件
  │ cv2 cap.read()（主循环，文件源无实时节流）
  ├─ current_frame = frame.copy()          [realtime_detector.py L310-313]
  ├─ _buffer_frame(frame)                  [L315, 每次 read 都入队，无限频]
  └─ 每 1/FRAME_RATE(=1/3s 墙钟) 触发 _process_frame_async
        └─ worker 线程(process_lock 忙则跳过): YOLO→Tracker→Behavior
             更新 last_detection_result / self.tracked_vehicles   [≈3Hz 目标]

GET /api/realtime/stream (MJPEG, multipart/x-mixed-replace)
  循环 while True:
    get_annotated_frame()  → 最新 current_frame + 最近一次检测结果，现场 _draw_detection_boxes
    JPEG(q=80) → yield; await sleep(0.05)   [推流循环上限 20Hz，无条件推帧/允许重复帧]
        ▲ routers/realtime.py L164-198；get_annotated_frame L771-796
  <img :src="streamUrl">                    [AIDetect.vue L240-247, L531]
  （前端不绘制任何检测框；无帧率逻辑）

状态数字(帧率/总帧/处理帧): setInterval 1000ms 轮询 GET /status  [AIDetect.vue L619-634]
```

- **画面如何更新**：浏览器原生 MJPEG `<img>` 解码，节奏由后端 yield 决定（≤20Hz）；帧内容更新频率 = `current_frame` 写入频率（文件源≈读取循环速度，摄像头源≈摄像头帧率）。
- **框如何更新**：框不是前端图层，而是 `get_annotated_frame()` 每次拉流时把**最近一次** `last_detection_result`（≈3Hz 更新）画在**当前最新帧**上。框与画面是同一张 JPEG，用户无法对比两层刷新率；重推同一帧时画面/框均静止但流不断，观感"一直活着"。
- 状态条 FPS 是 `fps_monitor.tick()` 的**推理**帧率（process_frame 内 L406），不是画面推流帧率。

## 3. 事件回放数据流（EventDetail.vue + /replay）

```
加载: onMounted → getEventDetail + getEventFrames + getEventReplay(一次性全量 sidecar)
  [EventDetail.vue L1149-1155；api/index.js L323]
  ├─ 有 frames[] → replayState='ready'
  └─ success=false/code=no_frame_replay_data → 'unavailable' 事件级诚实降级 [realtime.py L1046-1052]

播放: <video controls autoplay loop muted>（浏览器原生播放声明 10fps 的 H.264）
驱动（三路，均调 syncReplayFrame）:
  ① requestAnimationFrame 循环 tickReplayLoop(~60Hz)        [L664-669]
  ② timeupdate / seeked（浏览器约 4Hz）                     [L658-661]
  ③ loadedmetadata、watch(playMode)                         [L653-656, L690-697]
帧选择:
  idx = round(video.currentTime × sidecar.fps)，clamp[0, frame_count-1]   [L645-651]
同源派生（框与侧栏严格同一帧，无采样/无插值）:
  currentReplayVehicles = replayData.frames[idx].vehicles（过滤 bbox 非法项） [L600-608]
  ├─ SVG: viewBox="0 0 video_width video_height"，rect/text 用车辆 bbox     [模板 L67-92]
  └─ 右侧"当前帧车辆"列表 v-for key=track_id（点击选中与 SVG 高亮联动）     [模板 L199-217]
坐标对齐:
  updateVideoRect: scale=min(ew/vw, eh/vh)（contain）+ offsetLeft/Top 居中
  SVG 绝对定位到视频内容矩形，剔除 letterbox 黑边            [L628-642]
```

- **时间→帧映射**：线性映射 + 最近邻，最大半帧量化误差（10fps 下 50ms，编码时间轴）；seek/正常播放/loop 均成立。
- **框、侧栏、视频是否同帧**：框与侧栏严格同帧（同一 computed）；与视频画面的对应关系依赖"视频第 i 编码帧 = sidecar frames[i]"。该一一对应在写盘时成立（`written_metas` 与 writer.write 同序，[circular_frame_buffer.py L209-225]），转码为 H.264 时 ffmpeg 未指定 `-r`，继承 10fps 与帧数（cv2 实测 fps=10/299 帧）。**故不错位，但两者共同慢放**（见 R1）。
- **重复渲染**：不存在。rAF 60Hz 仅执行一次乘法/比较；idx 未跨 0.1s 边界时 computed 缓存命中，Vue 不更新 DOM；侧栏 ≤11 条且按 track_id key 复用。

## 4. API 字段与数据契约核对

| 项 | 代码事实 | 评价 |
|---|---|---|
| sidecar 字段 | version/source/event_id/video_width/video_height/fps/frame_count/generated_at/frames[{index,time,vehicles[]}] | 宽高=视频原生 960×432（实测一致） |
| frames[].time | `round(idx/fps,3)` 派生（[L308](file:///E:/output/1/api/circular_frame_buffer.py#L308)） | **非真实采集时间戳**；真实 `ts`（三元组第 1 元素）落盘时丢弃 |
| vehicles | track_id/class_name/bbox(4 浮点)/speed_px/direction；缺速度→null | 前端 bbox 非法项过滤；px/s 明确标注非 km/h |
| 降级语义 | 无视频 404；有视频无 sidecar 200+success=false+no_frame_replay_data | 前端正确走事件级降级，不伪造框 |
| 接口形态 | 全量 JSON 单次返回（299 帧，量级约百 KB） | 当前规模无性能问题；设计文档建议未来流式 |
| 请求节奏 | 进入详情加载 1 次，播放期 0 请求 | 与帧率无关，排除请求节奏因素 |
| 实时推流 | JPEG q80、sleep 0.05、无帧序号去重 | 重复推帧，见额外发现 E3 |

## 5. 量化取证（2026-09-26，对既有 3 个新事件只读测量）

| 事件 | 容器 fps | 帧数 | 声明时长 | sidecar 时间跨度 | 事件 track 出现帧 | 全局车辆快照变化次数 |
|---|---|---|---|---|---|---|
| evt_..._79_64e07b | 10.000 | 299 | 29.90s | 29.80s | 299/299 | **1 / 298** |
| evt_..._80_32d423 | 10.000 | 299 | 29.90s | 29.80s | **0/299** | **1 / 298** |
| evt_..._75_613c3b | 10.000 | 299 | 29.90s | 29.80s | **0/299** | **1 / 298** |

- 视频画面抽帧（事件 79，灰度均值差/255）：0→50 帧 11.05，50→100 帧 5.41，166→167 帧 1.07，167→218 帧 6.52，218→298 帧 7.87 —— **画面持续在变**；007 浏览器记录"帧 167 有 6 车、帧 218 有 11 车"，恰对应唯一一次快照跳变。
- TASK-007 验证脚本样本中 frame[0] 与 frame[1] 的 bbox 逐值相同，与本次统计互证。

## 6. 根因候选与证据强度

### R1 采集/缓冲/编码 fps 失配导致回放整体慢放 —— 证据强度：**强（代码+产物双证）**
- `CircularFrameBuffer.add()` 仅 append，无任何按 fps 的抽帧/节流（[circular_frame_buffer.py L106-117](file:///E:/output/1/api/circular_frame_buffer.py#L106-L117)）；deque `maxlen=duration_sec*fps=300` 约束的是**帧数**不是时长。
- 文件源主循环 `cap.read()` 后无按源 fps 的实时等待，仅以墙钟 1/3s 节流推理（[realtime_detector.py L306-322](file:///E:/output/1/api/realtime_detector.py#L306-L322)）；优化设计文档 L44 已记录"视频源曾全速读取"。
- clip 按墙钟 `[trigger-5s, trigger+5s]` 取队中**全部**帧（L158-167），实测取出 299 帧（≈满队）；写出固定 fps=10（L579）→ 时长膨胀至 29.9s（慢放 ≈3×）。
- 因 sidecar fps 与写出 fps 同源，**框不与画面错位**；但 sidecar/视频都不代表真实时间轴。

### R2 sidecar 框有效刷新率远低于画面 —— 证据强度：**强（产物质证）+ 机制成立；精确入队跨度待运行时剖析**
- 元数据在入队瞬间快照 `tracked_vehicles`（[realtime_detector.py L495-512](file:///E:/output/1/api/realtime_detector.py#L495-L512)），其只在推理 worker 完成时整体替换（≈3Hz 目标，L368）；299 帧集中于短墙钟区间入队、区间内仅完成 1~2 次推理 → 299 份快照只有 2 个取值。
- 画面帧则来自源视频不同位置（像素差证实），以 10fps 慢放连续运动 → SVG 框几乎全程静止并在中段跳变一次。
- **已排除**"引用穿透"假设：质心追踪器（当前实际启用，启动日志"ByteTrack 不可用，将使用质心追踪"）每次 update 整体新建 dict 并替换 `self.vehicles`（[vehicle_tracker.py L78-125](file:///E:/output/1/api/vehicle_tracker.py#L78-L125)），历史快照不会被原地改写。
- 未能静态确定：299 帧入队的实际墙钟跨度、该窗口内 worker 完成/跳过次数（后端历史日志未保留该中文 logger 行）——**需 DSH 运行时时间轴剖析**。

### R3 前端可加固点（均非当前瓶颈）—— 证据强度：**代码**
- 未用 `video.duration` 与 `frame_count/fps` 做一致性校验；后端修复 R1 前/后，归一化进度映射都更健壮。
- `frames[].time` 字段已下发但前端未使用（用最近邻时间查表可兼容未来非均匀时间戳 sidecar；仍禁止插值）。
- `updateVideoRect` 只在 timeupdate(~4Hz)/metadata/切模式/resize 刷新，rAF 不刷新；播放中全屏切换等布局变化有 ≤250ms 跟随延迟，常规播放无影响。
- 无采样、无节流、无重复渲染问题（详 §3）。

### 排除项
- 不是视频容器帧率问题：容器确为 10fps 且与 sidecar 一致；不是请求/网络节奏问题（播放期零请求）；不是 letterbox 坐标误差（viewBox 与原生尺寸同源，截图贴合已由 TASK-007 证实）；不是前端算法造成——前端最多呈现 10Hz 框，而数据本身只给了 2 个快照。

## 7. 待验证项

### 7.1 需 DSH 后端时间轴审计（与优化设计阶段 A 对齐）
1. 文件源 `cap.read()` 墙钟速率；299 帧入队起止墙钟跨度；deque 实际覆盖秒数。
2. clip 10s 窗口内 `process_frame` worker 完成次数、`process_lock` 跳过次数、单帧耗时 P50/P95、云端调用是否同步占用 worker。
3. 事件触发 track（75/80）在自己事件 sidecar 全程 0 出现的原因（track 生存期 vs 触发时刻 vs 快照陈旧；三事件 sidecar 去重 track 集合几乎相同，佐证快照同源）。
4. 修复方向需 DSH 决策：文件源按源 fps/墙钟节流、buffer 按时间抽帧、sidecar 写真实 PTS/墙钟时间戳（设计文档 L100 ReplayManifest）。

### 7.2 可由前端只读浏览器实测确认（不启动检测、不产生数据，仅打开既有事件详情）
1. `video.duration` ≈29.9s 与 `frame_count/fps`≈29.8s 的展示；主观确认慢放。
2. 任意 seek 后 SVG 框更新延迟（代码路径应 ≤1 帧）；框车贴合抽样。
3. 全屏进入/退出时叠加层跟随（≤250ms 预期）。
4. 侧栏全程实际跳变次数（预期 1 次）。
5. sidecar 响应体积与 `loadReplay` 耗时（Performance 面板）。

## 8. 下一阶段前端任务建议（最小边界 + 量化验收）

建议编号 **TASK-COORD-008C**（纯前端、不依赖后端 R1/R2 修复即可独立交付与验收）：

- **最小文件范围**：仅 [web-admin/src/views/EventDetail.vue](file:///E:/output/1/web-admin/src/views/EventDetail.vue)；`api/index.js` 接口不变。不改后端、sidecar、DB。
- **建议内容**：
  1. loadedmetadata 后比对 `video.duration` 与 `(frame_count-1)/fps`：偏差 >10% 时在 note 明示"回放时间轴异常：媒体时长与逐帧数据时长不一致（采集/编码节奏问题）"，并自动把帧选择切换为归一化进度 `idx=round(currentTime/duration*(count-1))`；偏差正常时保持 `t×fps`。
  2. 用 `frames[].time` 构建时间数组做最近邻选择（替代乘法 round），为未来带真实时间戳的 sidecar 预留兼容；**仍只选最近真实帧，不做 bbox 插值**。
  3. note 增加"本片段检测数据实际更新 X/Y 帧"统计（前端比对相邻帧快照），把 R2 类数据陈旧问题透明化，不伪造流畅。
  4. `updateVideoRect` 并入 rAF（仅尺寸变化时写响应式值）。
  5. 可选：DevTools 指标打点（replay 首帧、seek→框更新延迟），仅 console 输出。
- **量化验收**：
  1. 新事件抽样 5 个播放时刻，框与车身目视贴合；任意 seek 后框更新 ≤100ms；
  2. 时长偏差 >10% 时出现异常提示且映射自动切换，提示语包含两侧时长数值；
  3. 旧事件仍为事件级诚实降级（无回归）；原始证据模式零叠加；
  4. Performance 录制 30s：无 detached node 增长、rAF 回调无长任务（>50ms）；
  5. `npx vite build` 通过（实施 TASK 执行）。
- 说明：R1/R2 的真正修复（慢放消失、框恢复与采集同频）必须由 DSH 后端任务完成；008C 只负责前端时间轴健壮性、问题透明化与同步准确性，不假装修复数据。

## 9. 额外发现（仅记录，未修改）

- **E1**：事件 75/80 的 track_id 在各自 sidecar 的 299 帧中 0 出现，"本事件"红标不会出现在逐帧框上（事件级面板信息不受影响）。
- **E2**：[AIDetect.vue L647-671](file:///E:/output/1/web-admin/src/views/AIDetect.vue#L647-L671) `onBeforeUnmount` 与 `onUnmounted` 都调用 `handleStopDetection()`（重复停止请求，第二次无 catch）。
- **E3**：[/stream 生成器 L196](file:///E:/output/1/api/routers/realtime.py#L196) 每 50ms 无条件 JPEG 编码+推帧，无帧序号去重；画面静止时重复传输浪费 CPU/带宽。
- **E4**：实时页"帧率"显示的是推理 tick 频率，用户易误读为画面帧率（优化设计 L106 要求分开报告采集/预览/检测/回放 FPS）。
- **E5**：sidecar 无真实时间戳/PTS、无哈希/写入完成标记（优化设计 L100/L128 已规划 ReplayManifest）。
- **E6**：TASK-007 报告 §5"坐标对齐正确"在编码时间轴上成立，但未记录本次发现的 R1 慢放与 R2 快照静止；属本次新增发现，不否定 007 验收范围（框存在性与联动）。
- **E7**：buffer.add 保存帧引用而 current_frame 保存 copy（[L117](file:///E:/output/1/api/circular_frame_buffer.py#L117) vs [L312](file:///E:/output/1/api/realtime_detector.py#L312)）；若 OpenCV 后端复用解码缓冲，历史帧存在被污染的理论风险——**未能检查/需验证**。

## 10. 本次任务模型信息

- 实际使用模型：**GLM-5.3-Flash**（由运行环境声明；Trae IDE 子代理无法从模型服务端进一步核实实际服务模型）。
- 任务复杂度：**L3**（跨实时页/回放页/后端推流与采集链路的数据流时序审计，含产物质证），与任务书预期一致。
- 模型选择理由：本任务以跨文件代码追踪、时序推理和量化证据归纳为主，当前分配模型在上下文中已完整持有 TASK-007 实现细节，可直接对照磁盘代码核验，避免重复探索；实际执行中成功完成了代码-产物双向取证并发现报告未载的两项根因。
- 是否切换模型：**否**。环境未提供可选模型通道；审计结论均可由引用行号与只读测量复核，不依赖不可验证的推测。如指挥官要求对后端运行时时间轴做更深的并发剖析，建议由 DSH 侧具备运行时插桩能力的任务承接（详 §7.1）。
