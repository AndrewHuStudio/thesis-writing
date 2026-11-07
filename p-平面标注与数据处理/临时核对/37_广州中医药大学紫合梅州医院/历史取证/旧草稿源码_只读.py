from pathlib import Path
from PIL import Image
from shapely.geometry import Polygon
import json,hashlib
ROOT=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-写作过程/标注试样/37_广州中医药大学紫合梅州医院')
TMP=Path('/tmp/outpatient37-review')
spaces=[]; meta=[]; keys={}; relations=[]
def rect(x1,y1,x2,y2): return [(x1,y1),(x2,y1),(x2,y2),(x1,y2)]
def add(key,name,typ,p,scope='public_service',level='functional_block',cand=None,evidence=None,confidence=None):
 sid=f'S{len(spaces)+1:03d}'; keys[key]=sid
 spaces.append(dict(id=sid,name=name,type=typ,level=level,scope=scope,polygon_px=[[2484-y,x] for x,y in p]))
 meta.append(dict(id=sid,key=key,polygon=p,candidates=cand,evidence=evidence,confidence=confidence))
def unknown(key,p,scope,cand,evidence,confidence='低'):
 add(key,'名称未确认','unknown',p,scope,cand=cand,evidence=evidence,confidence=confidence)
def rel(a,b,typ='access'):
 relations.append(dict(id=f'R{len(relations)+1:03d}',source=keys[a],target=keys[b],type=typ))
def entry(key,name,point,typ):
 relations.append(dict(id=f'E{1+sum(r["type"]=="entrance" for r in relations):02d}',source=None,target=keys[key],type='entrance',name=name,entrance_type=typ,position_px=[2484-point[1],point[0]]))
