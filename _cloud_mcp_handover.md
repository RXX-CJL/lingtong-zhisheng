# 云端闭环 + Windows MCP：实测结论与操作手册

> 2026-11-01。全部结论都有可复跑命令，没有一个数字是估计的。

---

## 第一部分：云端额度真相（推翻「没额度」）

### 实测结果

| 项 | 状态 | 证据 |
|---|---|---|
| DeepSeek key | ✅ **可用，余额 ¥100.00** | `GET /user/balance` → `is_available:true, total_balance:"100.00"` |
| DashScope key | ✅ **可用** | `qwen3-vl-plus` 正确读出图中文字 "RED 100" |
| 代码里的模型名 | ❌ **不存在** | `qwen3-vl-flash` → 404 `Model not exist` |

**「豆包没额度」这个前提是错的。** 真正卡住的是**模型名写死在一个该账号根本不提供的模型上**。

### 为什么之前「云端仲裁归零」

两个独立故障叠在一起：

1. `image_recognizer.py:1225` 硬编码 `model='qwen3-vl-flash'` → 每次都 404
2. `cloud_collaborator.py:1057-1062` 豆包失败时**直接跳过 DeepSeek**（设计上的付费保护）

所以豆包一挂，DeepSeek 也跟着不跑 → 整条云端仲裁静默归零，**日志只有一条 warning**。

### 已做的修复（1 处，最小改动）

`api/image_recognizer.py:1223-1231`：

```python
# 改前（硬编码，该账号不存在此模型）
model='qwen3-vl-flash'

# 改后（可配置，默认用实测验证可用的）
_vl_model = os.environ.get('DASHSCOPE_VL_MODEL', 'qwen3-vl-plus')
model=_vl_model
```

- 备份：`image_recognizer.py.bak_20261101`
- 换模型不用改代码：设环境变量 `DASHSCOPE_VL_MODEL=xxx`
- `py_compile` 通过

### 真实端到端实测（不是 mock）

```
=== analyze_with_doubao（真调用）===
success      = True
耗时         = 4.93s
message      = 豆包分析成功
模型回答     = 「图片为纯红色背景…无任何实际道路、车辆…第二步·是否违规：【不确定】…置信度：10」

=== analyze_with_deepseek_judge（真调用）===
success      = True
耗时         = 1.95s
message      = DeepSeek 审核成功
模型回答     = 「豆包推理：证据充分性【不足】/ 逻辑严谨性【严谨】
                我的独立判断：【无法确定·需人工】/ 置信度 5」
```

**两条链路都真通了。** 而且模型没瞎猜——它正确识别出「这是假图、没有真实道路」，给了低分。这才是真调用该有的表现。

---

## 第二部分：你要自己操作的步骤（四件套）

### 前提
- 后端当前**没有在跑**（8001 未监听）
- 我改的是 `image_recognizer.py`，**必须重启后端才生效**

### 步骤 1：启动服务

```bat
双击 E:\output\1\start-all.bat
```

> ⚠️ **不要**手工 `python -m uvicorn`——会静默丢掉 `TUNE_*` 配置，`/status` 会显示错误的模型序列。

### 步骤 2：确认配置正确（30 秒，必做）

浏览器打开：`http://127.0.0.1:8001/api/realtime/status`

**应该看到这三个字段（值必须一字不差）：**

```json
"model_sequence": "vehicle,traffic_light,helmet,lane"
"yolo_imgsz": 960
"frame_rate": 6
```

- ✅ **三个都对** → 继续步骤 3
- ❌ **任何一个不对** → 停，说明 `TUNE_*` 丢了，告诉我具体是哪一项不对

### 步骤 3：打开云端复核开关

在前端 `http://localhost:5173`（或 `/settings` 页）找到「**云端 AI 复核**」并**勾选开启**。

> 这个开关默认是**关**的（`runtime_settings.json` 里 `cloud_review: false`）。不打开它，云端一次都不会调。

### 步骤 4：跑素材

1. 进入「实时监测」页
2. 视频源选：`E:\output\_dual_cam_demo\dual_cam_demo_h264.mp4`
3. 点开始，让它跑 **30~60 秒**

> ⚠️ 演示素材**只用这一个**。FFV1 母版（`dual_cam_demo_lossless.mkv`）会让 cv2 崩溃。

### 应该出现的现象（判断标准）

**A. 页面上**
- 检测框正常显示（绿=已追踪正常 / 红=违规 / 灰=尚未追踪）
- 画面有中文标注

**B. 后端日志**（`E:\output\1\api\output\logs\api.log`）
用记事本打开，Ctrl+F 搜 **`Doubao analysis result`**
- ✅ **搜到了** → 豆包真在工作
- ❌ **搜不到** → 云端开关没开，或视频里没触发违规事件

再搜 **`DeepSeek judge result`**
- ✅ 搜到了 → 二审也在跑
- ⚠️ 只有 `跳过 DeepSeek 二级审核` → 豆包失败了，把那条日志整行发我

**C. 数据库**（最硬的证据）
跑完 1 分钟后执行：

