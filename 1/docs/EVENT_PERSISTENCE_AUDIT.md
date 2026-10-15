# 事件持久化审计 —— 「事件不落库」根因

> 2026-10-03 由 DSH 审计。**严重度：高**。本条是"证据链可追溯"红线的基础设施缺口。

---

## 一、事实与证据

### 证据 1：内存里在涨，数据库里不动
```
状态接口: 事件总数=42（本次运行新产生）
数据库  : 总行数=541，最新 created_at=2026-10-02 19:13:29
最近 10 分钟创建的事件: 0 条
当前时间: 2026-10-03 05:01:52
```

### 证据 2：541 行的 created_at 全部落在同一秒
```
evt_1790968408877_287_3caf47  speeding        created=2026-10-02 19:13:29.091547
evt_1790968406760_287_f2c1d1  lane_departure  created=2026-10-02 19:13:29.091547
evt_1790968397107_276_5bdb84  speeding        created=2026-10-02 19:13:29.091547
...
```
**同一秒写入 541 行** —— 只可能来自**批量迁移脚本**，不可能是实时产生的。

### 证据 3：引擎代码里没有任何数据库访问
```
TrafficEventEngine 的方法清单：
  __init__ / process_frame / _extract_vehicle_info / _trigger_event
  _extract_trajectory / reject / _update_event_state / _check_cooldown
  get_active_events / get_event / get_all_events / submit_to_ai
  apply_ai_result / manual_review / transition_to_recording / cleanup_old_events

全文件搜索 SessionLocal / from models / db.  -> 无任何匹配
```
**结论：`TrafficEventEngine` 是纯内存实现，事件从不写入 `traffic_events` 表。**

---

## 二、后果（为什么严重）

| # | 后果 | 说明 |
|---|---|---|
| 1 | **重启即丢失** | 后端一重启，所有事件（含 CONFIRMED/REJECTED 终态）全部消失。**证据不可追溯** —— 直接违反本项目"证据链完整可追溯"红线 |
| 2 | **`evidence_chain` 永远为空** | 我本轮实现的 `_persist_evidence_chain` 会先查库找行，找不到就跳过 → **实测 0% 落库**（与现象吻合）|
| 3 | **前端事件中心只看到旧数据** | `/events` 页面读的是数据库，永远显示那 541 条 9 月 26 日的记录 |
| 4 | **小程序/申诉无法关联** | 小程序按车牌查违规，走的是 `violation_evidences`（那条链路已修好）；但**事件级**证据（视频/关键帧/轨迹）无法被引用 |
| 5 | **`updated_at` 从不更新** | 状态流转只改内存，数据库看不到任何状态变化 |

---

## 三、修复方案

### 方案 A（推荐）：在 `_update_event_state` 里做 upsert
所有状态变化都经过 `_update_event_state`，是**唯一的收口点**：

```python
def _update_event_state(self, event, new_state, reason=""):
    ...
    event.state = new_state
    event.updated_at = datetime.now().isoformat()
    event.state_history.append({...})
    # 新增：落库（upsert）
    self._persist_event(event)
```

`_persist_event` 用 `event_id` 做 upsert：存在则 UPDATE，不存在则 INSERT。
- **优点**：一处收口，覆盖所有状态流转；事件一创建（TRIGGERED）就落库
- **风险**：每个状态变化一次写库（事件量不大，可接受）

### 方案 B：在 `_trigger_event` 创建时 INSERT 一次
只落"创建"这一下，后续状态更新再补。
- 优点：写库次数少
- 缺点：状态流转不同步到库（终态看不到）

**建议 A + B 结合**：创建时 INSERT，状态变化时 UPDATE 状态相关字段。

