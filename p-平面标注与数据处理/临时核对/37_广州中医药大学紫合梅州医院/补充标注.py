from pathlib import Path
import ast, json, hashlib
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union

R = Path(__file__).resolve().parent
P = R.parent.parent / '标注试样' / R.name
D = json.loads((R/'20261107_补充前备份/annotation.json').read_text())
S = {s['id']:s for s in D['spaces']}
def xy(p): return [2484-p[1], p[0]]
def upright(s): return Polygon([(y,2484-x) for x,y in s['polygon_px']])
audit = {'added_spaces':[], 'removed_relations':[], 'relation_evidence':[], 'opening_audit':[]}

# Recover the historical question numbers and candidates without executing old code.
old = ast.parse((R/'历史取证/旧草稿源码_只读.py').read_text())
meta = {}; index = 0
for node in old.body:
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
        call = node.value
        if isinstance(call.func, ast.Name) and call.func.id in ('add','unknown'):
            index += 1
            if call.func.id == 'unknown':
                a = call.args
                meta[f'S{index:03}'] = dict(candidates=ast.literal_eval(a[3]),
                    evidence=ast.literal_eval(a[4]), confidence=ast.literal_eval(a[5]) if len(a)>5 else '低')
order = ['S001','S004','S006','S008','S018','S033','S036','S035','S058','S044','S062','S061','S052','S026','S064','S066','S065','S069','S072','S073','S078']
names = [dict(review_id=f'{i:02}',space_id=sid,status='pending',**meta[sid]) for i,sid in enumerate(order,1)]
names[6].update(candidates=['庭院／采光井','未标用途房间'], evidence='通道围绕的矩形留白；无图例、家具及清晰出入口，功能未定。')
names[10].update(candidates=['庭院／采光井','未标用途房间'], evidence='通道围绕的多边形留白；未见明确功能文字。')
names[13].update(candidates=['休憩庭院','室内休憩大厅'], evidence='中央南侧留白设座椅，与门厅以门分隔；不能仅凭留白确定庭院或大厅。')

def add_space(sid,name,points,reason,scope='public_service'):
    poly = Polygon(points)
    poly = poly.difference(unary_union([upright(s) for s in S.values()]))
    if poly.geom_type != 'Polygon': raise ValueError((sid,poly.geom_type))
    s=dict(id=sid,name=name,type='corridor',level='open_space',scope=scope,
           polygon_px=[xy(p) for p in list(poly.exterior.coords)[:-1]])
    D['spaces'].append(s);S[sid]=s
    audit['added_spaces'].append(dict(space_id=sid,reason=reason))

add_space('S087','西南侧内通道',[(575,1206),(598,1206),(598,1332),(506,1332),(506,1319),(575,1319)],
    '原图专家门诊西侧小房组东、南侧灰色通道，北接药房后场通道。')
add_space('S088','东北侧公共通道',[(2096,570),(2195,570),(2215,632),(2345,660),(2345,705),
    (2310,705),(2310,845),(2291,845),(2291,705),(2171,705),(2171,813),(2141,813),
    (2141,706),(2051,706),(2051,638),(2096,638)],
    '原图儿科门诊东端至急诊的连续灰色公共空间，并沿矩形留白区西、东侧衔接。')
add_space('S089','妇科南侧连接通道',[(1686,842),(1871,842),(1871,735),(1895,735),
    (1895,944),(1871,944),(1871,865),(1686,865)],
    '原图妇科配套房组南侧、输液西侧连续灰色通道，南接放射科内部交通。')
add_space('S090','药房西侧后场通道',[(505,1031),(597,1031),(597,1181),(546,1181),
    (546,1128),(582,1128),(582,1080),(505,1080)],
    '原图药房西侧交通核前的灰色通道，向南接药房后场通道。',scope='ordinary_outpatient')

rels=D['relations']; next_r=56; next_p=1
next(r for r in rels if r['id']=='R035')['source']='S054'
def find(a,b,t='access'):
    return next((r for r in rels if r['type']==t and {r['source'],r['target']}=={a,b}),None)
def remove(rid,reason):
    r=next(r for r in rels if r['id']==rid);rels.remove(r)
    audit['removed_relations'].append(dict(**r,reason=reason))
