from pathlib import Path
import json
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
ROOT=Path('/Users/hushili/Documents/研究-论文写作/大论文')
OUT=ROOT/'p-写作过程/标注试样/07_内蒙古自治区儿童医院、妇产医院、妇幼保健院外迁合建项目'
TMP=ROOT/'p-写作过程/临时核对/07_内蒙古_20261029'
units=[]
scopes={'A':'emergency_obstetrics_gynecology','B':'obstetrics_outpatient','C':'perinatal_care','D':'outpatient_pharmacy','E':'medical_imaging','F':'emergency_pediatrics','G':'infusion_center','H':'fever_outpatient','J':'public_service'}
zone_names={'A':'妇产科急诊','B':'产科门诊','C':'产科超声与围产保健','D':'门诊药房','E':'影像中心','F':'儿科急诊','G':'输液中心','H':'发热门诊与哮喘中心','J':'公共大厅与医疗街'}
def add(z,b,name=None,typ=None,candidate=None,basis=None,confidence='低',level='room'):
 p=box(*b) if len(b)==4 and isinstance(b[0],(float,int)) else Polygon(b)
 if name is None: name='名称未确认';typ='unknown'
 units.append(dict(z=z,p=p,name=name,type=typ,level=level,scope=scopes[z],candidate=candidate or '用途未知',basis=basis or '原图文字不能可靠辨认',confidence=confidence))
 return units[-1]
def known(z,b,name,typ,level='room'):return add(z,b,name,typ,level=level)
def row(z,y1,y2,xs,cands=None):
 for i,(x1,x2) in enumerate(zip(xs,xs[1:])):
  c=cands[i] if cands else None
  add(z,(x1+3,y1+3,x2-3,y2-3),candidate=c or '用途未知')
def outline(z,p,name):
 from shapely.ops import split
 from shapely.geometry import LineString
 p=box(*p) if len(p)==4 and isinstance(p[0],(float,int)) else Polygon(p)
 used=unary_union([u['p'].buffer(4,join_style=2) for u in units if u['z']==z])
 remain=p.difference(used)
 stack=list(remain.geoms) if hasattr(remain,'geoms') else [remain]
 while stack:
  g=stack.pop()
  if g.area<750 or min(g.bounds[2]-g.bounds[0],g.bounds[3]-g.bounds[1])<12 or g.area/(g.length/2)<7:continue
  if g.interiors:
   hole=Polygon(g.interiors[0]);yy=hole.centroid.y
   stack.extend(split(g,LineString([(-10,yy),(2454,yy)])).geoms)
  else:
   units.append(dict(z=z,p=g,name=name,type='corridor',level='open_space',scope=scopes[z],candidate='',basis='',confidence='高'))
# A: upper-left wing in reading orientation. Rectangles follow actual partition lines.
row('A',155,218,[250,335,394,436,482,526,610],['办公室／值班室','库房／设备用房','卫生间／更衣室','卫生间／更衣室','库房／设备用房','工作人员支持用房'])
row('A',258,324,[250,302,357],['工作人员支持用房','工作人员支持用房'])
add('A',(250,328,357,385),candidate='检查室／处置室',basis='妇产科急诊内双扇门房间',confidence='低')
row('A',258,322,[398,478],['检查室／处置室'])
add('A',(398,326,478,385),candidate='B超检查室／诊室',basis='文字疑似B超，位于妇产科急诊',confidence='中')
row('A',258,385,[482,553,626],['抢救室／观察室','抢救室／观察室'])
known('A',(630,258,741,318),'妇产科急诊交通核','vertical_core','core_block')
row('A',322,385,[630,677,709,741],['设备用房／库房','卫生间／更衣室','卫生间／更衣室'])
add('A',(747,258,840,385),candidate='留观室／治疗室',basis='急诊侧端部独立大房间',confidence='低')
row('A',392,440,[250,302],['设备用房／库房'])
row('A',444,520,[250,302],['挂号收费／服务用房'])
row('A',445,520,[398,478,535,594,653,708],['妇产科诊室／检查室']*5)
row('A',525,596,[482,594,653,708],['处置室／治疗室','库房／设备用房','采血／检验用房'])
known('A',(401,532,465,589),'妇产科急诊护士站','nurse_station','semi_open_space')
row('A',445,520,[760,840],['心电图室／检查室'])
row('A',525,568,[760,840],['工作人员支持用房／检查室'])
row('A',573,645,[760,840],['检查室／处置室'])
row('A',650,789,[250,397,478,626,708,747,840],['观察室／留观室','患者准备／支持用房','急诊治疗室／抢救室','患者准备／支持用房','通道／前室','观察室／留观室'])
# refine three support rooms and WC at bottom
units=[u for u in units if not (u['z']=='A' and u['p'].bounds[0]>=400 and u['p'].bounds[2]<=475 and u['p'].bounds[1]>648)]
row('A',650,697,[398,478],['工作人员支持用房'])
row('A',701,742,[398,478],['卫生间／支持用房'])
row('A',746,789,[398,478],['卫生间／支持用房'])
# B upper centre wing
row('B',155,218,[895,1024,1068,1110,1256,1303,1348,1468],['办公室／值班室','库房／设备用房','库房／设备用房','工作人员支持用房','卫生间／更衣室','卫生间／更衣室','办公室／值班室'])
for a,b in [(258,320),(325,385),(390,453),(458,520),(525,580),(585,640)]:
 row('B',a,b,[895,976],['产科诊室／检查室'])
