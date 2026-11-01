from pathlib import Path
import json, importlib.util
from shapely.geometry import Polygon,box,LineString
from shapely.ops import unary_union
ROOT=Path('/Users/hushili/Documents/研究-论文写作/大论文')
OUT=ROOT/'p-写作过程/标注试样/08_青岛西海岸医疗中心'
TMP=ROOT/'p-写作过程/临时核对/08_青岛西海岸医疗中心_20261029'
spaces=[]; meta={}; keys={}; rels=[]
def add(k,shape,name=None,typ='unknown',level='room',scope='public_service',group='',candidate='',basis='',confidence='低'):
 p=box(*shape) if len(shape)==4 and isinstance(shape[0],(int,float)) else Polygon(shape)
 assert p.is_valid and p.area>0,(k,p)
 assert k not in keys,k
 s={'id':f'S{len(spaces)+1:03d}','name':name or '名称未确认','type':typ,'level':level,'scope':scope,'polygon_px':[[round(x*2,2),round(y*2,2)] for x,y in list(p.exterior.coords)[:-1]]}
 spaces.append(s);keys[k]=s;meta[k]={'group':group,'candidate':candidate,'basis':basis,'confidence':confidence};return p

def unknown(k,b,c,basis,group,scope='public_service',level='room',confidence='低'):
 return add(k,b,scope=scope,level=level,group=group,candidate=c,basis=basis,confidence=confidence)
def known(k,b,n,t,group,scope='public_service',level='room'):
 return add(k,b,n,t,level,scope,group)
def access(a,b):
 if a==b:return
 pair=tuple(sorted([keys[a]['id'],keys[b]['id']]))
 if any(r['type']=='access' and tuple(sorted([r['source'],r['target']]))==pair for r in rels):return
 rels.append({'id':f'R{len(rels)+1:03d}','source':keys[a]['id'],'target':keys[b]['id'],'type':'access'})
def entrance(k,n,p,typ):
 rels.append({'id':f'E{1+sum(r["type"]=="entrance" for r in rels):02d}','source':None,'target':keys[k]['id'],'type':'entrance','name':n,'entrance_type':typ,'position_px':[v*2 for v in p]})
def residual(k,outline,children,n,t,group,scope='public_service',level='open_space'):
 p=Polygon(outline) if not isinstance(outline,Polygon) else outline
 subtract=unary_union([Polygon([(x/2,y/2) for x,y in keys[c]['polygon_px']]) for c in children])
 result=p.difference(subtract)
 assert result.geom_type=='Polygon',(k,result.geom_type)
 assert not result.interiors,(k,'has holes')
 return known(k,list(result.exterior.coords)[:-1],n,t,group,scope,level)
# 01 北部药房及出入院服务：邻接房间成组编号。
g='A 北部大空间与出入院服务'
unknown('a01',(175,218,195,236),'办公／值班室','北部大空间西北角独立小间，字迹不清',g)
unknown('a02',(195,218,223,233),'后勤支持／办公','位于北部大空间西侧小房间组',g)
known('a_lift',(223,218,242,247),'电梯','vertical_core',g,level='core_block')
known('a_wc1',(242,218,273,250),'卫生间','toilet',g)
unknown('a03',(175,236,195,258),'库房／餐饮支持用房','靠近北部大空间的独立小间',g)
unknown('a04',(195,233,223,255),'后勤支持／办公','北侧小间，邻接大空间',g)
known('a_wc2',(175,258,194,286),'卫生间','toilet',g)
known('a_stair',(202,261,298,286),'楼梯及电梯交通核','vertical_core',g,level='core_block')
for k,b in [('a05',(298,261,316,274)),('a06',(298,274,316,286)),('a07',(316,261,331,274)),('a08',(316,274,331,286))]:unknown(k,b,'设备／储物间','紧邻交通核的小间，无可辨设备文字',g)
known('a_core2',(463,218,509,304),'楼梯及电梯交通核','vertical_core',g,level='core_block')
known('a_lifts',(509,207,577,286),'病房楼电梯厅及电梯组','vertical_core',g,level='core_block')
known('a_lift3',(577,229,593,254),'电梯','vertical_core',g,level='core_block')
unknown('a09',(577,254,593,285),'库房／设备间','电梯东侧小间，字迹不清',g)
unknown('a10',(593,229,603,285),'病房楼服务用房','紧邻病房楼电梯厅',g)
# pharmacy fill excludes west rooms and east core; shape hugs children outer edges
unknown('a_ph',[(273,218),(463,218),(463,304),(175,304),(175,286),(331,286),(331,261),(273,261)],'餐厅／药房','原字近似餐厅；大面积柱网与西侧后勤小间相邻，需确认',g,level='functional_block',confidence='中')
unknown('a11',(181,304,222,342),'值班室／办公','出入院服务西端，部分文字近似值班',g,confidence='中')
known('a_wc3',(181,342,222,357),'卫生间','toilet',g)
for i,(x1,x2) in enumerate([(222,246),(246,270),(270,294),(294,318),(318,342),(342,367)],1):
 unknown(f'a_row{i}',(x1,320,x2,355),'办公／出入院服务支持用房','沿出入院服务走道成排房间，房名模糊',g,confidence='中')
