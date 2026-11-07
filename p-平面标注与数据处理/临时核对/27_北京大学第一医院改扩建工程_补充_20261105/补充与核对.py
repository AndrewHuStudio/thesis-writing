from pathlib import Path
import json,copy,importlib.util,xml.etree.ElementTree as ET,os
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import Polygon,LineString
BASE=Path(__file__).resolve().parent
ROOT=BASE.parent.parent/'标注试样/27_北京大学第一医院改扩建工程'
SKILL=Path('/Users/hushili/.codex/skills/outpatient-plan-annotation')
d=json.loads((BASE/'续作前备份/annotation.json').read_text())
W=d['image']['width'];H=d['image']['height']
def orig(x,y):return [W-1-y,x]
def upright(s):return [(y,W-1-x) for x,y in s['polygon_px']]
spaces={s['id']:s for s in d['spaces']}
# 沿用首次发布的24个核对号；与历史候选图一一对应。
rows=[
('S002','办公','工作人员休息室','紧邻标6办公；无本间文字。两候选仅共用片区线索，不能区分。','低',(420,610)),
('S007','清洁间','卫生间','可见单个盆形设施，邻接卫生间；设施不足以区分两候选。','低',(872,634)),
('S008','候等休息区','工作人员支持用房','可见成排座椅；座椅不能确定服务对象，两候选共用该依据。','低',(930,638)),
('S009','暂无可靠候选','—','无可读用途文字及可区分功能的设施；依据不足。','低',(1002,620)),
('S010','办公','工作人员支持用房','位于标6办公南侧；两候选仅依片区功能推测，缺乏房间级证据。','低',(171,679)),
('S011','库房','设备用房','楼梯与电梯旁狭窄小间；尺寸与位置不能区分两候选。','低',(280,680)),
('S013','办公','工作人员支持用房','收费区西北侧独立间；两候选仅依片区功能推测，缺乏房间级证据。','低',(190,810)),
('S015','暂无可靠候选','—','西侧狭长围合区，无图例数字或可辨用途设施；不能仅凭形状指定用途。','低',(188,1020)),
('S020','办公','工作人员支持用房','邻接标6办公，有朝走道的门；开门只支持连接，不能区分两候选功能。','低',(460,1320)),
('S026','工作人员支持用房','办公','可见洗涤／茶水类设施，邻接标6办公；设施不足以确定具体功能。','低',(2220,574)),
('S030','办公','工作人员支持用房','楼梯旁独立大间，有门朝通道；两候选仅依片区功能推测，缺乏房间级证据。','低',(2520,650)),
('S031','库房','设备用房','外墙小间，无可读用途文字；两候选共用小间形态线索，不能区分。','低',(2620,631)),
('S034','库房','设备用房','外墙窄小间，无可读用途文字；图面不足以区分两候选。','低',(2620,694)),
('S035','库房','工作人员支持用房','办公旁小间，有门朝药房；门只支持连接，功能仅依片区推测。','低',(2295,750)),
('S037','办公','工作人员支持用房','与标6办公S038有门相通，另有门朝走道；两候选功能仍缺乏文字依据。','低',(2510,800)),
('S040','库房','工作人员支持用房','办公旁狭窄小间，有门朝药房；两候选仅依片区功能推测。','低',(2291,890)),
('S045','设备用房','库房','信息中心东侧小隔间，无用途文字；位置与尺寸不能区分两候选。','低',(2622,958)),
('S046','设备用房','工作人员支持用房','信息中心东侧独立间，有门朝横向走道；两候选仅依片区功能推测。','低',(2622,1020)),
('S047','信息中心','其他服务用房','圈⑤与普通5图例形式不同。若同义则支持信息中心；若另有含义，现图不足以确定其他具体功能。','中',(2520,1250)),
('S048','设备用房','工作人员支持用房','东侧独立小间，有门朝横向走道；两候选仅依片区功能推测。','低',(2622,1155)),
('S049','信息中心','其他服务用房','圈⑤与普通5图例形式不同。若同义则支持信息中心；若另有含义，现图不足以确定其他具体功能。','中',(2330,1255)),
('S051','服务工作区','库房','大厅东南角围合区，有朝大厅的门；两候选共用位置与围合线索，功能依据较弱。','低',(2020,1330)),
('S052','库房','设备用房','东南外墙小间，无用途文字及可靠设施线索；两候选不能区分。','低',(2620,1275)),
('S053','办公','工作人员支持用房','南端独立房间，有门朝东翼通道；两候选仅依片区功能推测。','低',(2330,1345))]
mapping=[dict(check=f'{i:02d}',id=a,candidate=b,alternative=c,basis=e,confidence=f,badge_xy=g) for i,(a,b,c,e,f,g) in enumerate(rows,1)]
assert {m['id'] for m in mapping}=={s['id'] for s in d['spaces'] if s['type']=='unknown'}
(BASE/'固定核对映射.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2)+'\n')
# 原有关系编号不重排；仅增加有明确门洞证据的漏连。
d['relations'].append(dict(id='R054',source='S027',target='S037',type='access'))
d['relations'].append(dict(id='R055',source='S027',target='S032',type='access'))
d['relations'].append(dict(id='R056',source='S024',target='S026',type='access'))
# 旧草稿把房门朝向与相邻公共空间混淆；按原图更正，编号沿用。
for r in d['relations']:
 if r['id']=='R019':r.update(source='S005',target='S007')
 if r['id']=='R046':r.update(source='S054',target='S053')
 if r['id']=='R010':r.update(source='S014',target='S019')
# S015唯一入口尚不可辨；楼梯经S018进入办公，不另造直接边。
d['relations']=[r for r in d['relations'] if r['id'] not in {'R014','R015'}]
# 填回楼梯南侧大厅的实际接近区；东翼大厅/走道边界移到可见分隔门。
from shapely.geometry import box
q=Polygon(upright(spaces['S022'])).union(box(1028,594,1087,666))
spaces['S022']['polygon_px']=[orig(x,y) for x,y in list(q.exterior.coords)[:-1]]
q=Polygon(upright(spaces['S024']))
pts=upright(spaces['S024']);pts=[(2148,608) if (x,y)==(2064,650) else (x,y) for x,y in pts]
spaces['S024']['polygon_px']=[orig(x,y) for x,y in pts]
q=Polygon(upright(spaces['S027'])).difference(box(2070,607,2153,648))
spaces['S027']['polygon_px']=[orig(x,y) for x,y in list(q.exterior.coords)[:-1]]
# 旧南侧外部入口坐标落在内部侧门，暂撤下并保留E002/E003编号，等待K01。
d['relations']=[r for r in d['relations'] if r['id'] not in {'E002','E003'}]
for r in d['relations']:
 if r['id']=='E005':r.update(target='S054',name='东南楼梯前室外部出口',position_px=orig(2440,1377))
d['relations'].append(dict(id='E006',source=None,target='S027',type='entrance',name='东北走道外部出口',entrance_type='pedestrian',position_px=orig(2440,532)))
# 逐门目视判读的转正图坐标；不以共墙中点自动生成门位。
points={
'R001':[(240,650)],'R002':[(497,610)],'R003':[(552,600)],
'R004':[(500,681),(500,710)],'R005':[(218,697)],'R006':[(280,723)],
'R007':[(520,773)],'R008':[(251,800)],'R009':[(366,1178)],
'R010':[(520,1190)],'R011':[(485,1268)],'R012':[(430,1295)],
'R016':[(548,743)],'R017':[(774,660)],'R018':[(1065,593)],
'R019':[(855,620)],'R020':[(900,658)],'R021':[(1000,658)],
'R022':[(618,798),(618,1165)],
'R023':[(1310,655),(1360,655)],'R026':[(1415,655),(1460,655)],
'R025':[(1283,1300),(1283,1350)],'R029':[(1486,1300),(1486,1350)],
'R030':[(2050,1239)],'R031':[(2151,625)],'R032':[(2190,1190)],
'R033':[(2415,685)],'R034':[(2543,1071)],
'R035':[(2240,606)],'R036':[(2390,606)],
'R037':[(2470,560)],'R038':[(2530,715)],'R039':[(2415,727)],
'R040':[(2415,907)],'R041':[(2471,880)],'R042':[(2415,948),(2415,1160)],
'R043':[(2543,1106),(2470,1210)],'R044':[(2615,1071)],'R045':[(2613,1106)],
'R046':[(2415,1333)],'R047':[(2441,1310)],'R048':[(2468,1343)],
'R049':[(2274,820)],'R050':[(2274,762)],'R051':[(2274,893)],
'R052':[(2415,1215)],'R053':[(2562,820)],'R054':[(2485,745)],
'R055':[(2252,650)],'R056':[(2090,606)]}
pnum=0
for r in d['relations']:
 if r['id'] in points:
  r['openings']=[]
  for x,y in points[r['id']]:
   kind='open_passage' if r['id'] in {'R013','R017'} else 'door'
   pnum+=1;r['openings'].append(dict(id=f'P{pnum:03d}',kind=kind,position_px=orig(x,y)))
(ROOT/'annotation.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
# 绘制总图与局部图，核对号置于房内，原图保持原样。
fontfile='/System/Library/Fonts/Supplemental/Arial Unicode.ttf'
def font(n):return ImageFont.truetype(fontfile,n)
base=Image.open(BASE/'转正全图.png').convert('RGB')
colors=['#c2410c','#a21caf','#2563eb','#0f766e','#7c3aed','#be123c']
def badge(dr,x,y,label,size=19,color='#9a3412'):
 ft=font(size);bb=dr.textbbox((0,0),label,font=ft);bw=bb[2]-bb[0]+8;bh=bb[3]-bb[1]+6
 dr.rounded_rectangle((x-bw/2,y-bh/2,x+bw/2,y+bh/2),radius=3,fill='white',outline=color,width=1)
 dr.text((x-(bb[2]-bb[0])/2,y-(bb[3]-bb[1])/2-bb[1]),label,font=ft,fill=color)
M=680;TOP=125;canvas=Image.new('RGB',(H+M*2,W+TOP+90),'#f8fafc');canvas.paste(base,(M,TOP));dr=ImageDraw.Draw(canvas)
dr.text((35,20),'27 北京大学第一医院改扩建工程｜24项名称核对',font=font(36),fill='#17324d')
dr.text((35,73),'沿用原核对号：左栏01—09，右栏10—24。填写见标注说明.md；候选尚未确认。',font=font(24),fill='#52677b')
left_ys=[590,611,632,650,687,713,812,1000,1330]
right_ys=[570,621,648,695,750,795,888,957,1020,1145,1170,1225,1245,1275,1330]
lines=[]
for j,m in enumerate(mapping):
 left=j<9;idx=j if left else j-9;color=colors[(idx//3)%len(colors)];poly=Polygon(upright(spaces[m['id']]));ay=(left_ys if left else right_ys)[idx]
 cross=poly.intersection(LineString([(-1,ay),(H+1,ay)]));assert not cross.is_empty
 ax=cross.bounds[0 if left else 2];X=M+ax;Y=TOP+ay;border=M-20 if left else M+H+20
 lx=25 if left else M+H+75;ly=TOP+(500+105*idx if left else 410+100*idx);lw=575;lh=86
 attach=(lx+lw,ly+lh/2) if left else (lx,ly+lh/2);path=[(X,Y),(border,Y),attach];lines.append(LineString(path))
 dr.line(path,fill=color,width=2);q=[(M+x,TOP+y) for x,y in poly.exterior.coords];dr.line(q,fill=color,width=3)
 bx,by=m['badge_xy'];badge(dr,M+bx,TOP+by,m['check'],17 if m['id'] in {'S035','S040'} else 20,color)
 dr.rounded_rectangle((lx,ly,lx+lw,ly+lh),radius=7,fill='white',outline=color,width=2)
 dr.text((lx+12,ly+5),f"{m['check']}｜{m['id']} 名称未确认",font=font(25),fill=color)
 dr.text((lx+12,ly+36),m['candidate']+' / '+m['alternative'],font=font(21),fill='#1e293b')
 dr.text((lx+12,ly+63),'把握：'+m['confidence'],font=font(17),fill='#64748b')
crossings=[(i+1,j+1) for i,a in enumerate(lines) for j,b in enumerate(lines) if j>i and a.intersects(b)]
assert not crossings,crossings
canvas.save(BASE/'27_完整核对总图.png');canvas.resize((2206,1280)).save(BASE/'27_核对总图预览.png')
groups=[
('01',(340,505,580,790),[1]),('02-04',(670,505,1120,800),[2,3,4]),
('05-07',(110,625,580,900),[5,6,7]),('08-09',(105,820,650,1420),[8,9]),
('10-13',(2030,495,2690,790),[10,11,12,13]),('14-16',(2115,685,2690,950),[14,15,16]),
('17-18',(2390,910,2690,1120),[17,18]),('19-24',(1840,1070,2700,1435),[19,20,21,22,23,24])]
for name,box,nums in groups:
 scale=2.5;im=base.crop(box).resize((int((box[2]-box[0])*scale),int((box[3]-box[1])*scale)));dd=ImageDraw.Draw(im)
 for n in nums:
  m=mapping[n-1];q=upright(spaces[m['id']]);dd.line([((x-box[0])*scale,(y-box[1])*scale) for x,y in q+[q[0]]],fill='#c2410c',width=4)
  x,y=m['badge_xy'];badge(dd,(x-box[0])*scale,(y-box[1])*scale,m['check'],35 if m['id'] in {'S035','S040'} else 44)
 im.save(BASE/f'名称_{name}_局部.png');base.crop(box).resize(im.size).save(BASE/f'名称_{name}_无标记.png')
# 连通局部：所有相关房间／大厅内部写稳定S编号，保留无标记对照。
kbox=(1130,1180,1600,1470);scale=2.5;im=base.crop(kbox).resize((1175,725));dd=ImageDraw.Draw(im)
for sid,pos in [('S022',(1185,1340)),('S023',(1190,1242)),('S024',(1540,1340)),('S025',(1380,1325))]:
 q=upright(spaces[sid]);dd.line([((x-kbox[0])*scale,(y-kbox[1])*scale) for x,y in q+[q[0]]],fill='#2563eb',width=3)
 badge(dd,(pos[0]-kbox[0])*scale,(pos[1]-kbox[1])*scale,sid[1:],40,'#1d4ed8')
im.save(BASE/'K01_南侧入口范围.png');base.crop(kbox).resize(im.size).save(BASE/'K01_无标记.png')
# S015有无通向西南走道的直接入口会改变主要可达网络，单列K02。
kbox=(105,750,650,1420);scale=2;im=base.crop(kbox).resize((1090,1340));dd=ImageDraw.Draw(im)
for sid,pos in [('S013',(180,810)),('S014',(450,950)),('S015',(185,1050)),('S018',(280,1270)),('S019',(570,1310)),('S020',(430,1330))]:
 q=upright(spaces[sid]);dd.line([((x-kbox[0])*scale,(y-kbox[1])*scale) for x,y in q+[q[0]]],fill='#2563eb',width=3)
 badge(dd,(pos[0]-kbox[0])*scale,(pos[1]-kbox[1])*scale,sid[1:],30,'#1d4ed8')
im.save(BASE/'K02_西侧狭长空间入口.png');base.crop(kbox).resize(im.size).save(BASE/'K02_无标记.png')
# 保存本轮语义更正记录在正式样本之外。
log={'added_access':['R054 S027-S037','R055 S027-S032','R056 S024-S026'], 'withdrawn_access':['R014 S018-S015','R015 S019-S017'],'retargeted_access':{'R010':'S014-S019','R019':'S005-S007','R046':'S054-S053'},'withdrawn_entrances':['E002','E003'], 'corrected_entrances':{'E005':'S054 东南楼梯前室外部出口'},'added_entrances':['E006 S027 东北走道外部出口'],'pending_key_questions':['K01','K02'], 'pending_names':24,'leader_crossings':len(crossings)}
(BASE/'本轮变更记录.json').write_text(json.dumps(log,ensure_ascii=False,indent=2)+'\n')
print('prepared mapping, review images, JSON;',pnum,'door points')
