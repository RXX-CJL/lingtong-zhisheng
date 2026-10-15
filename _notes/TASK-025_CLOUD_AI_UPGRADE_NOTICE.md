# TASK-025 云端AI升级与模型更换

> **指挥官交接说明**：TASK-024 的 M3（Claude 3.5 Sonnet 添加）未执行，需在此任务中完成。当前云端 AI 架构为豆包+DeepSeek，豆包误判率较高，需要用更强的 Claude 3.5 Sonnet 替换或增强。借鉴 Vibe Coding 理念：优先验证效果，其次审查代码。

---

## 0. 协作规则

1. **Git 优先复用**：先搜 GitHub
2. **禁止降级方案**：必须用更强的 AI 模型
3. **真实浏览器验证**：前端修改需在用户真实 Edge 浏览器验证
4. **自主决策权**：用户已休息，无需请示
5. **VPN 已开启**
6. **项目根目录**：`e:\output\1`
7. **结果输出**：`_TASK-025_OUTPUT.json` / `_TASK-025_ERROR.json` 到 `e:\output\`
8. **能力优先使用规则（强制）**：执行任何任务前，必须对照 `project_memory.md` 中的"工作流能力优先级"清单，按优先级从高到低选择工具。禁止因习惯跳过高优先级工具。高优先级工具不可用时，必须通知指挥官说明情况，获得允许后才能降级。例如：
   - 搜资料：优先 GitHub Skill → SearchCodebase → WebSearch（降级需报备）
   - 写代码：有对应 Skill 必须用（shadcn、frontend-design 等）
   - 测试：优先 test-driven-development / systematic-debugging Skill
   - 调试：优先 Chrome DevTools MCP
   - 文档：优先 doc-coauthoring / report-page Skill

---

## 1. 背景

当前云端 AI 架构（豆包视觉 + DeepSeek 裁决）存在以下问题：
- 豆包在交通违规识别上误判率较高
- 需要更强的视觉理解能力来识别复杂违规场景（逆行、压线等）
- 双模型协作时延较高

**目标**：添加 Claude 3.5 Sonnet 作为核心视觉分析模型，提升识别准确性。

---

## 2. 任务清单

### M1: 添加 Claude API 配置
- **优先级**：高
- **操作步骤**：
  1. 读 `e:\output\1\api\config.py`
  2. 添加 `CLAUDE_API_KEY` 和 `CLAUDE_API_URL` 配置项
  3. 读 `e:\output\1\api\config_runtime.json`（如果存在），确保配置兼容
- **必须 MCP/Skill**：Read + Edit
- **验收标准**：config.py 已添加 Claude API 相关配置

### M2: 创建 Claude 分析模块
- **优先级**：高
- **操作步骤**：
  1. 读 `e:\output\1\api\image_recognizer.py`，了解 `analyze_with_doubao` 和 `analyze_with_deepseek_judge` 的接口格式
  2. 创建 `analyze_with_claude` 函数：
     - 使用 Anthropic Claude 3.5 Sonnet API（claude-3-5-sonnet-20241022）
     - 支持图片输入（base64）
     - 返回格式与现有函数一致（is_violation_confirmed, confidence_adjusted, result_text）
     - 包含详细的违规场景提示词（逆行、未戴头盔、闯红灯、违规停车）
  3. 参考 `analyze_with_doubao` 的实现
- **必须 MCP/Skill**：Read + Edit + WebSearch（查 Anthropic API 最新用法）
- **验收标准**：`analyze_with_claude` 函数已创建，接口格式与现有函数一致

### M3: 修改云端协作逻辑
- **优先级**：高
- **操作步骤**：
  1. 读 `e:\output\1\api\cloud_collaborator.py`
  2. 在 `consult_cloud` 和 `consult_cloud_dual` 方法中，将豆包替换为 Claude，或添加 Claude 作为优先裁决者
  3. 更新 `build_ai_trace` 和 `build_ai_trace_v31` 方法，支持 Claude 结果
  4. 修改 `process_cloud_response` 方法，支持 Claude 作为主裁决者
  5. 确保现有代码兼容（不破坏豆包/DeepSeek 的调用）
- **必须 MCP/Skill**：Read + Edit
- **验收标准**：cloud_collaborator.py 已支持 Claude 调用，AI 追踪结构包含 claude 字段

### M4: 更新 Settings 页面
- **优先级**：中
- **操作步骤**：
  1. 读 `e:\output\1\web-admin\src\views\Settings.vue`
  2. 添加 Claude API Key 输入框（与智谱/DeepSeek/Qwen 并列）
  3. 添加测试连接功能
- **必须 MCP/Skill**：Read + Edit
- **验收标准**：Settings 页面已添加 Claude API Key 输入框

### M5: 测试验证
- **优先级**：高
- **操作步骤**：
  1. 写一个测试脚本测试 Claude 分析效果
  2. 用测试图片验证违规识别准确性
  3. 对比 Claude 与豆包的识别效果
- **必须 MCP/Skill**：Write + RunCommand + WebSearch
- **验收标准**：测试脚本能成功调用 Claude API，识别结果准确

---

## 3. 统一要求

1. **每个子任务完成**：
   - 写 `_TASK-025-MXX_OUTPUT.json` 或 `_TASK-025-MXX_ERROR.json`
   - OUTPUT 必须包含：task, timestamp, status, details, deviations
   - ERROR 必须包含：task, failed_at, error_text（完整 stack trace）, recommendation

2. **任务顺序**：M1 → M2 → M3 → M4 → M5

3. **高危操作**：默认同意，无需请示

4. **报告指挥官**：每个子任务完成后报告 OUTPUT 文件路径 + 状态

5. **任务后清理**：执行完所有任务后，清理临时文件、测试文件、日志文件等非必要文件，保持项目整洁

---

## 4. 验收标准

- [ ] M1 Claude API 配置项已添加到 config.py
- [ ] M2 `analyze_with_claude` 函数已创建，接口格式与现有函数一致
- [ ] M3 cloud_collaborator.py 已支持 Claude 调用，AI 追踪结构完整
- [ ] M4 Settings 页面已添加 Claude API Key 输入框
- [ ] M5 测试脚本能成功调用 Claude API，识别结果准确
- [ ] 所有 OUTPUT/ERROR 文件已写入
- [ ] 临时文件已清理

---

## 5. 关键文件路径

- 项目根：`e:\output\1`
- 配置文件：`e:\output\1\api\config.py`
- 图像识别模块：`e:\output\1\api\image_recognizer.py`
- 云端协作模块：`e:\output\1\api\cloud_collaborator.py`
- 前端设置页面：`e:\output\1\web-admin\src\views\Settings.vue`
- 截图目录：`e:\output\screenshots\`

---

**任务通知版本**：v1.0
**生成时间**：2026-07-24
**指挥官**：TRAE Assistant
**执行者**：TRAE Sub-agent
**用户状态**：已休息，全权委托执行者自主决策