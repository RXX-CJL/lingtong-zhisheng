# 任务单：智瞳灵声 · P1 攻坚（交给 WorkBuddy K3.1-Pro）

> **你（WorkBuddy）要独立完成，不需要等人回答。**
> 所有验收判据都写成了「可自己跑命令判定」，做完自己验，验过才算完。
> 遇到文档与实际代码不一致时：**以代码和实测为准**，不要相信文档里的说法。

---

## 0. 开工前必做（顺序不能乱）

### 0.1 先读这 3 个文件（只读，别改）

```
E:\output\_py312_migration_verdict_20261107.md      ← 上一轮结论（3.12 迁移 + OCR，已 PASS）
E:\output\_next_session_todo_20261107.md            ← 待办（**从第 238 行「2026-11-07 02:00 增补」开始读**，前面已过期）
E:\output\1\api\carla_source.py                     ← CARLA 数据源（本次主战场之一）
```

### 0.2 环境现状（2026-11-07 07:25 实测，可能已变，自己再确认）

| 项 | 状态 |
|---|---|
| 后端 8001 | **已停止**（需要你自己拉起） |
| CARLA 2000 | **已停止**（需要你自己拉起） |
| 前端 5173 | **已停止**（本次任务用不到） |

### 0.3 把服务拉起来

**Python 解释器（必须用这个，别用别的）：**
```
C:\Users\ROG\AppData\Local\Programs\Python\Python312\python.exe
```

**① 启动 CARLA**（约 6-7GB 显存，启动后等 20 秒）：
```bash
cd "E:/output/1/carla/CARLA_0.9.16/CarlaUE4/Binaries/Win64"
./CarlaUE4-Win64-Shipping.exe -carla-rpc-port=2000 -quality-level=High -nosound \
  -windowed -ResX=1280 -ResY=720 -benchmark -fps=20 &
```
⚠️ **不要用 `-quality-level=Epic`**，实测跑 10-15 分钟后进程会消失。

**② 启动后端 8001**（三个 `PADDLE_PDX_*` 变量必须带，否则车牌 OCR 起不来）：
```bash
cd E:/output/1
export PYTHONPATH="E:/output/1/api;E:/output/1"
export YOLO_IMGSZ=960 FRAME_RATE=6 \
       YOLO_MODEL_SEQUENCE="vehicle,traffic_light,helmet,lane" BOX_PREDICTION=1
export PADDLE_PDX_CACHE_HOME="F:/AI/paddlex_cache"
export PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT="False"
export PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK="True"
"C:/Users/ROG/AppData/Local/Programs/Python/Python312/python.exe" -u -m uvicorn app:app \
  --host 127.0.0.1 --port 8001 > E:/output/_tmp/wb_backend.log 2>&1 &
```

**③ 确认起来了**（两条都必须 200）：
```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8001/health
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8001/api/realtime/carla/status
```
> 第二条是**判断跑没跑在 3.12 的硬判据**：`carla` 模块只有 3.12 能导入，3.11 上这条必返 500。

---

## 任务一（最难 · 优先做）：让「闯红灯」真的被判成 `red_light`

### 现状（已实测确认，不是猜）

`api/carla_source.py` 的 `spawn_red_light_violator()` 现在只做两件事：

```python
actor.set_autopilot(False)
control = carla.VehicleControl(throttle=1.0, steer=0.0, brake=0.0)
actor.apply_control(control)
```

**问题**：车的朝向由随机 spawn point 的 yaw 决定，**不一定朝着红灯**。
所以实测结果是判出 `running_yellow` 和 `speeding`，**从来没有 `red_light`**。

### 已知的硬约束（实测过，别再试）

| 做法 | 实测结果 |
|---|---|
| `tm.ignore_lights_percentage(veh, 100.0)` | **本机无效**，车照样等红灯 |
| `traffic_light.set_green/yellow/red_time()` | **无效**，必须逐 tick `set_state()` |
| 硬编码 `spawn_points[0]` | 已被 `spawn_vehicles` 占死，静默返回 None |

### 你要做的

让车**真的朝红灯方向开过停止线**，并被判成 `red_light`。

