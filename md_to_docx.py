# -*- coding: utf-8 -*-
"""
Markdown 转 Word(.docx) 转换脚本 — TASK-031

功能：
  读取 Markdown 文件，按指定样式生成 Word 文档。

支持的 Markdown 元素：
  - # / ## / ### 标题
  - 普通段落（含 **加粗** / `代码` / [链接](url) 内联格式）
  - - 无序列表
  - 1. 有序列表
  - | 表格 |
  - ``` 代码块 ```
  - > 引用
  - --- 水平分隔线

样式规范（通知文件第二章）：
  - H1: 黑体 16pt 加粗 居中，段前 24pt 段后 12pt
  - H2: 黑体 14pt 加粗 左对齐，段前 18pt 段后 6pt
  - H3: 宋体 12pt 加粗 左对齐，段前 12pt 段后 6pt
  - 正文: 宋体 11pt，1.5 倍行距，段前 0pt 段后 6pt
  - 表格: 宋体 10pt，表头加粗居中
  - 代码块: Consolas 9pt，浅灰背景
  - 页面: A4，上下 2.54cm，左右 3.17cm
  - 页眉: 奇数页项目名，偶数页"论文资料包"
  - 页码: 底部居中阿拉伯数字

使用方法：
  py -3 md_to_docx.py <input.md> <output.docx>
  py -3 md_to_docx.py  # 不带参数则转换全部 3 个文件
"""

import os
import re
import sys
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


# ============== 样式常量 ==============
PROJECT_NAME = "智瞳灵声——基于视觉识别与云端推理的智慧交管系统"
FONT_HEI = "黑体"
FONT_SONG = "宋体"
FONT_CODE = "Consolas"


# ============== 辅助函数 ==============
def set_cell_shading(cell, color_hex):
    """设置单元格背景色"""
    shading = OxmlElement('w:shd')
    shading.set(qn('w:fill'), color_hex)
    cell._tc.get_or_add_tcPr().append(shading)


def set_paragraph_shading(paragraph, color_hex):
    """设置段落背景色"""
    pPr = paragraph._p.get_or_add_pPr()
    shading = OxmlElement('w:shd')
    shading.set(qn('w:fill'), color_hex)
    pPr.append(shading)


def set_run_font(run, font_name, size, bold=False, color=None):
    """设置 run 的字体（含中文 eastAsia）"""
    run.font.name = font_name
    run.font.size = Pt(size)
    run.font.bold = bold
    if color:
        run.font.color.rgb = RGBColor(*color)
    # 设置中文字体
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = OxmlElement('w:rFonts')
        rPr.append(rFonts)
    rFonts.set(qn('w:eastAsia'), font_name)
    rFonts.set(qn('w:ascii'), font_name)
    rFonts.set(qn('w:hAnsi'), font_name)


def add_page_number_field(paragraph):
    """在段落中添加页码字段"""
    run = paragraph.add_run()
    fldChar1 = OxmlElement('w:fldChar')
    fldChar1.set(qn('w:fldCharType'), 'begin')
    run._r.append(fldChar1)

    run2 = paragraph.add_run()
    instrText = OxmlElement('w:instrText')
    instrText.set(qn('xml:space'), 'preserve')
    instrText.text = 'PAGE'
    run2._r.append(instrText)

    run3 = paragraph.add_run()
    fldChar2 = OxmlElement('w:fldChar')
    fldChar2.set(qn('w:fldCharType'), 'end')
    run3._r.append(fldChar2)


def add_different_first_page_header_footer(doc):
    """设置奇偶页不同的页眉页脚"""
    sect = doc.sections[0]
    # 启用奇偶页不同
    sect.different_first_page_header_footer = False
    # 通过设置 evenAndOddHeaders 启用奇偶页不同
    settings = doc.settings.element
    even_odd = settings.find(qn('w:evenAndOddHeaders'))
    if even_odd is None:
        even_odd = OxmlElement('w:evenAndOddHeaders')
        settings.append(even_odd)


def setup_page(doc):
    """页面设置：A4 + 页边距"""
    sect = doc.sections[0]
    sect.page_width = Cm(21.0)
    sect.page_height = Cm(29.7)
    sect.top_margin = Cm(2.54)
    sect.bottom_margin = Cm(2.54)
    sect.left_margin = Cm(3.17)
    sect.right_margin = Cm(3.17)


