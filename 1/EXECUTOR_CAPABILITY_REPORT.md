# 执行者能力剖析报告

## 1. 可用 MCP 服务

| 服务名称 | 功能描述 | 典型用途 | 连接状态 |
|---------|---------|---------|---------|
| integrated_browser | 浏览器自动化 | 前端测试、页面交互、截图验证 | 可用 |
| mcp_GitHub | GitHub API 操作 | 代码仓库管理、PR 创建、代码搜索 | 可用 |
| mcp_Multi_Fetch | 多格式内容抓取 | HTML/JSON/TXT/Markdown 内容获取 | 可用 |
| mcp_Postgrest | PostgreSQL REST API | 数据库查询与操作 | 可用 |
| mcp_Sequential_Thinking | 顺序思考工具 | 复杂问题分解与推理 | 可用 |
| mcp_bigquery | BigQuery 查询 | 大规模数据分析 | 可用 |
| mcp_fetch | HTTP 请求 | 通用网络请求 | 可用 |
| mcp_mcp-clickhouse | ClickHouse 数据库 | 实时数据分析与查询 | 可用 |
| mcp_supabase-community | Supabase 服务 | 数据库与认证服务 | 可用 |
| mcp_windows-cli | Windows 命令执行 | 系统命令、SSH 操作 | 可用 |

## 2. 可用 Skills

### 2.1 前端开发类

| Skill | 触发条件 | 典型场景 |
|-------|---------|---------|
| web-dev | 创建网站/页面 | 从零构建 Web 应用 |
| frontend-design | UI设计/美化 | 页面设计与美化 |
| web-artifacts-builder | 复杂前端 | 多组件 React 应用 |
| shadcn | 组件库 | UI 组件集成 |
| figma | Figma 协作 | 设计稿解析与代码生成 |

### 2.2 数据可视化类

| Skill | 触发条件 | 典型场景 |
|-------|---------|---------|
| chart-visualization | 图表/可视化 | 数据图表生成 |
| Dashboard Page | 仪表盘页面 | KPI 面板与时间控件 |
| report-page | 报告页面 | 源数据支持的报告文档 |

### 2.3 数据分析类

| Skill | 触发条件 | 典型场景 |
|-------|---------|---------|
| data-analysis | Excel/CSV 分析 | 数据统计与汇总 |
| consulting-analysis | 市场分析 | 行业研究报告 |

### 2.4 文档与演示类

| Skill | 触发条件 | 典型场景 |
|-------|---------|---------|
| doc-coauthoring | 文档编写 | 技术文档协作 |
| slides | PPT/演示文稿 | 幻灯片制作 |
| PPT Page | 演示文稿 | HTML 演示画廊 |
| Doc Page | 文档页面 | 打印文档页面 |

### 2.5 AI 与工具类

| Skill | 触发条件 | 典型场景 |
|-------|---------|---------|
| alipay-payment-integration | 支付宝支付集成 | 支付功能接入 |
| douyinpay-payment-integration | 抖音支付集成 | 支付功能接入 |
| brainstorming | 创意/方案 | 头脑风暴与方案设计 |
| algorithmic-art | 算法艺术 | p5.js 生成艺术 |
| canvas-design | 画布设计 | PNG/PDF 视觉设计 |

### 2.6 代码质量类

| Skill | 触发条件 | 典型场景 |
|-------|---------|---------|
| TRAE-code-review | 代码审查 | 合并请求审查 |
| TRAE-debugger | 调试 | 运行时 Bug 诊断 |
| security-best-practices | 安全审查 | 安全最佳实践检查 |

### 2.7 游戏开发类

| Skill | 触发条件 | 典型场景 |
|-------|---------|---------|
| phaser-2d-game | 2D 游戏 | Phaser 游戏开发 |
| three-webgl-game | WebGL 游戏 | Three.js 3D 游戏 |
| react-three-fiber-game | React 3D 游戏 | React Three Fiber |

### 2.8 云服务类

| Skill | 触发条件 | 典型场景 |
|-------|---------|---------|
| cloudflare | Cloudflare 平台 | Workers、AI 代理开发 |
| byted-bp-cdn-pagesdeploy | CDN 部署 | 静态页面部署 |

### 2.9 办公协作类

| Skill | 触发条件 | 典型场景 |
|-------|---------|---------|
| lark-* | 飞书操作 | 文档、表格、日历、会议 |
| wecom-* | 企业微信操作 | 消息、文档、会议、日程 |
| notion-* | Notion 操作 | 知识库管理 |
| tencent-docs | 腾讯文档 | 在线文档管理 |

