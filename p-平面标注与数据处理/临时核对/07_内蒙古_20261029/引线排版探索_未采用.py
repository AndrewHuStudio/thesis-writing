from pathlib import Path
import json,base64,html,heapq,math
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import Polygon,LineString
T=Path('p-写作过程/临时核对/07_内蒙古_20261029');P=Path('p-写作过程/标注试样/07_内蒙古自治区儿童医院、妇产医院、妇幼保健院外迁合建项目')
rows=json.loads((T/'核对对应_临时.json').read_text());img=Image.open(next(P.glob('*.jpg')))
font='/System/Library/Fonts/PingFang.ttc'
colors={'F':'#b03d64','A':'#7547aa','G':'#147f78','D':'#99602b','B':'#3861a5','H':'#b84b29','E':'#28677a','C':'#5f7c28','J':'#7b5a79'}
# Ordered review numbers retain the independently established S identifiers and adjacent-region grouping.
assert [int(r['number']) for r in rows]==list(range(1,len(rows)+1))
def wrap(s,n):return [s[i:i+n] for i in range(0,len(s),n)] or ['']
def make(name,selected,bounds=None,full=False):
 # Main uses untouched complete source; local figures show spatially intact group crops.
 if bounds is None:bounds=(0,0,img.width,img.height)
 l,t,r,b=bounds; iw=r-l;ih=b-t
 left=[q for q in selected if q['zone'] in ('F','G','D','H','J')] if full else [q for q in selected if Polygon(q['polygon_px']).centroid.x<(l+r)/2]
 right=[q for q in selected if q not in left]
 # Same zone occupies a contiguous run, and each label shows the globally continuous review number.
 sides=[left,right]
 rowh=34 if full else 60; sidew=740 if full else 620; gutter=180 if full else 120
 h=max(ih+160,max(len(x) for x in sides)*rowh+190);w=iw+2*(sidew+gutter)+40
 ox=sidew+gutter+20;oy=(h-ih)//2
 raw=[]
 def put(x):raw.append(x)
 def txt(x,y,s,size=15,color='#243345',bold=False):put(f'<text x="{x}" y="{y}" font-family="PingFang SC,Microsoft YaHei,sans-serif" font-size="{size}" fill="{color}" font-weight="{700 if bold else 400}">{html.escape(s)}</text>')
 put(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><rect width="100%" height="100%" fill="#f8fafc"/>')
 txt(24,35,'07号平面｜'+name+'｜标注草稿：候选均待确认',25,bold=True)
 txt(24,65,f'共 {len(selected)} 项；按核对号回复“01=名称，02=名称”，可分批；S编号保持稳定。',17)
 txt(24,89,'边栏：核对号｜S编号｜候选用途（把握程度）；依据见同目录核对清单。原图未改动。',14)
 # embed source crop without modification
 import io
 bio=io.BytesIO();img.crop(bounds).save(bio,format='PNG' if not full else 'JPEG',quality=96)
 enc=base64.b64encode(bio.getvalue()).decode();mime='image/jpeg' if full else 'image/png'
 put(f'<image x="{ox}" y="{oy}" width="{iw}" height="{ih}" href="data:{mime};base64,{enc}"/>')
 # Define all starts/targets first so earlier routes cannot steal later endpoints.
 step=2 if full else 2;gw=math.ceil(w/step);gh=math.ceil(h/step)
 blocked=np.zeros((gh,gw),dtype=np.uint8)
 # route only central panel and blank lead gutters, never through label text
 xmin=sidew+24;xmax=w-sidew-24
 blocked[:,:max(0,xmin//step)]=1;blocked[:,min(gw,xmax//step+1):]=1
 blocked[:110//step,:]=1;blocked[-5:,:]=1
 routes=[];entries=[];target_seen=set()
 for side,ls in enumerate(sides):
  y0=130+(h-170-len(ls)*rowh)//2
  for i,q in enumerate(ls):
   p=Polygon(q['polygon_px']);x1,y1,x2,y2=p.bounds
   # Distinct endpoints on target boundary; move within its vertical span if grid-rounded endpoints coincide.
   tx=(x1 if side==0 else x2)-l+ox;ty=p.representative_point().y-t+oy
   target=(round(tx/step),round(ty/step))
   for shift in [0,1,-1,2,-2,3,-3,4,-4]:
    cand=(target[0],target[1]+shift)
    if cand not in target_seen and y1-t+oy+2<cand[1]*step<y2-t+oy-2:target=cand;break
   target_seen.add(target)
   cy=y0+i*rowh+rowh/2
   sx=sidew if side==0 else w-sidew
   start=(round(sx/step),round(cy/step))
   entries.append((q,side,cy,start,target))
 for _,_,_,s,e in entries:
  x,y=e;blocked[max(0,y-2):y+3,max(0,x-2):x+3]=2
 def route(start,end):
  # A* routes a planar matching. Each added leader reserves a one-cell separation.
  sx,sy=start;ex,ey=end;startid=sy*gw+sx;endid=ey*gw+ex
  dist={startid:0};prev={};heap=[(abs(sx-ex)+abs(sy-ey),0,startid)]
  while heap:
   _,cost,idx=heapq.heappop(heap)
   if cost!=dist.get(idx):continue
   if idx==endid:
    ids=[idx]
    while idx!=startid:idx=prev[idx];ids.append(idx)
    pts=[(i%gw,i//gw) for i in ids[::-1]]
    for x,y in pts:blocked[max(0,y-1):y+2,max(0,x-1):x+2]=1
    clean=[pts[0]]
    for i in range(1,len(pts)-1):
     a=pts[i-1];bb=pts[i];c=pts[i+1]
     if (bb[0]-a[0],bb[1]-a[1])!=(c[0]-bb[0],c[1]-bb[1]):clean.append(bb)
    clean.append(pts[-1]);return [(x*step,y*step) for x,y in clean]
   x=idx%gw;y=idx//gw
   for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
    if not(0<=nx<gw and 0<=ny<gh):continue
    ni=ny*gw+nx
    nearend=abs(nx-ex)<=2 and abs(ny-ey)<=2
    nearstart=abs(nx-sx)<=15 and abs(ny-sy)<=1
    if blocked[ny,nx] and not (nearend or nearstart):continue
    nc=cost+1
    if nc<dist.get(ni,1e12):
     dist[ni]=nc;prev[ni]=idx;heapq.heappush(heap,(nc+abs(nx-ex)+abs(ny-ey),nc,ni))
  Image.fromarray((blocked*80).astype("uint8")).save(T/"routing_debug.png");print("visited",len(dist),"start neighbors",blocked[sy-5:sy+6,sx-12:sx+3],flush=True)
  return None
 # Route short leaders first, then progressively wrap around their interior endpoints.
 for q,side,cy,s,e in sorted(entries,key=lambda v:abs(v[3][0]-v[4][0])+abs(v[3][1]-v[4][1])):
  pts=route(s,e)
  if pts is None:(T/'routing_paths_debug.json').write_text(json.dumps(routes));raise RuntimeError(f'No route for {name} {q["number"]} after {len(routes)}; start={s}, end={e}, grid={gw},{gh}, bounds={xmin},{xmax}')
  routes.append((q,pts))
 # Explicit crossing verification using full vector paths.
 crosses=[]
 for i,(q,pts) in enumerate(routes):
  a=LineString(pts)
  for other,points in routes[i+1:]:
   if a.intersects(LineString(points)):crosses.append((q['number'],other['number']))
 if crosses:raise RuntimeError(str(crosses[:10]))
 for q,pts in routes:
  col=colors[q['zone']];s=' '.join(f'{x},{y}' for x,y in pts)
  put(f'<polyline points="{s}" fill="none" stroke="white" stroke-width="3.0" stroke-linejoin="round"/><polyline points="{s}" fill="none" stroke="{col}" stroke-width="1.2" stroke-linejoin="round"/>')
  x,y=pts[-1];put(f'<circle cx="{x}" cy="{y}" r="3" fill="{col}"/>')
 # Boxes/number badges: source labels remain visible underneath and callouts avoid room-centre text.
 for q in selected:
  col=colors[q['zone']];poly=q['polygon_px'];points=' '.join(f'{x-l+ox},{y-t+oy}' for x,y in poly)
  put(f'<polygon points="{points}" fill="{col}" fill-opacity=".06" stroke="{col}" stroke-width="2"/>')
  x=min(x for x,y in poly)-l+ox+2;y=min(y for x,y in poly)-t+oy+3
  fs=12 if full else 15;bw=max(25,len(q['number'])*fs*.7+8)
  put(f'<rect x="{x}" y="{y}" width="{bw}" height="{fs+6}" rx="2" fill="white" stroke="{col}"/>');txt(x+3,y+fs+1,q['number'],fs,col,True)
 for q,side,cy,s,e in entries:
  col=colors[q['zone']];bx=20 if side==0 else w-sidew+12;bw=sidew-32
  put(f'<rect x="{bx}" y="{cy-rowh/2+2}" width="{bw}" height="{rowh-4}" rx="3" fill="white" stroke="{col}" stroke-width="1"/>')
  if full:
   txt(bx+8,cy+5,f'{q["number"]}｜{q["id"]}｜候选：{q["candidate"]}（{q["confidence"]}）',13,col,True)
  else:
   txt(bx+8,cy-7,f'{q["number"]}｜{q["id"]}｜候选／待确认（{q["confidence"]}）',16,col,True)
   txt(bx+8,cy+17,q['candidate'],15,col)
 put('</svg>');dest=T/(name+'.svg');dest.write_text(''.join(raw))
 (T/(name+'_引线核查.json')).write_text(json.dumps({'items':len(selected),'leader_count':len(routes),'crossing_count':len(crosses),'width':w,'height':h},ensure_ascii=False,indent=2))
 print(name,len(selected),w,h,'crossings',len(crosses),flush=True)
 return dest
make('00_高清核对总图',rows,full=True)
for i,z in enumerate(['F','A','G','D','B','H','E','C','J'],1):
 ls=[q for q in rows if q['zone']==z]
 if not ls:continue
 pts=[p for q in ls for p in q['polygon_px']];xs,ys=zip(*pts)
 bounds=(max(0,int(min(xs))-50),max(0,int(min(ys))-50),min(img.width,int(max(xs))+50),min(img.height,int(max(ys))+50))
 make(f'{i:02d}_{ls[0]["zone_name"]}_局部核对',ls,bounds)
lines=['# 07号平面名称核对清单','',f'标注草稿：{len(rows)}项候选全部待确认，核心JSON保持unknown。','核对号按相邻片区，片区按原图自上而下、同排从左到右编排；左右边栏分别从上到下读，按核对号回复。','可分批回复，例如：01=诊室，02=治疗室。保留所有已确认名称。','', '|核对号|S编号|片区|候选用途（待确认）|依据|把握|','|---|---|---|---|---|---|']
for q in rows:lines.append('|'+ '|'.join([q['number'],q['id'],q['zone_name'],q['candidate'],q['basis'],q['confidence']])+'|')
(T/'核对清单.md').write_text('\n'.join(lines)+'\n')
