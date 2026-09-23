# TASK-020 系统稳定性全面修复 + 数字孪生升级 + 执行者能力剖析

## 任务概述

本次任务包含 **5 个核心子任务**，指挥官（用户）已确认 VPN 已开启，可全面发挥执行者 MCP 和 Skill 能力。

**核心原则**：
1. 质量和稳定性优先
2. 不允许降级方案，必须找更好的方法
3. 所有需要用户同意的操作（高危事件），用户已默认全部同意
4. 信息获取和能力提升来源重点放在 **GitHub**

**项目根目录**：`e:\output\1`
**任务结果文件**：`e:\output\_TASK-020_OUTPUT.json`

---

## ⚠️ 新增规则（永久生效）

### 规则 A：VPN 状态确认
**每次任务开始时，必须在通知文件或执行结果中明确说明"VPN 状态：已开启/未开启"**。如果任务涉及 GitHub/HuggingFace/外部 API 下载，必须先确认 VPN 状态。

### 规则 B：高危操作用户已默认同意
用户已默认同意以下高危操作，无需再次请示：
- 安装 Python 包（pip install / conda install）
- 安装 npm 包
- 修改系统配置
- 重启服务
- 拉取 GitHub 代码
- 删除临时文件

但仍需在 OUTPUT.json 的 `deviations` 字段中记录所有变更。

### 规则 C：禁止降级方案
遇到问题时**禁止用低质量方法绕过**（如关闭某个功能、用 fake data 代替实现）。必须：
1. 找更高质量的解决方案
2. 或暂停任务，报告指挥官，由指挥官决策
3. 信息获取来源优先 GitHub（Issues、Discussions、Releases、Commits）

---

## 核心 Bug 根因（已诊断）

**所有 API 调用返回 404** 的根因：

`e:\output\1\web-admin\src\api\index.js` 中实时检测 API 路径**缺少 `/api` 前缀**：
```javascript
// 当前错误代码
export const getRealtimeCameraList = () => request.get('/realtime/camera/list')
export const startRealtimeDetection = (idx) => request.post('/realtime/start', ...)
```

但后端 router prefix 是 `/api/realtime`：
```python
router = APIRouter(prefix="/api/realtime", tags=["realtime"])
```

Vite 代理 `/api → 127.0.0.1:8001` 是按字面转发，前端用 `/realtime/...` 调用会被代理到 `http://127.0.0.1:8001/realtime/...`，**不是** `/api/realtime/...`，所以后端返回 404。

**修复方案**：所有实时检测 API 调用必须改为带 `/api` 前缀：
```javascript
export const getRealtimeCameraList = () => request.get('/api/realtime/camera/list')
export const startRealtimeDetection = (idx) => request.post('/api/realtime/start', ...)
```

---

## 执行步骤

### 步骤 1：修复 API 路径 404 Bug（最优先）

**目标**：修复前端所有实时检测 API 调用的路径，添加 `/api` 前缀。

**涉及文件**：
- `e:\output\1\web-admin\src\api\index.js`（核心修复点）
- 其他任何前端 JS 文件中涉及实时检测 API 的调用

**要求**：
1. 检查 `e:\output\1\web-admin\src\api\index.js` 中所有 `'/realtime/...` 路径，改为 `'/api/realtime/...'`
2. 同时检查其他文件是否有同类问题（用 grep 全局搜索 `/realtime/`）
3. 修复后端 MJPEG 流地址也使用正确的 `/api/realtime/stream` 路径
4. 验证：所有 API 调用都能正常返回 200，不再有 404

**验证标准**：
- `curl http://127.0.0.1:5173/api/realtime/camera/list` 返回 200（通过 Vite 代理）
- `curl http://127.0.0.1:8001/api/realtime/camera/list` 直接返回 200
- 前端"实时摄像头"标签页加载摄像头列表正常
- 启动检测后画面正常显示

---

### 步骤 2：数字孪生 3D 场景全面升级

**目标**：解决数字孪生演示模型问题，提升演示效果。

**当前问题**（用户反馈）：
1. 红绿灯像流水灯，没有倒计时
2. 灯与灯之间没有逻辑联动（红灯时所有方向都红？绿灯时所有方向都绿？不符合实际）
3. 车辆数量太多
4. 车辆穿模（穿越建筑物/其他车辆）
5. 车辆没有停车等红绿灯的行为
6. 没有行人、自行车等其他交通参与者