unknown('a12',(367,320,388,355),'档案／储物间','狭长小间，内有成排线条',g)
unknown('a13',(388,320,417,355),'工作人员支持用房／设备间','邻接办理柜台，内部线条不明',g)
known('a_admit',(417,320,509,355),'出入院办理','registration',g,scope='inpatient_support',level='semi_open_space')
known('a_toilet',(558,307,610,337),'卫生间','toilet',g)
unknown('a14',(558,337,610,355),'工作人员支持用房','卫生间南侧独立房间',g)
known('a_corr',[(222,304),(509,304),(509,286),(610,286),(610,307),(558,307),(558,355),(509,355),(509,320),(222,320)],'出入院服务通道','corridor',g,level='open_space')
# 02 病房楼大厅及外部大块未知范围
g='B 病房楼大厅与北侧场地'
unknown('n_roof',[(130,305),(181,305),(181,357),(417,357),(417,428),(460,477),(130,477)],'室外绿化／屋面绿化','绿色斜线填充；小字不清，需确认是否室外或屋面',g,level='open_space',confidence='中')
known('n_hall',[(417,355),(610,355),(610,270),(659,270),(683,295),(705,315),(732,341),(763,373),(784,392),(784,406),(755,433),(755,443),(580,443),(580,477),(460,477),(417,428)],'病房楼大厅','hall',g,level='open_space')
# slanted entrance vestibules shown as separated diagonal strips outside hall contour
known('n_entr1',[(659,270),(670,258),(692,280),(683,295)],'病房楼入口门斗（北）','entrance',g)
known('n_entr2',[(732,341),(743,330),(765,352),(753,363)],'病房楼入口门斗（南）','entrance',g)
known('n_entr3',[(774,382),(786,370),(799,383),(787,397)],'病房楼侧门斗','entrance',g)
# 03 东北部电梯、服务小间和输液区
g='C 东北部服务与输液片区';sc='medical_support'
known('b_lifts',(580,443,698,512),'电梯厅与楼梯交通核','vertical_core',g,sc,'core_block')
unknown('b01',(698,443,810,486),'药房／收费服务区','浅黄色功能块，有面向走道开口，房名模糊',g,sc,'functional_block','中')
unknown('b02',(724,486,750,512),'办公／服务用房','北侧服务区内独立小间',g,sc)
unknown('b03',(750,486,810,512),'办公／服务用房','邻接北侧服务区，门朝南',g,sc)
# b01 rectangle and lower b02/03 disjoint; rest circulation assigned separate
unknown('b04',(698,486,724,512),'服务走道／支持区','北侧浅黄区域南侧未读清用途',g,sc,'functional_block')
known('b_corr',(580,512,810,533),'东北服务通道','corridor',g,sc,'open_space')
for i,b in enumerate([(580,533,608,550),(580,550,608,567),(580,567,608,581)],1):unknown(f'b_small{i}',b,'储物／工作人员支持用房','服务区西侧连续小间',g,sc)
unknown('b05',[(608,533),(659,533),(659,581),(658,581),(658,633),(608,633)],'药房／检验工作区','浅黄色大房间，房名似功能区文字',g,sc,'functional_block','中')
unknown('b06',(659,533,706,581),'检验／采血服务区','与前一功能房相邻，原名无法读清',g,sc,'functional_block','中')
unknown('b07',(706,533,756,552),'办公／服务工作间','南侧小间组上排',g,sc)
unknown('b08',(706,552,756,581),'治疗／采血工作间','下排独立房间，有较长文字',g,sc)
unknown('b09',(756,533,780,581),'办公／工作人员支持用房','南侧狭长房间',g,sc)
unknown('b10',(780,533,800,557),'配药／治疗准备','紧邻输液片区的独立小间',g,sc)
unknown('b11',(780,557,800,581),'污物／储物','紧邻输液区的小间',g,sc)
unknown('b12',(800,533,810,581),'工作区／通道','狭长条状区域，边界可辨而文字不清',g,sc)
known('b_wc',(580,581,608,633),'卫生间','toilet',g,sc)
known('b_core',(659,581,706,633),'楼梯交通核','vertical_core',g,sc,'core_block')
# upper blue row across right, near hospital elevators
unknown('b_treat1',[(810,443),(904,443),(904,474),(958,474),(958,488),(843,488),(843,512),(810,512)],'成人输液区／输液候诊','多排输液椅式图符，局部文字近似成人',g,sc,'functional_block','中')
unknown('b13',(904,443,930,474),'值班／观察支持用房','输液区北缘独立小间',g,sc)
known('b_lift',(930,443,950,465),'电梯','vertical_core',g,sc,'core_block')
unknown('b14',(950,453,973,474),'工作人员支持用房','电梯东侧独立小间',g,sc)
known('b_wc2',(973,453,984,512),'卫生间','toilet',g,sc)
known('b_core2',(843,488,973,512),'楼梯、电梯及前室交通核','vertical_core',g,sc,'core_block')
known('b_cross',[(810,512),(995,512),(995,533),(843,533),(843,581),(810,581)],'输液片区通道','corridor',g,sc,'open_space')
unknown('b_treat2',(843,533,995,581),'成人输液区／输液观察区','连续座椅与输液椅符号，文字近似成人',g,sc,'functional_block','中')
# 04 西侧蓝色医技片区
g='D 西侧医技片区';sc='medical_support'
known('w_core1',(173,582,222,631),'楼梯、电梯交通核','vertical_core',g,sc,'core_block')
unknown('w01',(222,582,322,631),'影像检查室／治疗室','北端大间，文字模糊',g,sc,confidence='中')
unknown('w02',(345,582,419,631),'影像检查室／医技用房','北排大间，邻接医技通道',g,sc,confidence='中')
unknown('w03',(419,582,463,631),'影像支持用房／办公','北排最东侧房间',g,sc)
known('w_core2',(463,582,514,631),'楼梯、电梯及前室交通核','vertical_core',g,sc,'core_block')
unknown('w04',(173,631,211,657),'办公／工作人员支持用房','西侧单列第一间，文字不清',g,sc)
unknown('w05',(173,657,211,681),'库房／设备间','西侧单列第二间，无可靠房名',g,sc)
unknown('w06',(173,681,211,734),'检查支持／设备用房','西侧长房间，具体用途不清',g,sc)
# west main row 1
for i,b in enumerate([(222,657,270,705),(270,657,318,705),(318,657,367,705)],1):unknown(f'w_r1_{i}',b,'影像检查室／治疗室','独立检查式大间；具体科目不可辨',g,sc,confidence='中')
unknown('w_r1_4',[(367,657),(391,657),(391,692),(415,692),(415,705),(367,705)],'检查室及控制区','房内有一道分隔线，设备用途不清',g,sc,'functional_block')
unknown('w_r1_5',(391,657,415,692),'控制室／检查支持用房','与左侧检查间相邻',g,sc)
unknown('w_r1_6',(415,657,447,681),'器械／储物间','同排东端上方小间',g,sc)
unknown('w_r1_7',(415,681,447,705),'控制室／值班','同排东端下方小间',g,sc)
known('w_corr1',[(222,631),(322,631),(322,582),(345,582),(345,631),(447,631),(447,657),(222,657)],'医技北侧通道','corridor',g,sc,'open_space')
known('w_wait1',(222,705,447,734),'医技候诊通道（北）','corridor',g,sc,'open_space')
unknown('w07',(173,734,211,747),'设备间／工作人员支持用房','西侧狭长小间，无可靠房名',g,sc)
known('w_wc1',(173,747,211,774),'卫生间','toilet',g,sc)
for i,b in enumerate([(222,734,270,784),(270,734,318,784),(318,734,367,784),(367,734,415,784)],1):unknown(f'w_r2_{i}',b,'影像检查室','四间连续大房间；设备文字不清',g,sc,confidence='中')
known('w_wc2',(415,734,447,773),'卫生间','toilet',g,sc)
unknown('w08',(194,774,211,797),'办公／工作人员支持用房','西侧交通核东边上方小间',g,sc)
unknown('w09',(194,797,211,822),'办公／库房','西侧交通核东边下方小间',g,sc)
known('w_core3',(173,774,194,833),'楼梯','vertical_core',g,sc,'core_block')
# middle band room polygons preserve angled door recesses as approximate rectangles
for i,b in enumerate([(222,809,270,845),(270,809,318,845),(318,809,367,845),(367,809,415,845)],1):unknown(f'w_r3_{i}',b,'检查／治疗室','成排医技房间，北侧门口有斜角',g,sc,confidence='中')
unknown('w10',(415,773,447,809),'治疗准备／工作人员支持','位于卫生间南侧、通道东端',g,sc)
unknown('w11',(415,809,447,830),'控制室／值班','东端小间上排',g,sc)
unknown('w12',(415,830,447,845),'设备／储物间','东端小间下排',g,sc)
known('w_corr2',(222,784,415,809),'医技工作通道（中北）','corridor',g,sc,'open_space')
known('w_wait2',(222,845,447,871),'医技候诊通道（中）','corridor',g,sc,'open_space')
known('w_wc3',(173,833,211,881),'卫生间','toilet',g,sc)
for i,b in enumerate([(222,871,270,911),(270,871,318,911),(318,871,367,911),(367,871,415,911)],1):unknown(f'w_r4_{i}',b,'检查／治疗室','沿候诊通道排列，原房名不清',g,sc,confidence='中')
known('w_wc4',(415,871,447,911),'卫生间','toilet',g,sc)
unknown('w13',(173,881,211,908),'办公／工作人员支持用房','西侧单列独立房间',g,sc)
unknown('w14',(173,908,211,933),'设备／储物间','西侧楼梯北边，文字不清',g,sc)
known('w_core4',(173,933,211,974),'楼梯','vertical_core',g,sc,'core_block')
known('w_corr3',(222,911,420,933),'医技工作通道（中南）','corridor',g,sc,'open_space')
for i,b in enumerate([(222,933,270,974),(270,933,318,974),(318,933,354,974),(354,933,391,974)],1):unknown(f'w_r5_{i}',b,'影像检查／治疗室','南排医技房间；原文字不清',g,sc,confidence='中')
known('w_wc5',(391,933,420,974),'卫生间','toilet',g,sc)
unknown('w15',(420,911,447,954),'工作人员支持／准备间','卫生间东侧长条房间',g,sc)
unknown('w16',(420,954,447,974),'设备／储物间','南端小间',g,sc)
known('w_corr4',(222,974,447,988),'医技南侧通道','corridor',g,sc,'open_space')
known('w_westcorr',[(211,631),(222,631),(222,988),(173,988),(173,974),(211,974)],'医技西侧通道','corridor',g,sc,'open_space')
known('w_core5',(463,786,514,845),'楼梯及前室交通核','vertical_core',g,sc,'core_block')
# main eastern waiting hall polygon with notches around core
known('w_hall',[(447,631),(514,631),(514,786),(463,786),(463,845),(514,845),(514,1017),(447,1017)],'医技候诊大厅','hall',g,sc,'open_space')
unknown('w17',(415,1017,447,1043),'办公／工作人员支持用房','医技南端楼梯北侧小间',g,sc)
known('w_wc6',(415,1043,447,1091),'卫生间','toilet',g,sc)
unknown('w18',(463,1017,479,1032),'配药／工作人员支持用房','南交通核北侧小间',g,sc)
known('w_wc7',(479,1017,514,1043),'卫生间','toilet',g,sc)
known('w_core6',(463,1043,514,1091),'楼梯、电梯及前室交通核','vertical_core',g,sc,'core_block')
known('w_southhall',[(447,1017),(463,1017),(463,1091),(447,1091)],'医技南侧联络通道','corridor',g,sc,'open_space')
# 05 中央步行系统：空间顺序由北向南、同排左向右
g='E 中央公共交通与院落';sc='public_service'
unknown('c_uppercourt',[(514,477),(580,477),(580,633),(706,633),(706,782),(514,782)],'室外庭院／未标注公共空间','中央白色范围无室内铺地，需确认是否室外',g,sc,'open_space','中')
unknown('c_white',(560,684,634,782),'内庭上空／庭院','白色矩形内有上空类文字，不能确认可步入',g,sc,'open_space','中')
# c_uppercourt overlaps central small rectangle; remove with split to avoid holes
orig=keys['c_uppercourt'];orig['polygon_px']=[[x*2,y*2] for x,y in [(514,477),(580,477),(580,633),(706,633),(706,782),(634,782),(634,684),(560,684),(560,782),(514,782)]]
unknown('c_eastcourt',(843,581,941,684),'内庭院／室外庭院','白色庭院矩形，原字近似内庭院',g,sc,'open_space','中')
# north gallery elevator bank and south escalator cores
unknown('c01',(560,782,581,806),'办公／服务用房','中央电梯组北侧西小间',g,sc)
unknown('c02',(581,782,609,806),'总机／服务工作区','中央电梯组北侧，原名不清',g,sc)
unknown('c03',(609,782,637,806),'办公／服务用房','中央电梯组北侧东小间',g,sc)
known('c_lifts',(560,806,637,838),'中央电梯组','vertical_core',g,sc,'core_block')
known('c_esc1',(560,889,634,916),'自动扶梯交通核（中部）','vertical_core',g,sc,'core_block')
known('c_garden',(560,916,634,1092),'中心绿化','landscape',g,sc,'landscape')
known('c_esc2',(560,1115,634,1168),'自动扶梯交通核（南部）','vertical_core',g,sc,'core_block')
known('c_galleryw',[(514,782),(560,782),(560,1092),(514,1092)],'西侧医疗街','corridor',g,sc,'open_space')
known('c_gallerye',[(637,782),(706,782),(706,1092),(634,1092),(634,838),(637,838)],'东侧医疗街','corridor',g,sc,'open_space')
known('c_mid',(560,838,634,889),'中央公共连廊','hall',g,sc,'open_space')
known('c_lobby',[(514,1092),(750,1092),(750,1190),(800,1248),(800,1317),(514,1317)],'门诊大厅','hall',g,sc,'open_space')
# trim escalator from lobby with two connected partitions without holes
lp=Polygon([(x/2,y/2) for x,y in keys['c_lobby']['polygon_px']]);ep=box(560,1115,634,1168)
part1=lp.intersection(box(0,0,1200,1115));part2=lp.intersection(box(0,1115,560,1168));part3=lp.intersection(box(634,1115,724,1168));part4=lp.intersection(box(0,1168,1200,1640))
keys['c_lobby']['polygon_px']=[[x*2,y*2] for x,y in list(part4.exterior.coords)[:-1]]
known('c_lobbyn',list(part1.exterior.coords)[:-1],'门诊大厅北部','hall',g,sc,'open_space')
known('c_lobbyw',list(part2.exterior.coords)[:-1],'门诊大厅西侧','hall',g,sc,'open_space')
known('c_lobbye',list(part3.exterior.coords)[:-1],'门诊大厅东侧','hall',g,sc,'open_space')
# 06 儿科门诊及大厅
g='F 儿科门诊与儿科大厅';sc='pediatric_outpatient'
known('p_wait',(706,581,810,709),'儿科候诊','hall',g,sc,'open_space')
known('p_link',(810,581,843,782),'儿科联络通道','corridor',g,sc,'open_space')
unknown('p01',(706,709,753,737),'诊室／治疗室','儿科候诊区南排西间',g,sc)
unknown('p02',(753,709,785,737),'护士站／服务工作区','候诊区南排中间，有类似柜台的轮廓',g,sc,'semi_open_space','中')
unknown('p03',(785,709,810,737),'诊室／办公','儿科候诊区南排东间',g,sc)
unknown('p04',(706,737,732,756),'办公／工作人员支持用房','儿科南侧功能块西上小间',g,sc)
unknown('p05',(706,756,732,782),'办公／工作人员支持用房','儿科南侧功能块西下小间',g,sc)
unknown('p06',(732,737,785,782),'诊疗工作区／药房','儿科南侧较大功能房，字迹不明',g,sc,'functional_block','中')
unknown('p07',(785,737,810,759),'诊室／办公','儿科南侧功能块东上间',g,sc)
unknown('p08',(785,759,810,782),'诊室／办公','儿科南侧功能块东下间',g,sc)
# far east outpatient row and side support
known('p_wc',(843,684,866,725),'卫生间','toilet',g,sc)
known('p_core',(866,684,890,725),'楼梯','vertical_core',g,sc,'core_block')
for i,b in enumerate([(890,684,913,725),(913,684,936,725),(936,684,960,725),(960,684,984,725)],1):unknown(f'p_r1_{i}',b,'儿科诊室／治疗室','沿儿科门诊候诊通道连续布置',g,sc,confidence='中')
known('p_corr',(843,725,984,749),'儿科门诊候诊通道','corridor',g,sc,'open_space')
for i,b in enumerate([(843,749,866,782),(866,749,890,782),(890,749,913,782),(913,749,936,782)],1):unknown(f'p_r2_{i}',b,'儿科诊室／治疗室','下排诊疗房间，门朝北',g,sc,confidence='中')
unknown('p_desk',[(936,749),(948,749),(955,757),(955,775),(948,782),(936,782)],'护士站／分诊台','儿科门诊东南端弧形服务台轮廓',g,sc,'semi_open_space','中')
known('p_wc2',(941,649,961,684),'卫生间','toilet',g,sc)
unknown('p09',(961,649,984,684),'二次候诊／治疗室','东侧上方小间，原字不清',g,sc)
unknown('p10',(1017,630,1051,657),'办公／设备间','儿科最东北角房间',g,sc)
known('p_core2',(996,649,1017,698),'楼梯','vertical_core',g,sc,'core_block')
unknown('p11',(996,698,1018,725),'工作人员支持用房','东侧走道旁北排西小间',g,sc)
unknown('p12',(1018,698,1034,725),'设备／储物间','东侧走道旁北排东小间',g,sc)
unknown('p13',(996,725,1018,750),'工作人员支持用房','东侧走道旁南排西小间',g,sc)
unknown('p14',(1018,725,1034,750),'工作人员支持用房','东侧走道旁南排东小间',g,sc)
unknown('p15',(996,750,1034,762),'设备／储物间','东侧狭长小间',g,sc)
known('p_wc3',(996,762,1034,782),'卫生间','toilet',g,sc)
unknown('p16',(1017,782,1034,797),'设备／污物间','儿科东侧最南小间',g,sc)
known('p_sidecorr',[(941,630),(1017,630),(1017,649),(996,649),(996,797),(984,797),(984,649),(941,649)],'儿科东侧走道','corridor',g,sc,'open_space')
known('p_hall',[(810,782),(955,782),(955,749),(984,749),(984,797),(1034,797),(1034,834),(843,834),(843,887),(810,887)],'儿科门厅','hall',g,sc,'open_space')
known('p_core3',(843,834,1034,887),'儿科门厅自动扶梯及楼梯交通核','vertical_core',g,sc,'core_block')
# west of pediatric hall, upper waiting support
unknown('p17',(706,782,724,795),'设备／储物间','中央儿科交通核北侧西小间',g,sc)
unknown('p18',(724,782,740,795),'办公／工作人员支持用房','中央儿科交通核北侧中间',g,sc)
unknown('p19',(740,782,757,795),'工作人员支持用房','中央儿科交通核北侧东小间',g,sc)
known('p_core4',(706,795,757,839),'楼梯及前室交通核','vertical_core',g,sc,'core_block')
unknown('p20',(757,795,785,816),'办公／工作人员支持用房','中央儿科交通核东侧独立房',g,sc)
unknown('p21',[(785,782),(810,782),(810,839),(757,839),(757,816),(785,816)],'服务台／儿科支持工作区','有弧形工作台，具体用途未读清',g,sc,'semi_open_space','中')
known('p_hallwest',(706,839,810,887),'儿科门厅西侧联络区','hall',g,sc,'open_space')
unknown('p22',[(706,887),(746,887),(746,895),(758,895),(758,938),(706,938)],'诊室／治疗室','儿科与急诊交界西侧房间',g,sc)
unknown('p23',[(758,895),(778,895),(797,938),(758,938)],'诊室／治疗室','交界处斜边房间',g,sc)
unknown('p24',[(778,887),(810,887),(810,938),(797,938)],'工作人员支持用房','交界处东侧斜边小间',g,sc)
# 07 急诊ICU及其支持区
g='G 急诊 ICU 与支持片区';sc='emergency'
for i,b in enumerate([(843,887,866,912),(866,887,890,912),(843,912,866,938),(877,912,890,938)],1):unknown(f'icu_small{i}',b,'医护支持／治疗准备','ICU西侧成组小间，原名不清',g,sc)
known('icu_pass',(866,912,877,938),'ICU工作通道','corridor',g,sc,'open_space')
unknown('icu_desk',(843,938,890,960),'护士站／ICU服务台','面向ICU的半开放台面',g,sc,'semi_open_space','中')
known('icu',(890,887,980,960),'急诊ICU','observation',g,sc,'functional_block')
for i,b in enumerate([(996,887,1034,936),(996,936,1034,985)],1):unknown(f'e_resus{i}',b,'抢救室／监护室','床位及周边设备图符，属于急诊片区',g,sc,confidence='中')
known('e_wc',(843,985,866,1000),'卫生间','toilet',g,sc)
unknown('e_support',(843,1000,866,1040),'工作人员支持／处置间','急诊成排床位区西端独立房',g,sc)
unknown('e_beds',(866,985,980,1040),'急诊观察／输液区','连续床椅图符，有帘隔/护理空间',g,sc,'functional_block','中')
unknown('e25',(1017,985,1034,999),'设备／储物间','急诊东侧交通核上方小间',g,sc)
known('e_core',(996,985,1017,1040),'楼梯、电梯交通核','vertical_core',g,sc,'core_block')
unknown('e26',(1017,999,1034,1017),'工作人员支持用房','急诊东侧交通核东上小间',g,sc)
unknown('e27',(1017,1017,1034,1040),'设备／储物间','急诊东侧交通核东下小间',g,sc)
# circulation wrap three open boundary rectangles avoids core+rooms
known('e_corr1',(980,887,996,1040),'急诊东侧工作通道','corridor',g,sc,'open_space')
known('e_corr2',(843,960,980,985),'急诊ICU南侧通道','corridor',g,sc,'open_space')
known('e_corr3',(810,938,843,1092),'急诊西侧联络通道','corridor',g,sc,'open_space')
known('e_corr4',(843,1075,1034,1092),'急诊南侧联络通道','corridor',g,sc,'open_space')
unknown('e_white',(843,1040,1034,1075),'内庭院／露台','急诊南侧白色长条范围标有庭院类字样，需确认室外属性',g,sc,'open_space','中')
# emergency northwest waiting and support
known('e_wait',[(706,938),(810,938),(810,985),(785,985),(785,1007),(743,1007),(729,1027),(706,1027)],'急诊候诊区','hall',g,sc,'open_space')
unknown('e28',(785,985,810,1007),'治疗准备／储物间','急诊候诊区东南角小间',g,sc)
unknown('e29',(757,1007,810,1040),'处置／检查室','候诊区南侧大间',g,sc)
unknown('e30',[(743,1007),(757,1007),(757,1040),(734,1040),(734,1027)],'办公／工作人员支持用房','候诊区南侧西间',g,sc)
unknown('e31',(734,1040,757,1050),'设备／储物间','急诊西部交通核北侧小间',g,sc)
known('e_wc2',(757,1040,810,1092),'卫生间','toilet',g,sc)
known('e_core2',(706,1050,757,1092),'楼梯及前室交通核','vertical_core',g,sc,'core_block')
unknown('e32',(706,1027,734,1050),'医护支持／储物间','急诊西部交通核北侧房',g,sc)
# 08 西南部独立诊疗片区
g='H 西南部诊疗片区';sc='ordinary_outpatient'
known('s_wc',(173,1092,207,1115),'卫生间','toilet',g,sc)
unknown('s01',(173,1115,207,1140),'工作人员支持用房','西南片区西北角独立房',g,sc)
unknown('s02',(222,1092,246,1120),'办公／诊室','北排第一小间',g,sc)
unknown('s03',(246,1092,270,1120),'办公／诊室','北排第二小间',g,sc)
unknown('s04',(270,1092,318,1140),'检查室／诊室','北排较大房间',g,sc)
unknown('s05',(318,1092,415,1116),'工作人员支持区／治疗准备','北排狭长房间',g,sc)
unknown('s06',(415,1092,447,1116),'工作人员支持用房','北排东端小间',g,sc)
for i,b in enumerate([(318,1116,367,1165),(367,1116,391,1165),(391,1116,415,1165),(415,1116,463,1165)],1):unknown(f's_r1_{i}',b,'诊室／治疗室','西南片区北侧下排诊疗用房；原名不清',g,sc,confidence='中')
unknown('s07',(270,1140,318,1165),'检查室／治疗室','北排较大房间南侧独立间',g,sc)
known('s_core',(173,1140,251,1168),'楼梯、电梯交通核','vertical_core',g,sc,'core_block')
unknown('s08',(223,1168,251,1187),'工作人员支持用房','西南核心东侧小间上排',g,sc)
unknown('s09',(223,1187,251,1214),'设备／储物间','西南核心东侧小间下排',g,sc)
unknown('s10',(223,1214,251,1240),'办公／工作人员支持用房','核心东南侧房间',g,sc)
known('s_corehall',(173,1168,223,1240),'西南片区电梯门厅','hall',g,sc,'open_space')
known('s_corrwest',[(207,1092),(222,1092),(222,1120),(270,1120),(270,1240),(251,1240),(251,1140),(207,1140)],'西南片区西侧通道','corridor',g,sc,'open_space')
known('s_corr1',(270,1165,463,1189),'西南片区北侧通道','corridor',g,sc,'open_space')
for i,b in enumerate([(270,1189,318,1229),(318,1189,343,1229),(343,1189,367,1229),(367,1189,415,1240)],1):unknown(f's_r2_{i}',b,'诊室／治疗室','西南片区中部房间组，门朝走道',g,sc,confidence='中')
unknown('s11',(415,1189,440,1207),'设备／准备间','诊疗区东侧小间',g,sc)
unknown('s12',(415,1207,463,1257),'治疗／观察室','内有多张床式图符，具体房名不可辨',g,sc,confidence='中')
unknown('s13',(463,1189,488,1225),'办公／工作人员支持用房','西南片区东侧单列第一间',g,sc)
unknown('s14',(463,1225,488,1243),'诊室／治疗室','西南片区东侧单列第二间',g,sc)
unknown('s15',(463,1243,488,1260),'诊室／治疗室','西南片区东侧单列第三间',g,sc)
unknown('s16',(463,1260,488,1277),'工作人员支持用房','西南片区东侧单列第四间',g,sc)
unknown('s17',(463,1277,488,1295),'工作人员支持用房','西南片区东侧单列第五间',g,sc)
# southeast chair corridor in southwest block
unknown('s_wait',(488,1189,514,1295),'候诊／观察区','狭长空间沿外侧排椅；用途待确认',g,sc,'open_space','中')
unknown('s18',(173,1240,194,1268),'办公／工作人员支持用房','西南片区西边小间上排',g,sc)
unknown('s19',(173,1268,194,1295),'办公／工作人员支持用房','西南片区西边小间下排',g,sc)
unknown('s20',(207,1240,270,1295),'诊室／检查室','西南片区中西部较大房间',g,sc)
unknown('s21',(270,1240,294,1295),'诊疗支持用房','中西部狭长房间',g,sc)
unknown('s22',(294,1257,330,1274),'诊室／工作人员支持用房','中部小房间组北间',g,sc)
known('s_wc2',(294,1274,343,1295),'卫生间','toilet',g,sc)
unknown('s23',(330,1257,343,1274),'设备／储物间','中部小房间组东北小间',g,sc)
unknown('s24',(343,1257,367,1295),'诊室／工作人员支持用房','中部小房间组东间',g,sc)
unknown('s25',(367,1257,415,1295),'检查／治疗室','中部东侧大间',g,sc)
unknown('s26',(415,1257,447,1277),'办公／工作人员支持用房','东侧小间组上间',g,sc)
unknown('s27',(415,1277,447,1295),'办公／工作人员支持用房','东侧小间组下间',g,sc)
unknown('s28',(173,1340,207,1360),'办公／设备间','西南最底部小间',g,sc)
known('s_stair',(173,1295,194,1340),'楼梯','vertical_core',g,sc,'core_block')
for i,(x1,x2) in enumerate([(222,246),(246,270),(270,294),(294,318),(318,343),(343,367),(367,391),(391,415)],1):unknown(f's_r3_{i}',(x1,1312,x2,1340),'诊室／治疗室','最南排连续诊疗小间，门朝北',g,sc,confidence='中')
unknown('s29',(207,1312,222,1340),'储物／工作人员支持用房','最南排西端狭小间',g,sc)
known('s_entryhall',(415,1312,463,1340),'西南诊疗片区门厅','hall',g,sc,'open_space')
known('s_stair2',(463,1312,514,1340),'楼梯及前室交通核','vertical_core',g,sc,'core_block')
unknown('s30',(463,1340,497,1360),'工作人员支持用房','南侧交通核下方西间',g,sc)
unknown('s31',(497,1340,514,1360),'设备／储物间','南侧交通核下方东间',g,sc)
known('s_link1',(194,1240,207,1312),'西南片区西南通道','corridor',g,sc,'open_space')
# replace complex southern linkage with independent polygons (unambiguous circulation only)
known('s_link2',(207,1295,514,1312),'西南片区南侧通道','corridor',g,sc,'open_space')
known('s_link3',[(270,1229),(367,1229),(367,1257),(294,1257),(294,1240),(270,1240)],'西南片区中部通道','corridor',g,sc,'open_space')
# 09 东南急诊留观与门厅
g='I 东南急诊与留观片区';sc='emergency'
known('e_lifts',(724,1115,750,1168),'急诊电梯组','vertical_core',g,sc,'core_block')
unknown('er01',(750,1115,800,1145),'急诊诊疗服务台','急诊西侧半开放柜台，原名不可辨',g,sc,'semi_open_space','中')
unknown('er02',(843,1115,896,1145),'急诊诊疗服务台','急诊东侧对应半开放柜台',g,sc,'semi_open_space','中')
unknown('er03',[(750,1190),(774,1190),(774,1218)],'工作人员支持用房','急诊西南斜边小间',g,sc)
unknown('er04',(774,1190,800,1218),'设备／工作人员支持用房','急诊西南房间组北间',g,sc)
unknown('er05',[(774,1218),(800,1218),(800,1248)],'工作人员支持用房','急诊西南房间组斜边南间',g,sc)
unknown('er06',(843,1190,861,1208),'工作人员支持用房','留观区西南小间组北西间',g,sc)
unknown('er07',(843,1208,861,1224),'工作人员支持用房','留观区西南小间组南西间',g,sc)
unknown('er08',(861,1190,896,1224),'治疗／医护支持用房','留观区西南小间组大间',g,sc)
unknown('er09',(843,1224,896,1248),'护士站／服务工作区','急诊南侧台面，前缘有排椅或柜台图符',g,sc,'semi_open_space','中')
known('er_obs',(896,1092,958,1224),'留观区','observation',g,sc,'functional_block')
unknown('er10',(958,1092,984,1140),'办公／医护支持用房','留观区东侧北间',g,sc)
known('er_wc',(958,1140,984,1190),'卫生间','toilet',g,sc)
unknown('er11',(958,1190,984,1205),'治疗支持／办公','卫生间南侧小间',g,sc)
unknown('er12',(958,1205,984,1224),'工作人员支持用房','留观区东侧中下小间',g,sc)
unknown('er13',(896,1224,927,1248),'工作人员支持用房','留观区南排西间',g,sc)
unknown('er14',(927,1224,958,1248),'工作人员支持用房','留观区南排中间',g,sc)
unknown('er15',(958,1224,984,1248),'工作人员支持用房','留观区南排东间',g,sc)
unknown('er16',(996,1092,1034,1115),'工作人员支持用房','急诊东北角独立间',g,sc)
unknown('er17',(996,1115,1034,1140),'办公／治疗支持','急诊东侧北中间',g,sc)
known('er_core',(996,1140,1017,1190),'楼梯','vertical_core',g,sc,'core_block')
unknown('er18',(1017,1140,1034,1177),'工作人员支持用房','楼梯东侧独立间',g,sc)
unknown('er19',(996,1190,1034,1205),'设备／储物间','东侧楼梯下方狭长间',g,sc)
unknown('er20',(996,1205,1034,1243),'医护休息／工作人员支持','东侧最南房间',g,sc)
known('er_corr',(984,1092,996,1248),'急诊留观工作通道','corridor',g,sc,'open_space')
known('er_hall',[(750,1092),(896,1092),(896,1115),(843,1115),(843,1145),(896,1145),(896,1190),(843,1190),(843,1248),(800,1248),(800,1190),(750,1190),(750,1168),(750,1145),(800,1145),(800,1115),(750,1115)],'急诊诊疗大厅','hall',g,sc,'open_space')
known('er_lobby',[(800,1248),(1034,1248),(1034,1264),(969,1317),(800,1317)],'急诊大厅','hall',g,sc,'open_space')
# 10 南侧门斗与外部明确绿化
g='J 南侧入口与绿化';sc='public_service'
unknown('south01',(560,1317,607,1348),'保安／服务用房','门诊入口西侧小间',g,sc)
known('south_ent1',(607,1317,706,1348),'门诊入口门斗','entrance',g,sc)
unknown('south02',(706,1317,724,1348),'保安／设备间','门诊门斗东侧小间',g,sc)
known('south_core',(724,1317,800,1348),'南侧楼梯交通核','vertical_core',g,sc,'core_block')
known('south_ent2',(800,1317,893,1348),'急诊入口门斗','entrance',g,'emergency')
known('south_green1',[(207,1340),(415,1340),(415,1378),(218,1378),(207,1366)],'西南绿化','landscape',g,sc,'landscape')
known('south_green2',[(514,1317),(560,1317),(560,1348),(607,1348),(607,1378),(514,1378)],'南侧绿化','landscape',g,sc,'landscape')
known('south_green3',[(893,1348),(893,1317),(969,1317),(1034,1264),(1034,1243),(1051,1243),(1051,1378),(905,1378),(893,1366)],'东南绿化','landscape',g,sc,'landscape')
known('east_green1',(1034,657,1051,800),'儿科东侧绿化','landscape',g,sc,'landscape')
known('east_green2',(1034,887,1051,1040),'急诊中部东侧绿化','landscape',g,sc,'landscape')
known('east_green3',(1034,1092,1051,1243),'急诊南部东侧绿化','landscape',g,sc,'landscape')
# only clearly open continuous circulation is connected here; room-door edges remain conservative pending dense review.
for a,b in [('a_corr','a_admit'),('a_corr','a_lifts'),('a_corr','n_hall'),('n_hall','n_entr1'),('n_hall','n_entr2'),('n_hall','n_entr3'),('n_hall','b_lifts'),('b_lifts','b_corr'),('b_corr','b_cross'),('b_cross','p_link'),('p_link','p_wait'),('p_link','p_corr'),('p_corr','p_hall'),('p_corr','p_sidecorr'),('p_hall','p_hallwest'),('w_hall','w_wait1'),('w_hall','w_wait2'),('w_hall','w_corr4'),('w_hall','w_corr1'),('w_corr1','w_westcorr'),('w_wait1','w_westcorr'),('w_wait2','w_westcorr'),('w_corr2','w_westcorr'),('w_corr3','w_westcorr'),('w_corr4','w_westcorr'),('w_hall','w_southhall'),('c_galleryw','c_mid'),('c_gallerye','c_mid'),('c_galleryw','c_lobbyn'),('c_gallerye','c_lobbyn'),('c_lobbyn','c_lobbyw'),('c_lobbyn','c_lobbye'),('c_lobbyw','c_lobby'),('c_lobbye','c_lobby'),('c_lobby','south_ent1'),('er_lobby','south_ent2'),('er_hall','er_lobby'),('er_hall','e_corr3'),('er_corr','er_lobby'),('er_corr','e_corr4'),('e_corr3','e_corr4'),('e_corr3','e_wait'),('e_corr3','e_corr2'),('e_corr1','e_corr2'),('s_corr1','s_corrwest'),('s_corehall','s_link1'),('s_link1','s_link2'),('s_link2','s_entryhall'),('s_entryhall','s_stair2')]:access(a,b)
# direct external interfaces identified by source arrows
entrance('n_entr1','病房楼入口（北）',(678,270),'inpatient')
entrance('n_entr2','病房楼入口（南）',(749,346),'inpatient')
entrance('p_hall','儿科入口',(1034,834),'pediatric')
entrance('south_ent1','门诊入口',(657,1348),'outpatient')
entrance('south_ent2','急诊入口',(846,1348),'emergency')
entrance('s_entryhall','西南诊疗片区入口',(439,1340),'outpatient')
# Dense southwest inspection: one small room and the chair-filled northeast waiting area.
g='H 西南部诊疗片区';sc='southwest_clinical'
unknown('s32',(367,1240,415,1257),'办公／工作人员支持用房','中部东侧、治疗房南边的独立横向小间',g,sc)
known('s_waitnorth',[(447,1092),(514,1092),(514,1189),(488,1189),(488,1165),(463,1165),(463,1116),(447,1116)],'西南片区候诊区','hall',g,sc,'open_space')
known('s_linknorth',(463,1165,488,1189),'西南片区东侧联络通道','corridor',g,sc,'open_space')
access('s_corr1','s_linknorth');access('s_linknorth','s_waitnorth')