def access(a,b,points=(),reason='',kind='door'):
    global next_r,next_p
    r=find(a,b)
    if not r:
        r=dict(id=f'R{next_r:03}',source=a,target=b,type='access');next_r+=1;rels.append(r)
    if points:
        r.setdefault('openings',[])
        for p in points:
            o=dict(id=f'P{next_p:03}',kind=kind,position_px=xy(p));next_p+=1;r['openings'].append(o)
            audit['opening_audit'].append(dict(opening_id=o['id'],relation_id=r['id'],
                source=a,target=b,upright_position=list(p),evidence=reason))
    audit['relation_evidence'].append(dict(relation_id=r['id'],source=a,target=b,
        basis='原图可见开口' if points else '布局推断／连续功能空间',reason=reason))
    return r

# Service windows face the waiting hall. They do not imply a door through the counter.
for rid in ['R049','R050']:
    r=next(r for r in rels if r['id']==rid)
    audit['removed_relations'].append(dict(**r,reason='服务窗口位于候药大厅侧，校正其服务对象；关系编号保留。'))
    r['target']='S019'

# The treatment rooms have separate doors to the public route; a common wall is not a passage.
remove('R033','专家门诊北侧先经独立楼梯交通核；未见该空间对的直接开口。')
remove('R034','后场通道与专家门诊之间是诊室组，未见穿越这些小房的直接公共开口。')
remove('R026','留观西侧门通往配套房组S058；公共通行改由北侧急诊走道及南侧新补通道。')
remove('R028','留观南侧交通核东向门通往新补S091，校正原空间对。')
extension=Polygon([(2587,1227),(2660,1110),(2677,1117),(2595,1247),(2587,1247)])
extension=extension.difference(unary_union([upright(s) for sid,s in S.items() if sid!='S084']))
poly=upright(S['S084']).union(extension)
if poly.geom_type!='Polygon': raise ValueError('S084 extension disconnected')
S['S084']['polygon_px']=[xy(p) for p in list(poly.exterior.coords)[:-1]]
audit['added_spaces'].append(dict(space_id='S084',reason='原编号通道补齐多边形留白东侧的连续灰色通行带。'))
add_space('S091','留观南侧公共通道',[(2422,1038),(2607,1038),(2680,1064),(2719,1080),
    (2727,1101),(2677,1117),(2660,1110),(2607,1088),(2453,1088),(2453,1179),(2422,1179)],
    '原图留观南侧、东侧的连续灰色通道，绕过南侧交通核和多边形留白区。')
poly=upright(S['S085']).union(Polygon([(2111,1305),(2138,1305),(2138,1455),(2111,1455)]))
poly=poly.union(Polygon([(2188,1305),(2228,1305),(2228,1358),(2188,1358)]))
S['S085']['polygon_px']=[xy(p) for p in list(poly.exterior.coords)[:-1]]
audit['added_spaces'].append(dict(space_id='S085',reason='补齐卫生间与南端长条房之间通道，以及东南楼梯北侧前室。'))
poly=upright(S['S020']).union(Polygon([(1325,1075),(1375,1075),(1375,1122),(1325,1122)]))
S['S020']['polygon_px']=[xy(p) for p in list(poly.exterior.coords)[:-1]]
audit['added_spaces'].append(dict(space_id='S020',reason='补齐两南侧电梯之间实际连续的中央门厅西半通道。'))
S['S008']['polygon_px']=[xy(p) for p in [(1055,554),(1146,554),(1146,650),(1055,650)]]
poly=upright(S['S019']).difference(unary_union([upright(S['S008']),upright(S['S018'])]))
S['S019']['polygon_px']=[xy(p) for p in list(poly.exterior.coords)[:-1]]

