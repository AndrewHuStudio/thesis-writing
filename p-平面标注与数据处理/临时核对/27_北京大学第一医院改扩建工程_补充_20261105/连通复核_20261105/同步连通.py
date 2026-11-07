from pathlib import Path
import json,copy,sys,xml.etree.ElementTree as ET,re,hashlib
from collections import deque,Counter
from shapely.geometry import Polygon,box
from PIL import Image,ImageDraw,ImageFont
import pymupdf
O=Path(__file__).resolve().parent;B=O.parent;ROOT=B.parent.parent/'标注试样/27_北京大学第一医院改扩建工程';p=ROOT/'annotation.json'
sys.path.insert(0,'/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts');import annotation_tools as at;import review_workflow as rw
if (O/'复核记录.json').exists():raise RuntimeError('本轮已应用；继续前请读取最新版，不重复覆盖。')
d=json.loads(p.read_text());md=(ROOT/'标注说明.md').read_text();state=rw.load_state(B/'review_state.json',d,p);spaces={s['id']:s for s in d['spaces']};W=d['image']['width'];H=d['image']['height']
def orig(x,y):return [W-1-y,x]
def up(s):return [(y,W-1-x) for x,y in s['polygon_px']]
# 只扩展可见的东南公共通行带；不吞并邻接房间。
q=Polygon(up(spaces['S024'])).union(box(2219,1231,2271,1376));assert q.geom_type=='Polygon'
spaces['S024']['polygon_px']=[orig(x,y) for x,y in list(q.exterior.coords)[:-1]]
assert not any(r['id']=='R057' for r in d['relations'])
d['relations'].append(dict(id='R057',source='S043',target='S049',type='access',openings=[dict(id='P059',kind='door',position_px=orig(2288,1193))]))
r=next(r for r in d['relations'] if r['id']=='R030');r['openings'].append(dict(id='P060',kind='door',position_px=orig(2217,1248)))
at.normalize(d);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
# 图连通仅作复核证据，不因希望全连通而补边。
adj={sid:set() for sid in spaces}
for r in d['relations']:
 if r['type']=='access':adj[r['source']].add(r['target']);adj[r['target']].add(r['source'])
reached={'S021'};todo=deque(reached)
while todo:
 for sid in adj[todo.popleft()]-reached:reached.add(sid);todo.append(sid)
main=[s['id'] for s in d['spaces'] if s['type'] not in {'unknown','building_services'}]
assert set(main)<=reached
paths={}
for target in main:
 queue=deque([['S021']]);seen={'S021'}
 while queue:
  path=queue.popleft()
  if path[-1]==target:paths[target]=path;break
  for nxt in sorted(adj[path[-1]]-seen):seen.add(nxt);queue.append(path+[nxt])
record={'review_scope':'图例主要功能空间、走道/大厅、交通核及外部入口；不穷尽内部小间路线。','added_relation':'R057 S043-S049','added_openings':{'P059':'S043-S049 内部门','P060':'R030 S024-S051 第二扇门'},'geometry_correction':'S024补入S051东侧明确公共通行带','main_nodes':main,'main_nodes_reachable':len(main),'entrance_reachable_count':len(reached),'outside_main_network':sorted(set(spaces)-reached),'pending_key_questions':['K02'],'not_required_internal_details':['S031','S034','S045','S050','S052'],'paths_from_E001':paths,'layout_inference_relations':['R013','R024','R027','R028'],'existing_openings_preserved':True}
(O/'复核记录.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
state['checks'].update(connectivity_reviewed=True,visual_reviewed=False);state.setdefault('connectivity_rounds',[]).append({'date':'2026-11-05','record':'连通复核_20261105/复核记录.json','main_nodes_reachable':len(main),'pending':['K02']});rw.save_state(B/'review_state.json',state)
# 更新简短结果，保持K02原确认栏及内容；不再生成内部小间房名表。
md=re.sub(r'\*\*规模：\*\*[^\n]+','**规模：**55个空间节点、60条关系（55条人员可达、5条入口）、60处门洞／开口；已明确名称33个，22个未定功能节点继续保留unknown。',md)
start=md.index('**当前状态：**');end=md.index('\n\n',start)
md=md[:start]+'**当前状态：**主要功能空间的连通复核已执行；32个已具名主要空间均可从北侧主入口到达。新增S043—S049内部门，补入S051东侧门及其公共通行带。S015仍留K02；不将未知关系当作不相通，也不为全连通补边。全量JSON名称尚未齐全。'+md[end:]
(ROOT/'标注说明.md').write_text(md)
# 重新渲染转正SVG；保持核心P坐标、原始编号及显式旋转变换。
u=copy.deepcopy(d);u['image'].update(width=H,height=W)
for s in u['spaces']:s['polygon_px']=[[y,W-1-x] for x,y in s['polygon_px']]
for r in u['relations']:
 if 'position_px' in r:r['position_px']=[r['position_px'][1],W-1-r['position_px'][0]]
 for o in r.get('openings',[]):o['position_px']=[o['position_px'][1],W-1-o['position_px'][0]]
at.render(u,p,ROOT/'标注.svg');ns='{http://www.w3.org/2000/svg}';tree=ET.parse(ROOT/'标注.svg');rt=tree.getroot();im=rt.find('.//'+ns+'image');im.set('width',str(W));im.set('height',str(H));im.set('transform',f'matrix(0 -1 1 0 0 {W-1})')
for r in d['relations']:
 for o in r.get('openings',[]):
  og=rt.find('.//'+ns+'g[@data-opening-id="'+o['id']+'"]');c=og.find(ns+'circle');c.set('cx',str(o['position_px'][0]));c.set('cy',str(o['position_px'][1]));c.set('transform',f'matrix(0 -1 1 0 0 {W-1})');label=og.find(ns+'text')
  for key in ['stroke','stroke-width','paint-order']:label.attrib.pop(key,None)
  label.set('font-size','8');x=float(label.get('x'));y=float(label.get('y'));og.insert(list(og).index(label),at.element('rect',{'x':x-1,'y':y-8,'width':24,'height':10,'fill':'white','fill-opacity':'.9','rx':1}))
rt.findall(ns+'text')[0].text='27 北京大学第一医院改扩建工程｜主要功能空间连通复核'
for eid,bx,by in [('E004',2495,450),('E006',2235,465)]:
 eg=rt.find('.//'+ns+'g[@id="'+eid+'"]');rect=eg.find(ns+'rect');label=eg.find(ns+'text');line=eg.find(ns+'line');rect.set('x',str(bx));rect.set('y',str(by));label.set('x',str(bx+7));label.set('y',str(by+18));line.set('x2',str(bx+float(rect.get('width'))/2));line.set('y2',str(by+float(rect.get('height'))/2))
rt.find(ns+'g').append(at.txt(120,1780,'下方裁切平面不纳入本次标注。',24,'#64748b',True));tree.write(ROOT/'标注.svg',encoding='unicode')
doc=pymupdf.open(ROOT/'标注.svg');page=doc[0]
for name,clip,scale in [('全图',None,.8),('东南补充',pymupdf.Rect(2110,1230,2540,1545),2.5),('西翼',pymupdf.Rect(100,630,1120,1540),1.3)]:
 page.get_pixmap(matrix=pymupdf.Matrix(scale,scale),clip=clip,alpha=False).save(O/f'连通复核_{name}_检查.png')
print('main',len(main),'reachable',len(reached),'relations',Counter(r['type'] for r in d['relations']),'openings',sum(len(r.get('openings',[])) for r in d['relations']))
