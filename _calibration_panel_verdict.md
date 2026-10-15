# 管理端标定界面 + 云端复核开关 · 结论报告（`_calibration_panel_verdict.md`）

> 日期：**2026-10-06** ｜ 执行：DSH ｜ 类型：**C（编码）+ D（环境）+ F（验证）+ G（排查）**
> 用户决策：① 先做前端「测速标定 + 信号灯 ROI」界面（② CARLA 物理级验证暂缓）；
> 云端复核**关闭后转人工复核队列**（选项 C）；后端由 DSH 自行重启。
>
> **交接四件套之③**（本轮结论报告），必含"被推翻的旧结论"。

---

## 一、一句话结论

**后端早就有 `POST /api/scene/calibration-preview` 和 `traffic_light_roi` 契约，但管理端一个字段都没接** —— 也就是说换视频后没人能在界面上重标 ROI/停止线。本轮把这块补齐并**用真实浏览器跑通 17 项行为验证**，顺带挖出 **4 个真 bug**（其中 3 个是"看起来已标定、实际全废"的静默失效）。

| 交付 | 状态 | 证据等级 |
|---|---|---|
| 管理端标定面板（信号灯 ROI 框选 / 停止线 / 相机参数 4 项 / 地面标定点 / 量距 / 后端参数校验） | ✅ | **三级**（真实浏览器 17/17） |
| 灯态作用域可视化（未标 ROI 时按钮+状态条双警告） | ✅ | 三级（截图 `04/08`） |
| 云端 AI 复核总开关（事件级，关掉转人工复核） | ✅ | 二级+三级（开关双向读写 + 状态机路径） |
| `speed_calibration` 优先级 3 处修复 | ✅ | 二级（六条验收矩阵全 PASS） |
| `database.py` 相对路径 / `config.DB_PATH` / `app.py` 健康检查 | ✅ | 二级（`/health` 返回真实 27 MB 库路径） |
| 启动脚本重写（`start-all.bat` + 新增 `restart-backend.bat`） | ✅ | 三级（脚本实际执行、端口释放/自检输出） |

---

## 二、做了什么（逐项 + 文件）

### 2.1 新建 `E:\output\1\web-admin\src\views\CalibrationPanel.vue`（约 640 行）

四种交互模式（拖框/点一下/点一下/点两下）：

| 模式 | 落盘字段 | 说明 |
|---|---|---|
| 信号灯 ROI（拖框） | `traffic_light_roi` | **闯红灯判定的命门**：只统计 ROI 内灯的灯态 |
| 停止线（点一下） | `stop_line_y` | 换视频必须重标 |
| 地面标定点（点一下+填米制坐标） | `ground_points` | 不知道相机参数时用，≥4 点解单应 |
| 量距离（点两下） | — | 调 `pairs` 量地面距离，配"标准车道宽 3.75m"校验 |

+ 相机参数 4 项（**离路面**高度 / 俯角向下为负 / **水平**视场角 / 偏航）
+ 参数校验按钮 → 后端 `calibration-preview`，回显**地平线行 / 可解像素比例 / 逐行 ppm 表 / 告警 / 点误差**
+ **落点回显** `最近落点 px(u, v)`：坐标换算错了肉眼立刻能发现（本轮就是靠它证明换算是对的）

> **不重复造轮子**：几何计算**全部交给后端**，前端一行都不重算 —— 避免前后端两套公式漂移
> （旧「场景标注」弹窗里那份本地 `ppmPreview` 就是重复实现，已在新面板中不采用）。

### 2.2 改 `LiveMonitor.vue`

- 顶栏新增「测速标定/信号灯ROI」按钮；**未标 ROI 时按钮变黄并写"（未标）"**
- 状态条新增**灯态作用域徽标**：`roi`绿 / `frame`黄（全画面未标定）/ `roi_miss`红 ——
  后端 `/status` 的 `traffic_light_scope` 早就返回了，前端此前**一个字都没用**
- 设置栏新增**云端AI复核**开关（带 tooltip 说明"计费/转人工"），与旧的「云端复核」重命名为**逐帧咨询**区分开
- 修 `saveScene()` **硬编码 `road_direction: 'south'`** → 改为沿用已载入值（演示视频盘上是 `up`）
- `saveScene()` 新增 `pixel_per_meter: null`（清除历史遗留的默认 10，见 §三 BUG-1）

### 2.3 改 `realtime_detector.py`（云端复核总开关）

