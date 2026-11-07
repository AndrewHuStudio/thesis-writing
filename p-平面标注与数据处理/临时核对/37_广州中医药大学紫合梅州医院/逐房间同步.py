from pathlib import Path
import copy,json,sys
from shapely.geometry import Polygon,Point,LineString
from shapely.ops import split,unary_union
from 逐房间范围 import GROUPS

R=Path(__file__).resolve().parent;P=R.parent.parent/'标注试样'/R.name
B=R/'逐房间补充前备份'
if (R/'review_state.json').exists():
    current_state=json.loads((R/'review_state.json').read_text())
    if current_state.get('room_ids_frozen') and '--rebuild' not in sys.argv:
        raise ValueError('逐房间编号已冻结。请在当前JSON上增量修改；重建需显式--rebuild并先保护用户填写。')
D=json.loads((B/'annotation.json').read_text());original=copy.deepcopy(D)
state=json.loads((B/'review_state.json').read_text())
S={s['id']:s for s in D['spaces']}
polys={sid:Polygon([(y,2484-x) for x,y in s['polygon_px']]) for sid,s in S.items()}
families={sid:[sid] for sid in S};records=[];door_specs=[];audit=[]
next_s=max(int(s[1:]) for s in S)+1
def plain_parts(g):
    if g.is_empty:return []
    if g.geom_type=='Polygon':return [g]
    if hasattr(g,'geoms'):return [p for a in g.geoms for p in plain_parts(a)]
    return []
def no_holes(poly):
    queue=plain_parts(poly);out=[]
    while queue:
        p=queue.pop()
        if not p.interiors:out.append(p);continue
        hole=Polygon(p.interiors[0]);c=hole.representative_point();x0,y0,x1,y1=p.bounds
        pieces=plain_parts(split(p,LineString([(x0-1,c.y),(x1+1,c.y)])))
        if len(pieces)<2:raise ValueError(('cannot split corridor hole',p.bounds))
        queue.extend(pieces)
    return out
def put(sid,poly,name,typ,scope,level):
    item=dict(id=sid,name=name,type=typ,scope=scope,level=level,
              polygon_px=[[2484-y,x] for x,y in list(poly.exterior.coords)[:-1]])
    S[sid]=item;polys[sid]=poly
def new(poly,name,typ,scope,level):
    global next_s
    sid=f'S{next_s:03}';next_s+=1;put(sid,poly,name,typ,scope,level);return sid

# Restore the actual west-side imaging rooms missing from the previous rough block.
g=next(g for g in GROUPS if g['parent']=='S055');polys['S055']=polys['S055'].union(Polygon(g['extra']))
polys['S055']=polys['S055'].union(Polygon([(1722,1175),(1745,1175),(1745,1274),(1722,1274)]))
polys['S084']=polys['S084'].union(Polygon([(2208,1207),(2234,1207),(2234,1275),(2208,1275)]))
S['S084']['polygon_px']=[[2484-y,x] for x,y in list(polys['S084'].exterior.coords)[:-1]]
# The old VIP core included three ordinary rooms. Transfer their envelope before splitting.
vip_rooms=Polygon([(2337,1389),(2422,1389),(2422,1455),(2337,1455)])
move=polys['S081'].intersection(vip_rooms)
polys['S080']=polys['S080'].union(vip_rooms);polys['S081']=polys['S081'].difference(vip_rooms)
S['S081']['polygon_px']=[[2484-y,x] for x,y in list(polys['S081'].exterior.coords)[:-1]]
# The old coarse boundary cut across rooms. The clearly drawn cross-wall at y=1350
# separates the two corridor systems; room polygons are clipped only to that wall.
envelope=unary_union([polys['S082'],polys['S083'],Polygon([(2492,1264),(2660,1264),(2660,1455),(2492,1455)])])
polys['S082']=envelope.intersection(Polygon([(0,0),(3236,0),(3236,1350),(0,1350)]))
polys['S083']=envelope.difference(polys['S082'])

