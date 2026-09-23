# 项目整理与基线报告

> 日期: 2026-09-23
> 执行者: Trae IDE (豆包大模型)
> Git 基线提交: `9e954f0`
> 上一提交: `acf9541` (Initial commit, 2026-06-10)

---

## 1. 当前项目结构

```
e:\output\                          # Git 仓库根
├── .gitignore                       # 根级 .gitignore (基础规则)
├── _TASK-*.json                     # AI 任务执行记录 (100+ 文件)
├── TASK-*-NOTICE.md                 # AI 任务通知文件 (30+ 文件)
├── _COMANDANTE_ROLE_DEF.md           # 指挥官角色定义
├── _SKILLS_CATALOG.md                # 技能清单
├── _TASK_HISTORY.json               # 任务历史
├── IDE_EXEC_RULES.md                 # IDE 执行规则
├── PROJECT_HANDOVER_REPORT.md       # 项目交接报告
├── PROJECT_FILE_INDEX.md            # 项目文件索引
├── HANDOVER_UPDATE_RULE.md          # 交接更新规则
├── K230开发指南_智瞳项目专用.md       # K230 开发指南
├── PAPER_*.md                       # 论文材料 (3个文件)
├── md_to_docx.py                    # Markdown 转 Word 工具
├── screenshots/                     # 截图目录
├── .uploads/                        # 上传临时目录
└── 1/                               # === 项目代码根 ===
    ├── .gitignore                   # 项目级 .gitignore (新建)
    ├── .pai/                        # PAI 技能配置 (7文件)
    ├── README.md                    # 项目说明
    ├── PROJECT_BASELINE.md          # 项目基线文档
    ├── PROJECT_ISSUES.md            # 项目问题文档
    ├── TASKS.md                     # 任务列表
    ├── DEPLOYMENT.md                # 部署文档
    ├── RUNTIME_ISSUES.md            # 运行时问题
    ├── EXECUTOR_CAPABILITY_REPORT.md # 执行能力报告
    ├── NATIONAL_SPRINT_BRIEF.md     # 国家冲刺简报
    ├── NATIONAL_SPRINT_RESPONSE.md  # 国家冲刺回应
    ├── start-all.bat                # 一键启动脚本
    ├── start_zhitong.bat            # 旧版启动脚本
    ├── 项目问题记录文档.md             # 问题记录
    ├── torch-*.whl                  # PyTorch 安装包 (2.4GB, 已 gitignore)
    │
    ├── api/                         # === FastAPI 后端 (58文件) ===
    │   ├── app.py                   # ★ 主入口 (uvicorn app:app)
    │   ├── database.py              # 数据库连接 (zhitong_violations.db)
    │   ├── models.py                # SQLAlchemy 数据模型
    │   ├── schemas.py               # Pydantic 模型
    │   ├── config.py                # 配置类 (环境变量)
    │   ├── config_manager.py        # 持久化配置管理
    │   ├── config_runtime.json      # 运行时配置 (已 gitignore, 含密钥)
    │   ├── requirements.txt         # Python 依赖
    │   ├── start_api.bat            # API 启动脚本
    │   ├── yolov8n.pt               # YOLOv8 模型权重 (6.5MB)
    │   ├── zhitong_violations.db    # ★ 主数据库 (209KB)
    │   ├── zhitong.db               # 旧数据库 (49KB, 仅 main.py 使用)
    │   ├── image_recognizer.py      # 图像识别核心 (YOLO+豆包+DeepSeek)
    │   ├── cloud_collaborator.py    # 端云协作管理器
    │   ├── realtime_detector.py    # 实时违规检测
    │   ├── traffic_event_engine.py  # 交通事件引擎
    │   ├── circular_frame_buffer.py # 循环帧缓存
    │   ├── evidence_chain.py        # 证据链
    │   ├── behavior_engine.py       # 行为引擎
    │   ├── scene_perception.py      # 场景感知
    │   ├── vehicle_tracker.py       # 车辆追踪器
    │   ├── virtual_tracker.py       # 虚拟追踪器
    │   ├── violation_rules.py       # 违规规则引擎
    │   ├── multi_frame_validator.py # 多帧验证
    │   ├── ptz_controller.py        # PTZ 控制器
    │   ├── carla_source.py          # CARLA 数据源
    │   ├── k230_plate_client.py     # K230 车牌客户端
    │   ├── license_plate_recognizer.py # 车牌识别
    │   ├── main.py                  # ⚠ 旧入口 (使用 zhitong.db)
    │   ├── migrate_db.py            # 数据库迁移
    │   ├── seed_demo_data.py        # 演示数据填充
    │   ├── backend_evaluation.py    # 后端评估
    │   ├── DEVELOPMENT_GUIDE.md     # 开发指南
    │   ├── routers/                 # API 路由 (9个模块)
    │   │   ├── violations.py       # 违规管理
    │   │   ├── wechat.py            # 微信小程序
    │   │   ├── system.py            # 系统管理
    │   │   ├── statistics.py        # 统计分析
    │   │   ├── devices.py           # 设备管理
    │   │   ├── appeals.py           # 申诉管理
    │   │   ├── auth.py              # 认证授权
    │   │   ├── cloud_collab.py      # 端云协作
    │   │   ├── realtime.py          # 实时监控
    │   │   └── rtsp_stream.py       # RTSP 流
    │   ├── rule_engine/             # 规则引擎插件
    │   │   ├── __init__.py
    │   │   ├── base_plugin.py
    │   │   └── plugin_loader.py
    │   ├── uploads/                 # 上传图片 (已 gitignore)
    │   └── test_*.py                # 测试文件 (10个, 混在源码中)
    │
    ├── web-admin/                   # === Vue 3 前端 (34文件) ===
    │   ├── package.json             # 依赖配置
    │   ├── package-lock.json
    │   ├── vite.config.js
    │   ├── index.html
    │   ├── clean-vite-temp.cjs
    │   └── src/
    │       ├── App.vue              # 根组件
    │       ├── router/index.js      # 路由
    │       ├── api/                 # API 调用
    │       ├── views/               # 页面 (17个)
    │       │   ├── Dashboard.vue
    │       │   ├── ViolationList.vue
    │       │   ├── ViolationDetail.vue
    │       │   ├── RealTimeMonitor.vue
    │       │   ├── EventCenter.vue
    │       │   ├── EventDetail.vue
    │       │   ├── AIDetect.vue
    │       │   ├── AITrace.vue
    │       │   ├── CollabStats.vue
    │       │   ├── DisagreementList.vue
    │       │   ├── Statistics.vue
    │       │   ├── Settings.vue
    │       │   ├── QuotaMonitor.vue
    │       │   ├── DeviceList.vue
    │       │   ├── AppealList.vue
    │       │   ├── SystemLog.vue
    │       │   └── About.vue
    │       ├── components/          # 组件 (3个)
    │       │   ├── ConfidenceBar.vue
    │       │   ├── StatusBadge.vue
    │       │   └── TypeTag.vue
    │       ├── styles/              # 样式
    │       └── utils/              # 工具
    │
    ├── zhitong/                     # === 旧版/单机程序 (28文件) ===
    │   ├── main.py                  # 旧版主入口
    │   ├── config.py                # 旧版配置
    │   ├── README.md
    │   ├── detector.py              # YOLO 检测
    │   ├── tracker.py                # DeepSORT 跟踪
    │   ├── violation_detector.py    # 违规检测
    │   ├── speech.py / speech_manager.py # 语音播报
    │   ├── cloud.py / cloud_manager.py    # 云端服务
    │   ├── logger.py                # 日志
    │   ├── video_capture.py         # 视频采集
    │   ├── tensorrt_engine.py       # TensorRT 引擎
    │   ├── api_client.py             # API 客户端
    │   ├── demo_script.py            # 演示脚本
    │   ├── k230_app/                # K230 端应用 (12文件)
    │   ├── models/yolov8n.pt        # 模型 (重复副本)
    │   ├── data/                     # 数据集 (训练数据已 gitignore)
    │   ├── training/                 # 训练工具 (已 gitignore)
    │   └── data_tools/              # 数据采集工具 (已 gitignore)
    │
    ├── tests/                       # === 测试套件 (8文件) ===
    │   ├── __init__.py
    │   ├── test_circular_frame_buffer.py
    │   ├── test_cloud_collaborator_event.py
    │   ├── test_core.py
    │   ├── test_evidence_chain.py
    │   ├── test_multi_frame_validator.py
    │   ├── test_task029_integration.py
    │   └── test_traffic_event_engine.py
    │
    ├── digital_twin/                # 数字孪生 (6文件)
    ├── miniprogram/                 # Taro 小程序 (39文件)
    ├── wechat-miniprogram/          # 原生微信小程序 (89文件)
    ├── beforeness/                  # 旧/实验脚本 (4文件)
    ├── docs/                        # 技术文档 (13文件)
    ├── presentation/                # 答辩材料 (22文件)
    ├── scripts/                     # 脚本 (1文件)
    ├── carla/                       # CARLA 仿真 (仅代码, 环境已 gitignore)
    ├── K230/                        # K230 硬件资料 (已 gitignore)
    ├── 固件备份/                     # 固件备份 (已 gitignore)
    ├── .venv/                       # Python 虚拟环境 (已 gitignore)
    └── output/logs/                 # 运行日志 (已 gitignore)
```

