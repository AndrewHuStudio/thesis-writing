import json,hashlib,math,textwrap
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import LineString
P=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-写作过程/标注试样/21_海军总医院外科医疗大楼');T=Path('/tmp/outpatient21-review')
d=json.loads((P/'annotation.json').read_text());items=json.loads((T/'reading_items.json').read_text());ii={i['key']:i for i in items};ss={s['id']:s for s in d['spaces']}
font='/System/Library/Fonts/PingFang.ttc'
def ft(n):return ImageFont.truetype(font,n)
scale=2;ox=1120;oy=200;cw=2444*2+2240;ch=3260*2+300
im=Image.new('RGB',(cw,ch),'#f4f7fb');draw=ImageDraw.Draw(im)
source=Image.open(P/d['image']['file']);im.paste(source.resize((4888,6520),Image.Resampling.LANCZOS),(ox,oy))
draw.text((80,35),'21 海军总医院外科医疗大楼｜标注草稿 · 19项集中核对',font=ft(54),fill='#17324d')
draw.text((80,112),'完整原图保持原方向居中。按相邻片区编号；候选仅供核对，核心JSON均为unknown。可分批回复：01=名称，02=名称。',font=ft(31),fill='#56687e')
colors=['#2563eb','#0f766e','#7c3aed','#b45309','#a21caf','#0369a1','#be123c']
q=[]
def put(key,side,route,col):
 i=ii[key];q.append(dict(number=f'{len(q)+1:02d}',id=i['id'],key=key,side=side,route=route,color=colors[col],candidate=i['candidate'],evidence=i['evidence'],confidence=i['confidence']))
for n in range(1,6):
 k='acute_bed'+str(n);s=ss[ii[k]['id']];ys=[p[1] for p in s['polygon_px']];xx=min(p[0] for p in s['polygon_px']);yy=(min(ys)+max(ys))/2
 put(k,'left',[(xx,yy),(-40,yy)],0)
put('multi_bed','right',[(1370,233),(1370,45),(2484,45)],1)
put('med2','right',[(1530,233),(1530,105),(2484,105)],1)
put('med1','right',[(1620,233),(1620,165),(2484,165)],1)
put('preop','right',[(1664,363),(1664,225),(2484,225)],1)
put('acute_top','right',[(1958,624),(2484,624)],2)
put('stor2','right',[(1809,717),(2484,717)],2)
put('orth_side','right',[(1608,790),(1608,778),(1980,778),(2484,890)],3)
# orth_side original top edge is r x=844 (not 790); retain an anchor on its polygon.
q[-1]['route'][0]=(1608,844)
put('derm','left',[(1221,988),(-40,988)],3)
put('lab_side','right',[(1851,1040),(2484,1040)],4)
for key in ['physio','ecg','eeg','file']:
 s=ss[ii[key]['id']];ys=[p[1] for p in s['polygon_px']];xx=min(p[0] for p in s['polygon_px']);yy=(min(ys)+max(ys))/2
 put(key,'left',[(xx,yy),(-40,yy)],5)
put('elect_east','right',[(1585,2584),(2484,2584)],6)
assert len(q)==len([s for s in d['spaces'] if s['type']=='unknown'])
assert {v['id'] for v in q}=={s['id'] for s in d['spaces'] if s['type']=='unknown'}
# Test leader intersections before drawing.
lines=[LineString(v['route']) for v in q]
for a in range(len(lines)):
 for b in range(a+1,len(lines)):
  assert not lines[a].intersects(lines[b]),(q[a]['number'],q[b]['number'],'leader crossing')
