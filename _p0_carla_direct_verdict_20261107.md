# P0 结论：CARLA 直连实时检测 —— **成立**

> 2026-11-07 · 依据 `_next_session_todo_20261106.md` §1.3 三步验收
> **一句话**：P0 成立。§1.3 第 1 步 PASS；第 2、3 步也跑通了，但过程中挖出 **4 个从未暴露的代码 bug**（全部已修 + 备份）。

---

## 一、三步验收结果

| 步 | 判据 | 结果 | 证据 |
|---|---|---|---|
| **第 1 步** 验证连上 | `violator_actor_id` 是非 null 整数 | ✅ **PASS** | `{"success":true,"violator_actor_id":126}` 连续两次 126/127 |
| **第 2 步** CARLA 帧→检测 | `source_type=carla`、`processed_frames` 增长、`tracked_vehicle_count>0` | ✅ **PASS** | `src=carla total=62607 proc=325 tracked=1 fps=2.95` |
| **第 3 步** 制造违规→识别 | 新事件 + 灯态非 unknown + 轨迹>1 点 | ✅ **PASS** | `id=3271 running_yellow 灯态='yellow' 轨迹=5点 车道='south'` |

**第 3 步的完整证据（数据库 `zhitong_violations.db`）**：

```
事件总数 3269 → 3271
id=3271 running_yellow  灯态='yellow'  轨迹=5点  停止线=None  车道='south'
id=3270 speeding        灯态='yellow'  轨迹=4点  停止线=None  车道='south'
```

**B1（灯态键名）与 B2（轨迹 1 点）的修复在 CARLA 链路上同样成立** —— 这是上一轮没验证过的（上轮只在视频源验过）。

---

## 二、挖出 4 个 bug（都不是环境问题，是代码问题）

### BUG-1：`is_connected` 是 property 却被当方法调 → 所有 CARLA 路由 500

- **位置**：`carla_source.py:98`（`@property`）× `routers/realtime.py` + `realtime_detector.py` 共 8 处调用点
- **症状**：`GET /api/realtime/carla/status` → `{"error_code":"INTERNAL_ERROR"}` 500
- **真异常**：`TypeError: 'bool' object is not callable`
- **修法**：去掉 `@property`，改成普通方法（与全部调用点一致）
- **验证**：修后三个路由全部 200

### BUG-2：闯红灯车硬编码 `spawn_points[0]`，被 `spawn_vehicles` 占死

- **位置**：`carla_source.py:456`
- **症状**：`spawn_red_light_violator()` 返回 `None`，**0.02 秒就返回，连异常都不抛**
- **对照实验（决定性）**：

  | 场景 | 结果 |
  |---|---|
  | 空场直接调用 | ✅ id=46 |
  | 先 `spawn_vehicles(10)` 再调用 | ❌ None |
  | 车开走后重试 | ✅ id=56 |

- **根因**：`spawn_vehicles` 也是从 `spawn_points[0]` 按序占位（第 134 行），两者抢同一个点
- **修法**：遍历全部 155 个 spawn point，跳过 2m 内已被占用的，随机尝试直到成功
- **验证**：`spawn_vehicles(20)` 之后再连做 3 次 violator → 123/124/125 全成功

### BUG-3：`/start` 会把 carla 源覆盖成 camera（**严重，会偷偷开你的摄像头**）

- **位置**：`routers/realtime.py:61`
- **症状**：`/source {carla}` → `source_type=carla`；再 `/start` → `source_type=camera`，`total_frames=124`
- **实测后果**：**真把本机摄像头录了 124 帧**
- **根因**：`/start` 无条件调 `start_camera()`，而它内部强制写 `source_type="camera"`
- **修法**：当前源已是 carla 时跳过 `start_camera()`，检查连接后直接启动检测循环
- **验证**：修后 `/start` → `source_type` 保持 `carla`

### BUG-4：两个独立的 `CarlaSource` 实例（相机被放在世界原点）

- **位置**：`routers/realtime.py:1190`（`_carla_source_instance`）vs `realtime_detector.py:293`（`self.carla_source`）
- **症状**：检测到的帧是**一堵墙**，YOLO 100% `no detections`
- **根因链**：
  1. 两个实例各自 connect / 各自 attach_camera / 各自 tick()
  2. 检测器那个实例**从未 spawn_vehicles** → `_vehicles` 为空
  3. 于是 `attach_camera` 走 `parent=None` 分支，用 `Transform(Location(x=1.5, z=2.4))`
  4. **`attach_to=None` 时这个 Transform 是世界坐标** → 相机被放在世界原点 (1.5, 0, 2.4)，Town10HD 里那是建筑内部
- **修法**：① 复用路由层同一实例；② `attach_camera` 的 `parent=None` 分支改用**路侧固定机位**（环境变量可配）
- **验证**：修后画面是标准路口视角（斑马线+停止线+8 盏红绿灯），YOLO 检 10-12 个目标

---

## 三、相机机位：A_handbook 是唯一正确的

