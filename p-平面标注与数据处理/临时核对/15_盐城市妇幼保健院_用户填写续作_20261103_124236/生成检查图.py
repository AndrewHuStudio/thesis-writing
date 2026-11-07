from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont
import pymupdf

R = Path(__file__).resolve().parent
P = R / '待核验成果'
data = json.loads((P / 'annotation.json').read_text())
spaces = {s['id']: s for s in data['spaces']}
rows = []
for line in (P / '标注说明.md').read_text().splitlines():
    c = [v.strip() for v in line.strip().strip('|').split('|')]
    if len(c) == 7 and c[1] in {'S205', 'S206', 'S222', 'S245', 'S274'}:
        rows.append(c)
im = Image.open(P / data['image']['file']).convert('RGB').resize((4888, 6520))
draw = ImageDraw.Draw(im)
font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 28)
for row in rows:
    pts = [tuple(v * 2 for v in xy) for xy in spaces[row[1]]['polygon_px']]
    draw.line(pts + [pts[0]], fill='#d97706', width=5)
    x = min(v[0] for v in pts) + 3
    y = min(v[1] for v in pts) + 3
    label = row[0] + ' ' + row[1]
    bounds = draw.textbbox((x, y), label, font=font)
    draw.rectangle((bounds[0]-3, bounds[1]-3, bounds[2]+3, bounds[3]+3), fill='white', outline='#d97706', width=2)
    draw.text((x, y), label, font=font, fill='#9a3412')
im.save(R / '剩余5项定位总图.png')
document = pymupdf.open(P / '标注.svg')
page = document[0]
page.get_pixmap(matrix=pymupdf.Matrix(.65, .65), alpha=False).save(R / '标注全图检查.png')
head = 122.2
for name, box in {
    '西北角与名称修正': (175, 275, 570, 425),
    '东北角与名称修正': (1885, 280, 2230, 425),
    '大会议厅合并': (420, 2240, 690, 2540),
    '西南休息区合并': (320, 2800, 545, 2905),
    '最南端休息区与厕所': (610, 2880, 960, 3100),
    'VIP休息室及检查区': (580, 1040, 960, 1195),
}.items():
    x0, y0, x1, y1 = box
    clip = pymupdf.Rect(x0, y0+head, x1, y1+head)
    page.get_pixmap(matrix=pymupdf.Matrix(3, 3), clip=clip, alpha=False).save(R / (name + '.png'))
print('已生成剩余5项定位及全图、6处局部检查图')
