from pathlib import Path
import json,sys,hashlib
from shapely.geometry import Polygon,box,LineString
from shapely.ops import unary_union,split
ROOT=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理/临时核对/38_梅州市蕉岭县中医医院/历史映射恢复')
TMP=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理/临时核对/38_梅州市蕉岭县中医医院/历史映射恢复')
items=[]
def simple_parts(geom):
 gs=[geom] if geom.geom_type=='Polygon' else [g for g in geom.geoms if g.geom_type=='Polygon']
 out=[]
 while gs:
  g=gs.pop()
  if not g.interiors:out.append(g);continue
  h=Polygon(g.interiors[0]);x=h.representative_point().x
  parts=split(g,LineString([(x,g.bounds[1]-1),(x,g.bounds[3]+1)]))
  assert len(parts.geoms)>1
  gs.extend(parts.geoms)
 return out

def add(key,name,typ,geom,scope,group,level='room',candidate='',basis='',confidence='低'):
 if isinstance(geom,tuple): geom=box(*geom)
 assert geom.is_valid and geom.area>0,key
 items.append(dict(key=key,name=name,type=typ,geom=geom,scope=scope,group=group,level=level,candidate=candidate,basis=basis,confidence=confidence))
 return key
def room(key,b,scope,group,candidate,basis):
 return add(key,'名称未确认','unknown',b,scope,group,candidate=candidate,basis=basis)
def remaining(key,name,bounds,scope,group,typ='corridor',level='open_space'):
 geom=Polygon(bounds) if isinstance(bounds,list) else box(*bounds)
 used=[i['geom'] for i in items if i['geom'].intersects(geom)]
 geom=geom.difference(unary_union(used))
 gs=simple_parts(geom)
 for j,g in enumerate(sorted(gs,key=lambda q:(-q.area,q.centroid.y))):
  if g.area<12: continue
  add(key+('' if j==0 else '_'+str(j+1)),name+('' if j==0 else '（支段）'),typ,g,scope,group,level)
# 主大厅及药房，图例 1、2、3、6；原图坐标在最后统一转换。
add('hall','门诊大厅','hall',Polygon([(279,645),(350,645),(350,1025),(155,1025),(128,1035),(102,980),(86,920),(91,864),(116,780),(165,780),(268,780),(268,710),(279,710)]),'public_service',0,'open_space')
add('main_north_core','门诊大厅上侧电梯组','vertical_core',(221,710,268,780),'public_service',0,'core_block')
add('main_north_wc1','门诊大厅北侧卫生间一','toilet',(165,676,221,744),'public_service',0)
add('main_north_wc2','门诊大厅北侧卫生间二','toilet',(221,676,279,710),'public_service',0)
for k,b in [('hall_north_1',(165,646,196,676)),('hall_north_2',(196,646,252,676)),('hall_north_3',(252,646,279,676))]:
 room(k,b,'public_service',0,'无可靠候选','大厅交通核邻侧小房间，无用途文字')
# 完整放大图可辨认两个电梯旁的小房间；具体用途未标注。
for k,b in [('hall_core_side_1',(165,744,195,780)),('hall_core_side_2',(195,744,221,780))]:
 room(k,b,'public_service',0,'无可靠候选','电梯旁独立房间，图上无功能文字')
vest=next(i for i in items if i['key']=='hall_north_2')
vest.update(name='卫生间前厅',type='vestibule',level='open_space',candidate='',basis='')
room('pharmacy_west_1',(353,713,393,790),'pharmacy',0,'药房工作用房 / 储药用房','位于药房西侧条带，只有隔墙和门口可辨')
room('pharmacy_west_2',(353,790,393,952),'pharmacy',0,'储药用房 / 药房工作用房','位于药房西侧长条空间，未见独立名称')
room('pharmacy_inner',(424,713,511,753),'pharmacy',0,'药房工作用房 / 库房','药房内部独立围合且开向药房')
remaining('pharmacy','药房',(393,713,573,952),'pharmacy',0,'pharmacy','functional_block')
add('waiting','候药大厅','hall',(350,953,573,1025),'public_service',0,'open_space')
add('central_ramp','坡道交通区','corridor',(355,626,573,710),'public_service',0,'functional_block')
# 大厅东侧公共配套条带
for k,b in [('central_1',(612,714,686,747)),('central_2',(612,747,686,780)),('central_3',(612,780,686,815)),('central_4',(605,925,640,978)),('central_5',(605,978,640,1025))]:
 room(k,b,'public_service',0,'无可靠候选','医疗街邻侧独立小房间，无用途文字')