row('B',258,320,[1031,1110],['处置室／检查室'])
for a,b in [(325,385),(390,453),(458,520),(585,640)]:row('B',a,b,[1031,1110],['产科诊室／检查室'])
row('B',525,580,[1031,1070,1110],['患者准备／支持用房','患者准备／支持用房'])
add('B',(1165,258,1332,385),candidate='产科检查／治疗室',basis='产科门诊中央双开门大房间',confidence='中')
for a,b in [(390,453),(458,520),(585,640)]:row('B',a,b,[1165,1256,1332],['产科诊室／检查室']*2)
row('B',525,580,[1165,1256,1290,1332],['产科诊室／检查室','患者准备／支持用房','患者准备／支持用房'])
for a,b in [(258,320),(325,385),(390,453),(458,520),(525,580),(585,640)]:row('B',a,b,[1398,1468],['产科诊室／检查室'])
known('B',(895,650,973,789),'产科门诊交通核','vertical_core','core_block')
known('B',(1165,652,1332,705),'产科门诊护士站','nurse_station','semi_open_space')
add('B',(1398,650,1468,789),candidate='宣教室／诊室',basis='产科门诊南端独立用房',confidence='低')
# C top right + ultrasound lobby
row('C',155,218,[1745,1878,1920,1961,2108,2150,2196,2330],['办公室／值班室','卫生间／更衣室','卫生间／更衣室','工作人员支持用房','库房／设备用房','库房／设备用房','办公室／值班室'])
row('C',258,320,[1745,1787,1824],['患者准备／支持用房','患者准备／支持用房'])
for a,b in [(325,385),(390,453),(458,520),(525,580),(585,640)]:row('C',a,b,[1745,1824],['超声检查室／诊室'])
for a,b in [(258,320),(325,385),(390,453),(458,520),(525,580),(585,640)]:row('C',a,b,[1889,1961],['超声检查室／诊室'])
known('C',(1967,258,2108,320),'围产保健交通核','vertical_core','core_block')
add('C',(1967,325,2108,385),candidate='围产保健检查室／宣教室',basis='围产保健片区独立房间',confidence='低')
row('C',258,320,[2114,2196],['产后康复／保健用房'])
row('C',325,385,[2114,2196],['产后康复／保健用房'])
add('C',(1967,390,2196,520),candidate='产后康复／保健用房',basis='围产保健片区中央大房间',confidence='中')
add('C',(1967,525,2196,640),candidate='围产保健检查／治疗用房',basis='围产保健片区中央大房间',confidence='中')
add('C',(2254,258,2330,385),candidate='围产保健检查室／保健用房',basis='围产保健片区',confidence='低')
for a,b in [(390,453),(458,520),(525,640)]:row('C',a,b,[2254,2330],['围产保健诊室／检查室'])
known('C',(1967,650,2020,789),'围产保健电梯交通核','vertical_core','core_block')
known('C',(1468,650,1543,789),'产科超声交通核','vertical_core','core_block')
known('C',(1608,650,1737,789),'产科超声卫生间','toilet','functional_block')
known('C',(1550,650,1601,789),'产科超声前室','vestibule','open_space')
# F pediatric emergency
add('F',(250,2060,478,2197),candidate='抢救室／留观室',basis='房间内绘有三张诊疗床；位于儿科急诊',confidence='中')
row('F',2060,2105,[482,535],['库房／设备用房'])
row('F',2110,2153,[482,535],['库房／设备用房'])
row('F',2158,2197,[482,535],['患者准备／支持用房'])
add('F',(540,2060,708,2197),candidate='观察室／留观室',basis='急诊抢救室相邻大房间',confidence='中')
add('F',(760,2060,840,2197),candidate='治疗室／处置室',basis='儿科急诊端部房间',confidence='低')
row('F',2203,2260,[250,302],['挂号收费／服务用房'])
row('F',2330,2400,[250,302],['挂号收费／服务用房'])
row('F',2405,2452,[250,302],['库房／设备用房'])
known('F',(401,2265,473,2332),'儿科急诊护士站','nurse_station','semi_open_space')
row('F',2265,2332,[482,538,594,653,708],['儿科诊室／检查室']*4)
row('F',2337,2400,[398,478,538,594,653,708],['检查室／处置室']*5)
row('F',2203,2250,[760,840],['心电图室／检查室'])
row('F',2255,2332,[760,840],['处置室／治疗室'])
row('F',2337,2400,[760,800,840],['诊室／检查室']*2)
row('F',2458,2517,[250,357,398,478],['工作人员支持用房','通道／前室','检查室／处置室'])
# remove standalone narrow possible corridor
units=[u for u in units if not(u['z']=='F' and 359<u['p'].bounds[0]<395)]
row('F',2522,2585,[250,302,357],['工作人员支持用房','工作人员支持用房'])
row('F',2522,2585,[398,478],['B超检查室／诊室'])
row('F',2458,2585,[482,553,626],['留观室／治疗室','留观室／治疗室'])
row('F',2458,2517,[630,677,709,741],['设备用房／库房','卫生间／更衣室','卫生间／更衣室'])
known('F',(630,2522,741,2585),'儿科急诊交通核','vertical_core','core_block')
add('F',(747,2458,840,2585),candidate='观察室／留观室',basis='儿科急诊内侧大房间',confidence='中')
row('F',2627,2685,[250,335,394,436,482,526,610],['办公室／值班室','工作人员支持用房','卫生间／更衣室','卫生间／更衣室','库房／设备用房','工作人员支持用房'])
# G infusion
known('G',(895,2060,973,2197),'输液中心交通核','vertical_core','core_block')
add('G',(980,2060,1250,2197),candidate='输液中心留观区／输液区',basis='输液中心北侧连续大空间',confidence='中')
known('G',(1256,2060,1468,2585),'输液大厅','treatment','functional_block')
known('G',(1256,2210,1315,2393),'输液护士站','nurse_station','semi_open_space')
# nurse station carved out of hall
units[-2]['p']=units[-2]['p'].difference(units[-1]['p'])
# split L shaped hall no holes because station touches west boundary
row('G',2203,2255,[895,1031,1110],['输液配药／准备室','工作人员支持用房'])
add('G',(895,2260,1110,2393),candidate='输液治疗区／特殊输液区',basis='输液大厅相邻分隔大房间',confidence='中')
add('G',(895,2450,1110,2585),candidate='输液治疗区／留观区',basis='输液中心西侧独立大空间',confidence='中')
for a,b in [(2203,2260),(2265,2332),(2337,2393),(2398,2455),(2460,2517),(2522,2585)]:row('G',a,b,[1165,1250],['治疗准备／工作人员支持用房'])
row('G',2627,2685,[895,1031,1070,1110],['办公室／值班室','库房／设备用房','库房／设备用房'])
row('G',2627,2685,[1256,1300,1348,1468],['卫生间／更衣室','卫生间／更衣室','工作人员支持用房'])
# H lower-right wing fever and asthma
known('H',(1608,2060,1737,2197),'儿科医疗街卫生间','toilet','functional_block')
known('H',(1468,2060,1543,2197),'儿科医疗街交通核','vertical_core','core_block')
known('H',(1550,2060,1601,2197),'儿科医疗街前室','vestibule','open_space')
row('H',2060,2105,[1745,1824],['哮喘诊室／检查室'])
row('H',2110,2153,[1745,1824],['哮喘治疗／检查室'])
row('H',2158,2197,[1745,1824],['呼吸功能检查／治疗室'])
row('H',2060,2123,[1967,2110],['呼吸功能检查／治疗室'])
row('H',2128,2197,[1967,2110],['哮喘治疗／检查室'])
for a,b in [(2060,2105),(2110,2153),(2158,2197)]:row('H',a,b,[2254,2330],['哮喘诊室／检查室'])
row('H',2240,2332,[1745,1815,1880,2015,2070],['发热诊室／检查室','发热诊室／检查室','隔离观察／治疗室','工作人员支持用房'])
row('H',2398,2480,[1815,1880,1961],['发热诊室／检查室','检验室／处置室'])
row('H',2398,2425,[1967,2020],['患者准备／支持用房'])
row('H',2430,2480,[1967,2020],['工作人员支持用房'])
row('H',2398,2480,[2025,2070],['发热诊室／检查室'])
row('H',2398,2435,[1745,1810],['护士站／服务工作区'])
row('H',2522,2585,[1745,1815,1880,1920,1961],['工作人员支持用房','卫生间／支持用房','患者准备／支持用房','卫生间／支持用房'])
known('H',(1967,2522,2108,2585),'发热门诊交通核','vertical_core','core_block')
row('H',2627,2685,[1745,1878,1920,1961,2108,2150,2196,2330],['办公室／值班室','卫生间／更衣室','卫生间／更衣室','门斗／入口区','库房／设备用房','库房／设备用房','工作人员支持用房'])
# H blue strip at right
for a,b in [(2203,2332),(2337,2393),(2398,2455),(2460,2517),(2522,2585)]:row('H',a,b,[2114,2196],['诊室／检查室'])
for a,b in [(2203,2260),(2265,2332),(2337,2393),(2398,2455),(2460,2517),(2522,2585)]:row('H',a,b,[2254,2330],['诊室／检查室'])
# D outpatient pharmacy including registration windows
row('D',906,1004,[753,889],['门诊服务／管理用房'])
known('D',(895,906,1031,1050),'妇产科取药服务区','pharmacy_counter','open_space')
add('D',(1036,906,1178,1050),candidate='药房／库房',basis='位于门诊药房北端，图中无可确认设备',confidence='低',level='functional_block')
known('D',(1178,906,1324,1207),'药房东侧服务通道','corridor','open_space')
row('D',1057,1149,[850,905],['工作人员支持用房'])
row('D',1154,1207,[850,905],['设备用房／库房'])
known('D',(850,1213,905,1265),'药房电梯交通核','vertical_core','core_block')
row('D',1310,1355,[850,905],['工作人员支持用房'])
row('D',1360,1404,[850,905],['工作人员支持用房'])
row('D',1409,1454,[850,905],['工作人员支持用房'])
row('D',1459,1499,[850,905],['工作人员支持用房'])
row('D',1504,1596,[850,905],['库房／设备用房'])
for a,b in [(1057,1097),(1102,1207),(1213,1265),(1270,1404),(1409,1499),(1504,1552),(1557,1596),(1601,1637)]:
 row('D',a,b,[911,984],['药房配套／工作人员用房'])
