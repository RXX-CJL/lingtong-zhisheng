# CARLA 创造工坊 · 第 4 批交付（①场景 v2 / ②装饰物隐藏）

> 日期：2026-10-23　执行：DSH lead + 2 个 teammate　目标文件：`E:\output\1\carla\CARLA_0.9.16\PythonAPI\examples\carla_creator_workshop.py`

## 0. 一句话状态

**① 已交付并通过我的独立验收**（五层验证全绿 + 实机 round-trip 85/0）。
**② 代码已写完但未验收**（子代理中断于实机验证阶段，用户去睡觉）。**② 未合并风险 = 0**：三项既有回归仍全绿，说明它没破坏 ①。

## 1. ① 场景 v2 + 自动保存 + 最近项目 —— ✅ 已交付

### 1.1 证据（全部由 lead 独立复跑，非子代理自述）

| 验证层 | 命令 | 结果 |
|---|---|---|
| 编译 | `py -3.12 -m py_compile <目标>` | **exit 0** |
| 离线 GUI | `_verify_workshop_scene_v2_offline.py` | **PASS=68 FAIL=0** |
| 序列化 mock | `_verify_scene_v2_mock.py` | **PASS=103 FAIL=0** |
| 既有 GUI 回归 | `_verify_workshop_gui.py` | **PASS=35 FAIL=0** |
| **真实 CARLA** | `_verify_workshop_scene_v2.py` | **PASS=85 FAIL=0** |

实机关键数值：车辆还原 **xy 误差 0.00000**、dyaw 0.0000；红绿灯配时 12/2/15 正确恢复；
v1 旧档兼容不抛异常；自动存档真实写盘、无 `.tmp`、能被 `load_scene` 读回；K2 回归 `moved=0.70m dot=0.997`（正向）。

### 1.2 v2 格式字段（相对 v1 的补齐）

```json
{
  "format": "carla_creator_workshop_scene_v2",
  "map": "Town10HD_Opt",
  "weather": { /* 14 个实测数值字段，见 §3.1 */ },
  "vehicles": [{ "blueprint", "transform", "autopilot", "behavior_mode",
                 "target_speed_kmh", "ignore_lights_percent" }],
  "props":   [{ "blueprint", "transform" }],
  "traffic_lights": { "opendrive_id", "group_actor_ids",
                      "durations": {"Green","Yellow","Red"}, "phase", "running" },
  "camera": { "fov", "image_size_x", "image_size_y", "transform" },
  "hidden_environment_objects": { "Vegetation": [id,...], "Poles": [id,...] },
  "session": { "selected_vehicle_index", "selected_vehicle_id",
               "global_speed_diff_percent", "target_speed_kmh",
               "ignore_lights_percent", "record_fps", "camera_resolution",
               "spawn_autopilot_default" },
  "saved_at": "...", "auto_save": true
}
```

- **向后兼容**：`SCENE_FORMAT_READABLE` 同时接受 v1/v2，v1 缺的字段按旧语义（`auto_var`）填。
- **自动存档**：每 180 秒写 `仿真输出\场景快照\last_session.json`，`root.after` 定时、**原子写**（`.tmp` + `fsync` + `os.replace`）；`close()` 时最后一次落盘。
- **最近项目**：`仿真输出\_workshop_recents.json`，最多 10 条、新的在前、重复置顶、文件丢失的条目会标注并不崩。

## 2. ② 装饰物（EnvironmentObject）选中与隐藏 —— ⚠️ 代码已完成，未验收

### 2.1 已写入代码（行号，共 2752 → 约 3300 行）

**三档交互全部实现**（用户拍板要三档）：

| 档 | 函数 | 行号 | UI |
|---|---|---|---|
| A 按类别批量 | `hide_env_label` / `show_env_label` | 1199 / 1212 | 类别下拉 + 隐藏该类全部 / 恢复该类全部 |
| B 右键点中单个 | `_env_pick` / `_env_pick_menu` / `hide_env_single` | 1319 / 1375 / 1433 | 「右键优先拾取装饰物」勾选 + 右键菜单 |
| C 相机半径批量 | `hide_env_in_range` / `_env_range_ids` | 1221 / 1097 | 半径输入 + 隐藏范围内该类别 |
| 兜底 | `restore_all_env` | 1260 | 一键恢复全部已隐藏 |

支撑设施：`ENV_LABELS` 六类、`hidden_env_ids` 状态、`_load_env_cache`/`invalidate_env_cache` 缓存生命周期、
`_env_project_masked` 向量化投影、`_restore_hidden_environment_objects`（v2 加载侧接上）。

