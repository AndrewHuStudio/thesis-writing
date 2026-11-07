"""Restore the original full-plan review layouts with the recovered fixed IDs."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon, LineString

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1] / '标注试样'
FONT = '/System/Library/Fonts/STHeiti Medium.ttc'

for number in range(31, 35):
    project = next(ROOT.glob(f'{number}_*'))
    target = BASE / project.name
    data = json.loads((project / 'annotation.json').read_text())
    rows = json.loads((target / '固定核对映射.json').read_text())
    for r in rows:
        r.update(basis=r['evidence'], candidate=' / '.join(r['candidates']),
                 review=r['number'], review_no=r['number'])
    if number == 31:
        for r in rows:
            if r['key'] in ['dsa', 'equipment_image', 'film_delivery']:
                r['anchor_y'] = {'dsa':632, 'equipment_image':640, 'film_delivery':648}[r['key']]
        Image.open(project / data['image']['file']).rotate(90, expand=True).save(target / 'upright.png')
        (target / 'layout.json').write_text(json.dumps(rows, ensure_ascii=False))
        code = (BASE / '历史取证/31_112_review31.py').read_text()
        code = code[:code.index("(T/'review-map.json')")] + code[code.index('font='):]
        code = code[:code.index("(T/'leader-check.json')")]
        code = code.replace('15／17／19请补“露天、挑空或室内可步入”；16请说明范围性质。',
                            '庭院与普通大厅／走道的用途需区分；庭院不计面积；16请说明范围性质。')
        code = code.replace("font='/System/Library/Fonts/Supplemental/Arial Unicode.ttf'", f'font={FONT!r}')
        code = code[:code.index(' # Matching numbered badge')] + code[code.index(' d.ellipse((px-5'):]
    elif number == 32:
        (target / '核对映射.json').write_text(json.dumps(rows, ensure_ascii=False))
        code = (BASE / '历史取证/32_113_review.py').read_text().split('# 高密度小房间局部')[0]
        code = code.replace('绿色围合区的室内外属性另待确认。', '绿色围合区需确认用途；确定为庭院后不计面积。')
        code = code[:code.index('  # 图内编号置于目标点')] + code[code.index('  d.rounded_rectangle((labelx'):]
    elif number == 33:
        (target / '核对编号映射.json').write_text(json.dumps(rows, ensure_ascii=False))
        code = (BASE / '历史取证/33_129_build_review.py').read_text().split("(T/'核对编号映射.json').write_text")[0]
        code = '\n'.join(line for line in code.splitlines() if not line.startswith(' draw.rounded_rectangle((x,y,x+38'))
    else:
        for r in rows:
            r['candidate'] = r['candidates']
        (target / 'review-map.json').write_text(json.dumps(rows, ensure_ascii=False))
        code = (BASE / '历史取证/34_85_make_review.py').read_text().split('# 密集小字补充')[0]
        code = '\n'.join(line for line in code.splitlines() if not any(s in line for s in [
            'd.rounded_rectangle((min(xs)', 'd.text((min(xs)']))
    code = code.replace('p-写作过程/标注试样', 'p-平面标注与数据处理/标注试样')
    code = code.replace(f'/tmp/outpatient{number}-review', str(target))
    exec(compile(code, f'overview_{number}', 'exec'), {})
    names = {31: '31_高清核对总图.png', 32: '32_高清核对总图.png',
             33: '核对总图_高清.png', 34: '34_核对总图.png'}
    image = Image.open(target / names[number])
    image.save(target / '完整核对总图.png')
    image.thumbnail((2000, 2200))
    image.save(target / '总图预览.jpg', quality=92)
    print(number, 'overview restored', flush=True)

# Seven questions on 35: keep the full source sheet upright with two sidebars.
project = next(ROOT.glob('35_*'))
target = BASE / project.name
data = json.loads((project / 'annotation.json').read_text())
rows = json.loads((target / '固定核对映射.json').read_text())
src = Image.open(project / data['image']['file']).rotate(90, expand=True).convert('RGB')
ox, oy = 740, 150
out = Image.new('RGB', (src.width+1480, src.height+250), '#f5f7fa')
out.paste(src, (ox, oy))
draw = ImageDraw.Draw(out)
font = lambda size: ImageFont.truetype(FONT, size)
draw.text((40,30), '35｜阳春京伦妇产医院 · 首层核对总图 · 7项待确认', font=font(40), fill='#17314a')
draw.text((40,90), '完整原图逆时针转正90°显示；固定核对号不变；候选尚未确认。', font=font(28), fill='#475569')
paths = []
for i, r in enumerate(rows):
    poly = Polygon([(y,2444-x) for x,y in r['polygon_px']])
    side = 'left' if i < 4 else 'right'
    point = poly.representative_point()
    ay = point.y
    cut = poly.intersection(LineString([(-1,ay),(4000,ay)]))
    ax = cut.bounds[0] if side == 'left' else cut.bounds[2]
    px, py = ox+ax, oy+ay
    color = ['#2563eb','#0f766e','#be123c','#7c3aed','#c2410c','#0369a1','#8b5e00'][i]
    pts = [(ox+x,oy+y) for x,y in poly.exterior.coords]
    draw.line(pts,fill=color,width=4)
    tx = 30 if side == 'left' else ox+src.width+25
    edge = tx+680 if side == 'left' else tx
    route = [(edge,py),(ox if side=='left' else ox+src.width,py),(px,py)]
    paths.append(LineString(route))
    draw.line(route,fill=color,width=3)
    draw.rounded_rectangle((tx,py-75,tx+680,py+75),10,fill='white',outline=color,width=3)
    draw.text((tx+16,py-61),r['number']+'｜'+r['id']+' 名称未确认',font=font(30),fill=color)
    draw.text((tx+16,py-12),'候选：'+' / '.join(r['candidates']),font=font(23),fill='#17314a')
    draw.text((tx+16,py+29),'把握：'+r['confidence'],font=font(23),fill='#475569')
for i,p in enumerate(paths):
    assert all(not p.intersects(q) for q in paths[i+1:])
out.save(target / '完整核对总图.png')
out.thumbnail((2200,1600))
out.save(target / '总图预览.jpg',quality=92)
print(35, 'overview restored', flush=True)
