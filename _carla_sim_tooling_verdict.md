# CARLA 交通违规仿真「游戏级」工具化 · 调研与方案

> 日期：2026-10-17　｜　状态：**第 1 批已交付待实测；第 2/3 批待启动**
> 定位（用户 2026-10-17 明确）：这是**演示素材生产线**，用于生成演示视频以校验/展示「智瞳灵声」项目能力，**不属于项目本体**。
> 调研执行：`carla-eco-scout` / `traffic-sim-scout` 两名只读调研员；原始笔记见 `E:\output\_scout_notes\`。

---

## 0. 一句话结论

**CARLA 0.9.16 官方生态没有任何"拖拽摆车 + 逐车设速度 + 编辑红绿灯时长"三合一的图形化编辑器**；但**这些能力的底层 API 在 0.9.16 里全部存在**（本机实测）。
→ 因此最省力路线不是引入新平台，而是**把本机已有的「CARLA 创造工坊」补齐成编辑器**。

---

## 1. 你的诉求 → 6 项能力（含现状盘点）

现有资产：`E:\output\1\carla\CARLA_0.9.16\PythonAPI\examples\carla_creator_workshop.py`（2026-10-13 建立，入口 `E:\output\1\carla\启动CARLA创造工坊.bat`）。

| # | 你的诉求 | 改造前 | 本轮目标 | 状态 |
|---|---|---|---|---|
| 1 | 拖拽摆车 | ❌ 只能按 spawn point 顺序生成 | 鼠标点击摆车；拖动已有车辆 | 第 2 批 |
| 2 | 控制速度 | ❌ 只有 autopilot 开关 | 单车速度/全局速度差/闯红灯概率 | ✅ 第 1 批 |
| 3 | 红绿灯时长 | ❌ 完全没做 | 相位表编辑 + 稳定控灯 | ✅ 第 1 批 |
| 4 | 游戏级观感 | ⚠ 预览仅 960×540 | 1920×1080 预览/录制 | ✅ 第 1 批（录制 1080p） |
| 5 | **车牌号** | ❌ 没有 | 中国式车牌，文本可指定 | 第 3 批（待实测贴图） |
| 6 | 数据可输出 | ⚠ 录 `mp4v` 960×540 | H.264 / 1920×1080 / 20fps | ✅ 第 1 批 |

---

## 2. 事实：有没有现成的？（调研结论）

### 2.1 CARLA 官方生态

| 工具 | 图形化 | 拖拽摆车 | 设速度 | 改灯时长 | 结论 |
|---|---|---|---|---|---|
| **carla-studio**（官方唯一 GUI，Qt） | ✅ | ❌（Qt3D 拖拽=**传感器标定**） | 未证实 | ❌ | 不是场景编辑器 |
| ScenarioRunner | ❌ CLI | ❌（Python/OpenSCENARIO 定义） | ✅ `SpeedAction` | ⚠ `TrafficSignalControllerAction` 可用，但 OSC 的 `RoadNetwork TrafficSignals` **被忽略** | 场景靠写代码 |
| Traffic Manager | ❌ | ❌ | ✅ 百分比/精确目标速度 | ❌（可设 `ignore_lights_percentage`） | 运行时行为控制 |
| SUMO + netedit | ✅ | ❌（编辑路网/需求，非摆车） | ✅ SUMO 侧 | ✅ **相位表可直接编时长** | 2D；本机 CARLA **自带官方 co-sim** |
| UE 编辑器内的 CarlaTools | ✅ | — | — | — | **本机不可用**：release 包不含 UE 编辑器（官方原文：要用 UE Editor 必须源码构建） |

### 2.2 你点名的 `oasis-sim` —— 已定位

**最可能 = Synkrotron / GuardStrike 的 OASIS（OASIS Sim）**：
- CARLA 官方博客原文：**"OASIS Sim provides a Scenario Editor GUI that enables users to design and edit traffic scenarios visually and intuitively"**（`carla.org/2023/12/12/synkrotron-oasis/`）
- CARLA 官方文档 **0.9.16 生态页**即有此条目：*built on top of CARLA*
- **商业产品**：Request Trial License，**不开源**

→ 这解释了你为什么觉得"人家能拖拽"：那正是商业产品的卖点。我们不能直接拿它落地。

### 2.3 第三方 / 独立平台候选

| 候选 | 图形化拖拽 | 免费/许可 | Windows | 与 CARLA | 评价 |
|---|---|---|---|---|---|
| **SUMO + netedit** | 2D 点击建网、**相位表改灯时长**、点击插车 | EPL-2.0 | ✅ | **官方 co-sim（本机自带）** | 落地最容易，但非 3D、非"摆车" |
| **Webots** | ✅ 3D 拖拽对象 | Apache-2.0 | ✅ | ❌ 无官方桥 | 真 3D 拖拽，交通场景要自己搭 |
| **腾讯 TAD Sim 单机版** | ✅ 场景+地图编辑器、信控、速度参数、**鼠标画轨迹** | Apache-2.0 | 官方支持 Win11 | ❌ 独立平台 | 最接近"游戏级"，但落地有坑（见 §11） |
| UT-ADL visual-scenario-editor | ✅ 俯视地图摆车/灯 | 无 LICENSE（10★） | Python | **明确兼容 0.9.15/0.9.16** | 太小众、资质不明 |
| drawtonomy（浏览器画布） | ✅ 画车道/车/灯 | 免费浏览器 | ✅ | ⚠ OSC 灯动作会被 CARLA 忽略 | 好看但对接有损 |
| Blender Driving Scenario Creator | ✅ 3D 视图拖拽 | 开源 | ✅ | 导出 OpenDRIVE+OSC | 工程量最大 |

---

## 3. 关键技术可行性（**本机实测**，证据等级＝一级/命令结果）

> 实测方式：`py -3.12` 直接 introspect 本机 `carla` 模块（未启动 CARLA，零副作用）。
> 探针脚本：`E:\output\_scout_notes\probe_carla_api.py`、`probe_carla_api2.py`

### 3.1 点击摆车 / 拖动车辆 —— ✅ 可行（第 2 批）

```
World.ground_projection(Location, search_distance=10000.0) -> Location|None
World.cast_ray(initial_location, final_location) -> list[Actor]
World.project_point(Location, Vector3D direction, search_distance) -> object
```

实现路径：点击预览画面 → 相机反投影出世界射线 → `cast_ray` 判断是否点中车辆（选中/拖动）→ 未点中则 `ground_projection` 取地面点 → `map.get_waypoint()` 吸附车道 → spawn/移动。
★ 相机反投影公式项目里**已有现成知识**（`zht-project-playbook` §6），可直接复用。

### 3.2 速度控制 —— ✅ 可行（第 1 批已实现）

```
Actor.set_target_velocity / enable_constant_velocity / disable_constant_velocity
Vehicle.get_speed_limit
TrafficManager.vehicle_percentage_speed_difference / set_desired_speed
              / global_percentage_speed_difference / ignore_lights_percentage