```python
RUNTIME_SETTINGS["cloud_review"] = True      # 新增，默认保持原行为
```
在 `_process_event_engine` 的**最前面**（优先于"数值类是否值得送审"的判断）插入总闸：
关闭时 `submit_to_ai()` → `mark_manual_review()` → 落证据链（note=`cloud_review_disabled_manual_review`），
**不产生任何云调用**。

### 2.4 改 `traffic_event_engine.py`（新增一个方法，不动状态机）

```python
def mark_manual_review(self, event_id, reason="")   # PENDING_AI -> MANUAL_REVIEW
```
为什么经 `PENDING_AI` 中转：`VALID_TRANSITIONS` 里 `RECORDING` 只能去 `PENDING_AI / REJECTED`，
而 `REJECTED` 是**终态**、进去就再也接不了人工复核。`PENDING_AI` 的语义本就是"等待复核"，
**状态机因此无需改动**。为什么不复用 `apply_ai_result`：那个方法会写 `ai_judgment/ai_confidence`
并把状态强制推到 `AI_REVIEWED` —— 会把"根本没复核"记成"AI 已复核"。

### 2.5 后端三处"静默失效"修复

| 文件 | 修复 |
|---|---|
| `speed_calibration.py` | **① `pixel_per_meter` 抢优先级** → 加 `and not self._explicit_cam`<br>**② `lane_width_px` / `crosswalk` 同样抢优先级** → 同上（第三个漏网分支，浏览器里抓到的）<br>**③ `_explicit_cam` 用 `all(k in s)`** → 改 `all(s.get(k) is not None ...)`（前端清空字段发的是 `null`，**键在值为 None** 被判成"有相机参数"）<br>+ `any(...)` → `all(...)`（原来只填一项也当有几何，拿默认值算） |
| `database.py:51` | `sqlite3.connect("zhitong_violations.db")` 相对路径 → `_DB_FILE`（G2/T29，记录 4 天未修） |
| `config.py:31` | `DB_PATH` 指向项目根（**0 字节空壳**）→ 与 `database.py` 对齐 |
| `app.py:202` | 健康检查的相对路径 `os.path.exists("uploads")` / `("zhitong_violations.db")` → `Config` 绝对路径，并返回 `db_path` / `db_size_bytes` |

### 2.6 启动脚本

- `E:\output\1\start-all.bat` **重写**：先探测 8001/5173 端口（已在跑就跳过而不是撞端口）、
  默认**不带 `--reload`**（与一直在跑的实例一致）、显式探测 `E:\node.exe`
- **新增 `E:\output\1\restart-backend.bat`**：按**端口**找 PID → **校验是 python.exe 才杀**（防误杀）→
  等端口真正释放 → 原命令重拉 → `/health` + `openapi` + `cloud_review` 三项自检
- ⚠ **两个 .bat 必须保持纯 ASCII**：cmd.exe 在 `chcp` 生效**之前**就解析整个脚本，
  中文注释（无论 UTF-8 还是 GBK）都会把命令行撕裂（本轮实测踩过两次）。
  中文说明改放 `_STARTUP_GUIDE.md`。

---

## 三、★本轮挖出的真 bug（都有实测现场）

| # | Bug | 现场表现 | 根因 |
|---|---|---|---|
| **BUG-1** | `pixel_per_meter` 抢在相机几何之前 | 面板回 `标定来源=已标定(手工ppm)`，但**地平线空、可解比例 0、ppm 表全 ✗** | `realtime_detector.py:806` 的 `scene_config` 默认塞 `pixel_per_meter: 10`（违停/旧规则兜底），只要落进 scene 标注就一路传到 `SpeedCalibrator` 并占用 `ppm_ref`，而几何路径条件是 `if not self.ppm_ref` |
| **BUG-2** | `lane_width_px` 同样抢优先级 | 抓请求体发现**根本没发 `pixel_per_meter`**，后端却回 `lane_width` | 同上，还有 ②③ 两条分支没加 `_explicit_cam` 判断 |
| **BUG-3** | 「键在、值为 None」被当成"有相机参数" | 填完整参数仍回 `explicit_ppm`；清空参数又回 `unavailable` | `all(k in s ...)` 只看键存在。前端清空字段发的是 `{camera_height_m: null}` |
| **BUG-4** | `database.py` 迁移检查作用在空壳库上 | 缺列迁移**静默失效**（`ALTER TABLE` 报 no such table 被 except 吞掉） | 相对路径 + 从项目根启动 |
| **BUG-5** | `road_direction` 被前端硬编码覆盖 | 盘上 `up`，前端一保存就变 `south` | `LiveMonitor.saveScene()` 写死 `'south'` |

