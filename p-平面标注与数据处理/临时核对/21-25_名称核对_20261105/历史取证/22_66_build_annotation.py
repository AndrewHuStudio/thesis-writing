from pathlib import Path
import json, hashlib
from shapely.geometry import Polygon
P=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-写作过程/标注试样/22_山东省中医院国家中医临床研究基地综合楼')
T=Path('/tmp/outpatient22-review')
source=next(P.glob('*.jpg'))
spaces=[]; ids={}; questions=[];rels=[]
def rect(a,b,c,d):return [[a,b],[c,b],[c,d],[a,d]]
def add(key,name,typ,poly,level='room',scope='ordinary_outpatient',candidate=None,basis=None,confidence=None):
 sid=f'S{len(spaces)+1:03d}';ids[key]=sid
 spaces.append(dict(id=sid,name=name,type=typ,level=level,scope=scope,polygon_px=poly))
 if typ=='unknown':questions.append(dict(key=key,id=sid,candidate=candidate or '未知',basis=basis or '图面文字无法辨认',confidence=confidence or '低'))
 return sid
def box(key,name,typ,bounds,**kw):return add(key,name,typ,rect(*bounds),**kw)
def unk(key,bounds,candidate,basis,confidence='中',level='room',scope='public_service'):
 return box(key,'名称未确认','unknown',bounds,level=level,scope=scope,candidate=candidate,basis=basis,confidence=confidence)
def link(a,b,typ='access'):
 source,target=ids[a],ids[b]
 if any(r['type']==typ and {r['source'],r['target']}=={source,target} for r in rels):return
 rels.append(dict(id=f'R{len(rels)+1:03d}',source=source,target=target,type=typ))
