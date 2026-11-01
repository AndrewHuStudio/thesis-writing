from pathlib import Path
import json,base64,html,heapq,math
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import Polygon,LineString
T=Path('p-写作过程/临时核对/07_内蒙古_20261029');P=Path('p-写作过程/标注试样/07_内蒙古自治区儿童医院、妇产医院、妇幼保健院外迁合建项目')
rows=json.loads((T/'核对对应_临时.json').read_text());img=Image.open(next(P.glob('*.jpg')))
font='/System/Library/Fonts/PingFang.ttc'
colors={'F':'#b03d64','A':'#7547aa','G':'#147f78','D':'#99602b','B':'#3861a5','H':'#b84b29','E':'#28677a','C':'#5f7c28','J':'#7b5a79'}
# Fan leaders are monotonic between fixed vertical rails. This guarantees no crossings.
# Each sidebar forms a continuous spatial sequence, read left column then right column.
# Anchor at each shared top edge, progressing left-to-right within a row.
for q in rows:q['side']=0 if q['zone'] in ('F','G','D','H','J') else 1
for side in (0,1):
 pending=sorted([q for q in rows if q['side']==side],key=lambda q:Polygon(q['polygon_px']).bounds[1])
 while pending:
  top=Polygon(pending[0]['polygon_px']).bounds[1]
  group=[q for q in pending if Polygon(q['polygon_px']).bounds[1]<=top+8]
  pending=[q for q in pending if q not in group]
  base=max(Polygon(q['polygon_px']).bounds[1] for q in group)+2
  for i,q in enumerate(sorted(group,key=lambda q:Polygon(q['polygon_px']).bounds[0])):
   q['anchor_y']=round(base+i*.15,2)
