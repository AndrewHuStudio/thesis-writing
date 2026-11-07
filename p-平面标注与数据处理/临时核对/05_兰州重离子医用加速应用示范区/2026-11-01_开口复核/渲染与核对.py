from pathlib import Path
import json,xml.etree.ElementTree as E,base64,math
import pymupdf
from shapely.geometry import box,Point,LineString
O=Path(__file__).resolve().parent;P=O.parents[2]/'标注试样/05_兰州重离子医用加速应用示范区'
D=json.loads((P/'annotation.json').read_text());NS='http://www.w3.org/2000/svg';XL='http://www.w3.org/1999/xlink';E.register_namespace('',NS);E.register_namespace('xlink',XL)
def el(tag,attrs={},text=None):
 e=E.Element('{'+NS+'}'+tag,{k:str(v) for k,v in attrs.items()});e.text=text;return e
def txt(x,y,s,size=20,color='#18314c'):
 return el('text',dict(x=x,y=y,fill=color,**{'font-size':size,'font-family':'Arial, PingFang SC, Microsoft YaHei, sans-serif'}),s)
# P编号采用实色文字与单独白底，避免部分SVG渲染器将白色描边覆盖文字。
tree=E.parse(P/'标注.svg');root=tree.getroot();plan=next(g for g in root if g.get('id')=='plan')
labels=[]
for g in plan:
 if g.get('data-space-name') is not None:
  r=next(c for c in g if c.tag.endswith('rect'));x,y,w,h=[float(r.get(k)) for k in ['x','y','width','height']];labels.append(box(x,y,x+w,y+h))
markers=[g for g in plan if g.get('data-opening-id')];circles=[]
for g in markers:
 c=next(c for c in g if c.tag.endswith('circle'));circles.append(Point(float(c.get('cx')),float(c.get('cy'))).buffer(6))
placed=[]
for g in markers:
 c=next(c for c in g if c.tag.endswith('circle'));x,y=float(c.get('cx')),float(c.get('cy'));oid=g.get('data-opening-id');t=next(c for c in g if c.tag.endswith('text'))
 fs=10;w=30;h=15;candidates=[(x+8,y-20),(x+8,y+6),(x-w-8,y-20),(x-w-8,y+6),(x-w/2,y-26),(x-w/2,y+10)]
 def cost(p):
  b=box(p[0],p[1],p[0]+w,p[1]+h)
  return sum(b.intersection(v).area for v in labels)*2+sum(b.intersection(v).area for v in placed)*20+sum(b.intersection(v).area for v in circles)*50
 bx,by=min(candidates,key=cost);placed.append(box(bx,by,bx+w,by+h));g.remove(t)
 g.append(el('rect',dict(x=bx,y=by,width=w,height=h,rx=2,fill='white',**{'fill-opacity':'.94'})))
 g.append(txt(bx+2,by+11,oid,fs,'#b91c1c'))
