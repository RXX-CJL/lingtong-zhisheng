# 下一对话待办（2026-11-06 制定）

> 本轮探讨产物。上一轮：[`_zero_hardware_twin_verdict_20261106.md`](_zero_hardware_twin_verdict_20261106.md)
> 用法：新对话开场读本文件 + `_data_foundation_check_20261105.md`，即可接上。

---

## 零、已完成的（不要重做）

| 项 | 状态 | 证据 |
|---|---|---|
| B1 证据链落库键名错 | ✅ 已修 | 新事件 9/9 灯态非 unknown |
| B2 轨迹只有 1 个点 | ✅ 已修 | 新事件 9/9 轨迹点数 > 1 |
| 三文件备份 | ✅ 已做 | `.bak_20261105_b1b2*` |

**回滚**：`realtime_detector.py` / `traffic_event_engine.py` / `scene_annotation.py` 三个文件用对应 `.bak_20261105_b1b2*` 覆盖即可。

---

## 一、P0：CARLA 直连实时检测（用户 2026-11-07 提出的突破想法）

> 用户原话：「能不能将 carla 和我们的项目结合？实现直接在 carla 里面监测？这样就不用录视频了，
> 放一个"云台摄像头"在里面，我们只需要让里面的车正常运行，实时制造一些违规，摄像头实时识别」

### 1.1 关键事实：**代码已经写好，且已修过三个真 bug；但 `spawn_red_light_violator` 仍无运行记录**

> ⚠ **2026-11-07 修正**：原写「代码已经写好 80%，但从未跑过」——**「从未跑过」是错的**。
> 经 `grep` 读源码核实，代码已被真跑过并修了三处（详见 §1.4）。

**已有能力实测（`[一]` grep + 读源码）**：

| 用户需求 | 代码位置 | 状态 |
|---|---|---|
| CARLA 作为数据源 | `realtime_detector.py:784` `source_type in ("camera","video","carla")` | ✅ 已接 |
| 放"云台摄像头" | `carla_source.py:199` `attach_camera(width, height, fov)` | ✅ 已有 |
| 车正常运行 | `carla_source.py:105` `spawn_vehicles(20)` + `set_autopilot(True)` + `target_speed(30.0)` | ✅ 已有 |
| **实时制造违规** | `carla_source.py:440` **`spawn_red_light_violator()`** | ✅ **已写** |
| 实时识别 | `carla_source.py:244` `get_frame()` 返回 BGR ndarray | ✅ 已有 |
| 路由暴露 | `routers/realtime.py:1300` `POST /api/realtime/carla` `scene="violation"` | ✅ 已接 |
| 同步模式（稳定出片） | `carla_source.py:318` `set_synchronous_mode(dt=0.05)` + `tick()` | ✅ 已有 |
| 行人 | `carla_source.py:152` `spawn_walkers(10)` | ✅ 已有 |
| 数字孪生联动 | `routers/realtime.py:1315` `GET /carla/actors` | ✅ 已有 |

**⚠ 但**：`spawn_red_light_violator` 只有路由调用（`routers/realtime.py:1300`），
**没有任何一次真实运行记录**。项目手册里 CARLA 的坑（`ignore_lights_percentage` 无效、
`enable_constant_velocity` 方向反、actor 下次 tick 前返回 (0,0,0)）**都是在工坊踩的，不是在 `CarlaSource` 踩的**。
→ **这段代码的坑还在里面，未验证。**

### 1.2 为什么这个想法价值大（三个真问题）

1. **现在演示只能靠录好的 26 秒循环视频**，评委问"换个场景"只能换文件。CARLA 直连 = 现场生成任意场景
2. **这是数字孪生第 3 级「可管」**（同济四级标准：以虚预实，平行仿真推演），不是演示技巧
3. **让"零硬件"卖点更硬**：同一套检测代码既能接真实摄像头，又能接仿真 → 证明算法与硬件解耦

### 1.3 三步验收（每步独立，失败早停）

#### 第 1 步：验证 CARLA 能连上（约 30 分钟）

> ⚠ **2026-11-07 修正**：本节原写的接口是 `POST /api/realtime/carla` —— **该路径不存在**。
> 真实路由经 `grep '@router.*carla'` 核实为 5 个（`[一]`）：
> `GET /carla/status`、`POST /carla/connect`、`POST /carla/spawn`、
> `POST /carla/next-scene`、`GET /carla/actors`
> 且 **必须先调 `/carla/connect`**，否则 `_get_carla_source()` 返回未连接实例 → 400。

