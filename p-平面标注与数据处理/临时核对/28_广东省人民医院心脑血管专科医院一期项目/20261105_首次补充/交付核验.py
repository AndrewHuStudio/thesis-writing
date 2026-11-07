from pathlib import Path
import xml.etree.ElementTree as E,json,re,hashlib,shutil
import pymupdf
from shapely.geometry import Polygon,Point
P=next(Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理/标注试样').glob('28_*'));O=P.parents[1]/'临时核对'/P.name/'20261105_首次补充';NS='{http://www.w3.org/2000/svg}'
tree=E.parse(P/'标注.svg');root=tree.getroot();d=json.loads((P/'annotation.json').read_text())
# PyMuPDF不按paint-order绘制描边文字，给P号加白底并去掉遮字描边。
for g in root.iter(NS+'g'):
 if g.get('data-opening-id'):
  
  for old in list(g.findall(NS+'rect')):g.remove(old)
  t=g.find(NS+'text');x=float(t.get('x'));y=float(t.get('y'));f=float(t.get('font-size'))
  for a in ['stroke','stroke-width','paint-order']:t.attrib.pop(a,None)
  bg=E.Element(NS+'rect',{'x':str(x-1),'y':str(y-f),'width':str(f*2.65),'height':str(f+2),'rx':'1','fill':'white','fill-opacity':'.9'})
  g.insert(list(g).index(t),bg)
E.register_namespace('xlink','http://www.w3.org/1999/xlink');E.register_namespace('',NS[1:-1]);tree.write(P/'标注.svg',encoding='unicode')
ann=pymupdf.open(P/'标注.svg');ann[0].get_pixmap(matrix=pymupdf.Matrix(.55,.55)).save(O/'标注_全图预览.png')
for n,box in [('供应',(140,530,1225,890)),('影像上',(355,1225,1225,1600)),('影像下',(355,1580,1225,1845)),('急诊',(280,2060,1165,2650)),('门诊',(1628,2140,2345,2650))]:
 x0,y0,x1,y1=box;ann[0].get_pixmap(matrix=pymupdf.Matrix(1.6,1.6),clip=pymupdf.Rect(x0,y0+122.2,x1,y1+122.2)).save(O/('标注_'+n+'.png'))
polys={s['id']:Polygon(s['polygon_px']) for s in d['spaces']};out=[]
for r in d['relations']:
 for p in r.get('openings',[]):
  pt=Point(p['position_px']);ds=[round(polys[r[k]].distance(pt),2) for k in ['source','target']]
  if max(ds)>8:out.append([p['id'],r['source'],r['target'],ds])
print('point_distance_audit_over8px',out)
for s in d['spaces']:
 g=next(x for x in root.iter(NS+'g') if x.get('id')==s['id']);txt=''.join(x.text or '' for x in g.findall(NS+'text'));assert s['id'] in txt and s['name'] in txt,(s['id'],txt)
for src,name in [('/tmp/update28.py','本轮数据补充_已执行勿重复.py'),('/tmp/review28.py','生成核对材料.py'),('/tmp/finish28.py','交付核验.py')]:shutil.copy2(src,O/name)
print('visible_svg_labels',len(d['spaces']),'opening_labels',len([g for g in root.iter(NS+'g') if g.get('data-opening-id')]))
