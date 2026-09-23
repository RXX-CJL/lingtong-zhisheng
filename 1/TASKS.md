# 智瞳灵声 · 前端开发指挥清单

> **指挥人**：项目架构师
> **执行人**：IDE / 开发者
> **目标**：补全项目缺失的两大前端系统 —— 微信小程序（面向公众）+ Web 管理端（面向管理员），并打通本地检测端与后端 API 的数据通道。
> **后端 API 地址**（开发环境）：`http://127.0.0.1:8000`
> **API 文档**：`http://127.0.0.1:8000/docs`（FastAPI 自动生成的 Swagger UI）

---

## 0. 项目现状速览（执行前必读）

### 已有的后端接口

| 接口 | 路径 | 功能 |
|------|------|------|
| POST | `/api/violations/submit` | 提交单条违规证据（含 Base64 图片/视频） |
| POST | `/api/violations/batch` | 批量提交违规证据 |
| GET | `/api/violations/list` | 违规列表（支持类型/状态/时间筛选 + 分页） |
| GET | `/api/violations/{id}` | 单条违规详情 |
| PUT | `/api/violations/{id}` | 更新违规状态（确认/驳回） |
| DELETE | `/api/violations/{id}` | 删除违规记录 |
| GET | `/api/violations/statistics/summary` | 违规统计数据 |
| POST | `/api/wechat/violation/submit` | 微信小程序专用提交接口 |
| GET | `/api/wechat/violation/list` | 微信小程序查看自己提交的记录 |
| GET | `/uploads/{filename}` | 静态图片/视频资源访问 |

### 已有的数据模型（核心表 `violation_evidences`）

```
id (int, 主键)
violation_type (string, 如 "red_light", "no_helmet", "wrong_way")
track_id (int)
confidence (float, 0-1)
position (text, JSON 存储 {x,y,w,h})
timestamp (datetime)
image_path (string, 本地文件路径)
video_path (string, 可选)
additional_info (text, JSON 存储扩展字段)
cloud_validated (bool, 是否经云端二次确权)
cloud_result (text, 云端分析结果)
status (string, "pending" / "confirmed" / "rejected")
created_at / updated_at
```

### 违规类型枚举

```python
red_light      # 闯红灯
no_helmet      # 未戴头盔
wrong_way      # 逆行
illegal_parking # 违停
lane_departure # 压线
speeding       # 超速
```

### 当前缺失的内容

1. ✅ **后端 API** —— 已存在（`e:\output\1\api\`）
2. ⚠️ **本地检测端 → API** —— `zhitong` 检测到违规后**不会自动上传**，需补一个上传模块
3. ❌ **微信小程序** —— 完全缺失（约 5-6 个页面）
4. ❌ **Web 管理端** —— 完全缺失（约 7-8 个页面）

---

## 任务 1：打通本地检测端与后端 API

**文件修改/新增**：

1. **修改** `zhitong/config.py` —— 底部添加 API 配置：
   ```python
   # API 服务配置
   API_BASE_URL = "http://127.0.0.1:8000"
   API_SUBMIT_ENDPOINT = "/api/violations/submit"
   API_TIMEOUT = 10  # 秒
   API_RETRY_TIMES = 2  # 失败重试次数
   ENABLE_API_UPLOAD = True  # 开关：是否开启自动上传
   ```

2. **新增** `zhitong/api_client.py` —— 一个轻量的 API 客户端类：
   - 方法 `submit_violation(violation_obj, frame_image)`：将 `Violation` 对象 + 画面帧上传到后端
   - 将 `frame_image` 编码为 JPEG → Base64 字符串（因为 API 用 Base64 接收图片）
   - 调用 `POST /api/violations/submit`
   - 失败时重试 `API_RETRY_TIMES` 次，所有失败需记录到 `output/logs/api_upload_error.log`
   - 非阻塞方式：使用独立线程/队列执行上传，不影响主检测循环

3. **修改** `zhitong/main.py` —— 在 `ZhiTongSystem.__init__` 中初始化 `APIClient`，并在检测到违规（违规被保存证据之后）调用 `api_client.submit_violation(...)`

**验收标准**：
- [ ] 启动 `api/app.py`（`uvicorn app:app --reload --port 8000`）后，再启动 `zhitong/main.py` 处理一段测试视频
- [ ] 检测到的违规应自动出现在 GET `/api/violations/list` 的结果中
- [ ] 每条违规都有对应的图片文件保存在 `api/uploads/` 目录下

---

## 任务 2：微信小程序（面向公众用户）

### 2.1 项目初始化

**目录**：`e:\output\1\wechat-miniprogram\`（新建）

**小程序结构**：

```
wechat-miniprogram/
├── app.js                    # 全局逻辑（API base URL、用户 openid 初始化）
├── app.json                  # 全局配置（注册 5 个页面，导航栏标题"智瞳灵声"）
├── app.wxss                  # 全局样式（统一配色：科技蓝 #1890ff）
├── project.config.json       # 开发者工具配置
├── sitemap.json
├── pages/
│   ├── index/                # 首页（违规提交入口 + 我的统计）
│   ├── submit/               # 违规手动提交（拍照/相册 + 选择类型）
│   ├── list/                 # 我提交的违规记录列表
│   ├── detail/               # 单条违规详情（大图 + 状态 + 云端分析结果）
│   └── statistics/           # 全局违规统计（可选：数据可视化图表）
└── utils/
    ├── api.js                # 封装 wx.request 调用（统一 Base URL、错误处理）
    └── format.js             # 时间格式化、违规类型中文映射等工具
