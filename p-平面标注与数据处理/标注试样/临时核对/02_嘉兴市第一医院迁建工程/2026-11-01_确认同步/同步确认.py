from pathlib import Path
import json,re,copy,hashlib
from shapely.geometry import Polygon,box
from shapely.ops import unary_union

out=Path(__file__).resolve().parent
p=out.parents[2]/'02_嘉兴市第一医院迁建工程'
a=json.loads((out/'修改前备份/annotation.json').read_text())
ss={s['id']:s for s in a['spaces']};before=copy.deepcopy(a);notes=[]
def geom(sid):return Polygon(ss[sid]['polygon_px'])
def put(sid,g):
 assert g.geom_type=='Polygon' and g.is_valid and not g.interiors,(sid,g.geom_type)
 ss[sid]['polygon_px']=[[round(x,3),round(y,3)] for x,y in list(g.exterior.coords)[:-1]]
def rectangle(sid,x0,y0,x1,y1):put(sid,box(x0,y0,x1,y1))
# User-authorized merges preserve the surviving IDs; removed IDs are not reused.
put('S023',unary_union([geom('S023'),geom('S273')]))
ss['S023']['type']='waste_handling'
put('S223',unary_union([geom('S223'),geom('S027'),box(1887.589,1925.324,1903,1976.471)]))
ss['S223'].update(name='库房',type='storage',level='room')
put('S028',geom('S028').difference(geom('S223')))
removed={'S273':'S023','S027':'S223','S244':None}
for sid in removed:ss.pop(sid)
a['spaces']=[s for s in a['spaces'] if s['id'] not in removed]
# Repair the corridor formerly represented by a thin triangle, and the office next to it.
rectangle('S114',2305.633,301.403,2427.943,443.884)
rectangle('S118',2464.453,396.390,2537.474,537.045)
rectangle('S124',2464.453,537.045,2537.474,611.939)
rectangle('S261',2427.943,396.390,2464.453,611.939)
ss['S261']['name']='药房北侧医护走廊'
ss['S264'].update(name='医护走廊',type='corridor')
# Correct the local service-room boundaries so the visible store-room door belongs to S102.
rectangle('S100',1328.979,931.608,1351,988.236)
rectangle('S101',1351,931.608,1376,988.236)
rectangle('S102',1376,931.608,1414,988.236)
rectangle('S103',1414,931.608,1517.008,988.236)
# Include the stair vestibule on its confirmed street side, and remove duplicate corridor area.
stair_vestibule=box(896.331,1344.439,983.956,1379.146)
ss['S277']={'id':'S277','name':'急诊南侧楼梯门厅','type':'hall','level':'open_space','scope':'emergency','polygon_px':[]}
put('S277',stair_vestibule)
a['spaces'].append(ss['S277'])
put('S257',geom('S257').difference(stair_vestibule))
# Include the confirmed northward return in the west store room.
put('S227',unary_union([geom('S227'),box(1650.271,2124.433,1750,2150)]))
put('S274',geom('S274').difference(geom('S227')))
put('S031',geom('S031').difference(geom('S227')))
# Treat the connector and peripheral circulation as one aggregate corridor S250.
# The exterior entrance forecourt on the west remains outside this indoor annotation.
outer=Polygon([(390,2135),(396,2080),(420,2038),(465,2003),(520,1978),(585,1963),(655,1959),(730,1964),(795,1980),(850,2008),(891,2047),(914,2095),(974.828,2095),(974.828,2175),(914,2175),(900,2220),(875,2254),(832,2280),(775,2298),(715,2309),(645,2313),(580,2307),(520,2291),(465,2264),(425,2230),(400,2186)])
inner=Polygon([(421,2135),(426,2095),(449,2060),(482,2032),(522,2012),(572,1998),(620,1992),(675,1992),(730,1998),(782,2012),(827,2035),(856,2063),(874,2095),(879,2133),(875,2167),(859,2200),(829,2230),(785,2253),(733,2270),(677,2279),(621,2280),(570,2273),(522,2256),(483,2234),(450,2206),(430,2172)])
others=unary_union([geom(f'S{i}') for i in [245,247,248,249]])
put('S246',unary_union([geom('S246'),inner]).difference(others))
inner_nodes=unary_union([geom(f'S{i}') for i in range(245,250)])
put('S250',outer.difference(inner_nodes).difference(box(350,2110,445,2160)))
ss['S250']['name']='报告厅连接通道及外围环廊'
# Remove all dangling links, coalesce any links affected by the merges, retain unaffected R/P IDs.
rels=[]
for r0 in a['relations']:
 r=copy.deepcopy(r0)
 for key in ['source','target']:
  if r[key] in removed:r[key]=removed[r[key]]
 if r['target'] is None or (r['type']!='entrance' and (r['source'] is None or r['source']==r['target'])):continue
 existing=next((x for x in rels if x['type']==r['type'] and r['type']!='entrance' and {x['source'],x['target']}=={r['source'],r['target']}),None)
 if existing:
  if r.get('openings'):existing.setdefault('openings',[]).extend(r['openings'])
 else:rels.append(r)
