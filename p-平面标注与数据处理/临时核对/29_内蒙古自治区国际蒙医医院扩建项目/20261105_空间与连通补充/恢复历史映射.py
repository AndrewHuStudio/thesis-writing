from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import Polygon,box,Point
from shapely.ops import unary_union
import json,hashlib,math
ROOT=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理/标注试样/29_内蒙古自治区国际蒙医医院扩建项目')
TMP=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理/临时核对/29_内蒙古自治区国际蒙医医院扩建项目/20261105_空间与连通补充')
records=[]; rel=[]; groups={}
def add(key,pts,name=None,typ=None,level='room',scope='unresolved_function',cand=None,basis=None,confidence='低'):
 p=box(*pts) if len(pts)==4 and isinstance(pts[0],(int,float)) else Polygon(pts)
 if not p.is_valid: raise ValueError(key)
 records.append(dict(key=key,p=p,name=name or '名称未确认',type=typ or 'unknown',level=level,scope=scope,cand=cand or ['未知用途'],basis=basis or '原图文字不清，不能据此确定功能。',confidence=confidence))
 return key
def known(key,pts,name,typ,level='room',scope='public_service'):return add(key,pts,name,typ,level,scope)
def unk(key,pts,cand=None,basis=None,confidence='低',level='room'):return add(key,pts,level=level,cand=cand,basis=basis,confidence=confidence)
def access(a,b):rel.append((a,b,'access'))
def space(key):return next(r for r in records if r['key']==key)
def circulation(key,outline,name,exclude=None,scope='public_service'):
 p=Polygon(outline) if not isinstance(outline,tuple) else box(*outline)
 if exclude is None:exclude=[r['p'] for r in records]
 else:exclude=[space(k)['p'] for k in exclude]
 p=p.difference(unary_union(exclude))
 geoms=list(p.geoms) if hasattr(p,'geoms') else [p]
 idx=0
 for q in sorted(geoms,key=lambda q:-q.area):
  if q.area<100: continue
  if q.interiors:
   # Polygon holes are partitioned by vertical strips; retain exact no-overlap geometry.
   xs=sorted(set([q.bounds[0],q.bounds[2]]+[v[0] for ring in q.interiors for v in ring.coords]))
   parts=[]
   for x1,x2 in zip(xs,xs[1:]):
    frag=q.intersection(box(x1,q.bounds[1]-1,x2,q.bounds[3]+1))
    for v in list(frag.geoms) if hasattr(frag,'geoms') else [frag]:
     if v.geom_type=='Polygon' and v.area>100:parts.append(v)
  else:parts=[q]
  for v in parts:
   idx+=1;k=key if idx==1 else f'{key}_{idx}'
   known(k,list(v.exterior.coords)[:-1],name if idx==1 else name+f'（分区{idx}）','hall' if '大厅' in name else 'corridor','open_space',scope)
 return [r['key'] for r in records if r['key']==key or r['key'].startswith(key+'_')]