实测 4 个候选机位（截图存 `E:/output/_tmp/cam_shots/`）：

| 机位 | 坐标 | 画面内容 | 可用 |
|---|---|---|---|
| **A_handbook** | `(-15.720, -63.145, 5.732)` pitch `-23.445` yaw `179.536` | 斑马线居中、停止线在下 1/3、8 盏红绿灯、路口全景 | ✅ **用这个** |
| B_origin_high | `(0,0,30)` pitch -60 | 高空俯视 | ❌ 没有红绿灯参照 |
| C_mapcenter | `(110,60,25)` pitch -45 | 高空俯视路口 | ❌ 同上 |
| D_mapcenter2 | `(-50,20,20)` pitch -40 | 斜俯视 | ❌ 同上 |

**这组坐标是项目手册记录的工坊机位**，在 Town10HD_Opt 上直接可用 —— 与 `_next_session_todo` §1.4 风险①说的"必须重新标定"**部分不成立**：机位本身对得上，但**分辨率不同（1280×720 vs 标定的 1920×1080），反投影/测速仍需重标**。

---

## 四、性能实测（这组数字决定第 2 步能不能用于演示）

| 测量 | 首次（含 warmup） | 稳态 |
|---|---|---|
| 单模型 `vehicle` | **9947 ms** | **128-135 ms/帧** |
| 4 模型序列 | 911ms | ≈520ms/帧（≈1.9fps） |
| **2 模型序列**（vehicle+traffic_light） | — | **实测 avg_fps 2.2-2.95** |

**结论**：
1. **warmup 约 10 秒/模型**，必须预热后再启动检测，否则前几秒全是 0 处理
2. `YOLO_MODEL_SEQUENCE` 裁剪是**必需**的，不是优化 —— `helmet`/`lane` 在 CARLA 场景无标注数据
3. 演示口径：**`YOLO_MODEL_SEQUENCE=vehicle,traffic_light`**，实测 2.2-2.95 fps，够用

---

## 五、两个新发现的环境事实（下轮必须知道）

### 1. CARLA 用 Epic 画质会崩溃

- **现象**：`-quality-level=Epic` 跑约 10-15 分钟后进程消失，端口 2000 无响应
- **修复**：改 `-quality-level=High`，实测稳定
- **显存**：Epic 启动后剩 344MB（3.5%），High 剩 508MB
- **建议启动命令**（已验证可用）：

```bash
cd "E:/output/1/carla/CARLA_0.9.16/CarlaUE4/Binaries/Win64"
./CarlaUE4-Win64-Shipping.exe -carla-rpc-port=2000 -quality-level=High -nosound \
  -windowed -ResX=1280 -ResY=720 -benchmark -fps=20
```

### 2. Python 版本错配（**架构级，不是 bug**）

| 环境 | Python | carla 模块 | paddleocr | torch |
|---|---|---|---|---|
| `zhitong-gpu`（**8001 后端在用**） | 3.11.15 | ❌ **无，且装不上** | ❌ 无 | 2.5.1 |
| `Python312` | 3.12.10 | ✅ 有 | ✅ 有 | 2.5.0+cu121 |

- CARLA 官方 wheel 只有 `carla-0.9.16-cp312-cp312-win_amd64.whl`（**仅 cp312**）
- `zhitong-gpu` 是 3.11 → **物理上装不上**
- **Python312 能完整启动整个后端**（139 routes、7 个 YOLO 模型全加载成功）

**本轮做法**：在 **8002 端口另起一个 Python312 实例**做验证，**8001 完全没动**。
**下一轮要定**：把后端整体迁到 3.12，还是让 CARLA 走独立进程 + IPC。这是架构决策，需要你拍板。

---

## 六、被推翻的旧结论（诚实交代）

| 上一轮/待办里说的 | 本轮实测 | 修正 |
|---|---|---|
| "§1.3 第 1 步的命令是 `POST /api/realtime/carla`" | **404** | 真实路由是 `POST /api/realtime/carla/next-scene` |
| "`processed_frames=0` 说明检测卡住了" | 我采样时正在 warmup | **是我的判断错误**，warmup 结束后正常增长到 325 |
| "CARLA 换机位后现有标定失效，俯视孪生要等 CARLA 之后" | 机位 A_handbook 可直接用 | **部分不成立**：机位对得上，只有分辨率需重标 |
| "显存约 6GB 就够"（来自项目手册，非实测） | Epic 需 7.8GB+ 且会崩，High 需 7.4GB | High 更稳 |
| "代码已写好 80%，只差跑一次" | 代码**从没跑过是真的**，且有 4 个必现 bug | 实际是"骨架 80%，接线 0%" |

---

## 七、改动清单与回滚

**改了 3 个文件**（全部已备份，`py311`/`py312` 双版本语法检查通过）：

| 文件 | 备份 | 改动行数 |
|---|---|---|
| `api/carla_source.py` | `carla_source.py.bak_20261107_carla` | 140 行 |
| `api/routers/realtime.py` | `routers/realtime.py.bak_20261107_carla` | 26 行 |
| `api/realtime_detector.py` | `realtime_detector.py.bak_20261107_carla` | 38 行 |