add('central_core','药房东侧交通核','vertical_core',Polygon([(605,815),(686,815),(686,925),(640,925),(640,856),(605,856)]),'public_service',0,'core_block')
add('central_wc1','医疗街北侧卫生间一','toilet',(641,925,686,991),'public_service',0)
add('central_wc2','医疗街北侧卫生间二','toilet',(641,991,686,1025),'public_service',0)
remaining('central_passage','药房东侧公共通道',(574,714,686,1025),'public_service',0)
add('medicalstreet','医疗街','corridor',Polygon([(155,1025),(1000,1025),(1000,1108),(573,1108),(573,1155),(465,1155),(465,1108),(270,1108),(270,1165),(155,1165)]),'public_service',0,'open_space')
add('main_south_core','门诊大厅南侧交通核','vertical_core',(165,1058,270,1165),'public_service',0,'core_block')
# medicalstreet 与 main_south_core 用差集消除重复，保留已画出的整体核。
ms=next(i for i in items if i['key']=='medicalstreet');ms['geom']=ms['geom'].difference(next(i['geom'] for i in items if i['key']=='main_south_core'))
# 急诊、输液片区；内部无名房间逐室保留 unknown。
em='emergency'
for n,b in enumerate([(155,1253,195,1317),(195,1253,234,1317),(234,1253,274,1317)],1):
 room('em_west_'+str(n),b,em,1,'急诊诊室 / 急诊治疗室','急诊急救片区靠外墙房间，无独立用途文字')
add('infusion','输液室','treatment',Polygon([(435,1156),(573,1156),(573,1253),(435,1253),(435,1218),(373,1218),(373,1194),(435,1194)]),em,1,'functional_block')
add('infusion_core','输液室北侧楼梯','vertical_core',(350,1110,464,1155),em,1,'core_block')
for n,b in enumerate([(350,1156,393,1193),(393,1156,435,1193),(373,1218,435,1253),(350,1254,464,1317),(464,1254,510,1317),(510,1254,530,1317),(531,1254,573,1274),(531,1274,573,1295),(531,1295,573,1317)],1):
 room('em_central_'+str(n),b,em,1,'急诊治疗室 / 急诊工作用房','急诊或输液区内围合房间，具体功能未标注')
# 底排按实际隔墙分室，卫生洁具并入所属房间，不凭单个洁具创造房名。
xs=[155,195,234,274,316,349,424,461,500,536,573]
for n,(a,b) in enumerate(zip(xs,xs[1:]),1):
 room('em_south_'+str(n),(a,1359,b,1432),em,1,'急诊诊室 / 急诊治疗室','急诊区底排房间，可见开向公共通道的门')
for n,(a,b) in enumerate([(1110,1146),(1146,1185),(1185,1218),(1218,1254),(1254,1288),(1288,1320)],1):
 room('em_east_'+str(n),(605,a,684,b),em,1,'急诊工作用房 / 治疗用房','急诊与输液东侧房间，无独立名称')
add('em_core','急诊东南侧交通核','vertical_core',(575,1357,685,1432),em,1,'core_block')
remaining('em_public','急诊急救室公共区',[(155,1166),(350,1166),(350,1194),(373,1194),(373,1253),(350,1253),(350,1317),(464,1317),(464,1358),(155,1358)],em,1)
remaining('em_east_passage','输液及急诊东侧通道',(574,1110,685,1357),em,1)
# 发热、儿童发热及肠道门诊片区
fe='fever_outpatient'
for n,b in enumerate([(165,415,210,484),(210,415,245,484),(245,415,281,484),(321,415,356,446),(321,446,356,484),(357,415,395,484),(395,415,430,484),(430,415,465,484),(465,415,500,484),(500,440,539,484),(539,415,578,484)],1):
 candidate='儿童发热诊疗用房 / 发热诊疗用房' if n<7 else '发热或肠道诊疗用房'
 room('fe_north_'+str(n),b,fe,2,candidate,'儿童发热或肠道片区上排房间，仅有片区图例')