---

## 2. 整理了什么

| 操作 | 详情 |
|------|------|
| ✅ 新建 `.gitignore` | 项目根 (`1/.gitignore`) 创建完整 .gitignore，覆盖 Python/Node/大文件/模型/数据库/上传/日志/CARLA/K230/训练数据/构建缓存等 |
| ✅ 清理 `__pycache__` | 全项目递归删除所有 `__pycache__` 目录 (自动重生,不影响运行) |
| ✅ Git 暂存 | 461 个文件纳入版本控制 (核心源码+文档+测试+配置) |
| ✅ Git 基线提交 | `9e954f0` — 整理完成基线提交 |
| ✅ 验证 | 6 个核心 Python 文件语法通过, 7 个测试文件语法通过 |

---

## 3. 删除了什么以及为什么

### 从 Git 工作区删除 (已废弃的环境脚本,工作区中已不存在)

| 文件 | 删除原因 |
|------|---------|
| `fix_env.ps1` | 旧版 Python 环境修复脚本，已被 `api/requirements.txt` + `.venv` 替代 |
| `fix_python_env.bat` | 同上 |
| `install_deps.bat` | 旧版依赖安装脚本，已被 `api/start_api.bat` 内置安装逻辑替代 |
| `install_packages.py` | 旧版包安装脚本，已被 pip 直接安装替代 |
| `requirements.txt` (根) | 根级依赖文件，已被 `api/requirements.txt` 替代 |
| `setup_python_env.ps1` | 旧版环境配置脚本，已被 `.venv` 替代 |
| `yolov8n.pt` (根) | 根级重复模型，已移至 `api/yolov8n.pt` (代码实际加载路径) |

