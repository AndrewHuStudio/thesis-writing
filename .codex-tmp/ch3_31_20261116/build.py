"""从用户参考文档的样式与案例图表构建独立替换节稿。"""
from pathlib import Path
from copy import deepcopy
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import content as C

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[1]
SOURCE = WORKSPACE/'w-论文正文/261025 第三章 .docx'
OUT = WORKSPACE/'w-论文正文/GCN_train/09_第三章章名及3.1医院首层_修订稿.docx'
D = Document(SOURCE)
CASE_XML = deepcopy(next(t._tbl for t in D.tables if len(t.rows) == 7
                        and '组织模式' in t.cell(0, 0).text))
SECT = deepcopy(D.sections[-1]._sectPr)
for child in list(D._element.body):
    D._element.body.remove(child)
for tag in ['headerReference', 'footerReference', 'pgNumType', 'titlePg']:
    for e in list(SECT.findall(qn('w:'+tag))):
        SECT.remove(e)
D._element.body.append(SECT)


def font(r, size=12, bold=False, east='宋体'):
    r.font.name = 'Times New Roman'
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = RGBColor(0, 0, 0)
    r._r.get_or_add_rPr().rFonts.set(qn('w:eastAsia'), east)


def no_numbering(p):
    ppr = p._p.get_or_add_pPr()
    for el in list(ppr.findall(qn('w:numPr'))):
        ppr.remove(el)
    np = OxmlElement('w:numPr')
    ni = OxmlElement('w:numId')
    ni.set(qn('w:val'), '0')
    np.append(ni)
    ppr.append(np)


def para(text, lead='', size=12):
    p = D.add_paragraph(style='Normal')
    pf = p.paragraph_format
    pf.first_line_indent = Pt(24)
    pf.line_spacing = Pt(23)
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.widow_control = True
    pf.keep_with_next = False
    if lead:
        font(p.add_run(lead+' '), size, True)
    font(p.add_run(text), size)
    return p


def heading(text, level):
    p = D.add_paragraph(style=f'Heading {level}')
    no_numbering(p)
    pf = p.paragraph_format
    pf.page_break_before = False
    pf.first_line_indent = Pt(0)
    pf.keep_with_next = True
    pf.line_spacing = Pt(25)
    pf.space_before = Pt(12 if level != 1 else 0)
    pf.space_after = Pt(8)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if level == 1 else WD_ALIGN_PARAGRAPH.LEFT
    font(p.add_run(text), {1:16, 2:15, 3:14}[level],
         level != 3, '黑体' if level < 3 else '宋体')
    return p


def caption(text):
    p = D.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf = p.paragraph_format
    pf.first_line_indent = Pt(0)
    pf.line_spacing = Pt(15)
    pf.space_before = Pt(4)
    pf.space_after = Pt(5)
    font(p.add_run(text), 10.5)
    return p


def picture(stem, cap):
    p = D.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf = p.paragraph_format
    pf.first_line_indent = Pt(0)
    pf.space_before = Pt(5)
    pf.space_after = Pt(0)
    pf.line_spacing = 1
    pf.keep_with_next = True
    p.add_run().add_picture(str(ROOT/f'{stem}.png'), width=Cm(14.64))
    caption(cap)


def table_style(t, widths, size=10.5):
    t.autofit = False
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    pr = t._tbl.tblPr
    bd = pr.find(qn('w:tblBorders'))
    if bd is not None:
        pr.remove(bd)
    bd = OxmlElement('w:tblBorders')
    for side in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']:
        e = OxmlElement('w:'+side)
        e.set(qn('w:val'), 'single')
        e.set(qn('w:sz'), '4')
        e.set(qn('w:color'), '808080')
        bd.append(e)
    pr.append(bd)
    for i, w in enumerate(widths):
        t.columns[i].width = Cm(w)
    for ri, row in enumerate(t.rows):
        row.height = None
        trpr = row._tr.get_or_add_trPr()
        for e in list(trpr.findall(qn('w:trHeight'))):
            trpr.remove(e)
        cs = OxmlElement('w:cantSplit')
        trpr.append(cs)
        if ri == 0:
            repeat = OxmlElement('w:tblHeader')
            trpr.append(repeat)
        for ci, cell in enumerate(row.cells):
            cell.width = Cm(widths[ci])
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            tcpr = cell._tc.get_or_add_tcPr()
            margins = OxmlElement('w:tcMar')
            for side, val in [('top', '85'), ('bottom', '85'), ('left', '90'), ('right', '90')]:
                e = OxmlElement('w:'+side)
                e.set(qn('w:w'), val)
                e.set(qn('w:type'), 'dxa')
                margins.append(e)
            tcpr.append(margins)
            if ri == 0:
                shd = OxmlElement('w:shd')
                shd.set(qn('w:fill'), 'F0F0F0')
                tcpr.append(shd)
            for p in cell.paragraphs:
                no_numbering(p)
                pf = p.paragraph_format
                pf.first_line_indent = Pt(0)
                pf.line_spacing = Pt(15)
                pf.space_before = Pt(1)
                pf.space_after = Pt(1)
                pf.keep_with_next = False
                pf.keep_together = False
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if ci == 0 or ri == 0 else WD_ALIGN_PARAGRAPH.LEFT
                for r in p.runs:
                    font(r, size, ri == 0)


