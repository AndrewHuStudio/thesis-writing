from pathlib import Path
import json,copy
from shapely.geometry import Polygon,Point,box
from shapely.ops import nearest_points
ROOT=Path(__file__).resolve().parent
P=ROOT.parent.parent/'标注试样'/ROOT.name
D=json.loads((ROOT/'20261107_开始续作前备份/annotation.json').read_text())
S={s['id']:s for s in D['spaces']};audit={'geometry_changes':[],'relation_corrections':[],'observed_openings':[],'unlocated_conceptual':[]}
def sid(n):return f'S{n:03d}'
# 原图上急诊下半部公共走道连续，旧轮廓在 y=687.56 处提前结束。
g=Polygon(S['S027']['polygon_px']).union(box(431.03,687.56,493.24,850.56))
assert g.geom_type=='Polygon' and g.is_valid and not g.interiors
S['S027']['polygon_px']=[[round(x,2),round(y,2)] for x,y in list(g.exterior.coords)[:-1]]
audit['geometry_changes'].append({'space':'S027','reason':'原图下排诊室前存在连续公共走道，补足旧轮廓遗漏，沿用原编号','added_polygon_px':[[431.03,687.56],[493.24,687.56],[493.24,850.56],[431.03,850.56]]})
# 逐门复核后纠正医技中排开向功能检测走道的旧关系。
for r in D['relations']:
 if r['id'] in {f'R{x:03d}' for x in range(54,62)}:
  audit['relation_corrections'].append({'before':copy.deepcopy(r),'reason':'门洞实际开向 S126；西侧 S103 一侧为连续隔墙'})
  r['target']='S126'
 if r['id']=='R064':
  audit['relation_corrections'].append({'before':copy.deepcopy(r),'reason':'S136 上侧双扇门开向 S100，非 S126'})
  r['target']='S100'
 if r['id'] in ['R008','R009','R029']:
  audit['relation_corrections'].append({'before':copy.deepcopy(r),'reason':'改为经相邻前厅/空间到达；旧关系跨过了另一个已标注空间'})
  if r['id']=='R008':r['source']='S018'
  if r['id']=='R009':r['source']='S017'
  if r['id']=='R029':r['target']='S139'
 if r['id']=='R020':
  audit['relation_corrections'].append({'before':copy.deepcopy(r),'reason':'S078 入口首先进入 S077，原关系跨过了 S077'})
  r['target']='S077'
# E10 与室内 S002/S103 同一门口重复，归入 R023，不把室内门当外门。
r=next(r for r in D['relations'] if r['id']=='E10')
audit['relation_corrections'].append({'retired':copy.deepcopy(r),'reason':'该门位在 S002 与 S103 室内分界，保留 R023 的室内连接；E10 退役不复用'})
D['relations'].remove(r)
r=next(r for r in D['relations'] if r['id']=='R025')
audit['relation_corrections'].append({'retired':copy.deepcopy(r),'reason':'S126 与 S002 中间隔着放射影像区和房间，原图不支持直接连接；R025退役不复用'})
D['relations'].remove(r)
# S023 是单环差集形成的 1.49px 宽条，不是独立可使用空间，归并入相邻 S025。
sliver=Polygon(S['S023']['polygon_px']);part25=sliver.intersection(box(976.12,948,1100,951));part24=sliver.difference(part25)
merged24=Polygon(S['S024']['polygon_px']).union(part24)
assert merged24.geom_type=='Polygon' and merged24.is_valid and not merged24.interiors
S['S024']['polygon_px']=[[round(x,2),round(y,2)] for x,y in list(merged24.exterior.coords)[:-1]]
merged=Polygon(S['S025']['polygon_px']).union(part25)
assert merged.geom_type=='Polygon' and merged.is_valid and not merged.interiors
S['S025']['polygon_px']=[[round(x,2),round(y,2)] for x,y in list(merged.exterior.coords)[:-1]]
audit['geometry_changes'].append({'retired_space':copy.deepcopy(S['S023']),'merged_into':['S024','S025'],'reason':'旧差集产生1.49px宽边界条，非独立空间；S023退役不复用，名称固定核对映射不受影响'})
D['spaces'].remove(S['S023']);del S['S023']
polys={k:Polygon(s['polygon_px']) for k,s in S.items()}
next_r=max(int(r['id'][1:]) for r in D['relations'] if r['id'].startswith('R'))+1
next_p=1
B={'A':(880,220,1520,1040,2),'B':(300,215,820,1040,2),'C':(1370,220,1850,1040,2),'D':(900,1290,1725,2140,1600/850)}
def relation(a,b):
 global next_r
 a,b=sid(a),sid(b)
 r=next((r for r in D['relations'] if r['type']=='access' and {r['source'],r['target']}=={a,b}),None)
 if r is None:
  r={'id':f'R{next_r:03d}','source':a,'target':b,'type':'access'};D['relations'].append(r);next_r+=1
 return r

