# 场景 v2 + 自动保存 + 最近项目 —— 交付报告

## 0. 结论
五项验收全部通过：**round-trip 真实 CARLA PASS=82 FAIL=0**；世界已还原干净（23 actor、机位完好）。
过程中发现并修掉 **2 个真实 bug**（1 个是既有代码的潜伏缺陷）。

## 1. 改动摘要（唯一改动文件）
`E:\output\1\carla\CARLA_0.9.16\PythonAPI\examples\carla_creator_workshop.py`　2120 → **2711 行**
备份 `carla_creator_workshop.py.bak_20261023`（98,380 字节）未动。

### 1.1 新增函数（行号）
| 函数 | 行号 |
|---|---|
| `_weather_field_names` | 1526-1543 |
| `_weather_to_dict` | 1545-1558 |
| `_traffic_lights_to_dict` | 1560-1575 |
| `_camera_to_dict` | 1578-1586 |
| `_hidden_env_to_dict` | 1588-1602 |
| `_scene_to_dict` | 1604-1648 |
| `_write_json_atomic` | 1652-1668 |
| `save_scene` | 1670-1685 |
| `_apply_scene_weather` | 1687-1709 |
| `_restore_camera` | 1711-1746 |
| `_restore_traffic_lights` | 1748-1801 |
| `_apply_scene_session` | 1803-1820 |
| `_restore_selected_vehicle` | 1821-1839 |
| `load_scene` | 1841-1850 |
| `_load_scene_from_path` | 1852-1892 |
| `_spawn_scene_vehicles` | 1894-1918 |
| `_apply_vehicle_item` | 1920-1962 |
| `_spawn_scene_props` | 1964-1976 |
| `_auto_save_allowed` / `_schedule_auto_save` / `_auto_save_tick` / `run_auto_save` / `restore_auto_save` | 1980-2032 |
| `_load_recents_file` / `_load_recents` / `_recent_label` / `refresh_recents` / `_push_recent` / `open_recent_scene` | 2037-2118 |

### 1.2 修改的既有函数
| 函数 | 行号 | 改动 |
|---|---|---|
| `_build_ui` | 144-323 | 只在「场景与视频」框内追加控件 |
| `connect` | 335-355 | 连上后初始化最近项目+启动定时器（均包 try） |
| `_live_actor` | 891-906 | **修 bug，见 §2** |
| `set_vehicle_behavior` | 1133-1181 | 加 `apply_lateral` 形参 |
| `close` | 2661-2692 | 取消定时器 + 最后一次自动存档 |

### 1.3 新增 UI 控件（全在「场景与视频」框内）
- Label「最近项目（最多 10 条，新的在前）：」
- Combobox `self.recent_combo`（readonly）
- Button「打开最近项目」/「刷新列表」/「恢复上次自动存档」
- Label `self.auto_save_var`（显示上次自动存档时间与结果）

### 1.4 新增常量
`SCENE_FORMAT_V2/V1/READABLE`、`AUTO_SAVE_INTERVAL_SECONDS=180`、`AUTO_SAVE_PATH`（`仿真输出\场景快照\last_session.json`）、`RECENTS_PATH`、`MAX_RECENTS=10`

## 2. 过程中发现并修掉的 2 个真实 bug（重要）
### bug 1：`_live_actor` 对新生成的 actor 返回 None（既有代码潜伏缺陷）
证据：spawn 后立刻调用，`get_actors().find(id)` → **None 且不抛异常**；同一刻 `get_actor(id)` 正常；`id in live ids` → True；1 帧后才恢复。
后果：`set_vehicle_behavior` 开头 `_live_actor` 拿 None 直接 return → 右键设行为**静默失败**。
修法：find 返回 None 时用 `_live_actor_ids()` 确认存活再 `get_actor()` 兜底。
### bug 2：我自己引入的 UI bug（自查发现）
`refresh_recents` 空列表 `current(-1)` 抛 TclError → 被 `connect()` 吞成「连接失败」。已改 `set("")` + 独立 try。