## 3. 可用工具

### 3.1 文件操作工具

| 工具 | 功能 |
|------|------|
| Read | 读取文件内容 |
| Write | 写入文件 |
| Edit | 修改文件（精确替换） |
| DeleteFile | 删除文件 |
| Glob | 文件模式匹配 |
| LS | 列出目录 |
| Grep | 内容搜索 |
| SearchCodebase | 代码库检索 |

### 3.2 命令执行工具

| 工具 | 功能 |
|------|------|
| Shell | 执行系统命令 |
| GetDiagnostics | 获取代码诊断 |

### 3.3 网络工具

| 工具 | 功能 |
|------|------|
| WebSearch | 网络搜索 |
| WebFetch | 获取网页内容 |

### 3.4 任务管理工具

| 工具 | 功能 |
|------|------|
| TodoWrite | 任务规划与跟踪 |
| AskUserQuestion | 用户问答 |
| NotifyUser | 通知用户 |
| OpenPreview | 预览网页 |

### 3.5 MCP 调用工具

| 工具 | 功能 |
|------|------|
| run_mcp | 调用 MCP 服务 |

## 4. 可访问外部资源

| 资源类型 | 访问方式 | 用途 |
|---------|---------|------|
| GitHub | mcp_GitHub | 代码仓库、Issues、PR |
| HuggingFace | WebSearch | 模型下载、数据集 |
| 公共数据集 | WebSearch | 数据获取 |
| 技术文档 | WebFetch | API 文档、教程 |

## 5. 工作偏好

### 5.1 擅长领域

- **前端开发**: Vue/React 框架、Three.js 3D 场景、Element Plus UI
- **后端开发**: Flask/Python API 开发
- **代码修复**: Bug 诊断与修复、代码重构
- **文档编写**: 技术文档、报告生成
- **系统集成**: API 对接、服务配置

### 5.2 不擅长领域

- **移动端开发**: Android/iOS 原生开发（但支持 React Native）
- **大规模分布式系统**: 复杂微服务架构设计
- **机器学习模型训练**: 深度学习模型训练与调优
- **硬件交互**: 嵌入式系统、物联网设备控制

### 5.3 最佳实践

- 代码修改前必须先读取文件
- 使用精确匹配替换（old_string/new_string）
- 复杂任务先规划（TodoWrite）再执行
- 代码修改后进行验证
- 禁止硬编码敏感信息（API Key 等）

## 6. 能力短板

### 6.1 需要新 MCP 的能力缺口

| 能力缺口 | 推荐 MCP | 原因 |
|---------|---------|------|
| Redis 操作 | Redis MCP | 缓存与实时数据存储 |
| Docker 管理 | Docker MCP | 容器部署与管理 |
| Kubernetes | K8s MCP | 容器编排 |
| 邮件发送 | Email MCP | 邮件通知功能 |
| 短信服务 | SMS MCP | 短信通知功能 |

### 6.2 需要新 Skill 的能力缺口

| 能力缺口 | 推荐 Skill | 原因 |
|---------|---------|------|
| 数据库迁移 | DB Migration | 数据库版本管理 |
| API 文档生成 | API Doc Generator | OpenAPI 文档自动生成 |
| 性能监控 | Performance Monitor | 系统性能分析 |
| 日志分析 | Log Analyzer | 日志检索与分析 |
| CI/CD | CI/CD Pipeline | 自动化构建与部署 |

## 7. 后续能力提升建议

### 7.1 推荐安装的 MCP

1. **Redis MCP**: 用于缓存和实时数据存储
2. **Docker MCP**: 容器化部署支持
3. **Email MCP**: 邮件通知功能
4. **SMS MCP**: 短信通知功能

### 7.2 推荐安装的 Skill

1. **API 文档生成**: 自动生成 OpenAPI 文档
2. **性能监控**: 系统性能分析
3. **日志分析**: 日志检索与分析

### 7.3 推荐关注的 GitHub 项目

1. **vuejs/core**: Vue 3 核心库
2. **element-plus/element-plus**: Element Plus UI 组件库
3. **mrdoob/three.js**: Three.js 3D 库
4. **tensorflow/tensorflow**: 机器学习框架
5. **kubernetes/kubernetes**: K8s 容器编排

---

**生成时间**: 2026-03-18
**执行者版本**: TRAE Agent