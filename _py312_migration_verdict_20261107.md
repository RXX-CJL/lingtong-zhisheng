# 3.12 迁移验收 —— 结论

> 2026-11-07 · 依据 [`_next_session_todo_20261107.md`](_next_session_todo_20261107.md) §一
> **一句话**：迁移**完成并且 PASS**。8001 已跑在 Python 3.12.10 上，CARLA 直连在**正式端口**跑通。
> 途中推翻待办里两条"风险"判断（opencv 那次"倒退"实际是**修复**），挖出 **2 个真回归 + 2 个真 bug**（全部已修），
> 另发现 3 个待办没写的事实。
>
> **§十一 是后续新增的（OCR / hyperlpr3 部分），前面 §一~§十 是迁移验收本体。**

---

## 零、四条被本轮推翻的旧结论（先看这个）

| # | 原说法 | 实测 | 性质 |
|---|---|---|---|
| 1 | "opencv 5.x→4.x 是倒退，要盯" | **反了**：4.10 修好了 5.0 上的车道线崩溃 | 待办判断错 |
| 2 | "3.11 上有 PaddleOCR，可拿它比对精度" | 3.11 **从来没有** paddleocr | 待办事实错 |
| 3 | "Python312 能完整启动整个后端"（上轮 verdict） | 能启动，但 **OCR 起不来** | 上轮遗漏 |
| 4 | 迁移"不引入回归"（我一开始的乐观） | **引入了 1 个真回归**：`hyperlpr3` 缺失 | 我的判断错 |


## 一、四个必验项（逐项取证）

| # | 待办要求 | 结果 | 实测证据 |
|---|---|---|---|
| **1** | PaddleOCR 精度 | ⚠ **无法比对，且引擎当前起不来** | 见 §三 · 不是迁移造成的 |
| **2** | `ultralytics 8.4.35` 能否替代 `8.4.103` | ✅ **PASS** | 同一帧、同 4 模型，两版**逐类检测数完全一致**（22/21/20 检出，按类别计数 diff 为空） |
| **3** | 视频源回归 | ✅ **PASS** | `source_type=video` / `tracked_vehicle_count=2` / `avg_fps=1.67` / 检出 `2 cars, 6 traffic lights` |
| **4** | 既有回归基线 | ✅ **PASS（无新增回归）** | 见 §二 —— 待办点名的两个脚本**不存在**，改用真实存在的 11 个模块 |

### 待办里点名但**不存在**的脚本（R8 路径失效）

```
_scripts/_verify_hotreload_and_filter.py   ← 目录 _scripts/ 不存在（实为 scripts/）
_scripts/_verify_fixes_e2e.py              ← 同上
```
`find /e/output/1 -name "_verify*.py"` → **0 命中**。改用 `tests/` 下真实存在的 11 个模块做基线。

---

## 二、回归对照（3.11 vs 3.12，同一套代码）

```
module                                   3.11   3.12       delta
test_circular_frame_buffer               PASS   PASS        same
test_cloud_collaborator_event            PASS   PASS        same
test_evidence_chain                      PASS   PASS        same
test_event_lifecycle_safety              PASS   PASS        same
test_event_media_contract                FAIL   FAIL        same   ← 迁移前就坏
test_multi_frame_validator               PASS   FAIL   REGRESSED  ← 假阳性，见下
test_replay_sidecar_contract             PASS   PASS        same
test_task029_integration                 PASS   FAIL   REGRESSED  ← 假阳性，见下
test_timeline_metrics_contract           FAIL   FAIL        same   ← 迁移前就坏
test_traffic_event_engine                PASS   PASS        same
test_traffic_plugin_contract             PASS   PASS        same
```

### 两条"REGRESSED"经复核是**度量错误**，不是回归

`test_multi_frame_validator` / `test_task029_integration` 里全是**裸函数式** `def test_xxx()`
（pytest 风格），**没有 `unittest.TestCase` 子类**。`python -m unittest` 抓不到，
3.11 报 `Ran 0 tests ... OK`（rc=0 → 被我的脚本误判 PASS），
3.12 对"0 个测试"更严格，报 `NO TESTS RAN`（rc=5 → 被误判 FAIL）。

**按它们真正的运行方式重跑：**

| 模块 | 真实运行器 | 3.12 结果 |
|---|---|---|
| `test_multi_frame_validator` | 逐个调裸函数 | **14/14 PASS**（3.11 同样 14/14） |
| `test_task029_integration` | 自带 `main()` | **7/7 PASS**（`_TASK-029-M09_integration_selfcheck.json` 已写入） |