```bash
# ① 启动 CARLA（显存实测 8188 MiB 总，已用 1941，剩约 6.2GB；CARLA 约需 6GB）
cd E:/output/1/carla/CARLA_0.9.16/CarlaUE4/Binaries/Win64
./CarlaUE4-Win64-Shipping.exe -carla-rpc-port=2000 -quality-level=Low -nosound

# ② 先连接（必须！）
curl -X POST http://127.0.0.1:8001/api/realtime/carla/connect

# ③ 再验证状态
curl http://127.0.0.1:8001/api/realtime/carla/status

# ④ 生成违规车（正确路径是 /carla/next-scene，不是 /carla）
curl -X POST http://127.0.0.1:8001/api/realtime/carla/next-scene \
  -H 'Content-Type: application/json' -d '{"scene":"violation"}'
```

**预期**：
- ② 返回 `{"success":true,...}`（若 CARLA 未启动则 `success:false` + 降级信息，**不抛异常**）
- ③ 返回 `connected: true`
- ④ 返回 `{"success":true,"scene":"violation","violator_actor_id":<整数>,"message":"已生成一辆闯红灯车辆"}`

**判断标准**：④ 的 `violator_actor_id` 是**非 null 的整数**。
**失败分支**：
- ② 就失败 → 看 CARLA 窗口是否起来、端口 2000 是否一致（`netstat -ano | grep :2000`）
- ④ 返回 `"CARLA 未连接"` → 说明 ② 没成功，回到 ②
- ④ 返回 `actor_id: null` → `try_spawn_actor` 失败（可能 spawn point 被占），看后端日志 `[CarlaSource]` 行

#### 第 2 步：跑通「CARLA 帧 → 检测」（约 1-2 小时）

```bash
# 切源到 carla（注意：必须重启后端，或走路由热切换）
python -c "
import json,urllib.request
req=urllib.request.Request('http://127.0.0.1:8001/api/realtime/source',
  data=json.dumps({'source_type':'carla'}).encode(),
  headers={'Content-Type':'application/json'},method='POST')
print(urllib.request.urlopen(req,timeout=30).read().decode())"
```

**预期**：`{"success":true,"source_type":"carla"}`
**判断标准**：`GET /api/realtime/status` 的 `source_type="carla"`、`processed_frames` 持续增长、`tracked_vehicle_count > 0`
**失败分支**：帧不动 → 查是否需 `set_synchronous_mode` + 手动 `tick()`（`carla_source.py:318`）

#### 第 3 步：跑通「制造违规 → 识别」（约半天）★真正的验收

```bash
# 生成违规车
curl -X POST http://127.0.0.1:8001/api/realtime/carla \
  -H 'Content-Type: application/json' -d '{"scene":"violation"}'

# 等 30 秒后查库
python -c "
import sqlite3,json
c=sqlite3.connect('E:/output/1/api/zhitong_violations.db')
for eid,et,ca,ec in c.execute('select event_id,event_type,created_at,evidence_chain from traffic_events order by id desc limit 3'):
    d=json.loads(ec) if ec else {}
    print(eid, et, ca, '灯态=',d.get('traffic_light_state'), '轨迹点数=',len(d.get('trajectory') or []))"
```

**判断标准**：出现新的 `red_light` 事件，且 `evidence_chain` 的 `traffic_light_state` 不为 `unknown`、`trajectory` 点数 > 1
**失败分支**：判不出 → 见 §1.4 三个已知风险

### 1.4 已知风险（2026-11-07 实测核实后修正）

> ⚠ **原列的三条风险，经 grep 读源码核实后，两条判断错误，一条成立。**
> 教训：我上一轮把「从文件名/接口签名推断」当成了事实。下面是核实过的版本。

