from pathlib import Path
import json,copy
from shapely.geometry import Polygon,Point
out=Path(__file__).parent
project=out.parent.parent/'标注试样'/'03_晋中市第一人民医院迁建项目'
stage=out/'待核验成果';stage.mkdir(exist_ok=True)
d=json.loads((out/'修改前备份'/'annotation.json').read_text());original=copy.deepcopy(d);ss={s['id']:s for s in d['spaces']}
def poly(sid,pts):ss[sid]['polygon_px']=[[1440-y,x] for x,y in pts]
poly('S001',[(263,507),(277,507),(277,718),(263,718)])
poly('S146',[(812,411),(861,411),(861,436),(812,436)])
poly('S147',[(861,411),(905,411),(905,436),(861,436)])
poly('S164',[(730,518),(756,518),(756,578),(730,578)])
poly('S317',[(976,91),(1101,91),(1101,113),(1000,113),(1000,335),(976,335)])
poly('S207',[(721,781),(742,781),(742,815),(879,815),(879,864),(862,864),(862,826),(742,826),(742,849),(678,849),(678,839),(721,839)])
poly('S212',[(678,849),(710,849),(710,864),(678,864)])
poly('S326',[(1101,648),(1208,648),(1208,595),(1372,595),(1372,691),(1140,691),(1140,739),(1101,739)])
poly('S337',[(1101,811),(1133,811),(1133,789),(1372,789),(1372,755),(1465,755),(1465,789),(1520,789),(1520,704),(1574,704),(1574,839),(1450,864),(1101,864)])
s={'id':'S344','name':'医技通道','type':'corridor','level':'open_space','scope':'medical_technology','polygon_px':[]};d['spaces'].append(s);ss[s['id']]=s;poly('S344',[(650,864),(678,864),(678,884),(650,884)])
for sid in ['S028','S078','S227']:ss[sid]['type']='courtyard';ss[sid]['level']='open_space'
for sid in ['S153','S154','S156','S161','S182','S183','S184','S185','S193','S194','S195','S196','S197','S201','S203','S214','S215','S216','S257']:ss[sid]['type']='imaging'
for sid in ['S079','S082','S268']:ss[sid]['type']='operating_room'
ss['S140']['type']='conference'
# 每项均对照本院原图：移除跨越中间房间、实际开向其他侧或窗口被当门的旧边。
remove={
'R149':'S148 与 S150 仅接角点，医生办公实际入口待确认',
'R309':'S318 与 S319 仅接角点，交通核门实际通 S317 西侧走廊',
'R041':'S031 与 S023 中间由 S001 连续段连接，非直接相接',
'R042':'石膏 S044 门开向 S023，非隔着 S001 直连 S031',
'R109':'S110 与 S113 中间隔 S115，S113 南侧接大厅',
'R119':'S114 与 S110 之间隔 S111，原图无跨区直达依据',
'R147':'S145 与 S148 中间隔 S146/S147，改由 S143 连接',
'R174':'S160 与 S171 中间隔 S170，不能直连',
'R222':'S218 与 S187 中间隔 S224，不能直连',
'R229':'S226 与 S113 中间隔 S223/S116，不能直连',
'R251':'急诊药房 S247 的可见门在北侧 S237',
'R262':'S235 与 S259 之间隔 S260/S262，不能直连',
'R320':'S218 东侧开口实际接 S322，非下方的 S324',
'R341':'S326 与 S337 中间隔 S329 及其他房间，不能直连',
'R027':'医办右侧门连 S001，原 S002 仅在其上方',
'R036':'原 S001 与西侧交通核之间隔房，实际内侧／外侧入口待核',
'R038':'处置治疗经护士站 S025 进入，S024 与其不直接接触',
'R039':'卫生间实际门位在东侧 S110，不直接通 S024',
'R040':'交通核门开向东侧 S110，不是南侧 S024',
'R043':'治疗室门位位于 S001 南端，非 S031',
'R046':'处置治疗经 S047 护士站进入，非跨站直连 S046',
'R047':'交通核东侧开门通 S110，S046 与其之间有其他房间',
'R070':'原 S051 与西侧交通核之间隔房，实际入口待核',
'R080':'卫生间东侧两门通 S107，北侧等候区无该门',
'R138':'S143 与 S117 间隔一排职工房间，不直接相接',
'R145':'机房 S146 的可见门开向专用 MRI S156',
'R146':'库房 S147 的可见门开向东侧 S148',
'R160':'机房 S151 门在 MRI S153 一侧，未见西侧开门',
'R168':'值班 S166 上侧开门通 S159，原边跨过 S165',
'R171':'库房 S167 上侧开门通 S159，原 S160 仅接触角点',
'R173':'主任 S170 东侧开门通 S171',
'R185':'DR S193 清晰门在南侧 S190，北侧未见门洞',
'R186':'DR S194 清晰门在南侧 S190，北侧未见门洞',
'R187':'DR S195 清晰门在南侧 S190，北侧未见门洞',
'R188':'DR S196 清晰门在南侧 S190，北侧未见门洞',
'R189':'DR S197 清晰门在南侧 S190，北侧未见门洞',
'R199':'片库 S192 门开向 S191，西侧未见明确门洞',
'R200':'钼靶 S201 门在东侧 S190',
'R201':'口腔 S202 门在东侧 S207',
'R202':'骨密度 S203 门在东侧 S207',
'R207':'打印出片 S200 上方隔着 S199，不能直连 S188',
'R224':'值班 S219 与 S218 隔空调机房，改据局部门位连接',
'R225':'库房 S220 与 S218 隔空调机房，改据局部门位连接',
'R226':'交换 S221 门开向西侧交通核 S116，非跨机房连 S218',
'R231':'轮椅存车 S222 与 S226 隔 ATM，按西侧开口连接',
'R246':'筛查诊室西侧接 S238，原 S234 隔着大厅窄段',
'R249':'儿科诊室上侧开口接 S237',
'R250':'心电室上侧开口接 S237',
'R252':'外科上侧门接 S245，非跨 S236 连 S235',
'R253':'内科下侧门接清创 S252，非跨房连 S235',
'R254':'石膏下侧门接 S253，非跨房连 S235',
'R258':'急诊手术门开向 S272；S235 与其仅接角点',
'R260':'药房 S263 门开向 S266 收费工作区',
'R268':'药品 S269 可见门在北侧急诊手术一边',
'R274':'治疗 S274 西侧开门接 EICU S275',
'R275':'医生 S278 西侧开门接 EICU S275',
'R292':'S297 与 S301 中间隔 S298、S303，不直接接触',
'R307':'咖啡厅西侧开口接 S301，非北侧 S316',
'R336':'理发 S341 可见门在北侧 S329'
}
# 明确服务柜台前沿只记 service；员工入口另列待核。
service_ids={'R264','R296','R297'}
for r in d['relations']:
 if r['id'] in service_ids:r['type']='service'