---

## 四、验证证据（三级优先）

### 4.1 真实浏览器行为验证 —— **17/17 PASS**（三级，最强）

脚本：`E:\output\_uicheck\check.mjs`（Playwright + 本机 Edge，headless）
```powershell
$env:PATH = 'E:\;' + $env:PATH
cd E:\output\_uicheck ; & 'E:\node.exe' check.mjs
```

```
PASS 打开 /live（history 路由）           PASS 首帧图加载成功 naturalSize=1280x576
PASS 标定按钮存在                        PASS 拖框生成了 ROI 矩形
PASS 按钮标注出"未标"警告                 PASS ROI 列表显示坐标 [985,105,1029,190]
PASS 标定面板已打开                      PASS ROI 警告消失
PASS 停止线已落线                        PASS 落点换算与点击位置一致（期望518 实得517）
PASS 调用 calibration-preview 成功        PASS 回显地平线行 / 可解比例 / 逐行ppm表
PASS 标定来源与"未填相机参数"相符          PASS 底部汇总提示正确
PASS 面板可正常关闭
========== 汇总：PASS 17 / FAIL 0 ==========
```
截图：`E:\output\_uicheck\01-live.png` … `08-final-verified.png`

> ⚠ 途中 3 次 FAIL 全是**测试脚本自己的错**（已逐一更正，见 §五），不是产品缺陷：
> ① 用 `#/live` 访问而路由是 history 模式；② 按 natural 尺寸硬算点击位置，比实测 rect 偏 1.44 倍；
> ③ 断言"关闭后 DOM 应消失"，而 el-dialog 关闭是 `display:none`（DOM 保留）。

### 4.2 后端标定优先级验收矩阵 —— **6/6 PASS**（二级）

| 用例 | 输入 | 期望 | 实得 |
|---|---|---|---|
| ① | 相机 4 项 + 遗留 `pixel_per_meter:10` + `lane_width_px:190` | `camera_geometry` | ✅ `solvable=0.952` |
| ② | 仅 `pixel_per_meter` | `explicit_ppm` | ✅ |
| ③ | 仅 `lane_width_px` | `lane_width` | ✅ |
| ④ | 相机只给 2 项（残缺） | `assumed_lanes`（不再假装已标定） | ✅ |
| ⑤ | 相机三项全 `null` 键存在 + ppm | `explicit_ppm` | ✅ |
| ⑥ | 演示视频真实存档（1920×1080，无覆盖） | `camera_geometry` | ✅ `horizon=123.7`、`solvable=0.85` |

### 4.3 云端复核开关（二级 + 三级）

```
POST /api/realtime/settings {"cloud_review": false} → 回读 false（持久）
POST /api/realtime/settings {"cloud_review": true}  → 回读 true
```
`/api/realtime/settings` 现已返回 `cloud_review`（前端 `loadSettings()` 回读并回写，杜绝"界面显示关了、后端还开着"）。
状态机路径 `RECORDING → PENDING_AI → MANUAL_REVIEW` 合法（`VALID_TRANSITIONS` 未改）。

### 4.4 启动脚本（三级）

`restart-backend.bat` 实际执行输出：`found listener PID=42548` → `process name: python.exe` →
`stopping` → `port 8001 released` → `launching` → 自检 `openapi: 132 operations`。
`/health` 返回 `db_path=E:\output\1\api\zhitong_violations.db`、`db_size_bytes=27369472`（**真实库**，不再是空壳）。

### 4.6 ★第四轮：用户报「刷新管理端网页卡住」的排查（2026-10-06 深夜）

**结论：后端日志 0 个 ERROR/Traceback；浏览器侧也无法复现"卡死"**（`/live` 8 秒可交互、
主线程 2 秒 481 帧、140 个请求无一 >20s、零页面错误；检测运行中反复刷新同样测不出）。
但**查出一个真实的性能缺陷，很可能就是"卡"的来源**：