# Manually read approximate doorway centres in the upright reference. JSON remains in JPEG coordinates.
access('S020','S021',reason='同一大厅的概念分区，无实体隔墙，不造门点。')
access('S020','S019',[(1150,760)],'大厅与候药区连续开敞。',kind='open_passage')
access('S020','S022',reason='导诊为半开放柜台，仅记录工作人员可达的概念联系。')
access('S021','S022',reason='导诊为半开放柜台，不以服务窗口生成门点。')
access('S020','S023',reason='交通核整体包含扶梯入口；不把电梯门或扶梯端点当房间间门洞。')
access('S021','S023',reason='交通核东侧扶梯向大厅开放，内部路线不细分。')
access('S020','S024',[(1280,1076)],'西侧电梯前室北向双扇门。')
access('S021','S025',[(1490,1076)],'东侧电梯前室北向门。')
access('S019','S012',[(678,672)],'自助银行朝大厅的门。')
access('S019','S014',[(622,739)],'花店朝大厅的双扇门。')
access('S019','S016',[(567,804)],'便利店朝大厅的门。')
access('S019','S002',reason='电梯直接面向候药大厅；交通核内部电梯门不作P点。')
access('S007','S003',[(809,532)],'卫生间朝南门洞。')
access('S007','S004',[(875,532),(935,532)],'北侧房组朝厅门洞，保留功能块粒度。')
access('S007','S005',[(1022,532)],'北侧交通核南向门。')
access('S019','S007',[(752,586)],'开放办公西侧出入口。')
access('S019','S008',[(1127,650)],'收费东端房组南向门。')
access('S019','S001',reason='西北空白区在斜向端部与大厅衔接，通行边界不清，先保留概念连接。')
access('S001','S010',[(614,573)],'斜向楼梯东南侧开口。',kind='open_passage')
access('S011','S019',reason='商铺东侧经过银行旁连续空隙进入大厅；不补虚构门点。')
access('S013','S011',reason='两商铺共墙无门证据不足，撤回此临时关系。')
# Remove that unsubstantiated temporary access; retain the original shared wall.
tmp=find('S013','S011');remove(tmp['id'],'仅共墙，不增加人员可达关系；商铺外门另作建筑接口。')
access('S017','S018',[(408,860)],'西端楼梯交通核向南侧前室开口。')
access('S018','S019',[(492,905)],'西侧公共入口内侧前室向大厅开口。',kind='open_passage')
access('S019','S045',[(582,932)],'药房西侧卫生间朝候药区北向门。')
access('S021','S028',[(1595,548)],'儿科门诊内走道与中央大厅连续。',kind='open_passage')
access('S021','S030',[(1595,650)],'妇科门诊内走道与中央大厅连续。',kind='open_passage')
access('S021','S032',[(1595,840)],'妇科侧卫生间西向门。')
access('S028','S027',[(1608,532)],'北侧交通核向儿科内走道开门。')
access('S028','S029',reason='电梯直接开向儿科内走道，不单列电梯门。')
access('S028','S088',[(2190,570)],'儿科内走道东端连续衔接公共区。',kind='open_passage')

access('S030','S031',[(1895.5,650)],'妇科走道东端连续进入儿科输液前通道。',kind='open_passage')
access('S031','S034',[(2050.5,755)],'儿科输液东侧门通往成人输液功能块前通道。')
access('S030','S033',[(1815,735)],'妇科南侧配套组北面向内部横向通道开门。')
access('S030','S089',[(1883,735)],'妇科内部走道南延。',kind='open_passage')
access('S033','S089',[(1772,841),(1815,841)],'南侧配套房组朝南门。')
access('S034','S089',[(1896,820)],'成人输液西侧门。')
access('S034','S084',reason='成人输液功能块东端连公共区；边界包含前厅，保留概念关系，不定位不清楚的小门。')
access('S035','S055',[(2030,942)],'输液南侧配套组朝放射科北侧公共横向通道开门。')
access('S089','S055',[(1883,944)],'连接通道连续进入放射科内部交通。',kind='open_passage')
access('S088','S039',[(2345,682)],'东北公共区与急诊走道连续。',kind='open_passage')
access('S088','S084',[(2300,845)],'矩形留白东侧通道南延。',kind='open_passage')
access('S039','S037',[(2367,641)],'急诊北侧综合交通核朝南的门。')
access('S039','S038',[(2480,780)],'卫生间交通核东侧门。')
access('S088','S038',[(2310,815)],'卫生间交通核西侧门通向东北侧公共通道。')
access('S039','S084',[(2301,864)],'急诊南侧走道与公共通道衔接。',kind='open_passage')
access('S039','S040',reason='急诊与住院门厅连续，整体功能边界不对应实体门。')
access('S040','S041',[(2938,880)],'住院门厅与南侧交通核间门。')
access('S039','S042',[(2747,875.5)],'急救区与急诊南侧走道间可见门洞。')
access('S042','S063',reason='急救区南侧经核前室进入交通核；边界间通道短小，不定位内部路线。')
access('S043','S044',reason='值班中心与下方房组未见内部直通，撤回该临时关系。')
tmp=find('S043','S044');remove(tmp['id'],'仅相邻，无直接通行证据。')
access('S057','S058',[(2309.5,982)],'急诊留观西侧门通向配套房组。')
access('S057','S039',[(2490,876)],'留观北侧门通向急诊通道。')
access('S057','S091',[(2600,1037.5)],'留观南侧东端门通往公共通道。')
access('S084','S058',[(2268,970),(2268,1011)],'留观西侧房组朝公共通道门。')
access('S084','S059',reason='电梯面向公共通道，不单列电梯内部开口。')
access('S091','S060',[(2421.5,1091)],'留观南侧交通核东向门。')
access('S084','S061',[(2421,1150)],'留观南侧房组东向门。')
access('S091','S063',[(2706,1075)],'东南公共通道北端接综合交通核前室。',kind='open_passage')
access('S091','S084',[(2437,1088)],'留观南侧通道连续接多边形留白西侧通道。',kind='open_passage')
access('S084','S082',reason='肠道门诊西侧内部走道连接公共区，轮廓未精确贴合局部门扇，保留概念关系。')
access('S084','S083',reason='发热门诊西侧有朝公共通道的入口；内部候诊边界含小间，不定位不清楚的门。')

