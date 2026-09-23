# 智瞳智慧交管系统 - 项目文件索引

> 最后更新: 2026-07-20 (TASK-011)

---

## 后端API模块 (api/)

| 文件路径 | 用途 | 核心函数/类 | 状态 |
|---------|------|------------|------|
| api/app.py | FastAPI主入口，路由注册、生命周期管理 | lifespan, app | 已有(TASK-008更新) |
| api/image_recognizer.py | 图像识别核心模块，YOLO+豆包+DeepSeek | detect_with_yolo, analyze_with_doubao, analyze_with_deepseek_judge, multi_model_detect, detect_license_plate, analyze_with_collaboration | 已有(TASK-008更新) |
| api/cloud_collaborator.py | 端云协作管理器，本地AI主动咨询云端AI | CloudCollaborator | TASK-008新增(TASK-010更新) |
| api/models.py | SQLAlchemy数据模型定义 | ViolationEvidence, SystemConfig, APILog, User, CollaborationSession, SystemStatistics | 已有(TASK-008更新) |
| api/database.py | 数据库连接和初始化 | get_db, init_db, migrate_missing_columns | 已有 |
| api/migrate_db.py | 数据库迁移脚本（端云协作特性） | run_migration, rollback, show_status | TASK-008新增 |
| api/violation_rules.py | 违规规则引擎，6种违规类型判断（含逆行） | ViolationRuleEngine | 已有(TASK-010更新) |
| api/config_manager.py | 系统配置管理（API Key管理） | load_config, save_config | 已有 |
| api/config.py | 统一配置管理模块 | Config类（端口、路径、超时、帧率等） | TASK-011新增 |
| api/realtime_detector.py | 实时违规检测服务，摄像头采集+YOLO检测+帧缓存 | RealtimeViolationDetector | TASK-010新增(TASK-011更新) |
| api/vehicle_tracker.py | 车辆追踪器，质心追踪+方向计算+逆行检测 | VehicleTracker | TASK-010新增 |

### 路由模块 (api/routers/)

| 文件路径 | 用途 | 核心接口 | 状态 |
|---------|------|---------|------|
| api/routers/violations.py | 违规证据管理API | CRUD违规记录 | 已有 |
| api/routers/wechat.py | 微信小程序API | 违规提交、列表、详情 | 已有 |
| api/routers/system.py | 系统管理API | 健康检查、配置管理 | 已有 |
| api/routers/statistics.py | 统计分析API | 数据统计、趋势分析 | 已有 |
| api/routers/devices.py | 设备管理API | 设备CRUD、状态监控 | 已有 |
| api/routers/appeals.py | 申诉管理API | 申诉提交、审核 | 已有 |
| api/routers/auth.py | 认证授权API | 登录、注册、Token管理 | 已有 |
| api/routers/cloud_collab.py | 端云协作API | /api/cloud/consult, /collab-list, /statistics, /disagreements | TASK-008新增 |
| api/routers/realtime.py | 实时监控API | /api/realtime/stream, /api/realtime/status, /api/realtime/start, /api/realtime/stop, /api/realtime/consult | TASK-010新增 |

---

## 前端管理后台 (web-admin/)

| 文件路径 | 用途 | 核心组件/函数 | 状态 |
|---------|------|-------------|------|
| web-admin/src/App.vue | 根组件，顶部导航菜单 | 导航菜单 | 已有(TASK-008更新) |
| web-admin/src/router/index.js | Vue路由配置 | 路由定义 | 已有(TASK-008更新) |
| web-admin/src/views/Dashboard.vue | 仪表盘首页 | 统计概览 | 已有 |
| web-admin/src/views/ViolationList.vue | 违规记录列表 | 分页表格、筛选 | 已有 |
| web-admin/src/views/ViolationDetail.vue | 违规记录详情 | 详情展示、图片预览 | 已有 |
| web-admin/src/views/AIDetect.vue | 智能识别页面 | 图片上传、实时检测 | 已有 |
| web-admin/src/views/AITrace.vue | 精度验证页面 | AI分析结果总览 | 已有 |
| web-admin/src/views/CollabStats.vue | 端云协作统计页面 | 统计卡片、趋势图 | TASK-008新增 |
| web-admin/src/views/DisagreementList.vue | 分歧案例审核页面 | 表格、详情对话框、裁决 | TASK-008新增 |
| web-admin/src/views/Statistics.vue | 统计分析页面 | 数据图表 | 已有 |
| web-admin/src/views/Settings.vue | 系统设置页面 | API Key配置 | 已有 |
| web-admin/src/views/QuotaMonitor.vue | API额度监控 | 调用次数统计 | 已有 |
| web-admin/src/views/RealTimeMonitor.vue | 实时监控页面 | MJPEG视频流、WebSocket违规事件、检测状态面板 | TASK-010新增 |

---

## 微信小程序 (wechat-miniprogram/)

