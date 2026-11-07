from pathlib import Path
import json,shutil,collections
from shapely.geometry import Polygon,Point,box
from shapely.ops import unary_union
w=Path(__file__).resolve().parent;p=next((w.parents[1]/'标注试样').glob('07_*'));d=json.loads((w/'修改前备份'/'annotation.json').read_text());ss={s['id']:s for s in d['spaces']}
# 根据完整原图可见走廊补齐既有节点的漏段，不新建或更换 S 编号。
changes=[]
for sid,extra in [('S129',box(1530,818,1878,849)),('S130',box(2021,818,2079.5,849)),('S143',box(1626,833,1656,914)),('S276',box(2181.5,2158,2354,2189))]:
 g=Polygon(ss[sid]['polygon_px']).union(extra)
 assert g.geom_type=='Polygon',(sid,g.geom_type)
 if sid=='S129':g=g.difference(box(1626,833,1656,849))
 ss[sid]['polygon_px']=[list(q) for q in list(g.exterior.coords)[:-1]];changes.append(sid)
# 原图中 CT 扫描排的实际分隔横墙约在 y1818/1824，而非旧轮廓的1837/1843。
for sid,edge,val in [('S297','max',1818),('S304','min',1824),('S298','max',1818),('S305','min',1824),('S294','max',1700),('S296','min',1707),('S296','max',1753),('S301','min',1760),('S301','max',1815),('S303','min',1825),('S303','max',1880),('S312','min',1887),('S312','max',1955),('S305','max',1936),('S317','min',1944),('S317','max',2000),('S318','min',1944),('S318','max',2000),('S322','min',2005)]:
 pts=ss[sid]['polygon_px'];old=(max if edge=='max' else min)(q[1] for q in pts)
 for q in pts:
  if q[1]==old:q[1]=val
 changes.append(sid)
# 房间横墙调整后，同步裁去原通道在旧分隔线附近的细条，避免重复计面积。
for sid in ['S273','S276']:
 g=Polygon(ss[sid]['polygon_px'])
 for other in ss.values():
  if other['type'] not in ['corridor','hall']:
   g=g.difference(Polygon(other['polygon_px']))
 assert g.geom_type=='Polygon' and not g.interiors
 ss[sid]['polygon_px']=[list(q) for q in list(g.exterior.coords)[:-1]];changes.append(sid)
ps={sid:Polygon(s['polygon_px']) for sid,s in ss.items()}
# 原图无法确认门向的旧推测边移至外部核对材料，不作为当前 access 事实。
pending_ids={'R130','R168','R177','R183','R191','R198','R200'}
pending=[r for r in d['relations'] if r['id'] in pending_ids]
d['relations']=[r for r in d['relations'] if r['id'] not in pending_ids]
# 可辨门向修正，保留关系编号。
retarget={'R131':'S166','R132':'S168','R134':'S172','R137':'S166','R138':'S168','R140':'S172','R146':'S164','R148':'S168','R151':'S166','R152':'S197','R154':'S164','R158':'S164','R160':'S197','R185':'S304','R196':'S321','R200':'S320','R199':'S316','R201':'S276','R194':'S276','R190':'S276','R188':'S276','R149':'S168'}
for r in d['relations']:
 if r['id'] in retarget:r['target']=retarget[r['id']]
lookup={(tuple(sorted((r['source'],r['target']))),r['type']):r for r in d['relations'] if r['type']!='entrance'}
nextr=max(int(r['id'][1:]) for r in d['relations'] if r['id'].startswith('R'))+1
added=[]
def relation(a,b,typ='access'):
 global nextr
 key=(tuple(sorted((a,b))),typ)
 if key not in lookup:
  r=dict(id=f'R{nextr:03}',source=a,target=b,type=typ);nextr+=1;d['relations'].append(r);lookup[key]=r;added.append(r['id'])
 return lookup[key]
