from pathlib import Path
import json,math,sys
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import Polygon,LineString
T=Path('/tmp/outpatient24-review');P=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-写作过程/标注试样/24_成都市第三人民医院住院综合楼')
r=json.loads((T/'review-map.json').read_text());data=json.loads((P/'annotation.json').read_text())
FONT='/System/Library/Fonts/STHeiti Medium.ttc'
def font(n):return ImageFont.truetype(FONT,n)
colors={1:'#bb3e54',2:'#2267b4',3:'#8a42a4',4:'#087c69'}
S=2;OX=1100;OY=220;W=7000;H=6700
im=Image.new('RGB',(W,H),'#f5f7fb');d=ImageDraw.Draw(im)
src=Image.open(P/data['image']['file']).convert('RGB');im.paste(src.resize((4536,6216)),(OX,OY))
d.text((60,35),'24_成都市第三人民医院住院综合楼｜标注草稿·名称核对总图',font=font(42),fill='#17314b')
d.text((60,100),'45项待确认  ·  原图方向：从上到下、同排从左到右；按相邻片区连续编号  ·  回复：01=名称，02=名称（可分批）',font=font(28),fill='#465a70')
d.text((60,154),'候选仅供核对；核心 JSON 均保持 unknown。彩框与核对号一一对应，标签同时保留稳定 S 编号。',font=font(26),fill='#8f4919')
def wrap(t,maxchars):
 lines=[]; cur=''
 for c in t:
  if len(cur)>=maxchars:lines.append(cur);cur=''
  cur+=c
 if cur:lines.append(cur)
 return lines
leaders=[]; boxes=[]
for side in ['left','right']:
 rr=[x for x in r if x['side']==side]
 prev=-1
 for v in rr:
  p=Polygon(v['polygon_px']);a=p.representative_point();cy=max(a.y,prev+7)
  cy=min(cy,p.bounds[3]-3);prev=cy
  line=p.intersection(LineString([(-1,cy),(2269,cy)]))
  bounds=line.bounds
  cx=bounds[0] if side=='left' else bounds[2]
  v['anchor']=[cx,cy]
 for i,v in enumerate(rr):
  if side=='right': ly=800+i*133
  else:ly=OY+v['anchor'][1]*S
  v['label_center']=ly
  col=colors[v['group']];pts=[(OX+x*S,OY+y*S) for x,y in v['polygon_px']]
  overlay=Image.new('RGBA',im.size);od=ImageDraw.Draw(overlay);od.polygon(pts,fill=col+'16',outline=None);im.paste(overlay,(0,0),overlay);d=ImageDraw.Draw(im)
  d.line(pts+[pts[0]],fill=col,width=5)
  ax=OX+v['anchor'][0]*S;ay=OY+v['anchor'][1]*S
  # 图内等高平行段，图外统一折点；两个端点的顺序一致，避免引线交叉。
  edge=OX-25 if side=='left' else OX+4536+25
  end=990 if side=='left' else 5780
  points=[(ax,ay),(edge,ay),(end,ly)]
  d.line(points,fill=col,width=2)
  leaders.append(LineString(points));v['leader_px']=[list(p) for p in points]
  bx=OX+Polygon(v['polygon_px']).representative_point().x*S
  by=OY+Polygon(v['polygon_px']).representative_point().y*S
  badge=f"{v['number']}"
  d.rounded_rectangle((bx-32,by-25,bx+32,by+25),radius=9,fill='white',outline=col,width=3)
  d.text((bx,by-1),badge,font=font(31),anchor='mm',fill=col)
  x0,x1=(40,990) if side=='left' else (5780,6960)
  y0=ly-59;y1=ly+59
  d.rounded_rectangle((x0,y0,x1,y1),radius=12,fill='white',outline=col,width=3)
  d.rectangle((x0+2,y0+14,x0+10,y1-14),fill=col)
  d.text((x0+24,y0+8),f"{v['number']}｜{v['id']}  名称未确认  ·  把握{v['confidence']}",font=font(27),fill=col)
  d.text((x0+24,y0+43),'候选：'+v['candidate'],font=font(26),fill='#1e354b')
  basis=wrap('依据：'+v['basis'],42 if side=='right' else 33)
  d.text((x0+24,y0+81),basis[0],font=font(22),fill='#576779')
  if len(basis)>1:
   # 长依据在完整的临时文字清单保留；图上用短句，不缩到难读字号。
   d.text((x1-35,y0+82),'…',font=font(22),fill='#576779')
  boxes.append((x0,y0,x1,y1,v['number']))
# 严格检查引线交叉与标签重叠。
cross=[]
for i,a in enumerate(leaders):
 for j,b in enumerate(leaders[i+1:],i+1):
  if a.crosses(b) or a.overlaps(b):cross.append((i,j))
for i,a in enumerate(boxes):
 for b in boxes[i+1:]:
  if min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1]):raise ValueError(('label overlap',a[4],b[4]))
d.text((OX,6500),'阅读顺序：01–13 介入区 → 14–20 教学区 → 21–22 患者支持 → 23–45 静脉配液中心',font=font(27),fill='#17314b')
d.text((OX,6550),'完整原图未裁切、未改写；彩框为概念级轮廓。教学排椅房、机房及模糊小房均等待名称确认。',font=font(24),fill='#53667b')
im.save(T/'24_名称核对总图.png')
im.resize((2298,2200)).save(T/'24_名称核对总图_预览.png')
# 补充局部：临时正向图便于读取原房名；核对编号沿用总图。
u=Image.open(T/'upright.png').convert('RGB')
for name,bd,groups in [('介入与医护区_正向放大',(340,545,1420,1300),[1,3]),('教学区_正向放大',(1110,1440,2275,2005),[2]),('配液中心_正向放大',(1620,545,2630,1125),[4])]:
 z=3;c=u.crop(bd).resize(((bd[2]-bd[0])*z,(bd[3]-bd[1])*z));cd=ImageDraw.Draw(c)
 for v in r:
  if v['group'] not in groups:continue
  pp=[((y-bd[0])*z,(2268-x-bd[1])*z) for x,y in v['polygon_px']]
  co=colors[v['group']];cd.line(pp+[pp[0]],fill=co,width=6)
  a=Polygon(pp).representative_point();txt=f"{v['number']} | {v['id']}";f=font(30);bb=cd.textbbox((0,0),txt,font=f);ww=bb[2]-bb[0]+20
  cd.rounded_rectangle((a.x-ww/2,a.y-23,a.x+ww/2,a.y+23),radius=8,fill='white',outline=co,width=3)
  cd.text((a.x,a.y),txt,font=f,anchor='mm',fill=co)
 c.save(T/(name+'.png'))
(T/'review-map.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
(T/'review-layout-check.json').write_text(json.dumps(dict(numbers=len(r),unique_ids=len({x['id'] for x in r}),leader_crossings=cross,label_overlap_count=0),ensure_ascii=False,indent=2))
print('review saved; leader crossings',cross)