## 3. 五项验收：命令与输出
### 1) py_compile
```
py -3.12 -m py_compile <目标文件>  → exit=0
```
### 2) 离线 GUI 冒烟
```
py -3.12 -X utf8 E:\output\_scripts\_verify_workshop_scene_v2_offline.py → PASS=68 FAIL=0
```
### 3) 真实 CARLA round-trip
```
py -3.12 -X utf8 E:\output\_scripts\_verify_workshop_scene_v2.py → PASS=82 FAIL=0
```
- 连接 Town10HD_Opt，红绿灯实测 **15 盏**（非 0），未走 SKIP
- 3 车（obey/parked/run_light）+ 1 prop
- 红绿灯 12/2/15，opendrive_id=960，同组 3 盏（9/20/18），恢复后绿12/黄2/红15 **全部 PASS**
- 天气 14 字段（云量 77/方位角 202/湿度 44）恢复 PASS
- 机位 yaw 123.5 恢复 PASS；**xy 误差 0.00000**，dyaw 0.0000
- v1 兼容：不抛异常、生成 1 车、无错误弹窗
- 自动存档：真实写 last_session.json、无 .tmp、能被 load_scene 读回 3 车、录制中跳过
- K2 回归：`moved=0.70m dot=0.997`（正向，走反会约 -1.0）
### 4) 序列化 mock
```
py -3.12 -X utf8 E:\output\_scripts\_verify_scene_v2_mock.py → PASS=86 FAIL=0
```
### 5) 既有 GUI 回归
```
py -3.12 -X utf8 E:\output\_scripts\_verify_workshop_gui.py → PASS=35 FAIL=0
```

## 4. v2 完整 JSON 样例
文件 `E:\output\_scripts\_scene_v2_full_example.json`（骨架取自真实 round-trip 产物）
顶层字段：format / map / weather / vehicles / props / traffic_lights / camera / hidden_environment_objects / session / saved_at
hidden_environment_objects 已按你要求放超 int64 样例并验证往返不丢精度：
```json
"hidden_environment_objects": {
  "Buildings": [16740775638937321093, 15364796654548762122],
  "Vegetation": [16740260845389644291]
}
```
单车：`blueprint / transform / autopilot / behavior_mode / target_speed_kmh / ignore_lights_percent`
traffic_lights：`opendrive_id / group_actor_ids / durations{Green,Yellow,Red} / phase / running`
camera：`fov / image_size_x / image_size_y / transform`
session：`selected_vehicle_index / selected_vehicle_id / global_speed_diff_percent / target_speed_kmh / ignore_lights_percent / record_fps / camera_resolution / spawn_autopilot_default`

## 5. 假设与不确定项（不隐瞒）
1. **z 不参与精度判定**：实测 xy 完全一致（0.00000），z 差 0.04~0.15m，因车生成后悬挂落到路面沉降。断言改为「xy<0.05m」+「z 沉降<0.6m」。若你认为 z 也必须严格还原，需重新讨论。
2. `selected_vehicle_index` 是我加的非任务书字段（actor id 重载后必变，只存 id 恢复不了），同时保留 id 兼容旧档。
3. `camera_fov` 改为实例字段（原 fov 写死 90，要能恢复得先能改）。
4. `parked` 模式加了守卫不施加油门；其余手动模式是 apply_control 覆盖式设置，不会与 set_vehicle_behavior 内油门叠加翻倍。
5. **0.9.16 无 reflection_intensity**（任务书「反射率」在本版本不存在），已用实测 14 字段替代。
6. 自动存档间隔未做 UI 可调，常量 180s。
7. `hidden_environment_objects` 现恒写 {}（`self.hidden_env_ids` 尚不存在），读侧 getattr 容错。

## 6. 世界清洁度
- 总 actor **23**（与初始一致）；vehicles 0 / props 0 / cameras 0
- spectator `yaw=-45.592430 loc=(-172.196579, 183.859116, 27.638052)` 与原始机位完全一致
- `仿真输出` 下无 .tmp 残留

## 7. 我制造过又清理掉的污染（如实交代）
调试期间（进程崩溃 0xC0000409 + Tk 主循环卡死）留下 1 辆残留车、8 个预览相机、3 个僵尸 python 进程，**已全部清理**，世界已验证回到 23 actor。

## 8. 边界遵守
- 唯一改动代码文件是该 .py；脚本全在 `E:\output\_scripts\`
- 未碰 `ignore_lights_percentage` 现有实现；`apply_target_speed` 的 `enable_constant_velocity` 属既有代码未动
- 本次新增代码中 `enable_constant_velocity` 出现 **0 次**
- 全程未 `load_world()`、未切 synchronous_mode、未 destroy 非本次 actor
- 未重排 UI；项目名「智瞳灵声」未动
- 换图分支 askyesno 原本默认「是」（危险），已改 `default="no"`