from pathlib import Path
from collections import Counter
import copy,json,re,xml.etree.ElementTree as ET,base64,hashlib
from shapely.geometry import box,LineString,Polygon,Point

H=Path(__file__).resolve().parent
P=H.parents[2]/'标注试样/04_兰州市安宁新城医院新建项目'
d=json.loads((P/'annotation.json').read_text());by={s['id']:s for s in d['spaces']}
NS='http://www.w3.org/2000/svg';XL='http://www.w3.org/1999/xlink';ET.register_namespace('',NS);ET.register_namespace('xlink',XL)
def el(tag,attrs=None,text=None):
 e=ET.Element('{'+NS+'}'+tag,{k:str(v) for k,v in (attrs or {}).items()});e.text=text;return e
def txt(x,y,t,size=20,color='#18314c'):
 return el('text',{'x':x,'y':y,'font-size':size,'fill':color,'font-family':'Arial, PingFang SC, Microsoft YaHei, sans-serif'},t)

# Make every marker label legible in both SVG browsers and PDF renderers.
root=ET.parse(P/'标注.svg').getroot();plan=root.find("./{*}g[@id='plan']")
root.find('./{*}text').text='兰州市安宁新城医院｜一层平面标注'
root.findall('./{*}text')[1].text='246 个具名空间；本轮开口复核有 14 组连通疑点待确认'
root.findall('./{*}text')[1].set('fill','#b45309')

# Thin legacy fragments remain stable; move only their labels to nearby white margins.
outs={
 'S119':(190,1155),'S140':(190,3050),
 'S216':(2420,635),'S221':(2420,1498),'S230':(2420,3420),
 'S233':(190,910),'S236':(190,1260),'S237':(190,2775),'S238':(190,2840),
 'S044':(1250,1290),'S045':(1250,1320),'S046':(1250,1350),'S047':(1250,1380),
 'S065':(1250,2690),'S245':(1250,2720),'S066':(1250,2750),'S246':(1250,2780),
}
types=json.loads(Path('/Users/hushili/.codex/skills/outpatient-plan-annotation/references/space-types.json').read_text())
for sid,(x,y) in outs.items():
 g=plan.find(f'./{{*}}g[@id="{sid}"]');s=by[sid]
 for child in list(g):
  if child.tag in ['{'+NS+'}rect','{'+NS+'}text']:g.remove(child)
 poly=Polygon(s['polygon_px']);q=poly.representative_point()
 text=f'{sid} {s["name"]}〔{types[s["type"]]}〕'
 width=sum(7.6 if ord(c)<128 else 13 for c in text)+12
 rx=35 if x<400 else x
 g.append(el('line',dict(x1=q.x,y1=q.y,x2=rx+(width if x<1700 else 0),y2=y-5,stroke='#52677b',**{'stroke-width':'.8'})))
 g.append(el('rect',dict(x=rx-4,y=y-18,width=width+8,height=24,fill='white',**{'fill-opacity':'.95','stroke':'#52677b','stroke-width':'.8'})))
 g.append(txt(rx+2,y,text,13))

marker_points=[Point(o['position_px']) for r in d['relations'] for o in r.get('openings',[])]
# Compact two/three-line labels for short rooms; the shared category remains visible.
for sid in ['S116','S123','S170','S171','S173','S208','S242']:
 g=plan.find(f'./{{*}}g[@id="{sid}"]');s=by[sid];poly=Polygon(s['polygon_px']);x1,y1,x2,y2=poly.bounds
 for child in list(g):
  if child.tag in ['{'+NS+'}rect','{'+NS+'}text']:g.remove(child)
 fs=6.5;lines=[sid+' '+s['name']];cat='〔'+types[s['type']]+'〕';count=max(3,int((x2-x1-5)/fs))
 lines.extend(cat[i:i+count] for i in range(0,len(cat),count))
 ww=min(x2-x1-4,max(sum(fs*(.58 if ord(c)<128 else 1) for c in row) for row in lines)+4);hh=len(lines)*8+3
 rx=(x1+x2-ww)/2;ry=(y1+y2-hh)/2
 g.append(el('rect',dict(x=rx,y=ry,width=ww,height=hh,fill='white',**{'fill-opacity':'.95','stroke':'#52677b','stroke-width':'.6'})))
 for i,row in enumerate(lines):g.append(txt(rx+2,ry+8+i*8,row,fs))

