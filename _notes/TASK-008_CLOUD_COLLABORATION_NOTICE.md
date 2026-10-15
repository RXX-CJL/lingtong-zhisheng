# TASK-008 端云主动协作特性 + 系统全面完善

## 一、任务概述

**任务编号**: TASK-008
**任务名称**: 端云主动协作特性开发 + 系统全面升级
**预计耗时**: 6-8小时（整晚运行）
**核心目标**: 实现"本地AI主动咨询云端AI"的端云协同架构，同时全面完善后端API、管理后台、微信小程序、数字孪生四大模块

---

## 二、执行步骤（按优先级排序）

### 第一阶段：端云主动协作核心模块（优先级：最高）

#### 步骤1：创建云端协作管理器 `cloud_collaborator.py`

**文件位置**: `e:\output\1\api\cloud_collaborator.py`

**功能要求**:
```python
class CloudCollaborator:
    """
    端云协作管理器 - 本地AI主动咨询云端AI的核心模块
    三种协作模式：
    1. URGENT - 高置信度违规，立即上报确认
    2. CONSULT - 模糊地带，主动咨询云端
    3. NORMAL - 正常画面，仅统计不上报
    """
```

**必须实现的方法**:
- `should_consult_cloud(detection_result)` - 判断是否需要咨询云端（返回 "urgent"/"consult"/None）
- `consult_cloud(image_data, local_judgment, reason)` - 主动咨询云端大模型
- `process_cloud_response(local_result, cloud_result)` - 处理云端响应，生成最终裁决
- `build_ai_trace(yolo_result, doubao_result, deepseek_result, final_result)` - 构建v3版本ai_trace嵌套结构
- `save_collaboration_log(session_id, data)` - 保存协作日志供前端展示
- `get_statistics()` - 获取协作统计数据（总咨询次数、确认率、分歧率、准确率提升）

**触发阈值配置**:
```python
THRESHOLDS = {
    "urgent_confidence": 0.75,    # 高于此值 → 立即上报确认
    "consult_low": 0.4,           # 低于此值 → 直接丢弃（正常）
    "consult_high": 0.75,         # 介于consult_low和urgent之间 → 主动咨询
    "disagreement_threshold": 0.3 # 本地与云端置信度差超过此值 → 标记分歧
}
```

#### 步骤2：新增云端协作API路由 `routers/cloud_collab.py`

**文件位置**: `e:\output\1\api\routers\cloud_collab.py`

**必须实现的接口**:

| 接口 | 方法 | 功能 |
|------|------|------|
| `/api/cloud/consult` | POST | 本地AI主动咨询云端（核心接口） |
| `/api/cloud/collab-list` | GET | 获取协作记录列表 |
| `/api/cloud/collab-detail/{id}` | GET | 获取单次协作详情 |
| `/api/cloud/statistics` | GET | 获取协作统计数据 |
| `/api/cloud/disagreements` | GET | 获取分歧案例列表（待人工复核） |
| `/api/cloud/resolve-disagreement` | POST | 人工裁决分歧案例 |

**咨询请求格式**:
```json
{
  "session_id": "uuid",
  "image_base64": "...",
  "local_judgment": {
    "violation_type": "no_helmet",
    "violation_cn": "未戴头盔",
    "confidence": 0.62,
    "detections": [...]
  },
  "consult_reason": "low_confidence",
  "urgency": "normal"
}
```

**响应格式（含ai_trace v3）**:
```json
{
  "success": true,
  "session_id": "uuid",
  "final_judgment": "confirmed",
  "final_confidence": 0.91,
  "ai_trace": {
    "version": "v3",
    "yolo": {
      "violation_type": "no_helmet",
      "confidence": 0.62,
      "detections": [...],
      "duration_ms": 45
    },
    "doubao": {
      "judgment": "confirmed",
      "confidence": 0.88,
      "reasoning": "摩托车驾驶员头部未检测到头盔...",
      "duration_ms": 1200
    },
    "deepseek": {
      "judgment": "confirmed",
      "confidence": 0.91,
      "review_summary": "同意豆包判断，证据充分...",
      "disagreement_flag": false,
      "duration_ms": 1500
    },
    "final": {
      "judgment": "confirmed",
      "confidence": 0.91,
      "method": "deepseek_autonomous",
      "evidence_count": 2
    }
  },
  "evidence": ["头盔未出现在头部区域", "摩托车驾驶员位置明确"],
  "disagreement": false,
  "learning_hint": null
}
```

