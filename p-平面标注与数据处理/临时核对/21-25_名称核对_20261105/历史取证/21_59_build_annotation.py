import json,sys,hashlib
from pathlib import Path
sys.path.insert(0,'/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts')
import annotation_tools as at
from shapely.geometry import Polygon,box
P=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-写作过程/标注试样/21_海军总医院外科医疗大楼')
T=Path('/tmp/outpatient21-review')
W,H=2444,3260
items=[];rels=[]
# All working coordinates below refer to the temporary counterclockwise reading view.
# Source transformation: original (x,y)=(W-1-reading_y, reading_x).
def add(k,n,t,b,scope='emergency',level='room',cand='',why='',confidence='低',group=0):
 pts=list(box(*b).exterior.coords)[:-1] if len(b)==4 and isinstance(b[0],(int,float)) else b
 items.append(dict(key=k,name=n or '名称未确认',type=t if n else 'unknown',level=level,scope=scope,rpoly=pts,candidate=cand,evidence=why,confidence=confidence,group=group))
def a(k,n,t,b,**kw):add(k,n,t,b,**kw)
def unk(k,b,cand,why,**kw):add(k,None,'unknown',b,cand=cand,why=why,**kw)
def link(a,b,t='access'):rels.append((a,b,t))
# A: original upper-left perimeter, then original upper-right rooms.
for i,(x1,x2) in enumerate([(233,365),(365,495),(495,628),(628,758),(758,852)],1):
 unk('acute_bed'+str(i),(x1,1400,x2,1556),'观察室 / 治疗室','每间约4床，原字形近观察或治疗；需确认',group=0,confidence='中')
