# 任务通知单 · TASK-001

**指挥官**：2026-06-17
**执行者**：IDE / 子代理
**工作目录**：e:\output\

---

## 任务描述

对智瞳灵声项目进行完整健康检查，建立运行基线，产出结构化报告。

---

## 执行步骤

### 步骤 1：后端健康检查
- 切换到目录 `e:\output\1\api\`
- 执行：`py -3 -c "import sys; sys.path.insert(0, '.'); from image_recognizer import analyze_image; print('image_recognizer OK')"`
- 执行：`py -3 -c "import fastapi, uvicorn, sqlalchemy; print('deps OK')"`
- 启动后端：`py -3 app.py`（后台运行，超时 30 秒后检查端口 8001 是否监听）
- 若启动成功：执行 `curl.exe -s http://127.0.0.1:8001/health`

### 步骤 2：前端健康检查
- 切换到目录 `e:\output\1\web-admin\`
- 检查 node_modules 是否存在，若不存在执行：`npm install`
- 执行构建验证：`npx vite build --mode development`（允许警告但不能有 ERROR）

### 步骤 3：数据库健康检查
- 检查文件是否存在：`e:\output\1\api\zhitong_violations.db`
- 执行：`py -3 -c "import sqlite3; conn = sqlite3.connect('zhitong_violations.db'); cur = conn.cursor(); cur.execute(\"SELECT name FROM sqlite_master WHERE type='table'\"); print([r[0] for r in cur.fetchall()]); conn.close()"`

### 步骤 4：核心模块导入检查
- 执行：`py -3 -c "from image_recognizer import detect_with_yolo, analyze_with_doubao, analyze_with_deepseek_judge; print('ALL_MODULES_OK')"`

---

## 验收标准

- [ ] 后端依赖全部导入成功（无 ModuleNotFoundError）
- [ ] 前端 Vite 构建无 ERROR（允许警告）
- [ ] 数据库文件存在且包含表（violation_evidence 等）
- [ ] image_recognizer 四个核心函数均可正常 import

---

## 输出要求

**成功时**：写入 `e:\output\_TASK-001_OUTPUT.json`，包含：
```json
{
  "task": "TASK-001_项目健康检查",
  "timestamp": "ISO8601时间戳",
  "backend": { "import_ok": true/false, "port_8001": true/false, "health_check": "..." },
  "frontend": { "build_ok": true/false, "warnings": [] },
  "database": { "exists": true/false, "tables": [] },
  "modules": { "all_import_ok": true/false },
  "overall_status": "PASS" | "PARTIAL" | "FAIL",
  "details": {}
}
```

**失败时**：写入 `e:\output\_TASK-001_ERROR.json`，包含：
```json
{
  "task": "TASK-001",
  "failed_at": "失败步骤名称",
  "error_text": "完整原始错误信息",
  "recommendation": "下一步建议"
}
```

---

## 风险提示

1. **YOLO 模型首次加载慢**：预计 30-60 秒，超时则标记为超时而非失败
2. **端口 8001 已被占用**：检查 `netstat -ano | findstr 8001`，若有进程则记录 PID
3. **node_modules 缺失**：首次 npm install 可能需要 2-5 分钟，耐心等待

---

*本通知由指挥官建立 · 执行完成后报告结果文件路径*