#### 步骤3：更新 `image_recognizer.py` 集成协作模块

**文件位置**: `e:\output\1\api\image_recognizer.py`

**修改内容**:
1. 导入CloudCollaborator
2. 新增 `analyze_with_collaboration(image_input)` 函数 - 完整的端云协作检测流程
3. 确保 `analyze_with_doubao` 和 `analyze_with_deepseek_judge` 函数正常工作
4. 统一ai_trace v3格式输出

---

### 第二阶段：数据库模型完善（优先级：高）

#### 步骤4：更新数据库模型 `models.py`

**文件位置**: `e:\output\1\api\models.py`

**新增表**:

1. **CollaborationSession** - 端云协作会话表
   - id, session_id, violation_type, local_confidence, final_confidence
   - judgment_result (confirmed/rejected/uncertain)
   - disagreement (bool), resolved (bool), resolver_id
   - ai_trace_json, image_path, created_at, resolved_at

2. **SystemStatistics** - 系统统计表
   - id, stat_date, total_detections, consultations, confirmations
   - disagreements, accuracy_before, accuracy_after
   - saved_cost (估算节省的云端调用费用)

3. **给ViolationEvidence表增加字段**:
   - collaboration_session_id (关联协作会话)
   - ai_trace_version (v2/v3)
   - final_judgment_source (yolo_local/cloud_collab/manual)

#### 步骤5：数据库迁移脚本 `migrate_db.py`

**文件位置**: `e:\output\1\api\migrate_db.py`

- 自动检测现有表结构
- 安全地添加新字段和新表
- 保留现有数据不丢失
- 提供回滚能力

---

### 第三阶段：管理后台前端完善（优先级：高）

#### 步骤6：新增端云协作可视化页面 `AITrace.vue` 增强

**文件位置**: `e:\output\1\web-admin\src\views\AITrace.vue`

**已有页面，需增强**:
1. 增加"协作过程时间线"展示 - 动画展示本地→豆包→DeepSeek的判定过程
2. 增加置信度变化柱状图 - 本地 vs 豆包 vs DeepSeek vs 最终
3. 增加证据链高亮展示 - 云端AI指出的关键证据点
4. 增加分歧案例标记 - 红色高亮显示本地与云端不一致的案例

#### 步骤7：新增协作统计页面 `CollabStats.vue`

**文件位置**: `e:\output\1\web-admin\src\views\CollabStats.vue`

**功能**:
1. 顶部统计卡片：总咨询次数、确认率、分歧率、准确率提升百分比
2. 趋势图：每日咨询量折线图
3. 饼图：各违规类型咨询占比
4. 柱状图：本地准确率 vs 协作后准确率对比
5. 节省费用估算（按云端API调用单价计算）

#### 步骤8：新增分歧审核页面 `DisagreementList.vue`

**文件位置**: `e:\output\1\web-admin\src\views\DisagreementList.vue`

**功能**:
1. 表格展示所有分歧案例
2. 点击查看详情（本地判断 vs 云端判断 + 图片）
3. 人工裁决按钮（支持/驳回/待定）
4. 裁决历史记录

#### 步骤9：更新路由和侧边栏 `router/index.js`

**文件位置**: `e:\output\1\web-admin\src\router\index.js`

新增路由：
- `/collab-stats` → 协作统计
- `/disagreements` → 分歧审核

更新侧边栏菜单结构。

---

### 第四阶段：微信小程序完善（优先级：中高）