a('resusc','抢救','resuscitation',(233,547,415,779),group=1)
unk('med1',(233,779,311,867),'医办 / 辅助用房','两字竖排模糊，位于抢救与手术旁',group=1)
unk('med2',(233,867,311,958),'医办 / 辅助用房','与上一小间相同字形，独立开门',group=1)
unk('preop',(312,779,415,834),'术前准备 / 器械间','无清晰文字，紧邻手术房、绘有操作台',group=1)
a('surgery','手术','treatment',(312,834,415,958),group=1)
unk('multi_bed',(233,959,415,1220),'留观室 / 监护室','约4床与中央工作台，室名无法清读',group=1)
a('air','空调机房','building_services',(233,1221,415,1325),group=1)
a('acute_vest','急诊门斗','entrance',(415,463,577,545),level='open_space',group=1)
# B: upper central island.
unk('acute_top',(578,485,670,571),'后勤 / 辅助用房','文字近后勤，包含小型操作设施',group=2)
a('clean1','清洗','sterile_supply',(671,485,744,530),group=2)
a('lift1','污梯及前室','vertical_core',(579,573,744,632),level='core_block',group=2)
a('stor1','库房','storage',(579,634,670,690),group=2)
unk('stor2',(671,634,763,690),'器械 / 辅助用房','双字模糊，邻库房及收费',group=2)
a('cash','收费','registration',(799,490,843,650),group=2)
a('pharmacy','药房','pharmacy',(845,491,932,650),group=2)
a('lab','检验','laboratory',(976,499,1104,574),group=2)
unk('lab_side',(976,592,1104,659),'采血 / 检验支持','邻检验，原图无清晰室名',group=2)
a('lab_access','检验前通道','corridor',[(933,492),(975,492),(975,660),(1104,660),(1104,690),(933,690)],level='open_space',group=2)
# C: acute central consultation island.
a('orth','骨科','consultation',(749,790,842,872),group=3)
unk('orth_side',(844,790,936,872),'诊室 / 检查室','诊桌及床符号，与骨科相邻，未见清晰室名',group=3)
a('surg_cons','外科','consultation',(749,874,842,978),group=3)
a('gyn','妇科','consultation',(844,874,936,978),group=3)
a('wc_m','男卫生间','toilet',(938,790,1038,874),group=3)
a('wc_f','女卫生间','toilet',(938,877,1038,979),group=3)
a('acute_core','急诊楼梯及电梯核','vertical_core',(477,865,608,1057),level='core_block',group=3)
a('elect1','强电','building_services',(609,868,643,927),group=3)
a('elect2','弱电','building_services',(609,929,643,993),group=3)
a('elect3','电井','building_services',(609,995,643,1057),group=3)
a('triage','分诊','triage',(478,787,580,863),level='semi_open_space',group=3)
a('wait1','候诊','hall',(477,1060,745,1338),level='open_space',group=3)
a('ent','耳鼻喉','consultation',(749,1132,842,1222),group=4)
a('dental','口腔','consultation',(844,1132,935,1222),group=4)
a('derm','皮肤','consultation',(937,1132,1038,1222),group=4)
a('nurse','护士站','nurse_station',(725,1230,791,1338),level='semi_open_space',group=4)
a('docoff','医办','office',(793,1224,855,1281),group=4)
a('dirty','污房','waste_handling',(793,1283,855,1338),group=4)
a('wc2m','男卫生间','toilet',(857,1242,1060,1299),group=4)
a('wc2f','女卫生间','toilet',(857,1301,1060,1360),group=4)
a('neurology','神经','consultation',(1108,865,1204,960),group=4)
a('pediatrics','儿科','consultation',(1108,962,1204,1048),group=4)
a('property1','物业','staff_support',(1206,865,1285,1048),group=4)
a('med_cons1','内科','consultation',(1108,1050,1204,1135),group=4)
a('med_cons2','内科','consultation',(1108,1137,1204,1222),group=4)
a('property2','物业','staff_support',(1206,1050,1285,1222),group=4)
a('core2','楼梯及前室','vertical_core',[(1108,1225),(1285,1225),(1285,1393),(1207,1393),(1207,1356),(1108,1356)],level='core_block',group=4)
a('duty0','值班','staff_support',(1108,1306,1205,1355),group=4)
# Acute offices at original left lower edge.
a('duty1','值班','staff_support',(854,1400,944,1474),group=5)
a('director','主任','office',(854,1476,944,1556),group=5)
a('off1','办公室','office',(946,1476,1027,1556),group=5)
a('off2','办公室','office',(1029,1476,1117,1556),group=5)
a('off3','办公室','office',(1119,1476,1207,1556),group=5)
a('headnurse','护士长','office',(1209,1476,1285,1556),group=5)
a('duty2','值班','staff_support',(1209,1400,1285,1474),group=5)
a('meeting','会议','office',(946,1400,1207,1474),group=5)
# Circulation bands: split only to avoid polygons with holes around islands.
a('acute_hall','急诊大厅','hall',[(417,547),(577,547),(577,692),(1105,692),(1105,787),(747,787),(747,863),(582,863),(582,785),(477,785),(477,865),(417,865)],level='open_space',group=2)
a('acute_west','急诊西侧通道','corridor',[(417,865),(475,865),(475,1340),(747,1340),(747,1397),(417,1397)],level='open_space',group=3)
a('acute_mid','急诊中部通道','corridor',[(645,865),(747,865),(747,980),(1039,980),(1039,1129),(747,1129),(747,1338),(645,1338),(645,1058),(645,1058)],level='open_space',group=3)
a('acute_east','急诊东侧通道','corridor',(1040,790,1105,1224),level='open_space',group=4)
a('acute_south','急诊南侧通道','corridor',(1062,1225,1105,1397),level='open_space',group=4)
a('acute_cross','急诊办公前通道','corridor',(747,1362,1285,1397),level='open_space',group=5)
# D: central lobby, main vertical cores and commercial/service zones.
a('vest_main','门厅','hall',(1288,386,1975,500),scope='public_service',level='open_space',group=6)
a('core_main1','西侧客梯及楼梯核','vertical_core',(1288,502,1463,738),scope='public_service',level='core_block',group=6)
a('core_main2','东侧客梯医梯及楼梯核','vertical_core',(1621,502,1830,738),scope='public_service',level='core_block',group=6)
a('lift_wait','候梯厅','hall',(1465,502,1619,738),scope='public_service',level='open_space',group=6)
a('guide','导医台','service',(1485,798,1575,858),scope='public_service',level='semi_open_space',group=6)
a('shop','超市花店','retail_service',(1792,860,1975,1045),scope='public_service',group=6)
a('coffee','咖啡休息','retail_service',[(1738,1050),(1975,1050),(1975,1218),(1795,1218),(1795,1348),(1738,1348)],scope='public_service',level='open_space',group=6)
a('core_coffee','咖啡区楼梯','vertical_core',(1797,1220,1975,1294),scope='public_service',level='core_block',group=6)
a('wc_coffee','卫生间','toilet',(1978,860,2142,982),scope='public_service',group=7)
a('prep_coffee','备餐','staff_support',(1978,984,2070,1044),scope='public_service',group=7)
a('phone','吧台','service',(1978,1046,2050,1110),scope='public_service',level='semi_open_space',group=7)
a('fastfood','快餐','retail_service',[(2052,984),(2142,984),(2142,1298),(1978,1298),(1978,1112),(2052,1112)],scope='public_service',level='open_space',group=7)
a('inpatient_hall','住院大厅','hall',[(1288,740),(1830,740),(1830,502),(1975,502),(1975,858),(1790,858),(1790,1048),(1736,1048),(1736,1350),(1795,1350),(1795,1556),(1288,1556)],scope='public_service',level='open_space',group=6)
# Guide is a separately outlined semi-open subarea; split the hall around it without a hole using a narrow service boundary.
# E: health examination zone.
a('exam_wait','候诊','hall',[(1797,1297),(1975,1297),(1975,1300),(2142,1300),(2142,1400),(1797,1400)],scope='health_examination',level='open_space',group=7)
a('exam_triage','导医','triage',(1797,1402,2072,1556),scope='health_examination',level='semi_open_space',group=7)
a('blood','抽血','laboratory',(2074,1458,2142,1556),scope='health_examination',group=7)
for k,n,t,b in [
 ('exam_dir','主任','office',(2145,946,2200,1053)),('finance','财会','office',(2202,946,2262,1053)),('computer','库房','storage',(2264,946,2328,1053)),('menchange','男更','staff_support',(2330,946,2378,1053)),('womenchange','女更','staff_support',(2380,946,2440,1053)),
 ('doctor','医办','office',(2192,1097,2319,1173)),('nurseoff','护办','office',(2192,1175,2319,1225)),('consult','咨询','service',(2210,1227,2273,1333)),('checkup','主检','examination',(2275,1227,2380,1333)),('eye','眼科','consultation',(2382,1227,2440,1333)),
 ('ear','耳鼻喉','consultation',(2145,1458,2228,1556)),('oral','口腔','consultation',(2230,1458,2310,1556)),('surg1','外科','consultation',(2312,1458,2397,1556)),('surg2','外科','consultation',(2399,1458,2488,1556)),('inter1','内科','consultation',(2490,1458,2575,1556)),('inter2','内科','consultation',(2577,1458,2665,1556)),('gyn_exam','妇科','consultation',(2667,1458,2748,1556)),('ophth','眼科','consultation',(2750,1458,2834,1556)),('us','B超','examination',(2679,1228,2750,1333)),('us2','超声','examination',(2752,1228,2834,1333)),('water','开水','staff_support',(2836,1276,2880,1333))]:
 a(k,n,t,b,scope='health_examination',group=8)