for g in GROUPS:
    sid=g['parent'];old=copy.deepcopy(S[sid]);parent=polys[sid];remaining=parent;children=[]
    for i,spec in enumerate(g['rooms']):
        intended=Polygon(spec['polygon']);p=intended.intersection(remaining)
        parts=no_holes(p);parts=[p for p in parts if p.area>120]
        if not parts:
            audit.append(dict(parent=sid,event='spec_clipped_empty',index=i,bounds=intended.bounds));continue
        for part in parts:
            typ=spec['type'];name=spec['name'] or '名称未确认'
            level='core_block' if typ=='vertical_core' else 'open_space' if typ=='corridor' else 'room'
            if g['mode']=='first' and not children:
                child=sid;put(child,part,name,typ,old['scope'],level)
            else:child=new(part,name,typ,old['scope'],level)
            children.append(child);door_specs.append(dict(space_id=child,parent=sid,**spec))
        remaining=remaining.difference(intended)
        if p.area/intended.area<.7:audit.append(dict(parent=sid,event='clipped_spec',index=i,ratio=p.area/intended.area))
    residuals=sorted([p for p in no_holes(remaining) if p.area>120],key=lambda p:-p.area)
    circulation=[]
    if g['mode']!='first':
        if not residuals:raise ValueError(('no retained parent',sid))
        if g['mode']=='corridor':typ='corridor';level='open_space';name=g['label']
        else:typ=old['type'];level='core_block' if typ=='vertical_core' else 'room';name=g['label']
        put(sid,residuals[0],name,typ,old['scope'],level);circulation.append(sid)
        residuals=residuals[1:]
    for i,part in enumerate(residuals,1):
        if g['mode']=='main' and old['type']=='vertical_core':
            typ='vertical_core';name=g['label']+'前区';level='core_block'
        else:typ='corridor';name=g['label']+'连接通道';level='open_space'
        child=new(part,name,typ,old['scope'],level);circulation.append(child)
    families[sid]=list(dict.fromkeys([sid]+children+circulation))
    records.append(dict(parent_id=sid,previous_name=old['name'],previous_type=old['type'],
        previous_level=old['level'],mode=g['mode'],room_ids=children,
        circulation_ids=circulation,all_ids=families[sid],
        previous_polygon_px=old['polygon_px']))

# Transfer the existing relations and their stable opening IDs to the actual new endpoints.
oldrels=copy.deepcopy(D['relations']);next_r=max(int(r['id'][1:]) for r in oldrels if r['id'].startswith('R'))+1
next_p=1+max(int(o['id'][1:]) for r in oldrels for o in r.get('openings',[]))
relations=[];relation_map={};point_log=[];deferred=[]
def fresh_r():
    global next_r
    rid=f'R{next_r:03}';next_r+=1;return rid
def relationship(a,b,typ='access',oid=None,rid=None,reason=''):
    key=(typ,tuple(sorted([a,b])))
    if key not in relation_map:
        rr=dict(id=rid or fresh_r(),source=a,target=b,type=typ);relation_map[key]=rr;relations.append(rr)
    rr=relation_map[key]
    if oid:rr.setdefault('openings',[]).append(oid)
    if reason:audit.append(dict(relation_id=rr['id'],source=a,target=b,event='relation',reason=reason))
    return rr
def nearest_member(parent,pt):
    return min(families[parent],key=lambda sid:(polys[sid].distance(pt),polys[sid].boundary.distance(pt),polys[sid].area))