# A 原图上端，两处无房名的扇形翼部：暂存功能块，不臆造其各小房名称。
unk('fan_upper',[(440,242),(505,181),(567,145),(670,116),(740,373),(638,431)],['诊疗用房组','办公用房组'],'连续小房围绕三角形内空布置；原图未能读出科室名。',level='functional_block')
# Above coordinates were specified directly in ORIGINAL image; convert below with special flag.
records[-1]['original']=True
unk('fan_right',[(800,104),(900,120),(1057,173),(918,399),(800,373)],['诊疗用房组','办公用房组'],'连续小房与走廊形成三角形翼部；房名不可辨。',level='functional_block');records[-1]['original']=True
# Convert these two original polygons to reading coordinates now.
for r in records:r['p']=Polygon([(y,2444-x) for x,y in r['p'].exterior.coords[:-1]])
# Three broad rooms in upper sector (reading top-west).
unk('sector1',[(246,1282),(299,1229),(366,1190),(423,1312),(355,1359)],['诊疗大厅','治疗用房'],'大开间内有柱点，外侧另设入口；房名不可辨。')
unk('sector2',[(366,1190),(455,1153),(500,1300),(423,1312)],['诊疗大厅','治疗用房'],'与相邻大开间分隔，原图字迹不可辨。')
unk('sector3',[(355,1359),(423,1312),(500,1300),(526,1406),(436,1467)],['候诊区','服务用房'],'扇形大空间有独立边界，名称仅能辨认出若干笔画。')
known('sector_stair',[(390,1182),(454,1154),(470,1200),(409,1225)],'楼梯交通核','vertical_core','core_block')
# B 原图上中部：西侧矩形主楼。
known('west_top_core',(730,1132,814,1195),'楼梯交通核','vertical_core','core_block')
unk('west_service1',(640,1133,680,1197),['服务用房'],'小房位于主通道边，房名不可辨。')
unk('west_service2',(629,1197,680,1327),['服务用房','辅助用房'],'狭长独立房间，未能读准名称。')
unk('west_tiny1',(586,1327,640,1360),['卫生间','辅助用房'],'两个相邻小房设门；文字不足以确定用途。')
unk('west_tiny2',(586,1360,640,1395),['卫生间','辅助用房'],'与相邻小房并列，名称不清。')
unk('west_r1',(731,1226,814,1288),['检查室','辅助用房'],'内有分隔线；图面名称缺失或不可辨。')
unk('west_r2',(814,1226,900,1288),['超声检查室','检查室'],'短标签疑似检查设备缩写，不能可靠读准。')
unk('west_ct',(900,1226,980,1288),['CT室'],'图面可见近似CT字样，仍需核实。','中')
unk('west_mid',(814,1288,980,1330),['检查工作区','阅片室'],'位于上排与下排检查房之间，名称模糊。')
unk('west_x1',(814,1330,895,1394),['X线检查室','检查室'],'标签形似X光，但原文字形不足以确认。','中')
unk('west_x2',(895,1330,980,1394),['X线检查室','检查室'],'与相邻房布局相近，标签字形待确认。','中')
unk('west_r3',(1005,1227,1066,1280),['辅助用房'],'小房有门，原名不清。')
unk('west_r4',(1005,1280,1066,1330),['辅助用房'],'小房有门，原名不清。')
unk('west_r5',(1005,1330,1066,1393),['检查室','辅助用房'],'房间较深，文字不可辨。')
unk('west_r6',(731,1461,813,1493),['服务用房'],'沿大厅边设置的小房，文字不可辨。')
unk('west_r7',(813,1461,897,1493),['服务用房'],'与前室相接，小房文字不可辨。')
unk('west_r8',(897,1461,980,1493),['服务用房'],'狭长小房，原名不清。')
known('west_bottom_stair',(980,1461,1067,1530),'楼梯交通核','vertical_core','core_block')
known('west_lift',(731,1531,905,1646),'电梯及楼梯交通核','vertical_core','core_block')
unk('west_r9',(980,1531,1067,1646),['公共服务用房','服务工作区'],'贴近交通核，名称有字但不可读。')
unk('west_r10',(731,1710,770,1774),['辅助用房'],'底边小房设门，原名不可辨。')
unk('west_r11',(770,1710,815,1774),['辅助用房'],'与相邻小房并列，原名不可辨。')
unk('west_south_hall',(815,1710,980,1774),['门诊门厅','公共服务区'],'外侧有双入口符号，厅名不可读。','中',level='functional_block')
# Shared open hall with holes decomposed into spatial zones manually to avoid invented walls.
known('west_hall_a',(586,1395,1067,1460),'公共大厅（上区）','hall','open_space')
known('west_hall_b',(586,1460,730,1774),'公共大厅（左区）','hall','open_space')
known('west_hall_c',(730,1647,1067,1709),'公共大厅（下区）','hall','open_space')
known('west_hall_d',(906,1531,979,1646),'公共大厅（交通核旁）','hall','open_space')
known('west_hall_e',(730,1494,979,1530),'公共大厅（交通核前）','hall','open_space')
known('west_hall_f',(641,1198,730,1394),'公共通道（西侧）','corridor','open_space')
known('west_hall_g',(680,1133,730,1197),'公共通道（北侧）','corridor','open_space')
known('west_corridor_top',(815,1196,1067,1225),'检查区通道（上侧）','corridor','open_space')
known('west_corridor_left',(731,1289,813,1394),'检查区通道（左侧）','corridor','open_space')
known('west_corridor_right',(981,1226,1004,1394),'检查区通道（右侧）','corridor','open_space')
# C 中部上方橙色片区：按原图从左到右将竖排变成编号顺序。
known('central_stair_top',(1098,1048,1183,1084),'楼梯交通核','vertical_core','core_block')
for i,(x1,x2) in enumerate(zip([1216,1266,1308,1352,1392],[1266,1308,1352,1392,1434]),1):
 unk(f'central_top{i}',(x1,997,x2,1047),['诊室','辅助用房'],'连续小房沿通道布置；两个字的标签无法可靠读准。')