access('S080','S081',reason='VIP大厅与交通核前室连续；内部电梯门不细分。')
access('S080','S084',[(2452.5,1335)],'VIP大厅东向门。')
access('S046','S053',[(633,1181)],'中药房南侧朝后场通道双扇门。')
access('S047','S053',[(1040,1181),(790,1181)],'西药房南侧朝后场通道双扇门。')
access('S053','S054',[(1154,1194)],'药房后场通道东端门。')
access('S054','S020',[(1229.5,1060)],'西侧通道与中央公共厅连续。',kind='open_passage')
access('S054','S068',[(1154,1227)],'专家门诊北侧楼梯东向门。')
access('S068','S067',[(1100,1244)],'楼梯前室向专家门诊内部交通开放。',kind='open_passage')
access('S054','S067',[(1154,1300),(1154,1370)],'专家门诊东向两处门。')
access('S067','S069',[(920,1385),(996,1385)],'专家门诊南侧房组朝内部走道门。')
access('S069','S070',[(1053,1420)],'南侧卫生间朝专家内部走道门。')
access('S054','S071',[(1154,1485)],'西南楼梯东向门。')
access('S053','S087',[(583,1206)],'后场通道向西南内通道门。')
access('S087','S064',[(575,1225),(575,1285)],'西南小房组朝内通道门。')
access('S087','S065',[(540,1333)],'西南大房北向门。')
access('S053','S090',[(565,1182)],'药房西侧通道与后场通道连续。',kind='open_passage')
access('S090','S050',[(546,1160)],'药房西侧楼梯前室门。')
access('S054','S051',[(1154,1095)],'药房东侧综合交通核东向门。')
access('S053','S052',[(1110,1181)],'药房东侧配套房组南向门。')
access('S020','S048',[(1189,1020)],'药房东侧楼梯核朝中央厅西边缘的门。')
access('S048','S049',[(1153,985)],'卫生间朝交通核前室开门。')
access('S021','S056',[(1555.5,1010)],'放射科西侧交通核朝大厅开门。')
access('S086','S056',[(1595,1160)],'综合交通核南侧朝公共通道门。')
access('S021','S086',[(1535,1035)],'中央大厅向东翼内侧通道连续。',kind='open_passage')
access('S086','S085',[(1595,1220)],'内侧通道与医技南侧通道连续。',kind='open_passage')
access('S086','S074',[(1595,1370)],'南侧卫生间西向门。')
access('S086','S075',[(1595,1470)],'南侧楼梯西向门。')
access('S055','S084',[(2209,1120)],'放射科东侧门。')
access('S055','S085',[(2128,1274)],'放射科南侧朝外通道门。')
access('S085','S076',reason='电梯前室开向南侧通道，不单列电梯内部开口。')
access('S085','S077',[(2111,1407)],'南侧卫生间东向门。')
access('S085','S078',[(2138,1405)],'南端长条房西向门。')
access('S085','S079',reason='东南楼梯北侧前室接南侧通道，内部楼梯入口不细分。')

# Independent exterior doors stay separate interfaces; they are not connected through an outdoor node.
def entrance(eid,target,name,p,typ='public'):
    rels.append(dict(id=eid,source=None,target=target,type='entrance',name=name,
                    entrance_type=typ,position_px=xy(p)))
