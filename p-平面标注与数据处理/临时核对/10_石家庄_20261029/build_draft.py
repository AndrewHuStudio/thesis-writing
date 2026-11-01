from pathlib import Path
import json, hashlib
from PIL import Image
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

ROOT=Path('/Users/hushili/Documents/研究-论文写作/大论文')
OUT=ROOT/'p-写作过程/标注试样/10_石家庄第一医院新建赵卜口院区'
TMP=ROOT/'p-写作过程/临时核对/10_石家庄_20261029'
SOURCE=OUT/'10_石家庄第一医院新建赵卜口院区_原图.jpg'
W,H=Image.open(SOURCE).size
SX,SY=W/1367,H/1824
spaces=[]; meta={}; rels=[]; groups={}; aliases={}

def add(key,geom,name,typ,scope='public_service',level='room',row=None,candidate='',evidence='',confidence='低',side='left'):
    if isinstance(geom,(tuple,list)) and len(geom)==4 and isinstance(geom[0],(int,float)):
        geom=box(*geom)
    elif not isinstance(geom,Polygon):geom=Polygon(geom)
    assert geom.is_valid and geom.area>0,key
    sid=f'S{len(spaces)+1:03d}'
    spaces.append(dict(id=sid,name=name,type=typ,level=level,scope=scope,
        polygon_px=[[round(x*SX,2),round(y*SY,2)] for x,y in list(geom.exterior.coords)[:-1]]))
    aliases[key]=sid
    meta[sid]=dict(key=key,base_polygon=list(geom.exterior.coords)[:-1],row=row,
        candidate=candidate,evidence=evidence,confidence=confidence,side=side)
    if row:groups.setdefault(row,[]).append(sid)
    return sid

def known(key,b,name,typ,**kw):return add(key,b,name,typ,**kw)
def unk(key,b,row,candidate='',evidence='原图文字模糊，尚不能确定完整名称',confidence='低',**kw):
    return add(key,b,'名称未确认','unknown',row=row,candidate=candidate,evidence=evidence,confidence=confidence,**kw)
def corridor(key,base,occupied,name,scope):
    g=base.difference(unary_union([Polygon(meta[aliases[k]]['base_polygon']) for k in occupied]))
    gs=[g] if g.geom_type=='Polygon' else list(g.geoms)
    result=[]
    for i,p in enumerate(sorted(gs,key=lambda x:(x.bounds[1],x.bounds[0]))):
        if p.area<12:continue
        if p.interiors:
            # Split along vertical lines through the holes, keeping each polygon simple.
            from shapely.ops import split
            from shapely.geometry import LineString
            parts=[p]
            for hole in list(p.interiors):
                cutx=Polygon(hole).representative_point().x
                parts=[q for v in parts for q in split(v,LineString([(cutx,p.bounds[1]-1),(cutx,p.bounds[3]+1)])).geoms]
            for j,q in enumerate(parts):
                result.append(known(f'{key}_{i}_{j}',q,name,'corridor',scope=scope,level='open_space'))
        else:result.append(known(key if len(gs)==1 else f'{key}_{i}',p,name,'corridor',scope=scope,level='open_space'))
    return result
def link(a,b,typ='access'):
    a=aliases.get(a,a);b=aliases.get(b,b)
    if a==b:return
    if any(r['type']==typ and {r['source'],r['target']}=={a,b} for r in rels):return
    rels.append(dict(id=f'R{1+sum(r["type"]!="entrance" for r in rels):03d}',source=a,target=b,type=typ))
def entry(key,target,name,pos,kind='external_entrance'):
    rels.append(dict(id=key,source=None,target=aliases.get(target,target),type='entrance',name=name,
        entrance_type=kind,position_px=[round(pos[0]*SX,2),round(pos[1]*SY,2)]))