```

### 2.2 关键页面设计说明

#### 页面 1：首页 `pages/index/`
- 顶部大标题 + 项目 Logo 区
- 三个圆形功能入口按钮：
  - 📸 **拍照举报** → `submit` 页面
  - 📋 **我的记录** → `list` 页面
  - 📊 **全局统计** → `statistics` 页面
- 底部"最近 30 天我举报了 X 条违规"简要统计卡
- 调用 API：`GET /api/wechat/statistics/my?openid=xxx`

#### 页面 2：违规提交 `pages/submit/`
- **步骤 1（图片选择）**：`wx.chooseMedia` 支持拍照或从相册选 1-3 张图
- **步骤 2（类型选择）**：水平滚动的卡片式违规类型选择（6 种类型，选中高亮）
- **步骤 3（补充说明，可选）**：文本输入框，最多 200 字
- **提交按钮**：将图片转为 Base64 + 调用 `POST /api/wechat/violation/submit`
- 提交成功后 Toast "已提交，待审核"，2 秒后自动跳转到 `list` 页面

#### 页面 3：违规列表 `pages/list/`
- 卡片式列表，每条显示：缩略图、类型（中文）、时间、状态徽标
- 状态徽标颜色：
  - `pending` → 橙色 "待审核"
  - `confirmed` → 绿色 "已确认"
  - `rejected` → 灰色 "已驳回"
- 下拉刷新、上拉触底加载更多
- 调用 API：`GET /api/wechat/violation/list?openid=xxx&page=1&page_size=10`
- 点击卡片 → `detail` 页面

#### 页面 4：违规详情 `pages/detail/`
- 大图预览（支持 `wx.previewImage` 点击放大）
- 违规类型、时间、置信度百分比
- 状态徽标 + 云端分析结果（如果 `cloud_validated == true`，显示 `cloud_result` 文本）
- "我要补充信息"按钮（可选，暂不实现）

#### 页面 5：统计 `pages/statistics/`
- 调用 `GET /api/violations/statistics/summary` 获取全局数据
- 展示：总违规数、按类型的柱状图、按日期的折线图
- 使用 `wx-charts` 或 `ec-canvas` 组件（任选一个轻量级图表库）

### 2.3 utils/api.js 规范

```javascript
// Base URL —— 开发环境用你电脑的局域网 IP，不要写 127.0.0.1（真机调试会失败）
// 例如 http://192.168.1.100:8000
// 用户 openid 开发阶段可在 app.js 里用一个固定测试值，如 "TEST_OPENID_001"

