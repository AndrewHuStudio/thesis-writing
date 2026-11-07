from pathlib import Path
import json, hashlib
from shapely.geometry import Polygon, box, LineString
from shapely.ops import split

ROOT=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-写作过程/标注试样/39_梅州市蕉岭县人民医院')
TMP=Path('/tmp/outpatient39-review')
rows=[]
def rect(a,b,c,d): return [[a,b],[c,b],[c,d],[a,d]]
def add(key,g,name,typ,shape,scope='public_service',level='functional_block',cand=None,why='',confidence='低'):
    if len(shape)==4 and isinstance(shape[0],(int,float)): shape=rect(*shape)
    rows.append(dict(key=key,group=g,name=name,type=typ,level=level,scope=scope,polygon=shape,candidates=cand,why=why,confidence=confidence))
def u(key,g,shape,cand,why,confidence='中',scope='public_service',level='functional_block'):
    add(key,g,'名称未确认','unknown',shape,scope,level,cand,why,confidence)
def c(key,g,shape,scope='public_service',name='通道'):
    add(key,g,name,'corridor',shape,scope,'open_space')
def core(key,g,shape,name='交通核',scope='public_service'):
    add(key,g,name,'vertical_core',shape,scope,'core_block')

# A: 阅读方向的左上会议片区；每个科室内部按图面逐排编号。
core('Acore','A',(185,390,277,507))
u('A01','A',(278,390,374,507),['会议配套用房','办公用房'],'紧邻会议中心交通核，内部有小隔间')
u('A02','A',(375,390,534,507),['会议配套用房','办公用房'],'独立大开间，门向会议通道')
u('A03','A',(535,390,674,507),['会议配套用房','办公用房'],'与前一间同排，靠次出入口')
c('Apass1','A',(185,508,589,565),name='会议中心通道')
u('A04','A',(590,508,674,565),['会议配套用房','设备用房'],'舞台上侧的小房间',level='room')
add('Ameeting','A','会议中心','education',(190,566,589,795))
u('A05','A',(590,566,674,680),['会议配套用房','后台用房'],'沿舞台后侧独立布置',level='room')
u('A06','A',(590,681,674,795),['卫生间','会议配套用房'],'多个小隔间，邻舞台后侧')
c('Apass2','A',(190,796,459,862),name='会议中心南侧通道')
add('Agreen','A','会议中心旁绿化庭院','landscape',(460,796,674,914),level='landscape')
u('A07','A',(190,863,277,941),['卫生间','服务用房'],'有若干隔断及疑似洁具符号')
u('A08','A',(278,863,315,922),['收费配套用房','办公用房'],'挂号收费左侧小房间',level='room')
add('Areg','A','挂号收费','registration',(316,863,351,922),level='room')
u('A09','A',(352,863,387,922),['收费配套用房','办公用房'],'与图例4同一排小房间',level='room')
u('A10','A',(388,863,423,922),['收费配套用房','办公用房'],'与图例4同一排小房间',level='room')
u('A11','A',(424,863,459,922),['收费配套用房','办公用房'],'与图例4同一排小房间',level='room')
c('Apass3','A',[[278,923],[460,923],[460,915],[674,915],[674,942],[278,942]],name='挂号收费外侧通道')

