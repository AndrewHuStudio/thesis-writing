from pathlib import Path
import xml.etree.ElementTree as E,json,math
from shapely.geometry import box,Point,Polygon
P=Path(__file__).resolve().parent; f=P/'待核验成果/标注.svg';tree=E.parse(f);root=tree.getroot();NS='http://www.w3.org/2000/svg';tag=lambda s:'{'+NS+'}'+s
E.register_namespace('',NS);E.register_namespace('xlink','http://www.w3.org/1999/xlink')
d=json.loads((P/'待核验成果/annotation.json').read_text());polys={s['id']:Polygon(s['polygon_px']) for s in d['spaces']};plan=root.find(f".//{tag('g')}[@id='plan']")
root.find(tag('text')).text='06 鹿邑县第一人民医院整体迁建项目｜首层平面标注'
root.findall(tag('text'))[1].text='290个具名空间；275个开口红点；名称已齐，连通性仍有L01—L10待确认'
root.findall(tag('text'))[1].set('fill','#b45309')
groups={};bounds={};dots=[]
for g in list(plan):
 sid=g.get('id','');rect=g.find(tag('rect'))
 if sid in polys and rect is not None:
  x,y,w,h=[float(rect.get(k)) for k in ('x','y','width','height')];groups[sid]=(g,x,y,w,h);bounds[sid]=box(x,y,x+w,y+h)
 if g.get('data-opening-id'):
  c=g.find(tag('circle'));dots.append(Point(float(c.get('cx')),float(c.get('cy'))).buffer(float(c.get('r'))+1.8))
changes=[]
for sid,(g,x,y,w,h) in groups.items():
 if not any(bounds[sid].intersects(q) for q in dots):continue
 poly=polys[sid];cx,cy=x+w/2,y+h/2;found=None
 for scale in [1,.9,.8]:
  ww,hh=w*scale,h*scale
  for outside in [False,True]:
   if outside and scale!=.8:continue
   candidates=[(cx,cy)]
   for radius in [5,10,15,20,30,45,65,90,120]:
    candidates.extend((cx+radius*math.cos(a*math.pi/8),cy+radius*math.sin(a*math.pi/8)) for a in range(16))
   for xx,yy in candidates:
    b=box(xx-ww/2,yy-hh/2,xx+ww/2,yy+hh/2)
    if not outside and not poly.covers(b):continue
    if outside and poly.covers(b):continue
    if any(b.intersects(q) for q in dots):continue
    if any(k!=sid and b.buffer(2).intersects(v) for k,v in bounds.items()):continue
    found=(xx,yy,scale,b,outside);break
   if found:break
  if found:break
 if found:
  xx,yy,scale,b,outside=found;lab=E.Element(tag('g'),{'data-label-for':sid,'transform':f'translate({xx} {yy}) scale({scale}) translate({-cx} {-cy})'})
  for e in list(g):
   if e.tag in (tag('rect'),tag('text')):g.remove(e);lab.append(e)
  if outside:
   a=poly.representative_point();g.append(E.Element(tag('line'),{'x1':str(a.x),'y1':str(a.y),'x2':str(xx),'y2':str(yy),'stroke':'#64748b','stroke-width':'1','data-label-leader':sid}))
  g.append(lab);bounds[sid]=b;changes.append(sid)
# P号标签避开名称牌和其他P号；只移动文字，点位不变。
used=[]
for g in list(plan):
 if not g.get('data-opening-id'):continue
 t=g.find(tag('text'));c=g.find(tag('circle'));px,py=float(c.get('cx')),float(c.get('cy'));fs=float(t.get('font-size'));w=len(t.text)*fs*.6
 choices=[(8,-8),(-w-8,-8),(8,fs+9),(-w-8,fs+9),(12,-19),(-w-12,-19),(12,fs+21),(-w-12,fs+21)]
 candidates=[]
 for dx,dy in choices:
  xx,yy=px+dx,py+dy;b=box(xx-1,yy-fs-1,xx+w+1,yy+2)
  cost=sum(b.intersection(v).area for v in bounds.values())*2+sum(b.intersection(v).area for v in used)*4
  candidates.append((cost,xx,yy,b))
 _,xx,yy,b=min(candidates,key=lambda t:t[0]);t.set('x',str(xx));t.set('y',str(yy));used.append(b)
tree.write(f,encoding='unicode');(P/'标签避让记录.json').write_text(json.dumps({'moved_space_labels':changes,'opening_coordinates_unchanged':True},ensure_ascii=False,indent=2))
print('moved',len(changes),changes)
