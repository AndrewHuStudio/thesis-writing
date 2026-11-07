from pathlib import Path
import json
import xml.etree.ElementTree as ET
from shapely.geometry import box

WORK=Path(__file__).resolve().parent
ROOT=WORK.parents[3]
SAMPLE=ROOT/'p-平面标注与数据处理/标注试样'/WORK.parent.name
NS='http://www.w3.org/2000/svg'
ET.register_namespace('',NS)
ET.register_namespace('xlink','http://www.w3.org/1999/xlink')
path=SAMPLE/'标注.svg'
tree=ET.parse(path)
groups=tree.findall('.//{'+NS+'}g')
obstacles=[]
for g in groups:
    if (g.get('id') or '').startswith(('S','E')):
        for r in g.findall('{'+NS+'}rect'):
            x,y,w,h=[float(r.get(k)) for k in ['x','y','width','height']]
            obstacles.append(box(x,y,x+w,y+h))
labels=[]
placed=[]
for g in groups:
    oid=g.get('data-opening-id')
    if not oid:continue
    circle=g.find('{'+NS+'}circle')
    x=float(circle.get('cx'));y=float(circle.get('cy'))
    text=g.find('{'+NS+'}text')
    for k in ['stroke','stroke-width','paint-order']:text.attrib.pop(k,None)
    font=8.5;width=4*font*.6+3;height=font+3
    offsets=[(5,-height-3),(5,3),(-width-5,-height-3),(-width-5,3),
             (5,-height-15),(5,15),(-width-5,-height-15),(-width-5,15)]
    choices=[]
    for i,(dx,dy) in enumerate(offsets):
        rect=box(x+dx,y+dy,x+dx+width,y+dy+height)
        score=sum(rect.intersection(o).area for o in obstacles+labels)*100+i
        choices.append((score,x+dx,y+dy,rect))
    score,left,top,rect=min(choices,key=lambda v:v[0])
    bg=ET.Element('{'+NS+'}rect',{'x':str(left),'y':str(top),'width':str(width),
        'height':str(height),'fill':'white','fill-opacity':'.94','rx':'1'})
    g.insert(list(g).index(text),bg)
    text.set('x',str(left+1.5));text.set('y',str(top+font))
    text.set('font-size',str(font));text.set('font-weight','700');text.set('fill','#b91c1c')
    labels.append(rect)
    placed.append({'id':oid,'x':left,'y':top,'overlap_score':score//100})
tree.write(path,encoding='unicode')
(WORK/'P编号文字排版.json').write_text(json.dumps(placed,ensure_ascii=False,indent=2)+'\n')
print('P labels',len(placed),'requiring visual review',sum(p['overlap_score']>0 for p in placed))
