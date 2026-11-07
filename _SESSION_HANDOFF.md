# 智瞳灵声 · 会话交接（内容更新至 2026-10-17；项目本体最近一轮 = 2026-10-11）

> **共同启动规则：** 所有 AI 先读取 `E:\output\_AI_COMMON_RULES.md`。本文是 **2026-10-10 ~ 10-11 的旧任务进度快照**，不是全局永久规则；只有确认继续同一开发任务时，才采用下面的"具体步骤"（§一 ~ §二·补）。
> **⚠ 范围说明**：§三（用户行为纪律）、§四（CARLA 硬知识）、§五（服务与命令速查）、§七（已推翻的旧结论）是**常驻内容**，任何任务都适用 —— 不要因为"这是旧快照"而跳过它们。
>
> **✅ 本轮（2026-10-23，管理端 UI 优化，F1-F10 已全部实施并通过三级验收）**：
> 用户拍板三决策（1→A 换审核状态分布环形 / 2→授权改代码 / 3→A 统一亮色）后执行。
> **改 6 个文件**（全部以 .bak_20261023 备份）：
> ① utils/format.js —— TYPE_MAP 6→12 key（11 类 + 1 个历史别名）+ TYPE_COLORS 同步 + **未映射兜底**（返回「未知类型」并 console.warn，禁止英文外露）
> ② views/Dashboard.vue —— 类型分布**环形→横向排序条形图**（§2.5 参数：yAxis.inverse:true 最大值置顶、条尾标百分比、删 legend）+ 排行卡→**审核状态分布环形图**（取 by_status）+ 容器 250→260px + 三处 echarts.init 传亮色主题 + **修 KPI 栅格**（原 lg:2 仅 103px 装不下 4 字标签，内容溢出卡片）
> ③ views/EventDetail.vue —— 删本地补丁 EXTRA_TYPE_CN，统一走 getTypeName()
> ④ utils/echarts-theme.js —— 深色→**亮色 zt-light** 全量重写（对齐 design-tokens.css）
> ⑤ components/TypeTag.vue —— 文字色按底色亮度自适应（原硬编码白字，在 #F2C14E 上对比度约 1.9:1 读不清）
> ⑥ styles/design-tokens.css —— 新增 **el-card 全局令牌化**（全站卡片圆角/描边/阴影统一）
> **验收（三级证据）**：构建 exit 0；浏览器实测 englishLeak=[]（**零英文外露**）、KPI 1 行 6 卡 0 溢出、3 图 3 图例、7 类中文全可读、最大值在顶；截图 dash_final.png / dash_fullpage_after.png。
> **顺手发现 2 个既有问题，已登记未擅自修**：**G17** 违规列表「设备位置」列显示 x:undefined, y:undefined（ViolationList.vue:337 读 pos.x，后端实际给 center_x/center_y，与本轮改动无关）；**G16** Statistics.vue 三处 echarts.init 仍未传主题。
> **回滚**：把任意 .bak_20261023 覆盖回同名文件即可。
> ---
> **（评估阶段记录，已被本轮取代）** 用户指出仪表盘两处问题（设备违规排行无用 / 违规类型分布图重叠+文字不统一）。
> **三级证据诊断**（真实截图 `E:\output\dash.png` + 代码定位）：实测到 **4 个问题**（标签重叠、图例折行、`running_yellow` 英文外露、排行卡完全空白）。
> **根因**：① 排行卡后端**从无** `by_device` 字段（非故障）；② 7 分类塞 400×250 环形是**几何必然重叠**；③ 中文名有 **5 套映射表**各自为政（前端 6 类 vs 后端 10-11 类）。
> **三模型并行独立评审**（Codex/gpt-5.6-luna、Qoder/Qwen3.8-Max、CodeBuddy/glm-5.1，全部 exit 0）**结论高度一致：换成横向排序条形图**。
> 入口：**`E:\output\_ui_optimization_verdict.md`**（含待拍板 3 件事 + 实施清单 F1-F10 + 验收 5 项）。
> **遗留**：等用户拍板决策 1/2/3 后才能动代码；本会话**未修改任何项目文件**。
>
> **🆕 最近一轮（2026-10-16，属"办公室/工具链"而非项目任务）**：**AI 派活通道建设** ——
> **Codex / CodeBuddy / ★Qoder CN 三条 CLI 通道已打通**（第四条 TRAE CLI 因官方限制"仅企业版旗舰版可用"**已结案**）；
> ★ **共享技能池 `C:\Users\ROG\.agents\skills` 被 Qoder CLI 原生复用（实测 67/67 自动加载）**。
> 入口：**`E:\output\_DSH_OFFICE_STATE.md` §1.3 / §1.4** + `E:\output\qoder_cli_channel_verdict.md`；派活工具 `E:\output\_tools\qoder.ps1`。
> **智瞳项目本身的进度不受影响**（下方第七轮内容仍然有效）。
>
> **🆕 更近一轮（2026-10-17，仍是"办公室/工具链"，未触碰 `1/` 项目代码）**：**DSH 专属技能池建立** ——
> 新建 `C:\Users\ROG\.dsh\skills`（**热加载**，实测写入 3 秒生效；3 个自研技能：`dsh-office-ops` / `dsh-delegation-channels` / `zht-project-playbook`）；
> **dshmarket 一键重启在 Desktop 上不可开**（源码级定案：`allowRestart:false` 硬编码）→ 替代脚本 `E:\output\_tools\restart-desktop.bat`（双击即用）。
> 入口：**`_DSH_OFFICE_STATE.md` §27.16 / §27.17**。
> **遗留（新会话可直接接手）**：① 技能池是否继续扩展（候选：`windows-safe-fileops` / `dsh-env-forensics` / `zht-demo-runbook`）② 重启脚本首次实测（建议用户空闲时双击一次）。