# Move remaining name boxes that would cover a red marker, inside the same region.
for g in plan:
 sid=g.get('id','')
 if sid not in by or sid in outs:continue
 rect=g.find('./{*}rect')
 if rect is None:continue
 x,y,w,h=[float(rect.get(k)) for k in ['x','y','width','height']]
 current=box(x,y,x+w,y+h)
 if not any(current.buffer(3).contains(q) for q in marker_points):continue
 poly=Polygon(by[sid]['polygon_px']);chosen=None
 for dy in [10,20,30,40,50,-10,-20,-30,-40]:
  for dx in [0,10,-10,20,-20,30,-30]:
   moved=box(x+dx,y+dy,x+dx+w,y+dy+h)
   if poly.covers(moved) and not any(moved.buffer(3).contains(q) for q in marker_points):chosen=(dx,dy);break
  if chosen:break
 if chosen:
  dx,dy=chosen
  for c in g:
   if c.tag in ['{'+NS+'}rect','{'+NS+'}text']:
    c.set('x',str(float(c.get('x'))+dx));c.set('y',str(float(c.get('y'))+dy))

name_boxes=[]
for g in plan:
 if g.get('id','').startswith('S'):
  for e in g.findall('./{*}rect'):
   x,y,w,h=[float(e.get(k)) for k in ['x','y','width','height']];name_boxes.append(box(x,y,x+w,y+h))
marker_points=[Point(o['position_px']) for r in d['relations'] for o in r.get('openings',[])]
label_boxes=[];label_conflicts=[]
for g in plan:
 if g.get('data-opening-id') is None:continue
 circle=g.find('./{*}circle');x,y=[float(circle.get(k)) for k in ['cx','cy']]
 oldtext=g.find('./{*}text');g.remove(oldtext);oid=g.get('data-opening-id')
 candidates=[]
 for i,(dx,dy) in enumerate([(7,-7),(-28,-7),(7,14),(-28,14),(7,-17),(-28,-17),(12,3),(-34,3),(10,23),(-30,23),(7,33),(-28,33),(7,-29),(-28,-29),(28,-17),(-50,-17)]):
  r=box(x+dx-1,y+dy-8,x+dx+23,y+dy+2)
  n=sum(r.intersection(b).area for b in name_boxes)
  l=sum(r.intersection(b).area for b in label_boxes)
  z=sum(r.buffer(2).contains(q) for q in marker_points)
  candidates.append((n*5+l*30+z*100+i*.1,dx,dy,r,n,l,z))
 score,dx,dy,r,n,l,z=min(candidates,key=lambda q:q[0]);label_boxes.append(r)
 if l or z:label_conflicts.append((oid,n,l,z))
 attrs={'x':x+dx,'y':y+dy,'font-size':8.5,'font-family':'Arial, sans-serif','font-weight':'700'}
 g.append(el('text',{**attrs,'fill':'white','stroke':'white','stroke-width':2,'stroke-linejoin':'round'},oid))
 g.append(el('text',{**attrs,'fill':'#b91c1c'},oid))
ET.ElementTree(root).write(P/'标注.svg',encoding='unicode')