| 项 | 事实 |
|---|---|
| **🔴 `/api/realtime/evidence` 每次请求 stat 4513 个文件只为返回 24 条** | `uploads/` 现有 **4526 个文件 / 2234 MB**，其中 **4513 张** `realtime_*.jpg`。原实现 `glob` 全部 → 逐个 `os.stat` → 排序 → 才切片 `limit`。实测**稳定 500 ms**，而 `/live` 每 **1.5 秒**轮询一次（还顺带加载 24 张原图）→ 持续 I/O 抖动，UI 交互一顿一顿 |
| 修法 | 改 `os.scandir` 单次遍历（`DirEntry.stat()` 复用目录项信息）+ 按 mtime 取前 N 再建对象；**语义不变**（仍返回 `total=4513`、最新在前） |
| 效果（二级证据） | **500 ms → 10~19 ms**（同一命令连测 4 次：19/14/10/12 ms） |
| 检测运行中复测 | 最慢请求从 500 ms 降到 **133 ms**（`/api/realtime/stream`），证据接口不再进慢榜 |

**顺带修掉一个排查障碍（也是"日志"这件事本身的坑）**：

| 问题 | 说明 |
|---|---|
| `app.py` 的 `log_dir = "output/logs"` 是**相对 cwd** 的 | 从项目根启动 → `1\output\logs\api.log`（真实日志，已 **6.7 MB**）；从 `api\` 启动 → `api\output\logs\api.log`（停在 10-02 的旧文件）。**"日志在哪"取决于启动方式** —— 本轮我就先看错了文件，误判成"日志没在写" |
| 修法 | 锚定到 `api\output\logs\`（绝对路径），从任何 cwd 启动都写同一处 |
| 后端控制台输出 | 随 `restart-backend.bat` 的新窗口可见；若用重定向启动，**stderr 有缓冲**，不是不写（我一度看到 0 字节就下结论，属误判） |

**仍未确认**：用户说的"卡住"具体形态（整页白屏 / 转圈 / 画面不动但能点）。
我这边复现不出，需要用户补充。**未验证不写成事实。**



用户三条反馈全部核实，并牵出 2 个**新真 bug**：

| # | 用户反馈 | 核实结果 | 处置 |
|---|---|---|---|
| **R1** | "管理端没有途径能进 `/live`" | ✅ 属实：`App.vue` 导航里**没有** /live 项，`subToMain` 也无映射 → 访问 /live 时顶部**一项都不高亮** | 新增「实时监测」「交通事件」两个顶级导航项；`/events` 不再蹭「违规管理」的高亮 |
| **R2** | "演示视频太快"（用户指明 `evt_11200_18_60c808`） | ✅✅ **系统性 bug**：事件视频按 `fps=Config.FRAME_BUFFER_FPS`(**10**) 写盘，而源是 **20 fps** 采集的 → 时间轴拉长一倍、**播放快一倍**。扫描现有 **4855 个事件视频，抽查 12 个全部 2.0×**。`config.py:80` 的 `EVENT_VIDEO_FPS_FROM_SOURCE` 开关**定义了却全仓没人读**（空壳） | ① `realtime_detector` 改为按 `(帧数-1)/(首末帧时间戳跨度)` 推导 fps 并夹在 [5,60]；② 按用户指定**只重封 `evt_11200_18_60c808`**（188 帧：18.8s → **9.4s**，20fps），原件备份为 `.bak2x`；③ 同步修正 `replay.json` 的 `fps`/`time`（否则回放叠加框会与画面错位） |
| **R3** | "系统设置里『启动AI审核/启动兜底模型』是我想象的那个关了就不收费了吗？" | ❌ **两个都是装饰品**：`saveAiConfig()` 全文只有一句 `ElMessage.success()`，**没有任何 API 调用**；`aiConfig` 全在组件内存、刷新即丢。且**"启用兜底模型"后端根本没有该功能**（只存在自动降级：判色 CNN→HSV、云端 Claude→豆包、车牌模型→借用 yolov8s） | 整栏重写：接**真**运行时设置（`cloud_review` / `cloud_consult` / `cloud_review_uncalibrated` / `hold_sec` / `cooldown_sec` / `display_mode`），改一下即生效、并回读校验；删除 `aiConfig` 与 `saveAiConfig`；把无实现支撑的项改为**如实标注的「未实现」说明** |
| **R4** | "智能识别页上传不能传大视频" | ✅ 半属实 + **挖出更严重的**：① 50MB 上限，且**先把整个文件读进内存再判大小**、拒绝时已在磁盘留半个垃圾文件；② 🔴 **`result` 未初始化**（只在"图片+run_ai"分支赋值，后面无条件读）→ 实测原始逻辑下 `视频+run_ai=true` 抛 `UnboundLocalError`、**视频上传必失败**（用 git 原始代码隔离复现过） | 上传接口改**流式分块**（边读边写边累计，超限即中止并删掉半成品）、上限提到 **500MB**；补 `result = None` + 判空 |

**R4 验收（三级）**：
```
1) 图片 run_ai=false   -> success=True                    （修 result 后）
2) 视频 7MB run_ai=true -> success=True                   （原先该路径必崩）
3) 510MB（curl 真实 multipart）-> FILE_TOO_LARGE + 无残留  ✅
   ⚠ 测试陷阱：用 requests 的**生成器文件对象**会被 uvicorn 截断成 chunked
     （只传 1MB 就 200 返回），测大文件必须用**磁盘真实文件 + curl**。