for rel in oldrels:
    a,b=rel['source'],rel['target']
    if rel['type']=='entrance':
        x,y=rel['position_px'];pt=Point(y,2484-x)
        rel['target']=nearest_member(b,pt);relations.append(rel);continue
    if rel.get('openings'):
        first=True
        for opening in rel['openings']:
            x,y=opening['position_px'];pt=Point(y,2484-x)
            aa,bb=nearest_member(a,pt),nearest_member(b,pt)
            if aa==bb:raise ValueError(('opening became self edge',opening['id']))
            rr=relationship(aa,bb,rel['type'],opening,rel['id'] if first else None)
            first=False
            point_log.append(dict(opening_id=opening['id'],old_relation=rel['id'],relation_id=rr['id'],source=aa,target=bb,basis='原图已有门洞，沿用点位；按拆分后的轮廓更新端点。'))
    else:
        if a is None:continue
        changed={g['parent'] for g in GROUPS}
        if polys[a].distance(polys[b])<=12 or rel['type']=='service' or (a not in changed and b not in changed):
            relationship(a,b,rel['type'],rid=rel['id'],reason='沿用原关系；保留端点仍接触或为既有服务关系。')
        else:
            def family_corridors(parent):
                return [sid for sid in families[parent] if S[sid]['type']=='corridor'] or [parent]
            choices=[(polys[x].distance(polys[y]),-polys[x].intersection(polys[y]).length,x,y)
                     for x in family_corridors(a) for y in family_corridors(b) if x!=y]
            distance,_,aa,bb=min(choices)
            if distance<=4:
                relationship(aa,bb,rel['type'],rid=rel['id'],reason='沿用原已判读的概念连接，端点移至该功能块实际连续的通道分段。')
            else:deferred.append(dict(**rel,reason='原粗块拆分后该空间对不再直接相邻；撤回直接边，以逐房间门洞及实际通道重建。'))

for record in records:
    # These are subdivisions of one continuous circulation area, with no physical door.
    ids=record['circulation_ids']
    for i,a in enumerate(ids):
        for b in ids[i+1:]:
            if polys[a].intersection(polys[b]).length>3:
                relationship(a,b,reason='同一连续交通区域的几何分段，无实体门洞，不生成P点。')

for spec in door_specs:
    sid=spec['space_id'];parent=spec['parent'];p=polys[sid]
    if spec['type'] in ('corridor','vertical_core'):continue
    if not spec['door'] and not spec['connected']:continue
    target=spec.get('target')
    if target:
        candidates=families[target]
    else:
        candidates=[s for s in families[parent] if s!=sid and
            (S[s]['type']=='corridor' or (s==parent and next(g for g in GROUPS if g['parent']==parent)['mode']=='main'))]
    candidates=[s for s in candidates if s!=sid]
    if not candidates:
        deferred.append(dict(space_id=sid,reason='该处可见房间，但通行端点尚不能从粗图明确定位。'));continue
    if spec['door']:
        q=Point(spec['door']);other=min(candidates,key=lambda s:(polys[s].distance(q),polys[s].boundary.distance(q)))
        distance=max(p.boundary.distance(q),polys[other].boundary.distance(q))
        if distance>12:
            deferred.append(dict(space_id=sid,target=other,door=spec['door'],reason='门位人工判读与粗轮廓偏差超12px；待目检调整，未生成点或连接。'));continue
        # Existing points on this same pair and door stay stable; avoid duplicate dots.
        rr=relationship(sid,other,reason='逐房间复核：原图可辨门扇／开口。')
        if any(Point(o['position_px'][1],2484-o['position_px'][0]).distance(q)<12 for o in rr.get('openings',[])):continue
        opening=dict(id=f'P{next_p:03}',kind='door',position_px=[2484-q.y,q.x]);next_p+=1
        rr.setdefault('openings',[]).append(opening)
        point_log.append(dict(opening_id=opening['id'],relation_id=rr['id'],source=sid,target=other,basis='本轮逐房间原图目检的近似门洞；未从共墙中点自动生成。'))
    else:
        other=min(candidates,key=lambda s:p.distance(polys[s]))
        if p.distance(polys[other])<=5:
            relationship(sid,other,reason='原图房门／走道组织可辨，粗轮廓不支持精确门心，保留概念连接。')
        else:deferred.append(dict(space_id=sid,reason='可见房间已标记；可达关系无可靠直接证据，暂空。'))