def opening(a,b,group,x,y,kind='door'):
 global next_p
 r=relation(a,b);bb=B[group];raw=Point(bb[2]-y/bb[4],bb[1]+x/bb[4]);pa,pb=polys[sid(a)],polys[sid(b)]
 # 只在已目视指定的门洞附近，投影至现有两空间轮廓；不从邻接自动创造门。
 ca=nearest_points(raw,pa.boundary)[1];cb=nearest_points(raw,pb.boundary)[1]
 candidates=[raw,ca,cb,Point((ca.x+cb.x)/2,(ca.y+cb.y)/2)]
 p=min(candidates,key=lambda p:max(pa.distance(p),pb.distance(p))+0.001*p.distance(raw))
 dist=max(pa.distance(p),pb.distance(p));shift=p.distance(raw)
 entry={'relation_id':r['id'],'source':sid(a),'target':sid(b),'crop':group,'crop_position':[x,y],'observed_position_px':[round(raw.x,2),round(raw.y,2)],'position_px':[round(p.x,2),round(p.y,2)],'max_polygon_distance_px':round(dist,3),'projection_shift_px':round(shift,3),'kind':kind}
 if dist>4.5 or shift>10:
  entry['reason']='门洞可见，但旧概念轮廓与实际门洞不吻合；本轮保留概念连接，不虚构位于轮廓上的门位'
  audit['unlocated_conceptual'].append(entry);return
 r.setdefault('openings',[]).append({'id':f'P{next_p:03d}','kind':kind,'position_px':entry['position_px']});entry['opening_id']=f'P{next_p:03d}';next_p+=1
 audit['observed_openings'].append(entry)
