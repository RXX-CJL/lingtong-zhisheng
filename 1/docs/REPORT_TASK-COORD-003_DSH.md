# TASK-COORD-003 报告：TrafficPlugin ↔ TrafficEventEngine 车辆参数契约修复 + 生产形态回归测试

```text
任务编号：TASK-COORD-003
执行 Agent：DSH
状态：READY_FOR_REVIEW
复杂度：L3
读取过的基线/文件：
  E:\output\1\PROJECT_BASELINE.md
  E:\output\1\PROJECT_AUDIT_AND_BASELINE_REPORT.md
  E:\output\1\docs\AI_COORDINATION_PROTOCOL.md
  E:\output\1\docs\REPORT_TASK-COORD-001_DSH.md
  E:\output\1\docs\REPORT_TASK-COORD-002_TRAE.md
  E:\output\1\api\realtime_detector.py            （只读）
  E:\output\1\api\traffic_event_engine.py         （只读）
  E:\output\1\api\rule_engine\plugins\traffic_plugin.py
  E:\output\1\api\rule_engine\base_plugin.py
  E:\output\1\api\rule_engine\plugin_loader.py
  E:\output\1\api\behavior_engine.py              （只读，用于构造确定性违规）
  E:\output\1\api\vehicle_tracker.py              （只读，用于确认车辆字典结构）
  E:\output\1\tests\test_traffic_event_engine.py
实际改动：
  修改 1 个文件：1/api/rule_engine/plugins/traffic_plugin.py（+10 行，见 §3）
  新增 1 个文件：1/tests/test_traffic_plugin_contract.py（10 个用例）
  未修改 realtime_detector.py / traffic_event_engine.py / 数据库 / 路由 / 配置 / 启动脚本
验证命令及结果：见 §5（新测试 10/10 OK 退出码 0；相关测试 46/46 OK 退出码 0；全量 discover 47 Ran / 1 error 为改动前既有）
证据文件或日志：§5 命令输出；未新增证据文件
风险与阻塞：见 §7
建议的下一步：见 §8
```

---

## 0. 交付摘要

| 项 | 结论 |
|---|---|
| 断点是否修复 | ✅ 已修复，且**只改插件一处**（`_extract_vehicles` 增加第 4 条取车路径） |
| 生产形态是否创建事件 | ✅ 实测 `red_light`(track_id=7) + `speeding`(track_id=7) 两个 `TrafficEvent`，state=`TRIGGERED` |
| 车辆是否进入行为分析 | ✅ 记录型代理实测 `BehaviorEngine.analyze_all` 收到 id=7 的车辆对象（且对象身份与字典中同一 dict） |
| 测试是否真能捕获该回归 | ✅ 把 `_extract_vehicles` 打回修复前实现后，2 个核心用例 **FAIL**（§5.C 敏感性验证） |
| **测试验证的是"接口契约"** | ✅ 已由 10 个用例证明 |
| **真实视频闭环是否已验证** | ❌ **仍未验证**（无真实视频输入、无 mp4 落盘、`traffic_events` 仍 0 行）——见 §6 |
| 改动范围是否越界 | ✅ 仅授权文件；`git diff --stat` 见 §4 |

---

## 1. 开始前的工作区状态记录（步骤 1-2）

```text
$ git branch -vv
+ feat-empty-input-99G4ey b2747f4 (C:/Users/ROG/.trae-cn/worktrees/output/feat-empty-input-99G4ey)
* main                    4a67b5a [origin/main] security: remove hardcoded API keys ...

$ git log -n 5 --oneline
4a67b5a security: remove hardcoded API keys from source code (2026-09-24)
1eb430d docs: add project audit and baseline report
5bac816 chore: project audit and baseline establishment (2026-09-23)
b2747f4 Initial commit

$ git status --porcelain   （任务开始时）
 M 1/_TASK-029-M09_integration_selfcheck.json
?? 1/docs/AI_COORDINATION_PROTOCOL.md
?? 1/docs/PROMPT_DSH_TASK-COORD-001.md
?? 1/docs/PROMPT_TRAE_TASK-COORD-002.md
?? 1/docs/REPORT_TASK-COORD-001_DSH.md
?? 1/docs/REPORT_TASK-COORD-002_TRAE.md
?? dsh-compaction-verify/  dsh-workshop-backup/  dsh-workshop-patch/
?? dsh-workshop-src-recovered/  dsh/  skill-detail.mjs  skill-scan.mjs
```

