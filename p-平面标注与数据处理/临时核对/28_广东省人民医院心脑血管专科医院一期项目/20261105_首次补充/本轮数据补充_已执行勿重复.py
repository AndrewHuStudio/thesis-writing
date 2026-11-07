from pathlib import Path
import json,hashlib
P=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理/标注试样/28_广东省人民医院心脑血管专科医院一期项目')
O=P.parents[1]/'临时核对'/P.name/'20261105_首次补充'
d=json.loads((P/'annotation.json').read_text());by={s['id']:s for s in d['spaces']}
changes={3:('办公室','office'),14:('男更衣室','staff_support'),15:('女更衣室','staff_support'),22:('水处理间','building_services'),52:('注射室','treatment'),54:('更衣室','staff_support'),72:('阅片室','office'),74:('控制室','imaging'),75:('控制室','imaging'),78:('控制室','imaging'),79:('控制室','imaging'),94:('控制室','imaging'),95:('控制室','imaging'),97:('控制室','imaging'),112:('输液区','treatment'),114:('护士站','nurse_station'),118:('隔离室','isolation'),120:('手术室','operating_room'),123:('消毒室','sterile_supply'),126:('卫生间','toilet'),128:('抢救室','resuscitation'),139:('护士站','nurse_station'),206:('更衣室','staff_support')}
for n,(name,t) in changes.items():by[f'S{n:03d}'].update(name=name,type=t)
for n in [114,139]:by[f'S{n:03d}']['level']='semi_open_space'
# 旧边端点与本图连续通道不符。移除时保留其余R编号，新增编号接续。
removed=[r for r in d['relations'] if r['id'] in ['R117','R147']]
d['relations']=[r for r in d['relations'] if r not in removed]
seq=max(int(r['id'][1:]) for r in d['relations'] if r['id'].startswith('R'))
added=[]
def pair(a,b):
 global seq
 a=f'S{a:03d}';b=f'S{b:03d}'
 for r in d['relations']:
  if r['type']=='access' and {r['source'],r['target']}=={a,b}:return r
 seq+=1;r=dict(id=f'R{seq:03d}',source=a,target=b,type='access');d['relations'].append(r);added.append(r['id']);return r
points=[]
def mark(a,b,x,y,kind='door'):
 r=pair(a,b);oid=f'P{len(points)+1:03d}';r.setdefault('openings',[]).append(dict(id=oid,kind=kind,position_px=[x,y]));points.append(oid)
# 手工对照原图选取每一个可见门洞，不从共墙中点生成。
for a,b,x,y in [(3,10,814,628),(2,10,785,628),(14,10,781,659),(15,10,817,659),(19,10,838,752),(8,16,229,713),(9,16,314,738),
 (49,57,805,1367),(50,57,862,1367),(53,57,1040,1367),(54,57,1080,1367),
 (62,57,783,1395),(63,57,872,1395),(64,57,908,1395),(65,57,945,1395),(66,57,993,1395),(67,57,1025,1395),(68,57,1080,1395),
 (56,55,449,1381),(56,55,449,1457),(70,55,449,1490),(71,55,449,1529),(85,55,449,1568),(86,55,449,1607),(90,55,449,1647),(91,55,449,1687),
 (58,69,558,1476),(61,69,662,1476),(72,69,596,1516),(73,69,637,1516),(74,69,711,1516),(76,69,831,1516),(78,69,945,1516),(79,69,991,1516),
 (92,103,596,1712),(94,103,711,1712),(95,103,749,1712),(96,103,790,1712),(100,103,1040,1712),(101,103,1075,1712),
 (112,113,576,2120),(112,109,1156,2119),(112,140,871,2278),(118,141,374,2243),(120,141,454,2322),(128,141,576,2479),(127,131,789,2398),(126,131,754,2398),
 (119,141,932,2480),(156,189,1905,2194),(161,190,2259,2182),(206,191,2323,2557)]:mark(a,b,x,y)
mark(113,131,675,2322,'open_passage')
# 右侧门诊24处门凹口逐项定位，按原S编号与既有关系补点。
for a,b,x,y in [(165,189,1905,2307),(166,189,1942,2294),(167,190,2229,2307),(168,190,2260,2294),
 (169,189,1905,2347),(170,189,1942,2334),(171,190,2229,2347),(172,190,2260,2334),
 (173,189,1905,2387),(174,189,1942,2373),(175,190,2229,2387),(176,190,2260,2373),
 (177,189,1905,2426),(178,189,1942,2413),(179,190,2229,2426),(180,190,2260,2413),
 (181,189,1905,2466),(182,189,1942,2452),(183,190,2229,2466),(184,190,2260,2452),
 (185,189,1905,2505),(186,189,1942,2492),(187,190,2229,2505),(188,190,2260,2492)]:mark(a,b,x,y)
for a,b,x,y in [(36,45,1218,1338),(36,89,1218,1736),(141,110,1157,2499),(109,110,1399,2154)]:mark(a,b,x,y)
# 连续开放通道已有概念边，保留无定位；不为每条边强制造点。
(P/'annotation.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
(O/'本轮变更记录.json').write_text(json.dumps(dict(clear_names={f'S{k:03d}':v for k,v in changes.items()},removed=removed,added=added,openings=len(points)),ensure_ascii=False,indent=2)+'\n')
print('names_added',len(changes),'remaining',sum(s['type']=='unknown' for s in d['spaces']),'relations',len(d['relations']),'new_relations',added,'openings',len(points))
