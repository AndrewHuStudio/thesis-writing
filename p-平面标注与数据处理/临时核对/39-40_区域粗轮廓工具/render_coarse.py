from coarse_common import Plan,SKILL
from pathlib import Path
import copy,json,sys,math,xml.etree.ElementTree as ET
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import Point,box,Polygon
from shapely.ops import unary_union
import pymupdf
import annotation_tools as at
import coarse_labels
NS='{http://www.w3.org/2000/svg}'
COLORS=['#2563eb','#0f766e','#a21caf','#b45309','#0369a1','#be123c','#7c3aed','#15803d']
def run(n):
 p=Plan(n);p.d=json.loads((p.root/'annotation.json').read_text());p.st=json.loads((p.review/'review_state.json').read_text())
 view=copy.deepcopy(p.d);view['image']=dict(file='../判读原图.png',width=3104 if n==39 else 2192,height=2424 if n==39 else 3316)
 for s in view['spaces']:s['polygon_px']=[p.display(xy) for xy in s['polygon_px']]
 for r in view['relations']:
  if r['type']=='entrance':r['position_px']=p.display(r['position_px'])
  for o in r.get('openings',[]):o['position_px']=p.display(o['position_px'])
 st=copy.deepcopy(p.st);st.pop('image_signature',None)
 for i,z in enumerate(st['regions']):
  z['color']=COLORS[i%len(COLORS)]
  label=[1800,430+39*i] if n==39 else [1230+390*(i//17),1400+32*(i%17)]
  orig=p.st['regions'][i];orig['color']=z['color'];orig['label_px']=p.orig(*label)
  z['polygons_px']=[[p.display(xy) for xy in part] for part in z['polygons_px']];z['label_px']=label
 (p.review/'review_state.json').write_text(json.dumps(p.st,ensure_ascii=False,indent=2)+'\n')
 (p.out/'display').mkdir(exist_ok=True)
 (p.out/'display/annotation.json').write_text(json.dumps(view,ensure_ascii=False,indent=2))
 (p.out/'display_review_state.json').write_text(json.dumps(st,ensure_ascii=False,indent=2))
 coarse_labels.PLAN_N=n;coarse_labels.LABEL_AUDIT.clear();coarse_labels.ROTATION.clear();at.place_label=coarse_labels.place
 at.render(view,p.out/'display/annotation.json',p.root/'标注.svg',p.out/'display_review_state.json')
 tree=ET.parse(p.root/'标注.svg');root=tree.getroot()
 for sg in list(root.iter()):
  if sg.get('id') in coarse_labels.ROTATION:
   angle,cx,cy=coarse_labels.ROTATION[sg.get('id')];lg=ET.Element(NS+'g',{'transform':f'rotate({angle} {cx} {cy})'})
   for child in list(sg):
    if child.tag in (NS+'text',NS+'rect'):sg.remove(child);lg.append(child)
   sg.append(lg)
  if sg.get('data-region-id'):
   z=next(z for z in p.st['regions'] if z['id']==sg.get('data-region-id'))
   for i,q in enumerate([c for c in sg if c.tag==NS+'polygon']):
    q.set('points',' '.join(f'{x},{y}' for x,y in z['polygons_px'][i]))
    if n==39:q.set('transform','matrix(0 -1 1 0 0 2424)')
    q.set('stroke','none')
   union=unary_union([Polygon(part) for part in z['polygons_px']]);geoms=[union] if union.geom_type=='Polygon' else list(union.geoms)
   path=[]
   for geom in geoms:
    for ring in [geom.exterior]+list(geom.interiors):
     pts=list(ring.coords);path.append('M '+' L '.join(f'{x} {y}' for x,y in pts)+' Z')
   shape=ET.SubElement(sg,NS+'path',{'d':' '.join(path),'fill':'none','stroke':z['color'],'stroke-width':'4','stroke-opacity':'.85','data-outline-union':'true'})
   if n==39:shape.set('transform','matrix(0 -1 1 0 0 2424)')
   for q in sg:
    if q.tag==NS+'text':q.set('font-size','14')
 # 开口编号避让空间标签；红点仍用原始坐标保存，显示时显式转正。
 original={o['id']:o for r in p.d['relations'] for o in r.get('openings',[])}
 avoid=[]
 for sg in root.iter():
  if sg.get('data-space-name'):
   for q in sg.iter(NS+'rect'):
    x,y,w,h=[float(q.get(k)) for k in ['x','y','width','height']];avoid.append(box(x,y,x+w,y+h))
 points=[Point(o['position_px']) for r in view['relations'] for o in r.get('openings',[])];placed=[];collisions=[]
 for sg in root.iter():
  if sg.get('data-opening-id'):
   oid=sg.get('data-opening-id');o=original[oid];px,py=p.display(o['position_px'])
   for oldbg in list(sg):
    if oldbg.tag==NS+'rect':sg.remove(oldbg)
   for q in list(sg):
    if q.tag==NS+'circle' and n==39:
     q.set('cx',str(o['position_px'][0]));q.set('cy',str(o['position_px'][1]));q.set('transform','matrix(0 -1 1 0 0 2424)')
    if q.tag!=NS+'text':continue
    for a in ['stroke','stroke-width','paint-order']:q.attrib.pop(a,None)
    q.set('fill','#b91c1c');font=7;lw=font*2.8;lh=font+2;q.set('font-size',str(font))
    found=None
    for radius in [10,18,26,36,48,64,80,112,160]:
     for angle in [315,45,225,135,0,90,180,270]:
      xx=px+radius*math.cos(math.radians(angle))-lw/2;yy=py+radius*math.sin(math.radians(angle))+font/2;b=box(xx-1,yy-font,xx+lw-1,yy+2)
      if any(b.intersects(a) for a in avoid+placed) or any(b.distance(a)<5 for a in points):continue
      found=(xx,yy,b);break
     if found:break
    if found is None:found=(px+6,py-6,box(px+5,py-13,px+lw+5,py-4));collisions.append(oid)
    x,y,b=found;placed.append(b);q.set('x',str(x));q.set('y',str(y))
    if b.distance(Point(px,py))>15:
     sg.insert(1,ET.Element(NS+'line',{'x1':str(px),'y1':str(py),'x2':str(x+lw/2),'y2':str(y-font/2),'stroke':'#b91c1c','stroke-width':'.6'}))
    sg.insert(list(sg).index(q),ET.Element(NS+'rect',{'x':str(x-1),'y':str(y-font),'width':str(lw),'height':str(lh),'fill':'white','fill-opacity':'.9'}))
  if sg.tag==NS+'text':
   sg.set('font-family','STHeiti, Hiragino Sans GB, Arial, sans-serif')
   if sg.text=='门诊平面结构化标注':sg.text=f'{n}号｜逐空间粗轮廓＋区域概览'
 tree.write(p.root/'标注.svg',encoding='unicode')
 (p.out/'标签审计.json').write_text(json.dumps({'labels':coarse_labels.LABEL_AUDIT,'opening_label_conflicts':collisions},ensure_ascii=False,indent=2))
 doc=pymupdf.open(p.root/'标注.svg');pix=doc[0].get_pixmap();pix.save(p.out/'正式SVG全图.png')
 im=Image.open(p.out/'正式SVG全图.png');im.thumbnail((1500,1700));im.save(p.out/'正式SVG预览.png')
 # 区域概览只画轮廓，灰色线为逐间空间，展示范围不覆盖外部空白。
 src=Image.open(p.out/'判读原图.png').convert('RGB');draw=ImageDraw.Draw(src)
 for s in view['spaces']:
  pts=[tuple(q) for q in s['polygon_px']];draw.line(pts+[pts[0]],fill='#b1b8c4',width=1)
 font=ImageFont.truetype('/System/Library/Fonts/STHeiti Medium.ttc',16)
 for z in st['regions']:
  union=unary_union([Polygon(part) for part in z['polygons_px']]);geoms=[union] if union.geom_type=='Polygon' else list(union.geoms)
  for geom in geoms:
   for ring in [geom.exterior]+list(geom.interiors):
    pts=[tuple(q) for q in ring.coords];draw.line(pts,fill=z['color'],width=4)
  draw.text(tuple(z['label_px']),z['id']+' '+z['name'],font=font,fill=z['color'])
 src.save(p.out/'区域轮廓概览.png');src.thumbnail((1500,1700));src.save(p.out/'区域轮廓概览_预览.png')
 # 图面密集局部便于人工核验。
 full=Image.open(p.out/'正式SVG全图.png');head=min(125,view['image']['width']*.05)
 crops={39:{'急诊':(175,1130,680,1690),'医技':(830,885,1435,1250),'超声':(770,1335,1435,1700),'儿科':(770,1900,1335,2110)},40:{'发热':(1300,180,2045,560),'影像':(200,1480,960,1910),'急诊':(1260,2180,1810,2730),'儿科':(235,2520,770,2730)}}
 for title,(x0,y0,x1,y1) in crops[n].items():full.crop((x0,y0+head,x1,y1+head)).resize(((x1-x0)*2,(y1-y0)*2)).save(p.out/f'正式SVG局部_{title}.png')
 print(n,'rendered',len(p.d['spaces']),'label failures',[i for i in coarse_labels.LABEL_AUDIT if not i['inside']],'P label conflicts',collisions)
for arg in sys.argv[1:]:run(int(arg))
