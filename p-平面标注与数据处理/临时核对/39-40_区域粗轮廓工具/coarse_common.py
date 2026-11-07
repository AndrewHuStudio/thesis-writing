from pathlib import Path
import copy,json,sys,math
from shapely.geometry import Polygon,box,Point,LineString
from shapely.ops import unary_union,split
BASE=Path(__file__).resolve().parents[2]
SKILL=Path('/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts')
sys.path.insert(0,str(SKILL))
import annotation_tools as at
class Plan:
 def __init__(self,n):
  self.n=n;self.root=next((BASE/'标注试样').glob(f'{n}_*'));self.review=next((BASE/'临时核对').glob(f'{n}_*'));self.out=self.review/'20261107_区域粗轮廓'
  self.d=json.loads((self.out/'修改前备份/annotation.json').read_text());self.old=copy.deepcopy(self.d)
  self.st=json.loads((self.out/'修改前备份/review_state.json').read_text());self.oldst=copy.deepcopy(self.st)
  self.s={s['id']:s for s in self.d['spaces']};self.oldpoly={s['id']:self.poly(s) for s in self.old['spaces']}
  self.children={s['id']:[s['id']] for s in self.d['spaces']};self.nexts=max(int(s[1:]) for s in self.s)+1
  self.nextr=max(int(r['id'][1:]) for r in self.d['relations'] if r['id'].startswith('R'))+1
  self.nextp=max(int(o['id'][1:]) for r in self.d['relations'] for o in r.get('openings',[]))+1
  self.changes=[];self.extra=[];self.remap=[];self.continuities={}
 def orig(self,x,y):return [round(2424-y,3),round(x,3)] if self.n==39 else [round(x,3),round(y,3)]
 def display(self,xy):return [xy[1],2424-xy[0]] if self.n==39 else xy
 def poly(self,s):return Polygon([self.display(p) for p in s['polygon_px']])
 def points(self,p):return [self.orig(x,y) for x,y in list(p.exterior.coords)[:-1]]
 def sid(self,n):return n if isinstance(n,str) else f'S{n:03d}'
 def cut(self,num,rects,retain='remainder',corridor=None):
  sid=self.sid(num);old=copy.deepcopy(self.s[sid]);parent=self.poly(old);pieces=[]
  for spec in rects:
   p=box(*spec) if len(spec)==4 and isinstance(spec[0],(int,float)) else Polygon(spec)
   p=p.intersection(parent)
   if p.is_empty or p.area<5:continue
   if p.geom_type=='MultiPolygon':pieces.extend(p.geoms)
   else:pieces.append(p)
  # 按真实隔墙粗框切分；余部保留内部公共交通，显式检查不重叠。
  for i,p in enumerate(pieces):
   for q in pieces[i+1:]:assert p.intersection(q).area<.01,(sid,'cuts overlap')
  rest=parent.difference(unary_union(pieces))
  rests=[] if rest.is_empty else [rest] if rest.geom_type=='Polygon' else [p for p in rest.geoms if p.area>1]
  simple=[]
  for rr in rests:
   queue=[rr]
   while queue:
    q=queue.pop()
    if q.interiors:
     yy=Polygon(q.interiors[0]).centroid.y
     queue.extend(split(q,LineString([(-10,yy),(10000,yy)])).geoms)
    else:simple.append(q)
  rests=simple
  if retain=='first':tagged=[(q,'room') for q in pieces]+[(q,'remainder') for q in rests]
  else:tagged=[(q,'remainder') for q in sorted(rests,key=lambda p:-p.area)]+[(q,'room') for q in pieces]
  allparts=[q for q,role in tagged]
  assert allparts and abs(sum(p.area for p in allparts)-parent.area)<2,(sid,'area coverage')
  ids=[]
  corridor_ids=[]
  for i,(p,role) in enumerate(tagged):
   sn=sid if i==0 else f'S{self.nexts:03d}'
   if i:self.nexts+=1
   v=copy.deepcopy(old);v['id']=sn;v['polygon_px']=self.points(p)
   if role=='remainder' and retain!='first' and corridor:
    v.update(name=corridor,type='corridor',level='open_space');corridor_ids.append(sn)
   elif i==0 and retain!='first' and old['type']!='unknown':
    # 如原药房主体仍为同一房间，保留原名；拆出的配套小间独立保留未知。
    pass
   else:v.update(name='名称未确认',type='unknown',level='room')
   self.s[sn]=v;ids.append(sn)
  self.children[sid]=ids
  if corridor_ids:self.continuities[sid]=corridor_ids
  self.changes.append(dict(parent=sid,old_name=old['name'],children=ids,reason='按本图可辨隔墙逐单元粗分；原区域语义保存在regions，未知小间不沿用整个科室名称。'))
  return ids
 def which(self,parent,xy,other=None):
  candidates=self.children[self.sid(parent)];pt=Point(*xy)
  ds=[(self.poly(self.s[k]).distance(pt),i,k) for i,k in enumerate(candidates)]
  dist,_,k=min(ds,key=lambda a:(a[0],0 if self.s[a[2]]['level']=='room' else 1,a[1]))
  if other and dist<=2:
   near=[a for a in ds if a[0]<=dist+.05]
   if len(near)>1:
    op=self.poly(self.s[other]);k=min(near,key=lambda a:(self.poly(self.s[a[2]]).distance(op),a[1]))[2]
  return k
 def remap_relations(self):
  rels=[];seen={}
  for r in self.old['relations']:
   base=copy.deepcopy(r);opens=base.pop('openings',None)
   if r['type']=='entrance':
    base['target']=self.which(r['target'],self.display(r['position_px']));rels.append(base);continue
   if not opens:
    # 无定位关系保留在原编号对应的主要余部，不由共墙扩展到全部子房间。
    rels.append(base);continue
   groups={}
   for o in opens:
    xy=self.display(o['position_px']);a=self.which(r['source'],xy);b=self.which(r['target'],xy,a)
    groups.setdefault((a,b),[]).append(o)
   for i,((a,b),oo) in enumerate(groups.items()):
    nr=copy.deepcopy(base);nr.update(source=a,target=b,openings=oo)
    if i:nr['id']=f'R{self.nextr:03d}';self.nextr+=1
    rels.append(nr)
    if a!=r['source'] or b!=r['target']:self.remap.append(dict(old_relation=r['id'],relation=nr['id'],source=a,target=b,openings=[o['id'] for o in oo]))
  # 同一空间对合并，保留既有关系号及P号。
  final=[]
  for r in rels:
   key=(r['type'],frozenset((r['source'],r['target']))) if r['type']!='entrance' else r['id']
   if key in seen:
    seen[key].setdefault('openings',[]).extend(r.get('openings',[]))
    self.remap.append(dict(retired_relation=r['id'],merged_into=seen[key]['id']))
   else:seen[key]=r;final.append(r)
  self.d['relations']=final
  for root,ids in self.continuities.items():
   for i,a in enumerate(ids):
    for b in ids[i+1:]:
     if self.poly(self.s[a]).boundary.intersection(self.poly(self.s[b]).boundary).length>1:
      self.link(a,b,reason='同一连续公共带为避免带孔多边形而作的人工切分，接缝无实体隔墙；仅概念连接，不造门位。',remap=False)
 def link(self,a,b,xy=None,kind='door',reason='原图可见开口',remap=True):
  a=self.sid(a);b=self.sid(b)
  if xy:
   if remap and a in self.children:a=self.which(a,xy)
   if remap and b in self.children:b=self.which(b,xy,a)
  if xy and not remap:
   if b in self.continuities:
    b=min(self.continuities[b],key=lambda k:self.poly(self.s[k]).distance(Point(*xy)))
   if a in self.continuities:
    a=min(self.continuities[a],key=lambda k:self.poly(self.s[k]).distance(Point(*xy)))
  if a==b:return
  pair=frozenset((a,b));r=next((r for r in self.d['relations'] if r['type']=='access' and frozenset((r['source'],r['target']))==pair),None)
  if r is None:
   r=dict(id=f'R{self.nextr:03d}',source=a,target=b,type='access');self.nextr+=1;self.d['relations'].append(r)
  if xy:
   pos=self.orig(*xy)
   if not any(math.dist(pos,o['position_px'])<4 for rr in self.d['relations'] for o in rr.get('openings',[])):
    r.setdefault('openings',[]).append(dict(id=f'P{self.nextp:03d}',kind=kind,position_px=pos));self.nextp+=1
  self.extra.append(dict(relation=r['id'],source=a,target=b,display_position=xy,reason=reason))
 def region(self,name,parents,legend=None):
  ids=[k for p in parents for k in self.children[self.sid(p)]]
  oldparts=[self.oldpoly[self.sid(p)] for p in parents]
  merged=unary_union([p.buffer(.6,join_style=2) for p in oldparts]).buffer(-.6,join_style=2)
  parts=[merged] if merged.geom_type=='Polygon' else list(merged.geoms)
  simple=[]
  for p in parts:
   work=[p]
   while work:
    q=work.pop()
    if q.interiors:
     cy=Polygon(q.interiors[0]).centroid.y;xs=split(q,LineString([(-10,cy),(10000,cy)]))
     work.extend(xs.geoms)
    else:simple.append(q)
  z=dict(id=f'Z{len(self.st.setdefault("regions",[]))+1:02d}',name=name,member_space_ids=ids,polygons_px=[self.points(p) for p in simple],boundary_note='依据本图图例、原片区边界及隔墙作范围近似；非重复计面积节点，不表示内部全部互通。')
  if legend is not None:z['legend_number']=legend
  self.st['regions'].append(z)
 def finish(self):
  self.d['spaces']=list(self.s.values());at.normalize(self.d)
  self.st.update(annotation_mode='regional_coarse',scope_instruction={'user_text':'用38号regional_coarse模式快速标注39—40号房间','interpretation':'清晰围合逐空间粗框，区域概览不重复计面积；专门房名缺失保留unknown，辅助入口无证据不补。'})
  self.st['decomposition']=self.changes;self.st['relation_remapping']=self.remap;self.st['coarse_added_relations']=self.extra
  self.st.setdefault('checks',{}).update(individual_outline_reviewed=False,region_outline_reviewed=False,visual_reviewed=False,connectivity_reviewed=True)
  known={i['space_id'] for i in self.st['name_items']};num=max(int(i['review_id']) for i in self.st['name_items'])
  for s in self.d['spaces']:
   if s['type']=='unknown' and s['id'] not in known:
    num+=1;self.st['name_items'].append(dict(review_id=f'{num:02d}',space_id=s['id'],status='pending',reason='原图缺少专门房名，区域模式不要求猜名。'))
  at.normalize(self.d)
  (self.root/'annotation.json').write_text(json.dumps(self.d,ensure_ascii=False,indent=2)+'\n')
  (self.review/'review_state.json').write_text(json.dumps(self.st,ensure_ascii=False,indent=2)+'\n')
  # 物理端点审计仅用于核验人工选点，不凭几何生成门洞。
  errors=[]
  for r in self.d['relations']:
   for o in r.get('openings',[]):
    p=Point(self.display(o['position_px']));dist=[self.poly(self.s[k]).distance(p) for k in [r['source'],r['target']]]
    if max(dist)>3:errors.append(dict(relation=r['id'],opening=o['id'],distance=dist))
  (self.out/'拆分与点位审计.json').write_text(json.dumps({'decomposition':self.changes,'opening_exceptions':errors},ensure_ascii=False,indent=2)+'\n')
  print(self.n,'spaces',len(self.s),'regions',len(self.st['regions']),'openings',self.nextp-1,'endpoint_exceptions',errors)
