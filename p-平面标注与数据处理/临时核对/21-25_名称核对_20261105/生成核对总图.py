"""Restore the historical overview drawings in persistent review folders."""
import json
from pathlib import Path
from PIL import Image

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1] / '标注试样'
HIST = BASE / '历史取证'
FONT = '/System/Library/Fonts/STHeiti Medium.ttc'

import sys
for number in range(int(sys.argv[1]) if len(sys.argv) > 1 else 21, 26):
    project = next(ROOT.glob(f'{number}_*'))
    target = BASE / project.name
    data = json.loads((project / 'annotation.json').read_text())
    rows = json.loads((target / '固定核对映射.json').read_text())
    if number == 21:
        context = {}
        source = (HIST / '21_59_build_annotation.py').read_text()
        exec('\n'.join(source.splitlines()[:147]), context)
        items = context['items']
        for item in items:
            matching = [r for r in rows if r['key'] == item['key']]
            if matching:
                row = matching[0]
                item.update(id=row['id'], candidate=' / '.join(row['candidates']),
                            evidence=row['evidence'], confidence=row['confidence'])
        (target / 'reading_items.json').write_text(json.dumps(items, ensure_ascii=False))
        code = (HIST / '21_120_build_review.py').read_text()
    elif number == 22:
        for row in rows:
            row.update(candidate=' / '.join(row['candidates']), basis=row['evidence'])
        (target / 'review-map.json').write_text(json.dumps(rows, ensure_ascii=False))
        code = (HIST / '22_84_make_review.py').read_text().split('# Draft SVG render')[0]
    elif number == 23:
        for row in rows:
            row['row'] = row['key']
        (target / 'review_mapping.json').write_text(json.dumps(rows, ensure_ascii=False))
        code = (HIST / '23_220_straight_review.py').read_text()
        code = code.replace("if not rows or abs(y-rows[-1][0])>20:rows.append([y,[]])",
            "if not rows or abs(y-rows[-1][0])>20 or any(abs(Polygon(q['polygon_px']).centroid.x-Polygon(r['polygon_px']).centroid.x)<2 for q in rows[-1][1]):rows.append([y,[]])")
        code = code.replace("rs=[r for r in review if r['side']==side];n=len(rs)",
            "rs=[r for r in review if r['side']==side and r['group']!='03中央中段'];n=len(rs)")
        code = code.replace("lo=np.full(n,330.);hi=np.full(n,H-300.)",
            "lo=np.full(n,330.);hi=np.full(n,H-300.)\n for i,r in enumerate(rs):\n  if r['group']=='02左侧放射':hi[i]=4400\n  if r['group']=='05左下药房':lo[i]=4560")
        code = code.replace("arrange('left');arrange('right')", """arrange('left');arrange('right')
central=[r for r in review if r['group']=='03中央中段']
r=central[0];r['label_y']=4440;r['port']=(35,4440);r['path']=[r['port'],(15,4440),(15,2940),(3220,2940),(3220,r['anchor'][1]),r['anchor']]
r=central[1];r['label_y']=4480;r['port']=(650,4480);r['path']=[r['port'],(3190,4480),(3190,r['anchor'][1]),r['anchor']]
""")
    elif number == 24:
        for row in rows:
            row.update(candidate=' / '.join(row['candidates']), basis=row['evidence'],
                       side='left' if row['group'] in [0, 2] else 'right')
        (target / 'review-map.json').write_text(json.dumps(rows, ensure_ascii=False))
        code = (HIST / '24_110_make_review.py').read_text().split('# 补充局部')[0]
    else:
        for row in rows:
            row.update(review_no=row['number'], polygon=[[y / (3232 / 2300),
                       (2472-x) / (3232 / 2300)] for x,y in row['polygon_px']])
        Image.open(project / data['image']['file']).rotate(90, expand=True).save(target / 'upright.png')
        code = (HIST / '25_105_make_review.py').read_text().split("font_path=")[1]
        code = 'font_path=' + code
        code = code.split('# No leader crossings')[0] + '''
assert len(qs) == 18
out.save(T/'25_名称核对总图.png')
preview=out.copy();preview.thumbnail((2200,1600));preview.save(T/'25_核对总图_预览.png')
'''
    code = code.replace('p-写作过程/标注试样', 'p-平面标注与数据处理/标注试样')
    code = code.replace(f'/tmp/outpatient{number}-review', str(target))
    code = code.replace('/System/Library/Fonts/PingFang.ttc', FONT)
    code = code.replace('/System/Library/Fonts/Hiragino Sans GB.ttc', FONT)
    context = dict(T=target, qs=rows, data=data)
    if number == 25:
        from PIL import ImageDraw, ImageFont
        from shapely.geometry import LineString
        context.update(Image=Image, ImageDraw=ImageDraw, ImageFont=ImageFont, LineString=LineString)
    exec(compile(code, f'restored_review_{number}', 'exec'), context)
    print(number, 'overview restored', flush=True)
