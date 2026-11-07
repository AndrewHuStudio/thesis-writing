import json,math,heapq,base64,random,time
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import Polygon,LineString
from collections import Counter
T=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理/临时核对/14_无锡市人民医院二期建设项目');P=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理/标注试样/14_无锡市人民医院二期建设项目')
d=json.loads((P/'annotation.json').read_text());meta=json.loads((T/'review-meta.json').read_text());md={a['key']:a for a in meta};sp={s['id']:s for s in d['spaces']}
order='a_small1 a_small2 a_normal a_tpn a_hatch0 a_hatch1 a_hatch2 a_hatch3 a_hatchlow a_east a_east_small a_large a_guard a_dispense a_blank a_bath a_change1 a_change2 a_changehall a_change3 a_change4 b_staff b_big b_equip c_manage c_counter c_counter_small c_iso_inf e_draw e_immune e_lab e_small f_off g_eye0 g_eye1 g_inject f_pharmacy f_work1 f_small f_prepare f_work2 f_clean f_activity h_support h_baby h_small1 h_mid h_bone h_work h_store h_triage h_small h_drug i_doc i_reception'.split()
assert set(order)==set(md) and len(order)==len(md)
M=[dict(md[q],number=f'{i:02d}') for i,q in enumerate(order,1)]
W,H=4600,3030;OX,OY=670,390;G=2;GW,GH=math.ceil(W/G),math.ceil(H/G);SCALE=3
colors=dict(zip('ABCDEFGHI',['#b45309','#be185d','#0f766e','#0369a1','#7c3aed','#9f1239','#1d4ed8','#6d28d9','#047857']))
# Cards use stable continuous numbering within contiguous plan regions.
for i,m in enumerate(M):
 n=i+1;g=m['group'][0]
 if n<=9:side='L';cy=53+(n-1)*73
 elif n<=11:side='R';cy=180+(n-10)*73
 elif n<=15:side='L';cy=740+(n-12)*73
 elif n<=21:side='R';cy=420+(n-16)*73
 elif g=='B':side='R';cy=900+(n-22)*77
 elif g=='C':side='L';cy=1100+(n-25)*79
 elif g=='E':side='L';cy=1640+(n-29)*80
 elif g=='F':side='R';cy=1350 if n==33 else 1700+(n-37)*79
 elif g=='G':side='R';cy=1450+(n-34)*79
 elif g=='H':side='L';cy=1990+(n-44)*76
 else:side='R';cy=2430+(n-54)*85
 m['side']=side;m['card_y']=cy;m['color']=colors[g]
 m['polygon']=[[x+OX,y+OY] for x,y in sp[m['sid']]['polygon_px']]
 p=Polygon(m['polygon']);rp=p.representative_point();m['anchor']=[round(rp.x/G),round(rp.y/G)]
 
 if m['key']=='a_hatchlow':m['anchor'][1]+=8
 if m['number'] in ['37','38','39','40']:m['anchor'][1]=round(2050/G)
 if m['number']=='51':m['anchor'][1]=round(2340/G)
 if m['number']=='52':m['anchor'][1]=round(2326/G)
 m['end']=[round((618 if side=='L' else 3980)/G),round((cy+15)/G)]
# Routing constraints: other question boxes are obstacles, existing routes cannot be crossed.
base=Image.new('L',(GW,GH),0);bd=ImageDraw.Draw(base)
for m in M:
 x,y=m['anchor'];bd.rectangle((x-3,y-3,x+3,y+3),fill=1)
 x,y=m['end'];bd.rectangle((x-1,y-1,x+1,y+1),fill=1)
