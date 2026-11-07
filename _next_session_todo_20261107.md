# 下轮待办（2026-11-07 P0 跑通后更新）

> 本轮结论：[`_p0_carla_direct_verdict_20261107.md`](_p0_carla_direct_verdict_20261107.md)
> 上一轮：[`_next_session_todo_20261106.md`](_next_session_todo_20261106.md)（其 §1.3 三步已全部 PASS）

---

## 零、现在什么状态

| 项 | 状态 |
|---|---|
| **P0 CARLA 直连** | ✅ **成立**，三步验收全 PASS（见 verdict §一） |
| 挖出并修掉 4 个 bug | ✅ 已修 + 3 个 `.bak_20261107_carla` 可回滚 |
| 后端 8001（Python 3.11） | **在跑，未动**（PID 16400） |
| CARLA | **在跑**（PID 17744，High 画质，端口 2000，GPU 余 2420 MiB） |
| 8002 验证实例（Python 3.12） | 已关闭 |
| 前端 5173 | 未启动 |

---

## 一、已拍板：方案 A —— 后端整体迁 Python 3.12

> **用户 2026-11-07 决定**：「A吧，根除问题不算绕远路」
> 否掉的 B（IPC）与 C（双进程）都不再考虑。

### 为什么不是绕远路

`carla` 只有 cp312 wheel，这是**硬约束**不是选择。让 8001 停在 3.11 意味着：

- CARLA 永远只能跑在旁挂实例（8002）上 → 前端连 8001 永远看不到 CARLA 画面
- 或者写一层 IPC 把帧搬过去 → 多一个故障点，且调试时要跨两个进程看日志

迁版本是**一次性成本**，IPC 是**永久成本**。

### 迁移步骤（下轮照做）

| # | 步骤 | 判据 |
|---|---|---|
| 0 | **记基线**：8001 还在 3.11 时，先跑 §「迁移必须验的四项」里的第 0 项，把四项当前值写进一个 `_tmp/py312_baseline.json` | 文件存在且四项都有值 |
| 1 | **先备份** `restart-backend.bat` / `start-all.bat`（`.bak_20261107_py312`） | 文件存在 |
| 2 | 把两个 bat 里的 `PYEXE` 搜索顺序改成 **Python312 优先** | grep 到 `Python312` 在 `zhitong-gpu` 之前 |
| 3 | 重启后端，看启动日志 | 日志里出现 `carla = ...Python312...carla\__init__.py` |
| 4 | **配置三字段核对** `GET /api/realtime/status` | `model_sequence`/`yolo_imgsz=960`/`frame_rate=6` 三项不变 |
| 5 | **重跑基线四项，逐项对照 `py312_baseline.json`** | 数值一致或差异有合理解释；`carla` 能 import |
| 6 | 若回归失败 → 回滚两个 bat，改用 B 方案 | 8001 恢复到 3.11 且能跑 |

### 迁移必须验的四项（3.12 上未验过）

> ⚠ **一条硬约束（2026-11-07 补，来自本轮的实打实教训）**：
> **不许拿本轮在 8002 上跑通的结果，当成 8001 迁移成功的证据。**
>
> 这跟 `_next_session_todo` 里 CodeBuddy 11128 那条教训是同一个病：
> 「改完要用**新的真实请求**验证，不是拿旧样本重放」。
>
> 本轮的实例：我用 `GET /status` 判断"事件有没有落库"，查到 0 条，差点判成落库功能坏了。
> 实际是 `GET /events` 才触发 `_sync_active_events_to_db()` —— **尺子量错了对象**。
> 8002 是 Python 3.12 + 新起的进程 + 干净的 CARLA；8001 迁移后是另一套环境，
> **必须重跑同一串请求，拿新的响应数字说话。** 迁移前后各记一次，逐项对照。