known('central_entry',(1073,997,1183,1047),'门厅','hall','open_space')
for key,pts,cand,basis in [
 ('central_a',(1117,1085,1183,1153),['DR室','X线检查室'],'标签近似DR；设备用途仍待确认。'),
 ('central_b',(1117,1153,1183,1234),['CT室','检查室'],'标签似CT或汉字缩写，不能据此定名。'),
 ('central_c',(1117,1234,1183,1292),['DR室','检查室'],'与上方房间相近，名称模糊。'),
 ('central_d',(1216,1085,1266,1145),['控制室','辅助用房'],'紧邻大检查房，短标签不清。'),
 ('central_e',(1266,1085,1351,1160),['检查室'],'大房间有柱点，原名不清。'),
 ('central_f',(1351,1085,1403,1160),['控制室','辅助用房'],'窄房临通道，文字不可辨。'),
 ('central_g',(1216,1145,1266,1195),['检查辅助用房'],'小房名称较长，但文字像素不足。'),
 ('central_h',(1216,1195,1266,1235),['检查辅助用房'],'小房名称较长，具体字形不可读。'),
 ('central_i',(1266,1160,1351,1235),['检查室'],'大房间与上侧相似，标签不可辨。'),
 ('central_j',(1351,1160,1403,1235),['控制室','辅助用房'],'位于检查房右侧，原名不清。'),
 ('central_k',(1216,1250,1266,1328),['控制室','辅助用房'],'紧邻大检查房，名称模糊。'),
 ('central_l',(1266,1250,1351,1328),['CT室'],'可见CT形标签，仍需确认。'),
 ('central_m',(1351,1250,1403,1328),['控制室','辅助用房'],'检查房旁小房；名称模糊。'),
 ('central_n',(1098,1329,1183,1387),['登记区','服务用房'],'底边小房沿公共大厅设置，文字不清。'),
 ('central_o',(1183,1329,1266,1387),['检查室','辅助用房'],'底边独立房间，无法读准原名。'),
 ('central_p',(1266,1329,1403,1387),['候诊区','检查用房'],'较大独立房间，标签不可辨。')]:unk(key,pts,cand,basis)
known('central_stair_lower',(1098,1293,1183,1328),'楼梯交通核','vertical_core','core_block')
known('central_corridor_a',(1184,1048,1215,1328),'检查区通道','corridor','open_space')
known('central_corridor_b',(1216,1048,1434,1084),'检查区横向通道','corridor','open_space')
known('central_corridor_c',(1404,1085,1434,1387),'检查区侧通道','corridor','open_space')
known('central_corridor_d',(1216,1236,1403,1249),'检查区内部通道','corridor','open_space')
known('central_outer_a',(1073,1085,1097,1387),'公共通道（检查区外侧）','corridor','open_space')
known('central_hall',(1073,1388,1434,1475),'公共大厅（中段）','hall','open_space')
# D 同排左侧黄色片区。
for i,(x1,x2) in enumerate(zip([1073,1106,1148,1190,1232,1275],[1106,1148,1190,1232,1275,1318]),1):
 unk(f'yellow_top{i}',(x1,1589,x2,1647),['诊室','治疗室'],'黄色片区连续小房，原图均有短名称但无法辨读。')
known('yellow_core',(1319,1589,1398,1647),'楼梯交通核','vertical_core','core_block')
unk('yellow_middle',(1073,1648,1398,1708),['候诊区','治疗工作区'],'中间为连通开敞区域，名称不清。',level='functional_block')
for i,(x1,x2) in enumerate(zip([1073,1155,1237,1319],[1155,1237,1319,1398]),1):
 unk(f'yellow_bottom{i}',(x1,1709,x2,1774),['诊疗用房','治疗室'],'底边数个开间的墙体／柱网需核实，暂据清晰隔墙划区。')
