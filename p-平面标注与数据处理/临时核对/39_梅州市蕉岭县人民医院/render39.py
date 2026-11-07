from pathlib import Path
import copy, json, sys, math, xml.etree.ElementTree as ET
import fitz
from PIL import Image
from shapely.geometry import box,Point
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]/'标注试样'/'39_梅州市蕉岭县人民医院'
SKILL=Path('/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts')
sys.path.insert(0,str(SKILL))
import annotation_tools as at
import label39
at.place_label=label39.place
D=json.loads((ROOT/'annotation.json').read_text())
view=copy.deepcopy(D);view['image']=dict(file='原图转正.png',width=3104,height=2424)
for s in view['spaces']:s['polygon_px']=[[y,round(2424-x,3)] for x,y in s['polygon_px']]
for r in view['relations']:
 if r['type']=='entrance':
  x,y=r['position_px'];r['position_px']=[y,2424-x]
 for o in r.get('openings',[]):
  x,y=o['position_px'];o['position_px']=[y,2424-x]
(OUT/'display_annotation.json').write_text(json.dumps(view,ensure_ascii=False,indent=2))
at.render(view,OUT/'display_annotation.json',ROOT/'标注.svg')
p=ROOT/'标注.svg';root=ET.fromstring(p.read_text());ns='{http://www.w3.org/2000/svg}'
# 显示转正，红点仍保存原坐标并显式变换，确保核心JSON与SVG可双向核对。
original={o['id']:o for r in D['relations'] for o in r.get('openings',[])}
root.set('data-coordinate-system','original-image-pixels')
for sg in list(root.iter()):
 if sg.get('id') in label39.ROTATION:
  angle,cx,cy=label39.ROTATION[sg.get('id')]
  lg=ET.Element(ns+'g',{'transform':f'rotate({angle} {cx} {cy})'})
  for child in list(sg):
   if child.tag in (ns+'text',ns+'rect'):
    sg.remove(child);lg.append(child)
  sg.append(lg)
avoid=[]
for sg in root.iter():
 if sg.get('id','').startswith('S') and sg.get('data-space-name'):
  for q in sg.iter(ns+'rect'):
   x,y,w,h=[float(q.get(k)) for k in ['x','y','width','height']];avoid.append(box(x,y,x+w,y+h))
points=[Point(o['position_px']) for r in view['relations'] for o in r.get('openings',[])]
placed=[];pcoll=[]
for g in root.iter():
 if g.get('data-opening-id'):
  o=original[g.get('data-opening-id')]
  for e in list(g):
   if e.tag==ns+'text':
    e.attrib.pop('stroke',None);e.attrib.pop('stroke-width',None);e.attrib.pop('paint-order',None)
    e.set('fill','#b91c1c')
    font=8;e.set('font-size',str(font))
    px=o['position_px'][1];py=2424-o['position_px'][0]
    choices=[];lw=font*2.8;lh=font+2
    for dx,dy in [(6,-6),(6,14),(-lw-6,-6),(-lw-6,14),(-lw/2,-10),(-lw/2,19),(12,4),(-lw-12,4),(6,-18),(6,26)]:
     xx=px+dx;yy=py+dy;b=box(xx-1,yy-font,xx+lw-1,yy+2)
     cost=sum(b.intersection(q).area for q in avoid)*10+sum(b.intersection(q).area for q in placed)*20+sum(max(0,6-b.distance(q))*25 for q in points)
     choices.append((cost,xx,yy,b))
    cost,x,y,b=min(choices,key=lambda v:v[0])
    if cost>0:
     found=False
     for radius in [24,32,40,48,64,80,96,112,128,160]:
      for angle in [0,45,90,135,180,225,270,315]:
       xx=px+radius*math.cos(math.radians(angle))-lw/2;yy=py+radius*math.sin(math.radians(angle))+font/2
       bb=box(xx-1,yy-font,xx+lw-1,yy+2)
       if any(bb.intersects(q) for q in avoid+placed) or any(bb.distance(q)<6 for q in points):continue
       cost,x,y,b=0,xx,yy,bb;found=True;break
      if found:break
    placed.append(b)
    if b.distance(Point(px,py))>14:
     lead=ET.Element(ns+'line',{'x1':str(px),'y1':str(py),'x2':str(x+lw/2),'y2':str(y-font/2),'stroke':'#b91c1c','stroke-width':'.7'})
     g.insert(1,lead)
    if cost>0:pcoll.append({'id':o['id'],'collision_score':cost})
    e.set('x',str(x));e.set('y',str(y))
    bg=ET.Element(ns+'rect',dict(x=str(x-1),y=str(y-font),width=str(font*2.8),height=str(font+2),fill='white',**{'fill-opacity':'.90'}))
    g.insert(list(g).index(e),bg)
   if e.tag==ns+'circle':
    e.set('cx',str(o['position_px'][0]));e.set('cy',str(o['position_px'][1]));e.set('transform','matrix(0 -1 1 0 0 2424)')
 for e in [g]:
  if e.get('font-family'):e.set('font-family','STHeiti, Hiragino Sans GB, Arial, sans-serif')
  if e.tag==ns+'text' and e.text=='门诊平面结构化标注':e.text='39 梅州市蕉岭县人民医院 · 首层标注草稿'
ET.ElementTree(root).write(p,encoding='unicode')
doc=fitz.open(p);pix=doc[0].get_pixmap(matrix=fitz.Matrix(1,1));pix.save(OUT/'SVG_完整检查.png')
im=Image.open(OUT/'SVG_完整检查.png');im.thumbnail((1700,1700));im.save(OUT/'SVG_完整预览.png')
full=Image.open(OUT/'SVG_完整检查.png')
for k,b in {'会议':(175,500,790,1100),'后勤':(765,550,1730,1025),'急诊':(170,1065,785,1820),'医技':(765,970,1445,1370),'超声药房':(765,1355,1440,1815),'入口儿科':(315,1805,1330,2245)}.items():
 full.crop(b).resize(((b[2]-b[0])*2,(b[3]-b[1])*2)).save(OUT/f'SVG_局部_{k}.png')
(OUT/'SVG_门洞文字碰撞.json').write_text(json.dumps(pcoll,ensure_ascii=False,indent=2))
(OUT/'SVG_标签轮廓检查.json').write_text(json.dumps(label39.LABEL_AUDIT,ensure_ascii=False,indent=2))
print('SVG及转正预览已生成；标签越界', [s for s in label39.LABEL_AUDIT if not s['inside']])
