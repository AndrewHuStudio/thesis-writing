from pathlib import Path
from collections import Counter
import json,hashlib,re,xml.etree.ElementTree as E
import pymupdf
from PIL import Image
from shapely.geometry import Polygon,Point

H=Path(__file__).resolve().parent;P=H.parents[2]/'标注试样/04_兰州市安宁新城医院新建项目'
d=json.loads((P/'annotation.json').read_text());old=json.loads((H/'修改前备份/annotation.json').read_text());by={s['id']:s for s in d['spaces']}
root=E.parse(P/'标注.svg').getroot();plan=root.find('./{*}g');types=json.loads(Path('/Users/hushili/.codex/skills/outpatient-plan-annotation/references/space-types.json').read_text())
assert list(by)==[s['id'] for s in old['spaces']]
assert all(by[s['id']]['name']==s['name'] for s in old['spaces'])
missing=[];rect_points=[]
points=[(o['id'],Point(o['position_px'])) for r in d['relations'] for o in r.get('openings',[])]
for s in d['spaces']:
 g=plan.find(f'./{{*}}g[@id="{s["id"]}"]');t=''.join(e.text or '' for e in g.findall('./{*}text')).replace(' ','')
 if not all(v.replace(' ','') in t for v in [s['id'],s['name'],'〔'+types[s['type']]+'〕']):missing.append(s['id'])
 for r in g.findall('./{*}rect'):
  x,y,w,h=[float(r.get(k)) for k in ['x','y','width','height']]
  for oid,q in points:
   if x-2<q.x<x+w+2 and y-2<q.y<y+h+2:rect_points.append((s['id'],oid))
assert not missing,missing
assert not rect_points,rect_points
max_distance=0
for r in d['relations']:
 for o in r.get('openings',[]):
  q=Point(o['position_px'])
  for sid in [r['source'],r['target']]:max_distance=max(max_distance,Polygon(by[sid]['polygon_px']).boundary.distance(q))
assert max_distance<=22,max_distance
old_union=__import__('shapely').union_all([Polygon(s['polygon_px']) for s in old['spaces']]);new_union=__import__('shapely').union_all([Polygon(s['polygon_px']) for s in d['spaces']])
assert old_union.symmetric_difference(new_union).area<.001
name=d['image']['file'];sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
assert sha(P/name)==sha(H/'修改前备份'/name)
assert len(list(P.iterdir()))==4
qs=json.loads((H/'核对号映射.json').read_text());assert [q['number'] for q in qs]==[f'{i:02d}' for i in range(1,15)]

# Render final files, not intermediate versions.
for source,out in [(H/'连通核对总图.svg',H/'连通核对总图.png'),(P/'标注.svg',H/'标注_全图.png')]:
 doc=pymupdf.open(source);doc[0].get_pixmap(matrix=pymupdf.Matrix(1,1)).save(out)
im=Image.open(H/'连通核对总图.png');im.resize((1674,1608)).save(H/'核对总图_预览.png')
for name,b in [('01-06',(0,560,4464,1600)),('07-09',(0,2420,4464,2960)),('10-14',(0,2860,4464,3800))]:im.crop(b).save(H/f'核对局部_{name}.png')
im=Image.open(H/'标注_全图.png');im.resize((1532,2124)).save(H/'标注_全图预览.png')
doc=pymupdf.open(P/'标注.svg');page=doc[0]
for name,b in [('儿科药房',(1700,370,2410,1630)),('北住院',(420,880,1620,1270)),('放射北',(570,1530,1620,1960)),('放射南',(570,1950,1620,2675)),('南住院',(420,2780,1620,3150)),('输液急诊',(1725,2430,2410,3650))]:
 page.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5),clip=pymupdf.Rect(b[0],b[1]+125,b[2],b[3]+125)).save(H/f'标注_密集局部_{name}.png')
md=(P/'标注说明.md').read_text()
for link in re.findall(r'\]\(([^)]+)\)',md):assert (P/link).exists(),link
ops=[o for r in d['relations'] for o in r.get('openings',[])];located=sum(bool(r.get('openings')) for r in d['relations'])
report=dict(spaces=len(by),names_retained=True,original_sha256=sha(P/d['image']['file']),relations=dict(Counter(r['type'] for r in d['relations'])),openings=len(ops),opening_kinds=dict(Counter(o['kind'] for o in ops)),located_relations=located,conceptual_access=sum(r['type']=='access' and not r.get('openings') for r in d['relations']),max_opening_distance_to_both_boundaries_px=round(max_distance,2),all_visible_labels_match=True,name_labels_covering_points=rect_points,total_footprint_preserved=True,review_groups=len(qs),md_links_valid=True,files=[x.name for x in P.iterdir()])
(H/'独立核验结果.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