# A: 西北急诊组团。按相邻房间逐排编号；家具及轴网不作隔墙。
em='emergency'
known('A_wc',(178,321,221,365),'卫生间','toilet',scope=em)
xs=[239,269,300,330,360,390,421,452,483]
cs=['急诊用房／急诊诊室','急诊用房／急诊诊室','内科诊室／外科诊室','外科诊室','五官科急诊／五官科诊室','内科诊室','消毒室','污洗室']
ev=['位于急诊北排，文字不清','同排急诊诊疗用房，文字不清','文字似含“内科”或“外科”','文字似为“外科诊室”','文字似含“五官科”','文字似为“内科诊室”','文字似为“消毒”','文字似为“污洗”']
for i in range(8):unk(f'A_n{i}',(xs[i],321,xs[i+1],365),'A01',cs[i],ev[i],'中' if i>2 else '低',scope=em)
known('A_core',(178,365,221,442),'楼梯交通核','vertical_core',scope=em,level='core_block')
xs=[272,300,331,361,391,421,452,483]
cs=['一般急诊／急诊诊室','专科急诊诊室','心电检查／急诊检查','诊室／治疗室','抢救相关用房','儿科诊室／诊室','处置室／治疗室']
for i in range(7):unk(f'A_i{i}',(xs[i],386,xs[i+1],420),'A02',cs[i],
    '处于急诊诊室内排；局部字形不足以确定全名','低',scope=em)
known('A_northcorr',[(221,321),(239,321),(239,365),(483,365),(483,386),(272,386),(272,420),(483,420),(483,442),(221,442)],'急诊诊疗通道','corridor',scope=em,level='open_space')
unk('A_s0',(272,442,332,485),'A03','急诊检验／急诊检查','多行文字似含检查项目，靠抢救大厅','中',scope=em)
unk('A_s1',(332,442,361,485),'A03','VIP急诊／VIP诊室','字形似“VIP”','中',scope=em)
unk('A_s2',(361,442,421,485),'A03','留观用房／留观病房','文字似含“留观”，邻抢救及候诊','中',scope=em)
known('A_wc2',(421,442,483,463),'卫生间','toilet',scope=em)
known('A_wc3',(421,463,483,485),'卫生间','toilet',scope=em)
known('A_stair2',(421,485,483,522),'楼梯交通核','vertical_core',scope=em,level='core_block')
unk('A_green',(272,485,421,552),'A04','室内绿化庭院／露天采光庭院',
    '绿色底及树形符号，标题似“绿化…庭院”；露天属性未证实','中',scope=em,level='functional_block')
known('A_desk',[(246,483),(253,477),(271,477),(271,485),(258,489),(255,498),(258,510),(271,516),(271,524),(253,523),(246,515)],'急诊服务台','service',scope=em,level='semi_open_space')
g=box(178,442,272,552).difference(Polygon(meta[aliases['A_desk']]['base_polygon']))
# Service desk is an island; split public hall into simple non-overlapping polygons.
from shapely.ops import split
from shapely.geometry import LineString
for j,p in enumerate(split(g,LineString([(259,441),(259,553)])).geoms):known(f'A_hall{j}',p,'抢救大厅','hall',scope=em,level='open_space')
for i,b in enumerate([(178,552,221,596),(178,596,221,636),(178,636,221,674)]):
    unk(f'A_w{i}',b,'A05', ['急诊检查室／设备用房','留观支持用房／库房','处置室／办公室'][i],
        '位于抢救候诊区西侧，原字无法可靠读清','低',scope=em)
known('A_wcorr',(221,552,239,674),'急诊西侧通道','corridor',scope=em,level='open_space')
known('A_wc4',(239,552,271,577),'卫生间','toilet',scope=em)
known('A_wc5',(239,598,271,636),'卫生间','toilet',scope=em)
known('A_wait',[(271,552),(483,552),(483,645),(239,645),(239,636),(271,636),(271,598),(239,598),(239,577),(271,577)],'急诊候诊区','hall',scope=em,level='open_space')
xs=[239,271,310,332,391,422,451,483]
for i in range(7):
    if i==3:known('A_bottom3',(xs[i],645,xs[i+1],674),'护士站','nurse_station',scope=em,level='semi_open_space')
    else:unk(f'A_bottom{i}',(xs[i],645,xs[i+1],674),'A06',
        {0:'处置室／治疗室',1:'输液支持用房／治疗室',2:'配药室／库房',4:'治疗室／处置室',5:'男更衣／男卫生间',6:'女更衣／女卫生间'}[i],
        '位于急诊候诊区南排；末两间可见男、女字样但功能未清','低',scope=em)