**目标文件洁净性核查（关键）**：

```text
$ git status --porcelain -- 1/api/rule_engine/plugins/traffic_plugin.py \
     1/api/rule_engine/base_plugin.py 1/api/traffic_event_engine.py \
     1/api/realtime_detector.py 1/tests/
（无输出 = 全部未被修改，可安全动手）
```

**关于唯一的已跟踪修改文件 `1/_TASK-029-M09_integration_selfcheck.json`**：
- 其 `LastWriteTime = 2026/9/25 15:42:18`，早于本任务开始时间；
- `REPORT_TASK-COORD-002_TRAE.md` §1.9 已明确声明该副作用来自 Trae 运行 `tests/test_task029_integration.py`（脚本内置写文件行为）；
- 本任务**未运行该脚本的 `main()`**，全程未触碰该文件：任务结束后其 mtime 仍为 `2026/9/25 15:42:18`、size 仍为 `2095`（§4 有复核）。
- 按"必须保留上一轮遗留未提交内容"的要求，**原样保留，未覆盖、未还原、未清理**。

**未发现其他执行者并行修改目标文件**，无 P-RED 冲突，继续执行。

---

## 2. 修改前后的调用契约说明

### 2.1 三方契约（代码事实）

| 角色 | 位置 | 形态 |
|---|---|---|
| 抽象契约定义 | `api/rule_engine/base_plugin.py:72-84` | `analyze(self, frame, scene_context, tracker)` → `List[ViolationEvent]` |
| 生产者（检测器） | `api/realtime_detector.py:515-529` | `engine.process_frame(frame, detections or [], self.tracked_vehicles or {}, self.scene_config or {})` |
| 消费者（引擎） | `api/traffic_event_engine.py:183-206` | `process_frame(self, frame, detections, tracked_vehicles, scene_context)` → `plugin.analyze(frame, scene_context, tracked_vehicles)` |
| 实现（插件） | `api/rule_engine/plugins/traffic_plugin.py:107` | `analyze(self, frame, scene_context, tracker)` |

因此实际落到插件第 3 形参 `tracker` 上的，是 **`dict[int, vehicle_dict]`**（`VehicleTracker.update` 的返回值）；而 `scene_context` 是检测器的 `scene_config`，键集合为
`{traffic_light_state, stop_line_y, road_direction, speed_limit, pixel_per_meter, no_parking_zones, lane_lines}`（`realtime_detector.py:376-384`）——**不含任何车辆字段**。

### 2.2 修改前（断裂行为）

`TrafficPlugin._extract_vehicles(scene_context, tracker)` 只认三条路径：

```python
1. scene_context["vehicles"]        # list[dict]
2. scene_context["tracked_vehicles"] # dict[id -> dict]
3. tracker.get_all_vehicles()        # 需要 tracker 是"对象"
return []
```

生产形态（第 3 实参是 dict）下：路径 1/2 因 `scene_config` 无该键而落空；路径 3 因 `hasattr(dict, "get_all_vehicles") is False` 而落空 → **返回 `[]`** → `analyze` 返回 `[]` → 引擎 `new_events` 恒为 `[]`。

影响链（TASK-COORD-001 §3.3 已实证，本次复核一致）：
`tracked_vehicles dict` → `_extract_vehicles=[]` → `BehaviorEngine.analyze_all` 从不执行 → 无 `ViolationEvent` → 引擎不创建事件 → `active_events` 恒空 → `_sync_active_events_to_db()` 无数据可写 → `event_videos/` 无 mp4 → 前端事件中心恒空。

### 2.3 修改后（契约补齐）

只在插件侧补齐第 4 条路径（**下游三处代码均无需改动**）：

```python
        # 生产形态：tracker 实参就是 {track_id: vehicle_dict}
        if isinstance(tracker, dict) and tracker:
            return [v for v in tracker.values() if isinstance(v, dict) and v]
```

