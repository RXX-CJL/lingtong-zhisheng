# TASK-031: 论文资料包修正与 Word 导出

> **任务级别**: 文档修正 + 格式转换任务
> **前置任务**: TASK-030（已完成，生成 3 个 Markdown 文件）
> **核心目标**: 修正项目名称 + 优化内容 + 转为 Word(.docx) 格式方便传输

---

## 一、修正要求

### 1. 项目名称修正

TASK-030 生成的文档中项目名称有误，需全部替换：

- **错误名称**: "智瞳灵声——基于端云协同的智慧交通视觉感知与违法事件闭环系统"
- **正确名称**: "智瞳灵声——基于视觉识别与云端推理的智慧交管系统"

需在以下 3 个文件中全文搜索替换：
- `e:\output\PAPER_MATERIAL_PACK.md`
- `e:\output\PAPER_FIGURES_DESCRIPTION.md`
- `e:\output\PAPER_REFERENCES_SUGGESTION.md`

注意：可能出现多种变体写法，需全部替换：
- "智瞳灵声——基于端云协同的智慧交通视觉感知与违法事件闭环系统"
- "智瞳灵声—基于端云协同的智慧交通视觉感知与违法事件闭环系统"
- "智瞳灵声-基于端云协同的智慧交通视觉感知与违法事件闭环系统"
- "智瞳灵声" 单独出现时保留不变

统一替换为：**智瞳灵声——基于视觉识别与云端推理的智慧交管系统**

### 2. 内容优化

读取 3 个 Markdown 文件后，检查并优化以下内容：

- 检查全文是否有"灵声"误写为"灵瞳智声"或"智瞳灵声"等顺序错误，统一为"智瞳灵声"
- 检查是否有"交管"误写为"交通管理"（两者均可，但标题用"交管"）
- 检查章节编号连续性
- 检查表格格式对齐
- 检查代码路径引用准确性（如 `api/xxx.py` 格式统一）
- 移除任何残留的口语化表达

---

## 二、Word 导出要求

### 导出 3 个 Word 文件

| 源文件 | Word 输出路径 |
|--------|--------------|
| `e:\output\PAPER_MATERIAL_PACK.md` | `e:\output\智瞳灵声_论文资料包.docx` |
| `e:\output\PAPER_FIGURES_DESCRIPTION.md` | `e:\output\智瞳灵声_论文图表描述.docx` |
| `e:\output\PAPER_REFERENCES_SUGGESTION.md` | `e:\output\智瞳灵声_参考文献建议.docx` |

### Word 格式要求

1. **标题样式**：
   - 一级标题（`#`）：黑体 16pt 加粗，居中，段前 24pt 段后 12pt
   - 二级标题（`##`）：黑体 14pt 加粗，左对齐，段前 18pt 段后 6pt
   - 三级标题（`###`）：宋体 12pt 加粗，左对齐，段前 12pt 段后 6pt
2. **正文**：宋体 11pt（小四），行距 1.5 倍，段前 0pt 段后 6pt
3. **表格**：宋体 10pt，表头加粗居中，单元格内左对齐
4. **代码块**：等宽字体（Consolas）9pt，浅灰背景
5. **页面设置**：A4，上下页边距 2.54cm，左右页边距 3.17cm
6. **页眉**：奇偶页不同，奇数页"智瞳灵声——基于视觉识别与云端推理的智慧交管系统"，偶数页"论文资料包"
7. **页码**：底部居中，阿拉伯数字

### 技术方案

使用 `python-docx` 库生成 Word 文件。

```python
# 推荐方案：python-docx
from docx import Document
from docx.shared import Pt, Cm, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

# 如果 python-docx 未安装，执行：
# pip install python-docx
```

如果 `python-docx` 未安装，**自动安装**（`pip install python-docx`），不得因依赖缺失停下。

### Markdown → Word 转换规则

| Markdown 元素 | Word 处理 |
|---------------|----------|
| `# 标题` | Heading 1 样式 |
| `## 标题` | Heading 2 样式 |
| `### 标题` | Heading 3 样式 |
| 普通段落 | Normal 样式 |
| `- 列表项` | List Bullet 样式 |
| `1. 有序列表` | List Number 样式 |
| `\| 表格 \|` | Word Table |
| `` `代码` `` | 等宽字体段落 |
| `**加粗**` | run.bold = True |
| `[链接](url)` | 超链接（文字 + URL） |
| `> 引用` | 缩进段落，斜体 |

---

## 三、执行步骤

1. 读取 3 个 Markdown 文件
2. 全文替换项目名称（错误→正确）
3. 检查并修正其他名称/格式问题
4. 保存修正后的 Markdown（覆盖原文件）
5. 安装 python-docx（如未安装）
6. 编写转换脚本 `e:\output\md_to_docx.py`
7. 执行转换，生成 3 个 .docx 文件
8. 验证 Word 文件可正常打开（检查文件大小 > 0 + 用 python-docx 读取验证段落数）

---

## 四、验收标准

- [ ] 3 个 Markdown 文件中项目名称全部修正为"智瞳灵声——基于视觉识别与云端推理的智慧交管系统"
- [ ] 无"灵瞳智声"等顺序错误的写法
- [ ] 3 个 .docx 文件生成成功，文件大小 > 0
- [ ] Word 文件可用 python-docx 读取（段落数 > 100）
- [ ] Word 标题样式正确（Heading 1/2/3）
- [ ] Word 表格正确渲染
- [ ] Word 代码块用等宽字体
- [ ] 转换脚本 `md_to_docx.py` 保留（方便后续重新生成）
- [ ] Python AST 语法验证通过

---

## 五、文件索引

### 新建文件
| 文件 | 说明 |
|------|------|
| `e:\output\智瞳灵声_论文资料包.docx` | 主文档 Word 版 |
| `e:\output\智瞳灵声_论文图表描述.docx` | 图表描述 Word 版 |
| `e:\output\智瞳灵声_参考文献建议.docx` | 参考文献 Word 版 |
| `e:\output\md_to_docx.py` | Markdown 转 Word 转换脚本 |

### 修改文件
| 文件 | 修改内容 |
|------|---------|
| `e:\output\PAPER_MATERIAL_PACK.md` | 项目名称修正 |
| `e:\output\PAPER_FIGURES_DESCRIPTION.md` | 项目名称修正 |
| `e:\output\PAPER_REFERENCES_SUGGESTION.md` | 项目名称修正 |

---

## 六、OUTPUT 文件

完成后生成：`e:\output\_TASK-031_OUTPUT.json`

```json
{
  "task": "TASK-031",
  "task_name": "论文资料包修正与 Word 导出",
  "timestamp": "ISO8601",
  "status": "PASS/FAIL",
  "details": {
    "name_corrections": "替换次数",
    "docx_files_generated": 3,
    "docx_sizes": {"文件名": "大小KB"},
    "paragraph_counts": {"文件名": "段落数"},
    "heading_styles": "PASS/FAIL",
    "tables_rendered": "PASS/FAIL",
    "script_saved": true
  },
  "feedback": {
    "project_suggestions": [],
    "commander_suggestions": [],
    "dissent": [],
    "suggestions_adopted": []
  }
}
```

---

*本任务修正项目名称并转为 Word 格式，方便真人团队成员传输和使用。*