a['relations']=rels
# Reattach old located doors to the corrected corridor and vestibule, keeping their P IDs.
for r in rels:
 if r['id']=='R084':r['source']='S261'
 if r['id']=='R230':r['target']='S261'
stair_waiting_doors=[]
street_vestibule_doors=[]
for r in rels:
 if r['id']=='R312':
  street_vestibule_doors=[o for o in r.get('openings',[]) if o['id']=='P246']
  r['openings']=[o for o in r['openings'] if o not in street_vestibule_doors]
 if r['id']=='R068':
  stair_waiting_doors=[o for o in r.get('openings',[]) if o['id'] in ['P068','P069']]
  r['openings']=[o for o in r['openings'] if o not in stair_waiting_doors]
rnext=max(int(r['id'][1:]) for r in before['relations'] if r['id'].startswith('R'))+1
pnext=max(int(o['id'][1:]) for r in before['relations'] for o in r.get('openings',[]))+1
added=[]
def relation(x,y,typ='access',points=None):
 global rnext,pnext
 r=next((r for r in rels if r['type']==typ and {r['source'],r['target']}=={x,y}),None)
 if r is None:
  r={'id':f'R{rnext:03}','source':x,'target':y,'type':typ};rnext+=1;rels.append(r);added.append(r)
 for q in points or []:
  r.setdefault('openings',[]).append({'id':f'P{pnext:03}','kind':'door','position_px':q});pnext+=1
 return r
relation('S092','S277')['openings']=stair_waiting_doors
relation('S277','S260')['openings']=street_vestibule_doors
relation('S277','S257')
relation('S037','S038')
relation('S048','S258')
relation('S114','S261',points=[[2428,417]])
relation('S118','S261',points=[[2464,407]])
relation('S120','S261',points=[[2428,476]])
relation('S122','S261',points=[[2428,534]])
# R230/P097 already locates this door after its target was corrected.
relation('S115','S261',points=[[2440,396]])
relation('S261','S124')
relation('S135','S258',points=[[1767,755]])
relation('S102','S099',points=[[1389,932]])
relation('S099','S259')
relation('S105','S259')
relation('S172','S268')
relation('S173','S268',points=[[2464,1201]])
relation('S020','S268')
relation('S170','S268')
relation('S091','S277')
relation('S108','S276')
relation('S109','S276',points=[[1619,1781]])
relation('S223','S274',points=[[1895,1972]])
relation('S226','S274','service')
relation('S225','S274','shared_wall')
relation('S227','S274',points=[[1741,2125]])
relation('S249','S246',points=[[818,2181]])
relation('S246','S250',points=[[770,2005],[758,2266]])
relation('S235','S275',points=[[1308,2654]])
# Keep the user's wording verbatim in an external, directly viewable archive with valid links.
md=(out/'修改前备份/标注说明.md').read_text()
def relocate(m):
 path=m.group(1)
 if path.startswith('#'):return m.group(0)
 import os
 return ']('+os.path.relpath((p/path).resolve(),out)+')'
(out/'用户填写原文.md').write_text(re.sub(r'\]\(([^)]+)\)',relocate,md))
(out/'本轮变更.json').write_text(json.dumps({'removed_mapping':removed,'changed_spaces':[s['id'] for s in a['spaces'] if s!=next((x for x in before['spaces'] if x['id']==s['id']),None)],'added_relations':added},ensure_ascii=False,indent=2)+'\n')
(p/'annotation.json').write_text(json.dumps(a,ensure_ascii=False,indent=2)+'\n')
print('Updated:',len(a['spaces']),'spaces;',len(a['relations']),'relations;',pnext-1,'largest opening ID')
print('Removed:',removed,'; added relations:',len(added))