# 坐标来自逐幅放大图上可见的门扇和缺口。
A=[(151,1,102,466),(152,1,172,467),(6,7,139,110),(9,7,307,111),(5,7,186,155),(8,7,275,155),(11,1,609,535),(11,12,693,493),(12,14,725,451),(14,15,1046,383),(13,1,610,139),(13,82,1259,116),(16,82,1320,260),(19,16,1463,880),(20,16,1374,510),(21,16,1374,403),(22,16,1374,311),(17,16,1353,1070),(18,16,1353,920),(24,17,1456,1108),(25,18,1456,1007)]
# S013/S001 用原图转正感染图中同一门口，A 图门位在左上边缘。
A=[q for q in A if q[:2] not in [(13,1),(13,82),(16,82)]]
for a,b,x,y in A:opening(a,b,'A',x,y)
Bitems=[(26,27,125,781),(28,27,60,650),(29,27,178,782),(30,27,230,650),(31,27,327,782),(32,27,292,650),(33,27,446,782),(34,27,569,782),(35,27,813,778),(36,27,602,590),(36,44,946,600),(37,39,714,282),(40,27,676,420),(41,39,755,284),(41,39,853,260),(42,27,883,778),(43,27,1008,778),(45,27,1091,778),(47,27,1210,778),(46,27,1105,652),(48,52,1268,620),(49,52,1268,559),(50,52,1268,497),(53,52,1362,605),(54,52,1362,510),(55,52,1362,422),(56,52,1362,343),(57,52,1362,236),(58,52,1362,134),(39,2,1100,174),(39,52,1268,260),(51,52,1454,773)]
for a,b,x,y in Bitems:opening(a,b,'B',x,y)
opening(39,27,'B',675,324,'open_passage');opening(27,52,'B',1271,720,'open_passage')
C=[(61,59,151,246),(62,59,244,246),(64,59,315,246),(66,65,450,246),(67,65,579,246),(70,65,684,246),(71,65,775,246),(73,65,881,246),(75,65,1007,246),(78,77,1098,117),(60,59,169,382),(60,59,183,520),(69,65,704,380),(69,65,618,531),(74,65,932,315),(74,76,1041,350),(72,76,1138,380),(79,80,1240,380),(80,65,1246,310),(83,82,1292,246),(89,82,1376,275),(88,82,1390,445),(92,82,1500,445),(87,82,1390,567),(91,82,1500,563),(86,82,1390,700),(85,82,1390,752),(84,82,1390,863),(13,1,613,744),(13,82,1259,886),(16,82,1325,916),(63,65,328,380),(68,66,508,65),(81,77,1158,142),(81,65,1190,246)]
for a,b,x,y in C:opening(a,b,'C',x,y,'open_passage' if (a,b)==(66,65) else 'door')
Ditems=[(101,100,157,251),(101,100,415,251),(111,100,635,251),(113,100,727,251),(124,100,774,251),(125,100,888,251),(127,100,1006,251),(137,100,1189,251),(140,100,1310,251),(148,100,1362,251),(150,100,1452,251),(99,100,129,337),(99,98,86,447),(96,102,172,925),(97,103,364,675),(102,103,364,957),(95,103,364,1148),(110,103,654,455),(109,103,654,613),(108,103,654,793),(107,103,654,982),(106,103,654,1040),(105,103,503,1271),(112,103,610,1274),(123,126,957,389),(122,126,957,493),(121,126,957,594),(120,126,957,705),(119,126,957,803),(118,126,957,909),(117,126,957,1052),(116,126,957,1171),(115,126,957,1293),(115,103,780,1232),(114,103,780,1371),(136,100,1191,337),(135,126,1254,453),(134,126,1254,558),(133,126,1254,668),(132,126,1254,776),(131,126,1076,861),(130,126,1254,972),(129,126,1076,1062),(147,126,1343,576),(147,146,1457,646),(146,126,1345,687),(145,126,1345,777),(144,126,1345,872),(143,126,1345,966),(142,126,1345,1073),(141,126,1345,1151),(149,139,1440,1340),(138,126,1246,1462),(100,103,423,337),(100,126,1019,337),(94,2,185,1501),(103,2,310,1501)]
for a,b,x,y in Ditems:opening(a,b,'D',x,y,'open_passage' if (a,b)==(146,126) else 'door')
opening(98,104,'D',289,487,'open_passage')
opening(139,126,'D',1248,1350,'open_passage')
# 现有同一大厅中的连续分区，无实体门位，不增加红点。
for a,b,reason in [(7,65,'布局推断：卫生间前厅与感染门诊侧公共通道衔接，小开口分辨率不足'),(1,10,'连续大厅分区'),(1,2,'大厅与医疗街连续'),(10,2,'候药大厅与医疗街连续'),(16,2,'配套通道接医疗街'),(59,65,'同一公共通道因单环轮廓分段'),(65,82,'感染门诊公共通道连续')]:
 r=relation(a,b);audit['unlocated_conceptual'].append({'relation_id':r['id'],'source':sid(a),'target':sid(b),'reason':reason})
(P/'annotation.json').write_text(json.dumps(D,ensure_ascii=False,indent=2)+'\n')
(ROOT/'连通与门洞复核记录.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
print('relations',len(D['relations']),'openings',next_p-1,'door geometry unlocated',len([a for a in audit['unlocated_conceptual'] if 'crop' in a]))
for a in audit['unlocated_conceptual']:
 if 'crop' in a:print(a['source'],a['target'],a['crop'],a['crop_position'],a['max_polygon_distance_px'],a['projection_shift_px'])
