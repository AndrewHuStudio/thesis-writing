from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon
from collections import Counter
import hashlib
import json
import markdown
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET

WORK = Path(__file__).resolve().parent
PLAN = WORK.parents[2] / '标注试样/14_无锡市人民医院二期建设项目'
data = json.loads((PLAN / 'annotation.json').read_text())
before = json.loads((WORK / '修改前备份/annotation.json').read_text())
md = (PLAN / '标注说明.md').read_text()
original_md = (WORK / '修改前备份/标注说明.md').read_text()
questions = json.loads((WORK / '关键问题映射.json').read_text())
original = Image.open(PLAN / data['image']['file']).convert('RGB')
font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 22)
manual = {
    'L02': {'S025': (2350, 405), 'S027': (2170, 450)},
    'L03': {'S165': (1160, 1955)},
    'L04': {'S172': (810, 2100), 'S165': (820, 1950)},
    'L05': {'S105': (1730, 1615), 'S174': (1590, 1670)},
}
for q in questions:
    x0,y0,x1,y1 = q['box']
    scale = 3 if y1-y0 < 400 else 2
    crop = original.crop(q['box']).resize(((x1-x0)*scale, (y1-y0)*scale))
    draw = ImageDraw.Draw(crop)
    centres = {}
    for s in data['spaces']:
        pt = Polygon(s['polygon_px']).representative_point()
        if x0+35/scale < pt.x < x1-35/scale and y0+18/scale < pt.y < y1-18/scale:
            centres[s['id']] = (pt.x, pt.y)
    centres.update(manual.get(q['id'], {}))
    for sid, (px,py) in centres.items():
        x,y = (px-x0)*scale, (py-y0)*scale
        color = '#b45309' if sid in q['targets'] else '#1d4ed8'
        draw.rectangle((x-30,y-15,x+33,y+15),fill='white',outline=color,width=2)
        draw.text((x-28,y-13),sid,fill=color,font=font)
    crop.save(WORK / f'{q["id"]}_局部.png')

css = 'body{font-family:Arial,"PingFang SC",sans-serif;max-width:920px;margin:24px auto;font-size:17px;line-height:1.65}img{display:block;max-width:100%;max-height:820px;width:auto;height:auto}table{border-collapse:collapse}td,th{border:1px solid #aaa;padding:5px}a{color:#1664b0}'
def page(content):
    return f'<!doctype html><meta charset="utf-8"><base href="{PLAN.resolve().as_uri()}/"><style>{css}</style>' + markdown.markdown(content, extensions=['tables'])

(WORK / '标注说明_预览.html').write_text(page(md))
for q in questions:
    block = re.search(rf'^### {q["id"]}｜.*?(?=^### L\d|^## |\Z)', md, re.M|re.S).group()
    (WORK / f'{q["id"]}_MD预览.html').write_text(page(block))

chrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
with tempfile.TemporaryDirectory(prefix='annotation14_connectivity_qa_') as profile:
    def shot(url, output, width, height):
        result = subprocess.run([chrome,'--headless','--no-sandbox','--disable-gpu',f'--user-data-dir={profile}',
            '--hide-scrollbars','--allow-file-access-from-files','--force-device-scale-factor=1',
            f'--window-size={width},{height}',f'--screenshot={output}',url],capture_output=True,text=True,timeout=35)
        assert result.returncode == 0 and output.exists(), result.stderr[-1000:]
    shot((PLAN / '标注.svg').resolve().as_uri(), WORK / '标注_全图.png', 3300, 2680)
    for q in questions:
        shot((WORK / f'{q["id"]}_MD预览.html').as_uri(), WORK / f'{q["id"]}_MD预览.png', 1000, 1550)

im = Image.open(WORK / '标注_全图.png')
im.resize((1650,1340)).save(WORK / '标注_全图预览.png')
tiles = {'北侧':(1230,140,2110,470),'输液':(1240,470,2110,1380),'保健':(1240,1350,2230,1920),
         '体检':(2200,1330,2880,1930),'急诊':(170,1600,1280,2180),'留观':(1250,1630,1830,2180)}
smallfont = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 13)
for name, box in tiles.items():
    crop = original.crop(box).resize(((box[2]-box[0])*2,(box[3]-box[1])*2))
    draw = ImageDraw.Draw(crop)
    for r in data['relations']:
        for o in r.get('openings', []):
            x,y = o['position_px']
            if box[0] < x < box[2] and box[1] < y < box[3]:
                px,py = (x-box[0])*2,(y-box[1])*2
                draw.ellipse((px-5,py-5,px+5,py+5),fill='#dc2626',outline='white')
                draw.text((px+7,py-18),o['id'],fill='#b91c1c',font=smallfont,stroke_width=1,stroke_fill='white')
    crop.save(WORK / f'{name}_原图门位复核.png')

assert data['spaces'] == before['spaces']
assert len([p for p in PLAN.iterdir() if p.is_file()]) == 4
assert hashlib.sha256((PLAN / data['image']['file']).read_bytes()).hexdigest() == (WORK / 'source.sha256').read_text().strip()
rows = [line for line in original_md.splitlines() if re.match(r'^\| \d{2}\s*\| S\d+',line)]
assert len(rows)==55 and all(line in md for line in rows)
images = re.findall(r'!\[[^\]]*\]\(([^)]+)\)',md)
assert len(images)==15 and all((PLAN/img).is_file() for img in images)
assert len(re.findall(r'\*\*我的确认／备注：\*\*待填写',md)) == 5
ns = {'s':'http://www.w3.org/2000/svg'}
root = ET.parse(PLAN/'标注.svg').getroot()
for s in data['spaces']:
    g = root.find(f'.//s:g[@id="{s["id"]}"]',ns)
    assert g.get('data-space-name') == s['name'] and g.get('data-space-type') == s['type']
    text = ''.join(''.join(e.itertext()) for e in g.findall('s:text',ns))
    assert s['name'] in text
expected = {o['id']:(r,o) for r in data['relations'] for o in r.get('openings',[])}
markers = [e for e in root.iter() if e.get('data-opening-id')]
assert len(markers)==len(expected)==157
for g in markers:
    r,o = expected[g.get('data-opening-id')]
    circle = g.find('s:circle',ns)
    assert circle is not None and circle.get('fill') == '#dc2626'
    assert [float(circle.get(k)) for k in ('cx','cy')] == o['position_px']
    assert (g.get('data-source'),g.get('data-target')) == (r['source'],r['target'])
    assert g.get('data-kind') == o['kind']
graph = {s['id']:set() for s in data['spaces']}
for r in data['relations']:
    if r['type']=='access':
        graph[r['source']].add(r['target']);graph[r['target']].add(r['source'])
entry_targets = {r['target'] for r in data['relations'] if r['type']=='entrance'}
reached=set();stack=list(entry_targets)
while stack:
    sid=stack.pop()
    if sid in reached:continue
    reached.add(sid);stack.extend(graph[sid]-reached)
unreached=[{'id':s['id'],'name':s['name']} for s in data['spaces'] if s['id'] not in reached]
report = {'spaces':len(data['spaces']),'relations':len(data['relations']),
          'relation_types':dict(Counter(r['type'] for r in data['relations'])),
          'openings':len(expected),'opening_kinds':dict(Counter(o['kind'] for _,o in expected.values())),
          'names_geometry_original_image_preserved':True,
          'user_name_rows_preserved':55,'valid_embedded_images':len(images),
          'pending_questions':5,'unreached_from_documented_entrances':unreached,
          'graph_disconnection_does_not_mean_inaccessible':True}
(WORK/'本轮一致性核验.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