// 每个方法返回 Promise
// 统一错误处理：网络错误 Toast "网络连接失败"，业务错误 Toast 后端返回的 message
```

### 2.4 违规类型中文映射表（在 `utils/format.js` 中维护）

```
red_light      → 闯红灯
no_helmet      → 未戴头盔
wrong_way      → 逆行
illegal_parking → 违规停车
lane_departure → 压线行驶
speeding       → 超速
```

**验收标准**：
- [ ] 微信开发者工具打开项目可正常编译无报错
- [ ] 5 个页面之间的跳转流畅
- [ ] 手动提交一条违规 → `GET /api/wechat/violation/list` 能看到
- [ ] "我的记录"页面显示刚才提交的内容
- [ ] 详情页面图片可点击放大

---

## 任务 3：Web 管理端（面向管理员）

### 3.1 技术选型

使用 **Vue 3 + Vite + Element Plus + ECharts**。理由：
- Vue 3 组件化开发效率高
- Element Plus 提供开箱即用的表格、表单、对话框
- ECharts 用于统计数据可视化

**目录**：`e:\output\1\web-admin\`（新建）

### 3.2 项目结构

```
web-admin/
├── index.html
├── package.json            # 依赖: vue, vue-router, pinia, element-plus, echarts, axios, @element-plus/icons-vue
├── vite.config.js          # 配置 server.proxy → /api 代理到 http://127.0.0.1:8000
├── src/
│   ├── main.js             # 入口，注册 Element Plus
│   ├── App.vue
│   ├── router/index.js     # 路由配置（7 个页面）
│   ├── api/
│   │   └── index.js        # axios 实例 + 所有 API 调用封装
│   ├── views/
│   │   ├── Dashboard.vue   # 仪表盘首页（统计图表）
│   │   ├── ViolationList.vue  # 违规列表 + 审核
│   │   ├── ViolationDetail.vue # 违规详情弹窗/页面
│   │   ├── Statistics.vue  # 统计分析（多图表）
│   │   └── About.vue       # 关于项目
│   └── components/
│       ├── ViolationCard.vue   # 违规卡片组件（复用）
│       ├── StatusBadge.vue     # 状态徽章组件
│       └── TypeTag.vue         # 类型标签组件
└── README.md               # 写启动命令
```

### 3.3 页面功能设计

#### 页面 1：仪表盘 `Dashboard.vue`
- 顶部 4 个统计卡片：总违规数、今日新增、待审核数、已确认数
- 调用 `GET /api/violations/statistics/summary`
- 左侧饼图：各类型违规占比
- 右侧折线图：最近 7 天违规趋势
- 下方"最新 5 条待审核"列表 → 点击跳转到 ViolationList.vue

#### 页面 2：违规列表 `ViolationList.vue`
- **搜索区**：类型下拉筛选、状态下拉筛选、日期范围选择器
- **表格**（`el-table`）：
  - 列：ID、类型（彩色标签）、置信度（百分比条）、时间、状态（可切换下拉）、云端校验（✅/❌）、操作按钮
  - 操作按钮列："查看详情"、"确认"、"驳回"、"删除"
- **批量操作**：勾选多条 → 批量确认 / 批量删除
- **分页**：使用 Element Plus 的 `el-pagination`
- **状态切换按钮**：点击"确认"调用 `PUT /api/violations/{id}` 修改 `status=confirmed`；"驳回"修改为 `status=rejected`

#### 页面 3：违规详情 `ViolationDetail.vue`
- 大图片预览
- 所有字段表格化展示（包括 `additional_info` JSON 展开为键值对）
- 云端分析结果展示区（如果有）
- 状态操作按钮组（待确认/已确认/已驳回三态切换）

#### 页面 4：统计分析 `Statistics.vue`
- 按类型柱状图 + 按状态饼图 + 按日期面积图
- 支持按日期范围筛选后重新加载图表

#### 页面 5：关于 `About.vue`
- 项目介绍文字 + 团队成员列表

### 3.4 全局组件规范

- **StatusBadge.vue**：接收 `status` prop，输出不同颜色的 `el-tag`
- **TypeTag.vue**：接收 `violation_type` prop，输出带图标的彩色类型标签
- **api/index.js**：统一的 axios 实例，所有请求通过 `request(config)` 方法，统一错误 Toast

### 3.5 启动命令写入 `package.json`

```json
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  }
}
```

**验收标准**：
- [ ] `npm install && npm run dev` 后 `http://localhost:5173` 可访问
- [ ] 仪表盘显示正确的统计数字
- [ ] 列表页可搜索、可分页、可切换状态
- [ ] 点击"确认"后状态徽标从橙色变为绿色，API 返回成功
- [ ] 图表可正常渲染无报错

---

## 任务 4：一键启动脚本（可选，但强烈推荐）

**目的**：为用户提供一键启动开发环境的入口（后端 + 前端）。

**文件**：`e:\output\1\start-dev.bat`

```batch
@echo off
echo ========================================
echo  智瞳灵声开发环境启动
echo ========================================
echo.

echo [1/2] 启动后端 API 服务 (端口 8000)...
cd api
start "后端API" cmd /k "uvicorn app:app --reload --port 8000"
cd ..

echo [2/2] 启动 Web 管理端 (端口 5173)...
cd web-admin
start "Web管理端" cmd /k "npm run dev"
cd ..

echo.
echo 启动完成！
echo - API 文档: http://127.0.0.1:8000/docs
echo - Web管理端: http://localhost:5173
echo - 微信小程序: 用微信开发者工具打开 wechat-miniprogram 目录
pause
```

---

## 任务执行优先级

| 优先级 | 任务 | 依赖 | 预计耗时 |
|--------|------|------|----------|
| P0 | 任务 1（打通检测端 → API） | 无 | 1 小时 |
| P1 | 任务 3（Web 管理端） | 任务 1 完成后可并行 | 3-4 小时 |
| P1 | 任务 2（微信小程序） | 任务 1 完成后可并行 | 3-4 小时 |
| P2 | 任务 4（启动脚本） | 任务 2、3 完成 | 30 分钟 |

**建议工作流**：先完成任务 1 → 任务 2 和任务 3 并行开发。

---

## 执行后自检清单

- [ ] 数据库 `zhitong_violations.db` 中有测试数据
- [ ] `api/uploads/` 目录下有图片文件
- [ ] Swagger 文档 `http://127.0.0.1:8000/docs` 可访问
- [ ] 微信小程序 5 个页面可正常跳转和调用 API
- [ ] Web 管理端 5 个页面可正常访问和操作
- [ ] 三个系统（本地检测端 / 小程序端 / Web 管理端）共用同一个数据库

---

*本文件为 IDE 执行指南。遇到不确定的实现细节时，优先参考后端 API 的现有代码风格保持一致性；遇到阻塞问题在此文件顶部追加"问题记录"供指挥人审阅。*
