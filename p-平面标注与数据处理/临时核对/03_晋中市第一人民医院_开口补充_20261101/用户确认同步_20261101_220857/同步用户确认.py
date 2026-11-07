"""按已保存的用户填写和聊天授权同步 03 号概念级成果。"""

from pathlib import Path
from copy import deepcopy
import json
from shapely.geometry import Polygon, box
from shapely.ops import unary_union


OUT = Path(__file__).resolve().parent
STAGE = OUT / '待核验成果'
PATH = STAGE / 'annotation.json'
DATA = json.loads((OUT / '修改前备份/annotation.json').read_text())
OLD = deepcopy(DATA)
SPACES = {s['id']: s for s in DATA['spaces']}
CHANGES = []
CONCEPT = []
RMAX = max(int(r['id'][1:]) for r in DATA['relations'] if r['id'].startswith('R'))
PMAX = max(int(o['id'][1:]) for r in DATA['relations'] for o in r.get('openings', []))


def log(action, **fields):
    CHANGES.append({'action': action, **fields})


def remove(ids, reason):
    ids = set(ids)
    for r in DATA['relations']:
        if r['id'] in ids:
            log('remove_relation', relation=deepcopy(r), reason=reason)
    DATA['relations'] = [r for r in DATA['relations'] if r['id'] not in ids]


def add(a, b, rid=None, concept_reason=None):
    global RMAX
    found = next((r for r in DATA['relations'] if r['type'] == 'access'
                  and {r['source'], r['target']} == {a, b}), None)
    if found is None:
        if rid is None:
            RMAX += 1
            rid = f'R{RMAX:03}'
        found = {'id': rid, 'source': a, 'target': b, 'type': 'access'}
        DATA['relations'].append(found)
        log('add_relation', relation=deepcopy(found))
    if concept_reason:
        CONCEPT.append({'relation_id': found['id'], 'source': a, 'target': b,
                        'reason': concept_reason})
    return found


def doorway(a, b, x, y, reason):
    global PMAX
    r = add(a, b)
    q = [round(3064-y, 2), round(x, 2)]
    for o in r.get('openings', []):
        if sum((v-w)**2 for v, w in zip(o['position_px'], q)) < 225:
            return
    PMAX += 1
    o = {'id': f'P{PMAX:03}', 'kind': 'door', 'position_px': q}
    r.setdefault('openings', []).append(o)
    log('add_opening', relation_id=r['id'], opening=o, reason=reason)


def upright_polygon(sid):
    return Polygon([(y, 3064-x) for x, y in SPACES[sid]['polygon_px']])


def geometry(sid, poly):
    assert poly.geom_type == 'Polygon' and poly.is_valid and not poly.interiors
    SPACES[sid]['polygon_px'] = [[round(3064-y, 2), round(x, 2)]
                                for x, y in list(poly.exterior.coords)[:-1]]
    log('update_geometry', space_id=sid)


def rename(sid, name, kind, level=None):
    old = {k: SPACES[sid][k] for k in ('name', 'type', 'level')}
    SPACES[sid].update(name=name, type=kind)
    if level:
        SPACES[sid]['level'] = level
    log('update_space', space_id=sid, before=old,
        after={k: SPACES[sid][k] for k in old})


# 删除用户明确放弃的两个交通核；其他空间保持稳定编号。
deleted = {'S029', 'S076'}
remove([r['id'] for r in DATA['relations']
        if r.get('source') in deleted or r.get('target') in deleted], '用户明确删除空间')
DATA['spaces'] = [s for s in DATA['spaces'] if s['id'] not in deleted]
for sid in deleted:
    SPACES.pop(sid)
    log('delete_space', space_id=sid)

# 同一挂号收费医保新农合服务区保留最早 S265，合并边界与外部关系。
merged = unary_union([upright_polygon(sid) for sid in ('S265', 'S266', 'S267')])
geometry('S265', merged)
rename('S265', '挂号收费医保新农合', 'registration', 'semi_open_space')
for r in DATA['relations']:
    for key in ('source', 'target'):
        if r.get(key) in {'S266', 'S267'}:
            before = deepcopy(r)
            r[key] = 'S265'
            log('rewire_merged_space', before=before, after=deepcopy(r))