> **🆕 最近一轮（2026-10-17，「CARLA 仿真工具化」第 1、2 批已交付）**：用户要求把"脚本生成仿真 → 录视频"升级为**可交互拖拽的演示素材生产线**
> （**定位：演示素材生产线，不属项目本体**，用户当轮明确）。
> **调研结论**：CARLA 官方**无**"拖拽摆车 + 逐车速度 + 红绿灯时长"三合一 GUI（唯一官方 GUI `carla-studio` 的拖拽只做传感器标定；release 包**不含 UE 编辑器**）；
> 用户点名的 `oasis-sim` = **Synkrotron/GuardStrike 的 OASIS（商业产品）**，CARLA 官方博客原文称其"提供 Scenario Editor GUI"，需申请试用、不开源。
> **第 1 批已交付**：`E:\output\1\carla\CARLA_0.9.16\PythonAPI\examples\carla_creator_workshop.py` **546 → 1265 行**，
> 新增「红绿灯配时」（`freeze_all_traffic_lights` + `on_tick` 相位机）、「车辆速度」（单车/全局速度差/闯红灯概率）、1080p H.264 录制、相机分辨率与帧率切换；
> 备份 `carla_creator_workshop.py.bak_20261017`（回滚：把备份覆盖回去）。
> **验收**：`py_compile` exit 0、独立 GUI 冒烟通过（CARLA 未启动也能开窗）；**功能是否真实生效仍需开 CARLA 实测**（见 verdict §10.5 未验证项清单）。
> **✅ 第 2 批已交付（2026-10-17，点击摆车 / 拖动车辆）**：同一文件 **1265 → 1782 行**，新增「鼠标摆放」子框（点击空地摆车 / 按在车上拖动 / 可选吸附车道 / 删除选中 / 撤销上一步；**点中车会自动同步到「车辆速度」下拉**）；
> 反投影复用 playbook §6 基向量，屏幕→地面走"解析求交 + `ground_projection` 校正"——**别再去 CARLA API 里找现成函数**（新被推翻结论 **O6**）；
> 备份 `carla_creator_workshop.py.bak_20261017b`；验收：py_compile exit 0 + 投影单测 **12/12** + GUI 冒烟 **26/26** + 状态机 **13/13** + **真实 CARLA 三级验证 20/20**（Town10HD_Opt，含 4 个只有实机才暴露的 bug 修复，见 verdict §12.8）。
> **⚠ 启动器已修（2026-10-17）**：`启动CARLA创造工坊.bat` 原来同时有 **LF-only 换行** + **UTF-8 中文内容**，cmd 按 GBK 解析直接崩（双击没窗口）→ 已改成**纯 ASCII + CRLF**，备份 `.bak_20261017`；另给 Tk 加了窗口居中（原来会贴边被裁）。**以后写 .bat 必须 CRLF + 纯 ASCII**，详见 verdict §12.9。
> **✅ 第 3 批已交付（2026-10-17）**：① 项目名统一为 **智瞳灵声**（工坊标题）；② 修复"点车反而生成新车"——`点击空地摆车` **默认改关**、拾取加 45px 兜底、选中车画**黄框**；③ 新增**右键菜单**：点车可改朝向（正对镜头/±90°/对齐车道/输入角度）、目标速度、闯红灯 100%、删除；点空地可摆车。验收：GUI 冒烟 **35/35**、状态机 **15/15**、真实 CARLA **7/7 + 20/20**。详见 verdict §13。
> **另（2026-10-17）**：启动器改为 **pyw 无控制台**（不再有黑窗挡住工坊窗口），Python 崩溃会写 `1\carla\仿真输出\workshop_error.log`。
> **✅ 第 4 批已交付（2026-10-17，行为模式 + 道具）**：右键菜单→「行为模式」可设 **遵守/闯红灯/超速/逆行/压线/违停**（真实 CARLA **10/10** 验证）；蓝图下拉含 **99 种 static.prop** 道具；左栏有「全部车辆开始行驶」。
> ★ 两个硬坑见 verdict §14.5：**`ignore_lights_percentage(100)` 在本机无效**（同步模式也试了）；**`enable_constant_velocity` 在反向车道方向会反**（手动驱动一律用 `apply_control` 油门）。
> **🆕 最近一轮（2026-10-23，第 4 批剩余两项）**：① **已交付并验收**；② **代码写完但未验收**（用户睡觉，子代理中断）。
> 入口：**`E:\output\_carla_workshop_batch4_verdict.md`**（本轮验收结论，含 3 个被推翻的旧结论 + 3 个修掉的真实 bug）。
>
> **✅ ① 场景 v2 + 自动保存 + 最近项目 —— 已交付，lead 独立复跑五层全绿**：
> py_compile 0 ／ 离线 GUI **68/0** ／ 序列化 mock **103/0** ／ 既有 GUI 回归 **35/0** ／ **真实 CARLA round-trip 85/0**。
> v2 补齐 v1 全部缺口：vehicles(autopilot/behavior_mode/目标速度/闯红灯) + props + 红绿灯配时(含秒数) + 相机机位/fov + 全 14 字段天气 + session；
> **向后兼容 v1**（`SCENE_FORMAT_READABLE` 同时接受）；自动存档每 180s 原子写 `仿真输出\场景快照\last_session.json`；最近项目 10 条存 `_workshop_recents.json`。
> **✅ ② 装饰物（EnvironmentObject）选中与隐藏 —— 已交付并验收（2026-10-24）**：
> **实机 PASS=47 FAIL=0**（`_verify_workshop_env_live.py`）／离线 **73/0**（`_verify_workshop_env_offline.py`）。
> 三档全实现：A 按类别批量（`hide_env_label`/`show_env_label`）／B 右键点中单个（`_env_pick`/`hide_env_single`）／C 相机半径批量（`hide_env_in_range`）+ 一键恢复（`restore_all_env`）。
> **★ 本轮最有价值的发现**：一根路灯/一棵树常由**多个同心 EnvironmentObject** 组成（Poles 880 个聚成 508 组，**254 组是多对象**，每根灯常有 2~3 件，如 `BP_StreetLight_doble10_SM_1`/`_SM_2` 共用同一 bbox.location）。
> 单独藏会留下**残缺的半个路灯** → 新增 `_env_sibling_ids(label, ids, tol=0.05)` 按中心坐标吸附同组，藏一根 = 藏整组，恢复也成对。
> **缓存实测**：首次 1,444~1,552 ms → 命中 **0.0068 ms**（约 20 万倍）；三档实测：档A 藏 62,581 个植被（画面 19.6% 像素变化）、档B 精确命中 `SM_Parklight2_SM_0`、档C 半径 50m 命中 569 个。
>
> **✅ AI 化（--headless + JSON 剧本）—— 已交付并验收（2026-10-24）**：**PASS=21 FAIL=0**。
> **AI 一条命令出片**：`py -3.12 <工坊.py> --recipe E:\output\recipes\闯红灯演示.json` → 7.8 秒产出 4.05s H.264 视频（960x540/20fps/81帧），**全程零交互、无弹窗、世界自动还原**。
> 另有 `--selftest`（不开 CARLA 校验剧本，坏剧本给中文错误）与 `--print-schema`（自描述格式）。
> 实现方式（最小侵入）：headless 下仍建隐藏 `tk.Tk()` 让 32 个 Tk 变量保持真实，把 **17 种控件构造器**换 `_StubWidget`、**60 处模态调用**换无交互适配器 → **116 处 `.pack()` 一行不用改，GUI 路径零风险**。
> **★ 两个真实产品缺陷被修掉**：① **录制视频播放慢一倍**（CARLA 异步下相机实测 **43.4 fps**，ffmpeg 却用 `-r 20` 封装 → 5 秒录成 10.25 秒）→ 改用时间戳门控重采样，5 秒剧本现在产出 **101 帧/5.05 秒**；
> ② 录制起点错误（`hide`/相机等预置阶段被录进视频）→ 准备动作做完才开始录制。
> 入口：**`_carla_workshop_batch4_env_verdict.md`**（② 验收）+ **`_carla_workshop_ai_verdict.md`**（AI 化）+ `_carla_workshop_ai_design.md`（设计稿）+ `E:\output\recipes\闯红灯演示.json`（示例剧本）。
>
> **✅ 收尾轮（2026-10-24）—— 已交付**：**`_carla_workshop_wrapup_verdict.md`**。
> 修掉 1 个设计脆弱点：**`enable_headless()` 是进程级不可逆的 tkinter 改写**（同进程内先跑剧本再开 GUI → 窗口全是空壳控件且不报错）。
> 已加两道加固：前置检查（有存活实例直接抛错拒绝）+ 新增 `disable_headless()` 精确还原 23 个被替换对象；实测可逆切换 `preview=Label/record_button=Button/map_combo=Combobox`。
> **跨进程（用户双击 bat）完全干净**，GUI 交互行为零改动。
> 另验证了 3 个「写了但没真跑」的东西：真 GUI 开窗 OK、`_world_state.py diff` 能真抓到污染、AI 产物 → GUI 接续 OK。
> 修了验收脚本自身缺陷：**「断言世界干净」的脚本必须先清理自己的残留**（曾把自己的调试车误判成产品缺陷，21-0 掉到 19-2）。
> 清理 **44 个**临时脚本 + 3 个临时目录；**新增回滚点 `.bak_20261024_after_ai`**。
>
> **🎯 下一步（新会话直接用）**：
> 1. **车牌**（`apply_color_texture_to_object`，只走 CARLA 内贴图；后处理逐帧叠加已被用户否决）—— **需用户先确认贴图方案与素材来源**
> 2. 剧本 `camera.preset`（预设机位名）尚未实现，只支持显式 transform
> 3. 红绿灯配时的**崩溃场景**残留风险（进程崩溃时 stop 跑不到，无法写回）
> 4. `_scripts` 里另有 300+ 历史脚本（非本轮产生），是否清理待用户决定
>
> **📦 回滚点共 4 个**：`.bak_20261017b`(57K, 第2批) → `.bak_20261023`(96K, 第1~3批) → `.bak_20261023_after_v2`(123K, ①完成) → **`.bak_20261024_after_ai`(191K, 当前态)**。
>
> **⚠ 三个必须记住的新硬知识（详见 batch4 verdict §3）**：
> - `reflection_intensity` 在 0.9.16 **不存在**；`WeatherParameters` 只有 **14 个**数值字段 + 23 个预设常量（常量不能存）
> - **「6.2 万必须空间过滤」的理由要改**：真正慢的是 `get_environment_objects()` RPC（**133~228 ms**），numpy 全量投影只要 **1.2 ms**
> - `EnvironmentObject.id` **超出 int64**（样例 16740775638937321093）→ **绝不能进 numpy int64 数组**（OverflowError）；且它**没有** `get_world_vertices()`，`bbox.location != transform.location`
>
> **🐛 本轮修掉的 3 个真实 bug（都是 lead 审查抓的，不是子代理自查）**：
> ① 恢复场景速度用了 `enable_constant_velocity`（违反 K2，反向车道会走反）→ 改 `_drive_forward` + `parked` 守卫；
> ② 两处 `askyesno` 默认按钮是「是」→ 误按回车直接 reload 丢现场 → 已加 `default="no"`；
> ③ **红绿灯配时永久改写且不还原**（第 1 批遗留）：`set_*_time()` 永久改写、`reset_group()` 只重置相位不恢复秒数 → 已加 `_tl_snapshot_durations`/`_tl_restore_durations` 快照还原；**遗留**：只覆盖正常 stop 路径，崩溃仍会残留。
> &nbsp;&nbsp;&nbsp;教训：**「世界干净」不能只看 actor 数量**，配时/天气/世界设置/隐藏物体/机位都要逐项断言还原。
>
> **回滚**：`.bak_20261023_after_v2`（125,791 字节，① 完成后 ② 开工前）→ 只回滚 ②；`.bak_20261023`（98,380 字节，① 开工前）→ 连 ① 一起回滚。
> **收工现场已还原**：23 actor ／ 车辆·道具·相机 0 ／ 红绿灯 15 盏全 10/3/2 ／ 64,571 个装饰物全可见 ／ 用户机位未变。
> 早期入口：**`E:\output\_carla_sim_tooling_verdict.md`**（第 1~4 批实录 + 被推翻结论 O1~O9 + 硬坑 K1/K2 见 §14.5）+ `_scout_notes\`（调研原始笔记）。

> **用途**：新会话开场读这份 + `_PROJECT_MAP.md`，即可接上进度。
> **本文件只记"现在在哪、下一步做什么"**，不记过程与流水账（协议 §9.2）。

---

## 本轮旧任务的下一步（仅在确认继续该任务时适用）：读 **`_design_2026-10-09_verdict.md`**

> 第七轮（2026-10-10）**已真正改代码**：`_DESIGN_NOTES_2026-10-06.md` §11.0 的**前 3 项做完并验证通过**。
> 那份设计单的 **§12 仍是最权威的根因结论**、**§11.0 是执行顺序**。
> ⚠ **第 4 项（两个框）已完成**（见 §二 表，含 20/20 验证）；**未闭环的是 §二·补的第 5 / 8 / 9 / 10 / 13 / 14 项**，
> 其中 **第 13 / 14 项需你决策**（原生崩溃根因、1970 脏数据回填）。
> **本轮的结论（含被推翻的旧结论 O36~O43）在 `_design_2026-10-09_verdict.md`。**

---

## 一、本轮旧任务的建议读取清单（不是全局启动规则）

| # | 文件 | 作用 |
|---|---|---|
| 1 | `E:\output\_PROJECT_MAP.md` | **项目能力清单（必读）** —— 先读它，避免重复造轮子 |
| 2 | `E:\output\_SESSION_HANDOFF.md` | 本文件：现在在哪、下一步做什么 |
| 3 | `E:\output\_DSH_WORK_PROTOCOL.md` | 工作协议 **v1.4.1**（含五条铁律 + **4.6 多问用户/先猜他能做什么**，务必遵守） |
| 4 | **`E:\output\_design_2026-10-09_verdict.md`** | ★**本轮结论**（含被推翻的旧结论 + 遗留风险） |
| 5 | `E:\output\_DESIGN_NOTES_2026-10-06.md` | ★**任务总单**：11 个问题的根因 + **§11.0 执行顺序**（§12 最权威） |
| 6 | **`E:\output\_GPT6_HANDOFF_BRIEF.md`** | ★**给 GPT6 的疑难问题移交书**（2026-10-11 生成）：**后端原生崩溃**（一天 5 次、cv2 自带 FFmpeg、`0xc000001d`）、**1970 脏数据 = 566 条（2026-10-12 只读查库定案）**、**云端复核误判**、**告警栏延迟**、**"进程假死"型超时** —— 含全部证据、**已排除项**、环境红线、可复用脚本，以及 DSH 写给 GPT6 的私话 |
| 7 | **`E:\output\_ALERT_LATENCY_HANDOFF.md`** | ★**告警栏延迟专项**（2026-10-11）：**给用户的操作卡**（F12 看 `[告警延迟]` 两行数字）+ **给 GPT6 的线索包**（已排除环节的实测值、3 条假设、最短验证路径、代码位置） |

> 相关（按需读）：`_PERF_FPS_verdict.md`（识别框帧率那轮）、
> `_calibration_panel_verdict.md`（标定面板/云端开关/上传那轮，O25~O35）、
> `_speed_calibration_verdict.md`、`_redlight_accuracy_verdict.md`、`_STARTUP_GUIDE.md`。

---

## 二、当前进度

### ✅ 第七轮（2026-10-10）：**§11.0 前 3 项已改完并验证通过**

> 结论报告：**`_design_2026-10-09_verdict.md`**（含被推翻的旧结论 **O36~O43**）。

| # | 任务 | 状态 | 关键证据（等级） |
|---|---|---|---|
| **1** | **标定能生效**：干掉硬编码默认源 + 面板只认"正在跑的源" + 后端**热重载** | ✅ 完成 | 检测**运行中**保存 → `/status` `scene_annotation_reload_count` **0→1**、`reloaded_at=00:11:30`；面板首帧 `1920×1080`（原来是 1280×576 旧视频）`[三]` |
| **2** | **绘制侧 ROI 过滤**（只动绘制副本，判定链路不碰） | ✅ 完成 | trace 73 帧：收集 982 盏 / **ROI 外 362 盏被挡**；用户点名的 `('yellow',(419,120))` **144 帧全在 ROI 外**、`('red',(275,182))` 72 帧全在 ROI 外 `[三]` |
| **3** | **检测类白名单**（`TRAFFIC_CLASS_WHITELIST`，41 类） | ✅ 完成 | `/status` `class_filter_stats`：`kept=1644 / dropped=252`（全是 `potted plant`）`[三]` |
| — | **两条地雷**（渲染器红绿灯名单不一致 / `LiveMonitor:494` 未定义 `sc`） | ✅ 一并修 | 红绿灯类名收敛为单一 frozenset；`sc` 修复后"左右分流车辆栏"与灯态徽标恢复工作 |
| **4** | **两个框（我上一轮"框预测"引入的回归）** | ✅ 完成 | `_match_track_for_detection()` 多级关联；`_scripts\_verify_two_boxes_fix.py` **20/20**；实时 `box_draw_stats` = `main=2 tracks=2 max_dets_per_track=1 fallback=0` `[三]` |
| — | **灰色框（用户新口径）** | ✅ 完成 | 没拿到 track ID 的框 = **灰框 + 零文字 + 不画箭头**；绿=正常 / 红=违规 / 灰=尚未追踪。用户原话："没有ID要不直接用灰色框就行了……什么都不用显示" |
| — | **回归** | ✅ | `check.mjs` **17/17**、`check2.mjs` **15/15** |

**本轮教训（已写进 `_PROJECT_MAP.md` T81~T91）**，其中三条最容易再踩：
- **T84**：`/status` 里"绘制侧"的 `traffic_lights_collected/drawn`、`box_draw_stats` **在没有浏览器看流时会冻住**（绘制侧不跑）——不是 bug，是读取姿势
- **T86**：**手工 `python -m uvicorn` 重启会静默丢掉 `TUNE_*`**（imgsz 变 1280 / 多跑 `license_plate` / frame_rate 变 3）→ **判定配置永远看 `/status`**
- **T88**：**"源不一致"是标定失效的头号原因**，且会同时坑判定与界面提示
- **T89/T90**：**"两个框"= bbox 精确匹配被预测平移打破**；而"一会儿 ID、一会儿车型"是**关联失败帧把类名当标签画了**（不是第二个框）——用户亲自更正过，见 O42

### ✅ 第五轮（2026-10-09）：**设计讨论，零代码改动**

把用户 11 条观察**全部核实**（只读：grep / 实测接口 / 真实帧跑检测 / 探针 / 看抓拍图），
产出 `_DESIGN_NOTES_2026-10-06.md`。**其中 6 条根因已定位到代码级** —— 第七轮已修掉前 3 项。

**★ 三条最关键结论**：

1. **标定"没起作用"= 两条根因**（设计单 §12.5）：前端**硬编码默认源** + 后端**标注不热重载**
   → **第七轮已修**（见上）。
2. **"开久了像断网" + timeout + 刷新卡 = 同一个根因**（§12.1）：
   MJPEG 生成器**不检测客户端断开** → 僵尸生成器占满 `asyncio.to_thread` 默认线程池 → 全站排队。
   **先让用户导出「系统日志」页 JSON 坐实，再改** —— ⚠ **本轮仍未取证、未修**。
3. **"每车两个框"是我上一轮框预测引入的回归**（§12.3）：
   `bbox_to_track` 按 bbox **精确匹配**，预测把框平移后主循环查不到 → 画 `car`，
   兜底循环又画一次带 ID 的 → **一个 ID 框 + 一个车型框**。
   一行验证：`BOX_PREDICTION=0` 重启 → 两个框应立刻消失。→ **下一项就做它**。


**另两条（本轮新确证，§12.6）**：
- **左侧那盏黄灯被判色/被画**：判定只认 ROI，但**绘制没有任何 ROI 过滤**
  （`_collect_traffic_lights` 把画面里所有判出颜色的灯都塞进 `_last_traffic_lights`）。
  trace 铁证：`('yellow',(419,120))` 出现 252+228 次、`('red',(275,182))` 200 次。
- **盆栽被画成框**：渲染器主循环**只跳过红绿灯**，其余照画；`CLASS_CN_MAP` 有 **107 类**，
  其中 **83 类与交通无关**（`potted plant`/`fire hydrant`/`sports ball`…）。
  修法：在 `process_frame()` 里按**白名单**过滤 `detections`。

### ✅ 第四轮（2026-10-06）：识别框帧率

| 事项 | 证据等级 | 关键证据 |
|---|---|---|
| **★框位置预测**（两次检测之间外推，框跟着车连续滑动） | **三级** | `_verify_predicted_boxes.py`：16 次采样（每 150ms）里 **15 次位置变化**，`RESULT: PASS` |
| **★检测吞吐提升** | 二级 | 1.79 → **2.65 fps**；框的重定位间隔 558 → **378 ms**（−32%） |
| **★模型序列可配置**（裁掉模型文件不存在的 `license_plate`，保留 helmet/lane） | 三级 | `/status` 自报 `model_sequence = vehicle, traffic_light, helmet, lane` |
| **★配置可观测** | 三级 | `/status` 新增 `model_sequence`/`yolo_imgsz`/`box_prediction`/`predicted_boxes`/`prediction_stats` |
| **修标定按钮"未标"警告失效** | 三级 | 连续 12 秒采样，按钮**稳定**显示「⚠（未标）」 |
| **调优参数固化进两个启动脚本** | 二级 | `TUNE_*` 四项，两脚本一致 |
| 前端回归 | 三级 | `check.mjs` **17/17** + `check2.mjs` **15/15** |

> ⚠️ 该轮的框预测**引入了"两个框"回归**（见上 §12.3）—— 修"两个框"时不要顺手把预测删掉，
> 而是**把关联方式改成按 track_id**（预测本身是对的）。

### ⚠️ 素材口径（**别再用错**）

- **★主力演示视频（推荐）** = **`E:\output\_dual_cam_demo\dual_cam_demo_h264.mp4`**
  （1920×1080 / 20 fps / 26 s / **7.5 MB**，H.264）—— 由无损版转出，**同时长同帧率**，
  抽帧对比平均像素差 **2.02/255**；**换它的原因是规避 `cv2` 解码 FFV1 时的原生崩溃**（T99/T100）
- 原无损版 = `E:\output\_dual_cam_demo\dual_cam_demo_lossless.mkv`
  （1920×1080 / 20 fps / **FFV1 / BGRA / 373 Mbps / 1156 MB**）—— 保留为素材母版；
  但**它正是崩溃所在解码路径**，演示建议用 H.264 版
- ⚠ **两版的场景标注是两个键、不共用**：已用
  `_scripts\_copy_scene_config.py` 把标定复制到 H.264 键（两边都 `ROI=4`、`scope=roi`）；
  以后**换素材（改文件名/改编码）后若发现 `/status` 的 `scope=frame`，就是标注没跟过去**，跑一次该脚本即可（T101）
- `E:\output\_demo_scene\red_light_demo_key_lossless.mkv` 是**老素材、色调有问题** → **勿用于演示**

### ⚠️ 后端当前实例的实情（2026-10-10 23:2x 起）

- 启动方式 = `cmd start` 拉起，**带 `TUNE_*` 调优**，**不带 `--reload`**
- **当前数据源 = H.264 版演示视频**（`/status` 的 `video_path` 可核对），`scope=roi`
- 自报配置：`models=vehicle,traffic_light,helmet,lane` / `imgsz=960` / `frame_rate=6` / `tl_color_model=tl_color_cnn5_carla.pt` `[一]`
- **运行时设置已落盘**：`E:\output\1\api\output\runtime_settings.json`（`cloud_review=false` / `cloud_consult=false` / `loop_dedup_sec=300`）—— **重启不再重置**（T92）
- **下次改后端请用 `E:\output\1\restart-backend.bat`**（手工启动会丢 `TUNE_*`，见 T86）
- ⚠ **不要只杀 `python.exe` 来停后端**：两个 `.bat` 用 `cmd /k` 起它，父窗口会留成**空白黑窗口**（2026-10-10 我连续重启留下 8 个空壳，用户当场质问）。清理前先确认 `Get-Process python` 只剩 1 个，再关那些命令行只有 `cmd /k cd /d E:\output\1` 的空壳。详见 T98

---

## 二·补、未完成清单（**以设计单 §11.0 为准**）

| 序 | 任务 | 根因状态 |
|---|---|---|
| **1** | 标定热重载 + 干掉硬编码默认源 + 面板源绑定"运行源" | ✅ **第七轮已完成并验证** |
| **2** | **绘制侧 ROI 过滤**（左侧黄灯不该画/不该判） | ✅ **第七轮已完成并验证** |
| **3** | **检测类白名单**（盆栽等 83 个无关 COCO 类） | ✅ **第七轮已完成并验证** |
| **4** | **两个框（改按 track_id 关联）** | ✅ **已完成并验证**（§12.3；含"灰框=尚未追踪"新口径 —— 绿=正常/红=违规/**灰=未追踪无文字**） |
| **5** | 断网 / timeout / 刷新卡（**原判"MJPEG 僵尸流"**） | ⚠ **已取证、且原结论被推翻**：真身是**后端进程原生崩溃**（`cv2` 自带 FFmpeg / `0xc000001d`，见 T99）+ 另一种**"进程假死"型超时**（T112）。**规避** = 换 H.264 素材（已转好、标注已同步）；**根因未修**，已移交 GPT6（`_GPT6_HANDOFF_BRIEF.md`） |
| **6** | 云端开关"自动打开"（`pushSettings` 连带推送 **+ 重启即重置**） | ✅ **已完成并验证**（§十一。后端持久化 + 前端拆开推送 + 取消 fail-open） |
| 7 | 画面违规文字（用户已定**方案 a**，保留红/绿框配色） | ✅ 已定 |
| 8 | 录违停视频（**帧率已定 = 30 fps**，用户 2026-10-10 确认） | ✅ 已定，待录 |
| 9 | 旧事件视频 2×（只重封过 `evt_11200_18_60c808`） | 待用户定 |
| 10 | 审计出的前后端不一致（分歧审核 422 / 协作统计归零 / 证据图 404 / 通知设置假开关） | 已列清单 |
| **11** | ✅ **附带修掉**：`/settings` 点导出报 `Converting circular structure to JSON` | 三级（`_uicheck\_run_loggerexport.mjs` 6/6）；详见 §十一.3 |
| **12** | ✅ **附带修掉的取证三项**：① 同一违规**每圈重复取证**（5 分钟 9 条 → 3.4 条，`loop_dedup_sec`）② 视频时间**变负**导致取证窗口错位（14 条负 ID，`_loop_frame_base` 未归零）③ 事件落库时间戳**是 1970**（库里 **566** 行，改用 `wall_time`；2026-10-12 复核） | 一级 + 三级，见 `_design_2026-10-09_verdict.md` §十一.2 |
| **13** | ⚠ **新发现（未修，需用户定）**：后端被 `cv2` 自带 FFmpeg 解码器**原生崩溃**拖死（`opencv_videoio_ffmpeg500_64.dll` / `0xc000001d` / 同一偏移 `0x2e9930`）**已 4 次**。与本轮 Python 改动无关（不碰解码路径） | 一级（Windows 事件日志 + 崩溃转储） |
| **14** | ⚠ **未修，需用户定**：库里 **566 条事件**的 `trigger_time` 是 **1970 年**（历史脏数据；**2026-10-12 只读查库定案**：`traffic_events` 共 3209 行，`substr(cast(trigger_time as text),1,4)='1970'` → **566**，`created_at` 无 1970）。回填属**改历史数据**，需用户明确同意（会先备份 DB） | 一级 |
| **15** | ✅ **修掉"违规告警栏毫无反应"** —— 真凶是**我上一轮加的 `loop_dedup_sec` 把"展示"也一起掐掉了**（一圈墙钟约 217 秒 < 抑制窗口 300 秒 → 后面整圈被压掉，右栏实测空 **129 秒**）。现在**抑制只作用于"存证据/计费"**，重复违规仍喂展示（标「重复出现」）。**实测右栏每约 30 秒必现一次；浏览器侧 API 94 次 / DOM 90 次一致** | 三级（`_run_panel_dom_check.mjs`） |
| **16** | ✅ **按用户口径调整**：**车离开画面就撤掉告警卡**（用户："汽车离开画面后就不用显示了……只要下方的违规抓拍证据能有记录就行"）；我一度做的「已离开画面」保留卡**已撤回** | 三级（`_run_evidence_info_check.mjs` 5/5） |
| **17** | ✅ **抓拍证据补上关键信息**：`/api/realtime/evidence` 现在回带 **违法时间**（`violation_at`，落库时间）+ 抓拍时间（`captured_at`，文件名）+ 车辆ID + 置信度 + 车牌；前端卡片显示 `闯红灯 / 2026-10-11 00:21:07 / ID1 · 95%`。实测两者只差 **30 毫秒**（无错位） | 三级 |
| **18** | ✅ `/settings` 导出崩溃已修 + 新增「复制诊断摘要」按钮 | 三级（`_run_loggerexport.mjs` 6/6） |
| **19** | ✅ **告警栏改成"推送驱动"（回答"为什么比画面标注慢"）**：画面是**推**（标注直接画进 MJPEG，20fps）、告警栏是**问**（轮询）→ 实测后端→接口延迟 **0ms**，慢的全在轮询等待。已接上项目本来就有、但**前端从来没人接**的 `/api/realtime/violations/stream` WebSocket，收到推送即刷新 | 三级（浏览器侧 `收到 violation_detected 推送: 2 次`） |
| **20** | ✅ **修掉一个潜伏很深的缺陷：WebSocket 推送被静默吞掉**。症状极具迷惑性：`push_scheduled` 在涨、前端日志显示"已连接"、**但一条都收不到**（我为此绕了三轮）。两个独立缺陷叠加：① Vite `/api` 代理**没开 `ws: true`** → 前端改**直连 `127.0.0.1:8001`**；② 后端 `send_json` 异常**无任何日志**（只默默移除客户端）→ 现在计数 + warning，并在 `/status` 暴露 `ws_push` 四个字段 | 三级（修后 Python 客户端 2/2、浏览器 2 次收到） |

### 📌 第 1~10 项之外的其余待办（保留在此，避免丢失）

- **拆解单帧 ~350 ms 的非模型成本**（JPEG 编码/绘制/事件/落库各占多少）——
  想继续提检测帧率只能从这里下手（模型已无可榨）
- `uploads/` 已 **2234 MB / 4526 文件**，**保留策略待用户定**（清理属删除，必须先问）
- 剩余违规：**违停 → 压线 → 逆行 → 超速**
  （违停/超速只是素材问题；**压线缺车道线标注**；**逆行需先定"车道方向怎么配"且现机位不适合验**）
- 云端复核关闭后**没有批量确认入口**
- **给"上一个对话的前端提示词"**（用户要求，尚未产出）
- CARLA 物理级验证（用户明确"暂时放着"）：`_scripts\_carla_calibration_markers.py`，
  需先启 CARLA（~6 GB 显存，与后端不能舒适共存），验的是**测速几何**、**不覆盖闯红灯**
- 审计出的前后端不一致完整清单见 `_calibration_panel_verdict.md` §六
  （分歧审核两条 🔴 422 / 协作统计归零 / 设备在线恒 0 / 证据图 404 / 通知设置假开关）
  > ⚠ `resolver_id` 无来源（前端无登录态）—— 修前需用户定：硬编码管理员 id 还是接登录

---

## 三、用户明确的行为纪律（务必遵守）

1. **动手前先复述用户要求，等确认**（协议 §4.1）
2. **耗时测试由用户执行** —— ⚠ **已被用户 2026-10-06 明确覆盖**：代码/脚本/文档/环境类工作**一律由 AI 直接执行**，
   用户只做"实际效果测试 + 设计建议"。长任务放后台 job，别占死会话。
3. **途中遇重大分歧点当场问**（§4.3）
4. **先读 `_PROJECT_MAP.md`，禁止重复造轮子**（§4.4）
5. **主动提醒用户换对话**（§4.5）
6. **影响大的配置（帧率/分辨率/编码）必须先问用户**
7. **不要放慢视频、不要靠"堆算力"**

---

## 四、CARLA 硬知识（仍然有效）

- **投影公式（已修符号）**：`fwd=(cos p·cos y, cos p·sin y, sin p)`、`right=(−sin y, cos y, 0)`、
  `up=(−sin p·cos y, −sin p·sin y, cos p)`。pitch 向下为负。
  **切勿用 `cam_tf.get_inverse_matrix()`**。
- **车辆行为**：必须 `set_autopilot(True, tm.get_port())`；**不要** `enable_constant_velocity`。
  闯红灯用 `tm.ignore_lights_percentage(veh, 100.0)`。
- **灯态**：`set_green/yellow/red_time` **无效**；只有逐 tick `set_state()` 才准。
  `freeze(True)` 会永久钉住状态。
- **CARLA 重启后**：红绿灯 **Actor ID 会变**，spectator **回默认值**，有时红灯数为 0 需 `load_world`。
  → **脚本必须按"停止线地理坐标"找灯，不能硬编码 ID**。
- **相机本机位**：`(-15.720, -63.145, 5.732)` pitch `-23.445` yaw `179.536`，1920×1080 fov **90（水平）**。
  ⚠ `camera_height_m` 是**离路面**高度 → 填 **5.0**（相机世界 z=5.732、路面 z≈0.73）。
  ⚠ **地平线**：`horizon_y = H/2 + f·tan(pitch)`、`f = W/(2·tan(fov/2))` —— **1920×1080 时为 123.7**（画面内偏上）；
  **1280×576 时为 −10.5**（负值表示"地平线在画面上方之外"，俯角大时正常；见 O28 与工作区记忆 `carla-camera-and-projection`）。
  ⚠ **2026-10-12 更正**：本文件此前把两个画幅的值**写反了**（`_PROJECT_MAP.md` T54 与记忆一致，以它们为准）。
- **读图铁律**：CARLA `raw_data` 是 **BGRA**，`[:, :, :3]` **就是 BGR**，**绝不能再加 `[::-1]`**。

---

## 五、服务与命令速查

```powershell
# ★日常启动：双击  E:\output\1\start-all.bat     （已探测端口，不会撞车）
# ★改了后端：双击  E:\output\1\restart-backend.bat（按端口找 PID + 校验是 python 才杀 + 自检）
# 详细说明：E:\output\_STARTUP_GUIDE.md