```

### 3.3 红绿灯时长 —— ✅ 可行（第 1 批已实现；★修正旧结论见 §7）

```
TrafficLight.set_green_time / set_yellow_time / set_red_time / get_elapsed_time
TrafficLight.set_state / get_state / freeze / reset_group / get_group_traffic_lights
World.freeze_all_traffic_lights(bool) / reset_all_traffic_lights()
```

正确用法：
1. `set_green_time(x)` 改的是**该灯所属 junction 组 controller 的阶段阈值**（默认 10/3/2 秒），**不是**"从现在起绿 x 秒"。
2. 组 tick 会覆盖单次 `set_state` → 稳定控灯必须 `freeze_all_traffic_lights(True)`（0.9.16 的 `freeze()` 实为**全局**）**再逐 tick `set_state()`**。
3. `set_elapsed_time` **在客户端不存在**。

### 3.4 车牌号 —— ⚠ 需实测（第 3 批）

事实：**无 `license_plate` 蓝图属性、无专用 API**。车牌子串在车辆共用材质 `MI_LicensePLate` 上（本机 196 个 uasset 中仅 `BaseVehiclePawn*` 引用），官方从 0.4.1 起就是"随机贴图"。

贴图通道（本机实测存在）：
```
World.apply_color_texture_to_object(object_name: str, material_parameter: MaterialParameter, texture: TextureColor)
World.apply_textures_to_object(object_name, diffuse, emissive, normal, ao_r_m_e)
World.get_names_of_all_objects() -> list[str]
```
- **方案 a（唯一候选，待实测）**：给车牌材质槽贴自定义 PNG（对应社区 issue #5971）。风险：材质是**车辆共用**的 → 可能"所有车同号"。
- ~~方案 b（录制后逐车叠加）~~ —— **用户 2026-10-17 已否决**：车辆在移动，逐帧投影叠加容易出问题。**不再采用**。

---

## 4. 三条路线（用户已选 **D = A 第一批 + 自己试 C**）

| 路线 | 做什么 | 工作量 | 收益 | 代价 |
|---|---|---|---|---|
| **A 增强「创造工坊」** ✅ 选中 | 补齐 §1 的 6 项 | **中**（分 3 批） | 与项目素材口径对齐；零安装；车牌/机位可精确控制 | 界面 Tkinter 朴素；"拖拽"= 点击/拖动 |
| B Web 拖拽前端 | Three.js + Python 桥 | **大**（A 的 5~10 倍） | 最像"游戏" | 世界同步/拾取/UI 全重做 |
| C 换独立平台 | TAD Sim / SUMO / Webots | **小**（装+学） | 开箱有编辑器 | 脱离 CARLA、无车牌证据 |

---

## 10. 第 1 批交付实录（2026-10-17）

### 10.1 改了什么

| 项 | 值 |
|---|---|
| 文件 | `E:\output\1\carla\CARLA_0.9.16\PythonAPI\examples\carla_creator_workshop.py` |
| 行数 | 546 → **1265**（+719） |
| 备份 | `carla_creator_workshop.py.bak_20261017`（25740 B，原文件未动） |
| 入口 | `E:\output\1\carla\启动CARLA创造工坊.bat`（不变） |
| 回滚 | 用备份覆盖回去即可（一行命令，见 §10.7） |

### 10.2 新增 UI（用户视角）

左栏（新增滚动条）自上而下：
1. 自由相机（原有）
2. 车辆摆放（原有）
3. **红绿灯配时（新）**：`扫描本图红绿灯` → 下拉选灯 → 显示"同组 N 盏灯" → `绿灯秒 / 黄灯秒 / 红灯秒` → `开始自定义配时` / `停止自定义配时` → 实时显示"当前相位：绿灯 剩余 12.3s"
4. **车辆速度（新）**：`刷新车辆列表`（id | 车型 | 当前 km/h | 自动驾驶/手动）→ `目标速度 km/h` + `应用到选中车` → `取消选中车的恒定速度` → `全局速度差 %` + `应用全局` → `闯红灯概率 %` + `应用到选中车`
5. 天气与光照（原有）
6. 场景与视频（原有 + 新）：`相机分辨率` 960x540/1280x720/1920x1080（切换保留机位）· `录制帧率` 10/15/20/30 · ffmpeg 状态提示

### 10.3 关键实现事实

- **红绿灯**：`freeze_all_traffic_lights(True)` + `world.on_tick` 相位机 → 到点对**同组每盏灯** `set_state()` 并同步三个 setter；停止时 `remove_on_tick` + `freeze(False)` + `reset_group()`；`close()` 走同一收尾 → **不会把世界的灯冻在那里**
- **速度**：autopilot 车走 TM `set_desired_speed`；非 autopilot 车按**车头朝向**算世界向量 `enable_constant_velocity`；全局 `global_percentage_speed_difference`；闯红灯 `ignore_lights_percentage`
- **录制**：ffmpeg 解析顺序 = CanMV 真 exe → `which('ffmpeg.exe')` → `which('ffmpeg')`+shell；失败降级 `cv2 mp4v`；管道 IO 走独立 `record_lock`，**不与 GUI 的 `frame_lock` 嵌套**（避免编码跟不上时界面卡死）
- **预览**：超过 960 宽自动缩放，1080p 录制时预览仍流畅

### 10.4 验收证据（lead 独立复核，非子代理自述）

| 项 | 结果 |
|---|---|
| `py -3.12 -m py_compile` | **exit 0** |
| GUI 冒烟（CARLA 未启动） | 窗口正常开合；15 原有 + 8 新增方法全在 |
| ffmpeg 解析 | `C:\Program Files\CanMV IDE K230\...\ffmpeg.exe`，shell=False |
| 录制产物（子代理实测） | h264 **1920x1080 20fps** 91301 B；降级 mpeg4 960x540 |
| 录制中 close | 110770 B / h264 1920x1080 12 帧，收尾有效 |
| 修复后复测 | 产物字节数与修复前完全一致（91301/45907/110770）→ 无丢帧无重复 |

### 10.5 已知限制

1. **本机 ffmpeg 无 libx264**（构建时 `--disable-libx264`）→ 实际用 **libopenh264** 出 H.264（`-b:v 20M` 代替 `-crf 18`）。代码运行时探测，将来换成带 libx264 的 ffmpeg 会自动切回。
2. **预览是 960px 宽**（细节看不清属正常，录制仍是 1080p）。
3. ⚠ **未验证项（必须开 CARLA 才能确认，不算已完成）**：
   - 全局 freeze + `set_state` 在**本机实际**是否稳定（源码层面正确，未跑）
   - TM 的 `set_desired_speed` / `global_percentage_speed_difference` / `ignore_lights_percentage` 实际效果
   - 相机重建后机位是否真的保持
   - 1080p 长时间录制吞吐

### 10.6 用户实测路径（四件套）

见对话交付说明；核心是：先启动 CARLA → 双击 `启动CARLA创造工坊.bat` → 连接 → 扫描红绿灯 → 开始自定义配时。

### 10.7 回滚命令

```powershell
cd 'E:\output\1\carla\CARLA_0.9.16\PythonAPI\examples'
Copy-Item .\carla_creator_workshop.py.bak_20261017 .\carla_creator_workshop.py -Force
```

---

## 11. C 路线结论：TAD Sim / Webots / SUMO 试用手册（供用户自测）

详见 `E:\output\_scout_notes\traffic_sim_scout.md` **附录 A**（点击路径级）。关键判断：

| 平台 | 体积 | 优点 | **风险/短板** |
|---|---|---|---|
| **TAD Sim 单机版** | **740 MB** | 官方文档明写：模型库**左键长按拖拽**放车、信控配置可**克隆后改相位时长**、主车设初始/最大速度、地图编辑器可画路 | ① **`display` 模块官方没说从哪获取**（release 只有 exe/deb）→ 可能没有 3D 画面；② 内置仅 1 张地图；③ **"交通流"功能官方标注"暂未开放"**；④ **无车牌**（26 篇文档零命中）；⑤ **无视频导出**（只能 Win+G/OBS 录屏） |
| **Webots city_traffic** | **250 MB** | 装完 `File → Open Sample World` 搜 `city_traffic` 即开即播（自带路网/红绿灯/循线车/SUMO 接口） | 多车交通流需另装 SUMO；不是 CARLA |
| **SUMO netedit** | **166 MB** | 改信号配时最直接（Traffic Light 模式直接编 phase table）、点击插车 | 2D；不是"摆车"式编辑 |

**建议**：若只是"想亲眼看看游戏级效果"，**先跑 Webots（250 MB，3 分钟出画面）**；TAD Sim 先看官方文档截图再决定是否下 740 MB。

---

## 7. 被推翻 / 修正的旧结论

| # | 旧结论 | 现状 | 证据 |
|---|---|---|---|
| **O1** | "`set_green/yellow/red_time` **无效**，只有逐 tick `set_state()`"（`zht-project-playbook` §6） | **表述不准确**：setter **有效**，但它改的是"junction 组 controller 的阶段阈值"，单独调用会被组 tick 覆盖，所以才需要 freeze + 逐 tick `set_state`。**操作建议仍成立，理由需更正** | 源码链 `CarlaServer.cpp:2592-2615` → `TrafficLightController::SetStateTime` + 本机 `dir()` 实测 |
| **O2** | （隐含）"仿真只能靠脚本生成 + 录屏，没有交互工具" | **错**：`carla_creator_workshop.py` 早已存在（546 行，2026-10-13） | 本机文件实测 |
| **O3** | "oasis-sim 是某种开源仿真器" | **错**：它是 Synkrotron/GuardStrike 的**商业** CARLA 内核产品（Scenario Editor GUI） | CARLA 官方博客 + 0.9.16 生态页 |
| **O4** | "Python 的 subprocess 直接 Popen `.cmd` 必然失败"（**lead 本轮的错误推断**） | **错**：本机 Win11 + Python 3.12 实测 `Popen([ffmpeg.CMD, '-version'])` **rc=0 可用**；但仍按"真 exe 优先"重写（少一层 cmd.exe、更可控） | 实现员 smoke 实测（rc=0 + 出片 7424 B/h264） |
| **O5** | "录制后逐车叠加车牌可行"（lead 曾列为兜底） | **用户否决**：车辆移动时逐帧投影易出错 → 只保留 CARLA 内贴图路线 | 用户 2026-10-17 原话 |
| **O6** | （第 2 批开工前初判）"`cast_ray`/`project_point` 能直接给出'屏幕点 → 地面点'"，以及"它们返回 `Location` / Actor 列表" | **两处都错**：① 三个 API **没有一个**做"屏幕点 → 地面点"；② 0.9.16 实测它们返回的是 **`carla.LabelledPoint`**（`.location` + `.label`，如 `Roads`），不是 `Location`，`cast_ray` 也不是 Actor 列表。把返回值当 `Location` 用会**静默失效**（退化成 z=0 平面解） | 本机 docstring + **真实 CARLA 实测 20/20**（`_scripts\_verify_workshop_live_carla.py`） |
| **O7** | "让视频里的车**遵守**交通规则很难"（用户原话，lead 也曾顺着这个假设去调） | **错**：TM 一行 `set_autopilot(True, 8000)` 就遵守。实测车在**手动冻结并设红**的灯前减速到 **0**、停在停止线前 **2.92 m**、10 秒不动 | 真实 CARLA（§14.2 采样表） |
| **O8** | "`tm.ignore_lights_percentage(veh, 100)` 能造闯红灯车"（**CARLA 官方文档推荐做法**） | **本机实测无效**：异步模式车停 10.3 m；**切同步模式仍停 11.5 m（速度 0）**。→ 违规车必须**关 autopilot + `apply_control` 油门**手动驱动 | 真实 CARLA 两轮实测（§14.5 K1） |
| **O9** | "`enable_constant_velocity(fwd*speed)` 可用于任何方向的直线行驶" | **在反向车道会走反方向**：同一辆车同位置，`constant_velocity` → `dot=-1.00`，`apply_control(throttle)` → `dot=1.000` | 真实 CARLA 对照实测（§14.5 K2） |

---

## 8. 证据等级与来源

| 结论 | 等级 | 来源 |
|---|---|---|
| CARLA 官方无三合一图形编辑器 | 二级（官方文档/源码） | `_scout_notes\carla_eco_scout.md` |
| oasis-sim = Synkrotron OASIS（商业） | 二级（官方博客+官方文档） | carla.org / readthedocs 0.9.16 |
| API 全部存在 | **一级（本机命令结果）** | `probe_carla_api.py` / `probe_carla_api2.py` |
| set_green_time 语义 | 二级（源码链）+ 一级（方法存在） | CarlaServer.cpp / TrafficLightController.cpp |
| 车牌无属性、无 API | 二级（官方建模教程+CHANGELOG）+ 一级（本机 uasset 扫描） | `tuto_A_add_vehicle`、196 个 uasset |
| 第 1 批代码可编译/可启动 | **一级（py_compile + GUI 冒烟）** | 本文 §10.4 |
| 第 1 批功能真实生效 | **三级未验证**（需开 CARLA） | §10.5 |

---

## 9. 未确证清单（不要当结论用）

1. `apply_color_texture_to_object` 能否**逐车**独立贴车牌（材质共享风险）
2. carla-studio 是否随 0.9.16 发布 / 能否 Windows 原生构建
3. TAD Sim 单机版 `display` 模块来源、渲染质量、动力学许可
4. carla-simulator/traffic-generation-editor 与 0.9.16 实际兼容性
5. drawtonomy 是否开源
6. 51Sim / MORAI 免费版细节；rFpro 官网 403 未取证

---

## 12. 第 2 批交付实录：点击摆车 / 拖动车辆（2026-10-17）

### 12.1 改了什么

| 项 | 值 |
|---|---|
| 文件 | `E:\output\1\carla\CARLA_0.9.16\PythonAPI\examples\carla_creator_workshop.py` |
| 行数 | 1265 → **1782**（+517，含实测后修的 4 个 bug） |
| 备份 | `carla_creator_workshop.py.bak_20261017b`（58364 B，改前原样） |
| 回滚 | 见 §12.7 一行覆盖 |

### 12.2 新增 UI（用户视角）

「车辆摆放」框内新增子框「鼠标摆放（在右侧预览画面上操作）」：

1. ☑ 点击空地：摆一辆当前车型（默认开）
2. ☑ 按在车上：拖动（只平移，不转向，默认开）
3. ☐ 落点吸附车道中心与车道朝向（**默认关** —— 用户 2026-10-17 裁定"默认严格跟鼠标"）
4. ☐ 松手后恢复该车原来的自动驾驶（**默认关** —— 用户裁定"松手后停在原地"）
5. `删除选中车辆` / `撤销上一步`（撤销栈深度 10）
6. **（便利性）鼠标点中车辆时，自动把该车同步到「车辆速度」下拉** —— 省掉再去列表里找 id

### 12.3 关键实现事实

- **反投影**：复用 playbook §6 同一组基 `fwd/right/up`，`d = fwd + px*tan(fov/2)*right − py*tan(fov/2)*(h/w)*up`；fov 从 `camera.attributes['fov']` 读（不是写死 90）；**未用** `get_inverse_matrix()`
- **屏幕→地面三级回退**：① 解析求交（射线 ∩ z=0）→ ② `ground_projection(点, 300)` 校真实路面高度 → ③ 视角太平/解析失败时才用 `project_point` 兜底（语义未验证，只兜底）
- **拾取**：`bounding_box.get_world_vertices(transform)` 8 顶点投影 → `cv2.convexHull` → `pointPolygonTest`；多车命中取相机深度最近；只遍历 `owned_vehicle_ids`（不动别人的 Actor）
- **拖动**：40ms + 3px 双节流；拖动中**零 RPC 查询**（只 `set_transform`），松手才用 `ground_projection` 校正 z
- **自动驾驶**：拖动开始 `set_autopilot(False)` + `disable_constant_velocity()` + `set_target_velocity(0)`；松手默认不恢复（勾选才恢复）
- **撤销栈**：`("spawn", id, None)` / `("move", id, transform)`，深度 10；删除车辆时清掉该车全部记录
- **预览坐标**：`_refresh_preview` 记录 `preview_scale` + 居中 `preview_offset`，顺带修掉"窗口比图小就裁切"的老问题
- **抓取偏移**：按下时记录"车位置 − 鼠标地面点"，拖动不跳位

### 12.4 验收证据（lead 独立复核，非子代理自述）

| 项 | 结果 |
|---|---|
| `py -3.12 -m py_compile` | **exit 0** |
| 投影/拾取/地面 单测 `_scripts\_verify_workshop_projection.py` | **12/12 PASS**（像素↔世界往返误差 **0.0000px**） |
| GUI 冒烟 `_scripts\_verify_workshop_gui.py`（CARLA 未启动） | **26/26 PASS**：窗口开合、11 个新方法、断连点击不崩 |
| 状态机流程 `_scripts\_verify_workshop_drag_flow.py`（mock world） | **13/13 PASS**：点击摆车→拖动→松手落地→再拾取→撤销→删除全链 |
| **真实 CARLA 三级验证** `_scripts\_verify_workshop_live_carla.py`（Town10HD_Opt / 0.9.16） | **20/20 PASS**：点击摆车偏移 **0.00m**、拖动 **10.5m**、松手落地 z=0.18（路面 0.00）、拾取 id 一致、撤销/删除全过、世界清理 0 残留 |

★ 单测抓到并修掉一个真 bug：`_world_to_pixel` 的 v 轴符号写反（误差正好 1080px），修正后往返误差 0。

### 12.5 已知限制 / 未验证项

1. ✅ **2026-10-17 已在真实 CARLA 实测**（Town10HD_Opt / 0.9.16，**20/20**）：`set_transform` 拖动生效、落地高度正确、拾取/撤销/删除正常、世界清理 0 残留
2. `project_point` 返回 `LabelledPoint` 已实测；它仍只作兜底
3. 拖动**只平移不转向**；相机 roll 非 0 时反投影未按 roll 修正（`reset_camera` 会把 roll 归零）
4. 拖动刚开始一两帧可能残留原速度（已 `set_target_velocity(0)`，异步世界下属正常现象）
5. 相机正在移动时点击有几帧位姿延迟（静止无影响）
6. 叠车检查用 1.5m 阈值并遍历全场景车辆（约百辆时单次点击约百毫秒）
7. 多车前后重叠时按 bbox 凸包 + 深度最近拾取（符合直觉，但密堆场景可能选中前车）
8. **桥上/高架摆车**：落地高度改用车道高度后仍可能落到桥下车道（`get_waypoint` 取最近车道）

### 12.6 用户实测路径（四件套）

```powershell
# ① 启动 CARLA（已开可跳过；占约 6GB 显存）
& 'E:\output\1\carla\CARLA_0.9.16\CarlaUE4\Binaries\Win64\CarlaUE4-Win64-Shipping.exe' -carla-rpc-port=2000 -quality-level=Epic -nosound