**关键事实（项目手册实测，直接信）：**
- CARLA 重启后**红绿灯 Actor ID 会变** → 不能硬编码 ID，要按**停止线地理坐标**找灯
- 灯态只能用 `set_state()` 逐 tick 设
- 投射 API 返回的是 `carla.LabelledPoint`，不是 `Location`（`getattr(x, "location", x)`）
- 新 spawn 的 actor **下一次 tick 前 `get_transform()` 返回 `(0,0,0)`** → 先 `world.wait_for_tick()` 再读
- `world.get_actor(id)` 对已销毁 actor 仍返回 stale 代理 → 判存活用 `world.get_actors().find(id)`

### 验收判据（自己跑，必须全过）

```bash
B=http://127.0.0.1:8001/api/realtime
# 1) 连 CARLA
curl -X POST $B/carla/connect
# 2) 切源（BUG-3 回归点：source_type 必须保持 carla，不能变成 camera）
curl -X POST $B/source -H 'Content-Type: application/json' -d '{"source_type":"carla"}'
curl -X POST $B/start  -H 'Content-Type: application/json' -d '{}'
sleep 40   # 等 warmup，首次单模型约 10 秒
# 3) 造违规
curl -X POST $B/carla/next-scene -H 'Content-Type: application/json' -d '{"scene":"violation"}'
sleep 60
# 4) 不查 /events，直接查库（这是任务二的判据，一起验）
"C:/Users/ROG/AppData/Local/Programs/Python/Python312/python.exe" -c "
import sqlite3, json
c = sqlite3.connect(r'E:/output/1/api/zhitong_violations.db')
for r in c.execute('select id,event_type,evidence_chain from traffic_events order by id desc limit 5'):
    d = json.loads(r[2]) if r[2] else {}
    print(r[0], r[1], '灯态=', d.get('traffic_light_state'), '轨迹=', len(d.get('trajectory') or []), '点')
"
```

**PASS 条件（缺一不可）：**
1. 数据库里出现 `event_type = red_light` 的新记录
2. 该记录 `traffic_light_state = 'red'`（不是 yellow / None）
3. 该记录 `trajectory` 长度 ≥ 3
4. 整个过程 `source_type` 保持 `carla`（不能变成 `camera`）

**FAIL 时**：写清你试了什么、实测到什么，不要改判据凑通过。

---

## 任务二：事件落库改成「事件驱动」

### 现状（已定位到行）

`api/routers/realtime.py:1359` 定义了 `_sync_active_events_to_db()`，
但它**只在两处被调用**：

```
api/routers/realtime.py:1435   ← GET /events 列表查询时
api/routers/realtime.py:1746   ← 另一处查询
```

**⚠️ 2026-11-07 07:37 修正（WorkBuddy 提出、我核实成立）**：

上面这个描述**是错的**。真实情况：

```
traffic_event_engine.py:402   self._persist_event(event)   ← 事件创建时（TRIGGERED）
traffic_event_engine.py:592   self._persist_event(event)   ← _update_event_state() 内部，每次状态流转
```

`_persist_event()` 用 `event_id` 做 upsert 键，**任何状态流转都直接写库**。
所以「事件驱动落库」**早就有了**，`_sync_active_events_to_db()` 只是另一条兜底路径。

**我错在哪**：上一轮我查库的时机在事件确认之前，看到没数据就判定「不查列表就不写库」——
是**采样时机错**，不是代码错。

**所以本任务不重写，只找真缺口**：重点验 `_persist_event()` 失败时会不会被 `except` 静默吞掉
（名义上有、实际没落库才是真 bug）。

### 你要做的

**不要重写。** 保持 `_persist_event()` 现有链路。
先核实 `_persist_event()` 的失败路径是否被 `except` 静默吞掉 —— **那才是要查的真缺口**。
发现缺口才修，没缺口就如实记「无需改动」。

### 验收判据

**造完违规后，一次都不调用 `/events`**，直接查数据库，必须有新记录。

用任务一的那段 sqlite 命令即可 —— **注意：脚本里绝不能有 `curl .../events`**。
这一条把两个任务串在一起验：如果任务一 PASS 而这条 FAIL，说明落库还是被动的。

---

## 任务三：CARLA 相机标定重做（1280×720）