known('D',(990,1057,1104,1637),'门诊药房','pharmacy','functional_block')
known('D',(1109,1057,1178,1207),'药房内部通道','corridor','open_space')
known('D',[(1109,1637),(1178,1213),(1324,1213),(1324,1637)],'名称未确认','unknown','open_space')
units[-1].update(candidate='内庭院／中庭（是否露天待确认）',basis='图面留白并绘有斜边轮廓，无可辨识室内设施',confidence='中')
row('D',1643,1725,[850,984,1104,1324],['药房配套／工作人员用房','药房配套／工作人员用房','药房配套／工作人员用房'])
known('D',(753,1057,814,1318),'北侧挂号收费','registration','semi_open_space')
known('D',(753,1324,814,1518),'排号收费服务区','registration','semi_open_space')
known('D',(753,1524,814,1725),'南侧挂号收费','registration','semi_open_space')
# E imaging centre
row('E',906,994,[1333,1400,1470,1606,1745,1824,1889,1961,2020],['影像配套用房']*8)
row('E',906,947,[2026,2063,2154],['影像配套用房','影像配套用房'])
row('E',952,994,[2026,2063,2154],['影像配套用房','影像配套用房'])
known('E',(2190,906,2254,1050),'影像中心北交通核','vertical_core','core_block')
known('E',(1406,1057,1601,1150),'影像中心等候区','hall','open_space')
for x1,x2 in [(1607,1725),(1731,1849),(1855,1972),(2041,2154)]:known('E',(x1,1057,x2,1150),'影像检查室','imaging')
row('E',1057,1100,[1978,2035],['影像配套用房'])
row('E',1105,1150,[1978,2035],['影像配套用房'])
for a,b in [(1057,1120),(1125,1187),(1193,1318),(1324,1390),(1396,1450),(1456,1518),(1524,1580),(1586,1637)]:row('E',a,b,[2190,2254],['影像配套／工作人员用房'])
known('E',(1406,1200,1470,1390),'影像中心电梯交通核','vertical_core','core_block')
for x1,x2 in [(1476,1595),(1601,1720),(1843,1961),(2030,2154)]:known('E',(x1,1200,x2,1338),'影像检查室','imaging')
add('E',(1726,1200,1837,1338),candidate='影像设备／检查准备室',basis='位于多间大型影像检查室之间',confidence='中')
add('E',(1967,1200,2024,1390),candidate='设备机房／检查准备室',basis='影像检查室之间的长条独立空间',confidence='中')
for x1,x2 in [(1476,1533),(1539,1650),(1656,1720),(1726,1783),(1789,1849),(1855,1914),(1920,1961),(2030,2090),(2096,2154)]:
 add('E',(x1,1344,x2,1390),candidate='控制室／检查配套用房',basis='紧贴影像检查室背面的小房间',confidence='中')
