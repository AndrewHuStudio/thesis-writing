from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import json, math
from shapely.geometry import Polygon, LineString
T=Path('/tmp/outpatient31-review')
M=json.loads((T/'layout.json').read_text())
U=[m for m in M if 'candidate' in m]
for i,m in enumerate(U,1):m['review_no']=f'{i:02d}'
(T/'review-map.json').write_text(json.dumps(U,ensure_ascii=False,indent=2)+'
')
font='/System/Library/Fonts/Supplemental/Arial Unicode.ttf'
def F(sz):return ImageFont.truetype(font,sz)
colors=['#b45309','#be185d','#0369a1','#7c3aed','#087f5b','#9f1239']
def color(m):
 i=int(m['review_no'])
 return colors[0 if i<=6 else 1 if i<=14 else 2 if i<=16 else 3 if i<=20 else 4 if i<=25 else 5]
def wrap(txt,font,width):
 rows=['']
 for c in txt:
  if font.getlength(rows[-1]+c)>width:rows.append('')
  rows[-1]+=c
 return rows
S=3; ox=1350;oy=230;W=8700;H=4880
im=Image.new('RGB',(W,H),'#f7f9fc');d=ImageDraw.Draw(im)
source=Image.open(T/'upright.png').convert('RGB').resize((6000,4500),Image.Resampling.LANCZOS)
im.paste(source,(ox,oy))
d.text((70,40),'31｜暨南大学附属第一医院综合楼工程 · 一层标注草稿核对总图',font=F(68),fill='#142c45')
d.text((70,135),'26项待确认｜按相邻片区编号｜底图仅逆时针转90°显示，完整原图未裁切；原文件及JSON坐标保持原样',font=F(38),fill='#465b70')
# All source extents remain visible. Highlight only unresolved units.
for m in U:
 c=color(m);pts=[(ox+x*S,oy+y*S) for x,y in m['upright_polygon']]
 d.line(pts+[pts[0]],fill=c,width=8,joint='curve')
# Sidebars have continuous numbered groups; preserve order inside every group.
prev={'left':880,'right':830};lines=[];boxes=[]
def group(n):
 n=int(n)
 return 'A 北侧药房及支持用房｜01—06' if n<=6 else 'B 北侧公共服务｜07—14' if n<=14 else 'C 中部庭院｜15' if n==15 else 'D 东北边界范围｜16' if n==16 else 'E 中部庭院与交通｜17—20' if n<=20 else 'F 影像科｜21—25' if n<=25 else 'G 南侧影像支持｜26'
lastg={}
for m in U:
 side=m['side'];n=m['review_no'];c=color(m);gy=group(n)
 P=Polygon(m['upright_polygon']);ay=m['anchor_y']
 q=P.intersection(LineString([(-10,ay),(2010,ay)]))
 bounds=q.bounds
 ax=bounds[0]+5 if side=='left' else bounds[2]-5
 px=ox+ax*S;py=oy+ay*S
 bh=138
 cy=max(py,prev[side]+bh+16)
 if lastg.get(side)!=gy:
  cy=max(cy,prev[side]+bh+65)
  gx=48 if side=='left' else 7445
  d.text((gx,cy-bh/2-51),gy,font=F(30),fill=c)
  lastg[side]=gy
 prev[side]=cy
 cardx=38 if side=='left' else 7432
 edge=1268 if side=='left' else 7432
 boundary=ox if side=='left' else ox+6000
 route=[(px,py),(boundary,py),(edge,cy)]
 lines.append((n,route));d.line(route,fill=c,width=4)
 # Matching numbered badge inside each target, attached to the horizontal leader.
 badge=(px+40 if side=='left' else px-40,py)
 d.line([(px,py),badge],fill=c,width=4)
 d.rounded_rectangle((badge[0]-40,badge[1]-29,badge[0]+40,badge[1]+29),radius=12,fill='white',outline=c,width=4)
 d.text((badge[0],badge[1]-2),n,font=F(40),fill=c,anchor='mm')
 d.ellipse((px-5,py-5,px+5,py+5),fill=c)
 d.rounded_rectangle((cardx,cy-bh/2,cardx+1230,cy+bh/2),radius=13,fill='white',outline=c,width=3)
 d.text((cardx+18,cy-bh/2+7),f'{n}｜{m["id"]}  候选：{m["candidate"]}',font=F(37),fill=c)
 d.text((cardx+18,cy-bh/2+59),'依据：'+m['basis'],font=F(29),fill='#364e64')
 d.text((cardx+18,cy-bh/2+101),'把握：'+m['confidence']+'；确认前JSON=unknown',font=F(27),fill='#5c6b77')
 boxes.append((n,[cardx,cy-bh/2,cardx+1230,cy+bh/2]))
# No crossings: each leader has its own horizontal level inside the image and ordered outer endpoints.
cross=[]
for i,(a,pa) in enumerate(lines):
 for b,pb in lines[i+1:]:
  z=LineString(pa).intersection(LineString(pb))
  if not z.is_empty:cross.append((a,b,z.wkt))
assert not cross,cross
assert len({m['id'] for m in U})==26
assert [m['review_no'] for m in U]==[f'{i:02d}' for i in range(1,27)]
d.text((70,4774),'回复格式：01=名称，02=名称；可分批，也可直接用S编号。15／17／19请补“露天、挑空或室内可步入”；16请说明范围性质。',font=F(35),fill='#14314a')
im.save(T/'31_高清核对总图.png',optimize=True)
im.resize((2175,1220)).save(T/'review-overview.png')
(T/'leader-check.json').write_text(json.dumps(dict(pending=26,leaders=len(lines),crossings=cross,unique_mapping=True,original_image_shown='full, counterclockwise 90 degrees',cards=boxes),ensure_ascii=False,indent=2))
# Supplemental dense-area zooms use the same review numbers and do not replace the full source sheet.
base=Image.open(T/'upright.png').convert('RGB').resize((4000,3000),Image.Resampling.LANCZOS)
bd=ImageDraw.Draw(base)
for m in U:
 c=color(m);pts=[(x*2,y*2) for x,y in m['upright_polygon']];bd.line(pts+[pts[0]],fill=c,width=5,joint='curve')
 p=Polygon(m['upright_polygon']).representative_point();x=p.x*2;y=p.y*2
 bd.rounded_rectangle((x-39,y-26,x+39,y+26),radius=8,fill='white',outline=c,width=3)
 bd.text((x,y-1),m['review_no'],font=F(36),fill=c,anchor='mm')
for name,b in [('北侧服务区放大',(930,275,1340,590)),('影像科及南侧支持放大',(235,580,785,963)),('中部庭院交通放大',(765,420,1132,800))]:
 crop=base.crop(tuple(int(v*2) for v in b))
 crop=crop.resize((crop.width*2,crop.height*2),Image.Resampling.LANCZOS)
 canvas=Image.new('RGB',(crop.width,crop.height+105),'white');canvas.paste(crop,(0,105));cd=ImageDraw.Draw(canvas)
 cd.text((20,20),'31｜'+name+'（沿用核对号）',font=F(40),fill='#17334e');canvas.save(T/(name+'.png'))
rows=['# 31号一层标注草稿：26项集中核对','', '编号固定，可分批按 `01=名称，02=名称` 回答。候选仅用于提问，核心JSON保持unknown。','', '|核对号|S编号|候选用途|图面依据|把握|','|---|---|---|---|---|']
for m in U:rows.append(f'|{m["review_no"]}|{m["id"]}|{m["candidate"]}|{m["basis"]}|{m["confidence"]}|')
rows+=['','15、17、19请同时确认是露天/挑空，还是室内可步入。16请确认东北空白范围是否属于室外平台、预留室内空间或不应标注。','已确认名称只写回本图；未回答项继续保持unknown。']
(T/'核对清单.md').write_text('
'.join(rows)+'
')
print('review:',im.size,'leaders:',len(lines),'crossings:',len(cross))
