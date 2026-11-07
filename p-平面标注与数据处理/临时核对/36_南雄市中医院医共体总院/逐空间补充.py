from pathlib import Path
from copy import deepcopy
import json, sys
from shapely.geometry import Polygon, box
from shapely import set_precision

WORK = Path(__file__).resolve().parent
SAMPLE = WORK.parent.parent / '标注试样' / WORK.name
sys.path.insert(0, '/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts')
import annotation_tools as at
from review_workflow import load_state, save_state

path = SAMPLE / 'annotation.json'
data = json.loads(path.read_text())
assert len(data['spaces']) == 170, '本轮逐间补充只能运行一次；后续请增量修改'
state = json.loads((WORK / 'review_state.json').read_text())
meta = json.loads((WORK / '空间工作索引.json').read_text())
mapping = json.loads((WORK / '核对号对应.json').read_text())
spaces = {s['id']: s for s in data['spaces']}
index = {m['id']: m for m in meta}
next_id = max(int(s[1:]) for s in spaces) + 1
changes = []


def read_poly(sid):
    return Polygon([(y / 1.63, (2444 - x) / (2444 / 1500)) for x, y in spaces[sid]['polygon_px']])


def save_poly(sid, p):
    p = set_precision(p, .001)
    assert p.geom_type == 'Polygon' and p.is_valid and not p.interiors, (sid, p.wkt)
    spaces[sid]['polygon_px'] = [[round(2444 - y * 2444 / 1500, 5), round(x * 1.63, 5)]
                               for x, y in list(p.exterior.coords)[:-1]]
    index[sid]['shape'] = [list(q) for q in list(p.exterior.coords)[:-1]]


def add(poly, group, scope, basis, parent=None, name='名称未确认', typ='unknown', level='room'):
    global next_id
    assert poly.geom_type == 'Polygon' and poly.is_valid and not poly.interiors, (basis, poly.wkt)
    sid = f'S{next_id:03d}'
    next_id += 1
    space = {'id': sid, 'name': name, 'type': typ, 'level': level, 'scope': scope, 'polygon_px': []}
    spaces[sid] = space
    data['spaces'].append(space)
    record = {'id': sid, 'key': 'individual_' + sid, 'group': group,
              'candidate': '', 'basis': basis, 'confidence': '低', 'shape': []}
    meta.append(record)
    index[sid] = record
    save_poly(sid, poly)
    changes.append({'new_space_id': sid, 'split_from': parent, 'basis': basis,
                    'name_observed': typ != 'unknown', 'geometry_precision': 'coarse_outline'})
    return sid


def split(parent, shape, basis, **kwargs):
    original = read_poly(parent)
    cutter = box(*shape) if len(shape) == 4 and isinstance(shape[0], (float, int)) else Polygon(shape)
    child = original.intersection(cutter)
    remainder = original.difference(cutter)
    assert child.area > 15 and remainder.area > 15, (parent, child.area, remainder.area)
    assert remainder.geom_type == 'Polygon' and not remainder.interiors, (parent, '拆分后需人工重画', remainder.wkt)
    sid = add(child, index[parent]['group'], spaces[parent]['scope'], basis, parent, **kwargs)
    save_poly(parent, remainder)
    return sid


# 只拆有清楚隔墙的外围房间；梯段、电梯井、器具和家具不另造房间。
split('S026', (1356, 285, 1380, 306), '放射科东侧弧墙边上方独立小间，原S026内有清楚横向分隔')
split('S026', (1356, 306, 1380, 331), '放射科东侧弧墙边下方独立小间，原S026内有清楚横向分隔')
split('S040', (469, 510, 491, 530), '北西角圆形图案空间东侧上方有墙围合的小间')
split('S040', (469, 531, 491, 550), '北西角圆形图案空间东侧下方有墙围合的小间')
split('S042', (551, 540, 570, 558), '西横向通道北侧房间的西南角独立隔间')
split('S044', (494, 578, 517, 595), '保健门厅东北角、妇科交通核西北侧独立白色小间')
add(box(495, 653, 517, 663), index['S048']['group'], spaces['S048']['scope'],
    '妇科内侧通道东缘上方独立小间，原草稿未赋S号')
add(box(495, 666, 517, 672), index['S048']['group'], spaces['S048']['scope'],
    '妇科内侧通道东缘第二个窄小间，原草稿未赋S号')