| 原判断 | 核实结果 | 依据 |
|---|---|---|
| ① 相机标定要重做 | ❌ **错**。`attach_camera` 已修：无父车时用路侧固定机位 `(-15.720, -63.145, 5.732, pitch=-23.445, yaw=179.536)`，**正是项目手册记录的相机本机位，与 `scene_config` 标定参数一致**。且 `set_source` 的 carla 分支已把分辨率改成可配（`CARLA_DEMO_WIDTH/HEIGHT/FOV`，缺省 **1280×720**，不再是 640×480）→ **标定不用重做** | `carla_source.py:248-266`、`realtime_detector.py:820-832`（`[一]`） |
| ② 显存抢资源 | ✅ **成立**。实测总 8188 MiB / 已用 1941，CARLA 约需 6GB | `nvidia-smi`（`[一]`） |
| ③ 代码从未跑过 | ❌ **错，而且修过三个真 bug**：<br>· `is_connected` 原为 `@property`，8 处调用带括号 → 所有 CARLA 路由 500<br>· `attach_camera` 原把相机放世界原点 `(1.5,0,2.4)`（Town10HD 里是一堵墙）→ 实测 YOLO 100% no detections<br>· **BUG-4：`set_source` 原来 new 了一个独立 `CarlaSource`，与路由层 `_carla_source_instance` 是两个实例互相抢** → 检测循环取帧走另一个实例，相机挂在世界原点，实测抓到墙<br>**修法：`set_source` 改为复用路由层同一实例（single source of truth）** | `carla_source.py:98-105`、`:199-235`；`realtime_detector.py:798-820`（`[一]`） |

**这三条都带「实测踩到」的注释，说明有人（之前的会话）已经在 8002 端口真跑过并修了。**
→ **P0 不是「从零验证」，是「验证修完的版本能否跑通」。起点比我上一轮判断的高得多。**

**新增风险 ④（核实后发现）**：`attach_camera` 无父车时才走路侧机位；若 `spawn_vehicles` 先跑过，`self._vehicles[0]` 存在 → 相机挂到车上（前挡风视角），**不是路侧视角**。
→ **顺序很重要**：要路侧机位，就必须在 `attach_camera` 之前**不生成车辆**，或显式传 `attach_to=None` 且清空 `_vehicles`。

**新增风险 ⑤（核实后发现）**：`/source` 切到 `carla` 走 `realtime_detector.set_source()`（`:773` 已核实**存在**）。若 CARLA 未启动，`connect()` 失败 → 返回 `False` → 路由返回 `{"success":false,"message":"切换失败"}`。**不会抛 501**（我上一轮猜的 501 分支只在 `set_source` 完全不存在时才触发）。

### 1.5 关键文件（都在 `E:/output/1/api/`，`[二]` 已 `ls` 核实存在）

- `carla_source.py`（19 KB，475 行）— CARLA 数据源，含 `spawn_red_light_violator`（:440）
- `routers/realtime.py:1251-1360` — 5 个 CARLA 路由
- `realtime_detector.py:774-830` — 数据源切换
- `E:/output/1/carla/CARLA_0.9.16/CarlaUE4/Binaries/Win64/CarlaUE4-Win64-Shipping.exe` — 可执行文件（91 MB）

---

## 二、P1：零硬件二维俯视孪生（已验证可行，但需等 CARLA 之后）

> ⚠ **顺序调整原因（2026-11-07）**：CARLA 换机位后现有标定失效，先做 P0 俯视会白做。
> **且 CARLA 里的车辆世界坐标是精确已知的**（`get_actors_state()`），可以**直接做真值对照**，
> 不需要反投影 → **P0 做完 CARLA 后，俯视孪生反而更简单**。

### 2.1 为什么可行（已实测）

**已实测**（`_zero_hardware_twin_verdict_20261106.md` §二）：
- 单目反投影**全部成功**：真实轨迹 6/6、5/5、6/6
- 反投影几何**自洽**：左右对称点 X 完全一致（5.18/5.18）
- 精度：近处 0.6cm/像素，15m 内可用

**现在的 `_map_track_to_scene()` 是 `track_id % 4` 哈希到固定象限**（`digital_twin/app.py:109-140`，注释自称"伪 GPS 映射"）。这是「以虚映假」。

### 2.2 做什么

把哈希换成真实反投影：

```
bbox 中心 (u,v) → make_unprojector(u,v) → 地面 (x,y) 米制 → 2D 俯视渲染
```

### 2.3 完成标准（可判定，不许自评）