- 位置：`api/rule_engine/plugins/traffic_plugin.py`，`_extract_vehicles` 内，原 `return []` 之前；
- 同时更新该方法 docstring 的优先级列表（新增第 4 条）并说明其对应生产调用形态；
- 非 dict 值（`str`/`None`/`int`）被过滤，避免脏数据进入行为分析；
- 原有 1/2/3 三条路径与优先级**完全不变**（向后兼容，§5.A 已覆盖）。

### 2.4 为什么不改 `realtime_detector.py` / `traffic_event_engine.py`

任务要求"除非查证后确认仅修改插件无法满足既有接口契约"。查证结论：**仅改插件即可满足**。

- `base_plugin.py:72-84` 的形参名就叫 `tracker`，语义是"车辆/目标追踪器实例"；插件把"字典形态的 tracked_vehicles"也接受为自己的 tracker 入参，属于**插件侧扩大入参兼容性**，不改变任何人已声明的签名；
- 引擎 `plugin.analyze(frame, scene_context, tracked_vehicles)` 的传参顺序与 `base_plugin` 定义一致，无错位；
- 检测器 `process_frame(...)` 的实参顺序与引擎形参顺序一致，无错位；
- 因此改动引擎或检测器属于**不必要的核心链路改动**，风险更高，已按最小变更原则排除。

---

## 3. 修改文件及关键代码位置

| 文件 | 类型 | 位置 | 内容 |
|---|---|---|---|
| `E:\output\1\api\rule_engine\plugins\traffic_plugin.py` | 修改 | `_extract_vehicles`（约 L150-186） | docstring 增加第 4 条说明（+6 行）；新增 3 行分支 + 1 行注释 |
| `E:\output\1\tests\test_traffic_plugin_contract.py` | 新增 | 全文 | 10 个 unittest 用例（§4.2） |

净变化 **+10 行 / -0 行**（`git diff --stat` 见 §4.1），无任何删除或重排。

---

## 4. Git 状态与 diff 范围

### 4.1 任务结束后

```text
$ git status --porcelain
 M 1/_TASK-029-M09_integration_selfcheck.json      ← 任务开始前既有修改（Trae 副作用），原样保留
 M 1/api/rule_engine/plugins/traffic_plugin.py     ← 本任务授权修改
?? 1/docs/AI_COORDINATION_PROTOCOL.md              ← 既有未跟踪，保留
?? 1/docs/PROMPT_DSH_TASK-COORD-001.md             ← 既有未跟踪，保留
?? 1/docs/PROMPT_TRAE_TASK-COORD-002.md            ← 既有未跟踪，保留
?? 1/docs/REPORT_TASK-COORD-001_DSH.md             ← 既有未跟踪，保留
?? 1/docs/REPORT_TASK-COORD-002_TRAE.md            ← 既有未跟踪，保留
?? 1/docs/REPORT_TASK-COORD-003_DSH.md             ← 本报告（见 §9 说明）
?? 1/tests/test_traffic_plugin_contract.py         ← 本任务授权新增
?? dsh-compaction-verify/  dsh-workshop-backup/  dsh-workshop-patch/
?? dsh-workshop-src-recovered/  dsh/  skill-detail.mjs  skill-scan.mjs   ← 既有未跟踪，保留

$ git diff --stat
 1/_TASK-029-M09_integration_selfcheck.json  | 16 ++++++++--------   ← 非本任务产生
 1/api/rule_engine/plugins/traffic_plugin.py | 10 ++++++++++
 2 files changed, 18 insertions(+), 8 deletions(-)
```

### 4.2 授权文件的实际 diff

```diff
diff --git a/1/api/rule_engine/plugins/traffic_plugin.py b/1/api/rule_engine/plugins/traffic_plugin.py
@@ -155,6 +155,12 @@ class TrafficPlugin(BaseRulePlugin):
           1. scene_context["vehicles"]（list[dict]）
           2. scene_context["tracked_vehicles"]（dict[id -> dict]）
           3. tracker.get_all_vehicles()（若提供 tracker 且有该方法）
+          4. tracker 本身即是 tracked_vehicles 字典（dict[id -> vehicle]）
+
+        第 4 条对应生产调用形态：TrafficEventEngine.process_frame 把
+        realtime_detector.tracked_vehicles 原样作为第三实参传给
+        plugin.analyze(frame, scene_context, tracked_vehicles)，
+        此时车辆在 tracker 实参里，scene_context（检测器 scene_config）中不含车辆。
         """
         if not isinstance(scene_context, dict):
             return []
@@ -173,6 +179,10 @@ class TrafficPlugin(BaseRulePlugin):
             except Exception:
                 return []
 
+        # 生产形态：tracker 实参就是 {track_id: vehicle_dict}
+        if isinstance(tracker, dict) and tracker:
+            return [v for v in tracker.values() if isinstance(v, dict) and v]
+
         return []
```

