# TASK-COORD-003-R 复核报告：TrafficPlugin 车辆参数契约修复

> 执行 Agent：Trae IDE
> 日期：2026-09-25
> 性质：只读复核。未修改任何业务代码、测试、数据库、配置或启动脚本。唯一新增文件为本报告。
> 被复核对象：DSH 的 TASK-COORD-003（READY_FOR_REVIEW）

## 0. 复核结论

**ACCEPT**（建议 ChatGPT 正式验收通过）

核心判定：第三个参数为 `tracked_vehicles` 字典时，车辆能进入 `BehaviorEngine.analyze_all` 分析，并由 `TrafficEventEngine` 创建 `track_id` / `event_type` 正确的事件；新增测试以生产参数形态驱动完整路径且经敏感性验证能捕获回归。本任务证明的是**接口契约**修复，**不等于**真实视频闭环验证（后者仍未达成，见 §5）。

## 1. Git 状态与 diff 范围（步骤 2、7）

```text
$ git branch --show-current   → main
$ git log -n 5 --oneline
4a67b5a security: remove hardcoded API keys from source code (2026-09-24)
1eb430d docs: add project audit and baseline report
5bac816 chore: project audit and baseline establishment (2026-09-23)
b2747f4 Initial commit

$ git status --porcelain （仅列本任务相关项）
 M 1/api/rule_engine/plugins/traffic_plugin.py      ← DSH 授权修改（已暂存）
?? 1/tests/test_traffic_plugin_contract.py          ← DSH 授权新增

$ git diff --check    → EXIT=0（无空白错误；仅 LF→CRLF 提示，非错误）
$ git diff --cached --stat
 1/_TASK-029-M09_integration_selfcheck.json  | 16 ++++++++--------   ← 既有副作用（Trae TASK-001 运行 test_task029 所致），非本任务产物
 1/api/rule_engine/plugins/traffic_plugin.py | 10 ++++++++++          ← 与 DSH 报告 §3 声称的 +10 行一致
 2 files changed, 18 insertions(+), 8 deletions(-)
```

**diff 范围与授权一致**：目标改动仅 `traffic_plugin.py`（+10 行：docstring +6、取车分支 +3、注释 +1）与新增测试文件。未发现越界改动，未发现其他 Agent 并行修改的痕迹。

## 2. 调用链独立追踪（步骤 3）

逐层核对实参/形参（本次为独立读码追踪，非转录 DSH 报告）：

| 层 | 位置 | 代码事实 |
|---|---|---|
| 生产者 | `api/realtime_detector.py` L524-529 | `event_engine.process_frame(frame, detections or [], self.tracked_vehicles or {}, self.scene_config or {})` —— 第 3 实参 = `tracked_vehicles` **dict**，第 4 实参 = `scene_config` |
| 引擎形参 | `api/traffic_event_engine.py` L182-183 | `process_frame(self, frame, detections, tracked_vehicles, scene_context)` —— 顺序一致，无错位 |
| 引擎→插件 | 同文件 L205 | `plugin.analyze(frame, scene_context, tracked_vehicles)` —— **tracked_vehicles 落到插件第 3 形参** |
| 插件签名 | `api/rule_engine/plugins/traffic_plugin.py` L107-108 | `analyze(self, frame, scene_context, tracker)` → L124 `_extract_vehicles(scene_context, tracker)` |
| 新增路径 | 同文件 L182-184 | `if isinstance(tracker, dict) and tracker: return [v for v in tracker.values() if isinstance(v, dict) and v]` |
| 行为分析 | 同文件 L134 | `self._behavior_engine.analyze_all(vehicle, behavior_scene_config)` ↔ `api/behavior_engine.py` L477 `analyze_all(self, vehicle: Dict, scene_config=None)` —— 签名匹配 |
| 事件创建 | `traffic_event_engine.py` L212-228 | `track_id = v.vehicle_id`、`event_type = v.behavior_type` → 冷却检查 → `_extract_vehicle_info`（L235 从 tracked_vehicles dict 取车辆信息）→ `_trigger_event` 创建 `TrafficEvent(state=TRIGGERED)`（L260-276，event_id/track_id/event_type 正确） |

**生产 scene_context 不含车辆**：`realtime_detector.py` L376-384 构造的 `scene_config` 键集合为 `{traffic_light_state, stop_line_y, road_direction, speed_limit, pixel_per_meter, no_parking_zones, lane_lines}` —— 无 `vehicles` / `tracked_vehicles`。因此修复前 3 条取车路径在生产形态下全部落空（`tracker.get_all_vehicles()` 对 dict 不存在），返回 `[]` → 事件恒为 0。新增第 4 路径位于原 `return []` 之前、仅在路径 1/2/3 全部落空时生效，**原有行为零改变**（兼容用例实测确认）。