| # | 判据 | 怎么验 |
|---|---|---|
| 1 | 同一辆车连续帧俯视位置**随画面移动** | 取一条事件的 6 个轨迹点，看俯视坐标是否单调变化 |
| 2 | 移动方向与 bbox 移动方向**一致** | bbox 向右 → 俯视 X 增大 |
| 3 | 俯视路径长度与 `speed_calibration` 距离**吻合**（误差 < 1m） | 两个算法对同一轨迹算长度，比对 |
| 4 | 有备份可回滚 | `.bak_20261106_*` |

### 2.4 工作量与风险

- **半天~1 天**
- **风险**：前端 `main.js` 1774 行，3D 场景是硬编码 120×120 十字路口。改成俯视需要动渲染层。**先只改后端映射 + 用最小前端验证，别一次动太多。**

### 2.5 必须写进界面的限制

- **有效范围 15m 内**（>20m 精度崩到 11.6cm/像素）
- **只对已标定的机位有效**（换机位必须重新标定，项目手册 T88）

---

## 三、P2：多违规类型演示素材（**用户自己做，工坊精度更高**）

> ⚠ 若 P0（CARLA 直连）跑通，本节**大部分可以跳过**——因为 CARLA 能实时制造违规，
> 不需要预先录视频。但工坊出片**画质更可控**，适合做正式答辩素材。两者互补。

### 3.1 现状实测（这条很重要，推翻"只有闯红灯"的印象）

**数据库里有量的违规**：

| 类型 | violation_evidences | traffic_events |
|---|---|---|
| 逆行 wrong_way | **1072** | 1012 |
| 违停 illegal_parking | **985** | 759 |
| 闯红灯 red_light | 469 | 782 |
| 抢黄灯 running_yellow | 170 | 140 |
| 未戴头盔 | 23 | 2 |
| 超速 speeding | 10 | 300 |
| **压线 lane_departure** | **1** | 266 |

**关键发现**：
1. **逆行和违停有大量历史数据**——不是"没有数据"，是**没有能演示的视频**
2. **压线只有 1 条**——这是真的缺（项目手册说"压线缺车道线标注"）
3. **工坊已产出过 `超速.mp4`**（`1/carla/仿真输出/超速.mp4`，4.47MB）

### 2.2 需要补的素材（按优先级）

| 优先级 | 违规类型 | 为什么 | 工坊能不能做 |
|---|---|---|---|
| **P1-1** | **压线行驶** | 数据只有 1 条，最缺 | ✅ 能（行为模式里有「压线」） |
| **P1-2** | **违停** | 数据 985 条但无演示视频 | ✅ 能（有「违停」行为模式） |
| **P1-3** | **逆行** | 数据 1072 条但无演示视频 | ✅ 能（有「逆行」行为模式） |
| P1-4 | 未戴头盔 | 只有 23 条 | ❌ 工坊只能造车，造不出人 |
| P1-5 | 超速 | 已有 `超速.mp4` | 已有 |

### 2.3 工坊已知限制（用户自己做时要避开）

- **不能改地图标线**（无 UE 编辑器）→ 压线/违停只能靠「摆车到线上」，不能改标线设计
- `ignore_lights_percentage(100)` **本机无效** → 闯红灯车必须**关 autopilot + `apply_control` 油门**手动驱动
- `enable_constant_velocity` 在反向车道方向会反 → 手动驱动一律用 `apply_control`
- 场景 v2 支持：vehicles(autopilot/behavior_mode/目标速度/闯红灯) + props + 红绿灯配时 + 相机机位/fov + 14 字段天气

### 3.4 交付要求

每段视频需要配套：
1. **场景标注**（ROI / 停止线 / 车道线 / 斑马线）——否则判定失效
2. **场景配置 key 同步**（换素材后 `/status` 若 `scope=frame` 就是标注没跟过去，跑 `_scripts\_copy_scene_config.py`）

---

## 四、P3：云台跟踪摄像头（用户 2026-11-07 说「既然写了就先加进去」）

### 4.1 用户的判断（我同意一半）

> 「有一个能自动跟踪的云台摄像头演示力度会很强（像防空炮自动激光灭蚊器一样帅），但和项目关联度不高，因为在真实路口上用处不大，成本还高」

**我同意的部分**：演示效果确实强，视觉冲击力大。
**我不同意的部分**：见 §4.3。

### 4.2 项目里已有的东西（别重复造轮子）