# 手工起后端（工作目录必须是项目根；PYTHONPATH 不能少）
$env:PYTHONPATH='E:\output\1\api;E:\output\1'
cd E:\output\1 ; & 'C:\miniconda\envs\zhitong-gpu\python.exe' -m uvicorn app:app --host 127.0.0.1 --port 8001

# 前端（本机 node 在 E:\node.exe）
cd E:\output\1\web-admin ; npm run dev

# CARLA（重启后灯 ID 会变；脚本按停止线坐标找灯，不要硬编码 ID）
E:\output\1\carla\CARLA_0.9.16\CarlaUE4\Binaries\Win64\CarlaUE4-Win64-Shipping.exe -carla-rpc-port=2000 -quality-level=Epic -nosound

# ★管理端标定面板的自动化回归（真实浏览器，约 40 秒，17 项断言）
$env:PATH = 'E:\;' + $env:PATH
cd E:\output\_uicheck ; & 'E:\node.exe' check.mjs      # 17 项
cd E:\output\_uicheck ; & 'E:\node.exe' check2.mjs     # 15 项

# ★第七轮新增的三个验证脚本（都可复跑）
# ① 后端自校验 25 项：白名单 / 热重载 / ROI 谓词（用临时目录的假场景文件，零副作用，约 30 秒）
$env:PYTHONPATH='E:\output\1\api;E:\output\1'
& 'C:\miniconda\envs\zhitong-gpu\python.exe' -B E:\output\_scripts\_verify_hotreload_and_filter.py
# ② 端到端 HTTP 探针：真跑演示视频，验"运行中保存 -> 热重载"（约 60 秒；会自己恢复运行状态）
& 'C:\miniconda\envs\zhitong-gpu\python.exe' -B E:\output\_scripts\_verify_fixes_e2e.py
# ③ trace 逐帧核算：ROI 过滤 + 判定自洽（需先把 trace 文件名传进去）
& 'C:\miniconda\envs\zhitong-gpu\python.exe' -B E:\output\_scripts\_verify_trace_roi_filter.py E:\output\_rt_trace_roi_filter_20261010.jsonl