def setup_headers_footers(doc):
    """页眉页脚设置：奇偶页不同 + 页码"""
    sect = doc.sections[0]
    # 启用奇偶页不同
    settings = doc.settings.element
    even_odd = settings.find(qn('w:evenAndOddHeaders'))
    if even_odd is None:
        even_odd = OxmlElement('w:evenAndOddHeaders')
        settings.append(even_odd)

    # 奇数页页眉（default header）
    header = sect.header
    header.is_linked_to_previous = False
    if header.paragraphs:
        hp = header.paragraphs[0]
    else:
        hp = header.add_paragraph()
    hp.text = ""
    run = hp.add_run(PROJECT_NAME)
    set_run_font(run, FONT_SONG, 9, color=(128, 128, 128))
    hp.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # 偶数页页眉
    even_header = sect.even_page_header
    even_header.is_linked_to_previous = False
    if even_header.paragraphs:
        ep = even_header.paragraphs[0]
    else:
        ep = even_header.add_paragraph()
    ep.text = ""
    run = ep.add_run("论文资料包")
    set_run_font(run, FONT_SONG, 9, color=(128, 128, 128))
    ep.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # 页脚（页码）- 奇数页
    footer = sect.footer
    footer.is_linked_to_previous = False
    if footer.paragraphs:
        fp = footer.paragraphs[0]
    else:
        fp = footer.add_paragraph()
    fp.text = ""
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_page_number_field(fp)

    # 页脚（页码）- 偶数页
    even_footer = sect.even_page_footer
    even_footer.is_linked_to_previous = False
    if even_footer.paragraphs:
        efp = even_footer.paragraphs[0]
    else:
        efp = even_footer.add_paragraph()
    efp.text = ""
    efp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_page_number_field(efp)


# ============== 内联格式解析 ==============
def add_inline_runs(paragraph, text):
    """解析内联格式（**加粗** / `代码` / [链接](url)）并添加到段落"""
    # 正则：匹配 **bold** | `code` | [text](url)
    pattern = re.compile(
        r'(\*\*[^*]+\*\*)'   # **bold**
        r'|(`[^`]+`)'        # `code`
        r'|(\[[^\]]+\]\([^)]+\))'  # [text](url)
    )
    pos = 0
    for m in pattern.finditer(text):
        # 添加匹配前的普通文本
        if m.start() > pos:
            plain = text[pos:m.start()]
            if plain:
                run = paragraph.add_run(plain)
                set_run_font(run, FONT_SONG, 11)

        token = m.group()
        if token.startswith('**') and token.endswith('**'):
            # 加粗
            content = token[2:-2]
            run = paragraph.add_run(content)
            set_run_font(run, FONT_SONG, 11, bold=True)
        elif token.startswith('`') and token.endswith('`'):
            # 行内代码
            content = token[1:-1]
            run = paragraph.add_run(content)
            set_run_font(run, FONT_CODE, 10)
        elif token.startswith('['):
            # 链接 [text](url)
            link_m = re.match(r'\[([^\]]+)\]\(([^)]+)\)', token)
            if link_m:
                link_text = link_m.group(1)
                url = link_m.group(2)
                run = paragraph.add_run(link_text)
                set_run_font(run, FONT_SONG, 11, color=(0, 0, 255))
                run.font.underline = True
        pos = m.end()

    # 添加剩余文本
    if pos < len(text):
        remaining = text[pos:]
        if remaining:
            run = paragraph.add_run(remaining)
            set_run_font(run, FONT_SONG, 11)


# ============== Markdown 行类型判断 ==============
def is_heading(line):
    """判断是否为标题行，返回 (level, text) 或 None"""
    m = re.match(r'^(#{1,4})\s+(.*)', line)
    if m:
        return len(m.group(1)), m.group(2).strip()
    return None


def is_table_row(line):
    """判断是否为表格行"""
    return line.strip().startswith('|') and line.strip().endswith('|')


def is_table_separator(line):
    """判断是否为表格分隔行 |---|---|"""
    stripped = line.strip()
    if not stripped.startswith('|'):
        return False
    # 去掉首尾 | 后检查是否全是 - 或 : 或空格
    inner = stripped[1:-1] if stripped.endswith('|') else stripped[1:]
    return bool(re.match(r'^[\s:|-]+$', inner)) and '-' in inner


def is_bullet_list(line):
    """判断是否为无序列表项"""
    return bool(re.match(r'^\s*[-*]\s+', line))


def is_numbered_list(line):
    """判断是否为有序列表项"""
    return bool(re.match(r'^\s*\d+\.\s+', line))


def is_blockquote(line):
    """判断是否为引用"""
    return line.strip().startswith('>')


def is_hr(line):
    """判断是否为水平分隔线"""
    stripped = line.strip()
    return stripped == '---' or stripped == '***' or stripped == '___'


def parse_table_row(line):
    """解析表格行为单元格列表"""
    stripped = line.strip()
    # 去掉首尾 |
    if stripped.startswith('|'):
        stripped = stripped[1:]
    if stripped.endswith('|'):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split('|')]