### 4.3 未触碰区域确认

- 未修改：`realtime_detector.py`、`traffic_event_engine.py`、`base_plugin.py`、`plugin_loader.py`、`behavior_engine.py`、`vehicle_tracker.py`
- 未修改：数据库结构/数据/迁移、EvidenceChain、CloudAI、FastAPI 路由、EventCenter、视频规则阈值、启动脚本、模型权重、配置
- 未执行 `git reset --hard` / `git checkout -- .` / `git clean -fd`
- 未删除、重命名、覆盖、格式化任何文件
- 未产生新的 `__pycache__`：全程设 `PYTHONDONTWRITEBYTECODE=1`；`tests/`、`api/rule_engine/` 下 3 个既有 `__pycache__` 目录 mtime 仍为 `15:41:37 / 15:41:53`（Trae 上一轮产物，未变）

---

## 5. 执行的命令、结果与退出码

环境：`py -3` = Python 3.12（`C:\Users\ROG\AppData\Local\Programs\Python\Python312`），cwd = `E:\output\1`，`PYTHONDONTWRITEBYTECODE=1`。

### 5.A 新增契约测试

```text
$ py -3 -m unittest tests.test_traffic_plugin_contract -v
...
test_production_shape_creates_event_with_correct_track_and_type ... ok
test_vehicle_reaches_behavior_analysis ... ok
test_production_shape_cooldown_still_applies ... ok
test_production_shape_has_no_vehicle_in_scene_context ... ok
test_empty_tracked_vehicles_dict_creates_no_event ... ok
test_non_vehicle_dict_values_are_ignored ... ok
test_legacy_scene_context_vehicles_still_works ... ok
test_legacy_scene_context_tracked_vehicles_still_works ... ok
test_tracker_object_with_get_all_vehicles_still_works ... ok
test_plugin_analyze_directly_with_tracker_dict ... ok

Ran 10 tests in 0.053s
OK
EXITCODE=0
```

关键用例的运行时自述输出：

```text
[test_production_shape_creates_event] 事件类型=['red_light', 'speeding'] track_ids=[7]
[test_vehicle_reaches_behavior_analysis] 行为分析收到车辆 id=[7]
[test_plugin_analyze_directly] 插件直接返回 2 个违规 ['red_light', 'speeding']
[test_production_shape_cooldown] 首次=2 事件，冷却期第二次=0
```

### 5.B 相关既有测试（回归检查）

```text
$ py -3 -m unittest tests.test_traffic_plugin_contract tests.test_traffic_event_engine \
      tests.test_circular_frame_buffer tests.test_evidence_chain \
      tests.test_cloud_collaborator_event tests.test_multi_frame_validator

Ran 46 tests in 0.026s
OK
EXITCODE_A=0
```
（46 = 既有 36 + 新增 10；既有 36 个用例无一失败，无回归。）

### 5.C 敏感性验证：测试确实能捕获该回归

把 `TrafficPlugin._extract_vehicles` 用 monkeypatch 打回**修复前的逐行等价实现**（不修改任何文件），只跑 2 个核心用例：

```text
$ py -3 -（stdin 脚本，monkeypatch 后置打补丁）
test_production_shape_creates_event_with_correct_track_and_type ... FAIL
    AssertionError: 0 not greater than or equal to 1 :
    生产形态下未创建任何 TrafficEvent —— 车辆参数契约仍然断裂
test_vehicle_reaches_behavior_analysis ... FAIL
    AssertionError: [] is not true : 行为分析从未被调用 —— 车辆未到达规则分析阶段

Ran 2 tests in 0.054s
FAILED (failures=2)
tests run = 2  failures = 2  errors = 0
判定： 测试能捕获该回归（符合预期）
[exit code: 1]
```

