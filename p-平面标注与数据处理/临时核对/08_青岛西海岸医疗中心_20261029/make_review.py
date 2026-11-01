from pathlib import Path
import json,base64,html,math,heapq
from collections import defaultdict
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import Polygon,LineString
ROOT=Path('/Users/hushili/Documents/研究-论文写作/大论文');TMP=ROOT/'p-写作过程/临时核对/08_青岛西海岸医疗中心_20261029';OUT=ROOT/'p-写作过程/标注试样/08_青岛西海岸医疗中心'
data=json.loads((OUT/'annotation.json').read_text());review=json.loads((TMP/'核对对应.json').read_text());sp={s['id']:s for s in data['spaces']};source=Image.open(OUT/data['image']['file']).convert('RGB')
FONT='/System/Library/Fonts/STHeiti Medium.ttc';fonts={n:ImageFont.truetype(FONT,n) for n in [16,17,18,20,22,26,32,38]}
colors=['#c2410c','#0f766e','#1d4ed8','#7c3aed','#a21caf','#0369a1','#be123c','#15803d','#92400e'];groups=list(dict.fromkeys(q['group'] for q in review));palette={g:colors[i%len(colors)] for i,g in enumerate(groups)}
def side(q):return 'left' if q['group'][0] in 'ADH' else 'right'
def anchor_rows(qs):
 # Each adjacent row is monotone; distinguish same-row anchors without moving any room.
 results={};bygroup=defaultdict(list)
 for q in qs:bygroup[q['group']].append(q)
 for g,items in bygroup.items():
  rem=items[:]
  while rem:
   y0=rem[0]['bounds'][1];row=[]
   for q in rem:
    if q['bounds'][1]<=y0+10:row.append(q)
    else:break
   rem=rem[len(row):];lo=max(q['bounds'][1] for q in row);hi=min(q['bounds'][3] for q in row)
   if rem:hi=min(hi,rem[0]['bounds'][1])
   if hi<=lo:raise ValueError((g,'incompatible row',lo,hi))
   for j,q in enumerate(row):
    y=lo+(j+1)/(len(row)+1)*(hi-lo);p=Polygon(sp[q['sid']]['polygon_px']);actual=y*2
    line=p.intersection(LineString([(0,actual),(2380,actual)]))
    xx=line.bounds[0] if side(q)=='left' else line.bounds[2]
    results[q['sid']]=(xx,actual)
 return results
anchors=anchor_rows(review)
# Ensure distinct horizontal leaders even when independent opposite-side rows share the same ordinate.
used=[]
for q in review:
 x,y=anchors[q['sid']]
 while any(abs(y-v)<.025 for v in used):y+=.06
 p=Polygon(sp[q['sid']]['polygon_px']);line=p.intersection(LineString([(0,y),(2380,y)]));x=line.bounds[0] if side(q)=='left' else line.bounds[2]
 anchors[q['sid']]=(x,y);used.append(y)
def pava(vals):
 blocks=[]
 for i,v in enumerate(vals):
  blocks.append([i,i,v,1])
  while len(blocks)>1 and blocks[-2][2]/blocks[-2][3]>blocks[-1][2]/blocks[-1][3]:
   b=blocks.pop();a=blocks.pop();blocks.append([a[0],b[1],a[2]+b[2],a[3]+b[3]])
 result=[0]*len(vals)
 for i,j,v,n in blocks:
  for k in range(i,j+1):result[k]=v/n
 return result