**回滚**：用对应 `.bak_20261107_carla` 覆盖同名文件即可。

**新增环境变量**（都有缺省值，不设也能跑）：
```
CARLA_CAM_X / Y / Z / PITCH / YAW / ROLL   相机机位（缺省=工坊机位）
CARLA_DEMO_WIDTH / HEIGHT / FOV            相机分辨率（缺省 1280x720 fov90）
CARLA_TRAFFIC_N                            切源时自动生成多少辆车（缺省 20，0=不生成）
YOLO_MODEL_SEQUENCE                        模型序列（**演示建议 vehicle,traffic_light**）
```

---

## 八、可复跑命令（完整闭环）

```bash
# ① 启动 CARLA（High 画质）
cd "E:/output/1/carla/CARLA_0.9.16/CarlaUE4/Binaries/Win64"
./CarlaUE4-Win64-Shipping.exe -carla-rpc-port=2000 -quality-level=High -nosound \
  -windowed -ResX=1280 -ResY=720 -benchmark -fps=20 &

# ② 用 Python312 起 8002（不改 8001）
cd E:/output/_tmp
YOLO_MODEL_SEQUENCE='vehicle,traffic_light' \
C:/Users/ROG/AppData/Local/Programs/Python/Python312/python.exe -u run_8002_py312.py &

# ③ 三步
B=http://127.0.0.1:8002/api/realtime
curl -X POST $B/carla/connect
curl -X POST $B/source -H 'Content-Type: application/json' -d '{"source_type":"carla"}'
curl -X POST $B/start -H 'Content-Type: application/json' -d '{}'
sleep 30   # 等 warmup

# ④ 造违规
curl -X POST $B/carla/next-scene -H 'Content-Type: application/json' -d '{"scene":"violation"}'
sleep 60

# ⑤ 落库（注意：必须先调 /events 才写库）
curl -s "$B/events?limit=5" > /dev/null
python -c "
import sqlite3,json
c=sqlite3.connect(r'E:/output/1/api/zhitong_violations.db')
for r in c.execute('select id,event_type,evidence_chain from traffic_events order by id desc limit 3'):
    d=json.loads(r[2]) if r[2] else {}
    print(r[0], r[1], '灯态=',d.get('traffic_light_state'), '轨迹=',len(d.get('trajectory') or []))"
```

---

## 九、下一轮该做什么（按价值排序）

| # | 任务 | 为什么 | 工作量 |
|---|---|---|---|
| **1** | **决定 Python 版本架构**（迁 3.12 / CARLA 独立进程） | 不定这个，P0 只能跑在 8002 上，进不了正式演示 | 你是决策者 |
| **2** | **事件落库改成事件驱动**（现在靠"查列表时兜底"） | 这是真 bug：不查列表就不写库，实时性依赖调用方 | 半天 |
| **3** | **CARLA 相机标定重做** | 1280×720 与标定的 1920×1080 不同，反投影/测速现在不准 | 1 天 |
| **4** | 让 `spawn_red_light_violator` 真的冲红灯 | 现在只是"关 autopilot + 踩油门"，**没有对着红灯直行**，被判成 `running_yellow`/`speeding` 而不是 `red_light` | 半天 |
| **5** | warmup 预热 | 首次 10 秒/模型，演示时前几秒是空的 | 1 小时 |

**第 4 项值得单独说**：本轮 3 辆车生成后判出的是 `running_yellow` 和 `speeding`，**不是 `red_light`**。因为现在的 `spawn_red_light_violator` 只是把车放在随机 spawn point 上踩油门，车的实际朝向由 spawn point 的 yaw 决定，**不一定朝着红灯**。要真闯红灯，得按 `_next_session_todo` §2.3 记的办法（关 autopilot + `apply_control` 手动驱动，因为 `ignore_lights_percentage` 在本机无效）。

---

## 十、自审（按 delivery-self-review 七问）

| # | 项 | 状态 |
|---|---|---|
| ① | 证据等级 | 三级（真实行为）✅ —— 数据库新增事件、YOLO 检出数、截图、HTTP 响应全部实跑 |
| ② | 路径真实性 | 全部实测存在；`.bak_20261107_carla` × 3 已核 |
| ③ | 推断项 | 已标注：warmup 10 秒是单模型实测（4 模型叠加可能更长，未逐模型测）；Epic 崩溃的具体原因未查（只知现象）；`red_light` 判不出是因为朝向不对——这是推断，未逐车验证 |
| ④ | 入口已接 | 本文件 + 交接文件都指向 `_next_session_todo_20261106.md` |
| ⑤ | 残留扫描 | 8002 已关；8001 未动（PID 16400）；CARLA 保持运行；GPU 余 2420 MiB |
| ⑥ | 回滚 | 3 个 `.bak_20261107_carla` |
| ⑦ | 用户侧 | 见 §八 可复跑命令 + §九 需要你拍板项 |