unk('physio',(2488,1228,2555,1333),'动脉硬化检查 / 前列腺检查','室名首尾字近前列腺或动脉，绘有检查床',scope='health_examination',group=8)
unk('ecg',(2557,1228,2613,1333),'心电图','室名可见心字，检查床与仪器符号',scope='health_examination',confidence='中',group=8)
unk('eeg',(2615,1228,2677,1333),'电测听 / 电生理检查','可见电字，其余文字模糊',scope='health_examination',group=8)
unk('file',(2836,1228,2880,1274),'档案资料室','两行字形近档案资料，房间较小',scope='health_examination',confidence='中',group=8)
a('exam_wcm','男卫生间','toilet',(2342,1097,2480,1165),scope='health_examination',group=8)
a('exam_wcf','女卫生间','toilet',(2342,1167,2480,1225),scope='health_examination',group=8)
a('exam_corr','候诊廊','corridor',[(2144,1335),(2486,1335),(2486,1227),(2486,1227),(2486,1335),(2880,1335),(2880,1456),(2144,1456)],scope='health_examination',level='open_space',group=8)
a('exam_inner','体检内部通道','corridor',[(2144,1055),(2442,1055),(2442,946),(2481,946),(2481,1095),(2321,1095),(2321,1226),(2340,1226),(2340,1333),(2319,1333),(2319,1227),(2144,1227)],scope='health_examination',level='open_space',group=8)
a('exam_link','体检检查区通道','corridor',(2442,1227,2486,1333),scope='health_examination',level='open_space',group=8)
a('computer_room','中控室','building_control',(2546,1056,2880,1182),scope='building_support',group=9)
a('control_corr','中控室前通道','corridor',[(2482,1056),(2544,1056),(2544,1184),(2880,1184),(2880,1225),(2482,1225)],scope='public_service',level='open_space',group=9)
a('core_east','楼梯及电梯核','vertical_core',(2442,858,2550,1053),scope='public_service',level='core_block',group=9)
unk('elect_east',(2552,858,2616,1053),'管线井 / 设备井','长条竖井及上部密集竖排文字',scope='building_support',group=9)
a('vip','首长专用门厅','hall',(2618,858,2880,1053),scope='vip_service',level='open_space',group=9)
# F: plastic surgery; assign per adjacent room bands in original upper to lower order.
for k,n,t,b in [
 ('skin1','皮护','treatment',(1978,490,2067,626)),('skin2','皮护','treatment',(2069,488,2150,626)),('skin3','皮护','treatment',(2152,486,2239,626)),('laser1','点痣','treatment',(2241,485,2314,571)),('laser2','激光','treatment',(2241,573,2314,626)),
 ('push','推拿','treatment',(1978,680,2046,809)),('beauty','美体','treatment',(2048,680,2150,809)),('hair','育发','treatment',(2152,680,2239,743)),('haircare','护发','treatment',(2152,745,2239,809)),('light','激光','treatment',(2241,680,2326,743)),('wrinkle','纹眉','treatment',(2241,745,2326,809)),
 ('cos_dir','主任','office',(2371,858,2440,944)),('cos_consult','咨询','service',(2298,858,2369,944)),('duty_cos','值班','staff_support',(2232,858,2296,944)),('change_cos','更衣','staff_support',(2145,858,2182,944)),('cos_wash','洗手间','toilet',(2184,858,2230,944)),
 ('diag','诊室','consultation',(2370,680,2435,754)),('expert','专家','consultation',(2437,680,2499,754)),('beautymed','美容','treatment',(2370,756,2460,809)),('hotwater_cos','开水','staff_support',(2462,756,2499,809)),('doctor_cos','医办','office',(2501,720,2599,809)),('toilet_cos','卫生间','toilet',(2601,720,2662,809)),
 ('cos_dirty','污物','waste_handling',(2316,484,2372,542)),('cos_wash2','清洗','sterile_supply',(2374,483,2420,542)),('cos_store','库房','storage',(2422,482,2499,570)),('cos_lift','污梯及前室','vertical_core',(2338,573,2499,634)),
 ('recover','恢复室','observation',(2679,542,2880,626)),('dresschange','处置换药','treatment',(2739,628,2880,686)),('procedure','处理室','treatment',(2739,688,2880,774)),('prep','准备','patient_preparation',(2783,776,2880,853)),('cos_recept','咨询','service',(2501,680,2677,718))]:
 a(k,n,t,b,scope='plastic_surgery',level='core_block' if t=='vertical_core' else 'room',group=10)
