from pathlib import Path
import json,copy,sys
from shapely.geometry import Polygon,Point
from shapely.ops import unary_union

R=Path(__file__).resolve().parent;P=R.parent.parent/'标注试样'/R.name
BASE=R/'20261107_连通分析前备份_134616'
if (R/'review_state.json').exists() and json.loads((R/'review_state.json').read_text()).get('connectivity_update_frozen') and '--rebuild' not in sys.argv:
    raise ValueError('本轮连通更新已冻结；后续在当前JSON上增量编辑，不从历史备份覆盖用户新修改。')
D=json.loads((BASE/'annotation.json').read_text());state=json.loads((BASE/'review_state.json').read_text())
S={s['id']:s for s in D['spaces']};rels=D['relations']
audit={'scope':'逐房间粗轮廓；不把缺名、缺门位当作不通，不以全图连通为目标',
       'added_relations':[],'corrected_openings':[],'retired_openings':[],
       'classification_corrections':[],'geometry_corrections':[]}
def poly(sid):return Polygon([(y,2484-x) for x,y in S[sid]['polygon_px']])
def store_poly(sid,p):
    if p.geom_type!='Polygon' or p.interiors:raise ValueError((sid,'invalid outline form'))
    S[sid]['polygon_px']=[[2484-y,x] for x,y in list(p.exterior.coords)[:-1]]
def rel(a,b):return next((r for r in rels if r['type']=='access' and {r['source'],r['target']}=={a,b}),None)
next_r=max(int(r['id'][1:]) for r in rels if r['id'].startswith('R'))+1
next_p=max(int(o['id'][1:]) for r in rels for o in r.get('openings',[]))+1
def access(a,b,reason,point=None,kind='door',basis='布局推断'):
    global next_r,next_p
    r=rel(a,b)
    if not r:
        r={'id':f'R{next_r:03}','source':a,'target':b,'type':'access'};next_r+=1;rels.append(r)
    if point:
        o={'id':f'P{next_p:03}','kind':kind,'position_px':[2484-point[1],point[0]]};next_p+=1
        r.setdefault('openings',[]).append(o)
        audit.setdefault('new_openings',[]).append({'relation_id':r['id'],**o,'evidence':reason})
    audit['added_relations'].append(dict(relation_id=r['id'],source=a,target=b,basis=basis,reason=reason,
                                         has_localized_opening=bool(r.get('openings'))))
    return r

# S097 is a subdivided support strip, not a demonstrably continuous corridor.
old=copy.deepcopy(S['S097'])
S['S097'].update(name='名称未确认',type='unknown',level='functional_block')
audit['classification_corrections'].append(dict(space_id='S097',before=old,
    reason='放大原图可见内部横向实体分隔；不能继续把整条残余范围视为贯通走道。保留粗范围及编号，功能unknown。'))
for sid in ['S134','S137']:
    old=copy.deepcopy(S[sid]);S[sid].update(name='名称未确认',type='unknown',level='room')
    audit['classification_corrections'].append(dict(space_id=sid,before=old,
        reason='原图该白色窄区两端有分隔/家具界面，不能证明是贯通走道；保留独立粗轮廓，恢复unknown。'))
for rid in ['R069','R070']:
    old=next(r for r in rels if r['id']==rid);rels.remove(old)
    audit.setdefault('removed_relations',[]).append(dict(before=old,
        reason='逐房间拆分后该边由几何邻近转挂至S134/S137，回看原图无直接通行证据；不将共墙或家具界面视为门。'))
old=copy.deepcopy(S['S207'])
S['S207'].update(name='楼梯交通核（局部）',type='vertical_core',level='core_block')
audit['classification_corrections'].append(dict(space_id='S207',before=old,
    reason='原图该长条内是楼梯／交通核构造，原卫生间类别不成立；不将梯段当作卫生间房间。'))

# Explicit south-side public strip outside the two accessible toilets.
before=copy.deepcopy(S['S089']['polygon_px'])
strip=Polygon([(1595,865),(1691,865),(1691,877),(1595,877)])
others=unary_union([poly(sid) for sid in S if sid!='S089'])
addition=strip.difference(others)
store_poly('S089',poly('S089').union(addition))
audit['geometry_corrections'].append(dict(space_id='S089',before=before,
    reason='补齐卫生间南侧图面明确的连续公共带；避开既有房间/核心边界，未拆新空间、未重排编号。'))