```bash
cd E:/output/1/api && python -c "
import sqlite3, json
c=sqlite3.connect('zhitong_violations.db'); c.row_factory=sqlite3.Row
rows=c.execute('SELECT id,trigger_time,ai_judgment FROM traffic_events ORDER BY id DESC LIMIT 3').fetchall()
for r in rows:
    j = r['ai_judgment'] or ''
    ok = '"' in j and 'final' in j
    print(r['id'], r['trigger_time'], '有真云端结果=' + str(ok), j[:100])
"
```

- ✅ 看到 **`有真云端结果=True`** 且里面有 `"final": {..."method": "doubao_plus_deepseek"}` → **完全跑通**
- ❌ 全是 `有真云端结果=False` → 告诉我，我去看日志

### 步骤 5（可选）：还原

```bash
cd E:/output/1/api
cp image_recognizer.py.bak_20261101 image_recognizer.py
```

---

## 第三部分：Windows MCP（已装好并跑通）

### 现状

| 项 | 状态 |
|---|---|
| MCP server | `cua-driver.exe` v0.28.0（`C:\Users\ROG\.local\bin\cua-driver\`） |
| DSH 接入方式 | **stdio MCP**（`cordis.patch.yml` 里 computer-use 块**当前是注释状态**） |
| 协议握手 | ✅ 通（`initialize` 返回完整 capabilities） |
| 健康检查 | ✅ **6/7 全绿**（2 项 Windows 不适用） |
| 工具数量 | **57 个** |
| 真实调用 | ✅ 成功列出你桌面的 15 个窗口 |

### 健康检查实测输出

```
✅ cua-driver 0.28.0 on win32 — ok
  ✅ ax_capability: UIAutomation is reachable; UI tree walking will succeed.
  ✅ screen_capture_capability: D3D11 device reachable; Windows Graphics Capture will succeed.
  ⏭ tcc_accessibility / tcc_screen_recording: not applicable on Windows
```

### 它到底能干什么（57 个工具，按用途分）

| 用途 | 工具 |
|---|---|
| **看** | `get_desktop_state`（整屏原分辨率截图）`list_windows` `get_window_state`（UIA 树+元素索引）`get_screen_size` |
| **点/打字** | `click` `double_click` `right_click` `drag` `type_text` `press_key` `hotkey` `scroll` `set_value` |
| **窗口管理** | `launch_app`（**隐藏启动，不抢焦点**）`kill_app` `bring_to_front` `set_window_frame` `list_apps` |
| **菜单** | `invoke_menu`（逐级解析原生菜单） |
| **剪贴板** | `clipboard_read` `clipboard_write` |
| **验证** | `verify_state`（确定性断言，不信「传输成功」就算成功）`health_report` `check_permissions` |
| **光标** | `move_cursor` `get_cursor_position` `set_agent_cursor_*`（4 个） |

### 怎么用（三种方式）

**方式 A：命令行探针（现成，随时可跑）**
```bash
cd E:/output/_tools
node mcp-health.mjs      # 健康检查
node mcp-windows.mjs     # 列出所有窗口
node mcp-list-tools.mjs  # 列出 57 个工具
```

**方式 B：挂在 DSH 里当原生工具（需要你重启）**
`cordis.patch.yml` 第 78-86 行已经写好了配置块，**只是被注释掉**。
但**上次卸载的原因仍未解除**：官方包要求 `@deepseek-ai/dsh-brand 0.2.1-rc.2`，运行时是 rc.3。
所以**不建议现在恢复官方包**——会重演「应用起不来」。
更稳的路：保留 CLI 探针方式（方式 A），需要 GUI 操作时我用探针调用。

**方式 C：直接调 .exe**
```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"x","version":"1"}}}
```

### 一个诚实的局限

`cua-driver` 的 instructions 里自己写了一句：
> "Never advance on transport success alone."

意思是：**命令发出去成功 ≠ 界面真变了**。所以我用它时必须读回状态验证（`verify_state` 或再截一次图），不能只看返回 ok。
这跟我们项目的教训一模一样。

### 升级提示（不急着做）
stderr 提示有 v0.38.0 可用（当前 v0.28.0）。**现在不升级**——v0.28.0 实测能用，升级要重新验证 57 个工具，收益不明确。
需要时：`cua-driver update`

---

## 复现命令汇总

```bash
# 1. DeepSeek 余额（免费，不耗 token）
curl -H "Authorization: Bearer <deepseek_key>" https://api.deepseek.com/user/balance

# 2. 验证 DashScope 模型可用性
cd E:/output/1/api && python -c "
import json,base64,numpy as np,cv2,dashscope
dashscope.api_key=json.load(open('config_runtime.json'))['dashscope']['api_key']
img=np.zeros((360,640,3),np.uint8); img[:,:]=(0,0,200)
cv2.putText(img,'RED 100',(180,200),cv2.FONT_HERSHEY_SIMPLEX,2.2,(255,255,255),5)
_,b=cv2.imencode('.jpg',img)
r=dashscope.MultiModalConversation.call(model='qwen3-vl-plus',
  messages=[{'role':'user','content':[{'image':'data:image/jpeg;base64,'+base64.b64encode(b).decode()},{'text':'图里写的什么字'}]}])
print(r.status_code, r.output.choices[0].message.content[0]['text'])"

# 3. MCP 体检
cd E:/output/_tools && node mcp-health.mjs
```
