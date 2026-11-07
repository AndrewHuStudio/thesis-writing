"""Incremental additions to 38; all original identifiers remain traceable."""
from pathlib import Path
import copy,json
from shapely.geometry import Polygon,box
from shapely.ops import unary_union

RUN=Path(__file__).resolve().parent
R=RUN.parent
P=R.parent.parent/'标注试样'/R.name
D=json.loads((RUN/'修改前备份/annotation.json').read_text())
ST=json.loads((RUN/'修改前备份/review_state.json').read_text())
S={s['id']:s for s in D['spaces']}
AUDIT={'added_spaces':[],'updated_spaces':[],'added_relations':[],'evidence':[]}

def points(poly):
    assert poly.geom_type=='Polygon' and poly.is_valid and not poly.interiors
    return [[round(x,2),round(y,2)] for x,y in list(poly.exterior.coords)[:-1]]

def new_space(sn,geom,source,evidence):
    t=copy.deepcopy(S[source]);t.update(id=sn,name='名称未确认',type='unknown',
        level='room',polygon_px=points(geom));t.pop('area_ratio',None)
    D['spaces'].append(t);S[sn]=t
    AUDIT['added_spaces'].append({'id':sn,'split_from':source,'evidence':evidence})

# 原图左外墙、楼梯前区旁的小间，有明确实体围合和开向通道的门。
room=box(1660.44,244.5,1708.0,283.5)
assert Polygon(S['S059']['polygon_px']).covers(room)
new_space('S153',room,'S059','感染门诊西侧小间.png：通道中的围合小间，门扇可辨，具体用途无字。')
old=copy.deepcopy(S['S059']);S['S059']['polygon_px']=points(Polygon(old['polygon_px']).difference(room))
AUDIT['updated_spaces'].append({'id':'S059','reason':'从原公共区扣除独立小间S153'})
# 两扇门和实体横隔墙可辨；各自有实体范围，非家具、卫生器具分隔。
old=Polygon(S['S046']['polygon_px']);cut=550.0
new_space('S154',old.intersection(box(cut,740,600,800)),'S046',
    '急诊中央小间.png：原S046中可见横隔墙及独立门，分出上部小间。')
S['S046']['polygon_px']=points(old.intersection(box(480,740,cut,800)))
AUDIT['updated_spaces'].append({'id':'S046','reason':'保留较大原单元，独立上间续编S154'})

next_r=max(int(r['id'][1:]) for r in D['relations'] if r['id'].startswith('R'))+1
next_p=max(int(o['id'][1:]) for r in D['relations'] for o in r.get('openings',[]))+1
for a,b,pos in [('S153','S059',[1708.0,272.0]),('S154','S044',[568.0,755.73]),
                ('S046','S044',[529.0,755.73])]:
    rel={'id':f'R{next_r:03d}','source':a,'target':b,'type':'access',
        'openings':[{'id':f'P{next_p:03d}','kind':'door','position_px':pos}]}
    D['relations'].append(rel);AUDIT['added_relations'].append(copy.deepcopy(rel));next_r+=1;next_p+=1

# 儿童发热图例10对应的上排诊疗小间；此处仅校正所属区域，房名保持缺失。
child=[61,62,64,66,67,68]
for n in child:
    sn=f'S{n:03d}'
    if S[sn]['scope']!='pediatric_fever_outpatient':
        AUDIT['updated_spaces'].append({'id':sn,'reason':'按儿童发热公共区及图例10校正scope；不推断房间专门功能'})
        S[sn]['scope']='pediatric_fever_outpatient'

# 当前区域粗轮廓范围：该楼梯的两种门向均进入同一公共交通网络。
for item in ST['connectivity_items']:
    if item['review_id']=='K01':
        item['previous_question']=copy.deepcopy(item)
        item.update(status='not_required',reason='区域粗轮廓复核：S038相邻S002、S039，二者本已相连；未画清的小门方向不改变急诊／输液主要交通组织。本轮保留R015为面向公共交通侧的布局推断，无可靠门位不加P点；不记为用户确认具体门向。')
AUDIT['evidence'].append({'relation_id':'R015','source':'S038','target':'S002','kind':'布局推断',
    'basis':'楼梯整体紧贴医疗街侧，输液公共区另有清晰直通医疗街的双扇门；按粗轮廓保留概念联系，不表达精确门向。'})
ST['annotation_mode']='regional_coarse'
ST['checks'].update(individual_outline_reviewed=True,region_outline_reviewed=False,
    connectivity_reviewed=True,visual_reviewed=False)