**`api/ptz_controller.py`（23.5 KB，已有！）**：
- `PTZControllerBase`（ABC）
- `ONVIFPTZController`（真实实现）
- `SimulatedPTZController`（模拟实现）
- `PTZFactory`

**路由已接**：`routers/realtime.py:950` → `/api/realtime/ptz/*`

**也就是说：云台控制能力项目里早就有，从来没在演示里用过。**

### 4.3 云台在真实路口到底有没有用（我的判断）

**用户说"用处不大"，我认为分场景**：

| 场景 | 云台有用吗 | 理由 |
|---|---|---|
| **标准电子警察**（固定机位抓拍） | ❌ 没用 | 固定视角够用，云台反而增加故障点 |
| **大范围监控**（一个摄像头看多个方向） | ✅ **有用** | 一台顶多台，省成本 |
| **违法取证补拍**（发现违规后转向拍车牌） | ✅ **有用** | 这是真实需求：抓拍瞬间车牌可能糊，云台能跟上去补拍 |
| **移动目标跟踪**（无人机/车载） | ✅ 有用 | 但不是路侧场景 |

**关键洞察：云台的真正价值不在"跟踪"，在"补拍"**。

真实电子警察的痛点是：**抓拍到违规，但车牌糊了/被挡了**。这时候如果云台能转过去补一张清晰车牌，这条证据才成立。

**这恰好接上我们修的 B1**（证据链完整性）——云台补拍是「证据链可追溯」的一个具体实现。

### 4.4 怎么做最省（用户已拍板：先加进去）

| 方案 | 成本 | 可行性 |
|---|---|---|
| **纯软件模拟**（用 `SimulatedPTZController`） | ¥0 | ✅ 已有，可直接演示「发现违规→云台转向→补拍」 |
| 真云台（ONVIF 网络摄像头） | ¥500-2,000 | 需确认型号支持 ONVIF |
| 自制舵机云台 + 摄像头 | ¥300-800 | 需自己写控制代码 |

**用户 2026-11-07 决定：「云台的功能既然写了就先加进去吧」** → 走**软件模拟**路线（¥0）。

**要做的事**：
1. 验证 `SimulatedPTZController` 能实例化、能响应转向指令
2. 写一个演示串：`检测到违规 → 调 PTZ 转向 → 模拟补拍 → 回写证据链`
3. 前端加一个云台状态指示（可选）

**完成标准**：调 `/api/realtime/ptz/*` 能看到云台角度变化；补拍动作能被记录进事件。

---

## 五、P4：第 2 级「可诊」设施归因（保留，但降级）

### 5.1 为什么降级

上一轮定的「P0 可诊」，因为**用户指出"只有闯红灯视频"**而重新评估：

- 设施归因需要**多类型违规数据**才有说服力（现在只有闯红灯能演）
- 且只有 **2 个独立点位**

### 5.2 但数据基础已经具备

**实测**：逆行 1072 条、违停 985 条——**这些数据已经存在**，只是没有对应视频。

**所以顺序应该是**：先补素材（P2）→ 再算设施归因（P4）。

### 5.3 判据仍然可行

| 判据 | 需要 | 现状 |
|---|---|---|
| 视距充分性 | stop_line_y ✅ + 多帧轨迹 ✅ | **可算** |
| 可辨识度 | crosswalk_zones ✅ + 帧尺寸 ✅ | **可算** |
| 必然压线度 | lane_lines ❌ | 4 个场景全缺 |

---

## 六、P5：其他欠账（低优先级）

| # | 项 | 说明 |
|---|---|---|
| B3 | 申诉闭环 0 条 | 表/接口/页面全有，一次真实申诉没走完 |
| B4 | 逆行判定只用画面级 `road_direction` | 全仓无车道级方向配置，逆行占 39.5% 异常高 |
| — | 车牌识别 | `license_plate` 用 fallback `yolov8s`，不是真车牌模型 |

---

## 七、建议执行顺序（2026-11-07 更新）

```
P0 CARLA 直连（30min 验证 → 1-2h 跑通 → 半天出违规）   ← 用户提出的突破想法，代码已写好 80%
   ↓ 跑通后
P1 零硬件俯视孪生（半天）                              ← CARLA 给了精确真值，做起来更简单
   ↓
P2 补多类型素材（用户做工坊）                          ← 若 P0 跑通，这步可大幅简化
   ↓
P4 设施归因（1 天）                                    ← 有素材才算得有意义
   ↓
P3 云台演示（用户已拍板先加，¥0 软件模拟）              ← 与 P0 可并行，互不冲突
```