#### 步骤10：小程序增加协作信息展示

**文件**: `e:\output\1\wechat-miniprogram\pages\violation-detail\violation-detail.js` 和对应wxml

**修改内容**:
1. 违规详情页增加"AI协作过程"模块
2. 展示本地检测、云端复核、最终裁决三步时间线
3. 展示置信度变化
4. 展示云端AI的分析理由

#### 步骤11：小程序增加"我的申诉"增强

**文件**: `e:\output\1\wechat-miniprogram\pages\my\my.js` 和对应wxml

**修改内容**:
1. 增加申诉进度状态（待审核/审核中/已通过/已驳回）
2. 增加申诉次数统计
3. 优化申诉流程体验

---

### 第五阶段：数字孪生增强（优先级：中）

#### 步骤12：数字孪生增加违规事件动画

**文件位置**: `e:\output\1\digital_twin\static\js\main.js`

**增强功能**:
1. 摄像头检测到违规时，摄像头标记闪烁红色
2. 违规车辆3D标记（红色边框高亮）
3. 违规事件通知弹窗（从右上角滑入）
4. 违规事件时间轴（底部显示最近10条违规）
5. 点击违规事件 → 跳转查看详情

#### 步骤13：数字孪生增加多摄像头支持

**修改**:
1. 在场景中增加3-5个摄像头点位（模拟路口多角度监控）
2. 每个摄像头有独立的状态指示灯（绿色=正常，黄色=咨询中，红色=违规）
3. 摄像头连线展示数据流向（端→云）

---

### 第六阶段：系统全面完善（优先级：中）

#### 步骤14：后端API全面检查和完善

**检查清单**:
1. [ ] 所有API有统一的响应格式（ApiResponse包装）
2. [ ] 所有列表接口支持分页（page, page_size）
3. [ ] 所有列表接口支持筛选和排序
4. [ ] 所有接口有错误处理和日志记录
5. [ ] 健康检查接口 `/health` 返回完整状态
6. [ ] CORS配置正确
7. [ ] 文件上传大小限制合理

#### 步骤15：性能优化

1. **图片压缩**: 上传图片自动压缩到合适尺寸（最大1920px宽）
2. **缓存机制**: 模型加载结果缓存，避免重复加载
3. **异步处理**: 云端协作调用使用异步任务队列（简单版：线程池）
4. **数据库索引**: 为常用查询字段添加索引

#### 步骤16：启动脚本完善

**文件**: `e:\output\1\lan-start.bat`

确保：
- 后端端口8001
- 前端端口5173
- 使用 py -3 启动Python
- 数字孪生服务也能启动

---

### 第七阶段：测试和文档（优先级：中）

#### 步骤17：生成完整测试报告

**文件位置**: `e:\output\1\zhitong\training\reports\task008_test_report.md`

**测试内容**:
1. 端云协作功能测试（urgent/consult/normal三种模式）
2. ai_trace v3格式验证
3. API接口测试（所有新增接口）
4. 数据库迁移测试
5. 前端页面渲染测试
6. 性能测试（单次协作耗时、并发能力）
7. 异常场景测试（云端API超时、网络断开等）

#### 步骤18：生成API文档更新

更新API文档，记录所有新增接口。

---

## 三、验收标准

### 核心功能验收（必须100%通过）

1. **端云协作模块**
   - [ ] CloudCollaborator类正常实例化
   - [ ] 三种触发模式（urgent/consult/normal）工作正常
   - [ ] 云端咨询接口返回正确的ai_trace v3结构
   - [ ] 分歧检测逻辑正确

2. **API接口**
   - [ ] 6个新增API全部可用
   - [ ] 返回格式统一，无报错
   - [ ] 数据库读写正常

3. **数据库**
   - [ ] 新增表创建成功
   - [ ] 数据迁移不丢失现有数据
   - [ ] 关联关系正确