> **注意**: 以上文件在本次整理前已被工作区删除 (标记为 `D` in git status)。本次只是将其纳入基线提交确认删除。

### 通过 .gitignore 排除 (不删除文件,仅排除出版本控制)

| 排除项 | 原因 |
|--------|------|
| `torch-*.whl` (2.4GB) | 二进制安装包,不应纳入版本控制 |
| `config_runtime.json` | 含明文 API 密钥 (sk-*),安全风险 |
| `api/uploads/*.jpg` | 运行时上传图片,非种子数据 |
| `api/diag_frame.jpg` | 诊断临时图片 |
| `carla/CARLA_0.9.16/` | CARLA 仿真环境 (数千文件) |
| `K230/` | 硬件资料 (6K+ 文件) |
| `固件备份/` | 固件二进制备份 |
| `zhitong/training/` | 训练数据/模型 (数千文件) |
| `zhitong/data_tools/` | 数据采集工具缓存 (21K 文件) |
| `zhitong/k230_training/` | K230 训练数据 |
| `zhitong/data/*/` | 训练数据集 (helmet/traffic_light/vehicle) |
| `zhitong/data/extracted_frames/` | 抽帧结果 |
| `zhitong/data/test_images/` | 测试图片 |
| `.venv/` | Python 虚拟环境 |
| `node_modules/` | Node.js 依赖 |
| `__pycache__/` | Python 缓存 |
| `miniprogram/.swc/` | SWC 构建缓存 |
| `runs/` | YOLO 推理输出 |
| `test_results/` | 测试结果 |
| `output/logs/*.log` | 运行日志 |

---

## 4. 哪些内容保留以及为什么

### 保留的疑似废弃文件 (记录但不删除)

