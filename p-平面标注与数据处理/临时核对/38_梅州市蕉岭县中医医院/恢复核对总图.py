from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
import json,heapq,time,math
import numpy as np
TMP=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理/临时核对/38_梅州市蕉岭县中医医院')
ROOT=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理/标注试样/38_梅州市蕉岭县中医医院')
qs=json.loads((TMP/'固定核对映射.json').read_text())
W,H=8000,7800;S=2;OX=1556;OY=550;STEP=10
GW,GH=W//STEP,H//STEP
fontpath='/System/Library/Fonts/Supplemental/Arial Unicode.ttf'
fonts={s:ImageFont.truetype(fontpath,s) for s in [22,24,26,28,32,36,40,56]}
colors=['#9b2778','#1c6eae','#b05b08','#087b6b']
# 编号沿用相邻片区顺序，同组标签在其边栏连续排列。
counts={g:sum(q['group']==g for q in qs) for g in range(4)}
med=[q for q in qs if q['group']==3]
for q in qs:
 q['side']='left' if q['group']==1 or (q['group']==3 and med.index(q)<24) else 'right'
for side in ['left','right']:
 arr=[q for q in qs if q['side']==side]
 for j,q in enumerate(arr):q['label_y']=250+j*112
# 图上坐标映射及 anchor；中心仅作核对定位，不记录为门位。
for q in qs:
 poly=[(OX+S*x,OY+S*y) for x,y in q['polygon_px']]
 q['canvas_polygon']=poly
 xx=sum(x for x,y in poly)/len(poly);yy=sum(y for x,y in poly)/len(poly)
 q['anchor']=(round(xx/STEP),round(yy/STEP))
 q['port']=(149 if q['side']=='left' else 651,round((q['label_y']+48)/STEP))
# 连续几何布线：在原图、标签之间的自由平面三角网中寻找引线，避免栅格将窄缝错误封闭。
from shapely.geometry import Polygon,Point,LineString,box
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles,STRtree
from collections import deque
cards=[]
for q in qs:
 x1=145 if q['side']=='left' else 6600;x2=1400 if q['side']=='left' else 7855;y=q['label_y']
 cards.append(box(x1,y,x2,y+100))
card_obstacles=unary_union(cards)
outer=box(20,20,W-20,H-20)
completed=[]
# 先布置较小医技房间，保留其狭窄定位范围；编号和边栏顺序不随布线次序改变。
def pa(q):return Polygon(q['canvas_polygon']).area
route_order=[q for q in qs if q['group']!=3]+sorted([q for q in qs if q['group']==3],key=pa)
for idx,q in enumerate(route_order):
 roompoly=Polygon(q['canvas_polygon']);center=roompoly.representative_point()
 end_x=1400.0 if q['side']=='left' else 6600.0
 ends=[Point(end_x,q['label_y']+50+dy) for dy in [0,-10,10,-20,20,-30,30,-45,45]]
 xlo,xhi=(145,1400) if q['side']=='left' else (6600,7855)
 ends += [Point(xlo+(xhi-xlo)*fx,q['label_y']+dy) for dy in [0,100] for fx in [.1,.5,.9]]
 ends += [Point(xlo if q['side']=='left' else xhi,q['label_y']+50)]
 candidates=[center]
 x1,y1,x2,y2=roompoly.bounds
 for fx in [.15,.35,.65,.85]:
  for fy in [.15,.35,.65,.85]:
   p=Point(x1+(x2-x1)*fx,y1+(y2-y1)*fy)
   if roompoly.covers(p):candidates.append(p)
 candidates.sort(key=lambda p:p.distance(center))
 for exp in range(16):
  eps=2/(2**exp)
  wires=unary_union(completed).buffer(eps,quad_segs=2,join_style='mitre') if completed else Polygon()
  free=outer.difference(unary_union([card_obstacles,wires]))
  comps=[free] if free.geom_type=='Polygon' else [p for p in free.geoms if p.geom_type=='Polygon']
  start=None
  for end in ends:
   component=next((p for p in comps if p.covers(end)),None)
   if component is None:continue
   start=next((p for p in candidates if component.covers(p)),None)
   if start is not None:break
  if start is not None:break
 else:raise RuntimeError('连续布线未找到可达分量 '+q['number'])
 direct=LineString([start,end])
 if component.covers(direct):path=list(direct.coords)
 else:
  tris=list(constrained_delaunay_triangles(component).geoms)
  tree=STRtree(tris);si=int(tree.query(start,predicate='intersects')[0]);gi=int(tree.query(end,predicate='intersects')[0])
  adj=[[] for _ in tris];edges={}
  for ti,t in enumerate(tris):
   pts=list(t.exterior.coords)[:-1]
   for a,b in zip(pts,pts[1:]+pts[:1]):
    key=tuple(sorted((a,b)))
    if key in edges:
     tj=edges[key];mid=((a[0]+b[0])/2,(a[1]+b[1])/2)
     adj[ti].append((tj,mid));adj[tj].append((ti,mid))
    else:edges[key]=ti
  todo=deque([si]);parents={si:None};portals={}
  while todo:
   u=todo.popleft()
   if u==gi:break
   for v,mid in adj[u]:
    if v not in parents:parents[v]=u;portals[v]=mid;todo.append(v)
  assert gi in parents,q['number']
  mids=[];v=gi
  while parents[v] is not None:mids.append(portals[v]);v=parents[v]
  mids.reverse();raw=[tuple(start.coords)[0]]+mids+[tuple(end.coords)[0]]
  # 删除不必要折点，保留在自由平面内的直达线段。
  path=[raw[0]];i=0
  while i<len(raw)-1:
   j=len(raw)-1
   while j>i+1 and not component.covers(LineString([raw[i],raw[j]])):j-=1
   path.append(raw[j]);i=j
 path.append((end.x,end.y))
 geom=LineString(path)
 assert geom.is_simple,('self',q['number'])
 
 if any(geom.intersects(old) for old in completed):
  print('crossdetail',q['number'],eps,[(j,geom.intersection(old).wkt,geom.distance(old)) for j,old in enumerate(completed) if geom.intersects(old)],'path',path,flush=True)
  raise RuntimeError('cross '+q['number'])
 q['leader']=path;q['anchor']=(start.x/STEP,start.y/STEP);q['port']=(end.x/STEP,end.y/STEP)
 completed.append(geom)
 print('routed',idx+1,'/',len(qs),q['number'],'eps',eps,flush=True)
