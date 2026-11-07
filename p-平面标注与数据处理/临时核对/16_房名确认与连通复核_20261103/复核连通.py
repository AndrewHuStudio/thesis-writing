"""First-floor connectivity, manually read from this plan and six supplied photos."""
from pathlib import Path
from collections import Counter
import copy,json,sys
OUT=Path(__file__).resolve().parent
BASE=OUT.parents[1]
sys.path.insert(0,str(BASE/'临时核对/09-10_连通复核_20261102'))
from 连通工具 import annotation,fit_labels
path=OUT/'待核验成果/annotation.json'
a=json.loads(path.read_text())
# Always restart this review from the name-only snapshot.
snapshot=OUT/'名称同步后.json'
if not snapshot.exists():snapshot.write_text(json.dumps(a,ensure_ascii=False,indent=2)+'\n')
a=json.loads(snapshot.read_text())
spaces={s['id']:s for s in a['spaces']}
notes=[];concepts=[];removed=[]
def sid(i):return f'S{i:03d}'

from shapely.geometry import Polygon,box
from shapely.ops import unary_union
def setpoly(n,poly):
 assert poly.geom_type=='Polygon' and not poly.interiors,(n,poly.geom_type)
 spaces[sid(n)]['polygon_px']=[list(p) for p in list(poly.exterior.coords)[:-1]]
# Restore the visible vertical medical-street gap east of the service island.
new=dict(id='S211',name='医疗主街通道连接段',type='corridor',level='open_space',scope='public_service',polygon_px=[[1875,635],[1918,635],[1918,871],[1875,871]],area_ratio=0)
a['spaces'].append(new);spaces['S211']=new
# The pharmacy staff passage continues south beside the toilets and counters.
for n in [27,35,37]:
 pts=spaces[sid(n)]['polygon_px']
 spaces[sid(n)]['polygon_px']=[[1015 if x==1038 and y>=642 else x,y] for x,y in pts]
setpoly(36,box(1055,677,1073,737))
setpoly(40,box(1073,737,1252,774))
setpoly(30,unary_union([Polygon(spaces[sid(30)]['polygon_px']),box(1015,642,1055,774),box(1055,737,1073,774)]))
# Include the dedicated lift front hall down to its actual south door.
extension=box(1874,1145,1925,1205)
setpoly(184,unary_union([Polygon(spaces[sid(184)]['polygon_px']),extension]))
setpoly(174,Polygon(spaces[sid(174)]['polygon_px']).difference(extension))

def find(x,y,kind='access'):
 return next((r for r in a['relations'] if r['type']==kind and {r['source'],r['target']}=={sid(x),sid(y)}),None)
def drop(x,y,why):
 r=find(x,y)
 if r:a['relations'].remove(r);removed.append(dict(relation=r,reason=why))
def edge(x,y,p=None,kind='door',why=None,relation='access'):
 assert sid(x) in spaces and sid(y) in spaces and x!=y
 r=find(x,y,relation)
 if r is None:
  num=max([int(r['id'][1:]) for r in a['relations'] if r['id'].startswith('R')]+[0])+1
  r=dict(id=f'R{num:03d}',source=sid(x),target=sid(y),type=relation);a['relations'].append(r)
 if p is not None:
  assert relation=='access'
  num=sum(len(r.get('openings',[])) for r in a['relations'])+1
  r.setdefault('openings',[]).append(dict(id=f'P{num:03d}',kind=kind,position_px=p))
 else:
  concepts.append(dict(source=sid(x),target=sid(y),reason=why or '图面连续或功能块整体接口；不虚构门位'))
 return r
# Existing relations were reviewed individually. Two crossed intervening rooms/walls.
drop(72,61,'VIP大厅与S061之间隔着S058交通核，改经S058，不跨越交通核直连。')
drop(197,206,'东南交通核仅南侧对外开口清楚，西侧室内接口列K02，不沿用未证实旧边。')
drop(196,197,'EICU东侧实墙未见人员开口；改记北侧S174门和抢救区S195门。')
# Infection clinic: identifiable room doors and the two separate entrance halls.
for x,y,p in [(1,3,[338,620]),(1,4,[357,620]),(1,5,[401,620]),
 (1,8,[523,620]),(1,2,[575,624]),(2,9,[583,640]),(9,12,[610,694]),
 (3,12,[337,676]),(4,12,[380,676]),(6,12,[459,676]),(8,12,[529,676]),
 (1,12,[299,675]),(11,12,[300,690]),(11,20,[286,774]),
 (13,12,[307,698]),(14,12,[363,698]),(15,12,[379,698]),(15,20,[376,748]),
 (16,20,[447,748]),(17,12,[457,698]),(19,12,[537,721]),(19,20,[537,751]),
 (21,20,[354,770]),(22,20,[434,770]),(23,20,[477,770]),(25,20,[532,770]),
 (26,20,[341,787]),(20,82,[494,866])]:edge(x,y,p)