| 文件/目录 | 状态 | 保留原因 |
|-----------|------|---------|
| `api/main.py` | 旧入口点 | 使用 `zhitong.db`,已被 `app.py` 替代。但可能被其他脚本引用,不确认安全删除 |
| `api/zhitong.db` | 旧数据库 | 仅 `main.py` 使用 (49KB)。保留以防回退需要 |
| `beforeness/` | 实验目录 | 含 `blind_yun.py`, `photo_ai_analysis.py`, `untitled_2.py`, `yolov8n.pt`。疑似旧版实验代码,但未确认无引用 |
| `miniprogram/` | Taro 小程序 | 与 `wechat-miniprogram/` 并存。PROJECT_FILE_INDEX 引用 wechat-miniprogram,但 miniprogram 可能有不同用途 |
| `start_zhitong.bat` | 旧启动脚本 | 可能用于启动旧版 zhitong/main.py |
| `backend_evaluation.py` + 报告 | 评估脚本 | 历史评估产物,有参考价值 |
| 5份 `yolov8n.pt` 副本 | 重复模型 | 分布在 api/, beforeness/, data/models/, zhitong/models/, zhitong/training/models/。无法确认所有代码路径都不引用 |

### 保留的已知安全问题 (本次不修复)

| 问题 | 文件位置 | 严重度 |
|------|---------|--------|
| 硬编码 API Key | `api/image_recognizer.py:206` (`sk-e828ff...`) | P0 |
| 明文 API 密钥 | `api/config_runtime.json` (sk-*) | P0 (已 gitignore) |
| 硬编码 JWT Secret | `api/main.py:15` (`zhitong_jwt_secret_key_2026`) | P1 |

---

## 5. 当前启动方式

### 主启动 (开发环境)

```bash
# 一键启动 (后端 + 前端)
e:\output\1\start-all.bat
```

**后端 API**:
- 命令: `py -3 -m uvicorn app:app --host 127.0.0.1 --port 8001 --reload`
- 工作目录: `e:\output\1\api`
- 文档: http://127.0.0.1:8001/docs
- 健康检查: http://127.0.0.1:8001/health

**前端管理后台**:
- 命令: `npm run dev`
- 工作目录: `e:\output\1\web-admin`
- 地址: http://localhost:5173

### 独立启动 (旧版/单机)

```bash
# API 独立启动 (带环境检查)
e:\output\1\api\start_api.bat
# → 使用 C:\miniconda\envs\zhitong-gpu\python.exe

# 旧版单机程序
cd e:\output\1\zhitong
python main.py
```

### 端口分配

| 服务 | 端口 |
|------|------|
| 后端 API | 8001 |
| 前端 Web | 5173 |
| 数字孪生 | 5000 |
| CARLA | 2000 |

---

## 6. 当前已知问题

### P0 — 必须修复

| 编号 | 问题 | 影响 |
|------|------|------|
| P0-1 | 硬编码 API Key (`image_recognizer.py:206`) | 密钥泄露风险 |
| P0-2 | `config_runtime.json` 明文存储密钥 | 已 gitignore,但文件仍在磁盘 |
| P0-3 | Git 基线之前只有 1 个提交,大量代码未纳入版本控制 | ✅ 本次已修复 |
| P0-4 | 真实端到端闭环未验证 | 后端/前端/检测/云端均未实际启动验证 |

### P1 — 应修复

| 编号 | 问题 | 影响 |
|------|------|------|
| P1-1 | `pytest` 未安装 | 测试套件无法运行 (7个测试文件语法正确但未执行) |
| P1-2 | `api/main.py` 旧入口与 `app.py` 并存 | 路径/数据库引用混乱 |
| P1-3 | 两套小程序目录并存 | 边界不清晰 |
| P1-4 | `beforeness/` 实验目录 | 用途不明 |
| P1-5 | 5份 `yolov8n.pt` 重复 | 存储浪费,可能加载错误副本 |
| P1-6 | `cloud_collaborator.py` 参数错位 (B1/B2) | `analyze_with_claude` 3参数调2参数函数 |

### P2 — 后续优化

| 编号 | 问题 |
|------|------|
| P2-1 | 测试文件混在 `api/` 源码中 (10个 test_*.py) |
| P2-2 | `api/config.py` 与 `api/config_manager.py` 职责重叠 |
| P2-3 | 无 `.env` 文件,密钥通过 `config_runtime.json` 或环境变量管理 |
| P2-4 | `torch-2.5.0+cu121-cp312-cp312-win_amd64.whl` (2.4GB) 在项目根 |

