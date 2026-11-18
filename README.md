# 智瞳灵声 CityGuardian

**基于视觉识别与云端推理的智慧交管系统**

端云协同的交通违规检测与辅助治理平台。本地完成实时检测与判定，跨帧累积证据；
可疑样本异步送云端大模型二次裁决，不阻塞主链路。

---

## 能做什么

| 能力 | 状态 | 说明 |
|---|---|---|
| 实时目标检测 | ✅ | YOLO 多模型串行，车辆 / 行人 / 信号灯 / 头盔 / 车道线 |
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

## 仓库结构

```
1/                      项目本体
├── api/                后端（FastAPI）
├── web-admin/          管理端（Vue 3）
├── wechat-miniprogram/ 微信小程序
├── miniprogram/        管理端配套小程序
├── zhitong/            旧版单机程序（历史遗留，新代码不加这里）
├── carla/              CARLA 仿真接入
├── digital_twin/       2D 俯视孪生
├── tests/              测试
├── docs/               技术文档
└── presentation/       答辩材料
```

> 项目从本地多工程工作区演进而来，`1/` 是当时的工程编号，代码与文档都在这一层之下。

---

## 快速开始

```bat
cd 1
start-all.bat
```

| 服务 | 地址 |
|---|---|
| 管理端 | http://localhost:5173 |
| API 文档 | http://localhost:8001/docs |
| 健康检查 | http://localhost:8001/health |

需要手机等局域网设备访问：

```bat
start-all.bat --lan
```

默认绑定 `127.0.0.1` 是刻意的，加 `--lan` 才会监听局域网。

---

## 配置

复制 `1/api/.env.example` 为 `1/api/.env` 并填入密钥。`.env` 与 `config_runtime.json`
均已被 `.gitignore` 排除，不会进入仓库。

| 变量 | 用途 |
|---|---|
| `DASHSCOPE_API_KEY` | 阿里云百炼，云端视觉二次裁决 |
| `DEEPSEEK_API_KEY` | 代码分析与审核 |
| `CLAUDE_API_KEY` | 备用视觉分析（可选） |
| `ZHITONG_JWT_SECRET` | JWT 签名密钥，生产环境必填 |

---

## 环境要求

- Python 3.12（CARLA 只提供 cp312 轮子）
- Node.js（管理端构建）
- NVIDIA GPU + CUDA 版 PyTorch（CPU 也能跑，慢约 4 倍）
- ffmpeg（事件视频转 H.264，缺失时回退 mp4v）

---

## 文档

接手先读这三份（位于 `1/docs/`）：

- [DIRECTION.md](1/docs/DIRECTION.md) —— **最优先**：项目方向、被否掉的三条路、差异化在哪
- [ARCHITECTURE.md](1/docs/ARCHITECTURE.md) —— 架构地图、数据流、配置项、已知的坑
- [HANDOFF.md](1/docs/HANDOFF.md) —— 当前状态、待办、上一版做了什么

其余细节见 [1/README.md](1/README.md)。

---

## 团队

宁夏理工学院 · 电气信息工程学院

陈俊龙、母书祯、苗博文、余林峰、王泽轩

指导教师：赵智雯、汪永奇