# B: 上部后勤片区。24号明确是停车库上空，不作为室内面积。
add('Bentry','B','次出入口门厅','hall',(675,390,777,723),level='open_space')
u('B01','B',(778,447,839,564),['后勤值班用房','辅助用房'],'电梯厅左侧带小隔间的附属区域',scope='hospital_support')
core('Blift','B',(840,447,886,564),'电梯组',scope='hospital_support')
c('Blobby','B',(887,440,939,564),'hospital_support','后勤电梯厅')
core('Bcore','B',[[940,438],[1094,438],[1094,481],[1038,481],[1038,564],[940,564]],scope='hospital_support')
c('Bpass','B',[[778,565],[1039,565],[1039,482],[1094,482],[1094,608],[778,608]],'hospital_support','后勤交通核通道')
c('Bupper','B',[[1095,460],[1453,460],[1453,566],[1717,566],[1717,609],[1328,609],[1328,566],[1401,566],[1401,494],[1095,494]],'hospital_support','太平间北侧通道')
u('B02','B',(1328,495,1400,565),['太平间配套用房','后勤用房'],'紧邻图例23的东侧房间',scope='hospital_support',level='room')
u('B03','B',(1454,460,1608,565),['后勤用房','办公用房'],'后勤区北侧独立大房间',scope='hospital_support',level='room')
core('Bfarcore','B',(1609,460,1698,565),scope='hospital_support')
c('Bfarpass','B',(1699,460,1717,565),'hospital_support','东端交通核通道')
add('Bmort','B','太平间','staff_support',(1195,495,1327,609),'hospital_support')
add('Blaundry','B','洗衣中心','staff_support',[[829,609],[1094,609],[1094,494],[1194,494],[1194,718],[829,718]],'hospital_support')
u('B04','B',(778,609,828,718),['洗衣中心配套用房','后勤用房'],'紧靠洗衣中心西边的狭长房间',scope='hospital_support',level='room')
u('B05','B',(1195,610,1294,718),['卫生间','后勤配套用房'],'太平间南侧有多个小隔间',scope='hospital_support')
u('B06','B',(1295,610,1400,686),['太平间配套用房','后勤接待用房'],'位于太平间南侧，开向公共通道',scope='hospital_support',level='room')
c('Bbottom','B',[[1401,610],[1498,610],[1498,718],[1295,718],[1295,687],[1401,687]],'hospital_support','后勤南侧通道')
u('B07','B',(1499,610,1717,718),['后勤用房','设备用房'],'后勤东南端的大房间，无功能文字',scope='hospital_support',level='room')
add('Bgarden','B','后勤区绿化庭院','landscape',(830,720,1076,859),level='landscape')
add('Bvoid','B','地下停车库上空','courtyard',[[1077,720],[1424,720],[1424,816],[1314,816],[1314,859],[1077,859]],'hospital_support','open_space')
u('B08','B',(1315,817,1424,859),['车库配套用房','设备用房'],'图例24右下角的小围合空间',scope='hospital_support',level='room')

# C: 中部左侧急诊。未见图中12号落位，整组未知诊疗房保留unknown。
core('Ccore','C',(185,943,277,1043),scope='emergency')
u('C01','C',(278,943,374,1008),['卫生间','急诊配套用房'],'交通核旁的多个小隔间',scope='emergency')
u('C02','C',(375,943,451,1008),['急诊诊室','急诊配套用房'],'急救大厅北侧独立房间',scope='emergency',level='room')
u('C03','C',(452,943,562,1008),['急诊诊室','急诊配套用房'],'抢救大厅北侧大房间',scope='emergency',level='room')
u('C04','C',(563,943,674,1008),['急诊配套用房','卫生间'],'北侧房间组，含狭小隔断',scope='emergency')
c('Cnorthpass','C',(278,1009,674,1044),'emergency','急救区北侧通道')
add('Cfirstaid','C','急救大厅','resuscitation',(185,1045,278,1125),'emergency','open_space')
add('Crescue','C','抢救大厅','resuscitation',(279,1045,377,1125),'emergency')
u('C05','C',(378,1045,488,1108),['抢救配套用房','治疗用房'],'位于抢救大厅东侧，内有小隔间',scope='emergency',level='room')
u('C06','C',(519,1045,585,1108),['抢救配套用房','治疗用房'],'位于抢救大厅东侧，邻电梯',scope='emergency',level='room')
core('Clift','C',(588,1045,674,1125),'急诊电梯组',scope='emergency')
c('Crescuepass','C',[[489,1045],[518,1045],[518,1109],[587,1109],[587,1125],[378,1125],[378,1109],[489,1109]],'emergency','抢救配套通道')
add('Cnurse1','C','护士站','nurse_station',(185,1126,244,1151),'emergency','semi_open_space')
c('Cshortpass','C',(245,1126,455,1151),'emergency','急诊诊疗区入口通道')
u('Cfever','C',(185,1152,455,1351),['发热门诊','急诊诊疗配套区'],'连续小诊疗房及通道；图例有12发热门诊，但图面未见12落位',scope='emergency')
add('Cgreen','C','急诊旁绿化庭院','landscape',[[456,1127],[674,1127],[674,1235],[589,1235],[589,1350],[456,1350]],level='landscape')
u('Ctoilet','C',(590,1236,674,1350),['卫生间','急诊辅助用房'],'绿化边缘、含小隔间与疑似洁具符号',scope='emergency')
c('spine','C',[[675,724],[829,724],[829,860],[777,860],[777,1236],[885,1236],[885,1304],[777,1304],[777,1460],[675,1460]],name='首层主要公共通道')
core('Cmidlift','C',(778,1305,885,1351),'中部交通核')
add('Cemhall','C','急诊大厅','hall',[[185,1352],[288,1352],[288,1532],[674,1532],[674,1565],[185,1565]],'emergency','open_space')
c('Csmallpass','C',(289,1352,450,1372),'emergency','急诊大厅内通道')
add('Creg','C','挂号收费','registration',(289,1373,328,1500),'emergency')
add('Cinfusion','C','输液中心','treatment',[[329,1373],[450,1373],[450,1424],[442,1424],[442,1481],[486,1481],[486,1531],[329,1531]],'emergency')
u('Cprep','C',(451,1373,486,1424),['输液准备室','治疗准备室'],'输液中心与护士站之间的小房间',scope='emergency',level='room')
add('Cnurse2','C','护士站','nurse_station',(443,1425,492,1480),'emergency','semi_open_space')
add('Cobs','C','留观室','observation',[[487,1352],[674,1352],[674,1531],[487,1531],[487,1481],[493,1481],[493,1424],[487,1424]],'emergency')
core('Cexternalstair','C',(675,1352,720,1531),'留观室外侧楼梯',scope='emergency')
core('Csouthcore','C',(185,1566,278,1684),scope='emergency')
add('Cpharm','C','急诊药房','pharmacy',(296,1566,430,1684),'emergency')
u('Csouthrooms','C',(431,1566,674,1684),['挂号收费','门诊服务用房'],'临门诊大厅的一排房间；图例4标在该排外侧',scope='ordinary_outpatient')