root[1].text='兰州重离子医用加速应用示范区 · 一层概念标注'
root[2].text='129 个具名区域；117 个门洞红点；连通性复核仍有 14 组疑点（含16条旧关系）'
root[2].set('fill','#b45309')
tree.write(P/'标注.svg',encoding='unicode')
# 全图及密集局部均从最终SVG实际渲染。
doc=pymupdf.open(P/'标注.svg');page=doc[0];page.get_pixmap(matrix=pymupdf.Matrix(1,1),alpha=False).save(O/'标注全图.png')
regions=[('西北',(320,870,1340,1520)),('西中',(470,1500,1270,2410)),('东北',(1840,910,2770,1520)),('东中',(1840,1500,2640,2410)),('西南',(460,2390,1260,3350)),('东南',(1840,2390,2670,3350)),('入口',(1100,3120,2000,3360))]
for name,b in regions:page.get_pixmap(matrix=pymupdf.Matrix(2,2),clip=pymupdf.Rect(b[0],b[1]+125,b[2],b[3]+125),alpha=False).save(O/(name+'_标注.png'))
# 核对号与P编号独立：本轮映射固定，不因分批回答而重排。
qs=[
('西北','left',(785,950,955,1055),'S001↔S006',['R010'],'两座楼梯间是否直接相通？','图上门均朝向北侧间隙，未见两核之间的直接门。'),
('西北','left',(719,1195,761,1235),'S005↔S007',['R003'],'管井小符号能否供人员进入？','南侧小三角缺乏明确门扇弧，可能为检修符号。'),
('西北','left',(1114,1390,1245,1435),'S013↔S009',['R014'],'护士站人员入口是否朝下方通道？','曲线边界连续，向候诊区的服务联系已单列。'),
('东北','right',(1948,1090,1995,1225),'S041↔S042',['R053'],'入口区与准备区如何通行？','竖向边界设备和符号密集，未辨清门。'),
('东北','right',(1975,1270,2180,1343),'S042↔S052',['R055'],'准备区到南侧通道如何通行？','多个小间与缓冲门的空间归属不清。'),
('东北','right',(2438,1270,2542,1310),'S054↔S051',['R046'],'餐包北侧是门还是盆具/窗口？','类似盆具的连续弧线，西侧通库房的门已定位。'),
('东北','right',(2207,1440,2258,1500),'S057↔S053',['R060'],'二更东侧是否另通库房？','可辨西向门；东侧边界未见可靠门位。'),
('西中','left',(1036,1848,1245,1885),'S024、S025↔S020',['R030','R031'],'更衣、护士站各自有北向人员门吗？','北墙未见清晰开口；更衣南向门已定位，窗口不作通行。'),
('西中','left',(596,1972,637,2018),'S026↔S015',['R022'],'管井东侧是人员门还是检修口？','小三角符号；目前只保留旧边，无红点。'),
('西中','left',(1015,1972,1055,2118),'S028↔S024/S031',[],'MR的人员入口接更衣还是控制室？','右侧两处为狭长符号，门和观察窗难以区分；暂无新边。'),
('西中','left',(826,2324,934,2362),'S037、S038↔S032',['R037','R038'],'强电、弱电南侧可步入吗？','小三角符号，门或检修口待确认；已修正所接通道。'),
('东中','right',(2474,1977,2515,2017),'S070↔S059',['R070'],'管井西侧是人员门还是检修口？','同样为小三角符号，不从相邻关系新增红点。'),
('东中','right',(2175,2324,2283,2362),'S076、S077↔S072',['R077','R078'],'强电、弱电南侧可步入吗？','南侧小三角符号，是否人员门未确定。'),
('东南','right',(2474,2390,2545,2448),'S121↔S072',['R130'],'电梯前室北端通道是否可供人员通行？','北端含小管井；东向独立出口、南向门斗门已定位。'),
]
questions=[]
for i,(group,side,b,spaces,rels,question,evidence) in enumerate(qs,1):questions.append(dict(number=f'{i:02}',group=group,side=side,box=b,spaces=spaces,relations=rels,question=question,evidence=evidence))
(O/'本轮核对映射.json').write_text(json.dumps(questions,ensure_ascii=False,indent=2)+'\n')
# 完整原图居中；边栏保持同组编号连续。引线只锚定本项彩框。
W,H=4499,4298;ox,oy=710,140
r=el('svg',dict(width=W,height=H,viewBox=f'0 0 {W} {H}'));r.append(el('rect',dict(width=W,height=H,fill='white')))
r.append(txt(50,48,'05 兰州重离子｜连通性集中核对（14组）',32));r.append(txt(50,90,'按片区 01—14 阅读；原图完整保留。可回复“01=相通，02=检修口……”；同组可分别填写。',21,'#52677b'))
r.append(el('image',dict(x=ox,y=oy,width=3079,height=4088,**{'{'+XL+'}href':'data:image/jpeg;base64,'+base64.b64encode((P/D['image']['file']).read_bytes()).decode()})))
colors={'西北':'#2563eb','东北':'#b45309','西中':'#7c3aed','东中':'#0f766e','东南':'#be185d'}
# 靠近框所在高度排列；同侧每组编号顺序固定，外部锚点选框的最近侧。
ys={'01':1090,'02':1320,'03':1530,'04':1250,'05':1420,'06':1590,'07':1770,'08':2050,'09':2240,'10':2420,'11':2620,'12':2260,'13':2540,'14':2760}
leaders=[]
for q in questions:
 n=q['number'];x1,y1,x2,y2=q['box'];color=colors[q['group']];side=q['side'];yy=ys[n]
 r.append(el('rect',dict(x=ox+x1,y=oy+y1,width=x2-x1,height=y2-y1,fill=color,**{'fill-opacity':'.08','stroke':color,'stroke-width':4})))
 # 框角小号与侧栏同号。
 r.append(el('rect',dict(x=ox+x1,y=oy+y1-28,width=47,height=28,fill=color)))
 r.append(txt(ox+x1+7,oy+y1-7,n,21,'white'))
 lx=35 if side=='left' else 3820;lw=645;lh=114
 r.append(el('rect',dict(x=lx,y=yy,width=lw,height=lh,rx=7,fill='#f8fafc',stroke=color,**{'stroke-width':2})))
 r.append(txt(lx+14,yy+29,n+'｜'+q['spaces'],22,color))
 r.append(txt(lx+14,yy+59,q['question'],21,color))
 # 说明按固定字符宽度换行（边栏而非房间标签）。
 evidence=q['evidence'];chunks=[evidence[i:i+27] for i in range(0,len(evidence),27)]
 for k,line in enumerate(chunks):r.append(txt(lx+14,yy+83+k*23,line,18,'#52677b'))
 anchor=(ox+(x1 if side=='left' else x2),oy+(y1+y2)/2)
 edge=(lx+lw if side=='left' else lx,yy+lh/2)
 # 两端折线：框附近的扇出点与边栏高度配对，保持各组次序。
 gx=ox-18 if side=='left' else ox+3079+18
 pts=[edge,(gx,edge[1]),anchor]
 if n=='05':
  anchor=(ox+2080,oy+1270)
  pts=[edge,(gx,edge[1]),(ox+2600,oy+1260),anchor]
 leaders.append((n,LineString(pts)))
 r.append(el('polyline',dict(points=' '.join(f'{a},{b}' for a,b in pts),fill='none',stroke=color,**{'stroke-width':2.2})))
 r.append(el('circle',dict(cx=anchor[0],cy=anchor[1],r=5,fill=color)))
