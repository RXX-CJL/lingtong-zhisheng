# 智瞳灵声 · 架构地图

> 2026-11-18 建立。**读这一份就能上手**，不用翻历史 handoff。
> 如果你只需要知道「代码在哪、数据怎么流、怎么跑起来」，看前三节就够了。

---

## 1. 系统是什么

端云协同的交通违规检测系统。核心链路：

```
视频源 ──► 检测器 ──► 行为判定 ──► 事件 ──► 数据库 ──► 管理端
           (YOLO)     (规则引擎)   (状态机)   (SQLite)   (Vue)
                │
                └──► 云端二次裁决（豆包大模型，可选）
```

三个可独立运行的部分：

| 组件 | 位置 | 端口 | 说明 |
|---|---|---|---|
| 后端 API | `api/app.py` | 8001 | FastAPI，检测+判定+落库+推流 |
| 管理端 | `web-admin/` | 5173 | Vue 3 + Element Plus，20 个页面 |
| 微信小程序 | `wechat-miniprogram/` | — | 面向公众的举报入口 |

**不存在**「先启动前端才能用」的要求——后端自带 MJPEG 推流和演示页。

---

## 2. 怎么跑起来

```bat
E:\output\1\start-all.bat
```

它做三件事：起后端（8001）、起前端（5173）、开浏览器。

需要局域网访问（手机/其它设备）时加参数：

```bat
start-all.bat --lan
```

**默认只绑 `127.0.0.1`，手机连不上是设计如此，不是故障。**

单独起后端：

```bash
cd api
..\.venv\Scripts\python.exe -m uvicorn app:app --host 0.0.0.0 --port 8001
```

---

## 3. 目录地图

```
1/
├── api/                      后端（Python 3.12 + FastAPI）
│   ├── app.py                入口：注册 14 个 router、CORS、静态目录
│   ├── realtime_detector.py  ★ 220KB，检测主循环，几乎所有链路都在这
│   ├── image_recognizer.py   模型加载与调用（YOLO 多模型 + 类别白名单）
│   ├── behavior_engine.py    违规判定规则（闯红灯/逆行/违停/超速…）
│   ├── violation_rules.py    规则常量与类型定义
│   ├── traffic_event_engine.py  事件状态机（触发→确认→归档）
│   ├── cloud_collaborator.py 云端二次裁决（异步，不阻塞主循环）
│   ├── speed_calibration.py  像素→米的速度标定（透视校正）
│   ├── carla_source.py       CARLA 仿真视频源
│   ├── circular_frame_buffer.py  循环帧缓存 → 事件视频落盘（H.264）
│   ├── annotation_renderer.py    画框/画文字（中文标签）
│   ├── routers/              对外 HTTP 接口，按域拆分
│   │   ├── realtime.py       ★ 77KB，实时检测的绝大部分接口
│   │   ├── violations.py     违规记录 CRUD
│   │   ├── mobile_demo.py    扫码演示页（2026-11-17 新增）
│   │   ├── twin.py           2D 俯视孪生
│   │   └── ...               设备/申诉/场景标注/云协作/小程序
│   └── models.py             SQLAlchemy 表定义
│
├── web-admin/                管理端（Vue 3 + Vite）
│   └── src/views/            20 个页面，实时监控 / 事件中心 / 违规列表等
│
├── zhitong/                  旧版单机程序 + 训练脚本 + K230 应用
├── tests/                    18 个测试文件（见下方"测试现状"）
├── docs/                     技术文档（本文件在这里）
├── carla/                    CARLA 仿真环境
├── presentation/             答辩 PPT 及其生成脚本
└── start-all.bat             一键启动
```

**`zhitong/` 是历史遗留**，新代码不要往那里加。主线全在 `api/`。

---

## 4. 关键链路（改代码前必看）

### 4.1 一帧是怎么走完的

```
realtime_detector.start_detection()  ← 起一个线程循环读帧
  └─ process_frame()
       ├─ _yolo_detect()           多模型串行推理（vehicle/traffic_light/helmet/lane）
       ├─ _filter_traffic_classes()  按白名单裁掉非交通类（可切 all 模式）
       ├─ tracker.update()          分配 track_id
       ├─ behavior_engine.analyze_all()  每条规则跑一遍
       ├─ _try_recognize_plates()   车牌 OCR（后台线程，限流 2 秒）
       ├─ traffic_event_engine     触发事件、写库
       └─ _draw_detection_boxes()  画框 → current_frame
```

`get_annotated_frame()` 用 `current_frame` + `last_detection_result` 画框，
`/api/realtime/stream` 把它包成 MJPEG 推出去。**手机页、管理端、演示大屏都吃这一路。**

### 4.2 事件视频怎么来

```
循环帧缓存（circular_frame_buffer）
  → save_event_video()
  → cv2.VideoWriter 写 mp4v 临时文件
  → ffmpeg 转 H.264（浏览器才播得了）
  → 失败则保留 mp4v 并告警
```

### 4.3 云端裁决

异步：主循环只把可疑帧入队，独立 worker 调豆包大模型，结果回写事件。
**不要在 `process_frame` 里同步调云端**——历史上因为这个把帧率压到 0.7 fps。

---

## 5. 配置的真相

大部分行为由**环境变量**控制，不是配置文件：

| 变量 | 默认 | 作用 |
|---|---|---|
| `YOLO_IMGSZ` | 1280 | 推理分辨率，降到 960 提速明显 |
| `FRAME_RATE` | 3 | 检测帧率上限 |
| `YOLO_MODEL_SEQUENCE` | 全部 | 只跑需要的模型，去掉 license_plate 能省 30ms |
| `BOX_PREDICTION` | 0 | 检测间隔里外推框位置，纯显示用 |
| `PLATE_INTERVAL_SEC` | 2.0 | 车牌识别限流 |
| `ZHITONG_DB_PATH` | `api/zhitong_violations.db` | 数据库位置（测试时务必覆盖） |

`start-all.bat` 里有一组实测调优值，改之前先看那里的注释。

---

## 6. 已知的坑（读到这里能省你一天）

1. **默认值会咬人**。禁停区曾经默认是"画面下半部分"，导致等红灯的车全被判违停。
   凡是场景几何（停止线、禁停区、车道方向），**没有人工标注就不该判**。

2. **静默降级是这个项目的通病**。依赖找不到 → 返回空 → 功能失效但没日志。
   已修复两处（车牌 hyperlpr3、ffmpeg shim）。遇到"功能不工作但不报错"，
   先查是不是这个模式。**新增降级路径必须留可观测信号。**

3. **`which` 找到不等于能跑**。Windows 上 `.CMD` shim 可能指向已删除的路径。

4. **测试对工作目录敏感**。从项目根跑和从 `api/` 跑结果不同。

---

## 7. 测试现状

```bash
cd api && ..\.venv\Scripts\python.exe -m pytest ../tests/ -q
```

- 17 个独立失败，多数是测试自身过时（期待的接口不存在、路径问题）
- 另有 1030 个子测试失败：`test_event_media_contract` 遍历**历史事件**逐条断言
  "视频是 H.264"，而历史事件的视频是旧代码产生的。**这个数字不会随代码改动变化。**
- 要验证转码是否正常，用新生成的事件，别跑这个测试。

---

## 8. 下一步该看哪

- 交接状态与待办 → `docs/HANDOFF.md`
- 行为规则细节 → `docs/BEHAVIOR_RULES.md`
- 手机演示操作 → `docs/MOBILE_DEMO.md`
- 事件解释器字段 → `docs/EVENT_EXPLAINER_SCHEMA.md`