edge(10,11,why='图示电梯朝向挂号收费侧，交通核作为整体节点接该侧接口。')
edge(7,8,why='卫生间入口位于观察室侧；交通和附属小间按概念接口处理。')
edge(18,20,why='卫生间面向下侧肠道门厅；内部小间门位不细究。')
edge(24,20,why='卫生间面向肠道门厅，不因上下叠置连至发热门厅。')
# The two corridor polygons meet along the open far-east end, no wall at this split.
edge(12,20,why='两段通道在东端明确连续，分片线不是隔墙。')
# Pharmacy staff doors; service counters do not become patient through-routes.
for x,y,p in [(27,28,[824,622]),(27,29,[842,622]),(27,33,[730,636]),
 (27,32,[980,642]),(27,30,[1015,654]),(32,30,[1038,631]),
 (34,30,[1073,658]),(34,30,[1166,618]),(27,37,[936,721]),(30,36,[1055,701])]:edge(x,y,p)
edge(27,35,why='更衣直接附属于西药房工作区，内部小门位置不细究。')
edge(30,41,[1048,774],'open_passage')
edge(41,82,[927,866],'open_passage')
edge(39,41,relation='service',why='西药取药界面对等候区，柜台不当作人员通道。')
edge(40,41,relation='service',why='中药取药界面对等候区，柜台不当作人员通道。')
edge(31,82,[1354,817])
edge(211,82,[1895,635],'open_passage')
edge(211,82,[1895,871],'open_passage')
# North-side outpatient service island.
for x,y,p in [(42,82,[1455,675]),(47,82,[1455,782]),(47,48,[1512,860]),
 (44,48,[1664,751]),(45,211,[1875,690]),(46,211,[1875,724]),
 (50,82,[1639,871]),(51,82,[1717,871]),
 (52,82,[1810,871])]:edge(x,y,p)
edge(43,48,why='楼梯电梯前的交通核入口朝向本岛通道；不再拆分交通核内部路径。')
edge(48,82,[1535,871],'open_passage')
edge(49,82,[1585,871])
edge(43,82,[1524,635])
edge(44,82,[1713,635])
edge(53,82,why='东南交通核的整体对外接口朝医疗主街，内部小门不细究。')
# Inpatient preparation and VIP halls, keeping the central elevator group in path.
for x,y,p in [(54,55,[1980,674]),(55,60,[1992,731]),(56,60,[2140,731]),
 (60,57,[2188,750]),(58,61,[2393,731]),(57,61,[2351,750]),
 (72,58,[2385,635]),(72,82,[2352,582]),(60,211,[1918,748]),
 (63,62,[1980,806]),(63,70,[1980,825]),
 (64,60,[2106,769]),(65,64,[2117,794]),
 (57,82,[2270,871]),(67,66,[2409,816]),
 (67,71,[2409,842]),(67,80,[2432,871]),(68,61,[2470,769]),
 (68,80,[2515,871]),(73,74,[2564,674]),(78,74,[2564,694]),
 (74,80,[2867,731]),(75,74,[2878,670]),(77,80,[3093,731]),
 (80,82,[2352,910])]:edge(x,y,p)