### 2.2 未完成的部分（子代理中断处）

- `_verify_workshop_env_live.py` 已写（19,456 字节）但**未跑完**，无 PASS/FAIL 数字
- `_verify_workshop_env_offline.py` 已写（11,260 字节）但**我没拿到它的结果**
- 缓存性能数字、档 B 拾取实测数据**均缺失**

## 3. 被推翻的旧结论（本轮新增）

### 3.1 `reflection_intensity` 在 CARLA 0.9.16 **不存在**（推翻我的任务书假设）

我在任务书写「反射率、太阳方位角等能存就存」，子代理按此实现后 test 报 `KeyError`，去实测才发现该属性不存在。
lead 独立探测确认：`hasattr(w,'reflection_intensity')` = **False**，`getattr` 抛 `AttributeError`。

**真实数值字段恰好 14 个**：cloudiness, precipitation, precipitation_deposits, wind_intensity,
sun_azimuth_angle, sun_altitude_angle, fog_density, fog_distance, fog_falloff, wetness,
scattering_intensity, mie_scattering_scale, rayleigh_scattering_scale, dust_storm。

另有 23 个非数值属性（`ClearNoon` / `WetSunset` 等预设常量）**不可存入场景**。
实现走 `dir()` 实测 + `hasattr` 过滤自动发现，不是写死清单，所以将来 CARLA 真加字段也不会漏。

### 3.2 「6.2 万个必须空间过滤」的**理由要改**（推翻 verdict §14.1 的措辞）

§14.1 说「Vegetation 有 62,581 个，必须空间过滤 + 一次性缓存，不能每帧全量投影」——**结论对，理由错了**。
lead 实测：

| 操作 | 耗时 |
|---|---|
| `get_environment_objects(Vegetation)` RPC | **133 ~ 228 ms** |
| 62,581 个点 numpy 向量化全量投影 | **1.2 ms** |
| 半径 60m 预筛后投影 | **0.00 ms**（候选 332 个） |
| `enable_environment_objects(200 ids, False)` | **0.039 s** |
| `enable_environment_objects(200 ids, True)` | **0.009 s** |

→ **真正的瓶颈是 RPC 不是投影**。必须缓存的理由是「每帧调 RPC 会卡死」，不是「投影太慢」。
空间过滤的正确用途是**档 C 的按半径批量隐藏**，以及减少档 B 拾取的候选集。

### 3.3 `EnvironmentObject.id` **超出 int64**（新发现的坑，会导致崩溃）

实测样例 `16740775638937321093` > 2^63-1。它是 Python int，本身没问题，
但**一旦塞进 numpy int64/int32 数组就 `OverflowError: int too big to convert`**。
已在两个任务书里明确：坐标可进 numpy（float64），id 一律保持 Python list/set/int。
v2 序列化用 `int(x)` 原样写十进制，JSON 往返不丢精度（mock 里用该样例做了回归）。

### 3.4 `EnvironmentObject` **没有** `get_world_vertices()`，且 `bbox.location != transform.location`

Actor 有 `bounding_box.get_world_vertices(transform)`，EnvironmentObject **没有**，只有 `bounding_box` 属性。
且实测 `bbox.location` 是**箱体中心**不是锚点：
`name=SM_Parklight2_SM_0` → `transform.loc=(-19.85,56.40,0.15)` 但 `bbox.loc=(-19.85,56.40,2.38)`。
→ 拾取必须用 `bbox.location / extent / rotation` 自己算 8 个角点，否则「点这棵树选中旁边那棵」。

## 4. 本轮修掉的 3 个真实 bug（都是 lead 审查抓出来的，不是子代理自查）

### bug 1 · K2 违规：恢复场景速度用了 `enable_constant_velocity`

- 位置：`_apply_vehicle_item` 的 target_speed 非 autopilot 分支
- 后果：违反硬约束 K2 —— 该调用在反向车道会走**反方向**（实测 `dot=-1.00`），闯红灯/逆行场景恢复后车会朝反方向跑
- 修法：改用复用的 `_drive_forward(actor, mps)`（`apply_control` 油门）+ `mode != "parked"` 守卫

### bug 2 · `askyesno` 默认按钮是「是」→ 误按回车直接丢现场

- 位置：`_load_scene_from_path` 的「场景地图不同」与「替换当前场景」两处
- 后果：Tk 的 `askyesno` 默认按钮是 Yes，用户按回车就把世界 reload 了，用户调好的机位与场景全没
- 修法：两处都加 `default="no"`