| 文件路径 | 用途 | 核心页面/函数 | 状态 |
|---------|------|-------------|------|
| wechat-miniprogram/app.json | 小程序配置 | 页面注册、tabBar | 已有(TASK-007更新) |
| wechat-miniprogram/src/app.js | 小程序入口 | login, request | 已有 |
| wechat-miniprogram/utils/api.js | API请求封装 | request, submitViolation | 已有 |
| wechat-miniprogram/src/pages/index/ | 首页 | 统计概览、最近违规 | 已有 |
| wechat-miniprogram/src/pages/violation/detail.js | 违规详情页 | loadDetail, AI协作展示 | 已有(TASK-008更新) |
| wechat-miniprogram/src/pages/violation/detail.wxml | 违规详情页模板 | AI协作时间线展示 | 已有(TASK-008更新) |
| wechat-miniprogram/src/pages/violation/list.js | 违规列表页 | 分页列表 | 已有 |
| wechat-miniprogram/src/pages/appeal/submit.js | 申诉提交页 | 表单提交 | 已有 |
| wechat-miniprogram/src/pages/my/index.js | 个人中心 | 用户信息、申诉统计 | 已有 |
| wechat-miniprogram/src/pages/statistics/ | 统计页面 | 数据图表 | 已有 |

---

## 数字孪生 (digital_twin/)

| 文件路径 | 用途 | 核心类/函数 | 状态 |
|---------|------|-----------|------|
| digital_twin/static/js/main.js | 3D场景核心 | TrafficScene, initScene | 已有(TASK-008更新) |
| digital_twin/index.html | 数字孪生入口页面 | HTML结构 | 已有 |

### TASK-008新增数字孪生方法
- flashCamera() - 摄像头闪烁红色
- updateCameraStatusIndicator() - 摄像头状态指示灯
- highlightViolationVehicle() - 违规车辆3D标记
- showViolationNotification() - 违规通知弹窗
- addViolationToTimeline() - 违规事件时间轴
- setupMultiCameraStatus() - 多摄像头状态初始化
- triggerViolationEvent() - 完整违规事件动画序列

---

## K230端 (K230/)

| 文件路径 | 用途 | 核心类/函数 | 状态 |
|---------|------|-----------|------|
| K230/zhitong_detect.py | K230端违规检测程序 | TrafficViolationDetector | TASK-006新增 |

---

## 模型文件 (zhitong/training/models/)

| 文件路径 | 用途 | 状态 |
|---------|------|------|
| zhitong/training/models/yolov8n.pt | YOLOv8 Nano通用检测 | 已有 |
| zhitong/training/models/yolov8s.pt | YOLOv8 Small通用检测 | 已有 |
| zhitong/training/models/traffic_light.pt | 红绿灯检测模型 | TASK-007下载 |
| zhitong/training/models/helmet.pt | 头盔检测模型 | TASK-007下载 |
| zhitong/training/models/lane.pt | 车道线检测模型 | TASK-007下载 |

---

## 系统工具文件

| 文件路径 | 用途 | 状态 |
|---------|------|------|
| lan-start.bat | 一键启动脚本（后端+前端+数字孪生） | TASK-008新增 |
| PROJECT_FILE_INDEX.md | 项目文件索引（本文件） | TASK-008新增 |
| zhitong/demo_script.py | 测试视频演示脚本，模拟实时检测流程 | TASK-011新增 |

---

## 数据库表结构

| 表名 | 用途 | 状态 |
|------|------|------|
| violation_evidences | 违规证据记录 | 已有(TASK-008扩展) |
| system_configs | 系统配置 | 已有 |
| api_logs | API调用日志 | 已有 |
| users | 用户管理 | 已有 |
| collaboration_sessions | 端云协作会话记录 | TASK-008新增 |
| system_statistics | 系统统计数据 | TASK-008新增 |

---

## API接口清单

### 端云协作接口 (TASK-008新增)

| 接口 | 方法 | 功能 |
|------|------|------|
| /api/cloud/consult | POST | 本地AI主动咨询云端 |
| /api/cloud/collab-list | GET | 获取协作记录列表 |
| /api/cloud/collab-detail/{id} | GET | 获取单次协作详情 |
| /api/cloud/statistics | GET | 获取协作统计数据 |
| /api/cloud/disagreements | GET | 获取分歧案例列表 |
| /api/cloud/resolve-disagreement | POST | 人工裁决分歧案例 |

### 现有接口

| 接口 | 方法 | 功能 |
|------|------|------|
| /api/violations/* | GET/POST | 违规证据管理 |
| /api/wechat/* | GET/POST | 微信小程序接口 |
| /api/statistics/* | GET | 统计分析 |
| /api/devices/* | GET/POST | 设备管理 |
| /api/appeals/* | GET/POST | 申诉管理 |
| /api/auth/* | POST | 认证授权 |

### 实时监控接口 (TASK-010新增)

| 接口 | 方法 | 功能 |
|------|------|------|
| /api/realtime/stream | GET | MJPEG视频流 |
| /api/realtime/status | GET | 获取实时检测状态 |
| /api/realtime/start | POST | 启动实时检测 |
| /api/realtime/stop | POST | 停止实时检测 |
| /api/realtime/consult | POST | 强制云端咨询 |
| /api/realtime/ws | WebSocket | 违规事件推送 |