def matrix(rows, widths, cap):
    cp = caption(cap)
    cp.paragraph_format.keep_with_next = True
    t = D.add_table(rows=0, cols=len(widths))
    for record in rows:
        cells = t.add_row().cells
        for cell, text in zip(cells, record):
            cell.text = text
    table_style(t, widths)
    if len(t.rows) > 3:
        for cell in t.rows[-2].cells:
            for p in cell.paragraphs:
                p.paragraph_format.keep_with_next = True
    return t


def prose(items):
    for item in items:
        if isinstance(item, tuple):
            lead, text = item
            para(text, lead)
        else:
            para(item)


def cases():
    p = caption('表3-1 医院首层公共交通组织模式及案例分析')
    p.paragraph_format.keep_with_next = True
    D._element.body.insert(len(D._element.body)-1, deepcopy(CASE_XML))
    t = D.tables[-1]
    t.cell(0, 3).text = '案例图例'
    descriptions = [
        '以公共大厅为枢纽，功能区域围绕大厅或通过短走廊连接',
        '主走廊与次级通道结合，形成主次分明的交通网络',
        '以医疗街串联功能区域，结合中庭、候诊与公共服务',
        '围绕庭院或中庭配置功能区域，通过环廊建立联系',
        '各功能区域紧凑组合，通过内部交通网络连接',
        '功能组团相对独立，由公共交通系统连接',
    ]
    for r, text in zip(t.rows[1:], descriptions):
        r.cells[2].text = text
    table_style(t, [1.9, 3.4, 4.0, 5.34], 10)
    for row in t.rows[1:]:
        for ci in [1, 3]:
            for p in row.cells[ci].paragraphs:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                if p._p.xpath('.//a:blip'):
                    p.paragraph_format.line_spacing = 1
    for p in t.rows[-1].cells[3].paragraphs:
        if '南通市' in p.text:
            for node in p._p.xpath('.//w:t'):
                node.text = ''
            r = p.add_run('南通市第一人民医院新院\n门诊首层')
            font(r, 10)
    for cell in t.rows[-2].cells:
        for p in cell.paragraphs:
            p.paragraph_format.keep_with_next = True
    note = para('注：部分图例为门诊首层案例，用于说明公共交通与功能区域的组合，案例名称保留其使用范围。', size=10)
    note.paragraph_format.first_line_indent = Pt(0)
    note.paragraph_format.line_spacing = Pt(15)


sec = D.sections[0]
sec.page_width, sec.page_height = Cm(21), Cm(29.7)
sec.top_margin = sec.bottom_margin = Cm(2.54)
sec.left_margin = sec.right_margin = Cm(3.17)
sec.header_distance, sec.footer_distance = Cm(1.5), Cm(1.5)
header = sec.header.paragraphs[0]
header.text = '第三章 基于图卷积网络的医院首层空间关系预测'
header.alignment = WD_ALIGN_PARAGRAPH.CENTER
header.paragraph_format.line_spacing = Pt(13)
header.paragraph_format.first_line_indent = Pt(0)
for r in header.runs:
    font(r, 9)
footer = sec.footer.paragraphs[0]
footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
footer.paragraph_format.first_line_indent = Pt(0)
r = footer.add_run()
fld = OxmlElement('w:fldSimple')
fld.set(qn('w:instr'), 'PAGE')
r._r.addnext(fld)

heading(C.CHAPTER, 1)
heading(C.SECTION, 2)
prose(C.INTRO)
heading(C.SUB1, 3)
prose(C.CLASS_INTRO)
picture('fig3-1', '图3-1 医院首层功能空间分类及构成')
prose(C.CLASS_BODY)
heading(C.SUB2, 3)
prose(C.MODE_INTRO)
cases()
prose(C.MODE_BODY[:7])
picture('fig3-2', '图3-2 医院首层整体联系与门诊单元局部组合示意')
prose(C.MODE_BODY[7:])
heading(C.SUB3, 3)
prose(C.RULE_INTRO)
prose(C.CONFIG)
matrix(C.CONFIG_ROWS, [2.9, 5.0, 6.74], '表3-2 医院首层功能空间配置与规模确定依据')
prose(C.REL)
matrix(C.REL_ROWS, [2.2, 5.5, 6.94], '表3-3 医院首层功能空间关系归纳')
prose(C.CONSTRAINT)
matrix(C.CONSTRAINT_ROWS, [2.2, 4.2, 8.24], '表3-4 医院首层功能空间布局约束归纳')
note = para('注：表中常规门诊诊室与走道候诊指标依据GB 51039—2014（2024年版）相应条文[96]，其他功能另按适用要求核定。', size=10)
note.paragraph_format.first_line_indent = Pt(0)
note.paragraph_format.line_spacing = Pt(15)
prose(C.ENDING)
D.core_properties.title = C.CHAPTER
D.core_properties.subject = '第三章章名及3.1医院首层功能构成与空间组织特征'
D.core_properties.comments = '独立替换节稿。参考文献序号沿用原稿，合并全文时统一更新。'
D.save(OUT)
print(OUT)
print('paragraphs', len(D.paragraphs), 'tables', len(D.tables))