### bug 3 · 红绿灯配时**永久改写**且不还原（第 1 批遗留缺陷）

这是本轮最有价值的一次发现，**子代理交付报告漏报了**（它只检查了 actor 数和机位，没查配时）。

- 现象：实机测完后 `odr=960/961/962` 三盏灯残留成 `12/2/15`，而同图其余 12 盏是 `10/3/2`
- 根因：`_tl_apply_phase` 用 `set_green_time/set_yellow_time/set_red_time` **永久改写服务器上那盏灯**；
  而 `stop_custom_timing` 收尾只调 `light.reset_group()`，**它只重置相位、不恢复秒数**
- 归因：已核对 `.bak_20261023` 第 1854/1914 行，**同样的写法 → 第 1 批遗留，不是本次引入**
- 修法：`start_custom_timing` 前 `_tl_snapshot_durations()` 逐灯快照，`stop_custom_timing` 后 `_tl_restore_durations()` 写回；
  已有快照不覆盖（防二次启动把改过的值当原值）、无快照直接跳过（防崩溃后瞎写）、写失败吞异常
- 验证：mock +17 条断言（PASS=103），实机 +3 条断言，`FINAL all traffic lights back to baseline` = 15 盏全回 10/3/2

**遗留限制（已知未解）**：本修复只覆盖 `stop_custom_timing` **正常调用路径**。
若客户端进程崩溃导致 stop 没跑到，配时仍会留在世界里（进程没了无法写回）。彻底解决需服务端侧或启动时基线记录，属另一件事。

### 附：bug 1 与 bug 2 之外，子代理自己发现并修的 1 个既有缺陷

`_live_actor` 对**刚 spawn 的 actor** 返回 `None` 且不抛异常（`get_actors().find(id)` 返回 None，原 try/except 兜不住），
导致 `set_vehicle_behavior` 静默失败 → 右键设行为无效。已改为 find 返回 None 时用 `_live_actor_ids()` 确认存活再 `get_actor()` 兜底。

## 5. 现场状态（收工时已还原，逐项实测）

| 项 | 值 |
|---|---|
| 总 actor | **23**（与开工一致） |
| 车辆 / 道具 / 相机 | 0 / 0 / 0 |
| 红绿灯 | 15 盏，**全部 10/3/2**（地图原值，无残留） |
| 装饰物可见性 | 64,571 个**全部恢复可见**（幂等兜底） |
| 用户机位 | `loc=(-172.196579, 183.859116, 27.638052) yaw=-45.592213`（偏差 0.000035°） |

> 说明：`spectator` 由用户自己开着的工坊窗口（PID 42796）持续同步，lead 的临时改动会被它覆盖回来——这正是机位始终正确的原因。

## 6. 回滚

| 备份 | 内容 | 用途 |
|---|---|---|
| `.bak_20261023` | 98,380 字节，**① 开工前**（第 1~3 批成果） | 想连 ① 一起回滚 |
| `.bak_20261023_after_v2` | 125,791 字节，**① 完成后 ② 开工前** | **推荐**：只回滚 ② |

回滚命令（PowerShell）：
```powershell
$d='E:\output\1\carla\CARLA_0.9.16\PythonAPI\examples'
Copy-Item "$d\carla_creator_workshop.py.bak_20261023_after_v2" "$d\carla_creator_workshop.py" -Force
```

## 7. 未闭合项（下一轮从这里接）

1. **② 的验收全部缺失**（最关键）：跑 `_verify_workshop_env_live.py` 与 `_verify_workshop_env_offline.py`，拿 PASS/FAIL 数字
2. ② 的缓存性能数字（首次 / 第二次命中）未测
3. ② 的档 B 拾取实测（用 `SM_Parklight2_SM_0` 投影反查，断言 id 一致）未做
4. ② 与 v2 持久化对接未验（隐藏 → save → 恢复 → load → 断言重新隐藏）
5. 红绿灯配时的**崩溃场景**残留风险未解（已知限制，见 §4 bug 3）
6. 车牌（`apply_color_texture_to_object`）尚未开始，是第 4 批之后的事

## 8. 数据集口径提醒（给下一轮）

**「世界干净」不能只看 actor 数量。** 凡是写进服务器的世界状态都要逐项断言还原：
红绿灯配时、天气、世界设置（同步模式）、隐藏的 EnvironmentObject、spectator 机位。
本轮 bug 3 就是这么漏掉的。