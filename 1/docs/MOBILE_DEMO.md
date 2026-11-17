# 手机扫码演示 · 现场操作手册

> 2026-11-17 建立。目标是期中审查现场，老师扫个码就能参与演示，全程零安装。
> 代码入口：`api/routers/mobile_demo.py`

---

## 一、开场前 10 分钟

### 1. 启动环境（一条命令）

```bat
E:\output\1\start-all.bat --lan
```

`--lan` 是 2026-11-17 新加的参数。脚本默认只绑 `127.0.0.1`，手机连不上；加 `--lan` 后监听 `0.0.0.0`。

脚本会自动起后端 8001、前端 5173、打开浏览器，并且带上一组实测调优参数：

- `YOLO_IMGSZ=960`（1280 太慢，960 能保住小目标）
- `FRAME_RATE=6`
- 模型序列去掉 `license_plate`（它的 .pt 不存在，会静默回退 COCO 吐垃圾框）

启动信息里会有一行：

```
Bind   : 0.0.0.0  [LAN mode - phones can connect]
```

看到它就说明手机能连了。

需要重启后端时同理：

```bat
E:\output\1\restart-backend.bat --lan
```

不带 `--lan` 重启会切回 `127.0.0.1`，手机立刻断开——演示中途改代码要特别注意这点。

手动启动等价写法：

```bash
cd E:\output\1\api
set YOLO_IMGSZ=960
set FRAME_RATE=6
..\.venv\Scripts\python.exe -m uvicorn app:app --host 0.0.0.0 --port 8001
```

### 2. 启动实时检测

浏览器打开 `http://localhost:5173`（管理端）→ 实时监控 → 源类型选「视频文件」→ 填绝对路径 → 开始。

或者直接调接口：

```bash
curl -X POST http://127.0.0.1:8001/api/realtime/start ^
  -H "Content-Type: application/json" ^
  -d "{\"video_path\":\"E:\\\\output\\\\1\\\\test_assets\\\\traffic_videos\\\\test1.mp4\"}"
```

### 3. 打开演示大屏

浏览器打开 **`http://localhost:8001/demo`**，建议 F11 全屏。

页面上有：
- 左侧：二维码 + 访问地址
- 右侧上：实时检测画面
- 右侧下：现场上传墙（老师拍的照片会出现在这里）
- 右侧顶：识别模式切换（交通模式 / 全量识别）

### 4. 确认网络

手机和电脑要能互相访问。最稳的是**手机开热点，电脑连热点**——避开学校 WiFi 的客户端隔离。

验证：手机浏览器打开 `http://电脑IP:8001/health`，能看到 JSON 就通。

---

## 二、现场流程（约 2 分钟）

1. **开场**：大屏已经在跑实时检测画面
2. **邀请**：「各位老师可以扫一下左边这个码」
3. **老师扫码** → 手机打开落页，两个按钮
4. **演示拍照**：老师点「拍一张」，对着会场按下快门
5. **结果上屏**：2 秒内大屏右侧出现刚拍的照片，检测框逐一亮起
6. **切换模式**：点「全量识别」，同一画面里开始出现人、手机、椅子等非交通目标
7. **收尾**：切回「交通模式」，「识别类别可配置，交管场景只保留交通相关目标」

---

## 三、故障排查

| 现象 | 原因 | 处理 |
|---|---|---|
| 手机扫码打不开 | Windows 防火墙拦 8001 | 见下方放行命令 |
| 扫码打开是空白 | 手机和电脑不在同一网段 | 改连手机热点 |
| 大屏实时画面是深蓝色 | 检测没启动 | 执行「启动实时检测」 |
| 拍照后没反应 | 后端报错 | 看 `api/output/logs/api.log` |
| 大屏右侧一直空 | 还没人上传 | 正常，拍一张就有了 |
| 二维码指向的 IP 不对 | 多网卡选错 | 访问 `/api/demo/qr.png?host=正确IP:8001` |

### 放行防火墙（管理员权限的终端）

```bash
netsh advfirewall firewall add rule name="Zhitong-Demo-8001" dir=in action=allow protocol=TCP localport=8001
```

---

## 四、为什么不用手机推流

浏览器调用摄像头（`getUserMedia`）要求安全上下文——HTTPS 或 localhost。局域网里的 `http://192.168.x.x` 不满足，Chrome 和 Safari 都会直接拒绝。

所以演示形态是：
- **实时视频**：由我们自己的设备提供（笔记本 USB 摄像头 / 测试视频 / 提前装好 IP Webcam 的手机）
- **老师参与**：扫码「拍一张」，走 `<input capture>`，HTTP 下完全可用
- **老师观看**：扫码「看大屏」，走 MJPEG，同样是普通 `<img>`

这三件事都不需要安装、不需要证书、不需要 HTTPS。

---

## 五、接口清单

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/m` | 手机落地页 |
| GET | `/demo` | 大屏演示页 |
| GET | `/api/demo/qr.png` | 二维码，支持 `?host=IP:端口` |
| GET | `/api/demo/url` | 当前二维码指向的地址 |
| POST | `/api/demo/upload` | 手机拍照上传，返回标注图 |
| GET | `/api/demo/recent` | 最近上传列表（轻量元数据） |
| GET | `/api/demo/image/{id}` | 取某条上传的标注图 |
| GET | `/api/realtime/class-mode` | 查当前识别模式 |
| POST | `/api/realtime/class-mode` | 切换 `traffic` / `all` |

---

## 六、收尾

演示结束记得停掉后端。`0.0.0.0` 监听意味着同一网络里任何设备都能打开管理端，平时不要长期开着。