# D: 影像/放射，明确图例覆盖的房间组按科室功能块记录，不猜各机房名称。
core('Dcore','D',(777,860,834,987),scope='medical_technology')
c('Dnpass','D',(835,860,1424,899),'medical_technology','影像中心北侧通道')
add('Dreg1','D','登记接口','service',(879,900,912,974),'medical_technology','semi_open_space')
add('Dimaging','D','影像中心','imaging',(913,900,1399,974),'medical_technology')
c('Dmidpass','D',[[835,900],[878,900],[878,975],[1400,975],[1400,900],[1424,900],[1424,1014],[835,1014]],'medical_technology','影像中心通道')
add('Dreg2','D','登记接口','service',(879,1015,912,1085),'medical_technology','semi_open_space')
add('Drad','D','放射科','imaging',(913,1015,1399,1127),'medical_technology')
c('Dradpass','D',[[777,1015],[878,1015],[878,1086],[912,1086],[912,1148],[777,1148]],'medical_technology','放射科通道')
c('Dendpass','D',[[1400,1015],[1424,1015],[1424,1149],[913,1149],[913,1128],[1400,1128]],'medical_technology','放射科南侧通道')
u('D01','D',(777,1150,886,1199),['医技辅助用房','候诊用房'],'放射科通道南端独立房间',scope='medical_technology',level='room')
u('D02','D',(887,1150,1320,1239),['影像检查配套区','诊疗用房组'],'影像区南侧连续房间；未逐间标设备名称',scope='medical_technology')
u('D03','D',(1340,1150,1424,1203),['卫生间','医技辅助用房'],'东端小隔间组，邻公共通道',scope='medical_technology')
core('Dlift','D',(777,1200,886,1239),'医技区电梯组',scope='medical_technology')
c('Deastpass','D',[[1321,1150],[1339,1150],[1339,1204],[1429,1204],[1429,1239],[1321,1239]],'medical_technology','医技区东端通道')
add('Dgreen','D','医技与超声间绿化庭院','landscape',(887,1240,1320,1351),level='landscape')