### 两个"迁移前就坏"的（与本次无关）

- `test_event_media_contract`：断言 `key_frames` 非空，历史事件里是 `[]`。3.11 失败 403 条、3.12 失败 431 条
  （差值来自数据库里事件变多，不是行为变化）。
- `test_timeline_metrics_contract`：3.11 与 3.12 **都**是 `failures=1, errors=10`，完全一致。

**结论：3.12 迁移新增回归 = 0。**

---

## 三、被推翻的旧结论（诚实交代）

### ❌ 待办说："`opencv 5.x → 4.x` 是倒退，要盯"

**反了。** 3.12 的 cv2 4.10 在项目代码上**比 3.11 的 5.0 更好**：

```
3.12 (cv2 4.10):  [B] LaneDetector.detect -> 18 lines  OK
3.11 (cv2 5.0) :  [B] LaneDetector.detect -> CRASH
                  cannot unpack non-iterable numpy.int32 object -> 0 lines
```

**根因**：`cv2.HoughLinesP` 返回值形状在 5.x 变了 —— `(N,1,4)` → `(N,4)`。
项目两处代码按 `(N,1,4)` 写（`scene_annotation.py:290` 的 `lines[:, 0]`、
`scene_perception.py:170` 的 `raw[0]`），在 5.0 上**必崩**。

实测两版形状：
```
3.12 cv2 4.10:  raw shape = (36, 1, 4)   两种写法都 OK
3.11 cv2 5.0 :  raw shape = (36, 4)      两种写法都 FAIL (IndexError / TypeError)
```

**所以 3.11（现 8001）的车道线检测一直是坏的，只是被 try/except 吞了。** 迁移顺带修好了它。

### ❌ 待办说："3.11 上有 PaddleOCR，可以拿它比对精度"

3.11 **从来没有 paddleocr**：
```
3.11: ModuleNotFoundError: No module named 'paddleocr'
3.12: OK 3.7.0
```
所以待办必验项 1"比对 3.11 的结果"**在字面上无法执行** —— 没有基线。

### ❌ 上一轮 verdict §五 说："Python312 能完整启动整个后端"

成立，但**漏了 OCR**。后端能启动 ≠ 所有能力可用，见下。

---

## 四、新发现：PaddleOCR 引擎在 3.12 上**起不来**（历史 ACL 问题，非迁移引起）

```
TYPE: PermissionError
STR : [Errno 13] Permission denied:
      'C:\Users\ROG\.paddlex\official_models\PP-LCNet_x1_0_textline_ori\inference.yml'
```

**逐个探测五个模型目录的可读性：**

| 模型目录 | 可读 |
|---|---|
| `PP-LCNet_x1_0_doc_ori` | ✅ READABLE |
| `PP-LCNet_x1_0_textline_ori` | ❌ PermissionError 13 |
| `PP-OCRv6_medium_det` | ❌ PermissionError 13 |
| `PP-OCRv6_medium_rec` | ❌ PermissionError 13 |
| `UVDoc` | ❌ PermissionError 13 |

**根因**：`C:\Users\ROG\.paddlex\official_models` 顶层 ACL 里有
`LAPTOP-QUTJ924T\CodexSandboxUsers:(I)(OI)(CI)(RX)` —— 一个沙箱账户组，
子目录继承了它的限制性 ACE，压掉了 `ROG` 的读权限。`icacls` 连列都列不出。

**关掉 `use_doc_unwarping` / `use_doc_orientation_classify` 也绕不过** —— 检测模型本身就不可读。

**影响**：车牌识别只能走 fallback（YOLO 通用模型 + 传统方法），OCR 精识别不可用。
这是 P5 欠账里"车牌识别用 fallback 模型"的**真实原因之一**。

**修法（需你确认，因为要改 C:\ 下的 ACL）**：
```powershell
# 只给当前用户 ROG 补读权限，不删除 CodexSandboxUsers 那条
icacls "C:\Users\ROG\.paddlex\official_models" /grant "ROG:(OI)(CI)F" /T
```
代价：改系统盘 ACL。风险：低（只加不删），但**我不动环境配置，等你点头**。

---

## 五、CARLA 在正式端口跑通了（迁移的真正目标）