known('E',(1333,1450,1470,1637),'影像中心等候区','hall','open_space')
for x1,x2 in [(1476,1601),(1607,1745),(1751,1889),(1967,2108)]:known('E',(x1,1450,x2,1575),'影像检查室','imaging')
row('E',1450,1485,[1895,1930,1961],['卫生间／患者准备用房','卫生间／患者准备用房'])
add('E',(1895,1491,1961,1575),candidate='影像配套／设备机房',basis='影像检查室之间的独立小房间',confidence='中')
add('E',(2114,1450,2154,1575),candidate='设备机房／检查配套用房',basis='影像检查室外侧的长条空间',confidence='中')
row('E',1643,1725,[1406,1476,1545,1686,1824,1895,1961,2030,2108,2154],['影像配套／工作人员用房']*9)
known('E',(2190,1643,2254,1747),'影像中心南交通核','vertical_core','core_block')
# J common spaces, courtyards and vertical circulation
known('J',(390,915,615,1067),'共享大厅北侧扶梯与电梯核','vertical_core','core_block')
known('J',(390,1780,615,1937),'共享大厅南侧扶梯与电梯核','vertical_core','core_block')
# exterior main hall minus traffic cores
hall=Polygon([(245,900),(745,900),(745,1937),(245,1937),(185,1800),(170,1600),(170,1300),(185,1100)])
# explicitly split around cores to maintain no-hole polygons
for b in [(245,900,745,915),(615,915,745,1937),(245,1067,615,1780),(245,915,390,1067),(245,1780,390,1937)]:
 q=box(*b).intersection(hall)
 known('J',list(q.exterior.coords)[:-1],'共享大厅','hall','open_space')
