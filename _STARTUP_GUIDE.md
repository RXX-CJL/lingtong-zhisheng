# 智瞳灵声 · 启动说明（`_STARTUP_GUIDE.md`）

> 2026-10-06 由 DSH 重写（配合 `start-all.bat` / `restart-backend.bat` 两个脚本）
> 面向：**用户**。你只需要双击，不需要敲命令。
> ⚠ 两个 `.bat` **必须保持纯 ASCII**：cmd.exe 在 `chcp` 生效之前就解析整个脚本，
> 中文注释（UTF-8 或 GBK 都一样）会把命令行撕裂 —— 本轮实测踩过两次，已回退成英文注释。

---

## 一、日常启动（最常用）

**双击 `E:\output\1\start-all.bat`**

它会：
1. 探测 **8001**：已在跑就**跳过**（复用，不会撞端口、不会打断你正在用的后端）
2. 探测 **5173**：已在跑就跳过
3. 打开浏览器 <http://localhost:5173>

| 服务 | 地址 | 说明 |
|---|---|---|
| 管理端 | <http://localhost:5173> | Web 后台 |
| 后端 API 文档 | <http://127.0.0.1:8001/docs> | Swagger |
| 健康检查 | <http://127.0.0.1:8001/health> | 看 `db_path` / `db_size_bytes` / `yolo_available` |

**顶部导航（8 项）**：仪表盘 / 违规管理 / 智能识别 / **实时监测** / **交通事件** / 分歧审核 / 统计分析 / 系统设置

> ★ 2026-10-06 新增「**实时监测**」「**交通事件**」两个入口 —— 之前 `/live` **没有任何入口**，
> 只能手打 URL（用户反馈）。**实时监测页就是测试视频的地方**：

| 想做什么 | 去哪 |
|---|---|
| **测试整段长视频**（几十 MB ~ 数 GB） | **实时监测** 页 → 顶栏「视频文件」填**绝对路径** → 开始（**不限大小、不复制文件**） |
| 提交单张图片 / 短视频为一条违规证据 | 智能识别 页 → 文件上传（上限 500MB） |
| 标信号灯 ROI / 停止线 / 相机参数 | 实时监测 页 → 右上「测速标定/信号灯ROI」 |
| 看违规事件、人工确认或排除 | 交通事件 页 |
| 开关云端 AI 复核（**省钱**） | 系统设置 → AI模型配置（也可在实时监测页控制条） |

> 想边改后端边自动生效：`start-all.bat --reload`
> （**默认不开**：`--reload` 会在每次改动时整进程重启，而 YOLO/torch 模块加载很重，演示时容易卡住）

---

## 二、改了后端代码 → 双击 `restart-backend.bat`

后端**不会**自动加载你新改的代码（这是有意的，见上）。以前要自己去任务管理器找 python.exe 杀，
容易杀错；现在双击 `restart-backend.bat` 即可，它会：

1. 按**端口**（不是进程名）找 8001 的 PID
2. **校验这个 PID 确实是 python.exe** —— 不是就中止，绝不误杀
3. 停止并**等到端口真正释放**
4. 用与原来完全一致的命令重新拉起（新窗口，日志可见）
5. 自检三项：`/health`、`openapi`（应为 **132 operations**）、`cloud_review`

**预期输出（实测）**：
```
  found listener PID=46480
  process name: python.exe
  stopping PID=46480 ...
  port 8001 released.
  launching backend ...
  ---- self check ----
  /health       : OK   db=True size=27369472 yolo=True
  openapi       : 132 operations (expect 132)
  cloud_review  : True
```

### ⚠️ 不要手工 `python -m uvicorn` 起后端（2026-10-10 实测教训）

两个 `.bat` 里都设了 **4 个 `TUNE_*` 调优**，它们**只存在于脚本里**：

| 变量 | 值 | 少了会怎样（实测） |
|---|---|---|
| `YOLO_IMGSZ` | `960` | 回落 1280 → 更慢 |
| `FRAME_RATE` | `6` | 回落 3 → 检测帧率减半 |
| `YOLO_MODEL_SEQUENCE` | `vehicle,traffic_light,helmet,lane` | 多跑 `license_plate`（模型文件不存在 → 回退 COCO 吐盆栽等垃圾） |
| `BOX_PREDICTION` | `1` | 框位置预测失效 |

另外手工启动还必须自己带 `PYTHONPATH=E:\output\1\api;E:\output\1`，否则直接
`Error loading ASGI app. Could not import module "app"`，**进程秒退**（窗口一闪而过，看着像"没反应"）。

> **判定配置对不对，永远看接口而不是凭记忆**：
> `http://127.0.0.1:8001/api/realtime/status` 的 `model_sequence` / `yolo_imgsz` / `frame_rate`。

- **`/health : not ready yet`** = 后端还在加载模型（首次约 10~30 秒），**不是失败**，刷新页面即可。
- 只改**前端**（`.vue`）**不用重启任何东西**：vite 会热更新。

---

## 三、停止服务

关掉对应的黑色命令行窗口即可。

---

## 四、常见问题

| 现象 | 原因 / 处理 |
|---|---|
| 双击后窗口一闪而过 | 现在不会了（旧版撞端口会闪退）。若仍出现，在 cmd 里手动跑一次看报错 |
| 打开 5173 是白屏/连不上 | vite 掉了。重新双击 `start-all.bat`（它会检测到 8001 在跑而只补起前端） |
| 页面数据全是 0 / 请求失败 | 后端没起。看 <http://127.0.0.1:8001/health>；不行就 `restart-backend.bat` |
| 提示 `address already in use` | 旧版脚本才会。新版会跳过已在监听的端口 |
| **桌面多出一堆标题 "ZhiTong Backend API" 的黑窗口，里面是空的** | 后端由 `start ... cmd /k ...` 启动，`cmd /k` 是**常驻父进程**。只杀掉里面的 `python.exe`（例如 AI 反复重启后端）时，父窗口不会退出 → 留下**空壳窗口**。处理：先确认全系统只有一个 python.exe（`Get-Process python`），再关掉那些空窗口；**正常重启请双击 `restart-backend.bat`**，它按端口找 PID，不会留壳 |
| CARLA 与后端同时开 | 8 GB 显存下检测帧率会从 **2.77 掉到 1.5**；跑 CARLA 前建议先停后端 |

---

## 五、常用命令（需要手工时）

```powershell
# 后端（工作目录必须是项目根 E:\output\1）
$env:PYTHONPATH='E:\output\1\api;E:\output\1'
& 'C:\miniconda\envs\zhitong-gpu\python.exe' -m uvicorn app:app --host 127.0.0.1 --port 8001
# ⚠ PYTHONPATH 不能少，否则报 Error loading ASGI app. Could not import module "app"（本轮踩过）

# 前端（本机 node 在 E:\node.exe，不一定在 PATH）
cd E:\output\1\web-admin ; npm run dev

# 前端构建自检（改完 .vue 想确认没写错）
cd E:\output\1\web-admin
$env:TEMP='E:\output\_build_tmp'; $env:TMP=$env:TEMP   # 必须换临时目录，否则 esbuild 清 %TEMP% 会被拒
& 'E:\node.exe' node_modules\vite\bin\vite.js build
```