# P006 was on a solid west wall. The original shows a south-facing door instead.
r=next(r for r in rels if any(o['id']=='P006' for o in r.get('openings',[])))
audit['corrected_openings'].append(dict(opening_id='P006',before=copy.deepcopy(r),
    reason='原西侧点落在共墙；实际南向门进入卫生间南侧公共带，保留P006编号并更正端点/位置。'))
r['source']='S089';r['target']='S129'
o=next(o for o in r['openings'] if o['id']=='P006');o['position_px']=[2484-865,1610]

# P140 duplicated an assumed western entrance on a solid wall. P028 is the actual
# entrance to the shared forecourt; keep it, and connect the forecourt conceptually.
r=next(r for r in rels if any(o['id']=='P140' for o in r.get('openings',[])))
audit['retired_openings'].append(dict(opening_id='P140',before=copy.deepcopy(r),
    reason='原点在西侧实体墙上；实际西侧入口已由P028记录。经共用前区到S238，不再保存虚构的第二道门。',
    retained_actual_opening='P028'))
rels.remove(r)

access('S130','S089','原图无障碍卫生间南向门接南侧公共带。',point=(1668,865),basis='可见门洞')
access('S138','S089','儿科输液西侧前区左缘与妇科南侧连接通道连续；两者为粗轮廓分段，无实体门。',basis='图面连续')
access('S138','S031','儿科输液大室西侧有明确门扇，通向西侧前区。',point=(1950,757),basis='可见门洞')
access('S175','S054','专家门诊南排卫生间东侧门朝公共通道。',point=(1154,1410),basis='可见门洞')
access('S255','S080','VIP卫生间南向门通向内部大厅；不经北侧诊室。',point=(2398,1306),basis='可见门洞')
access('S077','S085','医技东南侧卫生间东向门开向公共通道。',point=(2110,1318),basis='可见门洞')

access('S009','S007','收费工作带与背后的开放办公构成工作人员后场，按柜台/办公组织推断可达；不增加大厅穿柜台关系。')
access('S032','S089','妇科侧卫生间经南侧共用前区接公共带；粗轮廓内未逐个表达前室转折，保留概念连接。')
access('S045','S019','药房西侧卫生间向北侧候药公共区组织出入；入口前区可辨，但精确门位不清。')
access('S049','S048','药房东侧卫生间组共用前区接楼梯交通核前区；不推断穿过另一卫生间。')
access('S186','S055','放射科中部卫生间右/南侧的前区通向内部交通；定位范围不够可靠，仅记概念关系。')
access('S207','S056','同一交通核内被粗轮廓分开的楼梯局部，与整体核内前区相接；不定位内部路线。',basis='交通核整体')
access('S208','S056','原图卫生间前区朝交通核内公共前室；具体门位不清，不通过楼梯墙体造门。')
access('S209','S056','交通核南部卫生间上侧与共用核前区组织出入；具体分隔小门不清。')
access('S210','S086','医技南侧卫生间的西侧前区面向东翼公共通道；门位不清，保留概念连接。')
access('S211','S085','东南卫生间中部单元面向东侧公用前区/通道，入口细节未清晰表达。')
access('S219','S039','急诊斜向电梯交通核直接面对急诊通道；电梯内部门不另作房间门洞。',basis='交通核面向通道')
access('S038','S232','急诊卫生间旁交通核南端前区直接朝连续公共通道，内部楼梯路线不细分。')
access('S238','S038','急诊西侧房组上缘的共用前区与交通核北端前区相接；按布局组织记录，不穿过实体楼梯墙。')
access('S238','S241','两粗轮廓之间的实际共用前区连续；P028为该组真正的西侧对外入口。',basis='共用前区连续')
access('S236','S238','急诊北侧左卫生间经其下方共用前区出入，前区部分包含于S238粗范围；不定位隐藏小门。')
access('S237','S038','急诊北侧右卫生间朝交通核北侧共用前室出入；该前区在粗轮廓中并入交通核。')
access('S240','S232','急诊核东南侧房组/卫生间前区南向公共通道组织出入；不推定具体功能或门位。')
access('S247','S084','留观南侧小卫生间西侧入口前区面向东部通道；保持粗轮廓，门位不清。')
access('S250','S091','东侧配套房组前公共带，经交通核南侧短前区接留观南侧通道；图面连续，短前区未另成节点。',basis='图面连续及布局推断')
access('S044','S250','东侧房组最上间门口朝西侧公共带；沿图面房组通行组织记录，门心不定位。')
access('S248','S250','东侧房组中间单元西侧门口面向公共带；其独立外门继续保留。')
access('S249','S250','东侧房组下方单元的门口朝公共带；无可靠门心，不画红点。')
access('S263','S082','肠道门诊卫生间经南/东侧共用前区接内部走道；不把共墙或设施当人员门。')
access('S143','S034','成人输液前区与输液大室在原图中连续，粗轮廓拆开后漏记连接；此分界不对应实体门。',basis='图面连续')
access('S133','S089','妇科南侧卫生间组的左单元南向门朝公共带。',point=(1705,841),basis='可见门洞')
access('S133','S089','同组右单元另有南向门；一个空间对保留一条关系，分别记录两道门。',point=(1735,841),basis='可见门洞')
access('S021','S089','卫生间南侧公共带向西连续接中央公共门厅，补齐粗轮廓交界的连接。',basis='图面连续')
access('S040','S233','急诊东端公共带与住院门厅连续，二者粗轮廓分段不是实体隔墙。',basis='图面连续')
access('S053','S067','药房后场通道南侧开门进入专家门诊西侧纵向通道；该窄通道已从诊室排中单独保留。',point=(792,1206.5),basis='可见门洞')
access('S055','S085','放射科中部纵向内通道南端与医技外通道连续，原粗块门位转挂小房后遗漏此主通道关系。',basis='图面连续')
access('S084','S270','北侧肠道门诊共用前区西端朝东部公共通道组织出入；局部粗轮廓含前室，不定位不清楚的小门。')
access('S088','S232','急诊卫生间组西侧窄公共带在南端接急诊横向公共通道，图面连续，不把分段边界当门。',basis='图面连续')

