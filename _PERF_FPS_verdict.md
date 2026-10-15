# 识别框帧率修复 · 结论报告（`_PERF_FPS_verdict.md`）

> 日期：**2026-10-06 深夜 ~ 10-09** ｜ 执行：DSH ｜ 类型：**G（根因排查）+ C（编码）+ F（验证）**
> 用户报告：**"识别框的帧率太低了，有时候都跟不上车辆"**
> 用户决策：**"按你推荐的来"** = B（稳妥调优，保留全部功能）+ C（框位置预测）
>
> **交接四件套之③**（本轮结论报告），必含"被推翻的旧结论"。

---

## 一、一句话结论

**不是算力不够，而是"框只在检测那一瞬间才动"**：

| 事实（实测） | 数值 |
|---|---|
| 模型推理（5 模型，稳态） | **139 ms/帧** → 理论上限 7.2 fps |
| GPU 显存占用 | **仅 393 MB / 8585 MB**（完全没吃满） |
| 端到端真实吞吐（原始配置） | **1.79 fps** = 单帧 **558 ms** |
| **每处理 1 帧，画面时间跳过** | **0.30 秒**（= 6 帧画面没检测） |
| → 用户感知 | **框每 0.3~0.56 秒才挪一次** |

而流接口（`get_annotated_frame`）是**每请求用"当前帧 + 缓存的检测结果"重画** ——
**画面一直是流畅的，是"框"在跳**。车连续走、框离散跳 → "跟不上车"。

**修法（两层）**：
1. **B：降低单帧成本 + 提高检测频率** —— `YOLO_IMGSZ` 1280→960、`FRAME_RATE` 3→6、
   `YOLO_MODEL_SEQUENCE` 裁掉 `license_plate`（**模型文件不存在，检出的是消防栓/盆栽等垃圾**）；
   `helmet`/`lane` **保留**（不为速度牺牲功能）
2. **C：框位置预测** —— 两次检测之间，用车辆最近轨迹位移**外推框位置**，
   让框跟着车连续滑动。**只影响显示副本，不回写追踪器**，所以违规判定/测速结论不受任何影响

**结果（三级证据）**：
- 检测吞吐 **1.79 → 2.65 fps**（框的"重定位"间隔 558 → 378 ms，**−32%**）
- **框在两次检测之间持续移动**：16 次采样（每 150 ms）里 **15 次位置变化**（`_verify_predicted_boxes.py` PASS）
- 两套前端回归 **17/17 + 15/15**，后端 **0 ERROR/Traceback**

---

## 二、A/B 实测矩阵（同一视频、同一时长，真跑出来的）

| 配置 | 吞吐 | 单帧 | **框的重定位间隔** |
|---|---|---|---|
| ① 原始（3fps / imgsz1280 / 5 模型） | 1.79 fps | 558 ms | 558 ms |
| ② 只提帧率到 6 | 1.92 fps | 522 ms | 522 ms |
| ③ ②+imgsz 960 | 2.00 fps | 500 ms | 500 ms |
| ④ ③+裁掉 license_plate、lane | 2.08 fps | 480 ms | 480 ms |
| ⑤ ④+再裁掉 helmet | 2.92 fps | 343 ms | 343 ms（**但砍掉了未戴头盔检测，未采纳**） |
| **最终采用（④ + 保留 helmet/lane + imgsz960）** | **2.65 fps** | **378 ms** | **378 ms** |

复跑：`& 'C:\miniconda\envs\zhitong-gpu\python.exe' -B E:\output\_scripts\_ab_fps_configs.py`

> ⚠ 关键认知：**单纯提 FRAME_RATE 几乎无效**（②只从 1.79 到 1.92）。
> 天花板是"单帧总成本"，而模型只占其中 139 ms —— 剩下 ~350 ms 在
> JPEG 编码、标注绘制、事件引擎、证据落库等**非模型环节**。

---

## 三、★挖出的真 bug（每个都有实测现场）