edge(55,59,[1980,690])
edge(63,60,[2024,769],'open_passage')
edge(65,69,why='X光控制小间与X光工作区相接；图面门位不够清楚，本轮不定位。')
edge(61,80,why='S061东端与住院大厅连续，无独立隔墙。')
edge(76,80,why='卫生间入口朝向住院大厅北侧通道。')
edge(79,80,why='机房入口朝住院大厅北侧通道；附属小间不追问内部开门。')
edge(81,80,why='消防安保中心西侧朝向住院大厅的独立入口，位置缩印不清，仅记概念接口。')
# Medical street to outpatient/ED main circulation.
edge(82,112,why='医疗主街与门诊大厅北侧完全开放。')
edge(112,116,why='同一门诊大厅被数据分为上下片，原图无分隔墙。')
edge(82,84,[285,954],'open_passage')
edge(82,117,[1085,954])
edge(112,117,[1038,995])
edge(82,118,[1268,954])
edge(116,122,[1038,1265])
edge(116,132,[1038,1439])
edge(82,141,why='急诊观察区东侧纵向大厅直接接医疗主街，无隔墙。')
edge(82,141,[1807,954])
edge(82,174,[2312,954])
# Office island, with internal corridor and the self-registration circulation.
for x,y,p in [(83,82,[228,954]),(87,84,[266,1018]),(85,84,[304,980]),
 (84,89,[304,1070]),(90,84,[266,1135]),
 (91,84,[304,1135]),(95,84,[266,1182]),(96,92,[371,1158]),
 (97,84,[304,1180]),(98,84,[266,1200]),(99,84,[304,1233]),
 (100,84,[266,1278]),(101,84,[304,1292]),(102,84,[266,1308]),
 (103,84,[266,1390]),(104,92,[371,1374]),(105,92,[371,1400]),
 (106,84,[266,1467]),(107,84,[304,1456]),(109,84,[304,1507]),
 (110,93,[410,1489]),(111,84,[266,1487]),(92,93,[410,1108]),
 (92,93,[410,1410])]:edge(x,y,p)
edge(84,88,why='安全通道与办公纵向通道连续。')
edge(89,92,why='交通核整体与南侧安全通道存在可通行接口，内部路线不细分。')
edge(86,82,[504,954],'open_passage')
edge(93,116,[518,1203],'open_passage')
edge(93,116,[518,1400],'open_passage')
edge(94,93,[510,1134])
edge(108,93,why='小机房位于自助挂号区侧；仅记整体接口，不追问小门细节。')
# Pediatric: north treatment room, internal service counter, consultation rows.
for x,y,p in [(118,120,[1205,1080]),(118,121,[1205,1109]),
 (118,122,[1271,1145]),(119,122,[1062,1145]),(123,122,[1134,1210]),
 (124,118,[1246,1145]),(126,122,[1287,1165]),
 (128,122,[1145,1349]),(129,122,[1254,1370]),(130,122,[1293,1362]),
 (131,132,[1145,1374]),(133,132,[1254,1404]),(134,132,[1293,1403]),
 (135,132,[1145,1392]),(136,132,[1254,1461]),(137,132,[1293,1462]),
 (138,132,[1293,1491]),(139,132,[1254,1506])]:edge(x,y,p)
edge(117,119,why='电梯前室与其南侧交通核为同一核心的前厅和电梯组。')
edge(122,132,why='儿科连续候诊区的人工分片线，不是门或隔墙。')
edge(115,116,why='导医台开放侧可进入工作区，仅记开放服务节点接口。')
edge(127,122,why='分诊台为开放工作区，图示侧向可进入，无独立小门。')
edge(124,122,relation='service',why='挂号收费南侧窗口服务儿科候诊区，不当作穿行入口。')
edge(123,122,relation='service',why='药房窗口朝向儿科候诊区；服务窗口与人员门分开记录。')
# ED observation and clinical rooms.
for x,y,p in [(140,141,[1771,1078]),(144,141,[1549,1205]),
 (143,148,[1435,1145]),(148,141,[1434,1214]),
 (149,141,[1430,1238]),(150,141,[1551,1238]),(151,141,[1570,1238]),
 (152,141,[1714,1238]),(153,141,[1781,1238]),(154,159,[1395,1334]),
 (155,159,[1460,1320]),(156,141,[1499,1324]),(157,159,[1622,1322]),
 (158,159,[1665,1321]),(160,159,[1499,1346]),(161,159,[1622,1347]),
 (162,159,[1665,1372]),(166,159,[1499,1394]),(167,159,[1622,1394]),
 (168,159,[1665,1395]),(171,159,[1460,1464]),
 (153,194,[1875,1310])]:edge(x,y,p)