# 测速标定端到端验证（真实渲染帧 + YOLO，约 1 分钟）
& 'C:\miniconda\envs\zhitong-gpu\python.exe' -B E:\output\_scripts\_validate_speed_calibration.py

# 判色/闯红灯评测（需带 trace 启动后端，见 _redlight_accuracy_verdict.md §五）
```

> ⚠ **判定"后端配置对不对"永远看这三个字段**（手工启动极易漏掉 `TUNE_*`，见 T86）：
> `GET http://127.0.0.1:8001/api/realtime/status` → `model_sequence` 应为
> `vehicle,traffic_light,helmet,lane`、`yolo_imgsz` 应为 **960**、`frame_rate` 应为 **6**。

- 端口：CARLA **2000** / 后端 **8001** / 前端 **5173**（固定）
- **重启后端后 openapi 应为 132 operations**（已实测）

---

## 六、交接自检（协议 §9.4）

- [x] 只读 3 个文件能否知道"项目有什么功能" → `_PROJECT_MAP.md` 已补本轮 4 项能力（§一 第 9/10 条 + §二 表项）
- [x] 能否知道"上一步做到哪、下一步做什么" → 本文 §二 + §二·补（**未闭环：第 5 / 8 / 9 / 10 / 13 / 14 项；第 13/14 需用户决策**）
- [x] 能否知道"哪些结论已被推翻" → `_design_2026-10-09_verdict.md` §四（**O36~O43**；其中 O40/O41 是我自己本轮的两次错判）
- [x] 交接文件里的路径是否都真实存在 → 已逐个核对（本文件提到的 3 个脚本、2 个配置文件、trace 文件均已 `Test-Path` 确认）
- [x] 是否把"推断"写成"事实" → 未验证项已标"未取证/未动"；
      **本轮我自己的错判（O40 断言写错两次报 FAIL / O41 手工重启丢 `TUNE_*`）也已登记**