DATA['spaces'] = [s for s in DATA['spaces'] if s['id'] not in {'S266', 'S267'}]
for sid in ('S266', 'S267'):
    SPACES.pop(sid)
    log('merge_space', removed=sid, retained='S265')

# 用途按用户接受的概念精度处理；庭院不参与室内面积或人员连接。
rename('S215', '设备间', 'building_services', 'room')
rename('S083', '清创室', 'treatment', 'room')
rename('S260', '操作间', 'examination', 'room')
rename('S262', '操作间', 'examination', 'room')
rename('S218', '庭院', 'courtyard', 'open_space')
remove([r['id'] for r in DATA['relations']
        if r.get('source') == 'S218' or r.get('target') == 'S218'], '用户指定庭院不与房间连通')

# MRI 控制廊补回右下侧回折段，仍保留原 S159／S164 两个节点。
old159, old164 = upright_polygon('S159'), upright_polygon('S164')
return_segment = old164.intersection(box(1553.95, 1102.19, 1609.29, 1146.87))
geometry('S159', unary_union([old159, return_segment]))
geometry('S164', old164.difference(return_segment))
remove(['R162', 'R163'], '用户确认 MRI／机房不通西侧等候通道')
doorway('S159', 'S161', 1553.95, 1125, '用户确认 MRI 右下侧门；原图门洞近似定位')
add('S161', 'S162', concept_reason='用户确认 MRI 下方门通机房；不细化含混门位')
doorway('S171', 'S172', 2056, 1146.87, '用户确认库房右上门，原有点位已对应此门')

# S177 下方未标的共享前室：保留原房间，新增稳定编号 S345。
foyer = box(1609.29, 1270.28, 1683.8, 1314.97)
SPACES['S345'] = {
    'id': 'S345', 'name': '合用前室', 'type': 'vestibule',
    'level': 'open_space', 'scope': SPACES['S177']['scope'], 'polygon_px': [],
}
DATA['spaces'].append(SPACES['S345'])
geometry('S345', foyer)
remove(['R170', 'R180'], '用户确认通过前室／通道，不直接跨房连通')
add('S173', 'S164', concept_reason='等候经医技通道的合用前室部分，再经既有 R169 到处置')
doorway('S177', 'S345', 1620, 1270.28, '打印出片左下门通合用前室')
add('S345', 'S179', concept_reason='前室接护士站及南侧等候 S175，半墙区域不编造门位')
add('S345', 'S178', concept_reason='相邻前室／过渡间的概念通路')
add('S179', 'S180', concept_reason='护士站与接待区域连续，按用户接受的概念连接补充')
add('S181', 'S178', concept_reason='用户确认控制廊与过渡间可直接通行')

# 南侧超市经缓冲间进交通核，不保留跳过中间空间的旧边。
remove(['R339'], '经中间缓冲／走道到达，不能跳过中间节点')
add('S340', 'S339', concept_reason='S337 经已有 R338 到 S340，再到 S339')
add('S329', 'S331', concept_reason='用户确认财务室有门通公共通道，门位不细化')
add('S188', 'S191', concept_reason='用户确认打印出片与普放通道直接相通')
remove(['R206'], '更衣室右侧门实际接东侧通道 S189，再接 S188')
add('S189', 'S199', rid='R206')
doorway('S189', 'S199', 2026.52, 1528, '用户确认更衣室右侧门，图面可辨')