| # | 验什么 | 怎么验 | 为什么重要 |
|---|---|---|---|
| **0** | **迁移前的基线快照**（先做这个） | 8001 还在 3.11 时，先把下面 4 项的**当前值**记下来：OCR 输出、4 模型检出数、视频源 `processed_frames`、两个自校验脚本的 PASS 数 | **没有基线就没有对照**。迁移后只能说"跑起来了"，不能说"没变坏" |
| **1** | **PaddleOCR 精度** | 拿一张已知车牌图跑 `paddleocr`，比对 3.11 上的结果 | 3.12 装的是 `paddleocr 3.7.0` / `paddlepaddle 3.3.1`，**与 3.11 不是同版本**，模型行为可能不同 |
| **2** | **车道线/头盔模型** | `YOLO_MODEL_SEQUENCE='vehicle,traffic_light,helmet,lane'` 跑一帧，看 4 个模型都加载 | 3.12 的 `ultralytics 8.4.35` vs 3.11 的 `8.4.103`，**版本倒退**，API 可能不兼容 |
| **3** | **视频源回归** | 用演示主力 `_dual_cam_demo/dual_cam_demo_h264.mp4` 跑一遍 | 这条链路是本轮没碰的，必须确认没被连带改坏 |
| **4** | **原有自校验脚本** | `_scripts/_verify_hotreload_and_filter.py`（25 项）+ `_verify_fixes_e2e.py` | 项目既有的回归基线，不能跳过 |

### 已知的版本差异（下轮先知道，少踩坑）

| 包 | 3.11（zhitong-gpu） | 3.12（Python312） | 风险 |
|---|---|---|---|
| `ultralytics` | 8.4.103 | **8.4.35**（倒退） | ⚠️ API 差异 |
| `fastapi` | 0.139.0 | 0.136.3（倒退） | 低 |
| `uvicorn` | 0.51.0 | 0.49.0（倒退） | 低 |
| `numpy` | 2.0.1 | 2.3.5（新） | 低 |
| `opencv-python` | 5.0.0.93 | 4.13.0.92（倒退）+ contrib 4.10.0.84 | ⚠️ **5.x→4.x 是大版本倒退**，`cv2` API 可能有差异 |
| `paddleocr` | ❌ 无 | 3.7.0 | 3.11 上根本没有，等于新增 |
| `torch` | 2.5.1 | 2.5.0+cu121 | 低 |
| `carla` | ❌ 无 | 0.9.16 | 本轮的动因 |

**最该盯的两个**：`ultralytics`（8.4.103→8.4.35）和 `opencv`（5.x→4.x）。**都是倒退，不是升级。**
如果回归在这两个上挂了，正确做法是**在 3.12 里把这两个包升到与 3.11 一致的版本**，而不是改项目代码去迁就旧 API。

### 回滚

```bash
cd E:/output/1
cp restart-backend.bat.bak_20261107_py312 restart-backend.bat
cp start-all.bat.bak_20261107_py312 start-all.bat
# 然后跑 restart-backend.bat
```

---

## 二、P1：把 P0 从"能跑"做到"能演示"（按价值排序）

> ⚠ **顺序调整**：下面的 1-4 项必须**排在 §一 的 3.12 迁移之后**做。
> 理由：迁移会改 bat 和后端环境，先做这些再迁移等于要验两遍。

### 1. 事件落库改成事件驱动（**真 bug，优先**）

**现状**：`_sync_active_events_to_db()` 只在 `GET /events` 列表查询时被调用（`routers/realtime.py:1359`）。
**后果**：不查列表就不写库 —— **实时性依赖调用方**。本轮我就是因为只查了 `/status`，误判成"事件没落库"。
**修法**：事件状态变化时（`triggered` / `confirmed` / `rejected`）直接写库，列表查询只做兜底。

**判据**：造违规后**不调任何查询接口**，直接查库应该有新记录。

### 2. 让 `spawn_red_light_violator` 真的冲红灯（半天）

**现状**：只是"关 autopilot + 踩油门"，车的朝向由 spawn point 的 yaw 决定，**不一定朝着红灯**。
**本轮实测结果**：3 辆车判出的是 `running_yellow` 和 `speeding`，**没有 `red_light`**。
**修法**（`_next_session_todo` §2.3 已记）：
- `ignore_lights_percentage(100)` **本机无效** → 必须关 autopilot + `apply_control` 手动驱动
- 按停止线地理坐标找灯（CARLA 重启后灯 Actor ID 会变）
- 车要 spawn 在「朝着红灯」的车道上，而不是随机点

**判据**：`event_type` 出现 `red_light`，且 `traffic_light_state='red'`。

### 3. CARLA 相机标定重做（1 天）