add('child_public','儿童发热门诊公共区','corridor',(282,414,320,484),'pediatric_fever_outpatient',2,'open_space')
# 上排有洁具的窄房间仍 unknown，不将整间当卫生间。
for n,b in enumerate([(165,529,210,590),(245,529,281,590),(357,529,430,590),(430,529,539,590),(539,529,577,590),(462,499,500,529),(500,499,539,529),(539,499,578,529)],1):
 room('fe_mid_'+str(n),b,fe,2,'发热诊室 / 发热治疗用房','发热门诊片区独立围合，无房间级文字')
add('fe_wc','发热门诊卫生间','toilet',(165,550,210,590),fe,2) if False else None
# 左端一间可见楼梯踏步，改为交通核。
t=next(i for i in items if i['key']=='fe_mid_1');t.update(name='发热门诊西侧楼梯',type='vertical_core',level='core_block',candidate='',basis='')
add('fe_wc2','发热门诊卫生间','toilet',(165,529,195,549),fe,2) if False else None
add('fe_north_entry','发热门诊北侧入口区','entrance',(500,415,539,440),fe,2,'open_space')
remaining('fe_passage','发热门诊公共区',(165,485,578,645),fe,2)
# 肠道门诊东侧房间
for n,b in enumerate([(613,485,666,525),(666,485,686,525),(613,526,651,551),(651,526,686,551),(613,591,651,612),(651,591,686,612),(613,612,686,650),(613,650,686,683),(613,683,651,713)],1):
 room('intestinal_'+str(n),b,'intestinal_outpatient',2,'肠道诊室 / 肠道门诊工作用房','肠道门诊片区围合房间，无独立名称')
add('intestinal_wc','肠道门诊卫生间','toilet',(651,683,686,713),'intestinal_outpatient',2)
add('fe_core','发热及肠道门诊东侧楼梯','vertical_core',(579,415,687,484),'intestinal_outpatient',2,'core_block')
remaining('intestinal_passage','肠道门诊公共区',[(578,485),(613,485),(613,551),(686,551),(686,590),(613,590),(613,713),(578,713)],'intestinal_outpatient',2)
# 右侧医技楼：上排未标明功能的房间。
mt='medical_technology'
xs=[889,1037,1106,1144,1179,1214,1249,1315,1349,1383,1417]
for n,(a,b) in enumerate(zip(xs,xs[1:]),1):
 room('tech_north_'+str(n),(a,501,b,576),mt,3,'医技检查用房 / 医技工作用房','医技楼北侧独立房间，未标注检查设备或房名')
# 放射影像室片区；不将每一间均当作影像检查室。
im='radiology'
for n,b in enumerate([(889,609,1000,646),(889,646,974,710),(974,646,1000,710),(889,711,1000,790),(889,791,932,851),(932,791,1000,851),(889,852,1000,916),(1040,609,1104,658),(1040,659,1104,711),(1040,712,1104,779),(1040,780,1104,849),(1040,850,1104,916),(1040,917,1072,943),(1072,917,1104,943)],1):
 room('radiology_'+str(n),b,im,3,'影像检查室 / 影像配套用房','图例7放射影像室片区，具体房间名称无文字')
add('tech_west_core','医技西南侧交通核','vertical_core',(889,919,967,1025),mt,3,'core_block')
# 功能检测室两侧小房间
ft='functional_diagnostics'
for side,x1,x2,bands in [('west',1150,1214,[609,642,677,713,749,783,819,869,916,960,1025]),('east',1257,1319,[609,641,676,711,748,783,818,851,885,923])]:
 for n,(a,b) in enumerate(zip(bands,bands[1:]),1):
  room('functional_'+side+'_'+str(n),(x1,a,x2,b),ft,3,'功能检查室 / 检查配套用房','图例8功能检测室片区，多间重复小房间，具体检查种类未标')