records=[]
for line in (w/'目视开口记录.txt').read_text().splitlines():
 if not line or line.startswith('#'):continue
 z=line.split();a='S'+z[0];q=list(map(float,z[1:3]));pt=Point(q)
 cands=sorted((ps[s['id']].distance(pt),s['id']) for s in d['spaces'] if s['type'] in ['corridor','hall'] and s['id']!=a)
 b='S'+z[3] if len(z)>3 else cands[0][1]
 # 两处多门房间及跨后场门以图面的隔墙两侧修正。
 if a=='S303':q=[1918.,1870.];b='S304'
 if a=='S320':q=[1918.,2080.];b='S321'
 if a=='S288':q=[1866.,1630.];b='S271'
 if a in ['S326','S327']:b='S276'
 r=relation(a,b);o=dict(id=f'P{len(records)+1:03}',kind='door',position_px=q);r.setdefault('openings',[]).append(o)
 records.append(dict(**o,relation=r['id'],source=r['source'],target=r['target']))
# 可见无门的宽入口，不将无实体分隔的走廊分区边界伪造为门点。
for a,b,x,y in [('S129','S143',1640,833)]:
 r=relation(a,b);o=dict(id=f'P{len(records)+1:03}',kind='door',position_px=[x,y]);r.setdefault('openings',[]).append(o);records.append(dict(**o,relation=r['id'],source=r['source'],target=r['target']))
# 可辨区域连续/半墙联系，只记概念通行。
for a,b in [('S370','S347'),('S142','S153'),('S090','S051'),('S129','S130'),('S130','S131'),('S143','S152'),('S238','S212'),('S120','S121'),('S022','S012'),('S068','S053'),('S185','S174'),('S397','S393'),('S398','S393')]:relation(a,b)
# 服务窗口保持服务语义，窗台和共墙不推断人员可达。
for a,b in [('S021','S007'),('S069','S058'),('S151','S152'),('S154','S152'),('S151','S401'),('S154','S401')]:relation(a,b,'service')
# 明确相邻且未辨门洞的 CT 后场隔墙单列，不以共墙补全 access。
for a,b in [('S285','S286'),('S294','S291'),('S296','S297'),('S301','S297'),('S312','S304'),('S318','S322')]:relation(a,b,'shared_wall')
# 合并同一空间对，保留最先已有编号。
seen={};out=[]
for r in d['relations']:
 if r['type']=='entrance':out.append(r);continue
 k=(tuple(sorted((r['source'],r['target']))),r['type'])
 if k in seen:seen[k].setdefault('openings',[]).extend(r.get('openings',[]))
 else:seen[k]=r;out.append(r)
d['relations']=out
stage=w/'待核验成果';stage.mkdir(exist_ok=True)
for name in [d['image']['file'],'标注说明.md']:shutil.copy2(p/name,stage/name)
(stage/'annotation.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
(w/'本轮开口对应表_工作.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
(w/'待核旧关系_工作.json').write_text(json.dumps(pending,ensure_ascii=False,indent=2))
(w/'修改清单_工作.json').write_text(json.dumps(dict(changed_polygons=changes,pending_relations=pending,retargeted=retarget,added_relation_ids=added),ensure_ascii=False,indent=2))
print('SPACES',len(d['spaces']),'RELATIONS',collections.Counter(r['type'] for r in out),'OPENINGS',len(records),'CHANGED_POLYGONS',changes)
for r in out:
 for o in r.get('openings',[]):
  pt=Point(o['position_px']);ds=[round(ps[r[k]].distance(pt),1) for k in ['source','target']]
  if max(ds)>15:print('DISTANCE',o['id'],r['source'],r['target'],o['position_px'],ds)
print('UNLOCATED NON-CIRCULATION')
for r in out:
 if r['type']=='access' and not r.get('openings') and any(ss[r[k]]['type'] not in ['corridor','hall'] for k in ['source','target']):print(r)