for b, note in [((921, 651, 937, 685), '西端外侧'), ((938, 665, 957, 685), '西端内侧'),
                ((1038, 665, 1053, 685), '东端内侧'), ((1054, 651, 1073, 685), '东端外侧')]:
    split('S078', b, '出入院服务后台' + note + '有实体边界的小间；中间公共带仍保留S078')
for b, note in [((1456, 509, 1487, 535), '上排西间'), ((1488, 509, 1518, 535), '上排中间'),
                ((1519, 509, 1560, 535), '上排弧墙间'), ((1539, 536, 1560, 553), '前沿东侧小间')]:
    split('S084', b, '120值班中心' + note + '，图例只能确定所属功能区，不能确定具体用途')
spaces['S084'].update(name='120值班中心公共区', type='staff_support', level='open_space')
split('S110', (1464, 554, 1487, 578), '变电所北西角独立围合小间，具体用途未画明')

# 后勤卫生间按独立房间分出两组，保留S112给左侧房间，不猜男女属性。
old = read_poly('S112')
left = old.intersection(box(1433, 758, 1455.5, 787))
right = old.intersection(box(1457.5, 758, 1488, 792))
foyer = old.difference(box(1433, 758, 1455.5, 787).union(box(1457.5, 758, 1488, 792)))
save_poly('S112', left)
add(right, index['S112']['group'], spaces['S112']['scope'],
    '后勤区独立卫生间房间，卫生器具可辨，性别未标', 'S112', name='卫生间', typ='toilet')
add(foyer, index['S112']['group'], spaces['S112']['scope'],
    '后勤两间卫生间南侧共用前室，保留独立空间节点', 'S112', name='卫生间前室', typ='vestibule', level='open_space')
split('S113', (1490, 754, 1509, 783), '后勤南东侧大房间西北角独立小间')
split('S140', (1252, 827, 1278, 840), '输液北侧窄房间内部有横向隔墙，上下应分为两个单元')
split('S157', [(1443, 840), (1459, 840), (1454, 871), (1438, 868)],
      '急诊北侧功能块内第一个独立小间；只依据墙线分出，不推测用途')
split('S157', [(1459, 840), (1474, 840), (1470, 875), (1455, 872)],
      '急诊北侧功能块内第二个独立小间；只依据墙线分出，不推测用途')
split('S152', (1290, 936, 1321, 955), '输液交通核南端支持区西侧上方独立小间')
split('S152', (1290, 955, 1318, 984), '输液交通核南端支持区西侧下方独立小间')
split('S165', [(1615, 878), (1665, 878), (1665, 935), (1600, 935)],
      '急诊东侧上排中间纵向墙把原大轮廓分成两个房间')
split('S132', (748, 955, 761, 982), '中药房南侧小条带内有独立隔间，左间另给编号')

# 原有临床名称和所有关系编号、P点都保留；拆出房间不继承父块的access。
for s in data['spaces']:
    if s['type'] == 'unknown' and s['id'] not in {i['space_id'] for i in state['name_items']}:
        number = max(int(i['review_id']) for i in state['name_items']) + 1
        rid = f'{number:02d}'
        m = index[s['id']]
        m['review'] = rid
        state['name_items'].append({'review_id': rid, 'space_id': s['id'], 'status': 'pending',
                                    'candidate': '', 'basis': m['basis'], 'confidence': '低',
                                    'review_mode': 'information_missing'})
        mapping.append(deepcopy(m))
for item in state['name_items']:
    item['review_mode'] = 'information_missing'
state['scope_instruction'] = {
    'user_text': '很多房间信息看不到。只能用较粗的轮廓来标记；但是很多方面即使没有名字也应该逐个将其标记出来。',
    'interpretation': '可辨独立空间逐个编号和画粗轮廓；功能不可见保持unknown，不要求补全所有具体房名；连通按证据独立审查。',
    'requires_exact_room_names_this_round': False,
    'existing_name_review_ids_retained': True}
state['checks'].update(visual_reviewed=False, individual_outline_reviewed=False)
at.normalize(data)
report, _ = at.check(data, path, True, False)
assert report['valid'], report['errors']
path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
(WORK / '空间工作索引.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n')
(WORK / '核对号对应.json').write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + '\n')
save_state(WORK / 'review_state.json', state)
save_state(WORK / 'review_state.json', load_state(WORK / 'review_state.json', data, path))
(WORK / '逐空间补充记录.json').write_text(json.dumps(changes, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'spaces': len(data['spaces']), 'new': len(changes),
                  'unknown': sum(s['type'] == 'unknown' for s in data['spaces']),
                  'new_ids': [i['new_space_id'] for i in changes]}, ensure_ascii=False))