```

**前端回归 `E:\output\_uicheck\check2.mjs` — 15/15 PASS**：导航入口与高亮、tooltip 说明、
假开关已移除、真开关"切换后**后端真的变了**"、上传文案。

⚠ **本轮我犯的错（记录在案）**：清理测试数据时写了
`delete from violation_evidences where image_path like 'upload_%' ... limit 10`，
**误删 6 条 2026-06-12 的旧演示记录**（id 19~24，`wrong_way`/`lane_departure`，
图片 17~194 KB，可通过重新上传恢复）。教训：删除类操作必须**先列清单、按精确 ID 执行**。

---

## 五、★被推翻 / 更正的东西（含本轮我自己的错判）

| # | 旧结论或旧实现 | 更正 |
|---|---|---|
| **O25** | "前端保存场景标注会抹掉 `traffic_light_roi` / `stop_line_y` / `camera_yaw_deg`" | ❌ **我一开始的判断错了**。`scene_annotation.save_scene()` 默认 `merge=True`（2026-10-03 已修），只写传入的字段。真实缺陷只是"填了 `road_direction: 'south'`"和"没有界面"。**据此不能再宣称"保存会抹字段"** |
| **O26** | "`_explicit_cam` 用 `any(...)`，只填一项也算有几何" | ⚠️ 半对。改成 `all(k in s)` 后**引入新 bug**：`null` 值也算"键存在"。最终正确形式是 `all(s.get(k) is not None ...)` |
| **O27** | "面板里 `method=explicit_ppm` 说明修复没生效" | ❌ 要看**上下文**：默认源（测试视频）的 scene 存档里本来就有 `pixel_per_meter=10`，此时填了相机参数才应走 `camera_geometry`；**没填相机参数时走 `explicit_ppm` 是正确行为**。原测试断言写死 `camera_geometry` 是测试设错目标 |
| **O28** | "`horizon_y` 手算真值 123.7（交接文档 §四记载）" | ⚠️ 该值**不满足** `horizon_y = H/2 + f·tan(pitch)`（1920×1080/fov90/pitch-23.445 应为 **-10.5**）。123.7 是 `preview()` 在 **1280×576** 下算出来的 | 
| **O29** | "`_debug_homography.py` 直调 `SpeedCalibrator(merged_cfg, ...)` 复现了路由的相反行为" | ❌ 那次我把脚本放在**临时目录**执行，`load_scene` 因相对路径找不到存档返回空 dict，所以 `pixel_per_meter` 变 None → 得出"直调与路由相反"的错误结论。复盘后确认**路由行为正确** |
| **O30** | "「云端复核」勾选框能省 cloud 费用" | ❌ 那个勾选只控制**逐帧咨询**（`cloud_consult`）。事件级复核（`analyze_event`，一次打 2~3 家云 API）**此前完全没有闸门**且默认开启 —— 这才是"一直花没必要的钱"的主因 |
| **O31** | 交接文档称"运行中实例是旧进程，重启后 openapi 才是 132" | ✅ 已闭环：重启后实测 **132 operations**；`_PROJECT_MAP.md` 里"需重启"的说明已过期 |
| **O32** | "事件视频没问题，只是演示素材本身短"（我第一轮的判断） | ❌ **错**。用户指出后实测：事件视频按 10fps 写盘而源是 20fps → **播放快一倍**，4855 个视频全都是。素材"短"（26s）与"快"（2×）是两件事 |
| **O33** | "系统设置里『启动AI审核/启用兜底模型』能控制是否收费"（用户的合理预期） | ❌ 两者**都是装饰品**（`saveAiConfig` 只有一句 `ElMessage.success`）。"关了就不收费"当时**不成立**；现已接成真开关 |
| **O34** | "智能识别页不能传大视频 = 50MB 上限的问题" | ⚠️ 只对一半。真正让**视频上传必失败**的是 `result` 未初始化（`UnboundLocalError`），与大小无关 |
| **O35** | "我上一轮清理临时目录导致项目 ffmpeg 转码链路受损"（我在第二轮的判断） | ❌ **错**。项目解析顺序是 `imageio_ffmpeg` 自带 ffmpeg 7.1 **优先于** PATH，所以转码一直正常；坏的只有我自己的 `ffprobe` 命令。已把 shim 重指向 CanMV 的 FFmpeg n6.0 |


---

## 六、仍未解决 / 风险（如实登记）

1. **🟠 审计发现的前后端不一致尚未修**（本轮只做了"查"，没做"修"，避免一次改太多模块）：

| 级别 | 问题 | 位置 |
|---|---|---|
| 🔴 | 分歧详情弹窗**永久 422**：前端传 `session_id`（UUID），后端要 `record_id: int` | `DisagreementList.vue:377` vs `cloud_collab.py:259` |
| 🔴 | 分歧裁决按钮**永久 422**：前端发 `{session_id, judgment_result}`，后端要 `resolution`(必填)+`resolver_id`(必填) | `DisagreementList.vue:407/425` vs `cloud_collab.py:60` |
| 🟠 | **协作统计页整页静默归零**：模板读 `total_consultations / confirmation_rate / cost_saved_*`，后端只给 `log_statistics / db_statistics` | `CollabStats.vue:11-181` vs `cloud_collab.py:307` |
| 🟠 | 「设备在线」恒 0（后端 summary 从不产出 `online_devices`） | `Dashboard.vue:243-271` vs `violations.py:857` |
| 🟠 | 追踪焦点框定位失效（后端不产出 `frame_width/height`） | `RealTimeMonitor.vue:111` vs `virtual_tracker.py:377` |
| 🟠 | 两处硬编码 `http://localhost:8001`（非本机访问必挂） | `CollabStats.vue:196`、`DisagreementList.vue:276` |
| **🟠 新** | **上传记录的证据图打不开**：仪表盘/违规管理请求 `/uploads/upload_*.jpg` 返回 **404**。上传接口把**纯文件名**写库、文件也确实存进了 `api/uploads/`，但前端按根路径 `/uploads/...` 取 —— 经 Vite 代理到后端 `/uploads` 静态挂载时命中不到（本轮实测 404 出现两次）。需核对 `app.py` 静态挂载目录与 `Config.UPLOAD_DIR` 是否同一个 | `routers/violations.py:762` + `app.py:202` |