# Final circulation inspection: represent the visible pediatric / emergency bridge explicitly.
g='F 儿科门诊与儿科大厅'
known('p_bridge',(810,887,843,938),'儿科南侧联络通道','corridor',g,'pediatric_outpatient','open_space')
access('p_hall','p_bridge');access('p_bridge','e_corr3')
access('s_corrwest','s_core');access('s_core','s_corehall')
# The south edge of the admission desk is a service counter facing the inpatient hall.
rels.append({'id':f'R{len(rels)+1:03d}','source':keys['a_admit']['id'],'target':keys['n_hall']['id'],'type':'service'})

# Refine diagonal interfaces using the drawn vestibule / room polygons; no overlapping area.
def trim(k,others):
 p=Polygon(keys[k]['polygon_px']).difference(unary_union([Polygon(keys[q]['polygon_px']) for q in others]))
 if p.geom_type=='MultiPolygon':
  pieces=sorted(p.geoms,key=lambda q:q.area,reverse=True)
  assert sum(q.area for q in pieces[1:])<50,(k,'large detached pieces')
  p=pieces[0]
 assert p.geom_type=='Polygon' and not p.interiors,(k,p.geom_type)
 keys[k]['polygon_px']=[[round(x,3),round(y,3)] for x,y in list(p.exterior.coords)[:-1]]
