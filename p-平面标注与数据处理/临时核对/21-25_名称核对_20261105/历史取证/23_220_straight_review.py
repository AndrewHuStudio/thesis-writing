from pathlib import Path
from collections import defaultdict
import json, math, bisect
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import Polygon,LineString,Point
from shapely.affinity import scale,translate
from shapely.strtree import STRtree

TMP=Path('/tmp/outpatient23-review');ROOT=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-写作过程/标注试样/23_西安经开医院')
review=json.loads((TMP/'review_mapping.json').read_text());data=json.loads((ROOT/'annotation.json').read_text())
W,H=6900,8500;OX,OY=1000,1000;PS=2
left_groups={'02左侧放射','03中央中段','05左下药房','08左下老年'}
groups=list(dict.fromkeys(r['group'] for r in review));colors=['#be123c','#1d4ed8','#7c3aed','#0f766e','#c2410c','#a21caf','#0369a1','#4d7c0f'];cm=dict(zip(groups,colors))
# Shared row ordinate makes targets preserve top-to-bottom, left-to-right order.
for group in groups:
 rs=[r for r in review if r['group']==group];rows=[]
 for r in rs:
  y=min(y for x,y in r['polygon_px'])
  if not rows or abs(y-rows[-1][0])>20:rows.append([y,[]])
  rows[-1][1].append(r)
 for _,row in rows:
  yy=max(min(y for x,y in r['polygon_px']) for r in row)
  for r in row:
   p=Polygon(r['polygon_px']);cross=p.intersection(LineString([(0,yy),(2444,yy)]))
   segs=list(cross.geoms) if hasattr(cross,'geoms') else [cross];segs=[q for q in segs if q.geom_type=='LineString']
   if not segs:raise RuntimeError(('bad row',r['number'],yy))
   a=max(segs,key=lambda q:q.length).interpolate(.5,normalized=True)
   r['anchor']=(OX+a.x*PS,OY+yy*PS);r['poly']=translate(scale(p,xfact=PS,yfact=PS,origin=(0,0)),OX,OY);r['side']='left' if group in left_groups else 'right'

allpolys=[translate(scale(Polygon(s['polygon_px']),xfact=PS,yfact=PS,origin=(0,0)),OX,OY) for s in data['spaces'] if s['type'] not in ('hall','corridor')]
tree=STRtree(allpolys)

def arrange(side):
 rs=[r for r in review if r['side']==side];n=len(rs);B=650 if side=='left' else 6200;sgn=-1 if side=='left' else 1
 xs=[sgn*r['anchor'][0] for r in rs];ys=[r['anchor'][1] for r in rs];bb=sgn*B
 lo=np.full(n,330.);hi=np.full(n,H-300.)
 for i in range(n):
  for j in range(i+1,n):
   ai,bi,aj,bj=xs[i],ys[i],xs[j],ys[j]
   if abs(ai-aj)<1e-6:
    assert bi<bj,(side,rs[i]['number'],rs[j]['number'],bi,bj)
   elif ai<aj:hi[i]=min(hi[i],bi+(bj-bi)*(bb-ai)/(aj-ai)-4)
   else:lo[j]=max(lo[j],bj+(bi-bj)*(bb-aj)/(ai-aj)+4)
 delta=[0]+[38 if rs[i]['group']==rs[i-1]['group'] else 64 for i in range(1,n)]
 # Propagate feasibility before choosing any label positions.
 for i in range(1,n):lo[i]=max(lo[i],lo[i-1]+delta[i])
 for i in range(n-2,-1,-1):hi[i]=min(hi[i],hi[i+1]-delta[i+1])
 for i in range(n):
  if lo[i]>hi[i]:raise RuntimeError(('infeasible',side,rs[i]['number'],lo[i],hi[i]))
 last=0
 for i,r in enumerate(rs):
  lower=max(lo[i],last+delta[i]);upper=hi[i];ax,ay=r['anchor']
  ideal=ay+(160 if side=='left' else -160)
  vals=set(np.linspace(lower,upper,45).tolist()+[max(lower,min(upper,ideal))])
  best=None
  for yy in vals:
   line=LineString([(B,yy),(ax,ay)])
   # Penalize drawing through unrelated rooms; endpoint's own room is exempt.
   lengths=[]
   for k in tree.query(line):
    poly=allpolys[int(k)]
    if poly.equals(r['poly']):continue
    inner=poly.buffer(-4)
    if not inner.is_empty:
     val=line.intersection(inner).length
     if val>0:lengths.append(val)
   score=sum(lengths)*12+abs(yy-ideal)*.06
   candidate=(score,yy)
   if best is None or candidate<best:best=candidate
  r['label_y']=best[1];r['port']=(B,best[1]);r['path']=[r['port'],r['anchor']];last=best[1]
 print(side,'labels',n,'range',round(rs[0]['label_y']),round(rs[-1]['label_y']),flush=True)
arrange('left');arrange('right')
collisions=[]
for i,a in enumerate(review):
 for b in review[i+1:]:
  q=LineString(a['path']).intersection(LineString(b['path']))
  if not q.is_empty:collisions.append([a['number'],b['number'],q.wkt])