---

## 7. 当前 Git 基线

```
分支: main
提交历史:
  9e954f0  chore: project audit and baseline establishment (2026-09-23)
  acf9541  Initial commit (2026-06-10)

本次提交统计:
  461 files changed, 146,843 insertions(+), 271 deletions(-)

工作区状态: clean (干净)
```

### 本次提交包含的变更

| 类型 | 数量 | 说明 |
|------|------|------|
| 新增 (New) | ~440 | 所有此前未跟踪的核心源码、文档、测试、配置 |
| 修改 (Modified) | 12 | app.py, database.py, models.py 等核心文件 |
| 删除 (Deleted) | 7 | 废弃环境脚本 + 重复根级 yolov8n.pt |
| 新建 .gitignore | 1 | 项目级 Git 忽略规则 |

### .gitignore 排除的大文件/目录

| 排除项 | 文件数 | 体积 |
|--------|--------|------|
| `zhitong/data_tools/` | ~21,000 | 数 GB |
| `K230/` | ~6,000 | 数 GB |
| `zhitong/training/` | ~600 | 数百 MB |
| `torch-*.whl` | 1 | 2.4 GB |
| `carla/CARLA_0.9.16/` | ~3,000 | 数 GB |
| `node_modules/` | ~1,000 | 数百 MB |
| `.venv/` | ~5,000 | 数百 MB |

**总计排除约 36,000+ 文件,使 Git 仓库从 34,000+ 文件降至 461 文件。**

---

## 8. 建议 DeepSeek Harness 接管时优先阅读的文件

### 第一优先 (理解项目全貌)

1. **`e:\output\1\PROJECT_BASELINE.md`** — 项目基线快照,含技术栈/目录/验证状态/风险
2. **`e:\output\1\README.md`** — 项目说明,含架构图和启动方式
3. **`e:\output\PROJECT_HANDOVER_REPORT.md`** — 完整项目交接报告 (25KB)
4. **`e:\output\1\PROJECT_AUDIT_AND_BASELINE_REPORT.md`** — 本报告

### 第二优先 (理解代码结构)

5. **`e:\output\PROJECT_FILE_INDEX.md`** — 项目文件索引,含每个文件用途和核心函数
6. **`e:\output\1\api\app.py`** — 后端主入口,理解路由注册和生命周期
7. **`e:\output\1\api\config.py`** — 配置类,理解端口/路径/密钥管理
8. **`e:\output\1\api\database.py`** — 数据库连接,理解数据层

### 第三优先 (理解问题)

9. **`e:\output\1\PROJECT_ISSUES.md`** — 已知问题清单
10. **`e:\output\1\RUNTIME_ISSUES.md`** — 运行时问题
11. **`e:\output\1\DEPLOYMENT.md`** — 部署文档
12. **`e:\output\1\TASKS.md`** — 任务列表和状态

### 第四优先 (深入模块)

13. **`e:\output\1\api\DEVELOPMENT_GUIDE.md`** — 开发指南 (42KB,最详细的代码文档)
14. **`e:\output\1\api\image_recognizer.py`** — 图像识别核心 (YOLO+豆包+DeepSeek,97KB)
15. **`e:\output\1\api\cloud_collaborator.py`** — 端云协作 (48KB,含已知 B1/B2 参数错误)
16. **`e:\output\1\api\traffic_event_engine.py`** — 交通事件引擎 (21KB,8状态机)

---

## 9. 总结

本次整理实现了以下目标:

- ✅ 建立清晰的 Git 基线 (从 1 个提交 → 2 个提交,461 文件纳入版本控制)
- ✅ 通过 .gitignore 排除 36,000+ 非必要文件 (训练数据/环境/缓存/大文件)
- ✅ 确认删除 7 个废弃环境脚本
- ✅ 保留所有源码、文档、测试、配置 (不删除无法确认用途的文件)
- ✅ 验证核心文件语法和路径
- ✅ 生成完整审计报告供后续接管

**未进行大规模重构,未修改功能逻辑,未删除无法确认用途的文件。**

项目现在处于一个结构清晰、可持续开发、方便后续交给 DeepSeek Harness/Agent Team 接管的稳定基线状态。