**现状**：检测用 1280×720，现有标定是 1920×1080。
**影响**：反投影、测速全错（同步 T88「源不一致是标定失效的头号原因」）。
**机位已确认可用**：`(-15.720, -63.145, 5.732)` pitch `-23.445` yaw `179.536`。
**做什么**：在这个机位 + 1280×720 上重新标 `stop_line_y` / `crosswalk_zones` / `lane_lines` / `pixel_per_meter`。

### 4. warmup 预热（1 小时）

**实测**：单模型首次 **9947ms**。4 模型叠加会更长。
**后果**：演示时前 10-40 秒 `processed_frames` 几乎不动，画面空着。
**修法**：启动检测前先拿一帧假图跑一遍各模型，或启动时立刻预热并显示"预热中"。

---

## 三、P2：零硬件二维俯视孪生（原 §二，现在更简单了）

**为什么更简单**：CARLA 里车辆世界坐标**精确已知**（`GET /carla/actors` 已实测返回真实坐标），
可以直接做**真值对照**，不需要反投影。

**判据**（原样保留）：
1. 同一辆车连续帧俯视位置随画面移动
2. 移动方向与 bbox 移动方向一致
3. 俯视路径长度与 `speed_calibration` 距离吻合（误差 < 1m）
4. 有 `.bak_20261107_*` 可回滚

---

## 四、P3 / P4 / P5（原封不动，见上一轮文件）

- **P3 云台演示**（¥0 软件模拟，`api/ptz_controller.py` 已有 `SimulatedPTZController`）
- **P4 设施归因**（需先补素材）
- **P5 欠账**：B3 申诉闭环 0 条、B4 逆行车道级方向、车牌识别用 fallback 模型

---

## 五、本轮的环境事实（下轮直接用，别重学）

### CARLA 启动命令（已验证稳定）

```bash
cd "E:/output/1/carla/CARLA_0.9.16/CarlaUE4/Binaries/Win64"
./CarlaUE4-Win64-Shipping.exe -carla-rpc-port=2000 -quality-level=High -nosound \
  -windowed -ResX=1280 -ResY=720 -benchmark -fps=20 &
```

- ❌ **`-quality-level=Epic` 会崩**（约 10-15 分钟后进程消失，端口无响应）
- High 启动后 GPU 余量约 500 MiB；Epic 只剩 344 MiB

### 8002 验证实例（Python 3.12）

```bash
cd E:/output/_tmp
YOLO_MODEL_SEQUENCE='vehicle,traffic_light' \
C:/Users/ROG/AppData/Local/Programs/Python/Python312/python.exe -u run_8002_py312.py &
```

### 模型性能实测

| 场景 | 首次 | 稳态 |
|---|---|---|
| 单模型 | 9947 ms | 128-135 ms |
| 4 模型序列 | — | ≈520 ms（1.9 fps） |
| **2 模型序列**（演示推荐） | — | **实测 2.2-2.95 fps** |

### 环境变量（本轮新增，都有缺省）

```
CARLA_CAM_X / Y / Z / PITCH / YAW / ROLL   相机机位（缺省=工坊机位）
CARLA_DEMO_WIDTH / HEIGHT / FOV            相机分辨率（缺省 1280x720 fov90）
CARLA_TRAFFIC_N                            切源时自动生成车数（缺省 20，0=不生成）
YOLO_MODEL_SEQUENCE                        模型序列（演示建议 vehicle,traffic_light）
```

---

## 六、可复跑的证据脚本（都在 `E:/output/_tmp/`）

| 脚本 | 干什么 |
|---|---|
| `carla_probe.py` | 只验证连接 + 地图信息 |
| `carla_step1.py` | 完整跑 CarlaSource 全流程（含 violator） |
| `carla_diag_violator.py` | **BUG-2 的对照实验**（空场 vs 先 spawn vs 车开走后） |
| `test_cam_positions.py` | **4 个候选机位截图对比** |
| `test_timing_real.py` | **warmup 与稳态耗时实测** |
| `run_8002_py312.py` | 起 8002 验证实例 |
| `cleanup_carla.py` | 清场 + 恢复异步模式 |
| `ping_carla.py` | 10 秒超时探活 |