known('yellow_lift',(1399,1476,1434,1578),'电梯交通核','vertical_core','core_block')
unk('yellow_aux1',(1435,1476,1483,1578),['值班室','辅助用房'],'小房临电梯与楼梯，原名不清。')
known('yellow_stair',(1484,1476,1517,1578),'楼梯交通核','vertical_core','core_block')
unk('yellow_work',(1435,1579,1517,1774),['服务工作区','治疗用房'],'内部沿一侧画有重复设备／柜台符号，名称不清。',level='functional_block')
unk('yellow_edge',(1518,1476,1567,1774),['服务区','治疗用房'],'竖向黄色带中有两行短标签，功能及内部隔断需核实。',level='functional_block')
# E 中部右侧橙色大开间（轴线不当作墙）。
known('orange_top_core',(1518,997,1602,1047),'楼梯交通核','vertical_core','core_block')
known('orange_bottom_core',(1435,1292,1518,1387),'楼梯及电梯交通核','vertical_core','core_block')
unk('orange_large',[(1435,997),(1517,997),(1517,1048),(1603,1048),(1603,1387),(1519,1387),(1519,1291),(1435,1291)],['药房','医疗服务大空间'],'橙色区域内大多为轴网线；有大字标签，但无法可靠辨认。',level='functional_block')
unk('orange_edge',(1604,997,1647,1387),['服务柜台区','工作区'],'沿大空间外侧的连续窄带，名称文字不清。',level='functional_block')
known('orange_side_hall',(1648,997,1733,1475),'公共大厅（连接段）','hall','open_space')
known('orange_low_hall',(1435,1388,1647,1475),'公共大厅（橙色片区下侧）','hall','open_space')
# F 中心连接大厅与绿色景观/中庭。
unk('hub_upper_green',[(1734,1048),(1853,1048),(1853,1078),(1764,1078),(1734,1227)],['景观绿化','中庭边绿化'],'绿色楔形带贴近开放空间；露天状态未定。',level='functional_block')
unk('hub_upper_void',[(1765,1079),(1853,1079),(1853,1227),(1735,1227)],['中庭','休息区'],'白色中空区域与绿色带相邻，是否室内可步入待确认。',level='functional_block')
unk('hub_lower_green',[(1735,1336),(1754,1336),(1754,1475),(1735,1475)],['绿化带'],'绿色狭长区域，范围可见但原名缺失。',level='functional_block')
unk('hub_lower_void',(1755,1336,1853,1475),['中庭','休息区'],'白色中空区域；不直接按露天中庭排除面积。',level='functional_block')
known('hub_top_hall',(1734,997,1900,1047),'公共大厅（北连接）','hall','open_space')
known('hub_east_hall',(1854,1048,1900,1475),'公共通道（中心东侧）','corridor','open_space')
known('hub_middle_hall',(1734,1228,1853,1335),'公共大厅（中心连接）','hall','open_space')
# Large central circle and ring: preserve unknown central green; arc corridor approximated manually.
center=(1780,1721);inner=Point(*center).buffer(143,resolution=32)
unk('round_center',list(inner.exterior.coords)[:-1],['景观庭院','室内中庭'],'圆形中心以绿色填充；图中标注不可读，不能确定是否露天。','中',level='functional_block')
# annulus split 8 sectors without holes, shape serves conceptual circulation.
for i in range(8):
 a1=i*math.pi/4;a2=(i+1)*math.pi/4
 pts=[(center[0]+r*math.cos(a),center[1]+r*math.sin(a)) for r,angles in [(196,[a1+j*(a2-a1)/16 for j in range(17)]),(143,[a2-j*(a2-a1)/16 for j in range(17)])] for a in angles]
 # restrict right side later to observed open footprint: whole circular ring visible.
 known(f'round_ring{i}',pts,f'环形公共通道（{i+1}区）','corridor','open_space')