zoneorder=['F','A','G','D','B','H','E','C','J']
rows.sort(key=lambda q:(zoneorder.index(q['zone']),q['anchor_y'],Polygon(q['polygon_px']).bounds[0]))
for i,q in enumerate(rows,1):q['number']=f'{i:02d}'
(T/'核对对应_临时.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
def wrap(s,n):return [s[i:i+n] for i in range(0,len(s),n)] or ['']
def make(name,selected,bounds=None,full=False):
 # Main uses untouched complete source; local figures show spatially intact group crops.
 if bounds is None:bounds=(0,0,img.width,img.height)
 l,t,r,b=bounds; k=1 if full else 2; iw=(r-l)*k;ih=(b-t)*k
 left=[q for q in selected if q['side']==0]
 right=[q for q in selected if q not in left]
 # Same zone occupies a contiguous run, and each label shows the globally continuous review number.
 sides=[left,right]
 rowh=27 if full else 60; sidew=740 if full else 620; gutter=180 if full else 120
 h=max(ih+160,max(len(x) for x in sides)*rowh+190);w=iw+2*(sidew+gutter)+40
 ox=sidew+gutter+20;oy=(h-ih)//2
 raw=[]
 def put(x):raw.append(x)
 def txt(x,y,s,size=15,color='#243345',bold=False):put(f'<text x="{x}" y="{y}" font-family="PingFang SC,Microsoft YaHei,sans-serif" font-size="{size}" fill="{color}" font-weight="{700 if bold else 400}">{html.escape(s)}</text>')
 put(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><rect width="100%" height="100%" fill="#f8fafc"/>')
 txt(24,35,'07号平面｜'+name+'｜标注草稿：候选均待确认',25,bold=True)
 txt(24,65,f'共 {len(selected)} 项；核对号先左栏后右栏，各栏自上而下；按“01=名称，02=名称”分批回复。',17)
 txt(24,89,'边栏：核对号｜S编号｜候选用途（把握程度）；依据见同目录核对清单。原图未改动。',14)
 # embed source crop without modification
 import io
 bio=io.BytesIO();img.crop(bounds).save(bio,format='PNG' if not full else 'JPEG',quality=96)
 enc=base64.b64encode(bio.getvalue()).decode();mime='image/jpeg' if full else 'image/png'
 put(f'<image x="{ox}" y="{oy}" width="{iw}" height="{ih}" href="data:{mime};base64,{enc}"/>')
 routes=[];entries=[]
 for side,ls in enumerate(sides):
  ls.sort(key=lambda q:q['anchor_y'])
  y0=130+(h-170-len(ls)*rowh)//2
  for i,q in enumerate(ls):
   poly=Polygon(q['polygon_px']);ty=q['anchor_y']
   sec=poly.intersection(LineString([(-10,ty),(3270,ty)]))
   tx=((sec.bounds[0] if side==0 else sec.bounds[2])-l)*k+ox;ty=(ty-t)*k+oy
   cy=y0+i*rowh+rowh/2;sx=sidew if side==0 else w-sidew
   rail=ox-12 if side==0 else ox+iw+12
   pts=[(sx,cy),(rail,ty),(tx,ty)]
   routes.append((q,pts));entries.append((q,side,cy,None,None))
 # Explicit crossing verification using full vector paths.
 crosses=[]
 for i,(q,pts) in enumerate(routes):
  a=LineString(pts)
  for other,points in routes[i+1:]:
   if a.intersects(LineString(points)):crosses.append((q['number'],other['number']))
 if crosses:raise RuntimeError(str(crosses[:10]))
 for q,pts in routes:
  col=colors[q['zone']];s=' '.join(f'{x},{y}' for x,y in pts)
  put(f'<polyline points="{s}" fill="none" stroke="white" stroke-width="3.0" stroke-linejoin="round"/><polyline points="{s}" fill="none" stroke="{col}" stroke-width=".9" stroke-opacity=".65" stroke-linejoin="round"/>')
  x,y=pts[-1];put(f'<circle cx="{x}" cy="{y}" r="3" fill="{col}"/>')
 # Boxes/number badges: source labels remain visible underneath and callouts avoid room-centre text.
 for q in selected:
  col=colors[q['zone']];poly=q['polygon_px'];points=' '.join(f'{(x-l)*k+ox},{(y-t)*k+oy}' for x,y in poly)
  put(f'<polygon points="{points}" fill="{col}" fill-opacity=".06" stroke="{col}" stroke-width="2"/>')
  x=(min(x for x,y in poly)-l)*k+ox+2;y=(min(y for x,y in poly)-t)*k+oy+3
  fs=12 if full else 15;bw=max(25,len(q['number'])*fs*.7+8)
  put(f'<rect x="{x}" y="{y}" width="{bw}" height="{fs+6}" rx="2" fill="white" stroke="{col}"/>');txt(x+3,y+fs+1,q['number'],fs,col,True)
 for q,side,cy,s,e in entries:
  col=colors[q['zone']];bx=20 if side==0 else w-sidew+12;bw=sidew-32
  put(f'<rect x="{bx}" y="{cy-rowh/2+2}" width="{bw}" height="{rowh-4}" rx="3" fill="white" stroke="{col}" stroke-width="1"/>')
  if full:
   txt(bx+8,cy+5,f'{q["number"]}｜{q["id"]}｜{q["zone_name"]}｜候选：{q["candidate"]}（{q["confidence"]}）',13,col,True)
  else:
   txt(bx+8,cy-7,f'{q["number"]}｜{q["id"]}｜候选／待确认（{q["confidence"]}）',16,col,True)
   txt(bx+8,cy+17,q['candidate'],15,col)
 put('</svg>');dest=T/(name+'.svg');dest.write_text(''.join(raw))
 (T/(name+'_引线核查.json')).write_text(json.dumps({'items':len(selected),'leader_count':len(routes),'crossing_count':len(crosses),'width':w,'height':h},ensure_ascii=False,indent=2))
 print(name,len(selected),w,h,'crossings',len(crosses),flush=True)
 return dest
# The complete review atlas is paginated by adjacent region; every page retains the full original.
for i,z in enumerate(['F','A','G','D','B','H','E','C','J'],1):
 ls=[q for q in rows if q['zone']==z]
 if not ls:continue
 pts=[p for q in ls for p in q['polygon_px']];xs,ys=zip(*pts)
 bounds=(max(0,int(min(xs))-50),max(0,int(min(ys))-50),min(img.width,int(max(xs))+50),min(img.height,int(max(ys))+50))
 make(f'总图{i:02d}_{ls[0]["zone_name"]}',ls,full=True)
 make(f'{i:02d}_{ls[0]["zone_name"]}_局部核对',ls,bounds)
lines=['# 07号平面名称核对清单','',f'标注草稿：{len(rows)}项候选全部待确认，核心JSON保持unknown。','核对号读取：总图按9个相邻片区分页，每页保留完整原图；核对号按片区连续01-269，各片区自上而下、同排从左到右。片区名称与S编号同时显示。','可分批回复，例如：01=诊室，02=治疗室。保留所有已确认名称。','', '|核对号|S编号|片区|候选用途（待确认）|依据|把握|','|---|---|---|---|---|---|']
nav=['','[打开9页高清核对总图](00_高清核对总图_9页.pdf)','','## 局部放大图','']
for image_path in sorted(T.glob('*局部核对.svg')):nav.append(f'- [{image_path.stem}]({image_path.with_suffix(".png").name})')
lines[5:5]=nav+['']
for q in rows:lines.append('|'+ '|'.join([q['number'],q['id'],q['zone_name'],q['candidate'],q['basis'],q['confidence']])+'|')
(T/'核对清单.md').write_text('\n'.join(lines)+'\n')