trim('n_hall',['n_entr2','n_entr3'])
trim('c_lobby',['er03','er05'])
# Clearly drawn room openings in the west block, all checked in the enlarged source.
for k in ['w01','w02']:access(k,'w_corr1')
access('w03','w_hall')
for i in range(1,4):access(f'w_r1_{i}','w_corr1')
access('w_r1_4','w_wait1')
for i in range(1,5):
 access(f'w_r2_{i}','w_corr2');access(f'w_r3_{i}','w_corr2')
 access(f'w_r4_{i}','w_corr3');access(f'w_r5_{i}','w_corr3')
# Pediatric row doors are visible on the corridor side.
for i in range(1,5):
 access(f'p_r1_{i}','p_corr');access(f'p_r2_{i}','p_corr')
# Review groups follow adjacent drawing zones; cross-boundary questions join their nearest zone.
for k in ['c_uppercourt']:meta[k]['group']='C 东北部服务与输液片区'
meta['c_white']['group']='D 西侧医技片区'
for k in ['c_eastcourt','c01','c02','c03']:meta[k]['group']='F 儿科门诊与儿科大厅'
for k in ['p22','p23','p24']:meta[k]['group']='G 急诊 ICU 与支持片区'
for k in keys:
 if meta[k]['group'].startswith('H '):keys[k]['scope']='southwest_clinical'