| 检查 | 结果 |
|---|---|
| `POST /api/realtime/carla/connect` | `{"success":true,"connected":true}` |
| `POST /source {carla}` | `source_type=carla` |
| `POST /start` | **`source_type` 保持 `carla`**（BUG-3 回归 PASS，没变成 camera） |
| 检测循环 | `total_frames=238078` / `processed_frames=838` / `avg_fps=2.05` |
| `POST /carla/next-scene {violation}` | `violator_actor_id=49`、`50`（连续两次成功） |
| 画面 | 标准路口：斑马线居中、停止线、8 盏红绿灯（截图 `_tmp/cam_shots/py312_snap.png`） |

**上一轮 P0 只能跑在 8002 旁挂实例上，现在跑在 8001 —— 这是迁移的核心收益。**

### 新的真实路由名（待办与 verdict 里写的都不对）

| 实际路由 | 说明 |
|---|---|
| `GET  /api/realtime/carla/status` | 连接状态 |
| `POST /api/realtime/carla/connect` | 连接 |
| `POST /api/realtime/carla/spawn` | 生成车+行人（`{"vehicles":15}` → 14 车 + 10 行人） |
| `POST /api/realtime/carla/next-scene` | 造场景 |
| `GET  /api/realtime/carla/actors` | 车辆/行人/红绿灯列表 |

---

## 六、`tracked_vehicle_count=0` 的调查（三次假设，两次被我推翻）

**这是 P1 演示品质问题，不是迁移缺陷。** 调查过程如实记录：

| # | 假设 | 结果 |
|---|---|---|
| 1 | `vehicle_tracker.py:137` 用墙钟减视频时间 → 每帧清空 | ❌ **被推翻**：三组对照实验都稳定保留 `[1,1,1,1,1]` |
| 2 | 应该测 ByteTrack 分支（`use_bytetrack=True`）而非质心 | ❌ **被推翻**：A/B/C 三组都 `[1,1,1,1,1,1]` |
| 3 | **画面里确实没车** | ✅ **成立** |

**证据**：截图只见 2-3 辆车；YOLO 日志 `1 person, 1 bus, 2 traffic lights, 2 potted plants`；
`/carla/spawn` 生成 26 个 actor 后，`tracked_vehicle_count` 仍为 0。

**部分 actor 会消失**：日志显示"车流已生成 23 辆"，25 秒后只剩 2 辆，且**无销毁日志**。
这是 CARLA 侧行为（掉出世界/超时回收），未深挖，留 §七。

---

## 七、改动清单与回滚

| 文件 | 备份 | 改了什么 |
|---|---|---|
| `restart-backend.bat` | `.bak_20261107_py312` | `PYEXE` 搜索顺序改为 **Python312 优先**；加 `ZHITONG_PY` 覆盖；加解释器版本 + carla 可导入性自检 |
| `start-all.bat` | `.bak_20261107_py312` | 同上（`PYEXE` 顺序 + `ZHITONG_PY`） |

**判据验证**：
- Python312 行号 < zhitong-gpu 行号：`restart-backend.bat` 46 < 47；`start-all.bat` 86 < 87 ✅
- 两个 bat **纯 ASCII**（`grep -P '[^\x00-\x7F]'` 零命中）✅
- md5 证明备份与改前一致 ✅

**回滚**：
```bash
cd E:/output/1
cp restart-backend.bat.bak_20261107_py312 restart-backend.bat
cp start-all.bat.bak_20261107_py312 start-all.bat
# 然后用旧 bat 重启（会回到 3.11）
```

**当前 8001 是我用命令行直接起的**（不是 bat），PID 15920，日志在
`_tmp/py312_logs/backend_8001.log`。要恢复成 bat 管理：直接跑 `restart-backend.bat`
（它会先杀 8001 再用 3.12 起）。

---

## 八、自审（delivery-self-review 七问）

| # | 项 | 状态 |
|---|---|---|
| ① | 证据等级 | **三级**（真实行为）：CARLA 在 8001 上真跑、画面截图、数据库直查、两解释器对照实跑 |
| ② | 路径真实性 | 全部实测。**待办点名的两个 `_verify_*.py` 不存在，已如实标注** |
| ③ | 推断项 | 已标注：actor 消失原因**未查**（只知现象）；OCR 已在 §十一 补验并跑通 |
| ④ | 入口已接 | 本文件 + 更新后的待办 |
| ⑤ | 残留扫描 | 8001 在跑（3.12，PID 4724）；5173 在跑（PID 11296）；**CARLA 进程已消失（非我停止，原因未查，见 §十二）**；8002 未启动 |
| ⑥ | 回滚 | 两个 `.bak_20261107_py312` + 一个 `.bak_20261107_ocr` + 上一轮的 3 个 `.bak_20261107_carla` |
| ⑦ | 用户侧 | 见 §九 |