known=Image.new('L',(GW,GH),0);kd=ImageDraw.Draw(known)
for s in d['spaces']:kd.polygon([(round((x+OX)/G),round((y+OY)/G)) for x,y in s['polygon_px']],fill=1)
# Header is not a routing obstacle.
B=bytes(base.tobytes());K=bytes(known.tobytes())
# Search restricted to connector field; label card interiors never used as routes.
XMIN,XMAX=round(618/G),round(3980/G)
def search(m,used):
 own=Image.new('L',(GW,GH),0);ImageDraw.Draw(own).polygon([(round(x/G),round(y/G)) for x,y in m['polygon']],fill=1);
 ex0,ey0=m['end'];ImageDraw.Draw(own).rectangle((ex0-1,ey0-1,ex0+1,ey0+1),fill=1);own=bytes(own.tobytes())
 sx,sy=m['anchor'];ex,ey=m['end'];start=sy*GW+sx;end=ey*GW+ex
 pq=[(abs(sx-ex)+abs(sy-ey),0,start)];dist={start:0};prev={};expanded=0
 while pq:
  _,cost,cur=heapq.heappop(pq)
  if cost!=dist.get(cur):continue
  if cur==end:
   p=[cur]
   while p[-1]!=start:p.append(prev[p[-1]])
   return [(v%GW,v//GW) for v in p[::-1]],expanded
  x,y=cur%GW,cur//GW;expanded+=1
  for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
   if not(XMIN<=nx<=XMAX and 2<=ny<GH-12):continue
   ne=ny*GW+nx
   if ne in used or (B[ne] and not own[ne]):continue
   # White margins and open original areas preferred to unrelated rooms.
   step=1+(4.0 if K[ne] and not own[ne] else 0)
   if ny!=ey:
    edge=min(nx-XMIN,XMAX-nx)
    if edge<120:step+=((120-edge)/max(3,edge+3))**2
   if 15/G<ny<255/G and 725/G<nx<3920/G:step+=30
   # Long bends discouraged, while remaining on a Manhattan grid.
   if cur in prev:
    pa=prev[cur];px,py=pa%GW,pa//GW
    if (nx-x,ny-y)!=(x-px,y-py):step+=.15
   nc=cost+step
   if nc<dist.get(ne,1e30):
    dist[ne]=nc;prev[ne]=cur;heapq.heappush(pq,(nc+abs(nx-ex)+abs(ny-ey),nc,ne))
 return None,expanded
# Short source-to-label routes first; same-region requests keep source ordering.
# Endpoint paths remain distinct: all occupied grid cells are locked for later paths.
exec((T/'manual_north.py').read_text())
manual=manual_routes(M,G)
manual_lines={j:LineString(v) for j,v in manual.items()}
for j,l in manual_lines.items():
 for i,q in manual_lines.items():
  if i<j:assert l.intersection(q).is_empty,('manual crossing',i+1,j+1,str(l.intersection(q)))
seq=[j for j in range(len(M)-1,-1,-1) if j not in manual]
for attempt in range(18):
 used=set();routes={}
 for j,pts in manual.items():
  path=[]
  for (x1,y1),(x2,y2) in zip(pts,pts[1:]):
   count=max(1,round(max(abs(x2-x1),abs(y2-y1))/G))
   for z in range(count+1):
    x=round((x1+(x2-x1)*z/count)/G);y=round((y1+(y2-y1)*z/count)/G)
    used.add(y*GW+x);path.append((x,y))
  routes[j]=path
 failed=None
 for j in seq:
  path,steps=search(M[j],used)
  if path is None:failed=M[j]['number'];break
  routes[j]=path
  for x,y in path:used.add(y*GW+x)
  print('route',attempt,M[j]['number'],len(path),steps,flush=True)
 if failed is None:break
 print('RETRY failed',failed,flush=True)
 idx=int(failed)-1;seq.remove(idx);seq.insert(0,idx)
else:raise RuntimeError('Cannot route all connectors without crossings')
# Exact geometric intersection check before drawing.
lines=[]
for j in range(len(M)):
 
 if j in manual:
  M[j]['line']=manual[j];lines.append(LineString(manual[j]));continue
 pts=routes[j];simple=[pts[0]]
 for i in range(1,len(pts)-1):
  if (pts[i][0]-pts[i-1][0],pts[i][1]-pts[i-1][1])!=(pts[i+1][0]-pts[i][0],pts[i+1][1]-pts[i][1]):simple.append(pts[i])
 simple.append(pts[-1]);M[j]['line']=[[x*G,y*G] for x,y in simple];lines.append(LineString(M[j]['line']))
for i,l in enumerate(lines):
 for j in range(i):assert l.intersection(lines[j]).is_empty,(i,j)
(T/'review-map.json').write_text(json.dumps(M,ensure_ascii=False,indent=2))
(T/'编号对应.txt').write_text('\n'.join(f"{m['number']}={m['sid']} | 候选：{'／'.join(m['candidates'])} | {m['confidence']} | {m['basis']}" for m in M)+'\n')
font='/System/Library/Fonts/STHeiti Medium.ttc'
def F(sz):return ImageFont.truetype(font,round(sz*SCALE))
canvas=Image.new('RGB',(W*SCALE,H*SCALE),'#f8fafc');draw=ImageDraw.Draw(canvas)
def text(x,y,t,size=13,color='#172b4d'):draw.text((round(x*SCALE),round(y*SCALE)),t,font=F(size),fill=color)
def rect(box,fill,outline=None,width=1):draw.rounded_rectangle(tuple(round(v*SCALE) for v in box),radius=round(3*SCALE),fill=fill,outline=outline,width=round(width*SCALE))
source=Image.open(P/d['image']['file']).convert('RGB');canvas.paste(source.resize((3260*SCALE,2444*SCALE),Image.Resampling.LANCZOS),(OX*SCALE,OY*SCALE))
text(740,30,'14｜无锡市人民医院二期建设项目',31)
text(740,76,'标注草稿 · 55 项名称待确认 · 核对号 01—55 固定',22,'#9a3412')
text(740,114,'按相邻片区自上而下、同排从左到右读取；候选仅供核对，核心 JSON 均保留 unknown。',17)
text(740,146,'回复示例：01=名称，02=名称；可分批回复，也可直接使用 S 编号。',17)
text(740,180,'完整原图居中，未裁剪、未旋转；彩框、核对号与引线均为叠加层。',15,'#475569')
text(740,215,'颜色对应片区：A 北侧配液，B 北侧支持，C 输液，E 检验，F 保健支持，G 体检，H 急诊，I 留观。',14,'#475569')
# Leaders behind room boxes and text, white halos maintain legibility.
for m in M:
 pts=[(x*SCALE,y*SCALE) for x,y in m['line']]
 draw.line(pts,fill='white',width=round(2.3*SCALE));draw.line(pts,fill=m['color'],width=round(.7*SCALE))
for m in M:
 pts=[(x*SCALE,y*SCALE) for x,y in m['polygon']]
 draw.line(pts+[pts[0]],fill=m['color'],width=round(1.8*SCALE))
 p=Polygon(m['polygon']);a=p.representative_point();x,y=[v*G for v in m['anchor']]
 rect([x-11,y-9,x+11,y+9],'#ffffff',m['color'],.7);text(x-8,y-7,m['number'],12,m['color'])
 side=m['side'];x=18 if side=='L' else 3980;y=m['card_y'];col=m['color']
 rect([x,y-3,x+600,y+68],'white',col,.8)
 text(x+10,y,f"{m['number']}｜{m['sid']} 名称未确认",17,col)
 candidates='／'.join(m['candidates']);text(x+10,y+22,f"候选：{candidates}　 把握：{m['confidence']}",14,col)
 text(x+10,y+44,'依据：'+m['basis'],12,'#475569')
text(740,2910,'图中编号仅用于本轮名称确认。未记录的可达关系不代表不连通；面积为概念级相对规模。',16,'#475569')
canvas.save(T/'14_高清核对总图.png',optimize=True)
canvas.resize((2300,1515),Image.Resampling.LANCZOS).save(T/'14_核对总图_预览.jpg',quality=92)
# Local enlarged panels supplement, never replace, the complete source map.
for name,bounds,groups in [('北侧密集局部',(1240,140,2075,455),'A'),('北侧支持局部',(1790,425,2780,585),'B'),('中部输液与检验局部',(1380,580,2095,1650),'CE'),('中下部保健支持局部',(1795,1360,2225,1915),'F'),('东侧体检局部',(2320,1360,2620,1790),'G'),('西南急诊局部',(215,1635,1270,2170),'H'),('留观支持局部',(1250,1635,1680,1990),'I')]:
 x1,y1,x2,y2=bounds;scale=4;crop=source.crop(bounds).resize(((x2-x1)*scale,(y2-y1)*scale),Image.Resampling.LANCZOS);dr=ImageDraw.Draw(crop)
 for m in M:
  if m['group'][0] not in groups:continue
  s=sp[m['sid']];poly=Polygon(s['polygon_px']);rp=poly.representative_point()
  if not(x1<=rp.x<=x2 and y1<=rp.y<=y2):continue
  pts=[((x-x1)*scale,(y-y1)*scale) for x,y in s['polygon_px']];dr.line(pts+[pts[0]],fill=m['color'],width=5)
  xx,yy=(rp.x-x1)*scale,(rp.y-y1)*scale;dr.rounded_rectangle((xx-32,yy-25,xx+32,yy+25),radius=5,fill='white',outline=m['color'],width=2);dr.text((xx-25,yy-21),m['number'],font=ImageFont.truetype(font,42),fill=m['color'])
 crop.save(T/('14_'+name+'.png'))
print('COMPLETE',len(M),'routes; intersections=0',flush=True)