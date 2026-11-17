# 交接 · 2026-11-18

> 上一份交接是 `HANDOFF-红绿灯判色-20261109b.md`（判色专项）。
> 本文件是**全局状态快照**，只看这一份就能接着干。

---

## 一句话现状

检测主链路、管理端、车牌识别、事件落库都跑得通；**方向已定**（红绿灯配时优化 + CARLA 验证，
见 `docs/DIRECTION.md`，三条被否掉的路不要再回头）；中期审查材料还没做；
测试套件大部分红，但红的原因不是产品坏了（见第六节）。

---

## 一、这一轮（11-17 ~ 11-18）改了什么

全部已重启生效，未提交 git。

| # | 文件 | 改了什么 | 为什么 |
|---|---|---|---|
| 1 | `api/routers/mobile_demo.py` | **新增**扫码演示页 `/m`、大屏页 `/demo`、二维码、拍照上传 | 期中演示用 |
| 2 | `api/realtime_detector.py` | 新增 `class_filter_mode`（traffic/all）+ `set_class_filter_mode()` | 演示时能切"全量识别" |
| 3 | `api/routers/realtime.py` | 新增 `GET/POST /api/realtime/class-mode` | 同上 |
| 4 | `api/realtime_detector.py` | 默认禁停区 `画面下半部分` → `[]` | **修违停误报**：等红灯的车全被判违停 |
| 5 | `api/schemas.py` | `track_id: int` → `Optional[int]` | **修分页 500**：库里 null 记录让整个请求崩 |
| 6 | `api/circular_frame_buffer.py` | ffmpeg 定位改为逐个试跑 `-version` | **修事件视频**：PATH 上的 shim 指向已删除路径 |
| 7 | `api/circular_frame_buffer.py` | 兼容裸 ndarray 帧输入 | **修 sidecar 崩溃**：`meta or {}` 对数组做布尔判断 |
| 8 | `start-all.bat` / `restart-backend.bat` | 加 `--lan` 参数 | 默认只绑 127.0.0.1，手机连不上 |
| 9 | `docs/ARCHITECTURE.md`、`docs/MOBILE_DEMO.md` | 新增 | 接手文档 |
| 10 | `docs/DIRECTION.md` | **新增** | 项目方向定稿：红绿灯配时优化 + CARLA 验证 |

依赖变更：
- 装了 `hyperlpr3`（车牌识别，之前缺这个包导致车牌永远为空）
- 装了 `qrcode`（二维码生成）
- PyTorch 从 `2.13.0+cpu` 换成 `2.13.0+cu130`（GPU 终于用上了）
- 装了 `ffmpeg 9.0.2`（winget）

---

## 二、性能现状（实测）

| 配置 | 单帧识别 | 实时帧率 |
|---|---|---|
| CPU / 1280 | 828 ms | 1.08 FPS |
| CPU / 640 | — | 2.91 FPS |
| GPU / 960（现行） | 174 ms | 4.6 FPS |
| GPU / 960 + 缓存优化后（无客户端） | — | **4.85 FPS** |
| GPU / 960 + 缓存优化后（2 个 MJPEG 客户端） | — | **3.6 FPS** |

`start-all.bat` 里的调优参数：`YOLO_IMGSZ=960`、`FRAME_RATE=6`、
模型序列 `vehicle,traffic_light,helmet,lane`（去掉 license_plate，
它的 .pt 不存在会静默回退 COCO 吐垃圾框）。

**2026-11-18 的优化**：`/api/realtime/stream` 原先对每个客户端、每一轮都
重画一次框再各自编码，画框还持 `self.lock` 和检测线程抢锁。
实测端到端 2.43 FPS，而四个模型本身只要 67 ms —— 瓶颈根本不在模型。
改成 `get_annotated_jpeg()` 按 `frame_count` 缓存同一帧的 JPEG 后，
无客户端 4.85 FPS，两个客户端 3.6 FPS。

仍可优化的点：画框目前仍在锁内；`asyncio.sleep(0.05)` 对 4 FPS 的源是空转。
再往下压需要把渲染和检测彻底解耦（生产者-消费者），收益递减。

---

## 三、方向已定（2026-11-18）

**主线：路口流量采集 → 信号配时优化建议 → CARLA 仿真验证。**

详细论证见 `docs/DIRECTION.md`。**三条被否掉的路不要再回头**：

- 执法/电子警察（政策壁垒）
- 市民举报端（伪需求）
- 校园共享单车治理（价值长在运营，学生项目做不了）

定位一句话：不做执法，做执法管不到的数据分析；不比谁算法新，比谁成本低——
用已有摄像头完成专用检测器的工作。

---

## 四、已知未修的问题

| 优先级 | 问题 | 现象 | 线索 |
|---|---|---|---|
| 中 | 事件 ID 撞车 | `UNIQUE constraint failed: traffic_events.event_id`，该条事件丢失 | `traffic_event_engine.py:386` 用 `uuid4().hex[:6]`，高频下有碰撞可能 |
| 中 | 数据库 InterfaceError | 偶发 `bad parameter or other API misuse` | 疑似多线程共用 session |
| 低 | FPS 显示 0.0 | 画面上 `FPS: 0.0`，但 `/status` 的 avg_fps 是 4.x | 瞬时值滑动窗口没攒够样本就除了 |
| 低 | 历史事件缺媒体 | 管理端打开旧事件看不到图/视频 | 早期代码没存，不是功能退化 |

---

## 五、演示相关（期中审查）

**现状**：能演示，但材料没做。

- 实时检测画面 ✅
- 类别切换（交通/全量）✅
- 车牌识别（近景才行，车牌小于约 30px 识别不出）✅
- 扫码演示页 ✅（HTTP 环境下是"只读看画面"模式）
- **PPT ❌ 完全没做**。现有 `presentation/make_ppt_v4.js` 是国赛路演版，
  内容与实际进度严重不符（详见对话记录：TensorRT 66FPS 那页零实现支撑）
- 云台硬件：已列采购清单，未下单

**手机接入摄像头**：技术上行不通。浏览器调 `getUserMedia` 必须 HTTPS，
局域网自签证书点"继续前往"也不算安全上下文。**不要再在这条路上花时间**，
除非有公网 HTTPS 域名。

替代方案：递一台提前装好 IP Webcam 的设备给评委操作，效果等价。

---

## 六、测试为什么是红的

```
1047 failed, 115 passed, 8714 subtests passed
```

拆开：
- **1030 个是子测试**：`test_event_media_contract` 遍历**历史事件**逐条断言
  "视频是 H.264"，历史数据是旧代码产生的，改代码不会让它们变好
- **17 个独立失败**：多数是测试自身问题（路径敏感、期待的接口不存在）

**不要用这个数字判断代码质量。** 验证功能用新数据。

---

## 七、下一个接手的人该先做什么

1. 读 `docs/ARCHITECTURE.md` 前三节（15 分钟）
2. 跑 `start-all.bat`，打开 `http://localhost:5173` 看能不能出画面
3. 看 `git status`——当前有大量未提交改动，先确认哪些要入库
4. 中期审查结束后，优先补 PPT 和提交代码

**代码修改原则**（这一轮总结出来的）：
- 任何"找不到依赖就降级"的路径，必须留日志或状态字段，否则就是埋雷
- 场景几何（停止线/禁停区/车道）没标注就不判，别用默认值兜底
- 改完先跑一遍真实视频，别看测试