# E: 超声/药房片区，图例16覆盖连续房间组与科室内通道。
core('Ecore','E',(1340,1240,1374,1295),'东侧电梯',scope='medical_technology')
u('E01','E',[[1375,1240],[1429,1240],[1429,1350],[1340,1350],[1340,1296],[1375,1296]],['医技辅助用房','交通核配套区'],'电梯旁含小隔间与连接空间',scope='medical_technology')
c('Eeastern','E',(1321,1240,1339,1685),'medical_technology','东侧医技后勤通道')
u('E02','E',(1340,1351,1429,1460),['卫生间','医技辅助用房'],'东侧通道旁成组小隔间',scope='medical_technology')
u('E03','E',(1340,1461,1429,1685),['医技辅助用房','办公用房组'],'沿东侧连续布置的无名房间',scope='medical_technology',confidence='低')
add('Enurse','E','护士站','nurse_station',(850,1352,891,1410),'medical_technology','semi_open_space')
add('Eultra','E','超声中心','examination',[[777,1352],[849,1352],[849,1411],[892,1411],[892,1352],[1320,1352],[1320,1532],[924,1532],[924,1460],[777,1460]],'medical_technology')
add('Ewait','E','候药区','hall',[[721,1461],[923,1461],[923,1685],[887,1685],[887,1630],[777,1630],[777,1685],[675,1685],[675,1532],[721,1532]],'ordinary_outpatient','open_space')
add('Echpharm','E','门诊中药房','pharmacy',(924,1533,1320,1599),'ordinary_outpatient')
add('Ewestpharm','E','门诊西药房','pharmacy',(924,1600,1278,1685),'ordinary_outpatient')
u('E04','E',(1279,1600,1320,1685),['药房配套用房','库房'],'西药房东侧狭长隔间',scope='ordinary_outpatient',level='room')
u('E05','E',(777,1631,886,1685),['便民服务区','导诊服务区'],'候药区南侧围合服务小间',scope='ordinary_outpatient',level='room')

# F: 入口大厅及儿科。
u('F01','F',(337,1686,413,1737),['门诊服务用房','挂号收费配套用房'],'门诊大厅西北角独立小房间',scope='ordinary_outpatient',level='room')
add('Fgreen','F','门诊与儿科间绿化庭院','landscape',[[777,1686],[1320,1686],[1320,1908],[859,1908],[859,1794],[777,1794]],level='landscape')
u('F02','F',(777,1795,858,1908),['卫生间','门诊服务用房'],'绿化庭院西南角有两组小隔间',scope='ordinary_outpatient')
eye=[[337,1764],[379,1764],[441,1824],[421,1848],[337,1780]]
add('Foptics','F','配镜中心','retail_service',eye,'ordinary_outpatient')
guide=[[565,1796],[654,1847],[642,1867],[554,1816]]
add('Fguide','F','导诊／咨询','triage',guide,'ordinary_outpatient','semi_open_space')
vest=[[455,1882],[500,1910],[550,1936],[627,1963],[613,2010],[560,1988],[500,1960],[438,1927]]
add('Fvest','F','门诊主入口门斗','entrance',vest,'ordinary_outpatient')
hall=Polygon([[337,1686],[777,1686],[777,2027],[674,2008],[617,1985],[627,1963],[550,1936],[500,1910],[455,1882],[421,1848],[441,1824],[379,1764],[337,1764]])
hall=hall.difference(box(337,1686,413,1737)).difference(Polygon(eye)).difference(Polygon(guide))
# 将岛式咨询台两侧开放大厅拆成两个连续节点，避免保存带孔多边形。
parts=split(hall,LineString([(300,1660),(800,1948)]))
for i,p in enumerate(sorted(parts.geoms,key=lambda p:p.centroid.y)):
    assert not p.interiors
    add('Fhall'+str(i+1),'F','门诊大厅','hall',list(p.exterior.coords)[:-1],'ordinary_outpatient','open_space')
core('FpedsNE','F',(1210,1909,1320,2000),'儿科东侧交通核',scope='ordinary_outpatient')
add('Fpeds','F','儿科门诊','consultation',[[777,1909],[1209,1909],[1209,2001],[1320,2001],[1320,2095],[835,2095],[835,2013],[777,2013]],'ordinary_outpatient')
core('FpedsSW','F',(777,2014,834,2095),'儿科西侧交通核',scope='ordinary_outpatient')

