from pathlib import Path
from collections import Counter
import json,re,hashlib,xml.etree.ElementTree as ET
from shapely.geometry import Polygon,Point,box,LineString
import pymupdf
R=Path(__file__).resolve().parent;P=R.parent.parent/'标注试样'/R.name;D=json.loads((P/'annotation.json').read_text());polys={s['id']:Polygon(s['polygon_px']) for s in D['spaces']};ns={'s':'http://www.w3.org/2000/svg'}
# 仅修正两处可见标签排版，保持几何和门洞数据不变。
ET.register_namespace('','http://www.w3.org/2000/svg');ET.register_namespace('xlink','http://www.w3.org/1999/xlink')
tree=ET.parse(P/'标注.svg');root=tree.getroot()
for sn in ['S016','S078']:
 g=root.find('.//s:g[@id="'+sn+'"]',ns);rect=g.find('s:rect',ns);a=rect.attrib;x,y,w,h=[float(a[k]) for k in ['x','y','width','height']]
 if sn=='S016':dx,dy=989-x,860-y;factor=1
 else:dx,dy=0,0;factor=.97 if h>57 else 1
 cx,cy=x+w/2,y+h/2
 for el in [rect]+g.findall('s:text',ns):
  for attr,c in [('x',cx),('y',cy)]:
   if attr in el.attrib:el.set(attr,str(c+(float(el.get(attr))-c)*factor+(dx if attr=='x' else dy)))
  for attr in ['width','height','font-size']:
   if attr in el.attrib:el.set(attr,str(float(el.get(attr))*factor))
tree.write(P/'标注.svg',encoding='unicode')
labels_bad=[]
for s in D['spaces']:
 g=root.find('.//s:g[@id="'+s['id']+'"]',ns);a=g.find('s:rect',ns).attrib;x,y,w,h=[float(a[k]) for k in ['x','y','width','height']]
 if not polys[s['id']].covers(box(x,y,x+w,y+h)):labels_bad.append(s['id'])
assert not labels_bad,labels_bad
# 历史映射、房内定位和引线的独立几何检查。
Q=json.loads((R/'固定核对映射.json').read_text());L=json.loads((R/'review_layout.json').read_text())
assert len(Q)==len(L)==116
assert {q['id'] for q in Q}=={s['id'] for s in D['spaces'] if s['type']=='unknown'}
assert [(q['number'],q['id']) for q in Q]==[(q['number'],q['id']) for q in L]
lines=[LineString(q['leader']) for q in L]
cross=[(L[i]['number'],L[j]['number']) for i in range(len(L)) for j in range(i) if lines[i].intersects(lines[j])]
assert not cross,cross
for q in L:assert Polygon(q['canvas_polygon']).covers(Point(q['anchor'][0]*10,q['anchor'][1]*10)),q['number']
md=(P/'标注说明.md').read_text();rows=re.findall(r'^\| (\d+) \| (S\d+) \|.*\| (\d+) \|$',md,re.M)
assert len(rows)==116 and all(a==c for a,b,c in rows)
assert [(a,b) for a,b,c in rows]==[(q['number'],q['id']) for q in Q]
links=re.findall(r'!\[[^]]*\]\(([^)]+)\)',md);missing=[f for f in links if not (P/f).exists()];assert not missing,missing
sha=hashlib.sha256((P/D['image']['file']).read_bytes()).hexdigest();oldsha=hashlib.sha256((R/'20261107_开始续作前备份'/D['image']['file']).read_bytes()).hexdigest();assert sha==oldsha
openings=[(r,o) for r in D['relations'] for o in r.get('openings',[])];geometry=[];unrelated=[]
for r,o in openings:
 p=Point(o['position_px']);a,b=r['source'],r['target'];dist=max(polys[a].distance(p),polys[b].distance(p));geometry.append(dist)
 for sn,poly in polys.items():
  if sn not in [a,b] and poly.contains(p) and poly.boundary.distance(p)>.1:unrelated.append((o['id'],sn))
assert max(geometry)<4.5 and not unrelated,(max(geometry),unrelated)
stat={'spaces':len(D['spaces']),'relations':len(D['relations']),'relation_types':dict(Counter(r['type'] for r in D['relations'])),'openings':len(openings),'opening_kinds':dict(Counter(o['kind'] for r,o in openings)),'relations_with_openings':sum(bool(r.get('openings')) for r in D['relations']),'unlocated_access':sum(r['type']=='access' and not r.get('openings') for r in D['relations']),'unknown_names':len(Q),'image_sha256':sha,'source_unchanged':True,'mapping_preserved':True,'leader_crossings':len(cross),'all_labels_inside':True,'image_links_valid':len(links),'max_opening_polygon_distance_px':round(max(geometry),3),'unrelated_space_openings':unrelated,'final_directory_files':sorted(f.name for f in P.iterdir() if f.is_file()),'retired_ids':['S023','R025','E10']}
(R/'本轮一致性检查.json').write_text(json.dumps(stat,ensure_ascii=False,indent=2)+'\n')
svg=pymupdf.open(P/'标注.svg');pdf=pymupdf.open('pdf',svg.convert_to_pdf());pdf[0].get_pixmap(matrix=pymupdf.Matrix(.65,.65)).save(R/'SVG全图目检.png')
print(json.dumps(stat,ensure_ascii=False,indent=2))