---

## 七、★已被推翻的旧结论（不要再引用）

> 本轮新增 **O36~O43** 见 `_design_2026-10-09_verdict.md` §四/§9.3。以下是**跨轮仍然有效**的更正：

| 曾经的说法 | 真相 |
|---|---|
| **"运行中保存的标定，后端会自己用上"** | ❌ 修前只有 `start_camera()` 加载一次 → 必须「停止→开始」；且 `/status` 仍报 `scope=roi`，**看起来在用、实际用旧值**。**2026-10-10 已修**（O36） |
| **"标定面板显示的是当前画面"** | ❌ 面板跟输入框，输入框被硬编码旧视频重置 → 首帧 1280×576 是**旧 B 站视频**。**已修**（O37） |
| **"左侧黄灯被识别是判色/判定的问题"** | ❌ 判定一直只认 ROI；真相是**绘制侧完全没有过滤**。**已修**（O38） |
| **"盆栽框是渲染器的问题"** | ⚠️ 半错：渲染器只是放大器，根因是**检测出口没有类白名单**。**已修**（O39） |
| "CARLA 红灯渲染成青蓝色，是地图资产缺陷" | ❌ 是读图多加了一次 `[::-1]` 导致红蓝互换 |
| "绿色正常、红色异常" | ❌ 绿"正常"是假象：G 通道在 R/B 互换中位置不变 |
| "`Proj.up = [sp·cy, sp·sy, cp]`" | ❌ 符号错，导致连续 5 轮实验建立在错误坐标上 |
| "`ground_plane_ppm` 偏小 0.61 倍" | ❌ 对照的是**损坏的 CSV**（像素列是模型输出）。公式比值 1.001~1.003 是对的 |
| "`ground_truth_dual.csv` 的 580 点可以验证标定" | ❌ `cam1_u/v` 是 `Proj.project()` 的模型输出（自证）；只有 `(x,y)` 可信 |
| "bbox 中心 = 车辆位置，可直接反投影测速" | ❌ 中心在车身上方约 0.7 m |
| "场景灯态 = 画面里最危险的那盏灯" | ❌ 必须取**受控方向**那盏（O19）；不标 ROI 每循环误报 5~7 次 |
| "前端保存场景标注会抹掉 ROI/停止线/yaw" | ❌ `save_scene()` 默认 `merge=True`，只写传入字段（O25） |
| "「云端复核」勾选框能省 cloud 费用" | ❌ 那个只管**逐帧咨询**；事件级复核此前**完全没有闸门**（O30） |
| "运行中实例是旧进程，重启后 openapi 才是 132" | ✅ 已闭环，重启后实测 132 |
| **"事件视频只是素材短，没有速度问题"** | ❌ 写死 10fps 而源 20fps → **播放快一倍**，4855 个全中（O32） |
| **"系统设置里的 AI 开关能控制收费"** | ❌ 那两个是**装饰品**；关了照收（O33） |
| **"上传不了大视频是 50MB 上限的问题"** | ⚠️ 真正让视频上传**必失败**的是 `result` 未初始化（O34） |
| **"我上一轮误删 ffmpeg 缓存导致项目转码受损"** | ❌ 项目优先用 `imageio_ffmpeg` 自带 7.1，转码一直正常（O35） |