# B: 东北影像组团。
im='diagnostic_imaging'
known('B_core',(734,321,858,350),'楼梯电梯交通核','vertical_core',scope=im,level='core_block')
xs=[858,920,950,982,1043,1108]
for i,c in enumerate(['示教室／示范室','阅片室／阅片间','处置室／处理室','主任办公／主任办公室','医护办公／医师办公室']):
    unk(f'B_staff{i}',(xs[i],321,xs[i+1],350),'B01',c,'北排工作人员用房，文字可辨部分字形','中',scope=im,side='right')
unk('B_ne',(1130,321,1171,361),'B01','设备用房／库房','东北角两字不清，无可靠用途依据','低',scope=im,side='right')
known('B_northcorr',(734,350,1108,366),'医护通道','corridor',scope=im,level='open_space')
known('B_ecorr',(1108,321,1130,677),'影像东侧通道','corridor',scope=im,level='open_space')
known('B_e_core',(1130,361,1171,440),'楼梯交通核','vertical_core',scope=im,level='core_block')
unk('B_read',(734,366,762,429),'B02','阅片室','字形似“阅片”，位于候片区西侧','中',scope=im,side='right')
known('B_seat',(762,366,796,443),'候片区','hall',scope=im,level='open_space')
known('B_ctrl1',(796,366,1108,389),'影像控制通道','corridor',scope=im,level='open_space')
xs=[796,858,919,982,1044,1108]
for i in range(5):unk(f'B_scan{i}',(xs[i],389,xs[i+1],447),'B03','CT检查室／X线检查室',
    '有固定影像设备及上侧控制台；具体模态无可读室名','中',scope=im,side='right')
unk('B_lowleft',(734,429,762,477),'B04','影像支持用房','文字不清，处于阅片用房南侧','低',scope=im,side='right')
known('B_wait2',(762,443,796,477),'候片区','hall',scope=im,level='open_space')
xs=[796,827,858,888,919,950,982,1013,1044,1077,1108]
for i in range(10):unk(f'B_small{i}',(xs[i],447,xs[i+1],477),'B04',
    '更衣室／影像辅助间' if i%2 else '暗室／影像辅助间',
    '每台设备南侧配对小间，部分文字似暗室或更衣；用途待核','低',scope=im,side='right')
known('B_ewc',(1130,440,1171,478),'卫生间','toilet',scope=im)
known('B_patient1',(796,477,1108,507),'病人通道','corridor',scope=im,level='open_space')
unk('B_e1',(1130,478,1171,519),'B05','处置室','文字似含“处置”','中',scope=im,side='right')
unk('B_e2',(1130,519,1171,595),'B06','观察室／影像支持用房','多字名称不清，位于东侧设备房排','低',scope=im,side='right')
known('B_desk',(776,557,791,615),'影像服务台','service',scope=im,level='semi_open_space')
g=box(734,477,796,677).difference(box(776,557,791,615))
for j,p in enumerate(split(g,LineString([(783,476),(783,678)])).geoms):known(f'B_waitbig{j}',p,'影像候诊区','hall',scope=im,level='open_space')
for i,b in enumerate([(796,507,827,538),(827,507,858,538),(796,538,827,570),(827,538,858,570)]):
    unk(f'B_aux{i}',b,'B07' if i<2 else 'B08',
        ['登记室／诊疗室','异物检查／影像辅助间','机房','器械／库房'][i],
        ['上排两间字形不清','局部似含“异物”','文字似“机房”','文字似“器械”或“库房”'][i],
        '中' if i>1 else '低',scope=im,side='right')
xs=[858,919,982,1044,1108]
for i in range(4):
    if i==3:known('B_gi',(xs[i],507,xs[i+1],570),'数字胃肠','imaging',scope=im)
    else:unk(f'B_scanm{i}',(xs[i],507,xs[i+1],570),'B07','X线检查室／影像检查室',
        '有影像检查设备，具体名称未能读清','中',scope=im,side='right')
known('B_ctrl2',(796,570,1108,595),'影像控制通道','corridor',scope=im,level='open_space')
xs=[796,827,858,919,982,1044,1108]
for i in range(6):unk(f'B_bottom{i}',(xs[i],595,xs[i+1],648),'B09',
    ['急诊摄影／急诊影像','钼靶／影像辅助间','X线检查室','X线检查室','骨密度检查室／影像检查室','数字摄影／影像检查室'][i],
    '前两间为影像支持小间；后四间有检查设备，室名不清','低' if i<2 else '中',scope=im,side='right')