def route_side(items,cardedge,imageedge,H,gap):
 if not items:return
 # Both endpoint sequences are ordered, allowing crossing-free orthogonal boundary labels.
 assert all(items[i]['ay']<items[i+1]['ay'] for i in range(len(items)-1)),[(x['number'],x['ay']) for x in items]
 fit=pava([q['ay']-i*gap for i,q in enumerate(items)]);upper=H-140-(len(items)-1)*gap
 for i,q in enumerate(items):q['ly']=min(upper,max(180,fit[i]))+i*gap
 edges=defaultdict(set);ind=[0]*len(items)
 def edge(i,j):
  if i!=j and j not in edges[i]:edges[i].add(j);ind[j]+=1
 for i,a in enumerate(items):
  for j,b in enumerate(items):
   if i==j:continue
   low,high=sorted((b['ly'],b['ay']))
   if low+1e-6<a['ly']<high-1e-6:edge(i,j)
   if low+1e-6<a['ay']<high-1e-6:edge(j,i)
 queue=[i for i,v in enumerate(ind) if v==0];heapq.heapify(queue);rank={}
 while queue:
  i=heapq.heappop(queue);rank[i]=len(rank)
  for j in edges[i]:
   ind[j]-=1
   if ind[j]==0:heapq.heappush(queue,j)
 assert len(rank)==len(items),'route constraint cycle'
 sign=1 if imageedge>cardedge else -1;lane_width=abs(imageedge-cardedge)-30
 for i,q in enumerate(items):
  x=cardedge+sign*(15+(rank[i]+.5)*lane_width/len(items));q['path']=[(cardedge,q['ly']),(x,q['ly']),(x,q['ay']),(q['ax'],q['ay'])]

