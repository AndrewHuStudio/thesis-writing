from pathlib import Path
import json, sys, copy
from shapely.geometry import Polygon, Point, LineString, box
from shapely.ops import unary_union

WORK = Path(__file__).resolve().parent
SAMPLE = WORK.parent.parent / '标注试样' / WORK.name
sys.path.insert(0, '/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts')
import annotation_tools as at
from review_workflow import load_state, save_state

path = SAMPLE / 'annotation.json'
data = json.loads(path.read_text())
spaces = {s['id']: s for s in data['spaces']}
meta = json.loads((WORK / '空间工作索引.json').read_text())
pending = json.loads((WORK / '核对号对应.json').read_text())
state_path = WORK / 'review_state.json'
assert not state_path.exists(), '仅首次补充运行，续作请增量更新'
audit = {'inferred_access': [], 'visible_openings': [], 'withdrawn_relations': [],
         'deferred_details': [], 'geometry_changes': []}

# 内部检查通道外围没有可辨开口；撤回旧边等待关键核对，保留原R号供确认后恢复。
old = next(r for r in data['relations'] if r['id'] == 'R006')
audit['withdrawn_relations'].append(dict(old, reason='原图内部通道南端为连续墙线，尚未找到接外围候诊的明确开口'))
data['relations'].remove(old)
next_r = max(int(r['id'][1:]) for r in data['relations'] if r['id'].startswith('R')) + 1
next_p = 1


def access(a, b, reason, evidence='布局推断'):
    global next_r
    pair = {a, b}
    found = [r for r in data['relations'] if r['type'] == 'access' and {r['source'], r['target']} == pair]
    if found:
        return found[0]
    r = {'id': f'R{next_r:03d}', 'source': a, 'target': b, 'type': 'access'}
    next_r += 1
    data['relations'].append(r)
    audit['inferred_access'].append({'relation_id': r['id'], 'source': a, 'target': b,
                                    'evidence': evidence, 'reason': reason})
    return r


def row(ids, corridor, reason):
    for sid in ids.split():
        access(sid, corridor, reason)


# 无精确门位的关系保留为概念连接；不为柜台和小间逐一补门。
row('S047 S050 S053 S055 S057 S051 S056', 'S048',
    '妇科诊室桌台朝向内侧候诊通道，成排诊疗单元围绕该通道组织；图纸未逐室表达可定位门扇。')
row('S088 S094 S097 S099 S102 S104 S090 S095 S098 S100 S103', 'S089',
    '综合门诊两列诊疗家具面对中间灰色候诊通道，通道南端连续汇入医疗街；只推断各诊疗单元对该通道可达。')
row('S123 S125 S127 S124 S126', 'S120',
    '儿科两侧诊室围绕中央连续候诊区组织，桌台朝向候诊侧；未据此推断诊室彼此互通。')
access('S045', 'S048', '妇科交通核南侧与候诊交通带衔接，交通核按整体节点保存。')
access('S066', 'S067', '西侧电梯组的前沿面对医疗街，电梯门厅并入交通核。')
access('S076', 'S070', '中部西侧灰色楼梯前室外侧直接面向同侧医疗街，保留整体交通核连接。')
access('S077', 'S075', '中部东侧灰色楼梯前室外侧直接面向同侧医疗街，保留整体交通核连接。')
access('S101', 'S075', '综合门诊电梯组西侧与中东段医疗街灰色交通带衔接。')
access('S122', 'S120', '儿科灰色交通核面向儿童候诊大厅，整体记录，不展开内部小间。')
access('S134', 'S137', '儿童输液座椅区与南侧候诊带之间未见完整隔墙，图面连续。', '区域连续')
access('S137', 'S120', '儿童输液南侧候诊带从长条房间南端绕入儿科等候大厅，白色开放候诊区域连续。', '区域连续')
access('S146', 'S115', '输液大厅北侧两组辅助房之间留有窄交通颈，向北衔接医疗街；不把服务窗口当作入口。')
access('S147', 'S146', '输液灰色交通核西南侧面对输液座椅区域，按整体核心与大厅连接。')
row('S149 S151 S152', 'S156', '输液支持房东侧面对急诊灰色候诊通道，依据朝向和完整交通组织记录概念连接。')
row('S159 S162 S163 S164 S165 S166 S168 S169 S170', 'S156',
    '急诊诊疗及留观、急救单元围绕灰色U形候诊交通带组织；仅记录面向交通带的可达，不推断串门。')