结论：新测试不是"跟着实现写的空断言"，而是**在修复前必然失败、修复后必然通过**的契约回归测试。

> 附带发现（已在测试中规避并注释）：`PluginLoader.discover()` 对已在 `sys.modules` 里的插件模块执行 `importlib.reload()`（`plugin_loader.py:84-87`），会生成新的类对象。因此测试在 `setUpClass` 里从 `sys.modules` 重新取得"加载器实际使用的那个类"再做 `isinstance` 校验；若在文件顶部 `import TrafficPlugin` 后直接 `isinstance`，会因陈旧类对象而误判失败（首轮即遇到，已修正）。

### 5.D 全量测试套件基线

```text
$ py -3 -m unittest discover -s tests -t tests
ERROR: test_core (unittest.loader._FailedTest.test_core)
ImportError: Failed to import test module: test_core
ModuleNotFoundError: No module named 'pytest'

Ran 47 tests in 0.030s
FAILED (errors=1)
EXITCODE_B=1
```

对照改动前基线（TASK-COORD-001 实测）：`Ran 37 tests / FAILED (errors=1)`，唯一错误同为 `test_core` 缺 `pytest`。
**改动后：47 = 37 + 10，错误数与错误对象完全不变**，即该错误与本任务无关（`pytest` 未安装，属既有环境问题，未安装、未修复）。

---

## 6. 回归测试如何隔离真实模型、摄像头与网络

测试文件 `tests/test_traffic_plugin_contract.py` 的隔离手段：

| 隔离目标 | 手段 | 证据 |
|---|---|---|
| **真实模型（YOLO/CUDA）** | 不导入 `realtime_detector`（其模块级单例 `realtime_detector.py:1098` 会执行 `init_all_models()` 加载 YOLO 并 `.to('cuda')`）；只导入 `rule_engine.plugin_loader` / `traffic_plugin` / `behavior_engine` / `traffic_event_engine` | 测试耗时 **0.053s**，输出中无任何 `YOLO model loaded` 行 |
| **摄像头 / 视频文件** | `process_frame(frame=..., detections=[], ...)` 传 `frame=None`、`detections=[]`；`TrafficPlugin.analyze` 的实现不使用 `frame`（`traffic_plugin.py:115` 注释已声明），行为分析只吃车辆轨迹字典 | 无 `cv2.VideoCapture`、无文件读取；不写任何文件 |
| **网络 / 云端** | 不导入 `image_recognizer` / `cloud_collaborator`；引擎路径止于 `TrafficEventEngine`（`traffic_event_engine.py:153-160` 明确"不直接调用云端 AI"），事件创建阶段不发任何 HTTP | 无云端调用；无 API Key 依赖 |
| **真实 BehaviorEngine 的确定性** | 用真实 `BehaviorEngine`（纯 Python 规则，无模型），车辆轨迹使用**固定时间戳** `_FIXED_BASE_TS=1700000000.0` 与固定坐标序列（y=100..500，每 0.5s），并显式提供 `traffic_light_state='red'`、`stop_line_y=350` → `red_light` 判定与 `speeding` 判定（200 px/s → 72 km/h > 默认 60）完全确定 | 重复运行结果一致（§5.A 与 §5.C 多次运行同结果） |
| **测试装置符合生产形态（自证）** | `test_production_shape_has_no_vehicle_in_scene_context` 显式断言 `'vehicles' not in scene_context`、`'tracked_vehicles' not in scene_context`、第 3 实参为 `dict`、被测对象确为 `TrafficPlugin` | 该用例 PASS |
| **用例间互不干扰** | 每个用例 `setUp` 新建 `TrafficEventEngine`（冷却表干净） | 冷却用例可独立验证 |

覆盖层级（验收对应）：