### 现状

- 检测用 **1280×720**
- 现有标定是 **1920×1080** 的
- → 反投影、测速**现在全是错的**

### 机位（已实测可用，直接用）

```
位置  x=-15.720  y=-63.145  z=5.732
姿态  pitch=-23.445  yaw=179.536  roll=0
相机高度 camera_height_m = 5.0（离路面高度，不是 z）
```

这个机位在 Town10HD_Opt 上画面正确：斑马线居中、停止线在下 1/3、8 盏红绿灯、路口全景。

### 你要做的

在这个机位 + 1280×720 上重新标定：

- `stop_line_y`
- `crosswalk_zones`
- `lane_lines`
- `pixel_per_meter`

**标定文件的落盘位置由 `api/scene_annotation.py` 的 `_path_for()` 决定**（第 99 行），
读那个函数自己算路径，**不要自己发明路径**。

### 验收判据

1. 标定文件真实存在，且含上述 4 个字段（用 `python -c "import json;print(json.load(open(...)).keys())"` 验证）
2. 用 1280×720 的一帧 CARLA 画面，`stop_line_y` 落在画面**下半部分**（y 在 360~720 之间）
3. 画面上叠加画出停止线 + 斑马线 + 车道线，**截图存盘**，人眼能看出线压在正确位置
4. 测速：让一辆车匀速开过，`speed_calibration` 算出的速度与 CARLA 真值
   （`GET /api/realtime/carla/actors` 里的 `velocity`）**误差 < 20%**

---

## 任务四（收尾必做）：写交接报告

新建 `E:\output\_wb_p1_report_20261107.md`，必须包含：

| 节 | 内容 |
|---|---|
| 一、三个任务各自的结果 | PASS / FAIL，**贴真实命令输出**，不要只说「完成了」 |
| 二、改了哪些文件 | 路径 + 行号 + 改了什么，**每个文件都要有 `.bak_20261107_wb` 备份** |
| 三、被推翻的旧结论 | 你实测发现哪些文档说法是错的 |
| 四、没做完的 | 卡在哪、试过什么、下一步建议 |
| 五、可复跑命令 | 让下一个人能一键复现你的验证 |

---

## 硬性纪律（违反等于没做）

1. **每个改动的文件都要先备份**成 `<文件名>.bak_20261107_wb`
2. **`.bat` 文件里不许出现中文**（cmd 用 GBK 读，中文会吃掉后面命令）——
   本次任务如果不需要改 bat，就别动
3. **报告里的每个数字都要能指回一条能重跑的命令**，不许凭感觉写
4. **不要改 `.paddlex` 目录的权限**（已用环境变量绕过，别再动 C 盘 ACL）
5. **不要动 `E:\output\_dual_cam_demo\` 里的演示素材**
6. 说「完成」必须带证据（命令输出 / 文件状态 / 真实行为），三级证据优先
7. **任务一如果确实做不到**（比如 CARLA 本身限制），**如实写 FAIL + 你的实测证据**，
   不要改判据凑 PASS。FAIL 也是有价值的结论。

---

## 参考：真实 CARLA 路由（文档里写过的不对，以这个为准）

| 路由 | 说明 |
|---|---|
| `GET  /api/realtime/carla/status` | 连接状态 |
| `POST /api/realtime/carla/connect` | 连接 |
| `POST /api/realtime/carla/spawn` | `{"vehicles":15}` → 14 车 + 10 行人 |
| `POST /api/realtime/carla/next-scene` | `{"scene":"violation"}` |
| `GET  /api/realtime/carla/actors` | 车辆/行人/红绿灯 + **真实世界坐标** |

## 参考：两个 Python 环境的真实差异（实测）

| 包 | 3.11 | 3.12（要用这个） |
|---|---|---|
| `carla` | ❌ 无 | ✅ 0.9.16 |
| `ultralytics` | 8.4.103 | 8.4.35（检测结果逐类一致，无影响） |
| `opencv` | 5.0.0 | 4.10.0（**4.10 更好**：5.0 上车道线检测必崩） |
| `hyperlpr3` | 0.1.3 | 0.1.3 |
| `paddleocr` | ❌ 无 | 3.7.0 |
