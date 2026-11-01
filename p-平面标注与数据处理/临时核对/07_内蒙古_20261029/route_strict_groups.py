from pathlib import Path
import json,heapq,math,time
import numpy as np
from shapely.geometry import Polygon,LineString
T=Path('p-写作过程/临时核对/07_内蒙古_20261029');rows=json.loads((T/'核对对应_临时.json').read_text())
zoneorder=['F','A','G','D','B','H','E','C','J'];rows.sort(key=lambda q:(zoneorder.index(q['zone']),q['anchor_y'],Polygon(q['polygon_px']).bounds[0]))
for i,q in enumerate(rows,1):q['number']=f'{i:02d}'
sidew=740;gutter=180;iw=3260;ih=2444;rowh=27;w=5140;h=4240;ox=940;oy=(h-ih)//2
entries=[]
for side in [0,1]:
 ls=[q for q in rows if q['side']==side];y0=130+(h-170-len(ls)*rowh)//2
 for i,q in enumerate(ls):
  p=Polygon(q['polygon_px']);ty=q['anchor_y'];sec=p.intersection(LineString([(-10,ty),(3270,ty)]));tx=sec.bounds[0] if side==0 else sec.bounds[2]
  entries.append((q,(sidew if side==0 else w-sidew,y0+i*rowh+rowh/2),(tx+ox,ty+oy)))
paths=[];step=4.0;refinements=0
# Discrete grid is refined when adjacent lines close a gap: physical vector paths remain separate.
def grid():
 gw=math.ceil(w/step)+1;gh=math.ceil(h/step)+1;a=np.zeros((gh,gw),np.uint8)
 a[:int(110/step),:]=1;a[-2:,:]=1
 a[:,:int((sidew+20)/step)]=1;a[:,int((w-sidew-20)/step)+1:]=1
 for q,s,e in entries:
  ex,ey=round(e[0]/step),round(e[1]/step);a[ey,ex]=2
 for _,pts in paths:
  for (x1,y1),(x2,y2) in zip(pts,pts[1:]):
   gx1,gy1,gx2,gy2=[round(v/step) for v in (x1,y1,x2,y2)]
   a[min(gy1,gy2):max(gy1,gy2)+1,min(gx1,gx2):max(gx1,gx2)+1]=1
 return a,gw,gh
blocked,gw,gh=grid()
def find(s,e):
 sx,sy=round(s[0]/step),round(s[1]/step);ex,ey=round(e[0]/step),round(e[1]/step);si=sy*gw+sx;ei=ey*gw+ex
 dist={si:0};prev={};heap=[(abs(sx-ex)+abs(sy-ey),0,si)];limit=time.monotonic()+35
 while heap:
  _,cost,idx=heapq.heappop(heap)
  if cost!=dist.get(idx):continue
  if idx==ei:
   allpts=[idx]
   while idx!=si:idx=prev[idx];allpts.append(idx)
   pts=[(i%gw,i//gw) for i in allpts[::-1]];clean=[pts[0]]
   for i in range(1,len(pts)-1):
    a,b,c=pts[i-1:i+2]
    if (b[0]-a[0],b[1]-a[1])!=(c[0]-b[0],c[1]-b[1]):clean.append(b)
   clean.append(pts[-1]);return [(round(x*step,4),round(y*step,4)) for x,y in clean]
  x=idx%gw;y=idx//gw
  for nx,ny in [(x-1,y),(x+1,y),(x,y-1),(x,y+1)]:
   if not (0<=nx<gw and 0<=ny<gh):continue
   ni=ny*gw+nx;nearstart=abs(nx-sx)*step<=24 and abs(ny-sy)*step<=.6*step
   if blocked[ny,nx] and ni!=ei and not nearstart:continue
   nc=cost+1
   if nc<dist.get(ni,1e12):dist[ni]=nc;prev[ni]=idx;heapq.heappush(heap,(nc+abs(nx-ex)+abs(ny-ey),nc,ni))
  if len(dist)%10000==0 and time.monotonic()>limit:return None
 return None
for q,s,e in sorted(entries,key=lambda a:abs(a[1][0]-a[2][0])+abs(a[1][1]-a[2][1])):
 while True:
  pts=find(s,e)
  if pts is not None:break
  if refinements>=4:raise RuntimeError(f'adaptive routing exhausted at {q["number"]} after {len(paths)}')
  step/=2;refinements+=1;blocked,gw,gh=grid();print('Refine',step,'after',len(paths),'grid',gw,gh,flush=True)
 paths.append((q['number'],pts));blocked,gw,gh=grid()
 if len(paths)%20==0:print('Routed',len(paths),flush=True)
cross=[]
for i,(n,p) in enumerate(paths):
 for m,q in paths[i+1:]:
  if LineString(p).intersects(LineString(q)):cross.append((n,m))
if cross:raise RuntimeError(str(cross[:10]))
(T/'分区连续序号_引线方案_临时.json').write_text(json.dumps({'rows':rows,'paths':paths,'crossings':cross,'entries':[(q['number'],s,e) for q,s,e in entries]},ensure_ascii=False,indent=2))
print('SUCCESS',len(paths),flush=True)