# South semi-circular outer fringe: ambiguous steps/edge columns, do not infer enclosed rooms.
unk('round_fringe',[(1568,1775),(1605,1853),(1665,1914),(1740,1954),(1814,1968),(1891,1940),(1967,1872),(1935,1853),(1878,1902),(1805,1917),(1732,1909),(1664,1869),(1610,1805)],['入口外廊','台阶及门廊'],'弧形外缘有连续柱点／台阶线，不据此划成诊室。',level='functional_block')
# G 原图下部蓝色片区。
# upper strip
known('blue_core_top',(2174,1080,2268,1113),'楼梯交通核','vertical_core','core_block')
for key,pts,c in [('blue_top1',(1902,1080,1964,1137),['辅助用房']),('blue_top2',(1964,1080,2001,1137),['辅助用房']),('blue_top3',(2001,1080,2035,1137),['辅助用房']),('blue_top4',(2035,1080,2112,1113),['办公用房']),('blue_top5',(2112,1080,2173,1113),['办公用房']),('blue_top6',(2269,1080,2351,1113),['办公用房'])]:unk(key,pts,c,'蓝色片区顶部小房，字迹不清。')
for key,pts,c in [('blue_a',(1902,1166,1964,1228),['检查室','诊室']),('blue_b',(1964,1166,2000,1228),['辅助用房']),('blue_c',(2000,1166,2035,1228),['辅助用房']),('blue_d',(2060,1138,2112,1193),['诊室']),('blue_e',(2112,1138,2154,1193),['诊室']),('blue_f',(2154,1138,2195,1193),['诊室']),('blue_g',(2195,1138,2237,1193),['诊室']),('blue_h',(2237,1138,2270,1193),['诊室']),('blue_i',(2271,1138,2351,1174),['辅助用房']),('blue_j',(2271,1174,2351,1228),['检查室','诊室'])]:unk(key,pts,c,'蓝色片区独立小房沿通道布置；房名无法读准。')
known('blue_corridor_upper',(2036,1114,2351,1137),'蓝色片区上通道','corridor','open_space')
known('blue_corridor_a',(2036,1138,2059,1228),'蓝色片区连接通道','corridor','open_space')
known('blue_corridor_b',(2060,1194,2270,1228),'蓝色片区内部通道','corridor','open_space')
known('blue_core_mid',(1902,1229,2035,1261),'楼梯交通核','vertical_core','core_block')
unk('blue_aux_mid',(1933,1262,2035,1330),['辅助用房组'],'多个狭小房间的分隔能见，原名和功能分组待确认。',level='functional_block')
unk('blue_entry1',(2036,1230,2111,1330),['门厅','公共服务区'],'外侧有入口，区域名称不清。',level='functional_block')
unk('blue_entry2',(2112,1230,2193,1330),['服务区','门厅'],'靠入口的相邻空间，名称不清。',level='functional_block')
unk('blue_entry3',(2194,1230,2351,1330),['公共大厅','服务区'],'较大留白区域，内部柱网不作隔墙。',level='functional_block')
# middle three rooms
for key,pts in [('blue_k',(1902,1331,1964,1408)),('blue_l',(1964,1331,2035,1408)),('blue_m',(2036,1331,2112,1408))]:unk(key,pts,['诊室','治疗室'],'房间有对外开口，短标签不清。')
known('blue_core_middle',(2144,1331,2270,1367),'楼梯交通核','vertical_core','core_block')
for key,pts in [('blue_n',(2144,1368,2194,1408)),('blue_o',(2194,1368,2270,1408)),('blue_p',(2271,1331,2351,1394)),('blue_q',(2292,1395,2351,1449)),('blue_r',(2292,1450,2351,1480))]:unk(key,pts,['诊室','辅助用房'],'独立小房有门，原图名称不可辨。')
known('blue_mid_hall',(1902,1409,2112,1441),'蓝色片区公共通道','corridor','open_space')
known('blue_mid_conn',(2113,1331,2143,1441),'蓝色片区中通道','corridor','open_space')
known('blue_mid_conn2',(2144,1409,2270,1441),'蓝色片区横通道','corridor','open_space')
known('blue_right_corr',(2271,1395,2291,1819),'蓝色片区右通道','corridor','open_space')
known('blue_toilet1',(1964,1442,2035,1476),'卫生间','toilet')
known('blue_toilet2',(1964,1537,2035,1575),'卫生间','toilet')
unk('blue_wait',(1964,1477,2035,1536),['候诊区','公共服务区'],'两组卫生设施之间的开放区，原名不清。',level='functional_block')
unk('blue_s',(2036,1442,2112,1550),['治疗室','服务工作区'],'房间较大并贴近卫生间，标签模糊。')
for key,pts in [('blue_t',(2036,1551,2073,1575)),('blue_u',(2073,1551,2112,1575)),('blue_v',(2036,1576,2112,1632)),('blue_w',(2036,1633,2112,1675)),('blue_x',(2036,1676,2112,1721))]:unk(key,pts,['诊疗用房','辅助用房'],'蓝色片区沿西侧一列房间，字迹不可辨。')
known('blue_core_low_left',(2036,1722,2112,1755),'楼梯交通核','vertical_core','core_block')
for key,pts,c in [('blue_y',(2144,1477,2194,1543),['诊室']),('blue_z',(2144,1544,2194,1616),['诊室']),('blue_aa',(2195,1442,2270,1575),['治疗室','检查室']),('blue_ab',(2144,1633,2194,1721),['诊室','治疗室']),('blue_ac',(2144,1722,2194,1755),['辅助用房']),('blue_ad',(2195,1633,2270,1755),['治疗室','检查室']),('blue_ae',(2292,1481,2351,1540),['辅助用房']),('blue_af',(2292,1541,2351,1580),['辅助用房']),('blue_ag',(2292,1581,2351,1632),['辅助用房']),('blue_ah',(2292,1633,2351,1819),['诊疗用房组'])]:unk(key,pts,c,'蓝色片区内部房间，名称不能可靠辨读。',level='functional_block' if key=='blue_ah' else 'room')
known('blue_core_low_mid',(2195,1576,2270,1616),'楼梯交通核','vertical_core','core_block')
known('blue_internal_corr',(2113,1442,2143,1755),'蓝色片区纵向通道','corridor','open_space')
known('blue_internal_corr2',(2144,1617,2270,1632),'蓝色片区内横通道','corridor','open_space')
known('blue_core_bottom',(2271,1820,2351,1853),'楼梯交通核','vertical_core','core_block')
unk('blue_south1',(2271,1854,2351,1913),['辅助用房'],'最下端房间有门，原名不可辨。')
unk('blue_south2',(2271,1914,2351,1958),['辅助用房'],'最下端房间有门，原名不可辨。')
unk('blue_southhall',(2113,1820,2270,1958),['公共门厅','诊疗服务区'],'南边有入口与较大厅空间，标签多行但不可读。',level='functional_block')
unk('blue_triangle',[(2036,1874),(2112,1934),(2112,1958),(2036,1907)],['辅助用房'],'临环形外缘的斜角小房，名称不清。')
known('blue_low_hall',(2036,1756,2270,1819),'蓝色片区下大厅','hall','open_space')
# H 原图右侧独立橙色片区上端（阅读图东北）。
known('ne_hall',(1750,660,2024,759),'公共大厅（独立橙色片区）','hall','open_space')
unk('ne_green',[(1750,568),(2004,568),(2004,577),(1773,590),(1750,659)],['绿化带'],'绿色区域贴建筑边缘，名称及内外属性不明。',level='functional_block')
unk('ne_void',[(1773,591),(2004,578),(2004,659),(1751,659)],['中庭','休息区'],'白色区域与绿带相邻，不能确认露天。',level='functional_block')
known('ne_core1',(1670,765,1750,841),'楼梯交通核','vertical_core','core_block')
unk('ne_equipment1',(1582,765,1669,841),['设备用房','治疗用房'],'可见平行长条设备符号，房名不清。')
unk('ne_equipment2',(1582,842,1669,905),['设备用房','治疗用房'],'与相邻房间同类长条图例，不能据此确定用途。')
unk('ne_equipment3',(1582,906,1669,984),['设备用房','治疗用房'],'与相邻房间同类长条图例，不能据此确定用途。')
unk('ne_equipment4',(1670,842,1750,984),['设备用房','治疗用房'],'可见长条设备，部分区域有短名称不可辨。')
known('ne_link',(1751,760,1834,984),'公共通道（橙色片区）','corridor','open_space')
unk('ne_aux1',(1835,765,1918,807),['辅助用房'],'上排有门的小房，房名不清。')
unk('ne_aux2',(1919,765,1961,807),['辅助用房'],'上排小房，房名不清。')
unk('ne_aux3',(1962,765,2006,807),['辅助用房'],'上排小房，房名不清。')
known('ne_work_corr',(1835,808,2006,840),'橙色片区内部通道','corridor','open_space')
unk('ne_seating',[(1835,841),(2006,841),(2006,855),(2151,855),(2151,841),(2210,841),(2210,984),(1835,984)],['候诊大厅','餐厅'],'大量成组桌椅／座椅图例；大字原名不可读，不能确定为诊疗或后勤。',level='functional_block')
known('ne_core2',(2026,730,2151,855),'电梯及楼梯交通核','vertical_core','core_block')
known('ne_core3',(2026,501,2151,674),'电梯及楼梯交通核','vertical_core','core_block')
unk('ne_aux4',(2026,675,2151,729),['辅助用房组'],'连接交通核的狭长房间，名称不清。',level='functional_block')
# Main lobby footprint with irregular boundary, no room subdivisions invented from column grid.
known('ne_big_hall',[(2152,567),(2391,567),(2391,658),(2262,840),(2152,840)],'公共大厅（东侧入口）','hall','open_space')
known('ne_big_hall_link',(2152,527,2603,566),'公共大厅（上连接）','hall','open_space')
known('ne_big_hall_link2',(2007,675,2025,840),'公共通道（交通核侧）','corridor','open_space')
known('ne_entry',(2005,425,2091,489),'门厅','hall','open_space')
unk('ne_top_tiny',(2005,351,2091,394),['服务用房'],'外侧短名称不可辨。')
unk('ne_top_large',(2092,351,2345,489),['诊疗用房','服务用房'],'大空间内部以柱网为主，非明确隔墙；原名不清。',level='functional_block')
unk('ne_top1',(2346,351,2388,425),['辅助用房'],'小房有门，名称不清。')
unk('ne_top2',(2389,351,2430,425),['辅助用房'],'小房有门，名称不清。')
known('ne_top_core',(2431,351,2516,450),'楼梯交通核','vertical_core','core_block')
unk('ne_top3',(2517,351,2603,425),['辅助用房'],'小房有门，多字标签不可读。')
known('ne_top_corr',(2346,451,2603,489),'独立片区通道','corridor','open_space')
unk('ne_band',(2177,490,2603,526),['服务工作区','服务柜台区'],'连续橙色窄带有名称但无法可靠读准。',level='functional_block')
# Repair only explicitly identified boundary conflicts; do not infer names or paths.
for target,cutters in [('sector2',['sector_stair']),('west_hall_f',['west_service2']),('round_fringe',[f'round_ring{i}' for i in range(8)]),('ne_hall',['ne_big_hall_link2'])]:
 q=space(target)['p'].difference(unary_union([space(k)['p'] for k in cutters]))
 if q.geom_type!='Polygon' or q.interiors: raise ValueError((target,q.geom_type))
 space(target)['p']=q
