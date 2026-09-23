# ONVIF 摄像头开启与配置指南

> 本文档对应模块: `api/ptz_controller.py` (M08: 云台控制)
> 适用摄像头: 支持 ONVIF Profile S/G 的网络摄像头（海康、大华、宇视、TP-Link 等）

---

## 1. 什么是 ONVIF

ONVIF (Open Network Video Interface Forum) 是网络视频设备的开放接口标准。
通过 ONVIF 协议，可以用统一接口控制不同厂商的摄像头 PTZ（云台）、获取视频流、配置参数等，
无需依赖厂商私有 SDK。

智瞳灵声系统的 `PTZControllerBase` 抽象层正是基于 ONVIF 实现，配合 `SimulatedPTZController`
可在无硬件时优雅降级。

---

## 2. 环境准备

### 2.1 安装 onvif-zeep

```bash
pip install onvif-zeep
```

> 若未安装，系统会自动回退到 `SimulatedPTZController`，仅返回设定值，无法控制真实硬件。

### 2.2 网络连通性检查

1. 确保摄像头与运行本系统的主机在同一局域网
2. 使用 ping 确认 IP 可达:
   ```bash
   ping 192.168.1.64
   ```
3. 确认 ONVIF 端口开放（默认 80，部分厂商为 8000/8080）

---

## 3. 各厂商摄像头开启 ONVIF 步骤

### 3.1 海康威视 (Hikvision)

1. 浏览器访问摄像头 Web 后台: `http://<摄像头IP>` (默认端口 80)
2. 登录 (默认账号 admin，密码为激活时设置)
3. 进入 **配置 → 网络 → 高级 → 平台接入**
4. 勾选 **启用 ONVIF**
5. 点击 **添加** 创建 ONVIF 用户:
   - 用户名: 自定义（如 `onvif_user`）
   - 密码: 至少 8 位，含字母+数字（如 `Onvif@2024`）
6. 进入 **配置 → 网络 → 基本配置 → 端口**，确认 HTTP 端口 (默认 80)
7. 进入 **配置 → 视音频 → 音视频**，确认存在 `Profile_1` 媒体配置
8. 保存并重启摄像头

### 3.2 大华 (Dahua)

1. 浏览器访问: `http://<摄像头IP>` (默认端口 80)
2. 登录 (默认 admin / admin，首次登录强制改密)
3. 进入 **设置 → 网络 → ONVIF**
4. 勾选 **启用 ONVIF 服务**
5. 在 **ONVIF 用户管理** 中添加用户:
   - 用户名 / 密码 (建议强密码)
   - 权限: 选择 **管理员** (控制 PTZ 需要)
6. 确认端口配置 (默认 80)
7. 保存

### 3.3 宇视 (Uniview)

1. 浏览器访问: `http://<摄像头IP>`
2. 进入 **配置 → 网络 → 平台接入 → ONVIF**
3. 勾选 **启用**
4. 添加 ONVIF 用户并赋予权限
5. 保存

### 3.4 TP-Link

1. 浏览器访问: `http://<摄像头IP>`
2. 进入 **设置 → 网络 → 高级 → ONVIF**
3. 开启 ONVIF 服务
4. 设置 ONVIF 账号密码
5. 保存

---

## 4. 验证 ONVIF 是否生效

### 4.1 使用 ONVIF Device Manager (Windows GUI 工具)

1. 下载 [ONVIF Device Manager](https://sourceforge.net/projects/onvifdm/)
2. 启动后点击 **Refresh** 扫描局域网设备
3. 双击发现的设备，输入 ONVIF 用户名密码
4. 进入 **Live Video** 看到画面 = 视频流 OK
5. 进入 **PTZ Control** 测试云台控制 = PTZ OK

### 4.2 使用本系统自检

```bash
cd e:\output\1
python -m api.ptz_controller
```

输出示例（连接成功）:
```
ONVIF 摄像头 192.168.1.64 连接成功, profile_token=Profile_1
```

输出示例（降级模式）:
```
onvif-zeep 未安装，将使用 SimulatedPTZController
```

---

## 5. 在系统中配置 ONVIF

在 `config_runtime.json` 或调用 `PTZFactory` 时传入配置:

```json
{
  "ptz": {
    "mode": "onvif",
    "camera_ip": "192.168.1.64",
    "port": 80,
    "username": "onvif_user",
    "password": "Onvif@2024",
    "profile": "Profile_1"
  }
}
```

代码示例:

```python
from api.ptz_controller import PTZFactory

controller = PTZFactory({
    "mode": "onvif",
    "camera_ip": "192.168.1.64",
    "port": 80,
    "username": "onvif_user",
    "password": "Onvif@2024",
    "profile": "Profile_1",
})

if controller.is_connected():
    controller.goto_home()
    pos = controller.get_position()
    print(f"当前位置: {pos}")

    # 目标跟踪
    dx, dy, dz = controller.track_object([400, 200, 600, 400], 1280, 720)
    controller.move_relative(dx, dy, dz)
else:
    print("ONVIF 未连接，已降级为模拟模式")
```

---

## 6. 常见问题排查

| 问题 | 可能原因 | 解决方案 |
|------|---------|---------|
| 连接超时 | IP/端口错误或防火墙拦截 | 检查 IP、端口；关闭摄像头防火墙拦截 |
| 认证失败 | 用户名密码错误或 ONVIF 未启用 | 在摄像头后台重新设置 ONVIF 账号 |
| 无 PTZ 控制 | 摄像头无云台或 Profile 不含 PTZ 配置 | 确认摄像头支持 PTZ；选择含 PTZ 的 Profile |
| `onvif-zeep` 导入失败 | 缺少 zeep 依赖 | `pip install onvif-zeep` 或 `pip install zeep` |
| Profile token 为空 | Media 服务未返回 profile | 在摄像头后台确认音视频配置存在 |
| 移动方向相反 | 摄像头安装方向 | 调整 `track_object` 中 FOV 参数符号 |

---

## 7. 安全建议

1. **不要在代码中硬编码密码**。建议通过环境变量或配置文件读取:
   ```python
   import os
   password = os.environ.get("ONVIF_PASSWORD", "")
   ```
2. ONVIF 账号应仅授予必要权限（PTZ 控制 + 视频流），避免管理员权限
3. 生产环境建议将 ONVIF 流量限制在内网，不暴露到公网
4. 定期更换 ONVIF 密码

---

## 8. 降级策略说明

本系统采用 **优雅降级** 设计:

```
用户配置 mode=onvif
        │
        ▼
onvif-zeep 已安装? ──否──▶ 回退到 SimulatedPTZController (日志警告)
        │是
        ▼
连接摄像头成功? ──否──▶ 返回 ONVIFPTZController 但 is_connected=False
        │是                (后续调用自动重连)
        ▼
正常工作，所有控制方法返回 True
```

降级后系统仍可运行，调用方可通过 `is_connected()` 判断是否真实控制硬件，
并在 UI 上提示"模拟模式"。

---

## 9. 参考资源

- ONVIF 官方文档: https://www.onvif.org/profiles/
- onvif-zeep GitHub: https://github.com/FalkTannhaeuser/python-onvif-zeep
- 海康 ONVIF 配置视频教程: 海康官网支持中心
- ONVIF Device Manager: https://sourceforge.net/projects/onvifdm/

---

**文档版本**: 1.0
**对应模块**: `api/ptz_controller.py` (M08)
**最后更新**: 2026-07-29