# First release ids follow adjacent group / row order. No published stable ids existed before this draft.
old_to_key={v['id']:k for k,v in keys.items()}
ordered_spaces=[]
for group in dict.fromkeys(meta[k]['group'] for k in keys):
 remaining=sorted([k for k in keys if meta[k]['group']==group],key=lambda k:(min(y for x,y in keys[k]['polygon_px']),min(x for x,y in keys[k]['polygon_px'])))
 while remaining:
  y0=min(y for x,y in keys[remaining[0]]['polygon_px'])
  row=[k for k in remaining if min(y for x,y in keys[k]['polygon_px'])<=y0+20]
  remaining=[k for k in remaining if k not in row]
  row_y=max(min(y for x,y in keys[k]['polygon_px']) for k in row)+.1
  def row_x(k):
   cut=Polygon(keys[k]['polygon_px']).intersection(LineString([(0,row_y),(2380,row_y)]))
   return cut.bounds[0] if not cut.is_empty else min(x for x,y in keys[k]['polygon_px'])
  for k in sorted(row,key=row_x):ordered_spaces.append(keys[k])
for i,s in enumerate(ordered_spaces,1):s['id']=f'S{i:03d}'
spaces=ordered_spaces
for r in rels:
 if r['source'] is not None:r['source']=keys[old_to_key[r['source']]]['id']
 r['target']=keys[old_to_key[r['target']]]['id']