截图证据：`E:/output/_tmp/cam_shots/`（A_handbook/final/probe_0/yolo_2 等）

---

## 七、新对话开场白

```
继续智瞳灵声项目。先读这两个文件：
E:\output\_p0_carla_direct_verdict_20261107.md   ← 上轮 P0 结论（已跑通，含 4 个 bug 修复）
E:\output\_next_session_todo_20261107.md          ← 本轮待办

当前状态：
- P0（CARLA 直连实时检测）已跑通，三步验收全 PASS，+2 条事件落库、灯态 yellow、轨迹 4-5 点
- 挖出并修掉 4 个 bug，有 .bak_20261107_carla × 3 可回滚
- 后端 8001（Python 3.11）在跑未动；CARLA（High 画质）在跑；8002 已关
- 关键约束：carla 模块只有 cp312，装不进 8001 用的 Python 3.11

已拍板：方案 A —— 后端整体迁 Python 3.12（用户原话「根除问题不算绕远路」）

本轮第一件事：做待办 §一 的 3.12 迁移。步骤、四个必验项、版本差异风险、回滚命令都在里面。
⚠ 迁移前先备份 restart-backend.bat 和 start-all.bat
⚠ 最该盯的两个包：ultralytics 8.4.103→8.4.35、opencv 5.x→4.x，都是倒退
⚠ 若这两个上挂了，正确做法是在 3.12 里把包升到与 3.11 一致，而不是改代码迁就旧 API

迁移验完 PASS 后，再按 §二 顺序：事件落库改事件驱动 → 让违规车真冲红灯 → 相机标定重做 → warmup 预热
```

---
---

# ⚠ 2026-11-07 02:00 增补：§一 已完成，以下是**新的**状态与本轮发现

> 详细取证：[`_py312_migration_verdict_20261107.md`](_py312_migration_verdict_20261107.md)
> **上面 §零~§一 的内容已过期**（那是迁移前的计划），以本节为准。

## A. 现在的真实状态

| 项 | 状态 |
|---|---|
| **Python 3.12 迁移** | ✅ **完成**，8001 跑在 3.12.10（PID 4724） |
| **CARLA 直连** | ✅ 已在 **8001 正式端口**跑通（`processed_frames=838` / `avg_fps=2.05`） |
| **PaddleOCR** | ✅ **跑通**（实测识别 0.9992） |
| **hyperlpr3** | ✅ 已补装 0.1.3 |
| 后端 8001 | 在跑（3.12，PID 4724） |
| 前端 5173 | 在跑（PID 11296） |
| CARLA | ⚠️ **进程已消失（非本轮停止，原因未查）**，开工第一件事是重新拉起 |

## B. 本轮修掉的 4 个问题

| # | 问题 | 性质 | 位置 |
|---|---|---|---|
| 1 | `hyperlpr3` 在 3.12 缺失 → 车牌识别静默失效 | **真回归** | 已 `pip install hyperlpr3==0.1.3` |
| 2 | `ocr(cls=True)`，PaddleOCR 3.7 不认 → 永远返空 | **真 bug** | `license_plate_recognizer.py:230` → 改 `predict()` |
| 3 | paddlex 缓存 4/5 模型不可读（连 Get-Acl 都拒） | 环境 | 用 `PADDLE_PDX_CACHE_HOME=F:\AI\paddlex_cache` 绕过 |
| 4 | paddlepaddle 3.3.1 oneDNN 崩溃 | 环境 | 用 `PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT=False` 绕过 |

## C. 被推翻的结论（3 条，别再信旧的）

1. **"opencv 5.x→4.x 是倒退"** → **反了**。4.10 修好了 5.0 上的车道线崩溃：
   ```
   3.12 (cv2 4.10):  LaneDetector.detect -> 18 lines  OK
   3.11 (cv2 5.0) :  崩溃 cannot unpack non-iterable numpy.int32 -> 0 lines
   ```
   `cv2.HoughLinesP` 形状在 5.x 从 `(N,1,4)` 变 `(N,4)`，项目代码按旧形状写。
   **3.11（旧 8001）的车道线检测一直是坏的，被 try/except 吞了。**
