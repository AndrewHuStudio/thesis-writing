from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import Polygon,LineString,Point
import json,math
from pathlib import Path
TMP=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理/临时核对/29_内蒙古自治区国际蒙医医院扩建项目/20261105_空间与连通补充');ROOT=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理/标注试样/29_内蒙古自治区国际蒙医医院扩建项目')
rs=json.loads((TMP/'review-data.json').read_text()); pending=[r for r in rs if r['type']=='unknown']
fontpath='/System/Library/Fonts/STHeiti Medium.ttc'
def F(size):return ImageFont.truetype(fontpath,size)
colors=['#2563eb','#7c3aed','#0f766e','#c2410c','#be185d','#047857','#9a3412']
# Preserve stable S IDs, review numbers group adjacent regions independently.
for r in pending:
 p=Polygon(r['polygon_px']);a=p.representative_point();r['anchor']=[a.x,a.y]
 y=a.y
 r['band']=0 if y<570 else 1 if y<1072 else 2 if y<1435 else 3 if y<1734 else 4 if y<1902 else 5 if y<2360 else 6
 # upper/main left vs right wings/rooms; choose outward-facing leader side.
 r['side']='L' if a.x<(910 if r['band']<2 else 1040 if r['band']<5 else 1000) else 'R'
# Each adjacent group is a consecutive run; original top-to-bottom within each run.
ordered=[]
for band in range(7):
 for side in ['L','R']:
  subset=[r for r in pending if r['band']==band and r['side']==side]
  subset.sort(key=lambda r:(r['anchor'][1],r['anchor'][0]))
  ordered+=subset
for i,r in enumerate(ordered,1):r['review']=f'{i:02d}'
# Ensure distinct anchor y; parallel horizontal leaders cannot cross.
for side in ['L','R']:
 side_rs=sorted([r for r in ordered if r['side']==side],key=lambda r:r['anchor'][1])
 last=-100
 for r in side_rs:
  if r['anchor'][1]-last<.7:r['anchor'][1]=last+.7
  last=r['anchor'][1]
# Massive high-resolution poster, exact unrotated full source centered.
scale=2.5;sideW=1570;top=260;imageW=6110;imageH=8150;W=imageW+2*sideW;H=8750
X=sideW;Y=(H-imageH)//2
out=Image.new('RGB',(W,H),'#f4f7fb');d=ImageDraw.Draw(out)
source=Image.open(ROOT/'29_内蒙古自治区国际蒙医医院扩建项目_原图.jpg').convert('RGB').resize((imageW,imageH),Image.Resampling.LANCZOS);out.paste(source,(X,Y))
d.text((60,32),'29号｜内蒙古自治区国际蒙医医院扩建项目｜名称核对总图（标注草稿）',font=F(46),fill='#12324f')
d.text((60,100),'共136项待确认；按相邻片区自上而下，同排从左到右。回复：01=名称，02=名称；可分批或用S编号。',font=F(30),fill='#475569')
d.text((60,151),'原图完整居中、方向保持不变。候选及把握仅供核对；确认前核心JSON均为unknown。',font=F(28),fill='#9a3412')
# leader endpoints in empty source margins, beyond the architectural footprint.
rails={'L':X+360*scale,'R':X+2170*scale};labelEdges={'L':sideW-35,'R':X+imageW+35}
segments=[];boxes=[]
for side in ['L','R']:
 rows=sorted([r for r in ordered if r['side']==side],key=lambda r:r['anchor'][1])
 desired=[Y+r['anchor'][1]*scale for r in rows]
 gap=93
 ys=[]
 for y in desired:ys.append(max(y,ys[-1]+gap if ys else 270))
 if ys and ys[-1]>H-140:
  ys[-1]=H-140
  for i in range(len(ys)-2,-1,-1):ys[i]=min(ys[i],ys[i+1]-gap)
 for r,ly in zip(rows,ys):
  color=colors[r['band']];ax=X+r['anchor'][0]*scale;ay=Y+r['anchor'][1]*scale
  # Inner edges of outer labels connect to a fixed rail, then parallel horizontal routes.
  rail=rails[side];edge=labelEdges[side]
  pts=[(edge,ly),(rail,ay),(ax,ay)]
  r['leader_px']=pts;r['label_y']=ly
  for a,b in zip(pts,pts[1:]):segments.append((r['review'],side,LineString([a,b])))
  d.line(pts,fill='white',width=7);d.line(pts,fill=color,width=2)
  x=26 if side=='L' else X+imageW+30;w=sideW-55
  d.rounded_rectangle((x,ly-43,x+w,ly+43),radius=10,fill='white',outline=color,width=2)
  d.text((x+13,ly-41),f"{r['review']}｜{r['id']}  候选：{' / '.join(r['cand'])}",font=F(27),fill=color)
  basis=r['basis'];maxchar=49
  if len(basis)>maxchar:basis=basis[:maxchar-1]+'…'
  d.text((x+13,ly-6),f"把握{r['confidence']}｜{basis}",font=F(23),fill='#475569')
  boxes.append((r['review'],(x,ly-43,x+w,ly+43)))