# curved west strip absent from rectangular decomposition
q=hall.difference(unary_union([u['p'] for u in units if u['z']=='J']))
for p in (list(q.geoms) if hasattr(q,'geoms') else [q]):
 if p.area>35:known('J',list(p.exterior.coords)[:-1],'共享大厅','hall','open_space')
known('J',(245,796,2330,900),'妇产科医疗街','corridor','open_space')
known('J',(245,1943,2330,2054),'儿科医疗街','corridor','open_space')
for b in [(753,1731,2190,1792),(753,1798,1023,1937),(1330,1798,1464,1937),(1895,1798,2190,1937),(2196,1753,2254,1937)]:known('J',b,'医疗街连接通道','corridor','open_space')
for b in [(1029,1798,1324,1937),(1470,1798,1889,1937)]:add('J',b,candidate='内庭院／中庭（是否露天待确认）',basis='交通街之间的封闭留白区，露天属性不能确定',confidence='中',level='open_space')
# Block outlines preserve individual rooms while partitioning remaining circulation into polygons without holes.
for z,b in [('A',(245,155,845,790)),('B',(888,155,1470,790)),('C',(1740,155,2335,790)),('F',(245,2058,845,2690)),('G',(888,2058,1470,2690)),('H',(1740,2058,2335,2690))]:outline(z,b,zone_names[z]+'通道及候诊区')
for z,b in [('D',(745,900,1330,1730)),('E',(1330,900,2260,1730))]:outline(z,b,zone_names[z]+'内部通道')
# Separate clearly coloured outpatient scopes in combined wings.
for u in units:
 if u['z']=='H':
  x1,y1,x2,y2=u['p'].bounds
  if (y2<2200 and x1>=1740) or (x1>=2110 and y1<2590):u['scope']='pediatric_asthma_outpatient'
 if u['z']=='C' and u['p'].bounds[2]<=1965:u['scope']='obstetric_ultrasound'
 if u['type']=='unknown' and u['basis']=='原图文字不能可靠辨认':
  u['basis']='位于'+zone_names[u['z']]+'片区；仅依片区用途推测，小字不能可靠辨认'