unk('B_pacs',(1130,595,1171,677),'B10','PACS工作室／影像信息用房','文字似“PACS”，尚未确认','中',scope=im,side='right')
known('B_patient2',(796,648,1108,677),'病人通道','corridor',scope=im,level='open_space')

# C: 西侧中部诊疗组团。
diag='diagnostic_treatment'
unk('C_green',(239,674,424,784),'C01','室内绿化庭院／露天采光庭院',
    '绿色底、树形及庭院字样；是否露天未确认','中',scope=diag,level='functional_block')
known('C_wait',(424,674,483,784),'候诊区','hall',scope=diag,level='open_space')
known('C_wc',(178,784,221,828),'卫生间','toilet',scope=diag)
xs=[239,301,332,361,391,421,452,483]
cs=['放射支持用房／设备房','技师用房／辅助间','急诊检验／检查室','主治办公／办公室','男更衣室','女更衣室','专用更衣／更衣室']
for i in range(7):unk(f'C_n{i}',(xs[i],784,xs[i+1],828),'C02',cs[i],
    '该排文字模糊；后部几间似含更衣字样，均待核','低',scope=diag)
known('C_core',(178,828,221,904),'楼梯交通核','vertical_core',scope=diag,level='core_block')
known('C_ncorr',(239,828,483,853),'诊疗通道','corridor',scope=diag,level='open_space')
unk('C_reg',(300,853,361,905),'C03','放射登记／放射支持用房','两字似“放…”，无设备符号','低',scope=diag)
unk('C_acc1',(361,853,419,905),'C03','直线加速器机房／治疗机房','文字似含“直线…”，有治疗设备符号','中',scope=diag)
unk('C_acc2',(438,853,483,905),'C03','直线加速器机房／治疗机房','与左侧同类设备和机房字形','中',scope=diag)
unk('C_aux1',(419,853,438,905),'C03','控制与设备支持区／治疗辅助区','两台治疗设备之间的窄小支持块；内部隔断精度待核','低',scope=diag,level='functional_block')
known('C_wc2',(419,905,483,926),'卫生间','toilet',scope=diag)
known('C_wc3',(419,926,483,948),'卫生间','toilet',scope=diag)
unk('C_green2',(300,905,419,1016),'C05','室内绿化庭院／露天采光庭院',
    '绿色底及庭院字样，内外属性不能从本图证实','中',scope=diag,level='functional_block')
known('C_core2',(419,948,483,986),'楼梯交通核','vertical_core',scope=diag,level='core_block')
known('C_elev',(419,986,450,1016),'电梯交通核','vertical_core',scope=diag,level='core_block')
unk('C_aux3',(450,986,483,1062),'C06','加速器辅助用房／设备用房','邻治疗机房及交通核，多行字不清','低',scope=diag)
known('C_desk',[(269,965),(278,958),(294,955),(294,963),(282,968),(279,981),(282,993),(294,998),(294,1006),(277,1003),(269,995)],'诊疗服务台','service',scope=diag,level='semi_open_space')
g=Polygon([(221,853),(300,853),(300,1016),(178,1016),(178,904),(221,904)]).difference(Polygon(meta[aliases['C_desk']]['base_polygon']))
for j,p in enumerate(split(g,LineString([(284,852),(284,1017)])).geoms):known(f'C_hall{j}',p,'诊疗大厅','hall',scope=diag,level='open_space')
known('C_wcorr',(221,784,239,853),'诊疗西侧通道','corridor',scope=diag,level='open_space')
xs=[300,330,361,391,419,450]
for i,c in enumerate(['骨科诊室／诊室','儿科／诊室','CT检查／影像检查','放射相关用房／诊室','心电图／检查室']):
    unk(f'C_m{i}',(xs[i],1016,xs[i+1],1062),'C07',c,'南排门向通道；部分字形可辨，仍不足以定名','低',scope=diag)