d['relations']=[r for r in d['relations'] if r['id'] not in remove]
# 录入转正参考图上的人工观察，修正与原几何实际两侧对应。
rows=[]
for l in (out/'人工判读开口.txt').read_text().splitlines():
 if not l.strip() or l.startswith('#'):continue
 a,b,x,y,*kind=l.split();a='S'+a;b='S'+b;x=float(x);y=float(y)
 swaps={('S002','S017'):('S001','S017'),('S001','S029'):('S019','S029'),('S024','S026'):('S025','S026'),('S031','S045'):('S001','S045'),('S046','S048'):('S047','S048'),('S051','S076'):('S075','S076'),('S110','S077'):('S107','S077'),('S187','S219'):('S344','S219'),('S112','S221'):('S116','S221'),('S112','S222'):('S116','S222'),('S316','S315'):('S301','S315'),('S235','S245'):('S237','S245'),('S235','S246'):('S237','S246'),('S236','S248'):('S245','S248'),('S235','S249'):('S252','S249'),('S235','S250'):('S253','S250')}
 if (a,b) in {('S187','S220'),('S226','S223'),('S226','S225')}:continue
 if (a,b)==('S112','S224'):a,b=('S219' if y<900 else 'S220'),'S224'
 a,b=swaps.get((a,b),(a,b))
 if (a,b) in {('S019','S029'),('S075','S076'),('S289','S290')}:continue
 if (a,b)==('S122','S124'):y=212
 if (a,b)==('S289','S290'):x,y=1113,950
 rows.append((a,b,x,y,kind[0] if kind else 'door'))
# 概念连续边不取中点补坐标。
concepts=[('S187','S344'),('S117','S319'),('S001','S031'),('S107','S113'),('S187','S207'),('S329','S337'),('S317','S319')]
maxr=max(int(r['id'][1:]) for r in original['relations'] if r['id'].startswith('R'))
lookup={(tuple(sorted([r['source'],r['target']])),r['type']):r for r in d['relations'] if r['type']!='entrance'}
def access(a,b):
 global maxr
 key=(tuple(sorted([a,b])),'access')
 if key not in lookup:
  maxr+=1;r={'id':f'R{maxr:03d}','source':a,'target':b,'type':'access'};d['relations'].append(r);lookup[key]=r
 return lookup[key]
# 先逐行分配 P 编号；同空间对自动并入同一条 relation，避免重复边。
for n,(a,b,x,y,k) in enumerate(rows,1):
 r=access(a,b);r.setdefault('openings',[]).append({'id':f'P{n:03d}','kind':k,'position_px':[1440-y,x]})
for a,b in concepts:access(a,b)
# 与具名原图逐轴同比例换算，不改变原图像素、朝向或文件字节。
fx=3064/1440;fy=3672/1725
def scale(q):return [round(q[0]*fx,2),round(q[1]*fy,2)]
for s in d['spaces']:s['polygon_px']=[scale(q) for q in s['polygon_px']]
for r in d['relations']:
 if 'position_px' in r:r['position_px']=scale(r['position_px'])
 for o in r.get('openings',[]):o['position_px']=scale(o['position_px'])
d['image']={'file':'03_晋中市第一人民医院迁建项目_原图.jpg','width':3064,'height':3672}
(stage/'annotation.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
import shutil
shutil.copy2(project/d['image']['file'],stage/d['image']['file'])
(out/'移除旧关系.json').write_text(json.dumps([dict(r,reason=remove[r['id']]) for r in original['relations'] if r['id'] in remove],ensure_ascii=False,indent=2)+'\n')
# 位置是近似门洞中心；大距离提示端点或范围需要重看，不能靠验证点数掩盖。
polys={s['id']:Polygon(s['polygon_px']) for s in d['spaces']}
issues=[]
for r in d['relations']:
 for o in r.get('openings',[]):
  q=Point(o['position_px']);dist=[round(polys[s].distance(q),2) for s in [r['source'],r['target']]]
  if max(dist)>5:issues.append([o['id'],r['source'],r['target'],dist])
print('spaces',len(d['spaces']),'relations',len(d['relations']),'points',len(rows),'removed',len(remove),'point-distance issues',issues)
with (out/'未定位关系盘点.txt').open('w') as f:
 for r in d['relations']:
  if r['type']=='access' and not r.get('openings'):
   a,b=r['source'],r['target'];f.write(f"{r['id']} {a} {ss[a]['name']} — {b} {ss[b]['name']} distance={polys[a].distance(polys[b]):.1f}\n")