# Review rows: stable room identifiers and confirmed names are not changed.
# Only these unresolved connections need a user decision.
questions=[
 ('01',['S015'],'儿科收费：工作人员从哪里进入？','服务柜台可辨，未见独立人员门；当前仅记 S015—S214 服务联系。','右',650,(2356,650)),
 ('02',['S119'],'北住院大厅强电/弱电：入口朝大厅还是其他空间？','设备带很窄，门扇与墙线不能可靠区分；暂不新增 access。','左',1155,(434,1155)),
 ('03',['S040'],'中药房西北交通核：与主街、住院通道或药房哪处相通？','主街侧未见直接开口；旧 R202 暂不作为已证实连接。保留整体交通核。','左',1280,(1738,1285)),
 ('04',['S041'],'中药房东北交通核：入口连向哪里？','外围房间与梯段交叠，不能辨定整体节点的外部入口；不推断内部互通。','右',1300,(2340,1325)),
 ('05',['S045','S046','S047'],'中药房 F、PY、SF：有人员门，还是仅检修柜/管井？','S044（KT）可辨开口已记录；其余三个小间未找到清晰人员门，不扩展缩写含义。','左',1385,(1814,1337)),
 ('06',['S199','S200'],'放射科两处“石膏”：外部入口与哪个空间相通？','两单元之间的内门已记录；外侧线条不能区分人员门与其他图线。','左',2390,(824,2394)),
 ('07',['S203'],'放射科西侧“调钡”：门连向更衣准备、数字胃肠还是通道？','未见足够清晰的独立人员门；旧直接连通道关系暂不采用。','左',2550,(1003,2480)),
 ('08',['S245','S066','S246'],'输液区 F、PY、SF：有人员门，还是仅检修柜/管井？','S065（KT）上侧开口可辨；另外三个小单元暂不定位人员开口。','左',2740,(1814,2729)),
 ('09',['S134'],'南住院大厅中间“更衣”：是否从结算区进入？','本小间未见清楚门扇；S133 与 S135 的可辨开口已分别记录。','左',2880,(736,2870)),
 ('10',['S140'],'南住院大厅强弱电：入口朝大厅还是其他空间？','与北侧类似，设备带太窄，门扇不能可靠分辨；暂不新增 access。','左',3040,(434,3040)),
 ('11',['S080'],'急救区“强电”：有人员门吗，连向哪里？','S081（EPS）东侧小开口可辨；S080 外围线条不足以确认人员门。','左',3190,(1738,3053)),
 ('12',['S092'],'急诊“拍片”：患者门在上、下或侧面？','上下长边未见可靠门弧；旧 R060 暂不作为已证实连接，邻近 CT 上侧门已记录。','右',3300,(2080,3352)),
 ('13',['S102'],'急诊东南交通核：与诊疗通道、药房还是室外相通？','西侧边界未辨出直接门；旧 R068 暂不作为已证实连接。保留整体交通核。','右',3555,(2333,3560)),
]
questions.insert(1,('02',['S219','S220'],'两处药房通道窄条：是可通行区域，还是柜台边界分片？','既有名称及轮廓保留；窄条只有约 14 像素宽，不能仅凭相邻就确认与药房人员相通。','右',1175,(1909,1164)))
questions=[(f'{i:02d}',*row[1:]) for i,row in enumerate(questions,1)]