# 北侧整排，自左至右。
box('wc_nw','卫生间','toilet',(560,490,947,620),level='functional_block',scope='public_service')
xs=[947,1026,1104,1183,1261,1340,1420]
for i in range(6):box(f'n{i}','诊室','consultation',(xs[i],490,xs[i+1],620))
box('office_n','医生办公','office',(1420,490,1534,620))
add('stair_n','楼梯及前室','vertical_core',[[1534,490],[1728,490],[1728,620],[1618,620],[1618,575],[1534,575]],level='core_block',scope='public_service')
unk('small_n',(1534,575,1618,620),'管井 / 前室','位于北侧楼梯下方，双字标签模糊')
unk('supply_n',(1728,490,1800,620),'病人用品 / 医护用品','北侧楼梯与卫生间之间，似有“用品”字样','低')
box('wc_ne','卫生间','toilet',(1800,490,1925,620),level='functional_block',scope='public_service')
# 北部候诊及诊室内排。
box('wait_n','候诊区','hall',(560,620,750,995),level='open_space')
box('corr_n','北侧门诊通道','corridor',(750,620,1925,694),level='open_space')
add('corr_w','门诊西侧通道','corridor',[[750,694],[878,694],[878,834],[942,834],[942,1002],[865,1002],[865,1352],[750,1352]],level='open_space')
box('nurse_n','护士站','nurse_station',(878,694,947,834),level='semi_open_space')
for i in range(6):box(f'ns{i}','诊室','consultation',(xs[i],694,xs[i+1],820))
box('treat_n','治疗室','treatment',(1420,694,1535,820))
unk('garden',(942,820,1535,1002),'内庭院：露天/挑空庭院 / 室内景观','绿色植物及步道填色，可辨“内庭院”；未标明顶盖','中',level='functional_block',scope='public_service')
# 西中部交通、候诊及第二诊室组。
box('core_w1','楼梯、电梯及前室','vertical_core',(560,995,750,1152),level='core_block',scope='public_service')
unk('small_w1',(560,1152,750,1208),'管井 / 前室','西侧交通核下方，通道侧有开口，双字标签模糊')
unk('supply_w',(560,1208,750,1274),'病人用品 / 病人休息','靠近门诊电梯，四字标签疑似“病人用品”','中')
box('lift_w1','门诊电梯组','vertical_core',(560,1274,750,1358),level='core_block',scope='public_service')
box('lift_hall_w','门诊电梯厅','hall',(560,1358,750,1514),level='open_space',scope='public_service')
add('wait_m','候诊区','hall',[[865,1002],[1057,1002],[1057,1125],[1104,1125],[1104,1352],[865,1352]],level='open_space')
box('nurse_m','护士站','nurse_station',(1057,1002,1104,1125),level='semi_open_space')
xx=[1104,1183,1261,1340,1420]
for i in range(4):box(f'm{i}','诊室','consultation',(xx[i],1002,xx[i+1],1125))
box('office_m','医生办公','office',(1420,1002,1535,1125))
box('corr_m','中部门诊通道','corridor',(1104,1125,1535,1200),level='open_space')
for i in range(4):box(f'ms{i}','诊室','consultation',(xx[i],1200,xx[i+1],1352))
box('treat_m','治疗室','treatment',(1420,1200,1535,1352))
box('corr_e','门诊东侧通道','corridor',(1535,694,1630,1352),level='open_space')
# 东中部输液与医护交通。
add('infusion','输液中心','treatment',[[1630,694],[1925,694],[1925,1200],[1724,1200],[1724,1352],[1630,1352]],level='functional_block')
box('nurse_i','护士站','nurse_station',(1724,1200,1848,1352),level='room')
box('prep_i','配药','medication_preparation',(1848,1200,1925,1352))
box('disposal_i','处置','treatment',(1724,1352,1808,1411))
box('lift_i','医护电梯组','vertical_core',(1808,1352,1925,1411),level='core_block',scope='staff_circulation')
box('hall_i','门诊医护电梯厅','hall',(1724,1411,1925,1498),level='open_space',scope='staff_circulation')
unk('small_e1',(1827,1498,1925,1556),'管井 / 前室','医护楼梯旁，双字标签与其他交通核旁小室相似')
add('core_e1','医护楼梯、电梯及前室','vertical_core',[[1724,1498],[1827,1498],[1827,1556],[1925,1556],[1925,1710],[1724,1710]],level='core_block',scope='staff_circulation')
box('reg','挂号/收费','registration',(1630,1498,1724,1710),level='semi_open_space',scope='public_service')
# 中部大厅与中厅上空。
unk('pharm_support',(560,1514,750,1727),'药房配套用房 / 药房办公','紧邻西药房、同色分区，室内四至五字标签模糊','低')
add('hall_mid','中部门诊大厅','hall',[[750,1352],[1724,1352],[1724,1498],[1630,1498],[1630,1710],[1335,1710],[1335,1624],[1286,1624],[1286,1530],[985,1530],[985,1624],[950,1624],[950,1710],[750,1710]],level='open_space',scope='public_service')
box('escalator','自动扶梯组','vertical_core',(985,1530,1286,1624),level='core_block',scope='public_service')
box('void','中厅上空','courtyard',(950,1624,1335,2138),level='open_space',scope='public_service')
box('pharm_w','西药房','pharmacy',(560,1727,765,2138),level='functional_block')
add('hall_w','中厅西侧通道','corridor',[[750,1710],[950,1710],[950,2138],[765,2138],[765,1727],[750,1727]],level='open_space',scope='public_service')
add('hall_s','中厅东侧及南侧通道','corridor',[[1335,1710],[1530,1710],[1530,2338],[765,2338],[765,2138],[1335,2138]],level='open_space',scope='public_service')
# 西南交通核与东侧住院支持。
box('core_w2','楼梯、电梯及前室','vertical_core',(560,2138,765,2297),level='core_block',scope='public_service')
unk('small_w2',(560,2297,765,2338),'管井 / 前室','西南交通核下方，双字标签模糊')
box('hall_inpatient','病房电梯厅','hall',(1724,1710,1925,1838),level='open_space',scope='inpatient_support')
box('lift_inpatient','病房电梯组','vertical_core',(1724,1838,1925,1920),level='core_block',scope='inpatient_support')
unk('small_e2',(1724,1920,1832,1980),'管井 / 前室','病房电梯下方上排小室，双字标签模糊',scope='inpatient_support')
unk('small_e3',(1724,1980,1832,2058),'管井 / 前室','病房电梯下方下排小室，双字标签模糊',scope='inpatient_support')
add('stair_e2','楼梯及前室','vertical_core',[[1832,1920],[1925,1920],[1925,2138],[1724,2138],[1724,2058],[1832,2058]],level='core_block',scope='inpatient_support')
box('wc_se','卫生间','toilet',(1724,2138,1925,2200),level='functional_block',scope='public_service')
unk('admit',(1724,2253,1925,2338),'出入院手续 / 入院登记','位于出入院大厅旁，标签末字近似“手续”','中',scope='inpatient_support')
add('lobby','出入院大厅及中医文化廊','hall',[[1530,1710],[1724,1710],[1724,2200],[1925,2200],[1925,2253],[1724,2253],[1724,2338],[1925,2338],[1925,2488],[1780,2488],[1780,2640],[1530,2640]],level='open_space',scope='inpatient_support')
# 底部药房与出入院服务。
box('pharm_s','中药房','pharmacy',(560,2338,1335,2640),level='functional_block')
unk('entry_room',(1335,2338,1530,2488),'便民服务 / 便民超市','出入院大厅西侧独立房间，四字标签模糊','低',scope='public_service')
box('lounge','会客','hall',(1335,2488,1530,2640),level='open_space',scope='public_service')
unk('info',(1780,2488,1925,2640),'信息导诊 / 信息管理','大厅东南角有桌椅，标签近似“信息…”','低',level='open_space',scope='public_service')
# 室外绿化只覆盖主要可见绿化带，不把门前台阶当室内空间。
box('green_w','室外绿化','landscape',(468,2155,560,2640),level='landscape',scope='external_landscape')
box('green_e','室外绿化','landscape',(1925,2138,2034,2640),level='landscape',scope='external_landscape')
add('green_front','室外绿化','landscape',[[468,2640],[1530,2640],[1530,2648],[1450,2655],[1360,2690],[1280,2768],[515,2768],[468,2720]],level='landscape',scope='external_landscape')
# 仅记录从图面门扇或连续开放区域可支持的可达关系。
link('wait_n','corr_n');link('wait_n','corr_w');link('corr_n','corr_w');link('corr_n','corr_e');link('corr_w','wait_m');link('corr_w','hall_mid');link('wait_m','corr_m');link('wait_m','hall_mid');link('corr_m','corr_e');link('corr_e','hall_mid')
for k in ['wc_nw','office_n','stair_n','supply_n','wc_ne']+[f'n{i}' for i in range(6)]+[f'ns{i}' for i in range(6)]+['treat_n']:link(k,'corr_n')
# 半墙工作区有朝向候诊/通道的开放边界；窗口服务与可达分开。
link('nurse_n','corr_n');link('nurse_n','corr_w','service');link('nurse_m','wait_m');link('nurse_m','wait_m','service')
for k in [f'm{i}' for i in range(4)]+[f'ms{i}' for i in range(4)]+['office_m','treat_m']:link(k,'corr_m')
link('supply_w','corr_w');link('lift_hall_w','hall_mid');link('lift_w1','lift_hall_w')
# 小室用途未定，先只保存明确共墙，不由邻接推断可通行。
for a,b in [('small_n','stair_n'),('small_w1','core_w1'),('small_w2','core_w2'),('small_e1','core_e1'),('small_e2','stair_e2'),('small_e3','stair_e2')]:link(a,b,'shared_wall')
link('infusion','corr_n');link('infusion','corr_e');link('nurse_i','disposal_i');link('nurse_i','prep_i');link('hall_i','hall_mid');link('hall_i','core_e1');link('hall_i','lift_i');link('reg','hall_mid','service')
link('pharm_support','hall_mid');link('pharm_support','pharm_w');link('pharm_w','hall_w');link('hall_mid','hall_w');link('hall_mid','hall_s');link('hall_mid','escalator');link('hall_w','hall_s');link('core_w2','hall_s');link('hall_s','pharm_s');link('hall_s','entry_room');link('entry_room','lobby');link('hall_s','lobby')
link('lobby','hall_inpatient');link('hall_inpatient','lift_inpatient');link('lobby','stair_e2');link('lobby','wc_se');link('lobby','admit');link('lobby','lounge');link('lobby','info')
rels.append(dict(id='E001',source=None,target=ids['lobby'],type='entrance',name='出入院大厅主入口',entrance_type='main',position_px=[1630,2640]))
data=dict(image=dict(file=source.name,width=2424,height=3244),spaces=spaces,relations=rels)
(P/'annotation.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
# 按核对空间所在连续片区固定本轮映射；上到下、同排从左到右。
order=['small_n','supply_n','garden','small_w1','supply_w','small_e1','pharm_support','small_e2','small_e3','small_w2','admit','entry_room','info']
questions.sort(key=lambda q:order.index(q['key']))
for i,q in enumerate(questions,1):q['number']=f'{i:02d}'
(T/'review-map.json').write_text(json.dumps(questions,ensure_ascii=False,indent=2)+'\n')
(T/'ids.json').write_text(json.dumps(ids,ensure_ascii=False,indent=2))
(T/'source.sha256').write_text(hashlib.sha256(source.read_bytes()).hexdigest())
print('spaces',len(spaces),'relations',len(rels),'pending',len(questions));print(json.dumps(questions,ensure_ascii=False,indent=2))