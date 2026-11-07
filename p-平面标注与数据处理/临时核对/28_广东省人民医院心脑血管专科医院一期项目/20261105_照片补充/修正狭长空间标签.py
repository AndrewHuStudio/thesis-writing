from pathlib import Path
import json,xml.etree.ElementTree as E
from shapely.geometry import Polygon,box,Point
import pymupdf
P=next(Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理/标注试样').glob('28_*'));O=P.parents[1]/'临时核对'/P.name/'20261105_照片补充';NS='{http://www.w3.org/2000/svg}'
d=json.loads((P/'annotation.json').read_text());by={s['id']:s for s in d['spaces']};types=json.loads(Path('/Users/hushili/.codex/skills/outpatient-plan-annotation/references/space-types.json').read_text());tree=E.parse(P/'标注.svg');root=tree.getroot();fixed=[]
def width(s,f):return sum(f*(.58 if ord(c)<128 else 1) for c in s)
def wrap(s,f,w):
 rows=['']
 for c in s:
  if rows[-1] and width(rows[-1]+c,f)>w:rows.append('')
  rows[-1]+=c
 return rows
for sid,s in by.items():
 g=next(x for x in root.iter(NS+'g') if x.get('id')==sid);rect=g.find(NS+'rect');p=Polygon(s['polygon_px'])
 if rect is None:continue
 x,y,w,h=[float(rect.get(a)) for a in ['x','y','width','height']]
 if p.covers(box(x,y,x+w,y+h)):continue
 color=rect.get('stroke');xmin,ymin,xmax,ymax=p.bounds;q=p.representative_point();centers=[(q.x,q.y)]
 if p.contains(p.centroid):centers.append((p.centroid.x,p.centroid.y))
 for a in [.25,.4,.5,.6,.75]:
  for b in [.25,.4,.5,.6,.75]:
   qx=xmin+(xmax-xmin)*a;qy=ymin+(ymax-ymin)*b
   if p.contains(Point(qx,qy)):centers.append((qx,qy))
 best=None
 for f in [7,6.5,6,5.5,5,4.5,4,3.5]:
  for w0 in [min(180,(xmax-xmin-3)*ratio) for ratio in [1,.8,.65,.5,.4,.3]]:
   if w0<7:continue
   for combined in [True,False]:
    name=s['name'];category='〔'+types[s['type']]+'〕';lines=wrap(sid+' '+name,f,w0-4) if combined else [sid]+wrap(name,f,w0-4)
    lines+=wrap(category,f,w0-4);lw=max(width(l,f) for l in lines)+4;lh=len(lines)*(f+1)+3
    for cx,cy in centers:
     r=box(cx-lw/2,cy-lh/2,cx+lw/2,cy+lh/2)
     if p.covers(r):best=(cx-lw/2,cy-lh/2,lw,lh,f,lines);break
    if best:break
   if best:break
  if best:break
 if best is None:raise RuntimeError('No interior label '+sid)
 for child in list(g):
  if child.tag in [NS+'rect',NS+'text']:g.remove(child)
 x,y,w,h,f,lines=best;g.append(E.Element(NS+'rect',{'x':str(x),'y':str(y),'width':str(w),'height':str(h),'rx':'1','fill':'#fff7df' if s['type']=='unknown' else 'white','fill-opacity':'.95','stroke':color,'stroke-width':'.6'}))
 for i,l in enumerate(lines):
  t=E.Element(NS+'text',{'x':str(x+2),'y':str(y+f+1+i*(f+1)),'font-size':str(f),'font-family':'Arial, PingFang SC, Microsoft YaHei, sans-serif','fill':color,'font-weight':'700'});t.text=l;g.append(t)
 fixed.append(sid)
# 为P号用白底红字，避免预览器描边盖字。
for g in root.iter(NS+'g'):
 if not g.get('data-opening-id'):continue
 t=g.find(NS+'text');x=float(t.get('x'));y=float(t.get('y'));f=float(t.get('font-size'))
 for k in ['stroke','stroke-width','paint-order']:t.attrib.pop(k,None)
 for old in g.findall(NS+'rect'):g.remove(old)
 g.insert(list(g).index(t),E.Element(NS+'rect',{'x':str(x-1),'y':str(y-f),'width':str(f*2.65),'height':str(f+2),'fill':'white','fill-opacity':'.9'}))
E.register_namespace('',NS[1:-1]);E.register_namespace('xlink','http://www.w3.org/1999/xlink');tree.write(P/'标注.svg',encoding='unicode')
for sid in by:
 g=next(x for x in root.iter(NS+'g') if x.get('id')==sid);t=''.join(x.text or '' for x in g.findall(NS+'text'));assert sid in t and by[sid]['name'] in t
 rect=g.find(NS+'rect');x,y,w,h=[float(rect.get(a)) for a in ['x','y','width','height']];assert Polygon(by[sid]['polygon_px']).covers(box(x,y,x+w,y+h))
ann=pymupdf.open(P/'标注.svg');ann[0].get_pixmap(matrix=pymupdf.Matrix(.55,.55)).save(O/'标注_全图预览.png')
for name,b in [('供应',(140,530,1225,890)),('影像上',(355,1225,1225,1600)),('急诊',(280,2060,1165,2650)),('门诊',(1628,2140,2345,2650))]:
 x0,y0,x1,y1=b;ann[0].get_pixmap(matrix=pymupdf.Matrix(2,2),clip=pymupdf.Rect(x0,y0+122.2,x1,y1+122.2)).save(O/('标注_'+name+'.png'))
(O/'标签排版核验.json').write_text(json.dumps(dict(fitted=fixed,all_label_panels_inside=True,visible_space_labels=len(by)),ensure_ascii=False,indent=2)+'\n')
print('fitted labels',len(fixed),'all 206 inside polygons')