2. **灯态 ROI 仍必须人工标**：换任何视频都要重标 `traffic_light_roi` + `stop_line_y`，
   否则 O19（每循环 5~7 次误报）立刻复现。**界面已用双警告提示，但没有自动检测能力**。
3. **`realtime_detector.py:806` 仍写死 `pixel_per_meter: 10`**：本轮是在 `SpeedCalibrator` 侧加了优先级判断来兜住。
   根治应由"场景合并"改成只在真有人工 ppm 时才注入 —— 属既有业务逻辑，未动。
4. **云端复核关闭后没有"批量确认"入口**：事件会一条条堆在「待人工复核」，量大时需要批量操作（未实现）。
5. **上传记录的证据图 404**（见上表最后一行，第三轮新发现，**未修**）。
6. **`_uicheck` 是临时验证目录**（含 playwright-core，约几十 MB）：确认后可删。
   **两个回归脚本建议保留**：`check.mjs`（标定面板 17 项）、`check2.mjs`（导航/设置/上传 15 项）。
7. **`evt_11200_18_60c808.mp4.bak2x`**（2× 速度的原始版本）保留在
   `E:\output\1\api\output\event_videos\20261006\` 作对照；不需要可删。

---

## 七、交接自检（协议 §9.4）

- [x] 只读 3 个文件能知道项目有什么 → `_PROJECT_MAP.md` 已补 `CalibrationPanel.vue`、两个 .bat、`cloud_review`
- [x] 能知道上一步做到哪、下一步做什么 → `_SESSION_HANDOFF.md` 已重写
- [x] 能知道哪些结论被推翻 → 本文件 §五（O25~O31）
- [x] 路径都真实存在 → 逐个核对（含截图、脚本、验证目录）
- [x] 未验证项如实标注 → §六 逐条列出；三级/二级证据分别标注