**涉及文件**：
- `e:\output\1\digital_twin\` 整个目录

**要求**：

#### 2.1 红绿灯逻辑重做
- 真正的四相位信号灯（南北直行/南北左转/东西直行/东西左转）
- 每个相位有倒计时显示（30秒/30秒/30秒/30秒循环）
- 灯色逻辑：
  - 南北直行绿灯 ↔ 东西直行红灯
  - 南北左转绿灯 ↔ 东西左转红灯
  - 存在黄灯过渡（3秒黄灯）
- 现实世界的信号灯配时方案参考 GitHub 项目

#### 2.2 车辆行为逻辑
- 使用简单的物理引擎（如 cannon-es 或自带 raycaster 碰撞检测）
- 车辆遵守交通规则：
  - 红灯停车（车头停在停止线前）
  - 绿灯通行
  - 黄灯减速
  - 不能穿模
- 车辆数量控制（建议 8-12 辆）
- 添加行人道、人行横道、斑马线

#### 2.3 3D 模型升级
- 使用更精细的车辆模型（GitHub 搜索 three.js car model）
- 添加建筑、树木、路灯等场景元素
- 路面添加车道线、人行横道线

**参考来源**（GitHub 搜索关键词）：
- `three.js traffic simulation`
- `three.js smart city`
- `three.js traffic light`
- `WebGL traffic light demo`

**验证标准**：
- 红绿灯有倒计时和正确的相位切换
- 车辆在红灯时停车，绿灯时通行
- 车辆不穿模
- 场景视觉效果好

---

### 步骤 3：管理端 API 自动填充与优化

**目标**：解决用户每次手动输入 API Key 的问题。

**当前问题**：
- 管理后台 API 配置（豆包、DeepSeek 等）每次都要手动输入
- 用户体验差

**涉及文件**：
- `e:\output\1\web-admin\src\` API 配置相关组件
- `e:\output\1\api\config_manager.py`

**要求**：
1. 检查当前 API Key 的存储和读取机制
2. **优先从后端配置文件自动读取**，前端无需输入
3. 如必须前端输入，则：
   - 首次输入后保存到 localStorage
   - 提供"清除已保存"按钮
   - 打开页面时自动填充
4. 后端 API Key 存储：
   - 加密存储（不能明文写在代码里）
   - 支持多环境切换（dev/test/prod）
   - 提供管理接口（可在线修改）

**验证标准**：
- 用户打开管理后台，API Key 自动填充
- 无需每次手动输入
- 安全存储

---

### 步骤 4：执行者能力全面剖析（必须执行）

**目标**：让执行者输出自己的完整能力清单，方便指挥官后续充分发挥执行者的能力。

**输出文件**：`e:\output\1\EXECUTOR_CAPABILITY_REPORT.md`

**要求**：
1. 列出所有可用的 MCP（连接的服务）：
   - 名称、功能、典型用途
   - 当前连接状态
   - 已使用的场景示例
2. 列出所有可用的 Skills：
   - 名称、功能、触发条件
   - 典型使用场景
3. 列出所有可用的工具（Tools）：
   - 文件操作、命令执行、网络搜索等
4. 列出可访问的外部资源：
   - GitHub 仓库
   - HuggingFace 模型
   - 公共数据集
5. 列出执行者的工作偏好：
   - 擅长的领域
   - 不擅长的领域
   - 最佳实践
6. 列出当前系统的关键能力短板：
   - 需要新 MCP 才能解决的能力缺口
   - 需要新 Skill 才能解决的能力缺口
7. 给出后续能力提升建议：
   - 推荐安装的新 MCP/Skill
   - 推荐关注的 GitHub 项目

**验证标准**：
- 报告文件存在且内容完整
- 信息准确，不夸大

---

### 步骤 5：移除"截图"任务（用户要求）

**目标**：移除 TASK-018 和 TASK-019 中添加的"截图保存"功能。

**涉及文件**：
- `e:\output\1\web-admin\src\views\AIDetect.vue`

**要求**：
1. 移除"截图保存"按钮
2. 移除 `handleSnapshot` 函数
3. 移除相关的 `getRealtimeSnapshot` API 调用
4. 清理相关代码和样式

**验证标准**：
- 前端"实时摄像头"标签页不再显示"截图保存"按钮
- 控制台无相关错误

---

### 步骤 6：端到端验证

**目标**：确认所有修复和优化都生效。

**验证流程**：
1. 启动后端（8001）、前端（5173/5174）、数字孪生（5000）
2. 验证 API 调用不再 404
3. 验证实时摄像头画面正常显示
4. 验证数字孪生 3D 场景效果良好
5. 验证 API Key 自动填充
6. 验证"截图"按钮已移除
7. 写实测报告：`e:\output\1\test_results\TASK-020_e2e_test_report.md`

**报告内容**：
- 各步骤的验证结果（PASS/FAIL）
- 截图（如能获取）
- 发现的问题及修复

---

## 强制规则

1. **所有代码修改必须通过 old_string 精确匹配替换**
2. **修改前必须先读取文件**
3. **所有变更必须在 _TASK-020_OUTPUT.json 的 deviations 字段中列出**
4. **不得在代码中硬编码 API Key**
5. **VPN 状态必须在 OUTPUT 中明确说明**
6. **遇到问题禁止降级**，必须找更好的方法或报告指挥官
7. **能力剖析报告必须全面、真实**

---

## 验收标准

必须全部满足才算 PASS：

- [ ] API 路径 404 Bug 已修复，所有 API 调用返回 200
- [ ] 实时摄像头画面正常显示（带 YOLO 检测框）
- [ ] 数字孪生红绿灯有倒计时和相位逻辑
- [ ] 数字孪生车辆遵守红绿灯，不穿模
- [ ] 数字孪生场景视觉效果好
- [ ] 管理端 API Key 自动填充
- [ ] "截图保存"按钮已移除
- [ ] 执行者能力剖析报告 `e:\output\1\EXECUTOR_CAPABILITY_REPORT.md` 完整
- [ ] 输出结果文件 `e:\output\_TASK-020_OUTPUT.json`
- [ ] VPN 状态已在 OUTPUT 中说明

---

## 输出要求

成功时写入：`e:\output\_TASK-020_OUTPUT.json`
失败时写入：`e:\output\_TASK-020_ERROR.json`

JSON 格式：
```json
{
  "task": "TASK-020",
  "timestamp": "ISO8601",
  "status": "PASS/FAIL/PARTIAL",
  "vpn_status": "已开启",
  "details": {
    "step1_api_fix": {...},
    "step2_digital_twin": {...},
    "step3_api_autofill": {...},
    "step4_capability_report": {"path": "..."},
    "step5_remove_snapshot": {...},
    "step6_e2e_validation": {...}
  },
  "deviations": [...]
}
```