# ② 启动工坊（或双击 E:\output\1\carla\启动CARLA创造工坊.bat）
& 'E:\output\1\carla\启动CARLA创造工坊.bat'
```

- **预期**：连接后右侧出现实景画面；车辆摆放框底部出现「鼠标摆放」
- **判断标准**：点空地 → 状态栏"已摆放 … id N"；按住车拖动 → "正在拖动 …"；松手 → "已放在 x=…, y=…；自动驾驶保持关闭"
- **失败分支**：点空地没反应 → 看状态栏是否提示"视角太平"（用 ↓ 低头）；提示"这个位置已经有车了" → 换位置；画面黑屏 → 确认 CARLA 已加载完地图

### 12.7 回滚命令

```powershell
cd 'E:\output\1\carla\CARLA_0.9.16\PythonAPI\examples'
Copy-Item .\carla_creator_workshop.py.bak_20261017b .\carla_creator_workshop.py -Force
```

### 12.8 真实环境暴露并修复的 4 个 bug（离线测试全绿也发现不了）

| # | 现象（真实 CARLA） | 根因 | 修法 |
|---|---|---|---|
| **B1** | 点地面后车落到 (0,0,0) 或 69m 外 | `ground_projection` / `project_point` 返回 **`LabelledPoint`**，`isinstance(Location)` 判假 → 主路径**静默失效** | `_as_location()` 支持 `.location` |
| **B2** | 摆完立刻按住拖，车会跳到 64m 外 | 新 spawn 的 actor 下次 tick 前 `get_transform()` 返回 **(0,0,0)**，`origin_z=0`、抓取偏移 = 0 − 地面点 | spawn 后 `wait_for_tick` + 把刚算出的 transform 直接传给 `_begin_drag` |
| **B3** | 车生成后掉到路面下 **1.79m** | `ground_projection` 取到的地面低于真实路面（Town10HD） | 落地高度改用 `map.get_waypoint().transform.location.z` |
| **B4** | 删除/撤销后车辆列表留**幽灵条目**；`_pick_vehicle` 仍会遍历已销毁车 | `world.get_actor(id)` 对已销毁 actor 仍返回 **stale 代理** | 判存活统一走 `world.get_actors().find(id)`（`_live_actor` / `_live_actor_ids`） |

★ 教训：**离线单测全绿 ≠ 真实环境可用**。这 4 个 bug 只有三级证据才能暴露；已同步写进 `zht-project-playbook` §6 的 CARLA 硬知识，下次不重踩。

### 12.9 启动器 bat「打不开」的根因排查（2026-10-17）

**现象**：双击 `启动CARLA创造工坊.bat` 没窗口 / cmd 一闪；但直接 `py -3.12 <脚本>` 完全正常。

**实测证据**（`cmd /c <bat>` 捕获输出）：
```
The system cannot find the path specified.
'??坊脚本：' is not recognized as an internal or external command
'??败。请确认' is not recognized as an internal or external command
Press any key to continue . . .
```

**双根因**：
1. **LF-only 换行**（原文件 `CRLF=1 / LF_only=14`）→ cmd.exe 解析多行 `if (...)` 块出错
2. **UTF-8 中文内容** + cmd 按系统代码页（GBK）读 → 中文行被拆成独立"命令"，`if not exist` 块被破坏，`py` 那行根本没执行

**修法**：
- 备份 `启动CARLA创造工坊.bat.bak_20261017`
- 内容改**纯 ASCII**（不写 `chcp`、不写中文），`Set-Content -Encoding ascii`
- 换行强制 **CRLF**（`ReadAllText → -replace "\`n","\`r\`n" → WriteAllText(ASCII)`）
- 验后：`CRLF=16 / LF_only=0`

**附带修复（窗口看不见）**：Tk 默认位置在高 DPI / 小屏上会贴边甚至跑出屏幕（实测左侧面板被裁）→ `__init__` 新增 `_place_window()`：显式居中 + 尺寸自适应屏幕。

**验证**：`cmd /c <bat>` → python PID 33064，窗口 rect `[213,123 – 1509,982]`（屏 1707×1067）完整可见；截图 `_screen_workshop_final.png`。

**排查用的三条命令**（以后遇到同类问题直接跑）：
```powershell
$bat='E:\output\1\carla\启动CARLA创造工坊.bat'
$b=[IO.File]::ReadAllBytes($bat); $crlf=0;$lf=0
for($i=0;$i -lt $b.Length;$i++){ if($b[$i] -eq 10){ if($i -gt 0 -and $b[$i-1] -eq 13){$crlf++}else{$lf++} } }
"CRLF=$crlf LF_only=$lf"          # 期望 CRLF=N, LF_only=0
py -3.12 "E:\output\1\carla\CARLA_0.9.16\PythonAPI\examples\carla_creator_workshop.py"   # 绕过 bat 验证脚本
Get-Process python | Select-Object Id, MainWindowTitle    # 看窗口是否真的存在
```

---

## 13. 第 3 批：项目名修正 + 选中 / 右键菜单 / 朝向编辑（2026-10-17）

### 13.1 用户报的问题与根因

| 现象 | 根因 |
|---|---|
| 点车反而**又生成一辆新车** | `place_on_click_var` **默认 True**：点击没命中 bbox 凸包就直接走摆车分支；凸包边缘差 1px 就判空 |
| 不知道**选中了谁** | 没有任何选中视觉反馈（状态栏一行字不算） |
| **改不了朝向** | 功能根本不存在（拖动只平移、不转向） |

### 13.2 改动

1. **左键点空地默认不再摆车**（`place_on_click` 默认 `False`）→ 只取消选中
2. `_pick_vehicle` 增加**屏幕中心距离 45px 兜底**（凸包未命中但点得够近也算选中）
3. 选中车在预览图画**黄框**（`_draw_selection`，每帧叠加，884 像素实测）
4. **右键菜单**（`<Button-3>` 绑定）：
   - 点车：正对镜头 / 朝向 ±90° / 对齐车道 / 输入角度 / 目标速度 / 闯红灯 100% / 取消恒速 / 删除
   - 点空地：在此摆放一辆车
5. 摆车入口保留两条：勾选「左键点空地：直接摆一辆」 或 右键空地菜单
6. **项目名修正**：`灵瞳智声` → **`智瞳灵声`**（窗口标题）
7. 启动器改 **无控制台**（`where pyw` → `start "" pyw -3.12 ...`），窗口不再被 cmd 黑窗挡住；Python 侧崩溃写 `仿真输出\workshop_error.log`（无控制台时也能排查）

### 13.3 验收

| 项 | 结果 |
|---|---|
| `py_compile` | exit 0（1960 行） |
| GUI 冒烟 | **35/35**（9 个新方法 + `<Button-3>` 绑定 + 默认值） |
| 状态机 | **15/15**（含 yaw +90 / 绝对值） |
| 真实 CARLA（选中黄框 + 朝向） | **7/7**：黄框 **884 像素**、yaw 0→90→37、对齐车道差 0.04° |
| 真实 CARLA 回归 | **20/20** |

### 13.4 项目名残留（**未动，等用户定**）

`灵瞳智声` 仍出现在：

| 文件 | 处数 | 说明 |
|---|---|---|
| `1\tools\evidence_cleanup_center.py` | 2 | 窗口标题 + docstring（项目代码） |
| `1\docs\project_analysis_gpt_upgrade.md` | 2 | 文档正文 |
| `_notes\TASK-029_*.md` / `TASK-031_*.md` | 4 | 引用外部 docx 原名，**不应改** |
| `1\NATIONAL_SPRINT_BRIEF.md` | 4 | 本身就在记录这个命名问题 |

### 13.5 CARLA 资源占用分析（**未执行，优化选项**）

| 项 | 实测 |
|---|---|
| 进程 Private | **10.4 GB** |
| WorkingSet | 4.7 GB |
| Content 资产 | 15.29 GB / 29426 文件 |
| Town10HD.umap | 6.9 MB（umap 只是索引，实际资产在 `Content/Packages`） |

**结论：不是"地图文件大"，而是资产库 + 画质 + UE 运行时开销。**

**"裁剪地图"不可行**：`.umap` 必须用 UE 编辑器重新打包，而 release 包**不含编辑器**（§10 已调研）。

**可按收益排序的替代手段**：

| # | 手段 | 预期 | 代价 |
|---|---|---|---|
| 1 | `-quality-level=Low` | 省 1–3 GB，帧率更高 | 画面变差（阴影/后处理降级） |
| 2 | `-ResX=1280 -ResY=720 -windowed` | 渲染负载约减半 | 录制分辨率降低（工坊内仍可 1080p 渲染相机） |
| 3 | 换小地图 `Town05`/`Town03`（1.8 MB） | 关卡加载更轻 | 路网风格不同，需重新选机位 |
| 4 | `-nullrhi` | 几乎不占显存 | **无画面、不能录视频** |
| 5 | 减少同时存在的车辆 / 关闭 TM | 少量 | 交通流变少 |

**对比测法**：
```powershell
& '...\CarlaUE4-Win64-Shipping.exe' -carla-rpc-port=2000 -quality-level=Low -ResX=1280 -ResY=720 -windowed -nosound
Get-Process CarlaUE4-Win64-Shipping | Select-Object @{n='WS_MB';e={[int]($_.WorkingSet64/1MB)}}, @{n='Priv_MB';e={[int]($_.PrivateMemorySize64/1MB)}}
```

---

## 14. 第 4 批可行性实测（2026-10-17，三项需求开工前调研）

### 14.1 静态装饰物不是 Actor，而是 EnvironmentObject

| 实测项 | 结果 |
|---|---|
| `world.get_actors().filter('static.*')` | **0 个**（Town10HD 的装饰物不是 Actor，`actor.destroy()` 删不掉） |
| `world.get_environment_objects(Buildings)` | **781** |
| `world.get_environment_objects(Vegetation)` | **62,581** |
| `world.get_environment_objects(Poles)` | **880**（路灯/杆） |
| `get_environment_objects(Fences / TrafficSigns / Walls)` | 148 / 147 / 34 |
| `EnvironmentObject` 字段 | `id` / `name` / `type` / `transform` / `bounding_box` |
| `world.enable_environment_objects(ids, enable)` | **存在**（可隐藏/恢复，隐藏后碰撞一起消失） |

**结论**：要"删掉挡视线的树/路灯"，正解是 `get_environment_objects` + `enable_environment_objects(ids, False)`；`actor.destroy()` 对它们无效。**代价**：Vegetation 有 6.2 万个，必须空间过滤 + 一次性缓存，不能每帧全量投影。

### 14.2 Traffic Manager **本来就遵守**自定义红绿灯（★推翻"遵守很难"）

实测：Tesla 放在停止线前 6 m → `set_autopilot(True, 8000)` → 灯 `freeze(True)` + `set_state(Red)` → 每秒采样：

```
t=01 speed=14.0 dist_to_stop=5.03 state=Red
t=02 speed= 0.0 dist_to_stop=2.92 state=Red
t=03..t=10 speed=0.0 dist_to_stop=2.92 state=Red
```

**车在停止线前 2.92 m 刹停并保持 10 秒不动。**

**结论**：TM 读灯的**实际状态**，`freeze + set_state` 会被正常遵守。"让车遵守交规很难"不成立 —— **车在 autopilot 上就会自己遵守**。之前"不遵守"的真正原因是：工坊**点击摆出来的车默认没开 autopilot**（`_spawn_vehicle_at` 未调用 `set_autopilot`，`auto_var` 只作用于"在可用道路位置生成一辆车"按钮）。

补充事实：`carla.Vehicle` **没有 `get_autopilot()`**，autopilot 状态只能客户端自己记账（本项目用 `autopilot_ids`）。

### 14.3 场景保存的字段缺口

现有 `save_scene`（v1）只存 `map / weather / vehicles[blueprint, transform]`。

**没存**：autopilot 状态、目标速度、`ignore_lights` 概率、红绿灯配时、相机机位、被隐藏的 EnvironmentObject、选中车 —— 这就是"重开后恢复不了原样"的原因。

### 14.4 第 4 批已交付：六种行为模式 + 道具放置（真实 CARLA 10/10）

**右键菜单 →「行为模式（造违规用）」**，每辆车可独立设置：

| 模式 | 实现 | 实测结果 |
|---|---|---|
| 遵守交规 | `set_autopilot(True, 8000)` + `ignore_lights 0` + `speed_diff 0` | 红灯前 **6.16 m 停住、速度 0.0** ✓ |
| 闯红灯 | 关 autopilot + **油门直行**（绕过 TM） | 沿车头移动 **15 m、dot=1.00** ✓ |
| 超速 | autopilot + `vehicle_percentage_speed_difference(-40)` | 沿用 TM 接口（未单独计时对比） |
| 逆行 | 挪到对向车道（`lane_id` 符号相反）+ 油门直行 | 车道 **-1 → +1** ✓ |
| 压线 | 横向偏移 0.95×半车道 + 油门直行 | 偏移 **1.66 m**（车道宽 3.50）✓ |
| 违停 | 关 autopilot + 零速 | **移动 0.00 m、速度 0.0** ✓ |

另新增：左栏 **「全部车辆开始行驶（遵守交规）」** 一键按钮；蓝图下拉可选 **99 种 `static.prop.*`**（路障/锥桶/施工牌/路牌/垃圾桶…），摆出来可拖动、可右键删除。

### 14.5 两个必须记住的坑（都实测确认）

| # | 坑 | 实测证据 | 结论 |
|---|---|---|---|
| **K1** | `tm.ignore_lights_percentage(veh, 100)` **不生效** | 异步模式：车停 10.3 m；**切同步模式后仍停 11.5 m**（速度 0.0）；官方文档明确说这是造"闯红灯车"的标准方法 | 0.9.16 本机该开关实际无效 → **违规车必须关 autopilot 手动驱动** |
| **K2** | `enable_constant_velocity(fwd*8)` 在**反向车道会走反方向** | 同一辆车同位置：`constant_velocity` → `dot=-1.00`；`apply_control(throttle)` → `dot=1.000` | 手动驱动一律用 **`apply_control` 油门**，不要用恒定速度定方向 |

★ 另外确认：**遵守交规一点都不麻烦**（一行 `set_autopilot`），麻烦的是"精确违规"。官方文档也承认 TM 是"非目标导向、路口随机选路"的群体模型，不适合精确编排单车剧本。