# A 上部左侧商服、行政片区；按连续相邻单元读取。
unknown('nw_room',[(604,450),(694,450),(694,524),(626,620),(562,563),(598,510)],'public_service',['商业服务用房','门厅配套用房'],'邻接三处小卖部；没有图例编号。','低')
add('nw_lift','电梯交通核','vertical_core',rect(750,450,789,532),level='core_block')
add('nw_wc','卫生间','toilet',rect(791,450,829,532),level='functional_block')
unknown('office_n',rect(831,450,1001,532),'administrative_support',['办公用房组','办公配套用房组'],'位于开放办公北侧，分隔为多间；无独立房名。','中')
add('nw_stair','楼梯及电梯交通核','vertical_core',[(1003,450),(1145,450),(1145,531),(1103,531),(1103,494),(1048,494),(1048,531),(1003,531)],level='core_block')
unknown('office_ne',rect(1003,495,1101,531),'administrative_support',['办公配套用房组','设备用房组'],'夹在楼梯、电梯及开放办公之间，原图无用途文字。','低')
add('office','开放办公','office',rect(750,533,1053,592),'administrative_support')
unknown('reg_e',rect(1055,554,1146,650),'public_service',['挂号收费配套用房组','办公用房组'],'紧邻挂号收费和开放办公东端，由多间小房组成。','中')
add('reg','挂号收费','registration',rect(750,594,1053,637),level='semi_open_space')
add('nw_diagonal_stair','楼梯交通核','vertical_core',[(554,506),(630,553),(596,596),(522,549)],level='core_block')
add('shop1','小卖部','retail_service',[(521,550),(596,597),(625,621),(585,668),(491,595)],level='room')
add('bank','自助银行','retail_service',[(625,606),(695,656),(641,718),(588,673)],level='room')
add('shop2','小卖部','retail_service',[(489,597),(585,670),(532,735),(437,657)],level='room')
add('flower','花店','retail_service',[(586,675),(640,720),(585,780),(534,738)],level='room')
add('shop3','小卖部','retail_service',[(435,660),(531,739),(477,801),(379,723)],level='room')
add('convenience','便利店','retail_service',[(532,741),(584,784),(527,847),(479,804)],level='room')
add('sw_diagonal_core','楼梯交通核','vertical_core',[(377,726),(475,805),(420,869),(321,789)],level='core_block')
unknown('shop_s',[(420,835),(461,860),(505,893),(479,921),(387,850)],'public_service',['商业配套用房','设备用房'],'小卖部南端、外墙与楼梯边的无编号房间。','低')
add('waiting_pharm','候药大厅','hall',[(695,450),(748,450),(748,639),(1150,639),(1150,874),(597,874),(597,929),(519,949),(481,921),(506,894),(480,872),(527,849),(585,783),(643,722),(697,658),(627,604),(695,524)],level='open_space')
# B 中央公共门厅：分成不重叠两半以避让导诊与中央交通核。
add('lobby_w','中央公共门厅西区','hall',[(1235,414),(1375,414),(1375,594),(1340,594),(1320,608),(1320,660),(1340,678),(1375,678),(1375,768),(1295,768),(1295,790),(1245,790),(1245,955),(1375,955),(1375,1075),(1325,1075),(1325,1118),(1230,1118),(1230,1035),(1190,1035),(1190,875),(1150,875),(1150,530),(1235,530)],level='open_space')
add('lobby_e','中央公共门厅东区','hall',[(1375,414),(1515,414),(1515,530),(1595,530),(1595,875),(1555,875),(1555,1035),(1515,1035),(1515,1075),(1420,1075),(1420,1118),(1375,1118),(1375,955),(1505,955),(1505,790),(1455,790),(1455,768),(1375,768),(1375,678),(1410,678),(1430,660),(1430,608),(1410,594),(1375,594)],level='open_space')
add('guide','导诊','service',[(1375,594),(1410,594),(1430,608),(1430,660),(1410,678),(1340,678),(1320,660),(1320,608),(1340,594)],level='semi_open_space')
add('central_core','中央扶梯、电梯交通核','vertical_core',[(1295,768),(1455,768),(1455,790),(1505,790),(1505,955),(1245,955),(1245,790),(1295,790)],level='core_block')
add('lobby_s_lift_w','南侧电梯交通核（西）','vertical_core',rect(1230,1076,1324,1118),level='core_block')
add('lobby_s_lift_e','南侧电梯交通核（东）','vertical_core',rect(1421,1076,1515,1118),level='core_block')
unknown('central_s',rect(1235,1122,1510,1510),'public_service',['室外休憩庭院','室内休憩区'],'中央下方大片留白设座椅，向建筑下边缘敞开；顶盖和室内外属性未能由本图确认。','中')
# C 上部妇儿门诊片区。
add('ob_n_core','楼梯、电梯交通核','vertical_core',rect(1595,450,1737,531),level='core_block')
add('pediatrics','儿科门诊','consultation',[(1738,450),(2050,450),(2050,530),(2090,530),(2090,450),(2150,450),(2195,465),(2170,530),(2195,530),(2195,570),(1595,570),(1595,532),(1738,532)],'ordinary_outpatient')
add('ped_n_lift','电梯交通核','vertical_core',rect(2051,450,2089,529),level='core_block')
add('gyn','妇科门诊','consultation',[(1595,571),(2095,571),(2095,637),(1895,637),(1895,735),(1595,735)],'ordinary_outpatient')
add('ped_infusion','儿科输液','treatment',rect(1896,638,2050,768),'ordinary_outpatient')
add('gyn_wc','卫生间','toilet',rect(1595,736,1685,865),'ordinary_outpatient')
unknown('gyn_s',rect(1686,736,1870,841),'ordinary_outpatient',['妇科检查及配套用房组','妇科门诊配套用房组'],'位于妇科南侧，有独立通道和若干小房；具体用途未标。','中')
add('adult_infusion','成人输液','treatment',[(1896,769),(2051,769),(2051,706),(2140,706),(2140,875),(1896,875)],'ordinary_outpatient')
unknown('infusion_s',rect(1896,876,2139,941),'ordinary_outpatient',['输液配套用房组','治疗及准备用房组'],'成人输液南侧的三个分隔单元；未见房名。','中')
unknown('central_e_blank',rect(2172,706,2290,813),'public_service',['中庭或采光井','未标用途房间'],'矩形空白、无家具及可辨门洞，四周是通道；室内外属性不明。','低')
# D 上部右侧急诊及住院入口片区。
add('er_n_core','楼梯、电梯交通核（含卫生间）','vertical_core',[(2262,504),(2400,552),(2360,660),(2215,632),(2215,591),(2240,591)],'emergency',level='core_block')
add('er_wc_core','卫生间及交通核','vertical_core',rect(2310,706,2480,845),'emergency',level='core_block')
add('er','急诊','consultation',[(2345,644),(2403,573),(2740,689),(2920,746),(2955,766),(2890,875),(2301,875),(2301,846),(2481,846),(2481,705),(2345,705)],'emergency')
add('inpatient_hall','住院门厅','hall',[(2955,766),(2980,790),(2990,825),(2988,860),(2970,887),(2930,870),(2910,883),(2890,875)],'inpatient_support',level='open_space')
add('inpatient_core','楼梯、电梯交通核','vertical_core',[(2930,871),(2970,889),(2945,931),(2875,903),(2890,876),(2910,885)],'inpatient_support',level='core_block')
add('resus','急救','resuscitation',[(2708,876),(2890,876),(2875,905),(2945,933),(2911,995),(2780,953),(2708,933)],'emergency')
add('duty120','120值班中心','staff_support',[(2844,985),(2910,1007),(2887,1061),(2820,1038)],'emergency',level='room')
unknown('er_duty_s',[(2817,1041),(2885,1064),(2836,1184),(2736,1149),(2754,1093),(2790,1105)],'emergency',['急诊及120配套用房组','值班及支持用房组'],'120值班中心下方连续小房组，未标各房用途。','中')
# E 中部左侧中西药房片区。
add('ph_wc_w','卫生间','toilet',rect(505,932,597,1030),level='functional_block')
add('tcm_pharm','中药房','pharmacy',rect(598,877,782,1180),'ordinary_outpatient')
add('western_pharm','西药房','pharmacy',rect(784,877,1053,1180),'ordinary_outpatient')
add('ph_core_e1','楼梯交通核','vertical_core',[(1055,877),(1188,877),(1188,1031),(1153,1031),(1153,925),(1055,925)],level='core_block')
add('ph_wc_e','卫生间','toilet',rect(1055,927,1152,1007))
add('ph_core_w','楼梯、电梯交通核','vertical_core',[(498,1080),(581,1080),(581,1128),(546,1128),(546,1180),(498,1180)],level='core_block')
add('ph_core_e2','楼梯、电梯交通核','vertical_core',rect(1055,1033,1153,1123),level='core_block')
unknown('ph_support_e',rect(1055,1125,1153,1180),'ordinary_outpatient',['药房配套用房组','工作人员支持用房组'],'位于西药房东侧交通核下方，与后场通道相邻。','低')
add('ph_back_corridor','药房后场通道','corridor',rect(545,1182,1153,1205),'ordinary_outpatient',level='open_space')
add('west_corridor','西翼外侧通道','corridor',rect(1155,1035,1229,1510),level='open_space')
# F 中部放射科；图例10对应的整组房间按功能块保存，内部不推断各设备名。
add('imaging','放射科','imaging',[(1722,865),(1870,865),(1870,944),(2140,944),(2140,877),(2208,877),(2208,1252),(2138,1252),(2138,1274),(1745,1274),(1745,1174),(1690,1174),(1690,1122),(1722,1122)],'medical_technology')
add('imaging_core_w','楼梯、电梯交通核（含卫生间）','vertical_core',rect(1595,877,1690,1177),'medical_technology',level='core_block')
# G 急诊留观及其南侧。
add('er_obs','急诊留观','observation',[(2310,910),(2470,910),(2470,877),(2607,877),(2607,1037),(2310,1037)],'emergency')
unknown('obs_w',rect(2268,950,2309,1036),'emergency',['留观配套用房组','处置用房组'],'留观西侧串联的小房，与留观区相邻；无房名。','低')
add('obs_lift','电梯交通核','vertical_core',rect(2215,877,2267,909),'emergency',level='core_block')
add('obs_s_core','楼梯、电梯交通核','vertical_core',rect(2308,1039,2421,1117),'emergency',level='core_block')
unknown('obs_s_support',rect(2268,1119,2420,1178),'emergency',['留观配套用房组','工作人员支持用房组'],'留观南侧楼梯旁房组，含小隔间；未标用途。','低')
unknown('east_blank',[(2454,1088),(2607,1088),(2660,1110),(2587,1226),(2454,1226)],'public_service',['中庭或采光井','未标用途房间'],'多边形留白、未见家具及房名，四周通道围绕；不据此确认露天。','低')
add('er_e_core','楼梯、电梯交通核','vertical_core',[(2753,957),(2821,982),(2790,1056),(2738,1038),(2719,1080),(2666,1061),(2688,1000),(2722,1012)],'emergency',level='core_block')
# H 下部左侧专家门诊。
unknown('expert_w_n',rect(506,1208,574,1318),'ordinary_outpatient',['专家门诊配套用房组','办公用房组'],'专家门诊西侧、三间小房成组，无标注文字。','低')
unknown('expert_w_s',rect(506,1333,595,1455),'ordinary_outpatient',['门诊配套用房','未标用途房间'],'西翼下部靠外墙大房，门向左侧通道，未标名称。','低')
unknown('expert_blank',rect(598,1208,781,1455),'ordinary_outpatient',['未标用途功能用房','室内休憩空间'],'大片白色矩形内有结构柱，外墙有开口符号；不具备判定为露天庭院的依据。','低')
add('expert','专家门诊','consultation',[(783,1208),(1053,1208),(1053,1244),(1153,1244),(1153,1384),(783,1384)],'ordinary_outpatient')
add('expert_core_n','楼梯交通核','vertical_core',rect(1055,1208,1153,1243),'ordinary_outpatient',level='core_block')
unknown('expert_s',rect(783,1386,1051,1455),'ordinary_outpatient',['专家门诊诊室组','专家门诊配套用房组'],'紧邻专家门诊南侧的连续小房，朝内部通道开门；无单独编号。','中')
add('expert_wc','卫生间','toilet',rect(1053,1386,1153,1455),'ordinary_outpatient')
add('expert_core_s','楼梯交通核','vertical_core',rect(1046,1457,1153,1510),'ordinary_outpatient',level='core_block')
# I 下部中央：两个无编号厚边界单元均保留未知，不外推治疗设备。
unknown('thick_w',rect(1689,1287,1841,1457),'medical_technology',['设备或结构单元','厚壁检查／治疗用房'],'外轮廓和中央隔构明显加粗，内部有折线；无设备或房名文字。','低')
unknown('thick_e',rect(1843,1287,2004,1457),'medical_technology',['设备或结构单元','厚壁检查／治疗用房'],'与左侧单元对称，厚边界和折线明显；用途未标。','低')
add('south_wc_w','卫生间','toilet',rect(1595,1318,1688,1417),'medical_technology')
add('south_core_w','楼梯交通核','vertical_core',rect(1595,1419,1688,1510),'medical_technology',level='core_block')
add('south_core_e','电梯交通核','vertical_core',rect(2006,1354,2049,1455),'medical_technology',level='core_block')
add('south_wc_e','卫生间','toilet',rect(2051,1306,2110,1455),'medical_technology')
unknown('south_support',rect(2138,1306,2187,1455),'medical_technology',['医技配套用房','工作人员支持用房'],'放射科南端、卫生间与楼梯之间的长条房间，未标名称。','低')
add('south_core_far_e','楼梯交通核','vertical_core',rect(2189,1359,2228,1455),'medical_technology',level='core_block')
# J 下部右侧发热、VIP、肠道门诊，依照图例原称归类，不合并普通门诊范围。
add('vip','VIP门诊','consultation',[(2234,1179),(2420,1179),(2420,1264),(2452,1264),(2452,1389),(2337,1389),(2337,1455),(2234,1455)],'vip_outpatient')
add('vip_core','楼梯、电梯交通核','vertical_core',[(2422,1353),(2454,1353),(2454,1421),(2483,1421),(2483,1455),(2339,1455),(2339,1390),(2422,1390)],'vip_outpatient',level='core_block')
add('intestinal','肠道门诊','consultation',[(2663,1111),(2837,1185),(2777,1345),(2624,1294),(2606,1321),(2566,1305)],'intestinal_outpatient')
add('fever','发热门诊','consultation',[(2492,1265),(2567,1265),(2567,1307),(2623,1323),(2775,1347),(2731,1455),(2492,1455)],'fever_outpatient')
# 明确公共连接通道，未以共墙补足任何人员通行关系。
add('east_spine','东部公共通道','corridor',[(2141,814),(2299,814),(2299,875),(2268,875),(2268,1179),(2421,1179),(2421,1263),(2449,1263),(2449,1228),(2587,1228),(2605,1194),(2660,1218),(2623,1294),(2605,1321),(2566,1305),(2566,1264),(2491,1264),(2491,1455),(2484,1455),(2484,1420),(2455,1420),(2455,1352),(2422,1352),(2422,1263),(2233,1263),(2233,1455),(2230,1455),(2230,1178),(2210,1178),(2210,910),(2141,910)],level='open_space')
add('rad_s_corridor','医技南侧通道','corridor',[(1595,1179),(1688,1179),(1688,1286),(2005,1286),(2005,1305),(2188,1305),(2188,1358),(2228,1358),(2228,1275),(2209,1275),(2209,1254),(2139,1254),(2139,1275),(1744,1275),(1744,1179),(1721,1179),(1721,1124),(1691,1124),(1691,1179)],'medical_technology',level='open_space')
# 几何核对，严格保留原图坐标。
D=dict(image=dict(file='37_广州中医药大学紫合梅州医院_原图.jpg',width=2484,height=3236),spaces=spaces,relations=relations)
# 从已辨认的开口、柜台和连续开放区域保守记录关系。
for a,b,t in [
 ('lobby_w','lobby_e','access'),('lobby_w','waiting_pharm','access'),('lobby_w','guide','access'),('lobby_e','guide','access'),
 ('lobby_w','central_core','access'),('lobby_e','central_core','access'),('lobby_w','lobby_s_lift_w','access'),('lobby_e','lobby_s_lift_e','access'),
 ('waiting_pharm','reg','service'),('reg','office','access'),('waiting_pharm','bank','access'),('waiting_pharm','flower','access'),('waiting_pharm','convenience','access'),
 ('waiting_pharm','nw_lift','access'),('waiting_pharm','nw_diagonal_stair','access'),('waiting_pharm','sw_diagonal_core','access'),
 ('lobby_e','pediatrics','access'),('lobby_e','gyn','access'),('lobby_e','gyn_wc','access'),('pediatrics','ob_n_core','access'),('pediatrics','ped_n_lift','access'),
 ('gyn','ped_infusion','access'),('ped_infusion','adult_infusion','access'),('adult_infusion','east_spine','access'),
 ('er','er_n_core','access'),('er','er_wc_core','access'),('er','east_spine','access'),('er','inpatient_hall','access'),('inpatient_hall','inpatient_core','access'),
 ('resus','er_obs','access'),('resus','er_e_core','access'),('er_obs','east_spine','access'),('east_spine','obs_lift','access'),('east_spine','obs_s_core','access'),
 ('tcm_pharm','ph_back_corridor','access'),('western_pharm','ph_back_corridor','access'),('ph_back_corridor','west_corridor','access'),
 ('west_corridor','lobby_w','access'),('west_corridor','expert','access'),('ph_back_corridor','expert','access'),('ph_back_corridor','expert_core_n','access'),('west_corridor','expert_core_s','access'),
 ('lobby_e','imaging','access'),('lobby_e','imaging_core_w','access'),('imaging','east_spine','access'),('imaging','rad_s_corridor','access'),
 ('east_spine','vip','access'),('east_spine','intestinal','access'),('east_spine','fever','access'),('vip','vip_core','access'),
 ('rad_s_corridor','south_wc_w','access'),('rad_s_corridor','south_core_w','access'),('rad_s_corridor','south_core_e','access'),('rad_s_corridor','south_wc_e','access'),('rad_s_corridor','south_core_far_e','access'),
 ('tcm_pharm','western_pharm','shared_wall'),('reg','office','shared_wall'),('shop1','shop2','shared_wall'),('shop2','shop3','shared_wall'),('ped_infusion','adult_infusion','shared_wall')]:rel(a,b,t)
entry('lobby_w','中央主入口',(1330,414),'main')
entry('waiting_pharm','西侧公共入口',(493,935),'public')
entry('resus','急救入口',(2926,966),'emergency')
entry('fever','发热门诊独立入口',(2694,1455),'fever')
entry('east_spine','东南侧公共入口',(2488,1450),'public')
entry('ph_back_corridor','西翼南侧后场入口',(666,1455),'staff')
# 后场入口处并非直接相连：移除，不经其他空间虚构通行。
relations[:]=[r for r in relations if r.get('name')!='西翼南侧后场入口']
# 只保存草稿事实；候选与依据仅存在临时核对材料。
(ROOT/'annotation.json').write_text(json.dumps(D,ensure_ascii=False,indent=2)+'\n')
(TMP/'review_meta.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
(TMP/'source.sha256').write_text(hashlib.sha256((ROOT/D['image']['file']).read_bytes()).hexdigest()+'\n')
print('spaces',len(spaces),'pending',sum(s['type']=='unknown' for s in spaces),'relations',len(relations))