unk('C_w1',(172,1016,213,1058),'C08','辅助用房／设备用房','西侧独立小间，字样不清','低',scope=diag)
unk('C_w2',(172,1058,213,1137),'C08','放射服务／诊疗服务用房','多字名称不清，无可靠具体用途证据','低',scope=diag)
known('C_corr',(300,1062,483,1098),'诊疗南侧通道','corridor',scope=diag,level='open_space')
known('C_wait2',[(213,1016),(300,1016),(300,1098),(300,1141),(213,1141)],'候诊区','hall',scope=diag,level='open_space')
xs=[300,330,361,391,421,452,483]
for i,c in enumerate(['诊室／治疗室','外科诊室','内科诊室','儿科诊室','专科诊室','门诊辅助用房']):
    unk(f'C_s{i}',(xs[i],1098,xs[i+1],1141),'C09',c,'房间门向北，室名字形不完整','低',scope=diag)

# D: 东中部药房与取药大厅。
ph='outpatient_pharmacy'
known('D_ncorr',(734,677,1108,697),'药房北侧通道','corridor',scope=ph,level='open_space')
unk('D_ph1',(734,697,906,792),'D01','西药房／门诊药房','可见药架，标题似“西药房”','中',scope=ph,level='functional_block',side='right')
known('D_ph2',(935,697,1067,792),'中药房','pharmacy',scope=ph,level='functional_block')
for i,b in enumerate([(906,697,935,753),(906,753,935,792),(1067,697,1108,751),(1067,751,1108,792)]):
    unk(f'D_sup{i}',b,'D02' if i in [0,2] else 'D03',
        ['药房值班室／药房辅助间','药房管理室／药房辅助间','配药分装／药房辅助间','药房管理室／辅助间'][i],
        '夹在药房之间或东侧，文字不完整；不能把位置当作确定名称','低',scope=ph,side='right')
unk('D_ph3',(734,792,906,873),'D04','门诊西药房／西药调剂区','大面积药架，标题似含“门诊…药”','中',scope=ph,level='functional_block',side='right')
unk('D_sup4',(906,792,935,834),'D05','药房辅助用房／药品周转间','药房中间小间，字不清','低',scope=ph,side='right')
unk('D_sup5',(906,834,935,873),'D06','药房辅助用房／药品准备间','药房中间小间，字不清','低',scope=ph,side='right')
unk('D_ph4',(935,792,1067,873),'D04','中药调剂区／中药房','药架及“中药…”字形，末尾文字不清','中',scope=ph,level='functional_block',side='right')
unk('D_sup6',(1067,792,1108,833),'D05','发药支持用房／药房辅助间','东侧小间字形不清','低',scope=ph,side='right')
unk('D_sup7',(1067,833,1108,873),'D06','药房辅助用房','没有足够证据判断具体用途','低',scope=ph,side='right')
known('D_counter',(734,873,1108,911),'发药窗口工作区','pharmacy_counter',scope=ph,level='semi_open_space')
known('D_hall',(734,911,1108,990),'候药大厅','hall',scope=ph,level='open_space')
known('D_ecorr',(1108,677,1130,990),'药房东侧通道','corridor',scope=ph,level='open_space')
unk('D_e0',(1130,697,1171,753),'D02','药品管理／药房支持用房','东侧独立用房，标题不清','低',scope=ph,side='right')
unk('D_e1',(1130,753,1171,793),'D03','药房办公／药房支持用房','字形似含“办公”，完整名称未明','低',scope=ph,side='right')
known('D_wc',(1130,793,1171,833),'卫生间','toilet',scope=ph)
unk('D_e2',(1130,833,1171,860),'D06','设备支持用房／管理用房','文字不清，不能确定用途','低',scope=ph,side='right')
known('D_elev',(1130,860,1171,883),'电梯交通核','vertical_core',scope=ph,level='core_block')
known('D_vest',(1130,883,1171,914),'东侧前室','vestibule',scope=ph)
known('D_stair',(1130,914,1171,990),'楼梯交通核','vertical_core',scope=ph,level='core_block')

# E: 西南与南侧门诊用房。
op='ordinary_outpatient'
known('E_core',(239,1141,310,1190),'楼梯交通核','vertical_core',scope=op,level='core_block')
unk('E_green',(315,1141,417,1220),'E01','室内绿化庭院／露天采光庭院','绿色底及庭院字样，露天属性待确认','中',scope=op,level='functional_block')
known('E_wait',(417,1141,483,1220),'候诊区','hall',scope=op,level='open_space')
xs=[310,352,385,419,457]
for i in range(4):unk(f'E_ped{i}',(xs[i],1220,xs[i+1],1257),'E02',
    '儿科诊室／儿科专用房','四间名称均似以“儿科”开头，后半字形不清','中',scope=op)
