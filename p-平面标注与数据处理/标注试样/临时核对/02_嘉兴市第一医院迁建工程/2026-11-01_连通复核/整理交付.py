from pathlib import Path
import json,importlib.util,xml.etree.ElementTree as ET,math,collections,hashlib
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import box,LineString,Point
out=Path(__file__).parent;p=out.parents[2]/'02_嘉兴市第一医院迁建工程'
spec=importlib.util.spec_from_file_location('at','/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts/annotation_tools.py');at=importlib.util.module_from_spec(spec);spec.loader.exec_module(at)
d=json.loads((out/'更新草稿.json').read_text());old=json.loads((out/'修改前备份'/'annotation.json').read_text());at.normalize(d)
assert [(s['id'],s['name']) for s in d['spaces']]==[(s['id'],s['name']) for s in old['spaces']]
# Space IDs and names, all eight entrance records, service links and shared walls remain stable.
assert [r for r in d['relations'] if r['type']!='access']==[r for r in old['relations'] if r['type']!='access']
(p/'annotation.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
at.render(d,p/'annotation.json',p/'标注.svg');at.summary(d,out/'更新概览.md')
NS=at.NS;tag=lambda n:'{'+NS+'}'+n
root=ET.parse(p/'标注.svg').getroot();plan=next(e for e in root if e.get('id')=='plan');spgroups={e.get('id'):e for e in plan if (e.get('id') or '').startswith('S')}
# Full names of the three extremely thin corridor fragments are placed in local outer margins.
def callout(sid,x,y,w,anchor):
 g=spgroups[sid]
 for e in list(g):
  if e.tag in [tag('rect'),tag('text')]:g.remove(e)
 s=next(s for s in d['spaces'] if s['id']==sid);lines=[sid+' '+s['name'],'〔'+at.TYPE_NAMES[s['type']]+'〕'];fs=10;h=len(lines)*14+8
 g.append(at.element('line',{'x1':anchor[0],'y1':anchor[1],'x2':x if x>anchor[0] else x+w,'y2':y+h/2,'stroke':'#0f766e','stroke-width':'.7'}));g.append(at.element('rect',{'x':x,'y':y,'width':w,'height':h,'fill':'#fff7df' if s['type']=='unknown' else 'white','stroke':'#d97706' if s['type']=='unknown' else '#0f766e','fill-opacity':'.95'}))
 for i,line in enumerate(lines):g.append(at.txt(x+4,y+14+i*14,line,fs,'#0f766e',True))
callout('S023',2570,1730,214,(2480,1704));callout('S261',2570,390,214,(2426,420));callout('S269',2570,1515,214,(2500,1544));callout('S273',2570,1685,214,(2518,1705))
# S270 is a 9px-wide stable connector: use a short callout in the adjacent main-street space.
g=spgroups['S270']
for e in list(g):
 if e.tag in [tag('rect'),tag('text')]:g.remove(e)
g.append(at.element('polyline',{'points':'1939,1570 1760,1570 1760,1530 1755,1530','fill':'none','stroke':'#0f766e','stroke-width':'.7'}));g.append(at.element('rect',{'x':1658,'y':1490,'width':97,'height':58,'fill':'white','stroke':'#0f766e'}))
for i,t in enumerate(['S270 核医学工作','通道（分段2）','〔通道〕']):g.append(at.txt(1662,1506+i*14,t,10,'#0f766e',True))
# Place P labels in nearby clear areas; marker coordinates and relationship attributes remain untouched.
obstacles=[]
for g in spgroups.values():
 for e in g:
  if e.tag==tag('rect'):obstacles.append(box(float(e.get('x')),float(e.get('y')),float(e.get('x'))+float(e.get('width')),float(e.get('y'))+float(e.get('height'))).buffer(1))
markerpts=[Point(*o['position_px']).buffer(5.5) for r in d['relations'] for o in r.get('openings',[])];placed=[];unresolved_placement=[]
for g in [e for e in plan if e.get('data-opening-id')]:
 c=next(e for e in g if e.tag==tag('circle'));x=float(c.get('cx'));y=float(c.get('cy'));oid=g.get('id')
 for e in list(g):
  if e.tag==tag('text'):g.remove(e)
 candidates=[]
 for rad in [6,18,30,42,54,66]:
  for dx,dy in [(rad,-rad),(rad,rad),(-rad-24,-rad),(-rad-24,rad),(rad,-4),(-rad-24,-4),(-12,-rad-10),(-12,rad)]:
   xx=x+dx;yy=y+dy;b=box(xx-1,yy-9,xx+25,yy+2)
   if not (0<=xx<=2777 and 10<=yy<=2928):continue
   hit_space=sum(b.intersection(v).area for v in obstacles if b.intersects(v));hit_label=sum(b.intersection(v).area for v in placed if b.intersects(v));hit_dot=sum(b.intersection(v).area for v in markerpts if b.intersects(v));score=hit_space*15+hit_label*100+hit_dot*80+math.hypot(dx,dy)*.2
   candidates.append((score,xx,yy,b,hit_space,hit_label,hit_dot))
 score,xx,yy,b,hs,hl,hd=min(candidates,key=lambda v:v[0]);placed.append(b)
 if hl or hd:unresolved_placement.append((oid,round(hl,1),round(hd,1)))
 nx=min(max(x,xx),xx+24);ny=min(max(y,yy-8),yy)
 if math.hypot(nx-x,ny-y)>10:g.insert(1,at.element('line',{'x1':x,'y1':y,'x2':nx,'y2':ny,'stroke':'#b91c1c','stroke-width':'.55'}))
 t=at.txt(xx,yy,oid,8.5,'#b91c1c',True);t.set('stroke','white');t.set('stroke-width','.8');t.set('paint-order','stroke');g.append(t)
# Explicit status separates complete names from unfinished connectivity review.
for e in root:
 if e.tag==tag('text') and e.text and ('具名空间' in e.text or '个空间名称未确认' in e.text):e.text='276 个稳定空间编号；S023、S273 功能/空间属性未确认；连通复核草稿：16 组疑点待确认';e.set('fill','#b45309')
ET.ElementTree(root).write(p/'标注.svg',encoding='unicode');print('P label collisions',unresolved_placement)
# Numbered review groups: top to bottom by adjacent region; existing S IDs are never reordered.
questions=[
 ('01','S037、S048',(375,335,995,720),'left',500,'急诊北端楼梯、女厕','S037 楼梯间与 S040 输液厅3之间是否可通行？S048 女厕由输液厅1还是其他空间进入？','门扇或墙线在扫描图中粘连；旧关系也未给出可靠入口。请分别写明连接的 S 编号。'),
 ('02','S261、S114、S118、S120',(2300,390,2460,615),'right',450,'药房北侧工作通道','S261 是否确有独立通道？S114 办公、S118 办公、S120 女更衣的人员出入是否还经过该通道？','旧 S261 轮廓仅约 6 像素宽的三角形，不能据此认定独立通道；暂不恢复三条旧 access，已辨认的其他门另行保留。'),
 ('03','S135',(1755,710,1880,780),'right',760,'药房楼梯入口','S135 楼梯间由 S134 中西药调剂区还是 S258 门诊大厅进入？','两侧墙线与楼梯线交叠；未把共墙当作通行。'),
 ('04','S102、S105',(1400,925,1655,995),'left',1000,'中央挂号收费后侧','S102 库房的门连接 S099 挂号收费还是 S259 医疗主街？S105 卫生间的直接入口在哪个空间？','服务间门扇与内部隔墙重叠；旧 S105—S258 access 暂不作为已核实连接。'),
 ('05','S172、S173、S020',(2455,1080,2547,1375),'right',1225,'医技东侧小房间','S172 楼梯间、S173 主任、S020 新风机房是否分别从 S268 东侧工作通道进入？','细墙上未能稳定辨认三个独立门洞；不按房间相邻关系补门。'),
 ('06','S170、S267',(1980,1190,2440,1415),'right',1430,'读片办公、控制廊','S170 读片办公东侧是否与 S268 相通？S267 控制廊西端怎样与 S264 病人等候厅连接？','办公东侧细线有断续；控制廊西端与楼梯轮廓及窄缝不吻合。室内已辨清的存片、值班与控制室门已保留。'),
 ('07','S091',(890,1270,995,1350),'left',1310,'急诊南侧楼梯','S091 楼梯间是否由 S257 急诊通道进入？入口在西侧还是南侧？','原先的直接 access 没有可稳定定位的门洞支持，已列入待确认而非负关系。'),
 ('08','S108、S109',(1495,1660,1655,1785),'left',1730,'中央南端卫生间、楼梯','S108 卫生间、S109 楼梯间分别连接 S276 医疗主街还是 S107 学术交流室？','卫生间内部与楼梯踏步线使门位不清；邻近 S106、S107 已辨门洞单独保留。'),
 ('09','S027、S223',(1880,1880,2005,1980),'right',1925,'住院北侧库房、设备房','S027 设备用房从 S224 电梯厅还是其他空间进入？S223 库房是否包括设备房西侧窄通道并从 S274 进入？','保留已确认粗名称“设备用房”；这里只核对出入口及轮廓，旧库房轮廓未包住疑似门前窄段。'),
 ('10','S225、S226',(2095,1960,2470,2132),'right',2050,'服务中心与住院大厅','S225 院区服务中心、S226 服务区与 S274 住院大厅的西侧界面是人员通道、服务窗口还是半墙连续区？','已保留 S225—S226 的两处门；西侧长线的通行/服务语义不能仅凭颜色连续确定。'),
 ('11','S227',(1640,2120,1748,2255),'right',2220,'住院西侧库房','S227 库房是否包括其北侧横向窄段，并通过该处门连接 S274？','原图北侧可见门形，但既有 S227 轮廓止于门左侧；未把门坐标强挂到错误空间。'),
 ('12','S249、S246、S250',(805,2130,990,2290),'left',2240,'报告厅音控及连接通道','S249 音控室从 S246 报告厅进入，还是从外围通道进入？S246 到 S250 是否经过外围环廊？','已标记 S245—S246 两门、空调机房门、休息室门及 S250—S276 门；外围环廊未独立分区，暂不保留无明确直接边界的旧 access。'),
 ('13','S244',(375,2560,455,2710),'left',2590,'西南独立楼梯','S244 楼梯间是否为独立室外入口，还是与 S243 门厅/其他室内空间相连？','图中两者之间为停车场，不能跨室外直接创建室内 access；若确为独立入口，续作沿用 E 体系补记。'),
 ('14','S235',(1190,2560,1335,2660),'left',2800,'行政区卫生间','S235 卫生间是否从 S275 行政通道进入，或从 S276 医疗主街侧进入？','洁具、隔断与门线混杂；旧 S235—S275 access 待确认。')
]
# Additional original-image evidence found in the nuclear medicine southeast corner.
questions[1]=tuple(list(questions[1][:2])+[(2300,390,2547,615)]+list(questions[1][3:]))
questions[2]=tuple(list(questions[2][:2])+[(1755,710,2547,780)]+list(questions[2][3:]))
questions[11]=tuple(list(questions[11][:2])+[(416,1990,990,2290)]+list(questions[11][3:]))
newq=[('09','S023',(2458,1680,2501,1725),'right',1680,'原废物存放：功能待核','S023 原名“废物存放”是否应为“卫生间”？请确认功能；原名暂留，type 为 unknown。','放大原图可辨文字更接近“卫生间”，并有洁具线索；门可由 S271 侧进入，不能据原名称继续确定废物功能。'),('10','S273',(2501,1680,2542,1725),'right',1790,'原通道：空间属性待核','S273 是否属于 S023 卫生间的洁具区域，而非独立通道？是否允许合并范围并保留旧编号映射？','框内黑白构件更像洁具，不支持独立通道及通向 S024 的门。保留 S273 编号、原名称，type 暂为 unknown。')]
questions=questions[:8]+newq+[tuple([f'{int(q[0])+2:02}']+list(q[1:])) for q in questions[8:]]
(out/'核对映射.json').write_text(json.dumps([dict(zip(['number','spaces','box','side','label_y','title','question','evidence'],q)) for q in questions],ensure_ascii=False,indent=2)+'\n')
fontfile='/System/Library/Fonts/Supplemental/Songti.ttc';font=ImageFont.truetype(fontfile,24);small=ImageFont.truetype(fontfile,21);titlefont=ImageFont.truetype(fontfile,38)
orig=Image.open(p/d['image']['file']).convert('RGB');left=550;top=150;W=3900;H=3170;canvas=Image.new('RGB',(W,H),'white');canvas.paste(orig,(left,top));dr=ImageDraw.Draw(canvas)
dr.text((35,20),'02 嘉兴市第一医院｜连通疑点总图（名称均沿用）',font=titlefont,fill='#1e293b');dr.text((35,80),'按 01—16 对照，回复“01=连接的S编号/说明”。红点 P 见正式 SVG；本图彩框仅表示待核对片区。',font=small,fill='#475569')
colors=['#2563eb','#b45309','#7c3aed','#0f766e'];lines=[]
for idx,q in enumerate(questions):
 n,sids,b,side,ly,ttl,qu,ev=q;x0,y0,x1,y1=b;color=colors[idx%4];rect=(left+x0,top+y0,left+x1,top+y1);dr.rectangle(rect,outline=color,width=4);dr.rounded_rectangle((rect[0]+5,rect[1]+5,rect[0]+(38 if x1-x0<80 else 62),rect[1]+(32 if x1-x0<80 else 42)),radius=5,fill='white',outline=color,width=2);dr.text((rect[0]+10,rect[1]+8),n,font=small if x1-x0<80 else font,fill=color)
 bx=20 if side=='left' else 3380;by=top+ly-44;bw=500;bh=100
 # Border-side anchors keep label-to-frame lines one-to-one, with no line crossing.
 anchor=(left+x0,top+(y0+y1)/2) if side=='left' else (left+x1,top+(y0+y1)/2);start=(bx+bw if side=='left' else bx,by+bh/2);elbow=(left-20 if side=='left' else left+2804+20,start[1]);poly=[start,elbow,anchor]
 if n=='04':poly=[start,elbow,(left+270,top+1006),(left+270,top+976),(left+500,top+976),(left+500,top+1050),(left+580,top+1050),(left+580,top+1185),(left+1000,top+1185),(left+1000,top+1005),(left+1408,top+1005),(left+1408,top+995)]
 if n=='07':poly=[start,elbow,(elbow[0],top+1360),(left+940,top+1360),(left+940,top+1350)]
 if n=='08':poly=[start,elbow,(elbow[0],top+1815),(left+1580,top+1815),(left+1580,top+1785)]
 if n=='11':poly=[start,(left+2600,start[1]),(left+2600,top+1830),(left+1990,top+1830),(left+1990,top+1880)]
 if n=='16':poly=[start,elbow,(elbow[0],top+2840),(left+1160,top+2840),(left+1160,top+2675),(left+1260,top+2675),(left+1260,top+2660)]
 dr.line(poly,fill=color,width=2);lines.append((n,LineString(poly)));dr.rounded_rectangle((bx,by,bx+bw,by+bh),radius=10,fill='#f8fafc',outline=color,width=3);dr.text((bx+12,by+10),n+'｜'+ttl,font=font,fill=color)
 ss=sids if len(sids)<29 else sids[:29]+'…';dr.text((bx+12,by+52),ss,font=small,fill='#334155')
 # A numbered original-image crop is supplemental; the total sheet remains the location reference.
 pad=40;bb=(max(0,x0-pad),max(0,y0-pad),min(orig.width,x1+pad),min(orig.height,y1+pad));crop=orig.crop(bb);scale=max(2,min(4,1800/crop.width));crop=crop.resize((round(crop.width*scale),round(crop.height*scale)));cd=ImageDraw.Draw(crop);rr=((x0-bb[0])*scale,(y0-bb[1])*scale,(x1-bb[0])*scale,(y1-bb[1])*scale);cd.rectangle(rr,outline=color,width=4);cd.text((8,5),n+' '+ttl,font=ImageFont.truetype(fontfile,28),fill=color,stroke_width=2,stroke_fill='white');crop.save(out/f'核对{n}_局部.png')
canvas.save(out/'连通疑点_原图核对总图.png');cross=[]
for i,(a,la) in enumerate(lines):
 for b,lb in lines[i+1:]:
  if la.intersects(lb):cross.append((a,b))
print('review leader intersections',cross);assert not cross
# MD keeps the prior case-specific text verbatim and retains all human-confirmed names.
oldmd=(out/'修改前备份'/'标注说明.md').read_text();precision=oldmd[oldmd.index('**范围：**'):]
summary=(out/'更新概览.md').read_text().replace('# 平面标注概览','# 嘉兴市第一医院_一层平面图｜连通性复核草稿',1).replace('未完成：2 个空间名称尚未确认。','未完成：S023、S273 保留原名称，功能/空间属性待确认；另有连通疑点，尚不能宣布本图标注完成。',1)
relprefix='../临时核对/'+p.name+'/'+out.name
count=collections.Counter(r['type'] for r in d['relations']);located=sum(bool(r.get('openings')) for r in d['relations'] if r['type']=='access');op=sum(len(r.get('openings',[])) for r in d['relations']);oldpairs={tuple(sorted((r['source'],r['target']))) for r in old['relations'] if r['type']=='access'};newpairs={tuple(sorted((r['source'],r['target']))) for r in d['relations'] if r['type']=='access'}
extras=f'''\n\n{precision}\n**本轮补充（2026-11-01）：**保留全部 276 个空间编号与具体名称、8 个入口、8 条服务关系及 11 条共墙关系。新增 {op} 个门洞红点，{located} 条 access 有定位；其余 {count['access']-located} 条为无定位的区域连续、交通核或半墙概念连通。没有以服务窗口、共墙或空间质心生成红点。本轮未辨得可独立定位的无门开口，区域连续不强行编造点位。原图保持原始字节不变。\n\n**旧关系处理：**原 174 条 access 中保留同一空间对 {len(oldpairs&newpairs)} 条；{len(oldpairs-newpairs)} 条旧边已从当前已核实图中撤下，其中有的已改连至原图实际开门一侧，有的仍待下表确认。撤下不表示不可达；旧关系、原成果及逐点工作记录保存在外部核对目录。新增空间对 {len(newpairs-oldpairs)} 条。既有关系编号尽量沿用；不再成立的编号留空，不重排其他关系。\n\n**类别修正：**S094 污洗房、S133 污洗归入 waste_handling；S023 原“废物存放”和 S273 原“核医学工作通道（分段5）”与原图存在功能/轮廓矛盾，保留原名并将 type 设为 unknown；S086 手术室归入 operating_room；S107 学术交流室、S203 示教、S246 报告厅归入 education。具体名称均未改写。\n\n**轮廓校正：**S050 中误含的灰色门前公共区域划回 S255，保留 S050 卫生间编号；S265 补入 MR 旁和南侧原先漏掉的连续通道。相应室内 area_ratio 重新归一化。S261、S223、S227 等存疑边界未擅自合并或删除。开口位置仍为原图像素近似中心，不代表施工精度。\n\n**文件：**[原图]({d['image']['file']}) · [具名标注 SVG](标注.svg) · [annotation.json](annotation.json)\n\n**核对方式：**以下为固定核对号 01—16。S023、S273 保留既有名称但功能/空间属性待核，其余项不需要重复填写房名。可在“我的确认／备注”填写连接的空间编号及必要说明，也可在聊天中按 `01=…，02=…` 分批回复；最右侧重复编号不是答案栏。待确认关系不作为负样本。\n\n![连通疑点原图总图]({relprefix}/连通疑点_原图核对总图.png)\n\n| 核对号 | S编号 | 待确认内容 | 图面依据与未确定处 | 我的确认／备注 | 核对号（重复） |\n| --- | --- | --- | --- | --- | --- |\n'''
for q in questions:
 n,sids,b,side,ly,ttl,qu,ev=q;extras+=f'| {n} | {sids} | {qu} [局部]({relprefix}/核对{n}_局部.png) | {ev} | 待确认 | {n} |\n'
extras+='\n**09—10 可直接修改的名称/功能预估表：**原名称仍在 JSON 保留，候选仅用于核对；修改预估名称后，在确认栏标“已确认”或直接填写实际名称和范围处理意见。\n\n| 核对号 | S编号 | 预估名称（可改） | 备选名称 | 依据与把握 | 我的确认／备注 | 核对号（重复） |\n| --- | --- | --- | --- | --- | --- | --- |\n| 09 | S023 | 卫生间 | 原名称：废物存放 | 原图文字更接近卫生间，并见洁具；此候选依据为文字与构件；原名保留仅为尊重既有确认，不作为反向证据。把握：中。 | 待确认 | 09 |\n| 10 | S273 | 名称/独立空间属性未确认 | S023 卫生间内洁具区域（可能不应独立分区） | 仅见洁具形构件，未见独立通道或门；候选依据为构件和邻接范围，是否合并须确认。把握：中。 | 待确认 | 10 |\n'
extras+='\n**校验状态：**待运行本轮正式 `validate --check-dir`；格式检查不能替代上述连通语义确认。\n'
(p/'标注说明.md').write_text(summary+extras)
# Readable change ledger outside the formal four-file directory.
rows=['# 本轮关系变化记录','',f'保留旧 access {len(oldpairs&newpairs)} 条；撤下旧 access {len(oldpairs-newpairs)} 条；新增空间对 {len(newpairs-oldpairs)} 条。','', '| 原关系 | 空间对 | 本轮状态 |','| --- | --- | --- |']
for r in old['relations']:
 if r['type']=='access' and tuple(sorted((r['source'],r['target']))) not in newpairs:rows.append(f"| {r['id']} | {r['source']}—{r['target']} | 旧边撤下；依据实际门位改连或列入标注说明的连通核对项；不作为负关系 |")
(out/'关系变化记录.md').write_text('\n'.join(rows)+'\n')
print('DELIVERY',p.resolve(),'points',op,'located access',located,'concept',count['access']-located,'counts',count)