# Explicitly connect the new room-level foyer/corridor fragments to their continuous neighbours.
corridors=[sid for sid,s in S.items() if s['type']=='corridor']
for i,a in enumerate(corridors):
    for b in corridors[i+1:]:
        if polys[a].intersection(polys[b]).length>5:
            relationship(a,b,reason='原图连续通道；几何接触仅用于定位已判读的通道分段，不向相邻房间自动补边。')

# S271 was a narrow geometric remainder of the same corridor, not another room.
if 'S271' in S and S['S271']['type']=='corridor' and 'S271' in families['S082']:
    merged=polys['S082'].union(polys['S271'])
    if merged.geom_type!='Polygon' or merged.interiors:raise ValueError('corridor merge needs review')
    polys['S082']=merged;S['S082']['polygon_px']=[[2484-y,x] for x,y in list(merged.exterior.coords)[:-1]]
    del S['S271'];del polys['S271']
    for rel in relations:
        for key in ('source','target'):
            if rel[key]=='S271':rel[key]='S082'
    unique=[];seen={}
    for rel in relations:
        if rel['source']==rel['target']:continue
        key=(rel['type'],tuple(sorted([str(rel['source']),str(rel['target'])])))
        if rel['type']=='entrance' or key not in seen:unique.append(rel);seen[key]=rel
        else:seen[key].setdefault('openings',[]).extend(rel.get('openings',[]))
    relations=unique
    for rel in relations:
        if rel.get('openings')==[]:rel.pop('openings')
    for rec in records:
        for key in ('all_ids','circulation_ids'):
            rec[key]=[sid for sid in rec[key] if sid!='S271']
    audit.append(dict(event='retired_corridor_fragment',space_id='S271',merged_into='S082',reason='同一连续通道的狭长余片合并；不作为额外空间，编号不复用。'))
for sid in ['S001','S003','S006','S007','S018','S065','S066','S078']:
    S[sid]['level']='room'
D['spaces']=sorted(S.values(),key=lambda s:int(s['id'][1:]));D['relations']=relations
sys.path.insert(0,'/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts')
from annotation_tools import normalize
normalize(D)
known={i['space_id']:i for i in state['name_items']};number=max(int(i['review_id']) for i in state['name_items'])
for rec in records:
    if rec['parent_id'] in known:
        known[rec['parent_id']]['split_history']=dict(previous_scope=rec['previous_name'],children=rec['all_ids'],note='保留原核对号在原S号；其余可见房间新编号续号，未将组名当作小房具体名称。')
for s in D['spaces']:
    if s['type']=='unknown' and s['id'] not in known:
        number+=1;item=dict(review_id=f'{number:02}',space_id=s['id'],status='pending',
            candidates=[],evidence='原图可辨房间轮廓，具体房名缺失或不可读；按用户要求独立标记，不强行补名。',confidence='低')
        state['name_items'].append(item);known[s['id']]=item
state['scope']='逐房间：有可辨隔墙即单列；无名称不合并；交通核保留较粗轮廓；不拆卫生间隔断、家具、床位或柜台。'
state['user_granularity_instruction']='很多房间信息看不到，只能用较粗轮廓；即使没有名字也应该逐个标记。'
state['no_detail_required']=['家具、床位、卫生间隔断不当作独立房间','无法判定的交通核内部精确路线']
state['checks'].update(connectivity_reviewed=False,visual_reviewed=False)
state['checks'].pop('visual_note',None)
state['room_split_map']='逐房间拆分对应.json'
(P/'annotation.json').write_text(json.dumps(D,ensure_ascii=False,indent=2)+'\n')
(R/'review_state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
(R/'逐房间拆分对应.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
(R/'逐房间连通审计.json').write_text(json.dumps(dict(events=audit,opening_points=point_log,deferred=deferred),ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(spaces=len(S),new_spaces=len(S)-len(original['spaces']),rooms=sum(s['level']=='room' for s in S.values()),
    unknown=sum(s['type']=='unknown' for s in S.values()),relations=len(relations),openings=next_p-1,
    deferred=len(deferred),geometry_events=[a for a in audit if a.get('event') in ('spec_clipped_empty','clipped_spec')]),ensure_ascii=False))
