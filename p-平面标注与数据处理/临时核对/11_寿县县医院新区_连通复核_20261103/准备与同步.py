from pathlib import Path
from collections import Counter
import html
import json
import re

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
PROJECT = ROOT / 'p-平面标注与数据处理/标注试样/11_寿县县医院新区'
BACKUP = sorted(WORK.glob('修改前备份_*'))[0]
DATA = json.loads((BACKUP / 'annotation.json').read_text())
SPACES = {s['id']: s for s in DATA['spaces']}
TEXT = (BACKUP / '标注说明.md').read_text()
ROWS = []
for line in TEXT.splitlines():
    cells = [html.unescape(c.strip()) for c in line.strip('|').split('|')]
    if len(cells) == 8 and re.fullmatch(r'\d+', cells[0]) and re.fullmatch(r'S\d+', cells[1]):
        ROWS.append(cells)
assert len(ROWS) == 37

TYPES = {
    '值班': 'staff_support', '主任办公室': 'office', '贵重品库': 'storage',
    '消防控制室': 'building_control', '更衣': 'staff_support', '入院处理': 'treatment',
    '结算': 'registration', '票据': 'office', '餐车停放': 'storage',
    '餐车清洗': 'hospital_logistics', '备餐': 'hospital_logistics',
    '主食库': 'storage', '副食库': 'storage', '调料库': 'storage', '冷库': 'storage',
    '营养液配置': 'medication_preparation', '管理办公': 'office', '主任办': 'office',
    '厨师休息': 'staff_support', 'CR': 'imaging', '钼靶机': 'imaging',
    '胃肠透视': 'imaging', '隔离观察': 'isolation', '输液': 'treatment',
    '贵重物品库': 'storage', '观察诊室': 'consultation', '器械、药品': 'equipment_room',
}
applied = []
for row in ROWS:
    number, sid, location, candidate, alternative, evidence, answer, repeat = row
    assert number == repeat
    if not answer or any(v in answer for v in ['待确认', '待定', '待填写']):
        continue
    if sid == 'S029':
        assert answer == '直接和下面餐厅打通'
        continue
    name = candidate if answer == '已确认' else answer
    s = SPACES[sid]
    s['name'] = name
    # Names alone do not settle the two previously flagged area attributes.
    s['type'] = 'unknown' if sid in {'S001', 'S035'} else TYPES[name]
    applied.append({'核对号': number, 'id': sid, 'name': name, 'type': s['type'], '原始填写': answer})

# The user's instruction joins the upper piece to the cafeteria below.
a = Polygon(SPACES['S029']['polygon_px'])
b = Polygon(SPACES['S032']['polygon_px'])
merged = unary_union([a, b, box(1462, 420, 1555, 424)])
assert merged.geom_type == 'Polygon' and merged.is_valid
SPACES['S032']['polygon_px'] = [list(p) for p in list(merged.exterior.coords)[:-1]]
DATA['spaces'] = [s for s in DATA['spaces'] if s['id'] != 'S029']
for relation in DATA['relations']:
    for key in ['source', 'target']:
        if relation.get(key) == 'S029':
            relation[key] = 'S032'
assert all(r.get('source') != r.get('target') for r in DATA['relations'])
denominator = sum(Polygon(s['polygon_px']).area for s in DATA['spaces'] if s['type'] not in {'courtyard', 'landscape'})
for s in DATA['spaces']:
    if s['type'] not in {'courtyard', 'landscape'}:
        s['area_ratio'] = round(Polygon(s['polygon_px']).area / denominator, 8)
(WORK / '已同步房名.json').write_text(json.dumps(DATA, ensure_ascii=False, indent=2) + '\n')
(WORK / '用户填写与同步记录.json').write_text(json.dumps({'applied': applied, 'merged': {'S029': 'S032', 'answer': '直接和下面餐厅打通'}, 'area_pending': ['S001', 'S035']}, ensure_ascii=False, indent=2) + '\n')

# Review crops use original pixel coordinates. All opening positions are read manually.
source = Image.open(PROJECT / DATA['image']['file']).convert('RGB')
FONT = '/System/Library/Fonts/STHeiti Medium.ttc'
font = ImageFont.truetype(FONT, 26)
small = ImageFont.truetype(FONT, 21)
REGIONS = [
    ('A_北侧药房与手续', (310, 235, 1240, 690)),
    ('B_餐饮', (1260, 235, 2130, 690)),
    ('C_感染门诊', (310, 1015, 1170, 1330)),
    ('D_影像北中', (1260, 1020, 2110, 1490)),
    ('E_影像南', (1260, 1460, 2110, 1860)),
    ('F_儿科', (310, 1550, 1170, 1870)),
    ('G_输液', (310, 2080, 1170, 2390)),
    ('H_急诊', (310, 2340, 1170, 2920)),
    ('I_药房', (1260, 2080, 2110, 2920)),
]
for title, bounds in REGIONS:
    x0, y0, x1, y1 = bounds
    z, margin = 3, 70
    base = source.crop(bounds).resize(((x1 - x0) * z, (y1 - y0) * z))
    raw = Image.new('RGB', (base.width + margin, base.height + margin), 'white')
    raw.paste(base, (margin, margin))
    draw = ImageDraw.Draw(raw)
    for x in range((x0 // 25 + 1) * 25, x1, 25):
        px = margin + (x - x0) * z
        draw.line((px, margin - 10, px, margin), fill='black', width=2)
        draw.text((px - 20, margin - 37), str(x), font=small, fill='black')
    for y in range((y0 // 25 + 1) * 25, y1, 25):
        py = margin + (y - y0) * z
        draw.line((margin - 10, py, margin, py), fill='black', width=2)
        draw.text((2, py - 12), str(y), font=small, fill='black')
    raw.save(WORK / (title + '_原图.png'))
    marked = raw.copy()
    draw = ImageDraw.Draw(marked)
    for s in DATA['spaces']:
        poly = Polygon(s['polygon_px'])
        if not poly.intersects(box(*bounds)):
            continue
        pts = [(margin + (x - x0) * z, margin + (y - y0) * z) for x, y in s['polygon_px']]
        draw.line(pts + pts[:1], fill='#0070aa', width=2)
        clipped = poly.intersection(box(*bounds))
        if clipped.area < 50:
            continue
        center = clipped.representative_point()
        px, py = margin + (center.x - x0) * z, margin + (center.y - y0) * z
        label = s['id']
        draw.rectangle((px - 38, py - 13, px + 45, py + 19), fill='white')
        draw.text((px - 35, py - 12), label, font=font, fill='#005080')
    marked.save(WORK / (title + '_编号.png'))
print('Saved staged names, archived answers, and nine original-coordinate review crops.')