# Keep raw supplied-image orientation for numbering: adjacent regions across each horizontal band.
# Sort each block top-to-bottom and left-to-right in original pixel coordinates.
order=['F','A','G','D','B','H','E','C','J']
def orig(p):return [(round(3260-y,2),round(x,2)) for x,y in list(p.exterior.coords)[:-1]]
for u in units:
 u['orig']=Polygon(orig(u['p']))
units.sort(key=lambda u:(order.index(u['z']),round(u['orig'].bounds[1]/40),u['orig'].bounds[0],u['orig'].bounds[1]))
spaces=[]
for i,u in enumerate(units,1):
 u['id']=f'S{i:03d}';spaces.append({k:u[k] for k in ('id','name','type','level','scope')}|{'polygon_px':orig(u['p'])})
# No speculative room access: only circulation continuities supported by uninterrupted open areas.
rels=[]
for i,a in enumerate(units):
 for b in units[i+1:]:
  if a['type'] not in ['corridor','hall'] or b['type'] not in ['corridor','hall']:continue
  if a['p'].distance(b['p'])<7 and a['p'].buffer(3.5).intersection(b['p'].buffer(3.5)).area>20:
   rels.append({'id':f'R{len(rels)+1:03d}','source':a['id'],'target':b['id'],'type':'access'})
# Open service counters create service links, but never imply crossing the counter.
for a in units:
 if a['type'] not in ['nurse_station','registration','pharmacy_counter']:continue
 candidates=[b for b in units if b['type'] in ['corridor','hall','treatment'] and a['p'].distance(b['p'])<12]
 if candidates:
  b=max(candidates,key=lambda b:a['p'].buffer(12).intersection(b['p']).area)
  rels.append({'id':f'R{len(rels)+1:03d}','source':a['id'],'target':b['id'],'type':'service'})
# external interfaces visible as doors on medical streets and emergency frontages; attach actual immediate area.
for name,pt,z in [('妇产科医疗街入口',(2330,850),'J'),('儿科医疗街入口',(2330,2000),'J'),('儿科急诊入口',(245,2280),'F'),('妇产科急诊入口',(245,580),'A'),('输液中心入口',(1190,2690),'G'),('发热门诊入口',(2030,2690),'H')]:
 from shapely.geometry import Point
 target=min([u for u in units if u['z']==z and u['type'] in ['corridor','hall']],key=lambda u:u['p'].distance(Point(pt)))
 rels.append(dict(id=f'E{sum(r["type"]=="entrance" for r in rels)+1:02d}',source=None,target=target['id'],type='entrance',name=name,entrance_type='building_entrance',position_px=[3260-pt[1],pt[0]]))
data={'image':{'file':next(OUT.glob('*.jpg')).name,'width':3260,'height':2444},'spaces':spaces,'relations':rels}
(OUT/'annotation.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
# Stable review mappings saved only in temporary directory, populated separately in source-image spatial order.
pending=[u for u in units if u['type']=='unknown']
pending.sort(key=lambda u:(order.index(u['z']),round(u['orig'].bounds[1]/40),u['orig'].bounds[0],u['orig'].bounds[1]))
review=[]
for i,u in enumerate(pending,1):review.append(dict(number=f'{i:02d}',id=u['id'],zone=u['z'],zone_name=zone_names[u['z']],candidate=u['candidate'],basis=u['basis'],confidence=u['confidence'],polygon_px=orig(u['p'])))
(TMP/'核对对应_临时.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
print('spaces',len(spaces),'unknown',len(pending),'relations',len(rels))
from collections import Counter
print(Counter(u['z'] for u in units));print(Counter(u['type'] for u in units))