edge(141,159,why='急诊连续大厅的上下分片，三条诊室间通道连续相接。')
edge(153,164,why='复苏室南侧未见完整横墙，短通道是该入口前厅的连续分片。')
edge(159,194,why='急诊大厅与急救大厅南侧开放连续，图上无完整分隔墙。')
edge(145,144,why='护士站朝留观区开放，按开放工作节点记录。')
edge(146,144,[1625,1145])
edge(146,140,[1620,1085])
edge(147,144,why='卫生间入口朝留观区，内部隔间不再细分。')
edge(142,143,[1407,1100])
edge(165,159,why='卫生间入口朝急诊大厅；内部隔间不细分。')
edge(163,164,why='处置室面向东侧短通道，原图门扇缩印不清，仅记概念接口。')
edge(169,164,why='化验房门朝上方短通道，保留对应接口。')
edge(170,164,why='检验房门朝上方短通道，保留对应接口。')
# Staff corridor, dedicated surgery lift and resuscitation/EICU.
for x,y,p in [(173,141,[1835,970]),(174,141,[1835,1030]),
 (177,174,[2170,1018]),
 (178,174,[2284,1018]),(179,141,[1835,1081]),(183,141,[1835,1100]),
 (184,174,[1895,1205]),(186,174,[1937,1205]),
 (187,174,[2018,1205]),(188,174,[2048,1205]),(189,174,[2130,1205]),
 (190,174,[2150,1205]),(191,174,[2230,1205]),(192,174,[2255,1205]),
 (193,141,[1835,1187]),(174,194,[1904,1238]),(174,195,[2080,1238]),
 (174,196,[2218,1238]),(194,195,[1925,1320]),(195,196,[2190,1320]),
 (198,197,[2352,1276]),(199,197,[2352,1297]),(199,197,[2352,1373]),
 (207,196,[2298,1438]),(208,196,[2298,1507]),
 (201,200,[1945,1381]),(202,195,[1994,1381]),(203,194,[2018,1427]),
 (204,194,[2104,1427]),(205,196,[2190,1393]),(209,194,[2133,1479])]:edge(x,y,p)
edge(180,174,why='北侧可见电梯前的整体交通核与医护通道相接；内部路线不细分。')
edge(180,184,why='手术专用电梯前室直接接本交通核内专用电梯，不强制分解核心。')
# S185 scope is a remaining question; no route through confirmed exterior lightwell.
edge(175,174,why='整组卫生间向医护通道开口；不把组内隔间门当作功能块边界门。')
edge(176,174,why='整组卫生间向医护通道开口；不把组内隔间门当作功能块边界门。')
edge(174,197,why='医护办公通道在东端转向EICU东侧通道，图面连续。')
edge(200,195,why='护士台为抢救区开放工作接口，缺口不画成实体小门。')
edge(210,194,why='VIP室通过其北侧前厅接急救大厅，内部卫生间不细分。')
# Independent exterior interfaces, never joined through a shared null node.
def entrance(num,target,name,p,kind):
 a['relations'].append(dict(id=f'E{num:02d}',source=None,target=sid(target),type='entrance',name=name,entrance_type=kind,position_px=p))
entrance(7,1,'发热门诊西入口',[200,624],'infectious')
entrance(8,1,'发热门诊北入口',[405,585],'infectious')
entrance(9,20,'肠道门诊西入口',[200,816],'infectious')
entrance(10,27,'西药房北侧入口',[762,564],'staff')
entrance(11,31,'变配电室北侧入口',[1341,564],'staff')
entrance(12,159,'急诊大厅入口',[1680,1539],'emergency')
entrance(13,174,'急诊医护东侧入口',[2312,1048],'staff')
entrance(16,206,'急诊东南交通核南侧出口',[2375,1427],'staff')
entrance(15,172,'急诊西南交通核南侧出口',[1425,1539],'staff')
entrance(14,196,'EICU南侧入口',[2248,1540],'emergency')
# Note conceptual edges already in old data too, for a complete no-position count.
annotation.normalize(a)
path.write_text(json.dumps(a,ensure_ascii=False,indent=2)+'\n')
annotation.render(a,path,OUT/'待核验成果/标注.svg');fit_labels(OUT/'待核验成果/标注.svg',a)
(OUT/'连通判读记录.json').write_text(json.dumps(dict(removed=removed,concepts=concepts,relations=Counter(r['type'] for r in a['relations']),openings=sum(len(r.get('openings',[])) for r in a['relations'])),ensure_ascii=False,indent=2))
print(Counter(r['type'] for r in a['relations']))
print('openings',sum(len(r.get('openings',[])) for r in a['relations']))