---

## 九、需要你拍板的（按影响排序）

| # | 事项 | 现状 | 我的建议 |
|---|---|---|---|
| **1** | `.paddlex` ACL | **已用官方支持的方式绕过**（`PADDLE_PDX_CACHE_HOME` 重定向到 F 盘），**没改 C 盘任何权限**。见 §十一 | 无需拍板，已完成 |
| **2** | `tracked_vehicle_count` 演示品质 | 真因是**画面里没车**（三次假设两次被我自己推翻） | 并到 §二 P1 第 2 项一起做 |
| **3** | **CARLA 进程消失** | 进程没了，非我停止 | 要我查吗？见 §十二 |

---

## 十、下一轮（待办 §二 原顺序，已确认可执行）

1. **事件落库改事件驱动**（真 bug：`_sync_active_events_to_db` 只在 `GET /events` 时触发）
2. 让 `spawn_red_light_violator` 真冲红灯
3. CARLA 相机标定重做（1280×720）
4. warmup 预热

---

# 十一、OCR 那条线（你拍板后新增，已跑通）

> 你说"修"之后的行。**结论：OCR 完全跑通，但不是我最初提的那个修法。**

## 11.1 我先想错了，技能救了我

我原计划执行 `icacls "C:\Users\ROG\.paddlex\official_models" /grant "ROG:(OI)(CI)F" /T`。

加载 `diagnose-windows-sandbox-acl` 技能后发现它**明令禁止**"递归替换子项权限"和"手工编辑 ACL"——
**我原来那个方案正是它禁止的做法**。于是改用技能带的官方脚本。

## 11.2 官方脚本给出 `NOT_THIS_CLASS`（没有做任何改动）

```
VERDICT=NOT_THIS_CLASS
SCAN VISITED=9  PACKAGE_SOURCES=0  UNREADABLE=8
顶层 official_models: READABLE=True  MY_RIGHTS=[FullControl]  WRITE_DAC=True  WRITE_OWNER=True
SUMMARY FIXED=0 GRANTED=0 REFUSED=0 RESTORED=0
报告：E:\output\_tmp\acl_report_20261107\acl-report-d720deb127324279a11574eb67060d62.jsonl
```

**这推翻了我上一轮的判断**：我说过"`CodexSandboxUsers` 的限制性 ACE 压掉了权限"。
实测那条 ACE 是 **`Allow ReadAndExecute`（允许，不是拒绝）**，而且顶层我**有 FullControl**。

## 11.3 真实形态（逐个排除）

| 检查 | 结果 |
|---|---|
| 五个子目录是符号链接/重解析点？ | ❌ **不是**，`LinkType=(not a link)`，`Attributes=Directory` |
| 顶层 vs 子目录 SDDL 不同？ | ❌ 可读的 `doc_ori` 与不可读的四个 **SDDL 完全一致** |
| 我能读子目录的 ACL？ | ❌ 连 `Get-Acl` 都报"拒绝访问"（READ_CONTROL 都没有） |
| 逐个 `open()` 探测 | `doc_ori` ✅ 可读；`textline_ori` / `medium_det` / `medium_rec` / `UVDoc` ❌ EPERM/13 |

**结论：四个子目录自身的权限条目把继承关闭且不含我，而我又读不到它自身的权限——所以连诊断都做不到。**

## 11.4 改走官方支持的配置，不动 C 盘权限

在 `paddlex/utils/cache.py:29` 找到：

```python
CACHE_DIR = os.environ.get("PADDLE_PDX_CACHE_HOME", DEFAULT_CACHE_DIR)
```

于是把缓存根重定向到 `F:\AI\paddlex_cache`，模型重下（**133MB → 现共 177MB**）。

**这当场又暴露第二个 bug：**

```
NotImplementedError: (Unimplemented) ConvertPirAttribute2RuntimeAttribute not support
[pir::ArrayAttribute<pir::DoubleAttribute>]  (onednn_instruction.cc:118)
```

根因：`paddlex/inference/models/runners/paddle_static/config/pp_option.py:39-42` 在 CPU 上**自动选 mkldnn 后端**，
而 `paddlepaddle 3.3.1` 的 oneDNN 转换有 bug。开关在 `paddlex/utils/flags.py:65`：

```python
ENABLE_MKLDNN_BYDEFAULT = get_flag_from_env_var("PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT", True)
```

## 11.5 三个环境变量，OCR 就通了

```
PADDLE_PDX_CACHE_HOME=F:\AI\paddlex_cache
PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT=False
PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True
```