# 相邻片区优先，片区内自上而下、同排从左到右。
rows.sort(key=lambda s:(s['group'],min(y for x,y in s['polygon']),min(x for x,y in s['polygon'])))
spaces=[]; bykey={}
for i,s in enumerate(rows,1):
    sid=f'S{i:03d}';s['id']=sid;bykey[s['key']]=s
    pts=[[round(2424-y,3),round(x,3)] for x,y in s['polygon']]
    spaces.append(dict(id=sid,name=s['name'],type=s['type'],level=s['level'],scope=s['scope'],polygon_px=pts))
rels=[]
def rel(a,b,t='access'):
    a=bykey[a]['id'];b=bykey[b]['id']
    if not any(r['source']==a and r['target']==b and r['type']==t for r in rels):
        rels.append(dict(id=f'R{len(rels)+1:03d}',source=a,target=b,type=t))
# 只记录图面清楚的开口、连续公共区域、交通核出口及服务窗口。
for a,b in [('Acore','Apass1'),('Apass1','Ameeting'),('Ameeting','Apass2'),('Apass3','spine'),('Bentry','spine'),('Bentry','Bpass'),('Bpass','Blobby'),('Blobby','Blift'),('Bpass','Bcore'),('Bupper','Bfarcore'),('Bupper','Bfarpass'),('Bupper','Bbottom'),('Bpass','Blaundry'),('spine','Cnorthpass'),('Ccore','Cnorthpass'),('Cfirstaid','Cnurse1'),('Cfirstaid','Cshortpass'),('Cshortpass','Crescue'),('Cshortpass','Crescuepass'),('Cemhall','Csmallpass'),('Cemhall','Cinfusion'),('Cobs','Cexternalstair'),('Cemhall','Ewait'),('spine','Cmidlift'),('spine','Eultra'),('spine','Ewait'),('spine','Dcore'),('Dcore','Dnpass'),('Dnpass','Dmidpass'),('Dmidpass','Dradpass'),('Dradpass','Dendpass'),('Dendpass','Deastpass'),('Deastpass','Eeastern'),('Dreg1','Dmidpass'),('Dreg2','Dradpass'),('Eeastern','Ecore'),('Ewait','Fhall1'),('Ewait','Fhall2'),('Fhall1','Fhall2'),('Fhall2','Fvest'),('Fhall2','Fpeds'),('Fpeds','FpedsNE'),('Fpeds','FpedsSW')]:
    rel(a,b)
for a,b in [('Areg','Apass3'),('Creg','Cemhall'),('Cnurse2','Cinfusion'),('Cnurse2','Cobs'),('Dreg1','Dmidpass'),('Dreg2','Dradpass'),('Enurse','Eultra'),('Echpharm','Ewait'),('Ewestpharm','Ewait'),('Fguide','Fhall1'),('Fguide','Fhall2')]: rel(a,b,'service')
# 不把柜台联系自动当作可穿行；登记接口access移除，窗口仅保留service。
rels=[r for r in rels if not(r['type']=='access' and r['source'] in {bykey['Dreg1']['id'],bykey['Dreg2']['id']})]
for i,r in enumerate(rels,1):r['id']=f'R{i:03d}'
for i,(key,name,typ,pos) in enumerate([
    ('Bentry','次出入口','secondary',[726,390]),
    ('Cfirstaid','急救入口','emergency',[185,1082]),
    ('Cemhall','急诊入口','emergency',[185,1456]),
    ('Fvest','门诊主入口','main',[528,1968]),
],1):
    rels.append(dict(id=f'E{i:03d}',source=None,target=bykey[key]['id'],type='entrance',name=name,entrance_type=typ,position_px=[2424-pos[1],pos[0]]))

data=dict(image=dict(file='39_梅州市蕉岭县人民医院_原图.jpg',width=2424,height=3104),spaces=spaces,relations=rels)
(ROOT/'annotation.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
pending=[s for s in rows if s['type']=='unknown']
for i,s in enumerate(pending,1):s['review']=f'{i:02d}'
(TMP/'review_mapping.json').write_text(json.dumps(pending,ensure_ascii=False,indent=2)+'\n')
(TMP/'reading_spaces.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(spaces=len(spaces),pending=len(pending),relations=len(rels),groups={g:sum(s['group']==g for s in pending) for g in 'ABCDEF'}),ensure_ascii=False))
for s in pending:print(s['review'],s['id'],s['key'],' / '.join(s['candidates']))