### 落库字段映射（models.TrafficEvent → dataclass TrafficEvent）
| 数据库列 | dataclass 字段 |
|---|---|
| `event_id` | `event_id` |
| `event_type` | `event_type` |
| `track_id` | `track_id` |
| `state` | `state.value` |
| `trigger_time` | `trigger_time` |
| `vehicle_info` | `json.dumps(vehicle_info)` |
| `scene_context` | `json.dumps(scene_context)` |
| `trajectory` | `json.dumps(trajectory)` |
| `key_frames` | `json.dumps(key_frames)` |
| `event_video_path` | `event_video_path` |
| `rule_judgment` | `json.dumps(rule_judgment)` |
| `ai_judgment` / `ai_confidence` / `ai_explanation` | 同名 |
| `state_history` | `json.dumps(state_history)` |
| `evidence_chain` | 由 `_persist_evidence_chain` 写 |
| `created_at` / `updated_at` | 时间戳 |

---

## 四、连带发现（同一根因）

| # | 问题 | 与本次审计的关系 |
|---|---|---|
| 1 | **P0「未标定超速跳过 AI 复核」未能验证** | 我的门禁代码已就位（`reject()` + `RUNTIME_SETTINGS.cloud_review_uncalibrated`），但**事件不落库** → 无法从数据库侧验证；需先修持久化 |
| 2 | `ai_trace.yolo.confidence` 恒为 0.0 | 独立问题：应写入真实检测置信度 |
| 3 | `evidence_chain` 设计完整但从未被调用 | 类 `EvidenceChain` 有 22 个字段、`to_json()` 都写好了，只是没人调用 |

---

## 五、本轮已完成的修复（在持久化修复后即可生效）

### 修复 1：未标定超速不进 AI 复核队列
位置：`realtime_detector.py`（事件处理流程第 3 步）
```python
_needs_numeric = event.event_type in ("speeding",)
_calib = event.vehicle_info.get("calibration") or event.vehicle_info.get("speed_method")
_is_calibrated = bool(_calib) and not str(_calib).startswith("assumed")
_skip_ai = _needs_numeric and not _is_calibrated
if _skip_ai and not RUNTIME_SETTINGS.get("cloud_review_uncalibrated", False):
    self.event_engine.reject(event.event_id, reason="数值类违规未经场景标定，无法由视觉模型验证")
    return
```
新增 `TrafficEventEngine.reject()`（RECORDING 的合法去向只有 PENDING_AI/REJECTED，
不能直接跳 MANUAL_REVIEW）。
新增运行时开关 `cloud_review_uncalibrated`（默认 False，可在控制台改）。

### 修复 2：`_persist_evidence_chain`
位置：`realtime_detector.py:1688`
- 用 `EvidenceChain` 组装 22 个字段（车辆/场景/轨迹/关键帧/规则判断/AI判断/终态）
- upsert 到 `traffic_events.evidence_chain`
- **正常 AI 流程**与**跳过 AI 的分支**都会调用
- 若事件不在库中会**明确记 debug 日志**（不是静默失败）

**实测结果**：0% 落库 —— **因为前提（事件落库）不成立**，这正是本审计要解决的问题。

---

## 六、下一步（按优先级）

| # | 事项 | 依赖 |
|---|---|---|
| **P0** | **实现事件 upsert 落库**（方案 A+B） | 无 —— 约 60 行 |
| P0 | 落库后重新验证：`evidence_chain` 落库率、未标定超速跳过 AI | P0 |
| P1 | `ai_trace.yolo.confidence` 写真实置信度 | 无 |
| P1 | 前端 `/events` 页面回归（数据会开始增长） | P0 |
| P2 | 事件清理策略（`cleanup_old_events` 只清内存，落库后需考虑归档） | P0 |

---

## 七、可复现命令

```powershell
# 1) 内存事件数 vs 数据库行数（差值 = 未落库量）
curl http://127.0.0.1:8001/api/realtime/status    # 看 event_engine.total_events
sqlite3 E:\output\1\api\zhitong_violations.db "SELECT COUNT(*) FROM traffic_events"

# 2) 检查 541 行是否同一秒写入（判断是否为迁移批量导入）
sqlite3 ... "SELECT COUNT(DISTINCT created_at) FROM traffic_events"

# 3) 确认引擎无数据库访问
Select-String -Path E:\output\1\api\traffic_event_engine.py -Pattern 'SessionLocal|from models'
```