# all colored outlines and badges above leaders
for r in ordered:
 color=colors[r['band']];pts=[(X+x*scale,Y+y*scale) for x,y in r['polygon_px']]
 d.line(pts+[pts[0]],fill=color,width=5)
 ax=X+r['anchor'][0]*scale;ay=Y+r['anchor'][1]*scale
 text=r['review'];bb=d.textbbox((0,0),text,font=F(29));bw=bb[2]+14
 d.rounded_rectangle((ax-bw/2,ay-18,ax+bw/2,ay+24),radius=6,fill='white',outline=color,width=3)
 d.text((ax-bw/2+7,ay-18),text,font=F(29),fill=color)
d.text((60,H-72),'概念级草稿：部分无名连续用房暂按功能块记录；绿色/中庭属性未确认。原图未改动。',font=F(28),fill='#475569')
out.save(TMP/'29_名称核对总图.png',optimize=True)
out.resize((1388,1313)).save(TMP/'review-preview.png')
# Prove one-to-one and no geometric crossings among leaders of distinct entries.
cross=[]
for i,(n,s,l) in enumerate(segments):
 for m,t,k in segments[i+1:]:
  if n!=m and l.crosses(k):cross.append((n,m))
print('poster',W,H,'labels',len(ordered),'sides',sum(r['side']=='L' for r in ordered),sum(r['side']=='R' for r in ordered),'leader crossings',len(cross))
if cross:print('crossings',cross[:30])
# List all mapping and evidence as editable temporary text; no review fields enter core JSON.
md=['# 29号名称核对清单（临时材料）','','136项待确认。回复 `01=名称，02=名称`；可分批，也可用S编号。候选不是确定名称。','','| 核对号 | S编号 | 候选用途 | 图面依据 | 把握 |','|---|---|---|---|---|']
for r in ordered:md.append(f"| {r['review']} | {r['id']} | {' / '.join(r['cand'])} | {r['basis']} | {r['confidence']} |")
(TMP/'29_核对清单.md').write_text('\n'.join(md)+'\n')
(TMP/'review-mapping.json').write_text(json.dumps(ordered,ensure_ascii=False,indent=2)+'\n')
# Supplementary enlarged sheets, reading orientation only; common numbering preserved.
read=Image.open(TMP/'reading.png').convert('RGB')
details=[('A_上部扇形翼',(80,1120,585,2010)),('B_上中部主楼',(585,1125,1072,1780)),('C_中部两侧密集区',(1072,990,1435,1780)),('D_橙色大空间及中心区',(1435,990,1902,1975)),('E_下部蓝色密集区',(1902,1070,2360,1960)),('F_右侧独立橙色区',(1580,330,2605,990))]
for name,b in details:
 fac=3;crop=read.crop(b).resize(((b[2]-b[0])*fac,(b[3]-b[1])*fac),Image.Resampling.LANCZOS)
 canvas=Image.new('RGB',(crop.width+100,crop.height+175),'white');canvas.paste(crop,(50,125));dd=ImageDraw.Draw(canvas)
 dd.text((30,20),'29号｜'+name+'（阅读方向局部放大）',font=F(31),fill='#12324f')
 dd.text((30,67),'核对号与总图相同；候选和依据见临时核对清单。',font=F(24),fill='#475569')
 shown=[]
 for r in ordered:
  p=Polygon(r['reading_polygon']);a=p.representative_point()
  if not (b[0]<=a.x<=b[2] and b[1]<=a.y<=b[3]):continue
  color=colors[r['band']];pts=[(50+(x-b[0])*fac,125+(y-b[1])*fac) for x,y in r['reading_polygon']]
  dd.line(pts+[pts[0]],fill=color,width=5)
  xx=50+(a.x-b[0])*fac;yy=125+(a.y-b[1])*fac
  label=f"{r['review']}｜{r['id']}";bb=dd.textbbox((0,0),label,font=F(22));ww=bb[2]+12
  dd.rounded_rectangle((xx-ww/2,yy-17,xx+ww/2,yy+20),radius=4,fill='white',outline=color,width=2)
  dd.text((xx-ww/2+6,yy-16),label,font=F(22),fill=color);shown.append(r['review'])
 canvas.save(TMP/(name+'.png'),optimize=True)
 print(name,len(shown))
# Poster dense crop for actual-size inspection
out.crop((0,2550,W,4150)).resize((2312,400)).save(TMP/'review-dense-preview.png')
# Save square SVG wrapper for Quick Look to preserve the full portrait canvas.
import xml.etree.ElementTree as ET
svg=ET.parse(ROOT/'标注.svg');rt=svg.getroot();rt.set('width','3600');rt.set('height','3600');svg.write(TMP/'draft-square.svg',encoding='utf-8',xml_declaration=True)