W,HGT=4464,4288;OX,OY=700,130
svg=el('svg',dict(width=W,height=HGT,viewBox=f'0 0 {W} {HGT}'))
svg.append(el('rect',dict(width=W,height=HGT,fill='white')))
svg.append(txt(30,45,'04 兰州市安宁新城医院｜连通性核对总图（14 组）',32))
svg.append(txt(30,85,'按 01—14 回复；名称与 S 编号均沿用已有确认。红点门位详见标注.svg；本图仅框出待核范围。',23))
svg.append(el('image',{'x':OX,'y':OY,'width':3064,'height':4088,'{'+XL+'}href':'data:image/jpeg;base64,'+base64.b64encode((P/d['image']['file']).read_bytes()).decode()}))
colors=['#be185d','#0369a1','#9a3412','#6d28d9','#047857','#a21caf','#b45309']
routes=[]
for i,(num,sids,question,evidence,side,ly,anchor) in enumerate(questions):
 color=colors[i%len(colors)];lx=28 if side=='左' else 3790;ey=OY+ly
 for sid in sids:
  s=by[sid];svg.append(el('polygon',{'points':' '.join(f'{OX+x},{OY+y}' for x,y in s['polygon_px']),'fill':color,'fill-opacity':'.10','stroke':color,'stroke-width':3}))
 ax,ay=anchor;ax+=OX;ay+=OY
 if side=='左':
  route=[(lx+615,ey),(OX+370,ey),(ax,ay)]
 else:
  route=[(lx-15,ey),(OX+2420,ey),(ax,ay)]
 # For the two dense radiology items route in the corridor/wall band, not through the row.
 if 'S219' in sids:route=[(lx-15,ey),(OX+2420,ey),(OX+2420,OY+1190),(OX+1909,OY+1190),(ax,ay)]
 if 'S199' in sids:route=[(lx+615,ey),(OX+560,ey),(OX+688,OY+2392),(OX+710,OY+2330),(OX+850,OY+2330),(OX+850,OY+2368)]
 if 'S203' in sids:route=[(lx+615,ey),(OX+704,ey),(OX+704,OY+2508),(OX+1003,OY+2508),(ax,ay)]
 if 'S134' in sids:route=[(lx+615,ey),(OX+400,ey),(OX+400,OY+2975),(OX+715,OY+2975),(OX+715,OY+2870),(ax,ay)]
 if 'S080' in sids:route=[(lx+615,ey),(OX+1700,ey),(OX+1700,OY+3053),(ax,ay)]
 if 'S092' in sids:route=[(lx-15,ey),(OX+2420,ey),(OX+2420,OY+3370),(OX+2080,OY+3370),(ax,ay)]
 routes.append((num,LineString(route)))
 svg.append(el('polyline',{'points':' '.join(f'{x},{y}' for x,y in route),'fill':'none','stroke':color,'stroke-width':2.2}))
 # One numbered badge for the whole question, even when it contains several small cells.
 bx,byy=route[-1];svg.append(el('circle',dict(cx=bx,cy=byy,r=20,fill='white',stroke=color,**{'stroke-width':2.5})))
 svg.append(txt(bx-14,byy+8,num,24,color))
 svg.append(el('rect',dict(x=lx,y=ey-43,width=615,height=93,rx=7,fill='white',stroke=color,**{'stroke-width':2})))
 svg.append(txt(lx+13,ey-13,num+'｜'+'、'.join(sids),24,color))
 # Short callout; full wording and evidence are in the editable MD table.
 short=question.split('：')[0]
 svg.append(txt(lx+13,ey+22,short,24,color))

cross=[]
for i,(a,la) in enumerate(routes):
 for b,lb in routes[i+1:]:
  if la.intersects(lb):cross.append((a,b))
assert not cross,cross
ET.ElementTree(svg).write(H/'连通核对总图.svg',encoding='unicode')
(H/'核对号映射.json').write_text(json.dumps([dict(number=n,spaces=s,question=q,evidence=e) for n,s,q,e,*_ in questions],ensure_ascii=False,indent=2)+'\n')

# Preserve the existing authored scope, precision, abbreviations, and all prior content.
original=(H/'修改前备份/标注说明.md').read_text()
auto=(H/'自动概览.md').read_text()
for prefix in ['**标注规模：**','**类型与数量：**','**连接关系：**']:
 replacement=next(l for l in auto.splitlines() if l.startswith(prefix))
 original=re.sub(re.escape(prefix)+r'[^\n]*',lambda _:replacement,original)