# Two curved service islands; names remain unknown.
unk('west_island1',[(423,1584),(450,1598),(479,1624),(494,1651),(489,1665),(461,1650),(438,1628),(420,1618)],['服务柜台区','导诊台'],'弧形独立服务岛有文字，字形不能可靠辨认。',level='functional_block')
unk('west_island2',[(424,1536),(449,1499),(485,1464),(515,1492),(494,1525),(471,1554)],['服务柜台区','导诊台'],'弧形服务岛临主大厅，文字不可辨。',level='functional_block')
# West connection hall, conservatively bounded around the visible central open zone.
# Holes are opened to edges by narrow separators so the core schema can represent simple polygons.
left_hall=[(371,1645),(371,1698),(434,1700),(457,1736),(481,1763),(529,1801),(578,1820),(585,1775),(585,1396),(585,1133),(560,1136),(560,1396),(526,1407),(436,1468),(429,1480),(405,1526),(371,1510),(350,1568),(350,1645)]
# split at island edges using explicit simple zones, leaving islands separately identified.
base=Polygon(left_hall).difference(unary_union([r['p'] for r in records]))
from shapely.ops import split
from shapely.geometry import LineString
for r in [space('west_island1'),space('west_island2')]:
 base=base.difference(r['p'])
parts=[base]
for y in [1499,1536,1584,1665]:
 nxt=[]
 for part in parts:
  for piece in split(part,LineString([(300,y),(600,y)])).geoms:
   if piece.geom_type=='Polygon' and piece.area>100:nxt.append(piece)
 parts=nxt