# 东侧无名房间与公共设施
for n,b in enumerate([(1353,718,1426,746),(1353,747,1426,782),(1353,783,1426,817),(1353,818,1426,851),(1353,852,1426,885),(1353,886,1426,923)],1):
 room('tech_east_'+str(n),b,mt,3,'医技工作用房 / 检查用房','医技楼东侧独立房间，未见功能文字')
add('tech_ne_core','医技东北侧交通核','vertical_core',(1353,609,1426,716),mt,3,'core_block')
add('tech_se_core','医技东南侧楼梯','vertical_core',(1318,987,1427,1025),mt,3,'core_block')
add('tech_wc1','医技东南侧卫生间一','toilet',(1318,925,1387,987),mt,3)
add('tech_wc2','医技东南侧卫生间二','toilet',(1387,925,1427,987),mt,3)
# 剩余走道以围合范围差集构造；不覆盖院外空白及图面右下斜线建筑。
remaining('tech_north_passage','医技北侧横向通道',(889,577,1426,606),mt,3)
remaining('radiology_passage','放射影像室公共通道',[(1001,607),(1039,607),(1039,944),(1105,944),(1105,607),(1147,607),(1147,1025),(969,1025),(969,918),(1001,918)],im,3)
remaining('functional_passage','功能检测室公共通道',[(1215,607),(1256,607),(1256,924),(1318,924),(1318,607),(1351,607),(1351,925),(1317,925),(1317,1025),(1215,1025)],ft,3)

# 将工作坐标映射回原始竖向图，编号按原图相邻片区组织。
def to_original(x,y):return [round(2444-y*2444/1650,2),round(x*3260/2200,2)]
# 空间号在相邻片区内按原图纵向带分排，同排从左到右。
# 使用原图最小 y 对应工作 x，将近似同排的房间归并，保证不会在左右翼之间跳转。
for it in items:
 assert not it['geom'].interiors,it['key']
 coords=[to_original(x,y) for x,y in it['geom'].exterior.coords[:-1]]
 it['polygon_px']=coords
 p=Polygon(coords);it['orig_geom']=p
# 按组内原图行带组织，先固定编号，再生成核对顺序。
ordered=[]
for group in range(4):
 group_items=[i for i in items if i['group']==group]
 # 先按顶边聚成原图横排，再从左至右。
 bands=[]
 for i in sorted(group_items,key=lambda i:i['orig_geom'].bounds[1]):
  yy=i['orig_geom'].bounds[1]
  b=next((b for b in bands if abs(b[0]-yy)<24),None)
  if b is None: bands.append([yy,[i]])
  else:b[1].append(i)
 for _,row in bands:
  ordered.extend(sorted(row,key=lambda i:i['orig_geom'].bounds[0]))
old_path=TMP/'work_spaces.json'
old=json.loads(old_path.read_text()) if old_path.exists() else []
old_ids={i['key']:i['id'] for i in old}
next_id=max([int(i[1:]) for i in old_ids.values()]+[0])+1
for it in ordered:
 if it['key'] in old_ids:it['id']=old_ids[it['key']]
 else:it['id']=f'S{next_id:03d}';next_id+=1

bykey={i['key']:i for i in ordered}
# 只录能从连续开敞区或清楚开口判断的联系。无名房间的门向需逐一核对后另补。
rels=[]
def rel(a,b,typ='access'):
 if a not in bykey or b not in bykey or a==b:return
 aa,bb=bykey[a]['id'],bykey[b]['id']
 if any(r['source'] in (aa,bb) and r['target'] in (aa,bb) and r['type']==typ for r in rels):return
 rels.append(dict(id=f'R{len(rels)+1:03d}',source=aa,target=bb,type=typ))