original=original.replace('空间名称已齐；结构与关系仍以原图及人工核对为依据。','空间名称已齐；本轮可确定开口与连接已更新，仍有 14 组连通性疑点待确认，整图连通复核尚未完成。')
original=original.replace('绿化 1 个','露天／挑空中庭 1 个')
original=original.replace('绿化不参与。','已确认的下沉庭院不参与。')
opening_line=next(l for l in auto.splitlines() if l.startswith('**门洞与开口：**'))
review_rel='../../临时核对/04_兰州市安宁新城医院新建项目/2026-11-01_开口复核'
extra=['','## 本轮补充（2026-11-01）','',opening_line,'',
 '**保留与修正：**246 个 S 编号及全部具体名称保留。S034“会议室”改归共享类别 `conference`；S187“下沉庭院”沿用既有不计室内面积说明，归为 `courtyard/open_space`。S181、S183 控制室轮廓补至原图南墙，S243、S244 对应收回走廊凹口；DSA 北侧 S169/S170/S171/S172/S242/S244 的共享边界对齐原图小间隔墙。共九处轮廓调整，不改变总覆盖范围。全部人工原名、缩写和范围说明沿用。','',
 '**连接复核：**患者门与控制室门分别对应实际两端空间；同一空间对的多个门合并保存。剔除 29 条旧的直接连接表达，按可读门位补入或改连正确空间；移除项保存在目录外备份与复核记录中。服务窗口、共墙分别记录，不代替人员通行。交通核沿用整体节点，不推断内部各房间互通。','',
 '**未定位概念连接：**大厅连续分片、开放工作区及既有整体交通节点保留概念可达，不用共墙中点补门位。S219/S220 窄通道分片依其既有名称和范围沿用，其与药房是否人员相通单列待核；S216/S221/S230/S233/S236/S237/S238 等细碎分片保留原编号和轮廓，不额外推断独立入口。未列关系仍为未知，不能作不可通行负例。','',
 '**校验状态：**正式 `validate --check-dir` 通过（结构、名称、面积与红点同步）；另行核对每个红点与两端多边形，近似边界偏差不超过 22 像素。结构通过不等于下列疑点已确认。','',
 f'[原图]({d["image"]["file"]}) · [具名标注 SVG](标注.svg) · [核对总图 PNG]({review_rel}/连通核对总图.png) · [核对总图 SVG]({review_rel}/连通核对总图.svg)','',
 '## 连通性集中核对','',
 '以下询问连接与开口，不重新确认已确定的名称。核对号按相邻片区从上到下排列，S 编号保持原样。可在“我的确认／备注”填写，也可在聊天按 `01=仅窗口，工作人员从……进入；02=……` 分批回复；未回答项保持待确认。','',
 f'![完整原图连通核对总图]({review_rel}/连通核对总图.png)','',
 '| 核对号 | S编号 | 要确认的问题 | 图面依据与当前处理 | 我的确认／备注 | 核对号（重复） |',
 '| --- | --- | --- | --- | --- | --- |']
for n,s,q,e,*_ in questions:extra.append(f'| {n} | {"、".join(s)} | {q} | {e} 把握：低；不编造门位。 | 待确认 | {n} |')
extra+=['',f'放大查看：[01—06 北部局部]({review_rel}/核对局部_01-06.png) · [07—09 中部局部]({review_rel}/核对局部_07-09.png) · [10—14 南部局部]({review_rel}/核对局部_10-14.png)','',
 '**文件边界：**本项目仅保留具名原图、标注.svg、annotation.json、标注说明.md。备份、全图与密集局部、开口复核记录及脚本均放在上述目录外核对目录。原图逐字节未改动。']
(P/'标注说明.md').write_text(original.rstrip()+'\n'+'\n'.join(extra)+'\n')
print('review questions',len(questions),'leader crossings',cross,'marker label conflicts',label_conflicts)

# Full room audit index: every existing space appears once, without rewriting core data.
audit=['S编号\t原名\t类别\t已定位开口\t未定位概念连接\t待核号']
for s in d['spaces']:
 sid=s['id'];rs=[r for r in d['relations'] if sid in [r['source'],r['target']]]
 ops=[o['id'] for r in rs for o in r.get('openings',[])]
 cons=[r['id'] for r in rs if r['type']=='access' and not r.get('openings')]
 qs=[n for n,ids,*_ in questions if sid in ids]
 audit.append('\t'.join([sid,s['name'],s['type'],','.join(ops),','.join(cons),','.join(qs)]))
(H/'逐空间复核索引.tsv').write_text('\n'.join(audit)+'\n')
print('original sha256',hashlib.sha256((P/d['image']['file']).read_bytes()).hexdigest())