实测（合成蓝牌 "JING A 12345"）：

```
engine ready
predict() -> list
  TEXT 'JING A 12345' score=0.999211311340332
RESULT=OK
```

## 11.6 又挖出第三个 bug：项目代码用错 PaddleOCR API

`license_plate_recognizer.py:230` 原来是：

```python
result = self._ocr_engine.ocr(enhanced, cls=True)      # 2.x 写法
```

PaddleOCR 3.7 的 `ocr()` 只是 `predict()` 的别名，**不接受 `cls`**：

```
TypeError: PaddleOCR.predict() got an unexpected keyword argument 'cls'
```

而这个异常被 `except` 吞掉 → **永远返回空车牌，只留一行 warning**。
即使 ACL 修好，这条链路也永远是空的。

**已修**（`license_plate_recognizer.py.bak_20261107_ocr` 可回滚）：改成 `predict()` + 兼容 2.x/3.x 两种返回结构。

修后走项目真实入口 `recognize_plate()`：

```
{'plate_number': 'JINGA12345', 'confidence': 0.4991}
```

（`0.4991 = 0.9982 × 0.5`，因为 `_validate_plate` 认为"JINGA12345"不是合法中国车牌格式——
这符合预期，测试图是拼音不是中文省份简称，不是 bug。）

## 11.7 第四个 bug：**真回归** —— `hyperlpr3` 在 3.12 上没有

这才是最该记的一条。生产链路的车牌识别走的是 **`plate_recognizer.py`（hyperlpr3）**，
**不是**我上面修的那个 `license_plate_recognizer.py`（PaddleOCR）。**两套并行实现。**

| 环境 | `hyperlpr3` | `is_available()` |
|---|---|---|
| 3.11 (zhitong-gpu) | **0.1.3 有** | True |
| 3.12 (迁移后) | **缺 → 已装 0.1.3** | True（装后） |

**如果不查这一步，迁移就会静默地把车牌识别做没了**——
因为 `realtime_detector.py:2826` 用的是 `logger.debug(f"[RealtimeDetector] 车牌识别失败: {e}")`，
**DEBUG 级别在默认日志里根本看不到**。

而且这个异常是 `ImportError` 触发 `_load_failed=True`，之后**永久返回 False**，不会重试。

已装 `hyperlpr3==0.1.3`（依赖 onnxruntime/loguru/tqdm，均已满足，**没有升级任何已有包**）。
两环境行为对齐后，同一批输入结果完全一致（都是 `[]`——合成图本来检不出，不是 3.12 的问题）。

## 11.8 改动清单（§十一 部分）

| 文件 | 备份 | 改动 |
|---|---|---|
| `restart-backend.bat` | `.bak_20261107_py312` | 注入 3 个 `PADDLE_PDX_*` 环境变量（含注释说明原因与实测数字） |
| `start-all.bat` | `.bak_20261107_py312` | 同上（两处分支都注入，共 2 处） |
| `api/license_plate_recognizer.py` | `.bak_20261107_ocr` | `ocr(cls=True)` → `predict()`，兼容 2.x/3.x 返回结构 |
| Python312 环境 | — | `pip install hyperlpr3==0.1.3` |
| `F:\AI\paddlex_cache` | — | 新建，177MB 模型缓存 |

---

# 十二、要如实交代的两件事

## 12.1 CARLA 进程消失了（不是我停的）

迁移验收时 CARLA 在跑（PID 17744），后来 `netstat` 里 **2000 端口没了，`CarlaUE4*` 进程也没了**。

- **不是我杀的**（我全程只杀过 8001 的 python，而且每次都先确认是 python 才杀）
- **时间窗重叠**：并行会话 `session-b8215cb0` 正在装 Python 3.14.10，我抓到过它的安装器弹窗（PID 3700/24056）
- **原因未查**（可能是显存争用、可能与该安装器有关、可能是 CARLA 自身的 Epic/High 画质崩溃问题）

**GPU 现在仍占 5624 / 8188 MiB**，说明还有东西没完全释放，但 CARLA 进程确实不在了。

## 12.2 并行会话的弹窗

你看到的 Python 安装弹窗来自 `session-b8215cb0`（在装 `free-claude-code`，需要 Python 3.14.10）。
那条命令把 `C:/Users/...` 误当参数传给安装器，导致 `/quiet` 失效、弹出图形界面。

**我没有动它的进程**（那是别人的活）。我这条线全程用绝对路径调用 python，没有触发裸 `python`。