4. **管理后台**
   - [ ] 协作统计页面正常渲染
   - [ ] 分歧审核页面功能完整
   - [ ] AITrace页面增强效果可见

### 系统完善验收（80%以上通过）

5. **微信小程序**
   - [ ] 违规详情展示协作过程
   - [ ] 申诉功能增强可用

6. **数字孪生**
   - [ ] 违规事件动画效果
   - [ ] 多摄像头点位展示

7. **性能优化**
   - [ ] 图片压缩功能正常
   - [ ] 单次协作总耗时 < 3秒（含云端调用）

### 文档验收

8. **测试报告**
   - [ ] 测试用例完整
   - [ ] 测试结果有数据支撑
   - [ ] 问题和改进建议明确

---

## 四、现有资源参考

### 已有文件
- 核心识别：`e:\output\1\api\image_recognizer.py`
- 违规规则：`e:\output\1\api\violation_rules.py`
- 后端主入口：`e:\output\1\api\app.py`
- 数据模型：`e:\output\1\api\models.py`
- 数据库：`e:\output\1\api\database.py`
- 云模块参考：`e:\output\1\zhitong\cloud.py`
- 管理后台：`e:\output\1\web-admin\src\views\`
- 微信小程序：`e:\output\1\wechat-miniprogram\`
- 数字孪生：`e:\output\1\digital_twin\`

### 已有模型
- YOLOv8n: `e:\output\1\zhitong\training\models\yolov8n.pt`
- YOLOv8s: `e:\output\1\zhitong\training\models\yolov8s.pt`
- 其他：helmet.pt, traffic_light.pt, lane.pt（当前为yolov8s fallback）

### API Key
- DashScope（豆包）：从 config_runtime.json 或环境变量获取
- DeepSeek：从配置中获取

---

## 五、注意事项

1. **安全**: 不得在代码中硬编码任何API Key，必须通过配置文件或环境变量读取
2. **兼容性**: 新增功能不得破坏现有API和数据，向前兼容
3. **错误处理**: 云端API调用失败时，必须有优雅降级（返回本地判断结果 + 标记pending_review）
4. **代码风格**: 遵循现有代码风格，使用中文注释
5. **验证**: 每个大步骤完成后，运行相应的验证测试
6. **数据库**: 迁移操作必须可逆，先备份再修改
7. **文件索引（重要）**: 每新增/修改一个重要文件，必须同步更新项目文件索引 `PROJECT_FILE_INDEX.md`，注明文件路径、用途、核心函数/类。验收时将检查索引完整性。

---

## 六、项目文件索引要求

**索引文件位置**: `e:\output\PROJECT_FILE_INDEX.md`

**格式要求**: 按模块分类，每个文件一行，格式如下：
```
### 后端API模块 (api/)
| 文件路径 | 用途 | 核心函数/类 | 状态 |
|---------|------|------------|------|
| api/app.py | FastAPI主入口，路由注册、生命周期管理 | lifespan, app | 已有 |
| api/cloud_collaborator.py | 端云协作管理器 | CloudCollaborator | 新增 |
```

**执行者必须**:
1. 开始任务前，先读取现有索引文件（如不存在则新建）
2. 每完成一个步骤，在索引中更新对应文件的状态
3. 任务完成时，索引必须与实际代码完全一致
4. 索引文件作为验收第一项检查内容

---

## 六、执行顺序建议

```
第1-2小时：  第一阶段（核心协作模块 + API路由）
第2-3小时：  第二阶段（数据库模型 + 迁移脚本）
第3-4小时：  第三阶段（管理后台3个新页面/增强）
第4-5小时：  第四阶段 + 第五阶段（小程序 + 数字孪生）
第5-6小时：  第六阶段（系统完善 + 性能优化）
第6-8小时：  第七阶段（全面测试 + 生成报告）
```

遇到阻塞时，跳过继续下一个大模块，不要卡死在一个地方。

---

**任务签发**: 指挥官
**签发时间**: 2026-07-17
**预期完成**: 次日早晨验收
