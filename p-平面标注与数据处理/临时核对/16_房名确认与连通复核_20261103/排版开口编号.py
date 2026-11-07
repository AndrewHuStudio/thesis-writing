"""Make opening labels readable in SVG and raster renderers without hiding room labels."""
from pathlib import Path
import xml.etree.ElementTree as ET
from shapely.geometry import box
OUT=Path(__file__).resolve().parent
PATH=OUT/'待核验成果/标注.svg'
NS='{http://www.w3.org/2000/svg}'
ET.register_namespace('','http://www.w3.org/2000/svg')
ET.register_namespace('xlink','http://www.w3.org/1999/xlink')
tree=ET.parse(PATH);root=tree.getroot()
room_rects=[]
for group in root.iter(NS+'g'):
 if group.get('id','').startswith('S'):
  for r in group.findall(NS+'rect'):
   x,y,w,h=[float(r.get(k)) for k in ['x','y','width','height']]
   room_rects.append(box(x-1,y-1,x+w+1,y+h+1))
point_rects=[]
for g in root.iter(NS+'g'):
 if g.get('data-opening-id'):
  c=g.find(NS+'circle');px,py=float(c.get('cx')),float(c.get('cy'))
  point_rects.append(box(px-6,py-6,px+6,py+6))
used=[];collisions=[]
for group in root.iter(NS+'g'):
 oid=group.get('data-opening-id')
 if not oid:continue
 point=group.find(NS+'circle');text=group.find(NS+'text')
 x,y=float(point.get('cx')),float(point.get('cy'))
 size=8;w=25;h=11
 candidates=[]
 for gap in [8,15,25,35,50,70]:
  for dx,dy in [(gap,-gap-h),(-gap-w,-gap-h),(gap,gap),(-gap-w,gap),
                (gap,-h/2),(-gap-w,-h/2),(-w/2,-gap-h),(-w/2,gap)]:
   b=box(x+dx,y+dy,x+dx+w,y+dy+h)
   area=sum(b.intersection(r).area for r in room_rects)
   area+=sum(b.intersection(r).area for r in used)*2
   area+=sum(b.intersection(r).area for r in point_rects)*5
   score=area*100+gap+abs(dx)*.01
   candidates.append((score,b,area))
 _,b,area=min(candidates,key=lambda t:t[0]);used.append(b)
 if area>0:collisions.append((oid,area))
 x0,y0,x1,y1=b.bounds
 bg=ET.Element(NS+'rect',dict(x=str(x0),y=str(y0),width=str(w),height=str(h),rx='1',fill='white',**{'fill-opacity':'.96'}))
 group.insert(list(group).index(text),bg)
 text.set('x',str(x0+2));text.set('y',str(y0+8.5));text.set('font-size',str(size))
 text.set('fill','#a51b1b');text.set('stroke','none');text.attrib.pop('stroke-width',None);text.attrib.pop('paint-order',None)
tree.write(PATH,encoding='utf-8',xml_declaration=True)
print('opening labels',len(used),'room-label overlaps',collisions)