- `test_production_shape_creates_event_with_correct_track_and_type` —— **经过 `TrafficEventEngine.process_frame` + 真实 `TrafficPlugin` + 真实 `BehaviorEngine`**，断言事件 `event_type='red_light'`、`track_id=7`、`state=TRIGGERED`、`vehicle_info` 取自字典、`rule_judgment.confidence>0`、`state_history` 起始正确；
- `test_vehicle_reaches_behavior_analysis` —— 用记录型代理包裹真实 `BehaviorEngine`，断言 `analyze_all` **被调用且收到的正是字典中那个车辆对象**（`assertIs(spy.seen_vehicles[0], self.vehicle)`），即"车辆进入行为分析"而非"只被提取"；
- `test_plugin_analyze_directly_with_tracker_dict` —— 插件层直接契约（不经引擎）同样成立；
- 反向用例 —— 空字典、非车辆值不产生事件（防止"凭空造事件"）；
- 兼容用例 —— scene_context 两条旧路径 + `tracker.get_all_vehicles()` 对象路径均未回退。

**未做的隔离妥协**：未使用假行为引擎替代真实 `BehaviorEngine`，而是"真实引擎 + 记录代理"，因此既确定了违规结果，又对"车辆真的进入分析阶段"提供了直接证据。

---

## 7. 风险与阻塞

### 7.1 本任务相关风险（低）

| 项 | 说明 |
|---|---|
| 兼容性 | 新增分支放在最后，仅当 1/2/3 全部落空时才生效，原有行为零改变（兼容用例已覆盖） |
| 脏数据 | 非 `dict` 值被过滤；空字典直接落到 `return []` |
| 引擎侧未动 | `_extract_vehicle_info`（`traffic_event_engine.py:233-244`）与 `_extract_trajectory`（L289-296）**未修改**——因此事件 `trajectory` 仍是 1 个点（TASK-COORD-001 R-4），属本任务范围外，不影响事件创建 |
| 生产未实跑 | 本任务的证据是"契约层 + 单元层"，**不是**真实视频端到端证据（见 §6 与 §8） |

### 7.2 仍未验证（明确区分）

> **本任务证明的是：** 生产参数形态下，车辆能够从 `tracked_vehicles` 字典进入行为分析，并让 `TrafficEventEngine` 创建出 `track_id` / `event_type` 正确的事件。
> **本任务没有证明：** 真实交通视频能跑通完整闭环。

仍未验证的具体事项：