| # | Bug | 现场 | 影响 |
|---|---|---|---|
| **P1** | **`license_plate` 模型文件不存在** → 回退 COCO `yolov8s` | 一帧返回 **12 个垃圾框**：`fire hydrant`（消防栓）、`potted plant`（盆栽）、`sports ball`（运动球） | 白花 ~30 ms/帧（约 20% 模型时间），且垃圾框污染 `all_detections` 去重与规则判定 |
| **P2** | **`_predict_boxes` 把 dict 当 list 遍历** | `tracked_vehicles` 实际是 `{track_id: {...}}`（`vehicle_tracker` 返回 OrderedDict）→ 遍历出字符串键 → `v.get()` 抛异常 → **被自己的 `except` 吞掉** | **框预测功能从头到尾一次都没生效**（`ran=47` 但 `predicted_boxes` 恒空） |
| **P3** | **`_predict_boxes` 返回 list，而渲染器要 Dict** | `AnnotationRenderer.render(tracked_vehicles=...)` 的契约是 `Optional[Dict]` | 同上；两处类型错误叠加 |
| **P4** | **前端 `roiMissing` 被轮询覆盖** | `refresh()` 里 `if (sc) roiMissing.value = (sc === 'frame')`，而**未启动检测时后端固定返回 `frame`** | 每 1.5 秒把"该源尚未标注 ROI"的结论**覆盖成 false** → 按钮永远不显示"未标"警告（接口明说 roi=0，按钮却是默认态） |

> **P2/P3 的教训（重要）**：我给预测函数加了 `try/except` 兜底，本意是"宁可不动也不能画错"，
> 结果**把类型错误彻底静默了** —— 功能没生效却毫无迹象。后来是靠"加观测出口 + 计数器"
> 才定位到 `ran=47` 但 `out` 为空。
> **规则：兜底必须配可观测计数，否则等于埋雷。**

---

## 四、改了什么（文件级）

| 文件 | 改动 |
|---|---|
| `api/image_recognizer.py` | ① 模型序列支持 `YOLO_MODEL_SEQUENCE` 环境变量（不设=原样，向后兼容）；② 新增模块级 `ACTIVE_MODEL_SEQUENCE`，把**实际生效的序列**暴露出去 |
| `api/realtime_detector.py` | ① 新增 `_predict_boxes()`（**dict 进 dict 出**，只平移不改尺寸，多重上限保护）；② 在 `_draw_detection_boxes` 里对**显示副本**做预测；③ 在 `process_frame` 里记账 `_last_detect_wall_ts` 与 `_det_interval_ema`；④ `/status` 新增 `model_sequence` / `yolo_imgsz` / `box_prediction` / `predicted_boxes` / `prediction_stats` |
| `web-admin/src/views/LiveMonitor.vue` | ① 拆分 `roiMissing`（标注态）与 `lightScope`（运行态），修 P4；② 状态条徽标改用 `lightScope` |
| `start-all.bat` + `restart-backend.bat` | 把 4 个调优参数（`TUNE_IMGSZ` / `TUNE_FRAME_RATE` / `TUNE_MODEL_SEQUENCE` / `TUNE_BOX_PREDICTION`）**固化并保持两脚本一致**；想回退旧行为注释掉那 4 行即可 |
| 新增 `_scripts/_bench_models.py` | 单模型耗时基准 |
| 新增 `_scripts/_bench_steady.py` | 稳态基准（**含"首次调用是冷启动"的教训**） |
| 新增 `_scripts/_bench_stages.py` | 分段计时 |
| 新增 `_scripts/_ab_fps_configs.py` | A/B 配置对照（会自己重启后端，容错） |
| 新增 `_scripts/_probe_fps_headroom.py` | 吞吐探针 |
| 新增 `_scripts/_verify_box_motion.py` | 从流帧像素验证"画面在两次检测之间变化" |
| 新增 `_scripts/_verify_predicted_boxes.py` | **直接证明预测框在移动**（必须一边消费流一边采样） |

---

## 五、验证证据

### 5.1 框预测（三级，关键证据）

```
$ & 'C:\miniconda\envs\zhitong-gpu\python.exe' -B E:\output\_scripts\_verify_predicted_boxes.py
tuning   : frame_rate=6  yolo_imgsz=960  box_prediction=True
models   : vehicle, traffic_light, helmet, lane
sampling window: 2.8s, 16 samples @ 150ms (detection period ~378ms)

track 1      samples=16  bbox_changes=15  flagged_predicted=16
        first=(968.7, 511.9, 1282.0, 812.5)
        last =(995.3, 305.7, 1085.2, 391.0)   delta=(+26.6, -206.2) px
track 2      samples=9   bbox_changes=6   flagged_predicted=9
RESULT: PASS - predicted boxes move between detections
```
> track 1 = 行驶中的车（16 次采样里 15 次位置变化，每 150 ms 都在动）；
> track 2 = 静止车（几乎不动）—— **符合预期，说明不是"乱动"**。

### 5.2 单元级（6 个边界场景，用**正确类型** dict 测）