print('crossings',len(collisions),flush=True)
assert not collisions,collisions[:4]
(TMP/'leader_paths.json').write_text(json.dumps({r['number']:r['path'] for r in review}))
(TMP/'leader_check.json').write_text(json.dumps({'leaders':len(review),'crossings':collisions},ensure_ascii=False,indent=2))

FONT='/System/Library/Fonts/PingFang.ttc';fs={}
def font(n):
 if n not in fs:fs[n]=ImageFont.truetype(FONT,n)
 return fs[n]
im=Image.new('RGB',(W,H),'#f1f5f9');d=ImageDraw.Draw(im)
def txt(x,y,t,size=18,color='#172c42'):d.text((round(x),round(y)),t,font=font(size),fill=color)
source=Image.open(ROOT/data['image']['file']);im.paste(source.resize((2444*PS,3260*PS)),(OX,OY))
txt(80,55,'23_西安经开医院｜一层平面 · 名称核对总图',48)
txt(80,125,'标注草稿：219 个空间／区域，166 项名称待确认。完整原图居中；彩框、核对号、S编号、边栏和引线一一对应。',25)
txt(80,174,'按相邻片区从上到下、同排从左到右核对。支持分批回复：01=名称，02=名称。候选并非确定名称，核心 JSON 保持 unknown。',23)
txt(80,217,'绿色区域请同时说明“露天／挑空”或“室内可步入”。全部候选、图面依据与把握程度见《核对清单.md》。',22)
for r in review:
 p=r['path'];color=cm[r['group']]
 d.line(p,fill='white',width=5);d.line(p,fill=color,width=2)
for r in review:
 color=cm[r['group']];p=list(r['poly'].exterior.coords);d.line(p,fill=color,width=4)
 a=r['anchor'];d.ellipse((a[0]-4,a[1]-4,a[0]+4,a[1]+4),fill=color)
 pt=r['poly'].representative_point();n=r['number'];width=d.textbbox((0,0),n,font=font(18))[2]+14
 d.rounded_rectangle((pt.x-width/2,pt.y-14,pt.x+width/2,pt.y+14),radius=4,fill='white',outline=color,width=2)
 txt(pt.x-width/2+7,pt.y-13,n,18,color)
 x1=35 if r['side']=='left' else 6200;x2=650 if r['side']=='left' else 6865;y=r['label_y']
 d.rounded_rectangle((x1,y-17,x2,y+17),radius=5,fill='white',outline=color,width=1)
 txt(x1+10,y-16,f'{r["number"]}｜{r["id"]}  '+' / '.join(r['candidates']),16,color)
 txt(x1+10,y+3,f'把握：{r["confidence"]} · {r["group"][2:]}',11,'#52677b')
# Use separate color swatches above the sheet, avoiding any label overlap.
for gi,g in enumerate(groups):
 x=80+(gi%4)*1650;y=285+(gi//4)*42;rs=[r for r in review if r['group']==g]
 d.rectangle((x,y+4,x+18,y+22),fill=cm[g]);txt(x+30,y,g[2:]+'  '+rs[0]['number']+'—'+rs[-1]['number'],20,cm[g])
txt(80,H-170,'核对号在同轮分批回答中固定；也可直接按 S 编号回答。已确认的答案保留，未回复项继续显示“名称未确认”。',24)
txt(80,H-120,'临时核对材料，不修改原图。名称确认后同步 JSON / SVG / MD，再依次 normalize → render → summary → validate --check-dir。',22)
txt(80,H-77,'SVG 草稿直接显示 S编号和名称；缺少名称及关系不作为训练真值或不可达结论。',21)
im.save(TMP/'23_西安经开医院_高清核对总图.png',optimize=True)
im.resize((1624,2000)).save(TMP/'核对总图_预览.jpg',quality=92)
for name,b in [('急诊_密集局部',(1345,370,2310,835)),('放射_密集局部',(170,975,1175,1695)),('体检_密集局部',(1355,2380,2310,2860))]:
 bb=(OX+b[0]*PS,OY+b[1]*PS,OX+b[2]*PS,OY+b[3]*PS);im.crop(bb).save(TMP/(name+'.png'))
lines=['# 23_西安经开医院：名称核对清单','',f'标注草稿；{len(review)} 项待确认。核对号与 S 编号在本轮分批回答时保持固定。候选未写入核心 JSON。','', '查看完整高清核对总图；回复示例：`01=设备间，02=诊室`。也可直接用 S 编号。','', '七处绿色区域请同时确认名称和露天／室内属性；确认前临时计入标注区域的相对面积分母。','']
for group in groups:
 lines+=['## '+group[2:],'','| 核对号 | S编号 | 候选用途（最多两个） | 图面依据 | 把握 |','|---|---|---|---|---|']
 for r in review:
  if r['group']==group:lines.append(f'| {r["number"]} | {r["id"]} | '+'；'.join(r['candidates'])+f' | {r["evidence"]} | {r["confidence"]} |')
 lines.append('')
(TMP/'核对清单.md').write_text('\n'.join(lines)+'\n')
print('written',im.size,flush=True)