a('cos_hall','整形厅','hall',(2501,548,2677,678),scope='plastic_surgery',level='open_space',group=11)
a('cos_vest','整形门斗','entrance',(2501,463,2677,546),scope='plastic_surgery',level='open_space',group=11)
a('cos_corr','整形主通道','corridor',[(1978,628),(2316,628),(2316,544),(2336,544),(2336,636),(2500,636),(2500,678),(2328,678),(2328,811),(2677,811),(2677,720),(2737,720),(2737,855),(2152,855),(2152,811),(1978,811),(1978,811),(2150,811),(2150,678),(1978,678)],scope='plastic_surgery',level='open_space',group=10)
a('cos_right_corr','整形东侧通道', 'corridor',[(2679,628),(2737,628),(2737,776),(2781,776),(2781,853),(2679,853)],scope='plastic_surgery',level='open_space',group=11)
# Remove the separately marked guide island from the large lobby with a small slit to a conceptual service boundary.
# This avoids double area and keeps a simple single-ring polygon.
hall=next(i for i in items if i['key']=='inpatient_hall')
g=box(1485,798,1575,858)
hp=Polygon(hall['rpoly']).difference(g.union(box(1530,738,1530.02,798)))
assert hp.geom_type=='Polygon' and not hp.interiors
hall['rpoly']=list(hp.exterior.coords)[:-1]
# Stable S order: adjacent clusters; original image top to bottom, left to right within each row.
# Group order is spatial, with large circulation zones at the end of each respective group.
items.sort(key=lambda i:(i['group'],min(p[0] for p in i['rpoly'])//90,-max(p[1] for p in i['rpoly']),min(p[0] for p in i['rpoly'])))
for ix,i in enumerate(items,1):i['id']=f'S{ix:03d}'
keys={i['key']:i['id'] for i in items}
spaces=[]
for i in items:
 pts=[[round(W-1-y,2),round(x,2)] for x,y in i['rpoly']]
 spaces.append({k:i[k] for k in ['id','name','type','level','scope']}|{'polygon_px':pts})
# Clearly drawn doors and continuous passages only; no automatic adjacency-to-access conversion.
for k in ['resusc','surgery','med1','med2','multi_bed','air','acute_bed1','acute_bed2','acute_bed3','acute_bed4','acute_bed5']:link(k,'acute_west' if k.startswith('acute_bed') or k in ['multi_bed','air'] else 'acute_hall')
for k in ['cash','pharmacy']:link(k,'acute_hall','service')
for k in ['orth','surg_cons','gyn','ent','dental','derm']:link(k,'acute_mid')
for k in ['neurology','pediatrics','med_cons1','med_cons2']:link(k,'acute_east')
for k in ['director','off1','off2','off3','headnurse','duty1','duty2']:link(k,'meeting')
for u,v in [('acute_hall','acute_west'),('acute_hall','acute_mid'),('acute_hall','acute_east'),('acute_west','acute_cross'),('acute_mid','acute_cross'),('acute_east','acute_south'),('acute_south','acute_cross'),('acute_vest','acute_hall'),('wait1','acute_west'),('wait1','acute_mid'),('triage','acute_hall'),('acute_core','acute_west'),('core2','acute_south'),('meeting','acute_cross'),('vest_main','lift_wait'),('lift_wait','inpatient_hall'),('core_main1','inpatient_hall'),('core_main2','inpatient_hall'),('guide','inpatient_hall'),('shop','inpatient_hall'),('coffee','inpatient_hall'),('coffee','fastfood'),('coffee','core_coffee'),('fastfood','prep_coffee'),('phone','fastfood'),('wc_coffee','fastfood'),('exam_wait','exam_triage'),('exam_triage','exam_corr'),('exam_corr','exam_inner'),('exam_inner','exam_link'),('exam_link','exam_corr'),('control_corr','computer_room'),('control_corr','core_east'),('cos_vest','cos_hall'),('cos_hall','cos_corr'),('cos_hall','cos_right_corr'),('cos_corr','cos_right_corr'),('vip','core_east')]:link(u,v)
for k in ['ear','oral','surg1','surg2','inter1','inter2','gyn_exam','ophth','blood','physio','ecg','eeg','us','us2','file','water','consult','checkup','eye']:link(k,'exam_corr')
for k in ['exam_dir','finance','computer','menchange','womenchange','doctor','nurseoff','exam_wcm','exam_wcf']:link(k,'exam_inner')
for k in ['skin1','skin2','skin3','laser1','laser2','push','beauty','hair','haircare','light','wrinkle','cos_dir','cos_consult','duty_cos','change_cos','cos_wash','diag','expert','beautymed','cos_dirty','cos_store','cos_lift']:link(k,'cos_corr')
for k in ['recover','dresschange','procedure','prep','doctor_cos','toilet_cos']:link(k,'cos_right_corr')
link('cos_recept','cos_hall','service')
# Known shared partitions (independent of access).
for a1,b1 in [('cash','pharmacy'),('orth','orth_side'),('surg_cons','gyn'),('ent','dental'),('dental','derm'),('med_cons1','med_cons2'),('skin1','skin2'),('skin2','skin3'),('laser1','laser2'),('hair','haircare'),('light','wrinkle'),('diag','expert'),('doctor','nurseoff'),('ear','oral'),('surg1','surg2')]:link(a1,b1,'shared_wall')
rr=[];seen=set()
for u,v,t in rels:
 kk=tuple(sorted([u,v]))+(t,)
 if kk in seen:continue
 seen.add(kk);rr.append(dict(id=f'R{len(rr)+1:03d}',source=keys[u],target=keys[v],type=t))
for ix,(n,k,xy,typ) in enumerate([('急诊入口','acute_vest',(493,464),'emergency'),('北入口','vest_main',(1522,387),'public'),('南入口','inpatient_hall',(1528,1556),'public'),('整形入口','cos_vest',(2585,464),'specialty'),('行政入口','control_corr',(2879,1202),'staff'),('首长入口','vip',(2879,955),'vip')],1):
 rr.append(dict(id=f'E{ix:03d}',source=None,target=keys[k],type='entrance',name=n,entrance_type=typ,position_px=[W-1-xy[1],xy[0]]))
data=dict(image=dict(file='21_海军总医院外科医疗大楼_原图.jpg',width=W,height=H),spaces=spaces,relations=rr)
at.normalize(data)
(P/'annotation.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
(T/'reading_items.json').write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n')
print(len(items),'spaces;',sum(i['type']=='unknown' for i in items),'unknown;',len(rr),'relations')