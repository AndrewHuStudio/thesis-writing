from sync_paths import P,R,W
import json
from shapely.geometry import Polygon,Point
p=P/'annotation.json';d=json.loads(p.read_text());rels={r['id']:r for r in d['relations']};spaces={s['id']:s for s in d['spaces']}
log={'source':'本图原图逐区人工目视，坐标图A—H；非共墙自动建边','corrections':[],'manual_openings':[],'conceptual':[],'not_required':[]}
# 柜台服务侧、房间实际开门侧及交通核外部连接按原图更正；原R编号保留。
fix={'R075':'S062','R076':'S060','R077':'S076','R080':'S101','R081':'S101','R106':'S112','R111':'S117','R112':'S128','R118':'S145','R119':'S143','R120':'S143','R121':'S143','R141':'S178','R142':'S178','R143':'S178','R144':'S178','R150':'S059','R168':'S007','R169':'S062'}
for rid,target in fix.items():
 r=rels[rid];log['corrections'].append({'relation_id':rid,'source':r['source'],'old_target':r['target'],'target':target,'basis':'原图可见开门侧／连续柜台实际服务侧；见A—H坐标图'})
 r['target']=target
# 办公小走廊与东侧大厅之间为完整实体隔墙，通行应经北端回到大厅。
rels['R162']['type']='shared_wall';log['corrections'].append({'relation_id':'R162','change':'access改为shared_wall','basis':'F图S103/S104共墙连续，无人员开口；两者分别经北端连到S101'})
# 北侧交通核纳入其北端窄前通道，沿用整体交通核节点。
s=spaces['S022'];s['polygon_px']=[[894,797],[1025,797],[1025,1001],[894,1001]]
log['corrections'].append({'space_id':'S022','change':'北边界822延至797','basis':'H图阶梯北侧真实前通道与西侧外门，纳入同一交通核；不细分核心内部'})
next_r=max(int(r['id'][1:]) for r in d['relations'] if r['id'].startswith('R'))+1

def access(a,b):
 global next_r
 for r in rels.values():
  if r['type']=='access' and {r['source'],r['target']}=={a,b}:return r['id']
 rid=f'R{next_r:03}';next_r+=1
 r={'id':rid,'source':a,'target':b,'type':'access'};rels[rid]=r;d['relations'].append(r)
 return rid
# 以下坐标全部为逐处目读门扇/开口所得近似中心，不使用几何中心生成。
points=[]
def point(rid,x,y,kind='door'):
 points.append((rid,x,y,kind))
def pair(a,b,x,y,kind='door'):
 point(access(a,b),x,y,kind)