entrance('E06','S066','西南未定功能区独立入口',(710,1455))
entrance('E07','S040','住院门厅独立入口',(2990,825))
entrance('E08','S043','120值班中心独立入口',(2903,1024),'staff')
entrance('E09','S044','东侧配套房组独立入口',(2870,1100),'staff')
entrance('E10','S013','中部小卖部外侧入口',(460,631))
entrance('E11','S015','南侧小卖部外侧入口',(400,699))
entrance('E12','S080','VIP门诊南侧入口',(2285,1455))
entrance('E13','S085','医技南侧通道入口',(2125,1455))
entrance('E14','S076','南侧电梯前室入口',(2025,1455))
entrance('E15','S026','中央南侧未定空间入口',(1375,1120))
# E15 is internal: use access rather than marking a second external entrance.
rels.pop()
access('S020','S026',[(1350,1121)],'中央南侧留白区北面双扇门；空间功能待确认。')
access('S021','S026',[(1400,1120)],'中央南侧留白区北面东半双扇门；空间功能待确认。')

# Final visual audit: continuous conceptual boundaries have no physical threshold.
# Retain access, but omit dots at these boundaries and at unclear internal core routes.
unclear={(809,532),(1815,735),(2747,875.5),(2421.5,1091),(2209,1120),
         (1595,1370),(1595,1470),(1555.5,1010),(1595,1160)}
clear_core={(1280,1076),(1490,1076),(1022,532),(2367,641),(2480,780),
            (2310,815),(2938,880),(1154,1227),(1154,1095),(1189,1020),(1153,985)}
new_audit=[];number=0
for rel in rels:
    kept=[]
    for opening in rel.get('openings',[]):
        x,y=opening['position_px'];p=(y,2484-x)
        core=any(S[sid]['type']=='vertical_core' for sid in (rel['source'],rel['target']))
        if opening['kind']=='open_passage' or p in unclear or (core and p not in clear_core):
            audit.setdefault('unlocated_connections',[]).append(dict(relation_id=rel['id'],
                position_rejected=list(p),reason='目检后保留概念连接；连续分区或核内路线不作为实体门洞。'))
            continue
        number+=1
        evidence=next(o for o in audit['opening_audit'] if o['opening_id']==opening['id'])
        opening['id']=f'P{number:03}'
        evidence['opening_id']=opening['id'];new_audit.append(evidence);kept.append(opening)
    if kept:rel['openings']=kept
    else:rel.pop('openings',None)
audit['opening_audit']=new_audit
next_p=number+1
next(r for r in rels if r['id']=='E01')['position_px']=xy((1374.5,414))

questions=[
 dict(review_id='K01',source='S066',target='S067',status='pending',
      question='S066是否仅由南侧独立入口进出，还是能直接通往专家门诊S067？',
      reason='S066南侧门清楚；东侧边界符号不能可靠辨为人员门。暂只记录独立入口E06。'),
 dict(review_id='K02',source='S072',target='S085',status='pending',related_spaces=['S073'],
      question='S072、S073这两个厚边界单元是否是可进入的房间；若是，是否由S085进出？',
      reason='两单元外圈较厚、内部有折线，未见可可靠定位的外门；其用途和可达性会改变医技主关系。'),
]
state=dict(name_items=names,connectivity_items=questions,
    checks=dict(connectivity_reviewed=True,visual_reviewed=False),
    scope='科室功能块／主要公共通道与交通核；不继续拆分块内小房',
    historical_mapping_source='2026-10-31 transcript render_review.py: order',
    no_detail_required=['功能块内部小房之间的路线','电梯轿厢门及交通核内部路线',
                        '无证据的小设备间、服务柜台内部小门'],
    audit_file='连通与门洞审计.json')
for s in D['spaces']:
    if s['type']=='courtyard': s['level']='open_space';s.pop('area_ratio',None)
for o in audit['opening_audit']:
    pt=Point(o['upright_position'])
    o['endpoint_boundary_distance_px']={sid:round(upright(S[sid]).boundary.distance(pt),3)
                                      for sid in (o['source'],o['target'])}
(P/'annotation.json').write_text(json.dumps(D,ensure_ascii=False,indent=2)+'\n')
(R/'review_state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
(R/'固定核对映射.json').write_text(json.dumps(names,ensure_ascii=False,indent=2)+'\n')
(R/'连通与门洞审计.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
print('spaces',len(D['spaces']),'relations',len(rels),'openings',next_p-1)
print('endpoint distances > 8:',[o for o in audit['opening_audit'] if max(o['endpoint_boundary_distance_px'].values())>8])