for a,b in [('hall','waiting'),('hall','medicalstreet'),('waiting','medicalstreet'),('central_passage','medicalstreet'),('main_south_core','medicalstreet'),('main_north_core','hall'),('central_core','central_passage'),('central_passage','central_wc1'),('central_passage','central_wc2'),('infusion','medicalstreet'),('infusion','em_public'),('em_east_passage','medicalstreet'),('em_public','em_east_passage'),('em_core','em_east_passage'),('infusion_core','medicalstreet'),('fe_passage','child_public'),('intestinal_passage','fe_passage'),('intestinal_passage','central_passage'),('fe_core','intestinal_passage'),('fe_north_entry','fe_passage'),('tech_north_passage','radiology_passage'),('tech_north_passage','functional_passage'),('tech_north_passage','functional_passage'),('radiology_passage','medicalstreet'),('tech_west_core','medicalstreet'),('functional_passage','medicalstreet'),('functional_passage','functional_passage'),('tech_ne_core','functional_passage'),('tech_se_core','functional_passage'),('tech_wc1','functional_passage'),('tech_wc2','functional_passage')]:rel(a,b)
# 以下门口在放大图可见；仅记录概念联系，不存门位或门扇参数。
for n in range(1,11):rel('tech_north_'+str(n),'tech_north_passage')
for n in [1]:rel('radiology_'+str(n),'tech_north_passage')
for a,b in [('radiology_1','radiology_2'),('radiology_2','radiology_3'),('radiology_5','radiology_6')]:rel(a,b)
for n in [4,6,7,8,9,10,11,12,13,14]:rel('radiology_'+str(n),'radiology_passage')
for side,nums in [('west',range(1,11)),('east',range(1,10))]:
 for n in nums:rel('functional_'+side+'_'+str(n),'functional_passage' if side=='east' else 'radiology_passage')
for n in range(1,7):rel('tech_east_'+str(n),'functional_passage')
# 某些连续走道因单环数据结构分为支段，只有边界连续时记录相互可达。
for a in ordered:
 if a['type']!='corridor':continue
 for b in ordered:
  if a['key']>=b['key'] or b['type']!='corridor':continue
  if a['key'].split('_passage')[0]!=b['key'].split('_passage')[0]:continue
  if a['geom'].boundary.intersection(b['geom'].boundary).length>2:rel(a['key'],b['key'])
# 取药窗口只记服务关系。
rel('pharmacy','waiting','service')
rel('pharmacy','pharmacy_inner')
# 明确外墙开口的概念入口，名称为方位描述，不增加外部公共节点。
for n,(name,typ,key,pt) in enumerate([
 ('门诊大厅西侧主入口','main','hall',(91,905)),
 ('医疗街东端入口','public','medicalstreet',(1000,1065)),
 ('医疗街南侧入口','public','medicalstreet',(776,1108)),
 ('儿童发热门诊北侧入口','fever','child_public',(300,414)),
 ('发热门诊北侧入口','fever','fe_north_entry',(518,415)),
 ('肠道门诊东侧入口','intestinal','intestinal_passage',(686,571)),
 ('急诊急救区西侧入口','emergency','em_public',(155,1332)),
 ('急诊东南侧入口','emergency','em_east_passage',(574,1383)),
 ('医技北侧入口','public','tech_north_passage',(889,591)),
 ('放射影像区南侧入口','public','radiology_passage',(977,1025)),
 ('功能检测区南侧入口','public','functional_passage',(1227,1025))],1):
 # 急诊东南开口坐落于交通核边缘，目标采用整体交通核。
 if n==8:key='em_core'
 rels.append(dict(id=f'E{n:02d}',source=None,target=bykey[key]['id'],type='entrance',name=name,entrance_type=typ,position_px=to_original(*pt)))
spaces=[{k:i[k] for k in ['id','name','type','level','scope','polygon_px']} for i in ordered]
data=dict(image=dict(file='38_梅州市蕉岭县中医医院_原图.jpg',width=2444,height=3260),spaces=spaces,relations=rels)
(ROOT/'annotation.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
# 临时核对表保留候选和范围依据，不污染核心 JSON。
review=[]
for i in ordered:
 if i['type']=='unknown':review.append(dict(number=f'{len(review)+1:02d}',id=i['id'],candidate=i['candidate'],basis=i['basis'],confidence=i['confidence'],group=i['group'],work_polygon=list(i['geom'].exterior.coords)[:-1],polygon_px=i['polygon_px']))
(TMP/'review_mapping.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
(TMP/'work_spaces.json').write_text(json.dumps([{k:i[k] for k in ['key','id','name','type','group']}|{'work_polygon':list(i['geom'].exterior.coords)[:-1]} for i in ordered],ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(spaces=len(spaces),pending=len(review),relations=len(rels)),ensure_ascii=False))