class Canvas:
 def __init__(self,w,h):
  self.im=Image.new('RGB',(math.ceil(w),math.ceil(h)),'white');self.d=ImageDraw.Draw(self.im);self.svg=[f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><rect width="100%" height="100%" fill="white"/>']
 def text(self,x,y,t,size=20,color='#1f2937'):
  self.d.text((x,y),t,font=fonts[size],fill=color)
  self.svg.append(f'<text x="{x}" y="{y+size*.86}" font-family="STHeiti,Microsoft YaHei,sans-serif" font-size="{size}" fill="{color}">{html.escape(t)}</text>')
 def rect(self,b,fill,stroke=None,width=1):
  self.d.rectangle(b,fill=fill,outline=stroke,width=width)
  self.svg.append(f'<rect x="{b[0]}" y="{b[1]}" width="{b[2]-b[0]}" height="{b[3]-b[1]}" fill="{fill or "none"}" stroke="{stroke or "none"}" stroke-width="{width}"/>')
 def line(self,pts,c,w=1):
  self.d.line(pts,fill=c,width=w,joint='curve');self.svg.append(f'<polyline points="'+ ' '.join(f'{x:.3f},{y:.3f}' for x,y in pts)+f'" fill="none" stroke="{c}" stroke-width="{w}"/>')
 def polygon(self,pts,c):
  self.d.line(pts+[pts[0]],fill=c,width=3,joint='curve');self.svg.append('<polygon points="'+' '.join(f'{x:.3f},{y:.3f}' for x,y in pts)+f'" fill="none" stroke="{c}" stroke-width="3"/>')
 def picture(self,im,x,y,scale,original=False):
  wi=round(im.width*scale);he=round(im.height*scale);self.im.paste(im.resize((wi,he),Image.Resampling.LANCZOS),(round(x),round(y)))
  if original:raw=(OUT/data['image']['file']).read_bytes();mime='image/jpeg'
  else:
   import io
   buf=io.BytesIO();im.save(buf,format='PNG');raw=buf.getvalue();mime='image/png'
  self.svg.append(f'<image x="{x}" y="{y}" width="{wi}" height="{he}" xlink:href="data:{mime};base64,'+base64.b64encode(raw).decode()+'"/>')
 def save(self,name,svg=True):
  self.im.save(TMP/(name+'.png'),optimize=True)
  if svg:(TMP/(name+'.svg')).write_text('\n'.join(self.svg)+ '</svg>')

def make(name,title,qs,crop=(0,0,2380,3280),scale=2,full=False):
 if not full:
  bounds=[Polygon(sp[q['sid']]['polygon_px']).bounds for q in qs]
  crop=(max(0,min(crop[0],int(min(b[0] for b in bounds))-20)),max(0,min(crop[1],int(min(b[1] for b in bounds))-20)),min(2380,max(crop[2],math.ceil(max(b[2] for b in bounds))+20)),min(3280,max(crop[3],math.ceil(max(b[3] for b in bounds))+20)))
 for q in qs:
  b=Polygon(sp[q['sid']]['polygon_px']).bounds
  assert crop[0]<=b[0] and crop[1]<=b[1] and crop[2]>=b[2] and crop[3]>=b[3],(name,q['number'],'clipped room')
 card=740;gutter=360 if full else 150;gap=84
 iw=(crop[2]-crop[0])*scale;ih=(crop[3]-crop[1])*scale
 sides={s:[dict(q) for q in qs if side(q)==s] for s in ['left','right']};maxcount=max(map(len,sides.values()))
 H=math.ceil(max(ih+300,(maxcount-1)*gap+350));W=math.ceil(iw+2*(card+gutter+30));ox=card+gutter+30;oy=(H-ih)/2
 items=[]
 for sd,ls in sides.items():
  for q in ls:
   x,y=anchors[q['sid']];q['ax']=ox+(x-crop[0])*scale;q['ay']=oy+(y-crop[1])*scale;q['side']=sd
  route_side(ls,card+24 if sd=='left' else ox+iw+gutter,ox-10 if sd=='left' else ox+iw+10,H,gap);items.extend(ls)
 c=Canvas(W,H);c.picture(source.crop(crop),ox,oy,scale,original=full)
 c.text(28,24,title,32);c.text(28,68,f'标注草稿｜{len(qs)} 项候选／待确认；按片区从上到下、同排从左到右。',22,'#92400e');c.text(28,99,'可按“01=名称，02=名称”分批回复；核对号与 S 编号对应固定。',20,'#475569')
 for q in items:
  color=palette[q['group']];pts=[(ox+(x-crop[0])*scale,oy+(y-crop[1])*scale) for x,y in sp[q['sid']]['polygon_px']];c.polygon(pts,color)
 # leaders first, then number badges; all routes programmatically tested for intersections.
 for q in items:c.line(q['path'],palette[q['group']],1)
 for q in items:
  color=palette[q['group']];sd=q['side'];x=24 if sd=='left' else ox+iw+gutter;y=q['ly']-37
  c.rect((x,y,x+card,y+74),'#ffffff',color,2)
  c.text(x+10,y+5,f'{q["number"]}｜{q["sid"]} 候选／待确认 · 把握{q["confidence"]}',22,color)
  c.text(x+10,y+30,q['candidate'] or '用途未知（无可靠候选）',20)
  basis=q['basis'];basis=(basis[:37]+'…') if len(basis)>38 else basis
  c.text(x+10,y+54,'依据：'+basis,17,'#64748b')
  p=Polygon(sp[q['sid']]['polygon_px']);a=p.representative_point();bx=ox+(a.x-crop[0])*scale;by=oy+(a.y-crop[1])*scale;ww=50 if len(q['number'])<3 else 62
  c.rect((bx-ww/2,by-14,bx+ww/2,by+14),'white',color,2);c.text(bx-ww/2+5,by-11,q['number'],20,color)
 c.text(28,H-44,'候选用途仅用于核对，未写入核心 JSON。原图未修改；缺失关系不表示不可达。',20,'#475569')
 paths=[(q['number'],LineString(q['path'])) for q in items]
 crosses=[];touches=[]
 for i,(a,pa) in enumerate(paths):
  for b,pb in paths[i+1:]:
   inter=pa.intersection(pb)
   if not inter.is_empty:
    if pa.crosses(pb) or inter.geom_type in ('LineString','MultiLineString'):crosses.append([a,b,inter.wkt])
    else:touches.append([a,b,inter.wkt])
 if crosses or touches:
  (TMP/(name+'_引线问题.json')).write_text(json.dumps({'crosses':crosses,'touches':touches},ensure_ascii=False,indent=2))
  raise ValueError((name,'leader intersections',len(crosses),len(touches),crosses[:2],touches[:2]))
 c.save(name,svg=full)
 if full:c.im.resize((2100,round(H*2100/W)),Image.Resampling.LANCZOS).save(TMP/'核对总图_预览.png')
 return {'file':name+'.png','width':W,'height':H,'questions':len(qs),'first':qs[0]['number'],'last':qs[-1]['number'],'crossings':0,'anchor_errors':sum(not Polygon(sp[q['sid']]['polygon_px']).buffer(.1).covers(__import__('shapely').geometry.Point(anchors[q['sid']])) for q in qs)}
reports=[]
reports.append(make('核对总图_高清','08 青岛西海岸医疗中心 · 完整原图核对总图',review,full=True))
# Supplementary crops retain continuous neighboring spaces; no individual-room collage.
sections=[
 ('01_北部_核对01-22',lambda q:q['group'][0] in 'AB',(125,205,610,480)),
 ('02_东北部',lambda q:q['group'][0]=='C',(500,430,1005,645)),
 ('03_西侧上段',lambda q:q['group'][0]=='D' and q['bounds'][1]<845,(165,575,640,850)),
 ('04_西侧下段',lambda q:q['group'][0]=='D' and q['bounds'][1]>=845,(165,840,520,1098)),
 ('05_儿科',lambda q:q['group'][0]=='F',(550,575,1060,805)),
 ('06_急诊ICU',lambda q:q['group'][0]=='G',(700,880,1055,1098)),
 ('07_西南上段',lambda q:q['group'][0]=='H' and q['bounds'][1]<1240,(165,1085,520,1248)),
 ('08_西南下段',lambda q:q['group'][0]=='H' and q['bounds'][1]>=1240,(165,1235,520,1370)),
 ('09_东南急诊',lambda q:q['group'][0]=='I',(720,1085,1055,1255)),
 ('10_南侧入口',lambda q:q['group'][0]=='J',(510,1305,900,1385))]
for name,selector,b in sections:
 qs=[q for q in review if selector(q)]
 reports.append(make(name,'08 · '+name+' · 密集片区放大',qs,tuple(int(v*2) for v in b),scale=3))
(TMP/'核对图校验.json').write_text(json.dumps({'total_questions':len(review),'unique_numbers':len(set(q['number'] for q in review)),'unique_space_ids':len(set(q['sid'] for q in review)),'numbers_continuous':[int(q['number']) for q in review]==list(range(1,len(review)+1)),'reports':reports},ensure_ascii=False,indent=2)+'\n')
lines=['# 08 青岛西海岸医疗中心：待确认核对材料','',f'标注草稿，{len(review)} 项待确认。候选不会自动成为确定名称。','', '[完整原图高清核对总图 PNG](核对总图_高清.png) · [可缩放核对总图 SVG](核对总图_高清.svg)','', '按相邻片区从上到下、同排从左到右读取。可以直接回复 `01=名称，02=名称`，也可以使用 S 编号；支持分批确认。','', '| 片区 | 核对号 | 放大图 |','|---|---|---|']
for r in reports[1:]:lines.append(f'|{r["file"].split(".")[0]}|{r["first"]}—{r["last"]}|[查看]({r["file"]})|')
lines+=['','四个白色庭院／上空范围和北侧绿色范围，除用途外还需确认是否室外、屋面或挑空；确认后再决定是否纳入室内面积。','', '|核对号|S 编号|候选／待确认|简短依据|把握|','|---|---|---|---|---|']
for q in review:lines.append(f'|{q["number"]}|{q["sid"]}|{q["candidate"]}|{q["basis"]}|{q["confidence"]}|')
(TMP/'核对索引.md').write_text('\n'.join(lines)+'\n')
(TMP/'回复模板.txt').write_text('\n'.join(q['number']+'=' for q in review)+'\n')
print(json.dumps({'questions':len(review),'rendered':len(reports),'all_crossings':sum(r['crossings'] for r in reports),'anchor_errors':sum(r['anchor_errors'] for r in reports)},ensure_ascii=False))