for n,q in enumerate(parts,1):
 if q.interiors: continue
 known(f'west_connect{n}',list(q.exterior.coords)[:-1],f'扇形翼部连接大厅（{n}区）','hall','open_space')
# Assign stable S IDs in original-image adjacent bands, original y increases with reading x.
# Bands keep nearby rooms together; within each band order original top-to-bottom, same row left-to-right.
for r in records:
 r['original_p']=Polygon([(2444-v,u) for u,v in r['p'].exterior.coords[:-1]])
def ordering(r):
 p=r['original_p'];cx,cy=p.centroid.coords[0]
 # adjacent original horizontal bands, then neighboring x clusters inside broad bands
 if cy<570: band=0
 elif cy<1072:band=1
 elif cy<1435:band=2
 elif cy<1734:band=3
 elif cy<1901:band=4
 elif cx<1458:band=5 # lower left blue
 else:band=6       # lower right orange
 return (band,round(p.bounds[1]/35),p.centroid.x,p.bounds[1])
records.sort(key=ordering)
for i,r in enumerate(records,1):r['id']=f'S{i:03d}'
lookup={r['key']:r for r in records}
# Explicit, visually evident open-zone continuities; narrow drawing gaps/doors added only where visible.
for a,b in [('west_hall_a','west_hall_b'),('west_hall_b','west_hall_c'),('west_hall_c','west_hall_d'),('west_hall_d','west_hall_e'),('west_hall_e','west_hall_b'),('west_hall_a','west_hall_f'),('west_hall_f','west_hall_g'),('west_hall_g','west_top_core'),('west_corridor_top','west_corridor_right'),('west_corridor_top','west_r1'),('west_corridor_top','west_r2'),('west_corridor_top','west_ct'),('west_corridor_right','west_mid'),('west_corridor_right','west_r5'),('west_hall_a','west_x1'),('west_hall_a','west_x2'),('west_hall_a','west_r6'),('west_hall_a','west_r7'),('west_hall_a','west_r8'),('west_hall_e','west_bottom_stair'),('west_hall_b','west_lift'),('west_hall_c','west_r10'),('west_hall_c','west_r11'),('central_entry','central_corridor_a'),('central_corridor_a','central_corridor_b'),('central_corridor_b','central_corridor_c'),('central_corridor_c','central_corridor_d'),('central_corridor_c','central_hall'),('central_outer_a','central_hall'),('central_hall','orange_low_hall'),('orange_low_hall','orange_side_hall'),('orange_side_hall','hub_top_hall'),('hub_top_hall','hub_east_hall'),('hub_east_hall','hub_middle_hall'),('hub_middle_hall','orange_side_hall'),('blue_corridor_upper','blue_corridor_a'),('blue_corridor_a','blue_corridor_b'),('blue_mid_hall','blue_mid_conn'),('blue_mid_conn','blue_mid_conn2'),('blue_mid_conn2','blue_right_corr'),('blue_mid_hall','blue_internal_corr'),('blue_internal_corr','blue_internal_corr2'),('blue_internal_corr','blue_low_hall'),('blue_right_corr','blue_low_hall'),('blue_low_hall','blue_core_bottom'),('ne_hall','ne_link'),('ne_link','ne_work_corr'),('ne_big_hall','ne_big_hall_link'),('ne_big_hall','ne_core2'),('ne_big_hall','ne_core3'),('ne_big_hall','ne_seating'),('ne_entry','ne_top_large')]:access(a,b)
for i in range(8):access(f'round_ring{i}',f'round_ring{(i+1)%8}')
for i in range(1,6):access(f'central_top{i}','central_corridor_b')
for k in ['central_a','central_b','central_c','central_d','central_g','central_h','central_k','central_stair_lower']:access(k,'central_corridor_a')

current=json.loads((ROOT/'annotation.json').read_text())
current_by={s['id']:s for s in current['spaces']}
serial=[]
for r in records:
 s=max(current['spaces'],key=lambda s: Polygon(s['polygon_px']).intersection(r['original_p']).area / Polygon(s['polygon_px']).union(r['original_p']).area)
 overlap=Polygon(s['polygon_px']).intersection(r['original_p']).area / Polygon(s['polygon_px']).union(r['original_p']).area
 assert overlap>0.999,(r['key'],s['id'],overlap)
 r['id']=s['id']
 assert s['type']==r['type'],(r['key'],s['id'])
 serial.append({k:v for k,v in r.items() if k not in ['p','original_p']}|{'polygon_px':s['polygon_px'],'reading_polygon':[(y,2444-x) for x,y in s['polygon_px']]})
(TMP/'review-data.json').write_text(json.dumps(serial,ensure_ascii=False,indent=2)+'\n')
Image.open(ROOT/current['image']['file']).transpose(Image.Transpose.ROTATE_90).save(TMP/'reading.png')
print('Recovered metadata',len(serial))