1. 真实视频 → YOLO → `VehicleTracker` 是否能在真实画面上产出带 `history ≥ 5` 的车辆（本次用固定构造字典替代）；
2. `event_videos/{YYYYMMDD}/{event_id}.mp4` 是否真实落盘（`E:\output\1\api\output\event_videos\` 当前仍为空）；
3. `traffic_events` 表是否首次出现真实记录（当前仍 **0 行**；TASK-COORD-001 §9.2、TASK-COORD-002 §1.4 均已实测）；
4. 云端 `analyze_event` 真实判定与 `_handle_event_lifecycle` 的完整状态流转（本次未进入 `_handle_event_lifecycle`）；
5. HTTP 层端到端（后端 8001 未在本任务启动）；
6. 前端 EventCenter 展示真实事件（属前端范围）。

---

## 8. 建议的下一步

1. **[P0，建议新开 TASK-COORD-004] 真实视频最小闭环验证**（TASK-COORD-001 §11 已给出可执行方案）：
   - 输入：一段真实交通视频（建议 ≥20s，含车辆轨迹）；
   - 前置：TASK-COORD-003 修复已合入（本次已具备触发条件）；
   - 路径：`POST /api/realtime/source {source_type:"video", video_path}` → `POST /api/realtime/start` → 轮询 `/status`（观察 `event_engine.total_events` 增长）→ `GET /events/active`、`GET /events`、`GET /events/{id}/video`；
   - 产物判据四件套：mp4 落盘 + `traffic_events` ≥1 行 + 该行 `event_video_path` 指向真实文件 + `GET /events/{id}` 返回含 `state_history`；
   - 若真实视频仍不触发，需排查"YOLO 是否在真实画面上产出带 `history` 的追踪车辆"，这是修复后**下一个**可能的断点（本任务未触及）。
2. **[P1] 复核本任务**：由 Trae IDE 只读复核（协作者权限），重点核对 `traffic_plugin.py` 的 10 行改动与 `tests/test_traffic_plugin_contract.py` 是否真以生产形态调用。
3. **[P1] 事件证据完整性**（TASK-COORD-001 已记录的 R-2/R-3/R-4/E-5，均需独立 TASK 授权）：`key_frames` 占位符、EvidenceChain 场景键名不匹配、`_extract_trajectory` 单点、review 的 `old_state` 记录错误。
4. **[P2] 数据库路径统一**（`config.py:19` vs `database.py:7`）：修好后 `test_task029_integration` 第 7 项才能转绿。

---

## 【发现的额外问题】

> 均为本任务范围外，**只记录，未修改**。

| # | 文件或模块 | 问题描述 | 是否阻塞本任务 | 建议后续 TASK |
|---|---|---|---|---|
| 1 | `api/config.py:19` vs `api/database.py:7` | `Config.DB_PATH` 指向不存在的 `E:\output\1\zhitong_violations.db`；`database.py` 用 CWD 相对路径，实际库在 `api\`。导致 `tests/test_task029_integration.py` 第 7 项恒 FAIL | 否 | 独立 TASK：DB 路径单一来源化 |
| 2 | `api/rule_engine/plugin_loader.py:84-87` | `discover()` 对已在 `sys.modules` 的插件模块执行 `importlib.reload()`，产生新类对象；任何"先 import 类、再 discover、再 isinstance"的调用方都会误判（本任务测试首轮即踩到，已规避） | 否（已规避） | 独立 TASK：reload 策略评估（或文档化该行为） |
| 3 | `api/realtime_detector.py:629-643` | `_pick_key_frame_paths` 返回 `frame_0/frame_5/frame_9` 占位字符串，非真实 jpg 路径 | 否 | 独立 TASK：关键帧落盘 |
| 4 | `api/evidence_chain.py:139-152` | 读 `scene_context['traffic_light']` / `['stop_line']`，生产写入键为 `traffic_light_state` / `stop_line_y` → 证据链场景字段恒 `unknown` | 否 | 独立 TASK：键名对齐 |
| 5 | `api/traffic_event_engine.py:289-296` + `233-244` | `_extract_trajectory` 只产出 1 个轨迹点（未透传 tracker 的 `history`），证据链轨迹退化 | 否 | 独立 TASK：轨迹透传 |
| 6 | `api/routers/realtime.py:1067-1074` | 人工复核 DB 分支先赋新值再取 `old_state`，导致 `old_state == new_state` | 否 | 独立 TASK：小修 |
| 7 | `tests/test_core.py:6` | 依赖未安装的 `pytest`，全量套件恒非全绿（改动前后同为该 1 个 error） | 否 | 独立 TASK：安装 pytest（需环境变更授权）或改写为 unittest |
| 8 | `api/routers/realtime.py:808-825` | `_sync_active_events_to_db` 的 `common_fields` 不含 `evidence_chain`，该列恒 NULL | 否 | 独立 TASK：证据链持久化 |
| 9 | 工作区 | `1/docs/REPORT_TASK-COORD-003_DSH.md`（本报告）不在任务"允许修改"清单中，但任务"最终报告要求"强制要求提交报告，故沿用 001/002 既有命名约定新增 | 否 | 请在验收时确认该文件是否纳入版本管理 |

---

## 【本次任务模型信息】

- **实际使用模型**：当前环境无法可靠读取实际模型名称。
- **任务复杂度**：**L3**
- **模型选择理由**：本任务需跨"检测器 → 事件引擎 → 插件 → 行为分析"四层核对实参/形参契约，并判断"仅改插件是否足够"（需排除对两个核心文件的改动），同时要设计一个既能捕获回归、又完全离线且确定的测试。属多文件交叉理解 + 最小风险改动，L3 适配；未为节省成本而降低所需能力。当前会话未提供可信的更高能力模型切换入口。
- **是否发生模型切换**：否。
- **切换原因**：不适用（全程未遇到能力瓶颈；唯一的判断难点——`importlib.reload` 导致的类身份失效——已通过测试内自证与规避解决）。

---

*报告结束。本任务仅修改 `1/api/rule_engine/plugins/traffic_plugin.py`（+10 行）并新增 `1/tests/test_traffic_plugin_contract.py`；未触碰任何禁止修改区域，未清理或还原任何既有工作区改动。*
