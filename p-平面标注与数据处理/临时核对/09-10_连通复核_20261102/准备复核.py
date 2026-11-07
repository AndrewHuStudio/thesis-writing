from pathlib import Path
import datetime
import hashlib
import html
import json
import re
import shutil

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
BASE = ROOT/'p-平面标注与数据处理'
FONT = '/System/Library/Fonts/STHeiti Medium.ttc'
NAMES = ['09_深圳大学学府医院', '10_石家庄第一医院新建赵卜口院区']
REGIONS = {
 '09': [('A_影像', (165,400,765,650)), ('B_北中央', (740,400,1000,720)),
        ('C_急诊', (965,400,1325,940)), ('D_药房', (165,635,765,1005)),
        ('E_体检', (165,990,765,1185)), ('F_儿科大厅', (745,700,1325,1125)),
        ('G_西南', (165,1170,765,1455)), ('H_儿科', (760,1110,1325,1455)),
        ('I_中央南', (730,1100,1000,1455))],
 '10': [('A_急诊', (160,305,515,680)), ('B_影像', (720,305,1190,685)),
        ('C_西中', (160,675,515,1150)), ('D_药房', (720,675,1190,1010)),
        ('E_西南', (160,1135,770,1410)), ('F_中央', (490,305,760,1420))]
}


def table_rows(text):
    rows = []
    for line in text.splitlines():
        cells = [html.unescape(x.strip()) for x in line.strip().strip('|').split('|')]
        if len(cells)==7 and re.fullmatch(r'\d+',cells[0]) and re.fullmatch(r'S\d+',cells[1]):
            rows.append(dict(number=cells[0], sid=cells[1], candidate=cells[2], answer=cells[5]))
    return rows


def work_polygon(space, number):
    scale = 2444/1367
    if number == '09':
        return [[(2444-y)/scale, x/scale] for x,y in space['polygon_px']]
    return [[x/(2444/1367), y/(3260/1824)] for x,y in space['polygon_px']]


def main(name):
    project = BASE/'标注试样'/name
    out = WORK/name
    backup = out/'修改前备份'
    if backup.exists():
        raise RuntimeError('Backup already exists; do not replace user evidence.')
    backup.mkdir(parents=True)
    for file in project.iterdir():
        if file.is_file():
            shutil.copy2(file, backup/file.name)
    data = json.loads((project/'annotation.json').read_text())
    rows = table_rows((project/'标注说明.md').read_text())
    assert len(rows) == sum(s['type']=='unknown' for s in data['spaces'])
    (out/'用户填写解析.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    hashes = {f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in project.iterdir() if f.is_file()}
    (out/'修改前文件校验.json').write_text(json.dumps(hashes,ensure_ascii=False,indent=2)+'\n')
    source = Image.open(project/data['image']['file']).convert('RGB')
    if name.startswith('09'):
        source = source.transpose(Image.Transpose.ROTATE_270)
    source = source.resize((1367,1824), Image.Resampling.LANCZOS)
    source.save(out/'工作坐标原图.png')
    polies = {s['id']:work_polygon(s,name[:2]) for s in data['spaces']}
    final = {r['sid']:r['answer'] for r in rows}
    catalog = []
    for s in data['spaces']:
        b = Polygon(polies[s['id']]).bounds
        adj = [r['target'] if r['source']==s['id'] else r['source'] for r in data['relations']
               if r['type']=='access' and s['id'] in [r['source'],r['target']]]
        catalog.append(f'{s["id"]} {final.get(s["id"],s["name"])} bounds={tuple(round(v,1) for v in b)} access={adj}')
    (out/'空间与旧关系.txt').write_text('\n'.join(catalog)+'\n')
    (out/'工作坐标多边形.json').write_text(json.dumps(polies,ensure_ascii=False,indent=2)+'\n')
    for region,b in REGIONS[name[:2]]:
        z=3
        raw=source.crop(b).resize(((b[2]-b[0])*z,(b[3]-b[1])*z),Image.Resampling.LANCZOS)
        raw.save(out/(region+'_原图.png'))
        draw=ImageDraw.Draw(raw)
        f=ImageFont.truetype(FONT,21)
        for sid,pts in polies.items():
            p=Polygon(pts)
            if not p.intersects(Polygon([(b[0],b[1]),(b[2],b[1]),(b[2],b[3]),(b[0],b[3])])):
                continue
            points=[((x-b[0])*z,(y-b[1])*z) for x,y in pts]
            draw.line(points+[points[0]],fill='#0891b2',width=2)
            q=p.representative_point();cx=(q.x-b[0])*z;cy=(q.y-b[1])*z
            draw.text((cx,cy),sid,anchor='mm',font=f,fill='#9f1239',stroke_width=3,stroke_fill='white')
        for x in range((b[0]//50+1)*50,b[2],50):
            draw.text(((x-b[0])*z+2,0),str(x),font=f,fill='#1d4ed8',stroke_width=2,stroke_fill='white')
        for y in range((b[1]//50+1)*50,b[3],50):
            draw.text((0,(y-b[1])*z),str(y),font=f,fill='#1d4ed8',stroke_width=2,stroke_fill='white')
        raw.save(out/(region+'_编号.png'))
    print(name, 'backup and views ready',len(rows),flush=True)


if __name__=='__main__':
    for name in NAMES:
        main(name)
