# CARLA 仿真环境集成指南

本指南说明如何在本交通检测项目中接入 CARLA 仿真环境，用于在无实体摄像头时进行端到端的违规检测与车牌识别演示。

## 1. 概述

项目通过 `api/carla_source.py` 中的 `CarlaSource` 类将 CARLA 仿真器抽象为与摄像头/视频文件同级的数据源。其 `get_frame()` 返回 BGR `np.ndarray`，可直接喂入既有 OpenCV/YOLOv8 检测管线，无需修改下游代码。

```
CARLA Server  ──carla.Client──▶  CarlaSource  ──get_frame()──▶  检测/识别管线
                                  (BGR np.ndarray)
```

## 2. 环境准备

### 2.1 硬件要求

| 资源 | 最低 | 推荐 |
|------|------|------|
| GPU 显存 | 4 GB | 8 GB+ |
| 内存 | 8 GB | 16 GB |
| 磁盘 | 20 GB（CARLA 安装包） | SSD |
| CPU | 4 核 | 8 核 |

### 2.2 安装 CARLA 0.9.16

1. 从 [CARLA Release](https://github.com/carla-simulator/carla/releases/tag/0.9.16) 下载 `CARLA_0.9.16.tar.gz` 或 Windows 包。
2. 解压至 `e:\output\1\carla\CARLA_0.9.16\`（仓库已内置该目录结构，含 `CarlaUE4.exe`）。
3. 安装 Python 依赖：

```bash
pip install carla==0.9.16
pip install numpy opencv-python
```

> `carla` 包未安装不会导致程序崩溃。`CarlaSource` 通过 `try/except ImportError` 优雅降级，`connect()` 返回 `False`。

## 3. 启动 CARLA 服务器

### 3.1 基本启动（低画质，节省显存）

```powershell
cd e:\output\1\carla\CARLA_0.9.16
.\CarlaUE4.exe -quality-level=Low -benchmark -fps=20
```

参数说明：
- `-quality-level=Low`：降低渲染画质，显存占用从 ~6GB 降至 ~2GB。
- `-benchmark -fps=20`：固定 20 FPS，使服务器以固定步长运行。
- `-carla-rpc-port=2000`：可选，指定 RPC 端口（默认 2000）。
- `-RenderOffScreen`：无窗口运行，适合服务器/CI 场景。

### 3.2 验证服务器

启动后等待 10–20 秒，看到 `CarlaUE4` 窗口出现即表示就绪。可通过 Python 验证：

```python
from api.carla_source import CarlaSource
src = CarlaSource()
print(src.connect('localhost', 2000))  # True 表示连通
```

## 4. 同步模式 vs 异步模式

| 模式 | 适用场景 | 说明 |
|------|----------|------|
| **同步模式** | 检测/记录/复现 | 服务器按 `fixed_delta_seconds` 推进，客户端调用 `tick()` 后服务器才前进一帧。帧序确定、可复现，**本项目推荐**。 |
| **异步模式** | 实时交互/人驾 | 服务器自主按真实时间推进，客户端被动接收。帧率不稳定，时序不可控。 |

### 选择建议

- **演示/违规取证/数据集录制** → 同步模式（`set_synchronous_mode(0.05)`，即 20 FPS）。检测循环每帧调用 `tick()`，保证"取帧 ↔ 仿真状态"严格对齐。
- **多人协同或外部人为接管** → 异步模式。
- 同步模式下务必同步 TrafficManager：`CarlaSource` 已自动处理。
- **重要**：程序退出前必须切回异步模式或调用 `disconnect()`，否则服务器会卡在 `tick()` 等待，下次连接异常。`CarlaSource.disconnect()` 已实现该清理。

## 5. 坐标映射说明

CARLA 使用**左手坐标系**（Unreal Engine 惯例）：

```
        Z (上)
        ▲
        │
        │
        └──────► X (前)
       /
      ▼
     Y (右)
```

| 轴 | 含义 | 单位 |
|----|------|------|
| X  | 前进方向（车头朝向） | 米 |
| Y  | 右侧方向 | 米 |
| Z  | 高度（向上为正） | 米 |

- `location = {x, y, z}`：世界坐标，单位米。
- `rotation = {pitch, yaw, roll}`：单位度。`yaw=0` 朝向 +X。
- `velocity`：合成速度标量，单位 m/s（乘 3.6 得 km/h）。

### 与图像像素的对应

摄像头回调返回的 `raw_data` 为 **BGRA** 4 通道（CARLA 内部存储格式）。`CarlaSource._on_camera_image()` 取前 3 通道得到 **BGR**，与 OpenCV 默认格式一致，可直接 `cv2.imshow` / `cv2.imwrite`。

如需将图像检测框反投影到世界坐标，需借助 `carla.Client.get_world().get_map().get_waypoint()` 与相机外参，不在本数据源职责范围内。

## 6. 常见问题

### Q1：端口 2000 被占用 / 连接超时

```
RuntimeError: time-out of 10s while waiting for the simulator, make sure the simulator is ready
```

- 确认 `CarlaUE4.exe` 已启动且窗口出现。
- 检查端口：`netstat -ano | findstr :2000`，若被占用，用 `-carla-rpc-port=2001` 启动并在脚本中 `--port 2001`。
- 防火墙放行 2000/2001 与 8000（TrafficManager）端口。
- `CarlaSource.connect()` 已捕获该异常并返回 `False`，主程序继续降级运行。

### Q2：Actor 数量上限

CARLA 单服务器默认 actor 上限约 10000，但受性能制约建议：

| 显存 | 建议车辆数 | 行人数 |
|------|-----------|--------|
| 4 GB | ≤ 30 | ≤ 15 |
| 8 GB | ≤ 80 | ≤ 40 |
| 16 GB | ≤ 150 | ≤ 80 |

超出会触发 `spawn_actor` 失败，`CarlaSource` 用 `try_spawn_actor` 自动跳过冲突点。

### Q3：GPU 显存不足 / 帧率骤降

- 启动加 `-quality-level=Low`。
- 减少摄像头分辨率（`attach_camera(width=640, ...)`）。
- 关闭其他 GPU 密集进程。
- 行人 AI 控制器开销大，优先减少行人数量。
- 同步模式下调大 `fixed_delta_seconds`（如 0.1 = 10 FPS）。

### Q4：`import carla` 报 ModuleNotFoundError

未安装 `carla` Python 包。本项目不强制安装，`CarlaSource` 会降级。如需完整功能：

```bash
pip install carla==0.9.16
```

注意版本必须与 `CarlaUE4.exe` 版本一致，否则 RPC 协议不匹配会报 `version mismatch`。

### Q5：同步模式下脚本卡死

通常是客户端未调用 `tick()` 或退出未清理。确保：
- 检测循环每帧调用 `src.tick()`。
- 使用 `with CarlaSource() as src:` 或 `finally: src.disconnect()` 保证清理。
- 若服务器已卡死，重启 `CarlaUE4.exe`。

### Q6：生成的车辆不动

- 确认调用了 `actor.set_autopilot(True)`（`spawn_vehicles` 已内置）。
- TrafficManager 端口冲突：用 `client.get_trafficmanager(port)` 指定新端口。
- 同步模式下 TrafficManager 需同步：`tm.set_synchronous_mode(True)`（`CarlaSource` 已自动处理）。

## 7. 运行演示

```powershell
cd e:\output\1
# 确保 CarlaUE4.exe 已启动
py -3 scripts/run_carla_demo.py --scene town01
py -3 scripts/run_carla_demo.py --scene town03 --host 127.0.0.1 --port 2000
py -3 scripts/run_carla_demo.py --scene violation --frames 300
```

输出文件：`e:\output\1\output\carla_demo_result.json`，包含：
- `violations`：红绿灯违规日志（车辆 id、速度、位置、最近红绿灯）
- `plates`：车牌识别结果（车牌号、置信度、边界框）
- `frames_processed`：实际处理帧数

## 8. 模块速查

| 文件 | 职责 |
|------|------|
| `api/carla_source.py` | `CarlaSource` 数据源抽象，优雅降级 |
| `scripts/run_carla_demo.py` | 一键演示：连接→生成交通→检测→输出 |
| `api/license_plate_recognizer.py` | 车牌识别（演示脚本可选调用） |
| `zhitong/violation_detector.py` | 违规检测（演示脚本可选调用） |