2. **"3.11 上有 PaddleOCR 可对比"** → 3.11 **从来没装过**。
3. **"`.paddlex` 是 CodexSandboxUsers 的拒绝型 ACE"** → 那条是 **Allow ReadAndExecute**，
   顶层有 FullControl。真实形态是四个子目录关闭了继承且读不到，**连诊断都做不到**。

## D. 迁移回归：新增回归 = 0

```
unittest 11 个模块：3.11 与 3.12 同结果（7 PASS / 2 迁移前就坏 / 2 裸函数被 unittest 抓不到）
裸函数 2 个（按真实 runner 跑）：test_multi_frame_validator 14/14 PASS、test_task029_integration 7/7 PASS
```

⚠️ 待办原 §一 点名的 `_scripts/_verify_hotreload_and_filter.py` 与 `_verify_fixes_e2e.py` **都不存在**（全盘 find 零命中）。

## E. 新增的三个环境变量（两个 bat 已注入）

```
PADDLE_PDX_CACHE_HOME=F:\AI\paddlex_cache
PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT=False
PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True
```

## F. 完整回滚

```bash
cd E:/output/1
cp restart-backend.bat.bak_20261107_py312 restart-backend.bat
cp start-all.bat.bak_20261107_py312 start-all.bat
cp api/license_plate_recognizer.py.bak_20261107_ocr api/license_plate_recognizer.py
# 然后跑 restart-backend.bat（回到 3.11）
```

## G. 下一轮顺序（§二 原顺序不变）

0. **先把 CARLA 拉起来**（见 §五 启动命令）
1. 事件落库改事件驱动
2. 让违规车真冲红灯
3. 相机标定重做（1280×720）
4. warmup 预热

## H. `tracked_vehicle_count=0` 的结论：不是 bug

我查了三次，**两次假设被自己推翻**：

| # | 假设 | 结果 |
|---|---|---|
| 1 | `vehicle_tracker.py:137` 用墙钟减视频时间 → 每帧清空 | ❌ 三组对照都 `[1,1,1,1,1]` |
| 2 | 应该测 ByteTrack 分支 | ❌ A/B/C 三组都 `[1,1,1,1,1,1]` |
| 3 | **画面里确实没车** | ✅ **成立** |

证据：截图只见 2-3 辆车；YOLO 日志 `1 person, 1 bus, 2 traffic lights`。

**待查**：`/carla/spawn` 生成 26 个 actor 后 25 秒只剩 2 个，**无销毁日志**（CARLA 侧行为，未深挖）。

## I. 真实 CARLA 路由名（之前写的都不对）

| 实际路由 | 说明 |
|---|---|
| `GET  /api/realtime/carla/status` | 连接状态 |
| `POST /api/realtime/carla/connect` | 连接 |
| `POST /api/realtime/carla/spawn` | `{"vehicles":15}` → 14 车 + 10 行人 |
| `POST /api/realtime/carla/next-scene` | `{"scene":"violation"}` |
| `GET  /api/realtime/carla/actors` | 车辆/行人/红绿灯 + 真实世界坐标 |

## J. 两个 Python 环境的真实差异（实测）

| 包 | 3.11 | 3.12 | 影响 |
|---|---|---|---|
| `carla` | ❌ 无 | ✅ 0.9.16 | 迁移动因 |
| `ultralytics` | 8.4.103 | 8.4.35 | ✅ 检测结果逐类一致 |
| `opencv` | 5.0.0 | **4.10.0** | ✅ 4.10 更好（5.0 上 LaneDetector 崩） |
| `hyperlpr3` | 0.1.3 | 0.1.3（本轮补装） | ⚠️ 曾缺失 |
| `paddleocr` | ❌ 无 | 3.7.0 | 3.12 新增 |

## K. 本轮新增的证据脚本

| 脚本 | 干什么 |
|---|---|
| `run_tests_312.py` | 回归基线（11 个 unittest 模块，带真实 exit code） |
| `diff_tests.py` | 两解释器回归对照（判定是否新增回归） |
| `track_bug_probe.py` / `track_bug_probe2.py` | 追踪器三次假设的对照实验（全部推翻） |
| `ocr_redirect_test.py` | OCR 缓存重定向 + 关 mkldnn 验证 |
| `attr_probe.mjs` | 模型目录属性/重解析点探测 |

ACL 报告：`E:/output/_tmp/acl_report_20261107/`