# ============== 主转换函数 ==============
def md_to_docx(md_path, docx_path):
    """将 Markdown 文件转换为 Word 文档"""
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.read().split('\n')

    doc = Document()

    # 页面设置
    setup_page(doc)

    # 页眉页脚
    setup_headers_footers(doc)

    # 设置 Normal 样式默认字体
    style = doc.styles['Normal']
    style.font.name = FONT_SONG
    style.font.size = Pt(11)
    style.element.rPr.rFonts.set(qn('w:eastAsia'), FONT_SONG)

    i = 0
    while i < len(lines):
        line = lines[i]

        # 空行
        if not line.strip():
            i += 1
            continue

        # 代码块
        if line.strip().startswith('```'):
            i += 1
            code_lines = []
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1
            # 跳过结束的 ```
            i += 1
            # 添加代码段落到文档
            code_text = '\n'.join(code_lines)
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.line_spacing = 1.0
            run = p.add_run(code_text)
            set_run_font(run, FONT_CODE, 9)
            # 浅灰背景
            set_paragraph_shading(p, 'F2F2F2')
            continue

        # 标题
        heading = is_heading(line)
        if heading:
            level, text = heading
            p = doc.add_paragraph()
            if level == 1:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_before = Pt(24)
                p.paragraph_format.space_after = Pt(12)
                run = p.add_run(text)
                set_run_font(run, FONT_HEI, 16, bold=True)
            elif level == 2:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p.paragraph_format.space_before = Pt(18)
                p.paragraph_format.space_after = Pt(6)
                run = p.add_run(text)
                set_run_font(run, FONT_HEI, 14, bold=True)
            elif level == 3:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p.paragraph_format.space_before = Pt(12)
                p.paragraph_format.space_after = Pt(6)
                run = p.add_run(text)
                set_run_font(run, FONT_SONG, 12, bold=True)
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                run = p.add_run(text)
                set_run_font(run, FONT_SONG, 11, bold=True)
            i += 1
            continue

        # 表格
        if is_table_row(line):
            table_lines = []
            while i < len(lines) and is_table_row(lines[i]):
                table_lines.append(lines[i])
                i += 1
            # 解析表格
            rows_data = []
            separator_idx = -1
            for idx, tl in enumerate(table_lines):
                if is_table_separator(tl):
                    separator_idx = idx
                    continue
                rows_data.append(parse_table_row(tl))
            if rows_data:
                num_cols = max(len(r) for r in rows_data)
                table = doc.add_table(rows=len(rows_data), cols=num_cols)
                table.alignment = WD_TABLE_ALIGNMENT.CENTER
                table.style = 'Table Grid'
                for r_idx, row_cells in enumerate(rows_data):
                    for c_idx, cell_text in enumerate(row_cells):
                        if c_idx < num_cols:
                            cell = table.cell(r_idx, c_idx)
                            cell.text = ""
                            p = cell.paragraphs[0]
                            p.paragraph_format.space_before = Pt(0)
                            p.paragraph_format.space_after = Pt(0)
                            # 表头（第一行）加粗居中
                            is_header = (r_idx == 0 and separator_idx > 0)
                            add_inline_runs(p, cell_text)
                            for run in p.runs:
                                set_run_font(run, FONT_SONG, 10, bold=is_header)
                            if is_header:
                                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                                set_cell_shading(cell, 'D9E2F3')
                            else:
                                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            continue

        # 无序列表
        if is_bullet_list(line):
            text = re.sub(r'^\s*[-*]\s+', '', line)
            p = doc.add_paragraph(style='List Bullet')
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.line_spacing = 1.5
            add_inline_runs(p, text)
            i += 1
            continue

        # 有序列表
        if is_numbered_list(line):
            text = re.sub(r'^\s*\d+\.\s+', '', line)
            p = doc.add_paragraph(style='List Number')
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.line_spacing = 1.5
            add_inline_runs(p, text)
            i += 1
            continue

        # 引用
        if is_blockquote(line):
            text = re.sub(r'^\s*>\s?', '', line)
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(1)
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.line_spacing = 1.5
            add_inline_runs(p, text)
            for run in p.runs:
                run.font.italic = True
            i += 1
            continue

        # 水平分隔线
        if is_hr(line):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run('─' * 40)
            set_run_font(run, FONT_SONG, 10, color=(180, 180, 180))
            i += 1
            continue

        # 普通段落
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.line_spacing = 1.5
        add_inline_runs(p, line.strip())
        i += 1

    # 保存
    doc.save(docx_path)
    return docx_path


# ============== 主入口 ==============
def main():
    """主入口：不带参数则转换全部 3 个文件"""
    conversions = [
        (r"e:\output\PAPER_MATERIAL_PACK.md", r"e:\output\智瞳灵声_论文资料包.docx"),
        (r"e:\output\PAPER_FIGURES_DESCRIPTION.md", r"e:\output\智瞳灵声_论文图表描述.docx"),
        (r"e:\output\PAPER_REFERENCES_SUGGESTION.md", r"e:\output\智瞳灵声_参考文献建议.docx"),
    ]

    if len(sys.argv) == 3:
        conversions = [(sys.argv[1], sys.argv[2])]

    for md_path, docx_path in conversions:
        print(f"转换中: {md_path} → {docx_path}")
        try:
            md_to_docx(md_path, docx_path)
            size_kb = os.path.getsize(docx_path) / 1024
            print(f"  完成: {size_kb:.1f} KB")
        except Exception as e:
            print(f"  失败: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    main()
