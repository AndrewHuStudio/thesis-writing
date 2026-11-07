from pathlib import Path
import json,sys,shutil,collections
from shapely.geometry import Polygon,Point
base=Path('/Users/hushili/Documents/研究-论文写作/大论文/p-平面标注与数据处理');root=base/'标注试样/29_内蒙古自治区国际蒙医医院扩建项目';w=base/'临时核对/29_内蒙古自治区国际蒙医医院扩建项目';run=Path((w/'当前续作目录.txt').read_text().strip());d=json.loads((root/'annotation.json').read_text());state=json.loads((w/'review_state.json').read_text());answers=json.loads((run/'用户连通填写原文.json').read_text());by={s['id']:s for s in d['spaces']}
# Retire superseded opposite-side routes; preserve IDs and all unaffected openings.
remove_pairs=[{'S059','S066'},{'S060','S066'},{'S061','S066'},{'S054','S066'},{'S055','S066'}]
retired=[]
for r in list(d['relations']):
 if r['type']=='access' and {r['source'],r['target']} in remove_pairs:
  assert not r.get('openings'),r
  d['relations'].remove(r);retired.append(r)
rnum=max(int(r['id'][1:]) for r in d['relations'] if r['id'].startswith('R'));pnum=max(int(p['id'][1:]) for r in d['relations'] for p in r.get('openings',[]));existing={frozenset((r['source'],r['target'])):r for r in d['relations'] if r['type']=='access'};added=[];audit=[]
def add(a,b,basis,uv=None):
 global rnum,pnum
 key=frozenset((a,b));r=existing.get(key)
 if r is None:
  rnum+=1;r=dict(id=f'R{rnum:03d}',source=a,target=b,type='access');d['relations'].append(r);existing[key]=r;added.append(r['id'])
 if uv:
  pnum+=1;pos=[2444-uv[1],uv[0]];r.setdefault('openings',[]).append(dict(id=f'P{pnum:03d}',kind='door',position_px=pos))
 audit.append(dict(relation_id=r['id'],source=a,target=b,basis=basis,reading_position=uv))
confirmed={
'K02':[('S005','S003'),('S005','S006'),('S005','S014'),('S013','S014')],
'K03':[('S049','S050'),('S062','S050'),('S067','S050')],
'K04':[('S150','S129')],
'K05':[('S193','S194'),('S194','S154')],
'K06':[('S061','S055'),('S060','S055'),('S059','S055')]}
for rid,pairs in confirmed.items():
 for a,b in pairs:
  basis=f'{rid}用户确认：{answers[rid]}'
  if rid=='K02' and {a,b}=={'S005','S014'}:basis+='；按题图所示大厅衔接理解人员进入路径。'
  add(a,b,basis)
# Independent visual judgments in the same two reviewed portions.
add('S054','S055','原图楼梯交通核西侧有可见门口，衔接西侧通道；旧东侧关系无对应开口。',(1098,1305))
add('S010','S006','布局推断：楼梯通过北侧共用前室衔接中药区域；不细究交通核内部路线。')
for item in state['connectivity_items']:
 rid=item['review_id']
 if rid not in answers:continue
 item.setdefault('history',[]).append({k:item[k] for k in ['source','target','status','question','judgment'] if k in item})
 item.update(status='confirmed_connected',answer=answers[rid],applied=True,confirmed_pairs=[list(p) for p in confirmed[rid]])
 first=confirmed[rid][0];item['source'],item['target']=first
 if rid=='K04':item['unselected_alternatives']=[['S150','S160']]
 if rid=='K05':item['unselected_alternatives']=[['S193','S157']]
 if rid=='K06':item['unselected_alternatives']=[['S061','S066'],['S060','S066'],['S059','S066']];item['scope_resolution']='按用户明确从S055进入保留西侧通道；未要求合并控制区。'
state['checks'].update(connectivity_reviewed=False,visual_reviewed=False)
state.setdefault('connectivity_review_history',[]).append({'source':'本轮MD原话及原图局部复核','retired_relations':retired,'added_relations':added,'basis':audit})
# Graph summary is evidence of recorded coverage, not a requirement to connect courtyards or staff details.
g={s['id']:set() for s in d['spaces']}
for r in d['relations']:
 if r['type']=='access':g[r['source']].add(r['target']);g[r['target']].add(r['source'])
seen=set();components=[]
for a in g:
 if a in seen:continue
 stack=[a];seen.add(a);comp=[]
 while stack:
  u=stack.pop();comp.append(u)
  for v in g[u]-seen:seen.add(v);stack.append(v)
 components.append(sorted(comp))
components.sort(key=len,reverse=True)
(run/'本轮连通同步与图审记录.json').write_text(json.dumps({'answers':answers,'added_relations':added,'retired_relations':retired,'basis':audit,'components':components,'isolated_spaces':[{'id':s,'name':by[s]['name'],'type':by[s]['type']} for s,n in g.items() if not n]},ensure_ascii=False,indent=2)+'\n')
(root/'annotation.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');(w/'review_state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
# Archive the exact user-edited MD before creating the compact status document.
sys.path.insert(0,'/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts');from review_workflow import archive_markdown
archive_markdown(root/'标注说明.md',w/'review_state.json',(root/'标注说明.md').read_text());(root/'标注说明.md').write_text('# 29号｜内蒙古自治区国际蒙医医院扩建项目\n')
shutil.copy2('/tmp/finish29_connectivity.py',run/'同步用户连通确认.py')
print({'spaces':len(d['spaces']),'relations':len(d['relations']),'openings':sum(len(r.get('openings',[])) for r in d['relations']),'added_access':len(added),'retired_access':len(retired),'components':[len(c) for c in components],'isolated':[s for s,v in g.items() if not v]})