# 普放三间的真实角色与内侧走廊路径。
remove(['R190', 'R191', 'R192', 'R213', 'R214'], '不通东侧／上侧走廊，改经内部 S207／S217')
add('S207', 'S217', concept_reason='用户确认内侧通道可到两间胃肠，保留中间通道节点')
add('S217', 'S214', concept_reason='内侧通道进入上侧胃肠间')
add('S217', 'S216', concept_reason='内侧通道进入下侧胃肠间')
add('S215', 'S214', concept_reason='用户确认设备间分别连通两间胃肠')
add('S215', 'S216', concept_reason='用户确认设备间分别连通两间胃肠')
doorway('S207', 'S205', 1723, 1734.15, '会诊示教门在下侧')
doorway('S207', 'S209', 1816, 1757.56, '主任室上侧门')
doorway('S207', 'S210', 1578.69, 1790, '卫生间左下侧门')
doorway('S207', 'S211', 1578.69, 1806, '下侧卫生间同侧入口')

# 交通核 S115 主入口面向下方门诊大厅；保留其他既有可见门。
remove(['R115'], '主入口面向下方门诊大厅，原边跨到西侧走廊')
add('S107', 'S115', rid='R115', concept_reason='用户确认主入口面向门诊大厅')

# 手术配套关系采用用户接受的概念连接，不据配套名称编造门坐标。
add('S079', 'S085', concept_reason='用户确认清洁治疗与手术间内部相通')
add('S082', 'S083', concept_reason='用户确认手术间及配套清创室，按概念连接保留')

# 合并收费区的员工支持用房与右侧临床操作用房分别组织。
for a, b in [('S265', 'S256'), ('S256', 'S259'), ('S259', 'S258'),
             ('S259', 'S261'), ('S235', 'S257'), ('S235', 'S262'), ('S262', 'S260')]:
    add(a, b, concept_reason='依据用户说明及相邻布局作概念连接，不补虚构门位')
doorway('S289', 'S290', 2380, 2058, '用户确认卫生间朝左进入 120 指挥中心')
add('S235', 'S253', concept_reason='用户确认挂号收费为半墙开放区，可直接到急诊通道')

# 急救内部按概念节点组织，不拆解 EICU 内部走廊和施工细节。
rename('S271', '合用前室', 'vestibule', 'open_space')
for a, b, reason in [
    ('S271', 'S285', '交通核经前方合用前室进入'),
    ('S271', 'S275', '前室经 EICU 内通道进入，内部通道包含于功能块'),
    ('S283', 'S280', '用户确认小通道成立并与护士室直接相通'),
    ('S283', 'S284', '用户确认小通道与办公直接相通'),
    ('S107', 'S286', '大厅侧保安配套联系，按用户接受的概念人员可达保存'),
    ('S098', 'S105', '用户确认药房通道直接通交通核'),
    ('S091', 'S105', '用户确认过道右侧有门通交通核'),
    ('S098', 'S343', '用户确认药房通道与洁具间相通'),
    ('S120', 'S125', '依用户接受的概念精度，经未单独建模的左侧通路可达；不表示直接门洞'),
    ('S316', 'S314', '用户明确确认直接相通'),
]:
    add(a, b, concept_reason=reason)

# 合并后清除重复关系；既有最早 R 编号保留，开口不丢失。
seen, cleaned = {}, []
for r in DATA['relations']:
    if r['source'] == r['target']:
        log('remove_self_relation', relation=r)
        continue
    key = r['id'] if r['type'] == 'entrance' else (r['type'], *sorted([r['source'], r['target']]))
    if key in seen:
        first = seen[key]
        for o in r.get('openings', []):
            first.setdefault('openings', []).append(o)
        log('deduplicate_relation', removed=r['id'], retained=first['id'])
        continue
    seen[key] = r
    cleaned.append(r)
DATA['relations'] = cleaned
PATH.write_text(json.dumps(DATA, ensure_ascii=False, indent=2)+'\n')
(OUT/'同步修改记录.json').write_text(json.dumps(CHANGES, ensure_ascii=False, indent=2)+'\n')
(OUT/'概念连接说明.json').write_text(json.dumps(CONCEPT, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({'spaces': len(DATA['spaces']), 'relations': len(DATA['relations']),
                  'changes': len(CHANGES), 'concept_notes': len(CONCEPT)}, ensure_ascii=False))