def xy(p):return (ox+p[0]*scale,oy+p[1]*scale)
for v in q:
 s=ss[v['id']];pts=[xy(p) for p in s['polygon_px']];color=v['color']
 draw.line(pts+[pts[0]],fill='white',width=11,joint='curve');draw.line(pts+[pts[0]],fill=color,width=6,joint='curve')
 route=[xy(p) for p in v['route']]
 draw.line(route,fill='white',width=11,joint='curve');draw.line(route,fill=color,width=5,joint='curve')
 ax,ay=route[0];draw.ellipse((ax-7,ay-7,ax+7,ay+7),fill='white',outline=color,width=4)
 xs=[p[0] for p in pts];ys=[p[1] for p in pts];cx=(min(xs)+max(xs))/2;cy=(min(ys)+max(ys))/2
 label=v['number'];bb=draw.textbbox((0,0),label,font=ft(36));ww=bb[2]+24
 draw.rounded_rectangle((cx-ww/2,cy-28,cx+ww/2,cy+28),radius=8,fill=color,outline='white',width=3)
 draw.text((cx-ww/2+12,cy-26),label,font=ft(36),fill='white')
 ex,ey=route[-1];x0=70 if v['side']=='left' else ex+15;x1=ex-15 if v['side']=='left' else cw-55
 draw.rounded_rectangle((x0,ey-57,x1,ey+57),radius=12,fill='white',outline=color,width=3)
 draw.text((x0+18,ey-53),f"{v['number']}｜{v['id']}  {v['candidate']}",font=ft(30),fill=color)
 evidence=f"依据：{v['evidence']}（把握：{v['confidence']}）"
 # Compact evidence in one line with a smaller font when necessary.
 fs=25
 while draw.textlength(evidence,font=ft(fs))>x1-x0-35 and fs>20:fs-=1
 draw.text((x0+18,ey+1),evidence,font=ft(fs),fill='#45566e')
for text,x,y,col in [
 ('急诊左侧床位区 · 01—05',70,oy+360,0),
 ('急诊上缘 · 06—09',cw-1050,oy-10,1),
 ('急诊服务区 · 10—11',cw-1050,oy+1100,2),
 ('急诊中央 · 12—13',70,oy+1820,3),
 ('急诊检验旁 · 14',cw-1050,oy+1950,4),
 ('体检检查区 · 15—18',70,oy+4780,5),
 ('体检交通核旁 · 19',cw-1050,oy+4950,6)]:draw.text((x,y),text,font=ft(30),fill=colors[col])
# A row header must not collide with the first upper-right card; move it to the global subtitle instead.
# It is deliberately above that first card.
im.save(T/'21_高清核对总图.png',optimize=True)
small=im.copy();small.thumbnail((2200,2300));small.save(T/'21_核对总图预览.jpg',quality=92)
(T/'核对号对应.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n')
(T/'核对清单.md').write_text('# 21号待确认空间（本轮映射固定）\n\n'+'\n'.join(f"- {v['number']}｜{v['id']}：{v['candidate']}；依据：{v['evidence']}；把握：{v['confidence']}。" for v in q)+'\n')
# Supplementary dense-region detail: rotate only the temporary reading view.
r=source.transpose(Image.Transpose.ROTATE_90)
for name,b in [('21_急诊密集区核对放大',(225,480,1108,1398)),('21_体检密集区核对放大',(2480,840,2890,1350))]:
 fac=3;local=r.crop(b).resize(((b[2]-b[0])*fac,(b[3]-b[1])*fac),Image.Resampling.LANCZOS);ld=ImageDraw.Draw(local)
 for v in q:
  i=ii[v['key']];pts=i['rpoly'];cx=sum(p[0] for p in pts)/len(pts);cy=sum(p[1] for p in pts)/len(pts)
  if not (b[0]<=cx<=b[2] and b[1]<=cy<=b[3]):continue
  pp=[((x-b[0])*fac,(y-b[1])*fac) for x,y in pts]
  ld.line(pp+[pp[0]],fill=v['color'],width=6)
  label=v['number']+'｜'+v['id'];f=ft(28);bb=ld.textbbox((0,0),label,font=f);xx=(cx-b[0])*fac;yy=(cy-b[1])*fac
  ld.rectangle((xx-bb[2]/2-8,yy-24,xx+bb[2]/2+8,yy+22),fill='white',outline=v['color'],width=2);ld.text((xx-bb[2]/2,yy-22),label,font=f,fill=v['color'])
 local.save(T/(name+'.png'))
print(json.dumps(dict(review_size=im.size,pending=len(q),leader_intersections=0,mapping=[v['number']+'='+v['id'] for v in q]),ensure_ascii=False))