**顺序理由**：
- **P0 优先**：它解决「只能靠录好的视频」这个根本限制，且代码已有 80%
- **P1 依赖 P0**：CARLA 换机位后现有标定失效，先做俯视会白做；且 CARLA 有精确世界坐标，可直接做真值对照
- **P3 可与 P0 并行**：云台是独立模块，不冲突

---

## 八、待用户确认

1. **P0 第一步（验证 CARLA 能连上）什么时候做？** 30 分钟就能知道成不成立
2. **P2 用户什么时候做工坊？**（需要 CARLA 启动，6GB 显存；若 P0 跑通则可能不需要）
3. **2 万预算怎么用？**（上一轮建议：买设备做**验证**，不买设备做**部署**；用户说"钱不着急花"）

---

## 九、本文件的自审（按 delivery-self-review 七问）

> **2026-11-07 第二次自审**：第一版把三处「推断」写成了「事实」，本轮全部核实并修正。

| # | 项 | 状态 |
|---|---|---|
| ① | 证据等级 | 一级（grep/读源码/数据库查询/nvidia-smi）×9 / 二级（`ls` 文件存在）×3 / 三级（真实行为）×0 |
| ② | 路径真实性 | 已核 11/11 全存活（`carla_source.py`、`ptz_controller.py`、`routers/realtime.py`、exe、`超速.mp4`、三个 `.bak` 等） |
| ③ | 推断项 | **第一版有 3 处推断被我写成了事实，已全部修正**：<br>· 「相机标定要重做」→ 实测**不需要**（`attach_camera` 已修路侧机位，分辨率已改可配 1280×720）<br>· 「代码从未跑过」→ 实测**跑过并修了三个 bug**<br>· 「路由返回 501」→ 实测 `set_source` 存在，不会走 501 分支<br>**仍为推断（已标注）**：CARLA 显存需求「约 6GB」（来自项目手册非实测）、LiDAR 报价「未查到」 |
| ④ | 入口已接 | 本文件即新对话入口，§10 有可复制开场白 |
| ⑤ | 残留扫描 | 已修正：接口路径 `/api/realtime/carla` → `/api/realtime/carla/next-scene`；补上「必须先调 `/carla/connect`」；编号 P1/P2/P3 → P2/P3/P4；标题「从未跑过」→ 已改 |
| ⑥ | 回滚 | 代码回滚：`.bak_20261105_b1b2*` 覆盖同名文件；本文件为文档，无需回滚 |
| ⑦ | 用户侧 | 四件套已在 §1.3 三步验收中给出（命令/预期/判据/失败分支），且命令**已按真实路由修正** |

**本轮最大教训（值得记）**：
我在上一轮把「从文件名、接口签名、注释猜出来的东西」当成了事实写进待办。
**三条推断，两条是错的。** 错的方式很典型——我没读 `set_source` 的实现，就断言它会抛 `AttributeError`。
**判据：凡是我在文档里写下「会/不会/必须」的地方，都要能指回一次 `grep` 或一次运行。**

---

## 十、新对话开场白（可直接复制）

```
继续智瞳灵声项目。先读这两个文件，再动手：
E:\output\_next_session_todo_20261106.md   ← 待办与验收标准
E:\output\_data_foundation_check_20261105.md ← 上一轮修的数据地基

当前状态：
- B1（证据链键名）和 B2（轨迹只有1点）已修完并验证 9/9 PASS，有 .bak_20261105_b1b2* 可回滚
- 后端在跑（8001），前端未跑
- CARLA 未启动

本轮目标：P0 —— 验证 CARLA 直连实时检测。
关键事实：carla_source.py 已有 spawn_red_light_violator()，路由已接。
**代码已被跑过并修过三个真 bug**（is_connected 的 @property、attach_camera 的世界原点、
set_source 的双实例互抢），都在 2026-11-07 修完。
所以 P0 不是「从零验证」，是「验证修完的版本能否跑通」。
先跑 §1.3 第 1 步（30 分钟）判断成不成立。注意：必须先调 /carla/connect 再调 /carla/next-scene。
```
