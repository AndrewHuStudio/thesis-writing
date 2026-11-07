from pathlib import Path
from shapely.geometry import Polygon,box,Point
from shapely.ops import transform,unary_union
import json,collections
base=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理');root=base/'标注试样/29_内蒙古自治区国际蒙医医院扩建项目';w=base/'临时核对/29_内蒙古自治区国际蒙医医院扩建项目';run=Path((w/'当前续作目录.txt').read_text().strip());d=json.loads((root/'annotation.json').read_text());by={s['id']:s for s in d['spaces']};audit=[];geometry=[]
(run/'名称同步后_连通复核前.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def original(g):return transform(lambda x,y,z=None:(2444-y,x),g)
def polyread(g):return [[round(x,2),round(y,2)] for x,y in list(original(g).exterior.coords)[:-1]]
def replace(sid,g,reason):
 geometry.append({'space_id':sid,'before':by[sid]['polygon_px'],'reason':reason});by[sid]['polygon_px']=polyread(g)
# Restore omitted, visually continuous parts of the same named halls and room boundaries.
replace('S038',box(731,1196,1067,1225),'检查区上通道漏掉交通核下方至CT门前的一段，按原图连续灰色通道补齐。')
replace('S201',box(2005,395,2091,489),'接待中心南侧与门厅之间为连续灰色前室，补齐门厅北段。')
replace('S159',Polygon([(2036,1820),(2270,1820),(2270,1958),(2113,1958),(2113,1874),(2036,1874)]),'急诊大厅西北角与圆形厅之间的同一灰色通行范围原来漏画。')
for sid,x1,x2 in [('S211',2346,2388),('S212',2389,2430),('S214',2517,2603)]:replace(sid,box(x1,351,x2,450),'房间南界原草稿止于柱网线；原图实体墙和门洞在450像素附近，延至实际南界。')
# These are missing common circulation areas, not subdivisions of enclosed rooms.
def add_space(sid,name,g,scope='public_service'):
 occupied=unary_union([Polygon(s['polygon_px']) for s in d['spaces']]);q=original(g).difference(occupied)
 assert q.geom_type=='Polygon' and not q.interiors,(sid,q.geom_type,len(getattr(q,'interiors',[])))
 s=dict(id=sid,name=name,type='hall' if '大厅' in name else 'corridor',level='open_space',scope=scope,polygon_px=[[round(x,2),round(y,2)] for x,y in list(q.exterior.coords)[:-1]])
 d['spaces'].append(s);by[sid]=s;geometry.append({'space_id':sid,'reason':'原图可见连续公共通行区域，补充原草稿漏标范围。'})
add_space('S215','主入口西北连接大厅',box(1568,1476,1733,1774))
add_space('S216','主入口北连接大厅',box(1734,1476,1963,1721))
add_space('S217','主入口东连接大厅',box(1902,1576,2035,1873))
add_space('S218','急诊北侧通道',box(1902,1138,2035,1165),'emergency')
add_space('S219','东侧交通核连接通道',box(2005,490,2025,674))
add_space('S220','住院药库前通道',Polygon([(2026,490),(2176,490),(2176,526),(2152,526),(2152,500),(2026,500)]))
add_space('S221','体检区侧通道',box(1399,1579,1434,1774),'ordinary_outpatient')
# The block-to-hall link is visible through the short continuous gray seam.
replace('S119',box(1751,760,1834,996),'商业片区公共通道至主楼北连接大厅间为连续灰色通行带，延续到接合处。')
retire_pairs=[('S045','S046'),('S144','S184'),('S201','S206'),('S129','S160')]
removed=[]
for a,b in retire_pairs:
 for r in list(d['relations']):
  if r['type']=='access' and {r['source'],r['target']}=={a,b}:d['relations'].remove(r);removed.append(r)
# IDs are stable and retired IDs are not reused.
rnum=max([int(r['id'][1:]) for r in d['relations'] if r['id'].startswith('R')]+[97]);pnum=0
existing={(r['type'],frozenset((r['source'],r['target']))):r for r in d['relations'] if r['type']!='entrance'}
def relation(a,b,kind='access',uv=None,basis='图面门洞',opening_kind='door'):
 global rnum,pnum
 key=(kind,frozenset((a,b)));r=existing.get(key)
 if r is None:
  rnum+=1;r=dict(id=f'R{rnum:03d}',source=a,target=b,type=kind);d['relations'].append(r);existing[key]=r
 if uv:
  pnum+=1;r.setdefault('openings',[]).append(dict(id=f'P{pnum:03d}',kind=opening_kind,position_px=[round(2444-uv[1],2),round(uv[0],2)]))
 audit.append({'relation_id':r['id'],'source':a,'target':b,'type':kind,'reading_position':uv,'basis':basis})
def door(a,b,u,v):relation(a,b,uv=(u,v))
def concept(a,b,reason='图面公共通行区连续；空间边界是标注分区。'):relation(a,b,basis=reason)
# West main building. Pixel positions are read from the original, not derived from centroids.
for a,b,u,v in [
('S030','S038',770,1226),('S037','S038',820,1226),('S042','S038',904,1226),
('S036','S029',814,1310),('S036','S045',980,1310),
('S048','S045',1005,1236),('S047','S045',1005,1291),('S046','S017',1010,1394),
('S035','S017',882,1394),('S041','S017',967,1394),
('S034','S017',830,1461),('S044','S017',1007,1461),('S044','S027',980,1505),
('S024','S025',770,1710),('S032','S025',813,1710),
('S019','S020',640,1347),('S018','S020',640,1380),('S021','S020',680,1230),
('S026','S039',905,1624),('S031','S038',798,1196)]:door(a,b,u,v)
for a,b in [('S029','S020'),('S029','S017'),('S038','S020'),('S025','S033'),('S161','S160'),('S167','S186'),('S144','S159')]:concept(a,b)
concept('S001','S007','图面门诊用房组团的内部通道在东端直接汇入扇形翼部连接大厅。')
concept('S002','S004','图面门诊用房组团的内部通道在东端直接汇入扇形翼部连接大厅。')
concept('S011','S007','布局推断：收费挂号为独立弧形服务岛，服务侧面向同一大厅；人员门未清晰画出。')
relation('S011','S007','service',basis='用户确认收费挂号；服务岛外侧与大厅直接形成柜台服务界面。')
# Central imaging unit.
for a,b,u,v in [
('S075','S074',1230,1048),('S081','S074',1275,1048),('S082','S074',1318,1048),('S088','S074',1360,1048),('S091','S074',1404,1048),
('S056','S066',1192,1084),('S061','S066',1118,1104),('S060','S066',1118,1165),('S059','S066',1118,1256),
('S054','S066',1110,1304),('S053','S065',1183,1347),
('S073','S080',1266,1091),('S072','S066',1216,1162),('S071','S066',1216,1201),('S069','S066',1216,1281),
('S080','S087',1352,1090),('S079','S070',1285,1236),('S086','S070',1371,1236),
('S085','S090',1404,1260),('S085','S078',1352,1280),('S078','S070',1350,1250),
('S087','S090',1404,1092),('S077','S090',1404,1358)]:door(a,b,u,v)
concept('S057','S074')
concept('S055','S066','布局推断：检查区外侧窄通道与检查通道在北侧楼梯前开口衔接。')
# Physical-examination block: clear room doors and the independent lobby entrance.
for a,b,u,v in [('S058','S050',1141,1647),('S064','S050',1221,1647),('S068','S050',1245,1647),('S076','S050',1284,1647),('S093','S094',1458,1476),('S097','S093',1484,1568),('S098','S215',1567,1489),('S050','S221',1399,1688)]:door(a,b,u,v)
for a,b in [('S051','S050'),('S063','S050')]:concept(a,b,'布局推断：体检小房朝向同一连续体检区，图面底边开口可辨，门位未能可靠定位。')
concept('S089','S093','布局推断：电梯组面向用户确认的候梯区，不细究交通核内部路线。')
concept('S084','S221','布局推断：楼梯东侧前室衔接体检区侧通道，准确门位未清。')
concept('S092','S221','布局推断：体检大厅西侧的通行口衔接侧通道。')
relation('S092','S098','service',basis='体检大厅与用户确认的挂号收款区之间有连续柜台符号。')
# Gray links around the now-confirmed main entrance hall.
for a,b in [('S094','S215'),('S215','S216'),('S215','S111'),('S216','S111'),('S216','S217'),('S217','S111'),('S216','S126'),('S216','S136'),('S119','S118'),('S218','S153'),('S219','S200'),('S219','S201'),('S220','S219'),('S220','S208'),('S204','S207')]:concept(a,b)
for a,b,u,v in [('S129','S126',1902,1427),('S218','S126',1902,1151),('S145','S217',2036,1738),('S144','S217',2036,1780),('S159','S217',2036,1838)]:door(a,b,u,v)
# Emergency block, north rooms.
for a,b,u,v in [
('S133','S218',1925,1137),('S140','S218',1984,1137),('S142','S218',2011,1137),
('S141','S218',2005,1166),('S155','S154',2101,1113),('S164','S154',2121,1113),('S195','S154',2277,1113),
('S158','S157',2087,1194),('S173','S157',2164,1194),('S180','S157',2204,1194),('S181','S157',2248,1194),('S194','S154',2280,1138),
('S152','S153',2048,1229),('S162','S157',2127,1229),
('S130','S129',1932,1409),('S138','S129',1997,1409),('S151','S129',2078,1409),
('S172','S161',2144,1344),('S171','S170',2162,1409),('S178','S170',2233,1409),
('S191','S186',2292,1405),('S190','S186',2292,1458),('S189','S186',2292,1494),('S188','S186',2292,1534),('S187','S186',2292,1598),('S185','S186',2292,1790)]:door(a,b,u,v)
for a,b in [('S132','S218'),('S139','S218')]:concept(a,b,'布局推断：房间朝向北侧通道，原图北界处入口模糊；不定位红点。')
concept('S174','S154','布局推断：上侧楼梯交通核在南侧衔接连续通道。')
relation('S163','S157','service',basis='挂号房临公共通道形成服务界面；工作人员门本轮不细究。')
# Emergency block, south rooms.
for a,b,u,v in [
('S148','S160',2112,1603),('S169','S160',2144,1486),('S168','S160',2144,1603),
('S166','S160',2144,1648),('S165','S160',2144,1748),
('S177','S186',2271,1484),('S177','S186',2271,1564),('S175','S186',2271,1650),('S175','S186',2271,1744),
('S184','S159',2271,1834),('S183','S159',2271,1875),('S182','S159',2271,1928)]:door(a,b,u,v)
concept('S137','S129','布局推断：卫生间北侧入口朝向相邻急诊公共通道，不细究内部隔间。')
concept('S135','S136','布局推断：卫生间的对外口朝向用户确认的候梯厅。')
concept('S176','S186','布局推断：楼梯交通核东侧衔接急诊右通道，不细究内部楼梯路线。')
for a,b in [('S146','S160'),('S147','S160')]:concept(a,b,'布局推断：房间出入口朝向东侧连续急诊通道，原图门位模糊。')
relation('S143','S159','service',basis='用户确认挂号收费；三角服务区朝向急诊大厅，人员门本轮不细究。')
# Independent infusion/retail area and east pharmacy wing.
for a,b,u,v in [
('S110','S119',1751,805),('S102','S119',1751,946),('S196','S119',1835,912),('S196','S207',2180,841),
('S125','S197',1908,808),('S198','S197',1941,808),('S199','S197',1985,808),('S197','S119',1835,823),
('S200','S204',2026,700),('S203','S200',2026,776),('S203','S207',2152,776),('S203','S207',2152,823),
('S205','S219',2026,584),('S205','S207',2152,585),('S202','S201',2012,394),
('S206','S220',2162,489),('S206','S210',2346,471),('S211','S210',2368,451),('S212','S210',2410,451),('S214','S210',2558,451)]:door(a,b,u,v)
concept('S213','S210','布局推断：东端交通核在下侧前室接入独立片区通道。')
relation('S209','S208','service',basis='出入院手续服务带朝向其南侧公共大厅，图面有连续柜台界面。')
concept('S209','S220','布局推断：出入院手续带西端工作人员出入口衔接药库前通道。')
# Explicit external interfaces visible on this same source image.
for eid,target,name,u,v in [('E08','S092','体检大厅入口',1470,1774),('E09','S210','药库东侧通道入口',2603,470)]:
 d['relations'].append(dict(id=eid,source=None,target=target,type='entrance',name=name,entrance_type='external',position_px=[2444-v,u]))
# Keep diagnostics outside the core data; a distant door must be rechecked visually.
far=[]
for r in d['relations']:
 for p in r.get('openings',[]):
  q=Point(p['position_px']);dist=[Polygon(by[k]['polygon_px']).distance(q) for k in [r['source'],r['target']]]
  if max(dist)>18:far.append({'relation':r['id'],'opening':p['id'],'spaces':[r['source'],r['target']],'distances':dist,'position':p['position_px']})
(run/'连通复核依据.json').write_text(json.dumps({'relations':audit,'geometry_changes':geometry,'removed_relations':removed,'door_distance_flags':far},ensure_ascii=False,indent=2)+'\n');(root/'annotation.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
print({'spaces':len(d['spaces']),'relations':len(d['relations']),'openings':pnum,'distance_flags':far})
