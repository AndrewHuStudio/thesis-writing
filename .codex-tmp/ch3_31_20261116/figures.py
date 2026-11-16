"""使用矢量绘图生成论文组织示意图，不处理原图。"""
from pathlib import Path
import subprocess
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor

ROOT = Path(__file__).parent
POPPLER = Path(r'C:\Users\QIYILAB\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe')
pdfmetrics.registerFont(TTFont('Hei', r'C:\Windows\Fonts\simhei.ttf'))


def text(c, x, y, s, size=10.5):
    c.setFillColor(HexColor('#000000'))
    c.setFont('Hei', size)
    c.drawCentredString(x, y, s)


def box(c, x, y, w, h, title, lines=(), fill='#F1F4FA', size=10.5):
    c.setFillColor(HexColor(fill))
    c.setStrokeColor(HexColor('#455568'))
    c.setLineWidth(.65)
    c.rect(x, y, w, h, fill=1, stroke=1)
    total = 15 + len(lines) * 13
    ty = y + (h + total) / 2 - 12
    text(c, x+w/2, ty, title, size)
    for line in lines:
        ty -= 13
        text(c, x+w/2, ty, line, 9.5)


def line(c, x1, y1, x2, y2):
    c.setStrokeColor(HexColor('#455568'))
    c.setLineWidth(.65)
    c.line(x1, y1, x2, y2)


def render(c, stem):
    c.save()
    subprocess.run([str(POPPLER), '-png', '-singlefile', '-r', '260',
                    str(ROOT/f'{stem}.pdf'), str(ROOT/stem)], check=True,
                   capture_output=True)


def classification():
    c = canvas.Canvas(str(ROOT/'fig3-1.pdf'), pagesize=(420, 286))
    box(c, 130, 257, 160, 27, '医院首层功能空间', fill='#FFFFFF', size=12)
    line(c, 210, 257, 210, 45)
    data = [
        ('公共服务与等候', ['咨询、挂号缴费、取药、住院办理', '公共等候、候诊、卫生及便利服务']),
        ('诊查与医疗处置', ['普通及专科诊室、急诊诊室', '治疗、抢救及观察等']),
        ('检查与医技', ['采血、检验、医学影像', '超声、心电检查及配套用房']),
        ('医护办公与管理教学', ['办公、会议、示教、值班', '医护更衣、休息等']),
        ('后勤保障与设备', ['库房、清洁、供应与维护', '污物暂存及设备用房等']),
        ('交通与出入接口', ['门厅、医疗街、走廊', '出入口、电梯、楼梯及前室']),
    ]
    for i, (title, items) in enumerate(data):
        row, col = divmod(i, 2)
        x, y = col*225, 177-row*79
        line(c, 210, y+31, 195 if col == 0 else 225, y+31)
        box(c, x, y, 195, 62, title, items,
            fill='#EEF3FA' if col == 0 else '#FAF3E6')
    text(c, 210, 4, '按主要用途归纳，具体配置由项目条件确定', 9)
    render(c, 'fig3-1')


def organization():
    c = canvas.Canvas(str(ROOT/'fig3-2.pdf'), pagesize=(420, 315))
    text(c, 210, 300, '首层整体联系', 12)
    box(c, 0, 253, 77, 29, '室外到达', fill='#FFFFFF')
    box(c, 116, 253, 304, 29, '入口、门厅、医疗街与公共走廊')
    line(c, 77, 267, 116, 267)
    labels = [('门诊', '诊查与候诊'), ('急诊', '接诊与处置'),
              ('医技', '检查与共享'), ('住院服务', '办理与接口'),
              ('支持用房', '办公及后勤')]
    line(c, 268, 253, 268, 237)
    line(c, 40, 237, 380, 237)
    for i, (label, sub) in enumerate(labels):
        x = i*85
        line(c, x+40, 237, x+40, 220)
        box(c, x, 169, 80, 51, label, [sub], fill='#FAF3E6')
    text(c, 210, 151, '各组团依照业务组织内部空间，具体入口和联系分别确定', 9)
    c.setDash(3, 3)
    line(c, 0, 136, 420, 136)
    c.setDash()
    text(c, 210, 118, '局部组合示例  门诊单元', 12)
    local = [('诊室', 0), ('分诊', 107), ('候诊', 214), ('医护辅助', 321)]
    for label, x in local:
        box(c, x, 62, 99, 34, label, fill='#F4F4F4')
        line(c, x+49.5, 62, x+49.5, 43)
    box(c, 0, 18, 420, 25, '内部走廊及局部公共空间', fill='#EEF4EC')
    text(c, 210, 2, '连线表示组织联系，实际路径可包含中间空间', 9)
    render(c, 'fig3-2')


if __name__ == '__main__':
    classification()
    organization()