(TMP/'review_layout.json').write_text(json.dumps(qs,ensure_ascii=False,indent=2)+'\n')
# PNG 使用系统中文字体；原图像素仅作为底图复制，不修改原文件。
im=Image.new('RGB',(W,H),'#f6f8fb');d=ImageDraw.Draw(im)
orig=Image.open(ROOT/'38_梅州市蕉岭县中医医院_原图.jpg').convert('RGB').resize((4888,6520))
im.paste(orig,(OX,OY))
d.text((160,65),'38｜梅州市蕉岭县中医医院 · 首层标注草稿核对总图',font=fonts[56],fill='#17324c')
d.text((160,142),f'{len(qs)} 项待确认；原图居中且保持原方向。先按相邻片区阅读，各片区从上到下、同排从左到右。',font=fonts[32],fill='#42576a')
# 先线后框，箭头无方向含义；使用同色连线和对应数字。
for q in qs:d.line(q['leader'],fill=colors[q['group']],width=1)
for q in qs:
 c=colors[q['group']];p=q['canvas_polygon'];d.line(p+[p[0]],fill=c,width=5)
 x,y=(v*STEP for v in q['anchor']);r=23 if len(q['number'])<3 else 29
 d.rounded_rectangle((x-r,y-20,x+r,y+20),radius=8,fill='white',outline=c,width=3)
 bb=d.textbbox((0,0),q['number'],font=fonts[26]);d.text((x-(bb[2]-bb[0])/2,y-18),q['number'],font=fonts[26],fill=c)
 x1=145 if q['side']=='left' else 6600;x2=1400 if q['side']=='left' else 7855;y=q['label_y']
 d.rounded_rectangle((x1,y,x2,y+100),radius=10,fill='white',outline=c,width=3)
 d.text((x1+16,y+5),f"{q['number']}｜{q['id']}  名称未确认",font=fonts[28],fill=c)
 cand=q['candidate'] or '无可靠候选'
 d.text((x1+16,y+39),f"候选：{cand}  ｜把握：{q['confidence']}",font=fonts[24],fill='#243e54')
 # 短依据，完整依据同时在临时核对清单中。
 basis=q['basis'];d.text((x1+16,y+70),'依据：'+basis,font=fonts[22],fill='#627588')
 # 将边栏端口的最后一段连接到卡片边缘。
 port=tuple(v*STEP for v in q['port'])
 edge=(x2 if q['side']=='left' else x1,port[1]);None # leader already terminates at the selected card boundary
d.text((160,H-240),'片区：紫色＝大厅与药房配套；蓝色＝急诊／输液；橙色＝发热／儿童发热／肠道；绿色＝医技。',font=fonts[32],fill='#334e62')
d.text((160,H-180),'回复格式：01=名称，02=名称……；可分批确认，也可用 S 编号。候选均未写入核心 JSON。',font=fonts[36],fill='#17324c')
d.text((160,H-115),'范围：综合门诊医技楼首层；不含右下斜线建筑、室外空白与雨篷。引线仅用于定位，不表示空间可达。',font=fonts[28],fill='#627588')
im.save(TMP/'38_高清核对总图.png',optimize=True)
im.resize((1600,1560)).save(TMP/'38_核对总图预览.png')