# Keep original question numbers and prior wording, but remove noncritical questions
# from mandatory completion at the agreed coarse-outline scope.
for item in state['connectivity_items']:
    item['previous_pending_question']=dict(question=item.get('question'),reason=item.get('reason'))
    if item['review_id']=='K01':
        item.update(status='not_required',reason='S066的独立外门E06已明确。内部是否另接专家门诊无可靠证据，但不影响其可达；本轮保留未知连接，不确认直通或不通。',
                    resolution='独立入口保留；未补S066—S067；本轮不要求额外内部连接答案。')
    elif item['review_id']=='K02':
        item.update(status='not_required',reason='两厚边界单元的具体性质和可达信息在原图缺失。本轮保留各自编号、粗轮廓及unknown，不编门或连接，不要求猜测用途。',
                    resolution='信息缺失单元保留；关系留空不代表不相通。')
new_review_id=1+max(int(i['review_id']) for i in state['name_items'])
for sid in ['S097','S134','S137']:
    state['name_items'].append(dict(review_id=f'{new_review_id:02}',space_id=sid,status='pending',
        evidence='原通道分类撤回：有分隔或家具界面，缺乏贯通证据；用途不清，按信息缺失范围保留。'))
    new_review_id+=1
state['scope_instruction']=dict(user_text='请参考36的标注方法看37是否完成；分析连通性',
    interpretation='无名独立空间保留unknown；按图面通行组织补概念access，只有可定位真实门洞才画P点；不要求所有未知名称补齐或每个辅助小间全连通。',
    requires_exact_room_names_this_round=False)
state['checks'].update(connectivity_reviewed=True,visual_reviewed=False)
state['connectivity_audit_file']='本轮连通分析审计.json'
state.setdefault('retired_opening_ids',{})['P140']='撤回墙上误点；该组真实入口保留P028。'
state['room_granularity_counts']={'spaces':275,'room_level':sum(s['level']=='room' for s in S.values()),
                                 'unknown':sum(s['type']=='unknown' for s in S.values())}
sys.path.insert(0,'/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts')
from annotation_tools import normalize
normalize(D)
for r in rels:
    for o in r.get('openings',[]):
        p=Point(o['position_px'][1],2484-o['position_px'][0])
        distance=max(poly(s).boundary.distance(p) for s in (r['source'],r['target']))
        if distance>8:raise ValueError((o['id'],distance))
(P/'annotation.json').write_text(json.dumps(D,ensure_ascii=False,indent=2)+'\n')
(R/'review_state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
(R/'固定核对映射.json').write_text(json.dumps(state['name_items'],ensure_ascii=False,indent=2)+'\n')
(R/'本轮连通分析审计.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
print('added access',len({r['relation_id'] for r in audit['added_relations']}),'total access',sum(r['type']=='access' for r in rels),
      'openings',sum(len(r.get('openings',[])) for r in rels),'new IDs through',next_p-1)