## 3. 插件 dict 兼容性检查（步骤 4）

- 路径优先级：1 `scene_context["vehicles"]` → 2 `scene_context["tracked_vehicles"]` → 3 `tracker.get_all_vehicles()` → 4 **新增** `tracker` 本身为 dict → 5 `return []`。第 4 条放在最后，对既有三条路径零影响。
- 脏数据防护：`isinstance(v, dict) and v` 过滤 str/None/int 值；空 dict 自然落到 `return []`。
- 兼容性实测：新测试的 3 个向后兼容用例（scene_context["vehicles"]、scene_context["tracked_vehicles"]、tracker 对象 `get_all_vehicles()`）全部 PASS，既有路径未回退。

## 4. 新增测试质量评估与实测结果（步骤 5、6）

### 4.1 测试是否使用生产参数形态？

**是。** `tests/test_traffic_plugin_contract.py`：

- L54-62：`PRODUCTION_SCENE_CONFIG` 与生产 `scene_config` 的 7 个键**完全一致**（对照 realtime_detector.py L376-384），且**不含任何车辆字段**；
- L169-174：核心用例以 `engine.process_frame(None, [], self.tracked_vehicles, dict(PRODUCTION_SCENE_CONFIG))` 调用 —— 第 3 实参为 `{7: vehicle_dict}`，与 realtime_detector L524-529 生产形态同构；
- L152-162：`test_production_shape_has_no_vehicle_in_scene_context` **显式自证**：断言 `'vehicles' not in scene_context`、`'tracked_vehicles' not in scene_context`、第 3 实参为 dict、被测对象是 PluginLoader 实际加载的 TrafficPlugin 类（规避了 plugin_loader.py 对 sys.modules 模块 `importlib.reload` 产生的类身份失效问题）。

### 4.2 是否经过事件引擎、真实 TrafficPlugin 和行为分析？是否绕开生产契约？

**是，且未绕开。** 证据：

- 核心用例走 `TrafficEventEngine.process_frame` → 真实 `TrafficPlugin`（PluginLoader 加载，非 mock）→ 真实 `BehaviorEngine`（纯 Python 规则，无模型/网络）；
- `test_vehicle_reaches_behavior_analysis`（L208-226）用记录型代理包裹真实 BehaviorEngine，断言 `analyze_all` 被调用、收到的车辆 `id=7`，且 **`assertIs(spy.seen_vehicles[0], self.vehicle)`** —— 对象身份与字典中同一 dict，证明"车辆进入行为分析"而非"仅被提取"；
- **确认测试没有把车辆塞入 scene_context 绕开契约**：PRODUCTION_SCENE_CONFIG 无车辆键，且 L152-162 有前置断言锁死该形态；
- 事件断言完整：`red_light` 恰好 1 个、`track_id=7`、`state=TRIGGERED`、`vehicle_info`（class_name='car'）与 `plate_number` 取自字典、`rule_judgment.behavior_type='red_light'` 且 confidence>0、`state_history[0]['new_state']=='triggered'`；
- 隔离性：不导入 realtime_detector（避免模块级 YOLO/CUDA 加载）、不导入 image_recognizer/cloud_collaborator、无摄像头/文件/网络 IO（测试耗时 0.061s，输出无 YOLO 加载行）。

### 4.3 实测命令、结果与退出码（本次独立执行）

环境：`C:\miniconda\envs\zhitong-gpu\python.exe`（Python 3.11.15，conda env；DSH 用 py -3 / Python 3.12，本次构成**双环境交叉验证**），cwd=`E:\output\1`，`-B`（不写 pycache）：

```text
$ python -B -m unittest tests.test_traffic_plugin_contract -v
Ran 10 tests in 0.061s
OK
EXITCODE=0
（运行时自述：事件类型=['red_light','speeding'] track_ids=[7]；行为分析收到车辆 id=[7]；
 冷却首次=2 第二次=0；3 条旧路径仍可用；插件直接调用返回 2 个违规）

$ python -B -m unittest tests.test_traffic_plugin_contract tests.test_traffic_event_engine \
    tests.test_circular_frame_buffer tests.test_evidence_chain \
    tests.test_cloud_collaborator_event tests.test_multi_frame_validator
Ran 46 tests in 0.027s
OK
EXITCODE=0
```

**46 项结果与 ChatGPT 核对结果一致**（46 = 既有 36 + 新增 10，无回归、无失败）。

### 4.4 敏感性抽查（本次独立执行，不修改任何文件）

用 monkeypatch 将加载器实际使用的 `TrafficPlugin._extract_vehicles` 打回修复前等价实现（仅内存 patch，进程内），以生产形态调用引擎：