access('S010', 'S009', '餐厨灰色交通核南侧前室面向厨房操作大厅，整体交通核连接。')


def upright(sid):
    return Polygon([(y / 1.63, (2444 - x) / (2444 / 1500)) for x, y in spaces[sid]['polygon_px']])


def set_poly(sid, poly):
    assert poly.geom_type == 'Polygon' and poly.is_valid and not poly.interiors
    spaces[sid]['polygon_px'] = [[round(2444 - y * 2444 / 1500, 5), round(x * 1.63, 5)]
                               for x, y in list(poly.exterior.coords)[:-1]]


# 仅在已目读门洞的墙带补极小阈口轮廓，使门点同时落在两个节点边界。
# 点位均由本图坐标判读图人工读取，未从共墙中点或质心自动产生。
for a, b, x, y, side in [
    ('S029', 'S027', 1285.5, 367, 'left'),
    ('S032', 'S027', 1285.5, 419, 'left'),
    ('S034', 'S027', 1285.5, 470, 'left'),
    ('S033', 'S027', 1254.5, 472, 'right'),
    ('S037', 'S027', 1285.5, 517, 'left'),
]:
    r = access(a, b, '放射科检查／辅助房面向内部通道的门洞可辨，点位见坐标判读_C.png。', '可见门洞')
    pa, pb = upright(a), upright(b)
    local = pb.intersection(LineString([(1100, y), (1400, y)]))
    if side == 'left':
        aa = box(x, y - 4, pa.bounds[0] + .01, y + 4)
        bb = box(local.bounds[2] - .01, y - 4, x, y + 4)
    else:
        aa = box(pa.bounds[2] - .01, y - 4, x, y + 4)
        bb = box(x, y - 4, local.bounds[0] + .01, y + 4)
    set_poly(a, unary_union([pa, aa]))
    set_poly(b, unary_union([pb, bb]))
    audit['geometry_changes'].append({'source': a, 'target': b, 'upright_xy': [x, y],
                                      'reason': '已定位门洞处各延展约1.5个阅读坐标像素至同一阈口，不改变房间范围层级'})
    op = {'id': f'P{next_p:03d}', 'kind': 'door',
          'position_px': [round(2444 - y * 2444 / 1500, 5), round(x * 1.63, 5)]}
    next_p += 1
    r.setdefault('openings', []).append(op)
    audit['visible_openings'].append({'relation_id': r['id'], 'source': a, 'target': b,
                                     'opening': op, 'upright_xy': [x, y], 'evidence': '原图明确门口符号'})
access('S031', 'S027', 'CT设备房面向内部检查通道组织，门的精确位置不可可靠读取。')

