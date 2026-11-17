# 智瞳灵声 CityGuardian

**基于视觉识别与云端推理的智慧交管系统**

端云协同的交通违规检测与辅助治理系统。本地完成实时检测与判定，跨帧累积证据；
可疑样本异步送云端大模型二次裁决，不阻塞主链路。

---

## 能做什么

| 能力 | 状态 | 说明 |
|---|---|---|
| 实时目标检测 | ✅ | YOLO 多模型串行，车辆/行人/信号灯/头盔/车道线 |
| 多目标跟踪 | ✅ | 分配 track_id，轨迹只读不写回判定 |
| 违规判定 | ✅ | 闯红灯、逆行、违停、超速、压线、未戴头盔、抢黄灯 |
| 车牌识别 | ✅ | hyperlpr3，需车牌在画面中足够大（约 ≥30px） |
| 云端二次裁决 | ✅ | 豆包大模型，异步 worker |
| 事件落库与回放 | ✅ | 事件视频转 H.264，浏览器可直接播 |
| 管理端 | ✅ | Vue 3，20 个页面 |
| 微信小程序 | ⚠️ | 有代码，未做端到端验收 |
| CARLA 仿真接入 | ✅ | 可作为视频源，也用于算法验证 |
| 2D 俯视孪生 | ⚠️ | 有实现，未完整验收 |

---

## 快速开始

```bat
start-all.bat
```

- 管理端 http://localhost:5173
- API 文档 http://localhost:8001/docs
- 健康检查 http://localhost:8001/health

需要手机等局域网设备访问时：

```bat
start-all.bat --lan
```

**默认绑定 127.0.0.1 是刻意的**，加 `--lan` 才会监听局域网。

---

## 架构

```
视频源（文件 / USB 摄像头 / RTSP / CARLA）
    │
    ▼
检测器（YOLO 多模型 + 跟踪）
    │
    ├──► 行为判定引擎（规则）
    ├──► 车牌识别（后台限流）
    ├──► 云端裁决（异步）
    │
    ▼
事件状态机 ──► SQLite ──► 管理端 / 小程序
    │
    └──► 循环帧缓存 ──► 事件视频（mp4v → H.264）
```

推流走 MJPEG（`/api/realtime/stream`），管理端、演示大屏、手机页共用这一路。

---

## 目录

```
api/            后端（FastAPI）
web-admin/      管理端（Vue 3）
wechat-miniprogram/  小程序
zhitong/        旧版单机程序（历史遗留，新代码不要往这里加）
tests/          测试
docs/           技术文档
presentation/   答辩材料
```

---

## 文档

**接手先读这两份：**

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) —— 架构地图、数据流、配置、已知的坑
- [docs/HANDOFF.md](docs/HANDOFF.md) —— 当前状态、待办、上一个版本做了什么

细节文档：

- [docs/BEHAVIOR_RULES.md](docs/BEHAVIOR_RULES.md) —— 违规判定规则与阈值
- [docs/MOBILE_DEMO.md](docs/MOBILE_DEMO.md) —— 手机扫码演示的操作与排查
- [docs/EVENT_EXPLAINER_SCHEMA.md](docs/EVENT_EXPLAINER_SCHEMA.md) —— 事件解释器字段

---

## 环境要求

- Python 3.12（CARLA 只提供 cp312 轮子）
- Node.js（管理端构建）
- NVIDIA GPU + CUDA 版 PyTorch（CPU 也能跑，慢约 4 倍）
- ffmpeg（事件视频转 H.264，缺失时回退 mp4v）

---

## 团队

宁夏理工学院 · 电气信息工程学院
陈俊龙、母书祯、苗博文、余林峰、王泽轩
指导教师：赵智雯、汪永奇