# A 北侧候诊、挂号收费与治疗区。
pair('S003','S002',1400,266);pair('S003','S002',1400,480)
pair('S004','S007',1718,350)
pair('S005','S007',1730,305)
pair('S006','S004',1698,339);pair('S010','S004',1698,357)
point('R045',1815,405)
point('R046',1440,505);point('R047',1576,505);point('R048',1607,505)
point('R049',1400,608)
# B 西侧医技上段。
for rid,x,y in [('R052',478,1198),('R054',522,1311),('R055',629,1311),('R056',738,1311),('R057',526,1364),('R058',654,1364),('R059',478,1418),('R060',478,1434),('R061',478,1539),('R062',478,1566),('R063',836,1445),('R064',836,1495),('R065',525,1556),('R068',711,1556),('R069',836,1518),('R150',836,1338)]:point(rid,x,y)
point('R053',478,1346,'open_passage')
point('R066',608,1556,'open_passage');point('R067',667,1556,'open_passage')
# C 西侧医技中段。
for rid,x,y in [('R082',478,1661),('R083',478,1680),('R084',478,1742),('R085',478,1800),('R086',523,1676),('R087',629,1676),('R088',739,1676),('R090',524,1728),('R091',713,1728),('R092',740,1728),('R093',478,1882),('R094',523,1974),('R095',712,1974),('R096',739,1974),('R097',478,1982),('R098',478,2042),('R099',523,2030),('R100',654,2030),('R101',836,2068),('R102',836,2086),('R153',836,1998)]:point(rid,x,y)
pair('S078','S074',836,1704)
# D 西侧南段挂号收费及其独立工作人员门。
for rid,x,y in [('R107',478,2158),('R108',478,2218),('R109',478,2278),('R110',478,2353),('R111',545,2331),('R112',992,2414)]:point(rid,x,y)
pair('S124','S117',620,2331);pair('S124','S117',872,2331)
pair('S127','S124',632,2361)
# E 西南诊室及卫生间、交通核。
for rid,x,y in [('R113',478,2472),('R114',478,2545),('R115',478,2610),('R116',478,2672),('R117',478,2734),('R120',1025,2565),('R121',1025,2586),('R119',1025,2686),('R131',478,2799),('R161',510,2799)]:point(rid,x,y)
for rid,x in zip(['R122','R123','R124','R125','R126','R127','R128','R129','R130'],[523,564,626,649,690,752,775,817,879]):point(rid,x,2785)
for rid,x in zip(['R132','R133','R134','R135','R136','R137','R138','R139','R140'],[528,568,627,649,691,752,775,817,878]):point(rid,x,2833)
# F 东侧药房、主交通核和独立大厅。
for rid,x,y in [('R070',1400,1266),('R071',1428,1330),('R072',1584,1330),('R073',1607,1330),('R074',1670,1330),('R075',1855,1343),('R076',1400,1385),('R076',1400,1576),('R077',1400,1620),('R078',1400,1672),('R079',1400,1686),('R080',1495,1727),('R080',1625,1727),('R080',1805,1727),('R081',1870,1727),('R103',1470,1832),('R104',1470,1858),('R105',1470,1920),('R155',1488,1787),('R106',1512,2075)]:point(rid,x,y)
pair('S061','S062',1718,1343)
# G 东南交通核、诊室与走廊。
for x in [1435,1495,1620,1751]:point('R118',x,2670)
point('R156',1765,2707)
for rid,x in [('R141',1552),('R142',1593),('R143',1649),('R144',1684),('R145',1720)]:point(rid,x,2785)
for rid,x in [('R146',1555),('R147',1595),('R148',1683),('R149',1760)]:point(rid,x,2833)
pair('S175','S178',1700,2816)
# H 北侧卫生间与交通核，门洞为墙面真实缺口。
point('R050',1025,915,'open_passage');point('R051',1025,1177)
pair('S023','S019',1025,1013,'open_passage');pair('S024','S019',1025,1107,'open_passage')
# 不定位红点的连续大厅/服务工作区概念联系。
for a,b,reason in [('S003','S002','两处真实门已定位'),('S104','S101','F图大厅北侧无实体分隔，连续通行'),('S161','S177','E图走廊东端连续进入南侧主厅'),('S156','S157','E图护士站东侧边界无完整封闭墙，向东侧主厅开放；布局推断')]:
 rid=access(a,b);log['conceptual'].append({'relation_id':rid,'source':a,'target':b,'basis':reason})
# 独立建筑外门不以室外总节点互连；保留已有E001—E005。
entries=[('E006','S005',[1912,274],'北侧机房外门'),('E007','S022',[894,810],'北侧交通核外门'),('E008','S032',[385,1345],'西侧北交通核外门'),('E009','S087',[385,1876],'西侧中交通核外门'),('E010','S122',[385,2358],'西侧南交通核外门'),('E011','S160',[385,2805],'西南交通核外门'),('E012','S066',[1912,1630],'消防控制室外门')]
for rid,sid,xy,name in entries:d['relations'].append({'id':rid,'source':None,'target':sid,'type':'entrance','name':name,'entrance_type':'building_entrance','position_px':xy})
# 门点先按图面顺序编号，仅初次分配；后续续作不得重排。
points.sort(key=lambda q:(q[2],q[1]))
assert not any(r.get('openings') for r in rels.values())
for i,(rid,x,y,kind) in enumerate(points,1):
 r=rels[rid];o={'id':f'P{i:03}','kind':kind,'position_px':[x,y]};r.setdefault('openings',[]).append(o)
 log['manual_openings'].append({'relation_id':rid,'source':r['source'],'target':r['target'],**o})
log['not_required']=[{'spaces':['S012','S015'],'reason':'北侧护士站、配药内部小间；细部开门不影响治疗及主通行组织，保留空间，本轮不穷尽内部路线'}, {'spaces':['S125','S129'],'reason':'柜台东侧配药、护士站小间；具体内部开门仍需细看，不视为不相通'}]
# 筛查门点与对应两端几何距离，供人工复查，不生成任何门位。
log['point_distance_audit']=[]
for o in log['manual_openings']:
 distances={sid:round(Polygon(spaces[sid]['polygon_px']).distance(Point(o['position_px'])),2) for sid in [o['source'],o['target']]}
 if max(distances.values())>15:log['point_distance_audit'].append({'id':o['id'],'relation':o['relation_id'],'position':o['position_px'],'distances':distances})
(W/'连通与门洞人工记录.json').write_text(json.dumps(log,ensure_ascii=False,indent=2)+'\n')
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'spaces':len(d['spaces']),'relations':len(d['relations']),'openings':len(points),'point_distance_audit':log['point_distance_audit']},ensure_ascii=False))