known('E_pedcorr',(310,1257,457,1282),'门诊通道','corridor',scope=op,level='open_space')
unk('E_aux0',(310,1282,352,1315),'E03','儿科诊室／儿童检查室','门向南侧，局部似含“儿科”','低',scope=op)
unk('E_aux1',(352,1282,385,1315),'E03','儿童治疗／门诊支持用房','文字不清，邻儿科用房','低',scope=op)
known('E_wc1',(385,1282,402,1315),'卫生间','toilet',scope=op)
known('E_wc2',(402,1282,419,1315),'卫生间','toilet',scope=op)
unk('E_aux2',(419,1282,457,1315),'E03','诊疗用房／办公室','没有足够文字证据','低',scope=op)
known('E_southcorr',(310,1315,457,1337),'门诊南侧通道','corridor',scope=op,level='open_space')
xs=[310,352,385,419,448,483]
for i,c in enumerate(['问诊室／诊疗室','健康咨询／门诊支持用房','健康体检／门诊支持用房','健康咨询／门诊支持用房','医师办公／办公室']):
    unk(f'E_s{i}',(xs[i],1337,xs[i+1],1380),'E04',c,'底排房间文字不清，不能仅凭布局定名','低',scope=op)
known('E_ecorr',(457,1220,483,1337),'门诊连接通道','corridor',scope=op,level='open_space')
known('E_service',[(224,1292),(237,1306),(252,1317),(271,1326),(288,1330),(288,1345),(268,1340),(246,1330),(228,1315)],'门诊服务柜台','service',scope=op,level='semi_open_space')
g=Polygon([(170,1190),(239,1190),(239,1190),(310,1190),(310,1141),(315,1141),(315,1220),(310,1220),(310,1337),(288,1337),(288,1345),(268,1340),(246,1330),(228,1315),(202,1290),(180,1255)]).buffer(0)
g=g.difference(Polygon(meta[aliases['E_service']]['base_polygon']))
for j,p in enumerate(split(g,LineString([(262,1139),(262,1347)])).geoms):known(f'E_hall{j}',p,'门诊大厅','hall',scope=op,level='open_space')

# 南侧附属房排。
unk('E_southcounter',(483,1256,733,1280),'E05','挂号收费柜台／门诊服务柜台',
    '沿大厅设置连续柜台，局部似含挂号字样，具体用途未确认','中',scope=op,level='semi_open_space')
unk('E_n0',(483,1280,523,1316),'E06','门诊用房／办公室','南侧柜台后独立房间，室名不清','低',scope=op)
known('E_nwc1',(523,1280,544,1316),'卫生间','toilet',scope=op)
known('E_nwc2',(544,1280,562,1316),'卫生间','toilet',scope=op)
xs=[562,590,618,647,675]
for i,c in enumerate(['门诊用房／办公室','收费相关用房／财务室','值班／办公室','值班／办公室']):
    unk(f'E_n{i+1}',(xs[i],1280,xs[i+1],1316),'E06',c,'小字不清，暂无可靠完整名称','低',scope=op)
known('E_scorr',(483,1316,675,1340),'南侧后勤通道','corridor',scope=op,level='open_space')
unk('E_s5',(483,1340,562,1380),'E07','门诊管理办公／门诊办公室','文字似含“门诊”，后续不清','中',scope=op)
xs=[562,590,618,647,675]
for i,c in enumerate(['办公室／配套用房','主任办公／办公室','阅览室／资料室','办公室／配套用房']):
    unk(f'E_s{i+6}',(xs[i],1340,xs[i+1],1380),'E07',c,'位于南侧附属用房排，字形不清','低',scope=op)
known('E_vest',(675,1280,733,1302),'南侧入口前室','vestibule',scope=op)
known('E_score',(675,1302,733,1380),'楼梯交通核','vertical_core',scope=op,level='core_block')