questions = [
    ('K01', 'S014', 'S013', '左侧餐厅是否直接进入窄通道S013？',
     '倾向经西侧窄通道进入；门位未画清，暂不补边。', [600, 395, 830, 580]),
    ('K02', 'S015', 'S043', '右侧餐厅是否直接连向南侧横向通道S043？',
     '南侧墙线连续，无法排除经S012备餐区或其他位置进入，暂不补边。', [705, 395, 845, 600]),
    ('K03', 'S027', 'S028', '放射科内部检查通道S027从哪里连向外围候诊S028？',
     '南端墙线连续，原R006已暂撤；可填写实际直接相连的空间，或确认两通道相通。', [1150, 325, 1385, 585]),
    ('K04', 'S060', 'S067', '西药房工作人员是否直接从医疗街S067进入？',
     '可见配药家具，但南缘人员门与服务界面无法区分；暂不补人员边或服务边。', [610, 565, 835, 825]),
    ('K05', 'S130', 'S120', '中药房工作人员是否由儿科候诊S120一侧进入？',
     '药房西侧邻候诊区和交通核，尚不能确定工作人员入口；暂不补边。', [600, 810, 815, 1010]),
    ('K06', 'S044', 'S048', '保健门厅S044是否直接连向妇科候诊S048？',
     '两区之间墙线清楚但未见可靠开口，保健入口也可能独立使用，暂不补边。', [408, 550, 565, 840]),
    ('K07', 'S072', 'S070', '出入院门厅S072是否从西侧医疗街S070进入？',
     '两侧均邻医疗街，但门厅侧壁未表达清晰门口；可同时注明是否也连东侧S075。', [845, 555, 1145, 695]),
]
state = {'name_items': [{'review_id': m['review'], 'space_id': m['id'], 'status': 'pending',
                         'candidate': m['candidate'], 'basis': m['basis'],
                         'confidence': m['confidence'], 'mapping_origin': '恢复原首轮固定顺序；现有S号不变'}
                        for m in pending],
         'connectivity_items': [{'review_id': q[0], 'source': q[1], 'target': q[2], 'status': 'pending',
                                  'question': q[3], 'judgement': q[4], 'crop_upright': q[5],
                                  **({'reserved_relation_id': 'R006'} if q[0] == 'K03' else {})}
                                 for q in questions],
         'checks': {'connectivity_reviewed': True, 'visual_reviewed': False},
         'scope_note': '本轮初步逐区复核；七项主要可达关系待用户判断，不代表完成。'}
for ids, reason in [
    ('S001 S002 S003 S005 S006 S007 S008 S011 S012', '餐厨内部细分及备餐小间，先等名称与两餐厅入口确认，不逐间追门。'),
    ('S017 S018 S020 S021 S022 S023 S024 S026 S030 S035 S036 S038 S039', '放射科后端辅助小间、设备或值班支持空间，无可靠门位暂不补边。'),
    ('S040 S041 S042 S046 S049 S052 S054 S058 S061 S062 S063 S064 S065', '妇科与药房的小辅助空间、厕所入口依赖尚未确认的内部通路。'),
    ('S071 S073 S074 S078 S079 S081', '中央服务小间及未知共享空间先等名称、性质和门厅入口，不把柜台服务联系转人员边。'),
    ('S084 S085 S086 S087 S092 S093 S096 S105 S106 S107 S108 S109 S110 S111 S112 S113 S114', '综合门诊内部辅助间、后勤及120区的内部细节不逐间追问，独立使用区不强连主网。'),
    ('S117 S118 S119 S121 S128 S129 S131 S132 S133 S135 S136', '儿科交通核内部辅助间及药房、输液支持间待名称后再判断，保持原粒度。'),
    ('S138 S139 S140 S141 S142 S143 S144 S145 S148 S150 S153 S154 S155 S157 S158 S161 S167', '输液与急诊的内部辅助间和工作带不穷尽小门，未记录不等于不相通。'),
]:
    audit['deferred_details'].append({'spaces': ids.split(), 'reason': reason})
at.normalize(data)
path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
save_state(state_path, state)
save_state(state_path, load_state(state_path, data, path))
(WORK / '连通判读依据.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n')
# 供后续核对图使用当前轮廓，原候选和固定映射不变。
for m in meta:
    m['shape'] = [[y / 1.63, (2444 - x) / (2444 / 1500)] for x, y in spaces[m['id']]['polygon_px']]
(WORK / '空间工作索引.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n')
print('spaces', len(spaces), 'relations', len(data['relations']), 'new access', len(audit['inferred_access']),
      'openings', next_p - 1, 'pending connections', len(questions))