# Keep stable ids. Flag relation gaps in MD rather than inventing room doors.
data={'image':{'file':'08_青岛西海岸医疗中心_原图.jpg','width':2380,'height':3280},'spaces':spaces,'relations':rels}
spec=importlib.util.spec_from_file_location('annotation_tools','/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts/annotation_tools.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
mod.normalize(data)
(OUT/'annotation.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
review=[]
for k,s in keys.items():
 if s['type']=='unknown': review.append({'key':k,'sid':s['id'],**meta[k]})
# Group order kept; within each adjacent region top-to-bottom bands, same row left-to-right.
# Use manually assigned rows (top edges within 10 px are one row) to retain spatial continuity.
bygroup={}
for q in review:
 s=keys[q['key']];p=Polygon([(x/2,y/2) for x,y in s['polygon_px']]);q['bounds']=list(p.bounds);bygroup.setdefault(q['group'],[]).append(q)
ordered=[]
for group,items in bygroup.items():
 rem=sorted(items,key=lambda q:(q['bounds'][1],q['bounds'][0]))
 while rem:
  yy=rem[0]['bounds'][1];row=[q for q in rem if q['bounds'][1]<=yy+10];rem=[q for q in rem if q not in row];
  row_y=max(q['bounds'][1] for q in row)*2+.1
  def row_x(q):
   cut=Polygon(keys[q['key']]['polygon_px']).intersection(LineString([(0,row_y),(2380,row_y)]))
   return cut.bounds[0] if not cut.is_empty else q['bounds'][0]*2
  ordered.extend(sorted(row,key=row_x))
for i,q in enumerate(ordered,1):q['number']=f'{i:02d}'
(TMP/'核对对应.json').write_text(json.dumps(ordered,ensure_ascii=False,indent=2)+'\n')
(TMP/'key_to_id.json').write_text(json.dumps({k:s['id'] for k,s in keys.items()},ensure_ascii=False,indent=2)+'\n')
print('spaces',len(spaces),'unknown',len(ordered),'relations',len(rels))