# F: 中央大厅、交通核及景观小岛。庭院露天属性不明确时保持 unknown 并暂纳入面积。
unk('F_green1',(565,365,678,643),'F01','室内绿化庭院／露天采光庭院','中央绿色长庭院及树形，内外属性尚未确认','中',level='functional_block',side='right')
known('F_core1',(565,643,678,677),'楼梯电梯交通核','vertical_core',level='core_block')
known('F_tree1',(565,687,678,744),'景观种植池','landscape',level='landscape')
unk('F_green2',(565,750,678,952),'F02','室内绿化庭院／露天采光庭院','中央第二处绿色长庭院，露天属性尚未确认','中',level='functional_block',side='right')
known('F_core2',(565,952,678,985),'电梯交通核','vertical_core',level='core_block')
for i,b in enumerate([(565,997,678,1056),(565,1070,678,1133),(565,1148,678,1213)]):
    known(f'F_tree{i+2}',b,'景观种植池','landscape',level='landscape')
# Central open circulation is explicitly partitioned at garden/core edges rather than recording polygons with holes.
known('F_west',(483,321,565,1256),'中央大厅西侧通道','corridor',level='open_space')
known('F_east',(678,321,734,1256),'中央大厅东侧通道','corridor',level='open_space')
for i,(y1,y2) in enumerate([(321,365),(677,687),(744,750),(985,997),(1056,1070),(1133,1148),(1213,1256)]):
    known(f'F_cross{i}',(565,y1,678,y2),'中央大厅横向通道','corridor',level='open_space')
known('F_easthall',(734,990,1171,1067),'门诊入口大厅','hall',level='open_space')
unk('F_foyer',[(734,1067),(1044,1067),(1016,1174),(976,1249),(921,1292),(850,1318),(780,1332),(734,1334)],
    'F03','门诊入口门厅／室外入口雨棚','弧形入口边界及门符号；室内外范围需要确认','中',level='functional_block',side='right')

# Only readable openings/continuous public passages are encoded. Unrecorded pairs remain unverified.
for i in range(8):link(f'A_n{i}','A_northcorr')
for i in range(7):link(f'A_i{i}','A_northcorr')
for k in ['A_s0','A_s1','A_s2','A_core']:link(k,'A_northcorr')
link('A_hall0','A_hall1');link('A_northcorr','A_hall0');link('A_hall0','A_wcorr');link('A_wcorr','A_wait')
for i in range(3):link(f'A_w{i}','A_wcorr')
for i in range(7):link(f'A_bottom{i}','A_wait')
link('A_wc4','A_wait');link('A_wc5','A_wait');link('A_desk','A_hall0','service')
for i in range(5):link(f'B_staff{i}','B_northcorr')
link('B_core','B_northcorr');link('B_northcorr','B_ecorr');link('B_northcorr','B_ctrl1')
for i in range(5):link(f'B_scan{i}','B_ctrl1')
for i in range(10):link(f'B_small{i}','B_patient1')
link('B_seat','B_wait2');link('B_wait2','B_waitbig0');link('B_waitbig0','B_waitbig1');link('B_waitbig0','B_patient1');link('B_waitbig0','B_patient2')
link('B_patient1','B_ecorr');link('B_patient2','B_ecorr');link('B_ctrl2','B_ecorr');link('B_e_core','B_ecorr')
for k in ['B_e1','B_e2','B_pacs','B_ewc']:link(k,'B_ecorr')
for i in [0,1]:link(f'B_aux{i}','B_patient1')
for i in [2,3]:link(f'B_aux{i}','B_ctrl2')
for i in range(3):link(f'B_scanm{i}','B_ctrl2')
link('B_gi','B_ctrl2')
for i in range(6):link(f'B_bottom{i}','B_patient2')
link('B_desk','B_waitbig0','service')
for i in range(7):link(f'C_n{i}','C_ncorr')
link('C_ncorr','C_wcorr');link('C_core','C_wcorr');link('C_ncorr','C_hall0');link('C_hall0','C_hall1')
link('C_reg','C_hall1');link('C_acc1','C_reg');link('C_desk','C_hall0','service')
for i in range(5):link(f'C_m{i}','C_corr')
for i in range(6):link(f'C_s{i}','C_corr')
link('C_corr','C_wait2');link('C_wait2','C_hall0')
link('D_ph1','D_ncorr');link('D_ph2','D_ncorr');link('D_ncorr','D_ecorr');link('D_hall','D_ecorr')
link('D_counter','D_hall','service');link('D_wc','D_ecorr');link('D_e0','D_ecorr');link('D_e1','D_ecorr');link('D_e2','D_ecorr');link('D_elev','D_vest');link('D_vest','D_ecorr');link('D_vest','D_stair')
for i in range(4):link(f'E_ped{i}','E_pedcorr')
for i in range(3):link(f'E_aux{i}','E_southcorr')
link('E_wc1','E_southcorr');link('E_wc2','E_southcorr');link('E_pedcorr','E_ecorr');link('E_southcorr','E_ecorr')
for i in range(5):link(f'E_s{i}','E_southcorr' if i<4 else 'E_ecorr')
link('E_service','E_hall0','service');link('E_hall0','E_hall1');link('E_hall1','E_pedcorr');link('E_core','E_hall0')
for i in range(5):link(f'E_n{i}','E_scorr')
for i in range(5,10):link(f'E_s{i}','E_scorr')
link('E_scorr','E_vest');link('E_vest','E_score');link('E_ecorr','E_scorr')
for i in range(7):link(f'F_cross{i}','F_west');link(f'F_cross{i}','F_east')
for k in ['A_northcorr','A_wait','C_wait','C_ncorr','C_corr','E_wait','E_ecorr']:link(k,'F_west')
for k in ['B_northcorr','B_waitbig0','D_ncorr','D_hall','F_easthall']:link(k,'F_east')
link('F_core1','F_east');link('F_core2','F_east')
# Uncertain courtyard access, machine-room interfaces and entrance canopy connections are intentionally not recorded.
entry('E001','A_northcorr','西北侧入口',(178,378))
entry('E002','A_hall0','抢救入口',(178,496))
entry('E003','C_hall0','西侧中部入口',(178,957))
entry('E004','E_hall0','西南侧入口',(181,1305))
known('D_nvest',(1130,677,1171,697),'东侧北入口前室','vestibule',scope=ph)
known('A_ecorr',(421,522,483,552),'急诊东侧通道','corridor',scope=em,level='open_space')
link('D_nvest','D_ecorr');link('A_ecorr','F_west');link('A_ecorr','A_wait')
entry('E005','D_nvest','东侧北入口',(1171,687))
entry('E006','D_vest','东侧中部入口',(1171,896))
entry('E007','F_easthall','东南侧入口',(1171,1047))

