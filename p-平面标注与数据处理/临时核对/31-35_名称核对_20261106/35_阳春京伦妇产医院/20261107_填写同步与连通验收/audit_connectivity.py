from pathlib import Path
from collections import defaultdict,deque,Counter
import json,hashlib
from shapely.geometry import Polygon,Point
BASE=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理')
P=BASE/'标注试样/35_阳春京伦妇产医院'
RV=BASE/'临时核对/31-35_名称核对_20261106/35_阳春京伦妇产医院'
OUT=RV/'20261107_填写同步与连通验收'
d=json.loads((P/'annotation.json').read_text());old=json.loads((OUT/'用户填写及四文件备份/annotation.json').read_text())
ss={s['id']:s for s in d['spaces']};polys={sid:Polygon(s['polygon_px']) for sid,s in ss.items()}
rr={r['id']:r for r in d['relations']};adj=defaultdict(set);entrances=defaultdict(list)
errors=[]
for r in d['relations']:
    if r['type']=='access':
        adj[r['source']].add(r['target']);adj[r['target']].add(r['source'])
    elif r['type']=='entrance':entrances[r['target']].append(r['id'])

def path(a,b):
    prev={a:None};q=deque([a])
    while q:
        x=q.popleft()
        if x==b:break
        for y in sorted(adj[x]):
            if y not in prev:prev[y]=x;q.append(y)
    if b not in prev:return None
    result=[];cur=b
    while cur is not None:result.append(cur);cur=prev[cur]
    return list(reversed(result))

unseen=set(ss);components=[]
while unseen:
    root=min(unseen);q=[root];comp={root}
    for x in q:
        for y in adj[x]:
            if y not in comp:comp.add(y);q.append(y)
    unseen-=comp
    components.append({'spaces':sorted(comp),'size':len(comp),'entrances':{s:entrances[s] for s in sorted(comp) if entrances[s]}})
components.sort(key=lambda x:-x['size'])
reachable=set()
for comp in components:
    if comp['entrances']:reachable.update(comp['spaces'])
not_required={'S079','S081'}
unreachable=set(ss)-reachable
assert unreachable==not_required,unreachable
opening_audit=[]
for r in d['relations']:
    for op in r.get('openings',[]):
        distances={s:polys[s].boundary.distance(Point(op['position_px'])) for s in [r['source'],r['target']]}
        opening_audit.append({'id':op['id'],'relation_id':r['id'],'source':r['source'],'target':r['target'],'position_px':op['position_px'],'distance_px':distances})
        if max(distances.values())>.1:errors.append({'opening_endpoint':op['id'],'distances':distances})
old_ops={op['id']:op for r in old['relations'] for op in r.get('openings',[])}
new_ops={op['id']:op for r in d['relations'] for op in r.get('openings',[])}
assert old_ops==new_ops,'既有P编号、门位或类型发生了未授权修改'
assert 'S043' not in ss and not any(r.get(k)=='S043' for r in d['relations'] for k in ['source','target'])
assert 'S072' not in adj['S075'] and adj['S072']=={'S076'}
assert adj['S042']=={'S044'}
assert 'S007' in adj['S004'] and 'S006' in adj['S004']
assert ss['S017']['type']=='courtyard' and ss['S017']['level']=='open_space' and 'area_ratio' not in ss['S017']
assert all(s['type']!='unknown' for s in ss.values())
assert (P/d['image']['file']).read_bytes()==(OUT/'用户填写及四文件备份'/d['image']['file']).read_bytes()
key_paths={sid:path(sid,'S044') for sid in ['S001','S004','S006','S017','S031','S033','S042','S052','S053','S054','S058','S072','S073','S074','S077','S078','S082']}
assert all(key_paths.values())
# 普通人员关系须存在实际边界衔接；不把该检查当作门洞语义判断。
non_contact=[]
for r in d['relations']:
    if r['type']=='access':
        a,b=polys[r['source']],polys[r['target']]
        if a.distance(b)>.1:non_contact.append({'relation_id':r['id'],'source':r['source'],'target':r['target'],'gap_px':a.distance(b)})
assert not non_contact,non_contact
report={'spaces':len(ss),'relations':len(rr),'relation_types':dict(Counter(r['type'] for r in rr.values())),'openings':len(new_ops),'located_access_relations':sum(bool(r.get('openings')) for r in rr.values() if r['type']=='access'),'conceptual_access_relations':sum(not r.get('openings') for r in rr.values() if r['type']=='access'),'components':components,'reachable_from_building_entrances':len(reachable),'not_required_internal_details':[{'space_id':sid,'name':ss[sid]['name'],'note':'小辅助空间精确入口不属本轮主要通行组织，不补虚构连接，未记关系不代表不可达。'} for sid in sorted(unreachable)],'key_routes_to_S044':key_paths,'opening_audit':opening_audit,'opening_endpoint_errors':errors,'existing_openings_unchanged':True,'non_contact_access_relations':non_contact,'image_sha256':hashlib.sha256((P/d['image']['file']).read_bytes()).hexdigest(),'image_unchanged':True,'area_ratio_sum':sum(s.get('area_ratio',0) for s in ss.values()),'assertions_passed':True}
assert not errors
(OUT/'连通性测试结果.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['components','opening_audit','key_routes_to_S044']},ensure_ascii=False,indent=2))
print('components',[(c['size'],list(c['entrances'])) for c in components])
print('key_routes',json.dumps(key_paths,ensure_ascii=False))