ST['scope_instruction']={'user_text':'参照36—37号补充38号；面向区域级场景需要粗轮廓',
    'interpretation':'无名独立单元逐个粗框；图例区域有概览外轮廓；主要通行组织复核；原图缺名不作为必须补齐的任务。',
    'requires_exact_room_names_this_round':False}
for idx,sn in enumerate(['S153','S154'],117):
    ST['name_items'].append({'review_id':str(idx),'space_id':sn,'status':'pending',
        'manual_confirmation_required':False,'disposition':'missing_in_source_deferred_completion'})
ST['retired_space_ids']={'S023':'旧差集产生的1.49px条带，已归并S024／S025；退役不复用。'}

# 区域边界只作为概览；不增加核心空间节点，不再次计面积。
def ids(numbers):return [f'S{n:03d}' for n in numbers]
infu=set([37,38,39,40,41])
zone_numbers={1:[1,4,5,6,7,8,9,151,152],2:[10],3:[11,12,14,15],
    4:[n for n in range(26,59) if n not in infu]+[154],5:sorted(infu),6:[2,3],
    7:[94]+[n for n in range(95,113) if S[f'S{n:03d}']['scope']=='radiology'],
    8:[n for n in range(114,137) if S[f'S{n:03d}']['scope']=='functional_diagnostics']+
        [138,139,141,142,143,144,145,146,147,149],
    9:[59,60,63,65,69,70,71,72,73,74,75,76,77,78,79,80,81,153],
    10:child,11:list(range(82,94))}
names={1:'门诊大厅',2:'候药大厅',3:'药房',4:'急诊急救室',5:'输液室',6:'医疗街',
    7:'放射影像室',8:'功能检测室',9:'发热门诊',10:'儿童发热门诊',11:'肠道门诊'}
colors=['#2563eb','#0891b2','#7c3aed','#dc2626','#ea580c','#475569',
    '#0f766e','#65a30d','#b45309','#db2777','#4f46e5']
regions=[]
for number in range(1,12):
    members=ids(zone_numbers[number]);geom=unary_union([Polygon(S[sn]['polygon_px']) for sn in members])
    # 仅闭合概念标注坐标约1—4px的小缝；不取大凸包跨过邻区。
    geom=geom.buffer(2.3,join_style='mitre').buffer(-2.3,join_style='mitre')
    parts=[geom] if geom.geom_type=='Polygon' else list(geom.geoms)
    rings=[]
    for part in parts:
        if part.area<1:continue
        if part.interiors:
            # 环形区域保留洞：沿洞内部切分外轮廓，避免覆盖非本区空间。
            from shapely.geometry import LineString
            from shapely.ops import split
            pending=[part]
            while pending:
                g=pending.pop()
                if not g.interiors:rings.append(points(g));continue
                x=Polygon(g.interiors[0]).representative_point().x
                pending.extend(split(g,LineString([(x,g.bounds[1]-1),(x,g.bounds[3]+1)])).geoms)
        else:rings.append(points(part))
    region={'id':f'Z{number:02d}','name':names[number],'legend_number':number,
        'member_space_ids':members,'polygons_px':rings,'color':colors[number-1],
        'label_px':[1900,250+number*62],
        'boundary_note':'按图例片区及可辨房间／公共带近似，区域概览不表示内部各间的具体用途，也不再次计面积。'}
    regions.append(region)
ST['regions']=regions
ST['region_membership_unassigned']=[sn for sn in S if not any(sn in r['member_space_ids'] for r in regions)]
ST['region_membership_note']='未列入图例区域的医技外缘／公共配套节点保留原scope；不为补齐区域覆盖而强行归入某个科室。'
ST['task_status']={'layout_geometry_reviewed':True,'regional_legend_recorded':True,
    'primary_connectivity_pending':[],'room_names_missing':118,'room_name_completion_performed':False,
    'full_semantic_annotation_complete':False}
ST['current_scope_review']={'individual_outline_complete':True,'primary_connectivity_complete':True,
    'exact_names_required':False,'unresolved_information_not_negative':True,
    'accepted_as_current_scope_complete':False,'scope':'逐空间粗轮廓＋11个图例区域外轮廓＋主要连通；待实际目检后收尾'}
(P/'annotation.json').write_text(json.dumps(D,ensure_ascii=False,indent=2)+'\n')
(R/'review_state.json').write_text(json.dumps(ST,ensure_ascii=False,indent=2)+'\n')
(RUN/'增量补充依据.json').write_text(json.dumps(AUDIT,ensure_ascii=False,indent=2)+'\n')
print('spaces',len(D['spaces']),'relations',len(D['relations']),'openings',next_p-1,'regions',len(regions))
print('unassigned',ST['region_membership_unassigned'])