# First delivery establishes stable IDs in adjacent blocks: north west/centre/east,
# middle west/centre/east, then south west/centre/entrance. Within each block,
# rooms follow top-to-bottom and left-to-right. No published IDs exist yet.
def block(s):
    k=meta[s['id']]['key']; y=Polygon(meta[s['id']]['base_polygon']).bounds[1]
    if k.startswith('A_'):return 0
    if k.startswith('B_'):return 2
    if k.startswith('C_'):return 3
    if k.startswith('D_'):return 5
    if k.startswith('F_'):
        if k in ['F_easthall','F_foyer']:return 8
        return 1 if y<750 else 4 if y<990 else 7
    if k.startswith('E_'):
        return 7 if k.startswith(('E_southcounter','E_n','E_scorr','E_score','E_vest')) or k in [f'E_s{i}' for i in range(5,10)] else 6
    return 9
ordered=sorted(spaces,key=lambda s:(block(s),Polygon(meta[s['id']]['base_polygon']).bounds[1],Polygon(meta[s['id']]['base_polygon']).bounds[0]))
remap={s['id']:f'S{i+1:03d}' for i,s in enumerate(ordered)}
meta={remap[k]:v for k,v in meta.items()}
groups={k:[remap[x] for x in v] for k,v in groups.items()}
aliases={k:remap[v] for k,v in aliases.items()}
for s in ordered:s['id']=remap[s['id']]
for r in rels:
    if r['source'] is not None:r['source']=remap[r['source']]
    r['target']=remap[r['target']]
spaces=ordered
data=dict(image=dict(file=SOURCE.name,width=W,height=H),spaces=spaces,relations=rels)
(OUT/'annotation.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
(TMP/'draft_metadata.json').write_text(json.dumps(dict(meta=meta,groups=groups,aliases=aliases,
    source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest()),ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(spaces=len(spaces),unknown=sum(s['type']=='unknown' for s in spaces),relations=len(rels),source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest()),ensure_ascii=False))