# 交叉先检出，再调整边栏或引线；不变更编号解决。
cross=[]
for i,(a,l) in enumerate(leaders):
 for b,k in leaders[i+1:]:
  if l.crosses(k) or l.overlaps(k):cross.append([a,b])
print('review leader crossings',cross)
(O/'连通性核对总图.svg').write_text(E.tostring(r,encoding='unicode'))
pymupdf.open(O/'连通性核对总图.svg')[0].get_pixmap(matrix=pymupdf.Matrix(1,1),alpha=False).save(O/'连通性核对总图.png')
for group in dict.fromkeys(q['group'] for q in questions):
 items=[q for q in questions if q['group']==group];b=[min(q['box'][0] for q in items)-100,min(q['box'][1] for q in items)-90,max(q['box'][2] for q in items)+100,max(q['box'][3] for q in items)+90]
 # 同号局部图以总图原位裁取，标签号/框不另行分配。
 doc=pymupdf.open(O/'连通性核对总图.svg');clip=pymupdf.Rect(ox+b[0],oy+b[1],ox+b[2],oy+b[3]);doc[0].get_pixmap(matrix=pymupdf.Matrix(2,2),clip=clip,alpha=False).save(O/f'{group}_核对局部.png')
(O/'核对图检查.json').write_text(json.dumps({'count':len(questions),'continuous_numbers':[q['number'] for q in questions],'leader_crossings':cross},ensure_ascii=False,indent=2)+'\n')