```text
$ python -B -c "<内存 patch 脚本>"
patched-to-legacy: events = 0 []
SENSITIVITY_CHECK: CAUGHT_BY_TEST
EXITCODE=0
```

修复前实现下事件创建归零 → 新测试的核心断言（`assertGreaterEqual(len(events), 1)`）在该状态下必然失败。**测试是真实的契约回归测试，不是跟随实现的空断言。**

## 5. 尚未验证的事项（明确区分）

本复核证明的是**代码契约层 + 单元层**修复，以下事项仍未验证：

1. **真实视频闭环（E 级）未达成**：契约测试 ≠ 真实视频闭环验证。`traffic_events` 表仍 0 行、`api/output/event_videos/` 仍为空（TASK-COORD-002 §1.4/§1.5 实测，本轮未重跑后端，无理由预期变化）；
2. 真实视频 → YOLO → VehicleTracker 能否在真实画面产出带 `history ≥ 5` 的车辆（测试用固定构造字典替代了这一环）；
3. `_handle_event_lifecycle` 完整状态流转、事件视频提取落盘、云端 `analyze_event` 真实调用；
4. HTTP 层端到端与前端 EventCenter 展示真实事件。

## 6. 【发现的额外问题】

本轮复核**未发现新的阻塞问题**。以下为 DSH 报告 §7/§9 已记录、且经本轮独立读码确认仍然存在的事项（只记录，未修改）：

| # | 文件或模块 | 描述 | 阻塞本复核 | 建议 |
|---|---|---|---|---|
| 1 | `api/rule_engine/plugin_loader.py`（reload 行为） | `discover()` 对 sys.modules 中的插件模块 `importlib.reload()`，跨模块 isinstance 校验需从 sys.modules 取类（测试已自证规避） | 否 | 独立 TASK 评估 reload 策略 |
| 2 | `api/config.py:19` vs `api/database.py:7` | DB 路径定义矛盾，test_task029 第 7 项恒 FAIL | 否 | 独立 TASK |
| 3 | `api/realtime_detector.py:629-643` | key_frames 为占位字符串，非真实 jpg | 否 | 独立 TASK |
| 4 | `api/evidence_chain.py:139-152` | 证据链读 `traffic_light`/`stop_line`，生产写 `traffic_light_state`/`stop_line_y`，字段恒 unknown | 否 | 独立 TASK |
| 5 | `api/traffic_event_engine.py:289-296` | `_extract_trajectory` 单点轨迹（未透传 tracker history） | 否 | 独立 TASK |
| 6 | `api/routers/realtime.py:1067-1074` | review DB 分支 old_state==new_state | 否 | 独立 TASK |
| 7 | `tests/test_core.py:6` | 依赖未安装的 pytest，全量 discover 恒 1 error（本环境 conda env 亦无 pytest，与 DSH 环境结论一致） | 否 | 独立 TASK |
| 8 | `api/routers/realtime.py:808-825` | `_sync_active_events_to_db` 不写 evidence_chain 列 | 否 | 独立 TASK |

复核过程中的一条过程性说明（非问题）：本次敏感性脚本首次执行因 PowerShell here-string 剥离双引号而 NameError，改用单引号字符串后成功；未落盘任何临时脚本文件。

## 7. 验收标准逐项对照

| 验收标准 | 结论 | 证据 |
|---|---|---|
| 第 3 参数为 tracked_vehicles 字典时车辆能进入 BehaviorEngine | ✅ 是 | §2 调用链 + §4.2 assertIs 实测 |
| TrafficEventEngine 创建 track_id/event_type 正确的事件 | ✅ 是（red_light/track_id=7/state=TRIGGERED） | §2 L212-228 + §4.3 运行时自述 |
| 测试未把车辆塞入 scene_context 绕开契约 | ✅ 确认未绕开 | §4.1 前置断言 L152-162 |
| 测试结果与 ChatGPT 46 项通过一致 | ✅ 一致（46/46 OK，EXIT 0） | §4.3 |
| 契约测试 ≠ 真实视频闭环 | ✅ 已明确声明 | §5 |
| 文件/函数/命令/结果证据 | ✅ | §1-§4 |

---

【本次任务模型信息】

- 实际使用模型：GLM-5.3-Flash
- 任务复杂度：L3
- 模型选择理由：跨"检测器→引擎→插件→行为分析"四层的实参/形参契约核对 + 测试质量评估 + 双环境测试执行，属多文件交叉理解型复核，L3 适配；未为节省成本降低所需能力。
- 是否发生模型切换：否
- 切换原因：不适用。复核全程证据链清晰、测试可独立复现，未遇到能力瓶颈。