```
1) 刚检测完         : 不平移（pred=False）
2) 距检测 0.30s     : 平移 +10/+5 px（与轨迹位移一致）
3) 距检测 0.90s     : 被 MAX_FACTOR=3.0 封顶
4) 距检测 20s       : 被 max_shift=12%*画面 封顶（不会飞出画面）
5) 无 history/speed : 保持原框
6) 输入对象未被修改  : 关键安全性验证通过
```

### 5.3 配置可观测（`/status` 自报）

```
frame_rate     = 6
model_sequence = vehicle, traffic_light, helmet, lane
yolo_imgsz     = 960
box_prediction = True
```

### 5.4 回归

- `check.mjs`（标定面板）**17/17 PASS**
- `check2.mjs`（导航/设置/上传）**15/15 PASS**
- 后端 `backend_stderr.log`：**0 ERROR / 0 Traceback**

---

## 六、★被推翻 / 更正的东西

| # | 旧结论 | 更正 |
|---|---|---|
| **O36** | "检测帧率低是因为算力不够/GPU 吃满" | ❌ **GPU 只用了 393 MB / 8585 MB**，模型只要 139 ms。瓶颈在**单帧流水线的非模型环节**（渲染/编码/事件/落库） |
| **O37** | "把 FRAME_RATE 从 3 提到 6 就能解决" | ❌ 实测只从 1.79 → 1.92 fps。**不提单帧成本，提帧率等于空转** |
| **O38** | "我那次实测真实吞吐 1.39 fps" | ❌ 那次 `start` 返回 `False`（检测早就在跑），测的是**残留实例**；干净重测为 2.08~2.96 fps |
| **O39** | "multi_model_detect 要 1715 ms/帧" | ❌ **那是冷启动**（CUDA kernel/cudnn benchmark 首次编译）；稳态 **139 ms** |
| **O40** | "`_predict_boxes` 已通过 6 场景单元测试" | ❌ **那次测试无效** —— 我用 **list** 喂它，而真实类型是 **dict**。测试通过只说明"喂错类型时它不崩"（异常被吞），不代表功能可用（P2/P3） |
| **O41** | "`license_plate` 只是没接，无副作用" | ❌ 它**静默回退 COCO**，每帧产出 12 个垃圾框（消防栓/盆栽/运动球）并污染检测集合 |
| **O42** | "标定按钮不显示未标 = `loadRoiState` 没跑" | ❌ 它在跑、结果也对，是 `refresh()` 每 1.5 秒**把结果覆盖掉**（P4） |
| **O43** | "浏览器刷新卡住是页面/前端问题" | ⚠️ 部分：用户已自行确认 **"关掉页面再打开就不卡、用浏览器刷新才卡"** → 指向**刷新时旧 MJPEG 长连接未干净释放**（**尚未修**，见 §七） |

---

## 七、仍未解决 / 风险

1. **🟠 浏览器刷新卡（用户已定位现象，未修）**：
   "关掉页面再打开就正常，用浏览器自带刷新却容易卡住" —— 典型症状是
   **刷新时旧的 MJPEG 长连接没有被干净关闭**，连接被占住（浏览器对同源连接数有上限）。
   修法方向：流接口加**客户端断开检测**（`await request.is_disconnected()`）+ **连接数上限**，
   并在前端 `beforeunload` 主动 `img.src=''` 释放。**下一轮第一件事。**
2. **🟠 单帧 ~350 ms 的非模型成本尚未拆解**：本次只证明了"模型不是瓶颈"，
   JPEG 编码 / 标注绘制 / 事件引擎 / 证据落库各占多少**还没逐项量化**。
   继续优化检测帧率必须从这里下手（模型已无可榨）。
3. **🟡 框预测的固有误差**：直线外推，转弯/急刹时会偏。已用
   `MAX_FACTOR=3.0` + `max_shift=12%` 双重封顶。一键关闭：`BOX_PREDICTION=0`。
4. **🟡 "未戴头盔"仍保留**（按用户要求不牺牲功能）；若未来愿意放弃，
   配置 ⑤ 可把框的重定位间隔压到 **343 ms**。
5. **🟡 历史事件视频**：4855 个旧事件视频仍是 2× 速度（用户决定只重封 `evt_11200_18_60c808`）。

---

## 八、交接自检（协议 §9.4）

- [x] 只读 3 个文件能知道项目有什么 → `_PROJECT_MAP.md` 已补 T68~T71 与本轮条目
- [x] 能知道上一步做到哪、下一步做什么 → `_SESSION_HANDOFF.md` 已更新
- [x] 能知道哪些结论被推翻 → 本文件 §六（O36~O43）
- [x] 路径都真实存在 → 逐个核对（含 6 个新脚本）
- [x] 未验证项如实标注 → §七；"我复现不出浏览器卡死"也如实写了
