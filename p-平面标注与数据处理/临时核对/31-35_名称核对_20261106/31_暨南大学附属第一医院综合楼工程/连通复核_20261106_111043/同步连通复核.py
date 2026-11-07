"""31号逐图判读记录；门位由人工读取正向原图，不从几何自动生成。"""
import copy
import importlib.util
import json
import sys
from collections import defaultdict, deque
from pathlib import Path

from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

WORK = Path(__file__).resolve().parent
PATHS = json.loads((WORK / '路径.json').read_text())
PROJECT = Path(PATHS['project'])
REVIEW = Path(PATHS['review'])
BACKUP = WORK / '复核前备份'
DATA = json.loads((BACKUP / 'annotation.json').read_text())
STATE = json.loads((BACKUP / 'review_state.json').read_text())
SPACES = {s['id']: s for s in DATA['spaces']}
RELATIONS = {r['id']: r for r in DATA['relations']}
AUDIT = []
H = DATA['image']['width']
SKILL = Path('/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts')
sys.path.insert(0, str(SKILL))
spec = importlib.util.spec_from_file_location('annotation_tools', SKILL / 'annotation_tools.py')
at = importlib.util.module_from_spec(spec)
spec.loader.exec_module(at)


def original(points):
    return [[round(H - y, 2), round(x, 2)] for x, y in points]


def upright(sid):
    return Polygon([(y, H - x) for x, y in SPACES[sid]['polygon_px']])


# 候诊室东侧实际实体墙在1202.94；旧草稿把墙外通道也纳入S063。
vestibule = box(1202.94, 953.16, 1261.62, 1134.02)
old_wait = upright('S063')
old_hall = upright('S048')
for sid, geom in [('S063', old_wait.difference(vestibule)),
                  ('S048', unary_union([old_hall, vestibule]))]:
    assert geom.geom_type == 'Polygon' and geom.is_valid and not geom.interiors
    SPACES[sid]['polygon_px'] = original(list(geom.exterior.coords)[:-1])
AUDIT.append({'geometry': ['S063', 'S048'], 'basis': '原图候诊区东侧双扇门和墙外狭长通道；只转移门外通道归属，合计占地不变。'})


def retarget(rid, source, target, reason):
    r = RELATIONS[rid]
    before = copy.deepcopy(r)
    r.update(source=source, target=target)
    AUDIT.append({'relation': rid, 'before': before, 'after': copy.deepcopy(r), 'basis': reason})


retarget('R009', 'S009', 'S010', '女厕门开向S010轮廓包含的共用前室；旧S009-S011跨过该前室。不是从男厕厕位内部通行。')
retarget('R037', 'S038', 'S048', 'S038两部电梯门均朝南向门厅S048，不朝东侧S039。')
retarget('R038', 'S047', 'S049', 'S047北侧外门实际开向已并入S049的19号区域；不穿过东侧实体墙直连S048。')
retarget('R047', 'S054', 'S053', 'DSA西北门先进入控制室S053，之后经S053进入西侧走廊；删除跨过控制室的直接连接。')

NUMBER = max(int(r['id'][1:]) for r in DATA['relations'] if r['id'].startswith('R'))


def add(source, target, reason, typ='access'):
    global NUMBER
    assert not any(r['type'] == typ and {r['source'], r['target']} == {source, target}
                   for r in DATA['relations'])
    NUMBER += 1
    rid = f'R{NUMBER:03}'
    r = {'id': rid, 'source': source, 'target': target, 'type': typ}
    DATA['relations'].append(r)
    RELATIONS[rid] = r
    AUDIT.append({'relation': rid, 'source': source, 'target': target, 'basis': reason})
    return rid


# 以下全部坐标为正向原图(x,y)，最终反变换写回原图像素坐标。
# 每个门组取近似中心；无扇但有清晰门槛/滑门缺口的房间入口仍记door。
DOORS = {
    'R001': [(465, 570.27)], 'R002': [(551, 570.27)],
    'R003': [(578, 570.27)], 'R004': [(719, 570.27)],
    'R005': [(804, 570.27)], 'R006': [(831, 570.27)],
    'R007': [(1038, 570.27)], 'R008': [(1184, 570.27)],
    'R009': [(1261.62, 542)], 'R010': [(1292, 570.27)],
    'R011': [(431, 625.66), (699, 625.66)],
    'R012': [(772, 625.66), (1014, 625.66)],
    'R013': [(731.87, 711)], 'R014': [(731.87, 865)],
    'R016': [(1134.48, 638)], 'R017': [(1134.48, 794)],
    'R018': [(1307, 625.66)], 'R019': [(1642, 570.27)],
    'R020': [(1984, 570.27)],
    'R021': [(2011, 570.27), (2154, 570.27)],
    'R022': [(1647, 625.66)], 'R023': [(1676, 625.66)],
    'R024': [(1763, 625.66)], 'R025': [(1847, 625.66)],
    'R026': [(1998.38, 761)], 'R028': [(1687, 570.27)],
    'R029': [(1687, 542.58)], 'R030': [(1445, 692.47)],
    'R031': [(1488.19, 791)], 'R035': [(1998.38, 791)],
    'R037': [(1295, 953.16), (1359, 953.16)],
    'R038': [(1637, 1134.02)],
    'R039': [(1295, 1134.02), (1359, 1134.02)],
    'R041': [(1833.75, 1185)],
    'R044': [(455, 1023.22)], 'R045': [(481, 1023.22)],
    'R046': [(539.53, 1041)], 'R047': [(601.47, 969)],
    'R048': [(424, 1059.07), (523.23, 1101)],
    'R049': [(488, 1309.98)],
    'R050': [(601.47, 1141)], 'R051': [(601.47, 1268)],
    'R052': [(762, 1059.07)], 'R053': [(805, 1059.07)],
    'R055': [(792.18, 1108)],
    'R056': [(888, 1331.24)], 'R057': [(1053, 1331.24)],
    'R058': [(1080, 1331.24)],
    'R059': [(805, 1384.93), (1247, 1384.93)],
    'R060': [(768, 1384.93)], 'R061': [(586, 1384.93)],
    'R062': [(411, 1437.07)], 'R063': [(551, 1437.07)],
    'R064': [(577, 1437.07)], 'R065': [(719, 1437.07)],
    'R066': [(746, 1437.07)], 'R067': [(886, 1437.07)],
    'R068': [(915, 1437.07)], 'R069': [(1053, 1437.07)],
    'R070': [(1148, 1437.07)], 'R071': [(1178, 1437.07)],
    'R072': [(1261.62, 1412)],
    'R074': [(1388, 1525.06), (1424, 1525.06)],
    'R075': [(1501, 1384.93)], 'R076': [(1647, 1384.93)],
    'R077': [(1735, 1384.93)], 'R078': [(1760, 1384.93)],
}
PASSAGES = {
    'R015': [(1325.19, 598)], 'R027': [(1545.24, 598)],
    'R042': [(2053.8, 1350)], 'R043': [(1833.75, 1350)],
}
NEW_DOORS = [
    ('S012', 'S016', [(431, 775.56), (699, 775.56)], '中/西药库共界两组双扇门；不是仅有共墙。'),
    ('S014', 'S011', [(1243, 625.66)], '配置中心北侧另有单扇门通北侧走廊。'),
    ('S023', 'S025', [(1757, 570.27)], '楼梯旁库房南侧虚线门扇通走廊。'),
    ('S027', 'S032', [(1737, 775.56)], '办公南侧单扇门进入客服中心工作区。'),
    ('S028', 'S032', [(1764, 775.56)], '办公南侧单扇门进入客服中心工作区。'),
    ('S029', 'S033', [(1848, 775.56)], '办公南侧单扇门进入手续办理工作区。'),
    ('S031', 'S032', [(1662.6, 791)], '财务与客服中心之间的单扇门。'),
    ('S063', 'S048', [(1202.94, 1102)], '影像候诊区东侧双扇门，经墙外通道进入门厅；已校正通道归属。'),
    ('S065', 'S063', [(859, 1153.57)], '准备间北侧清晰门槛缺口。'),
    ('S066', 'S063', [(969, 1153.57)], '准备间北侧清晰门槛缺口。'),
    ('S067', 'S063', [(1052, 1153.57)], '设备机房北侧清晰门槛缺口；南侧连续墙不补CT/MR连接。'),
    ('S068', 'S063', [(1185, 1153.57)], '准备间北侧清晰门槛缺口。'),
    ('S065', 'S069', [(859, 1212.22)], '准备间南侧门槛通DR。'),
    ('S066', 'S070', [(969, 1212.22)], '准备间南侧门槛通CT。'),
    ('S068', 'S071', [(1185, 1212.22)], '准备间南侧门槛通MR。'),
    ('S080', 'S081', [(973.14, 1457)], '储片室与阅片室共界另有侧向单扇门。'),
]
for a, b, points, reason in NEW_DOORS:
    DOORS[add(a, b, reason)] = points

CONCEPTUAL = [
    ('S037', 'S039', '布局判读：候药厅右侧与北侧通道连续，铺装线不作为独立隔墙。'),
    ('S036', 'S049', '布局推断：三部电梯南向门前为S049，侧边及背墙不建立通道；门扇细部不足，不定位P点。'),
    ('S043', 'S039', '布局推断：公共电梯厅北端接中部通道，图案边缘为铺装/前区分界，无可靠门位。'),
    ('S043', 'S048', '布局推断：公共电梯厅南端与连续公共门厅衔接，无独立可定位门位。'),
    ('S032', 'S033', '布局判读：两处柜台后工作区连续，分界为轴线；不跨柜台建立人员连接。'),
    ('S033', 'S035', '布局推断：红色柜台东端未封闭，工作区从柜台端部进入大厅；保留概念连接，不编造柜台小门。'),
    ('S062', 'S063', '布局判读：护士站半墙工作区入口位于柜台开放端；服务关系另保留，不定位未画小门。'),
]
for a, b, reason in CONCEPTUAL:
    add(a, b, reason)

CONCEPT_REASONS = {
    'R032': '北侧公共通道南端与住院服务大厅连续，没有独立门槛。',
    'R036': '住院服务大厅南缘与主入口门厅连续，图面轴线不生成门洞。',
    'R040': '用户确认合并后的相邻门厅分区连续；分区边不等于实体门。',
    'R073': '开放楼梯的弧形前缘接门厅，无封闭房间门；交通核内部踏步不另定位。',
}

# 基线无既有P编号；本轮编号只依上述逐门判读清单顺序生成。
opening_number = 0
for mapping, kind in [(DOORS, 'door'), (PASSAGES, 'open_passage')]:
    for rid, points in mapping.items():
        relation = RELATIONS[rid]
        assert relation['type'] == 'access'
        relation['openings'] = []
        for x, y in points:
            opening_number += 1
            relation['openings'].append({'id': f'P{opening_number:03}', 'kind': kind,
                                          'position_px': original([(x, y)])[0]})
        AUDIT.append({'relation': rid, 'source': relation['source'], 'target': relation['target'],
                      'opening_kind': kind, 'upright_positions': points,
                      'basis': '逐门目读原图；对应细部01—14及补充照片02/04核实。'})

ENTRANCES = [
    ('E005', '独立交通核外门', 'S041', 'secondary', (2744, 700.61)),
    ('E006', '北侧走廊西外门', 'S011', 'secondary', (397.72, 598)),
    ('E007', '消防控制中心北外门', 'S021', 'service', (1985, 464.36)),
    ('E008', '北侧走廊东外门', 'S025', 'secondary', (2169.53, 598)),
]
for eid, name, target, typ, point in ENTRANCES:
    DATA['relations'].append({'id': eid, 'name': name, 'type': 'entrance', 'source': None,
                              'target': target, 'entrance_type': typ,
                              'position_px': original([point])[0]})
    AUDIT.append({'entrance': eid, 'target': target, 'basis': '外墙清晰门扇；独立外部接口，不经室外虚构内部连接。',
                  'upright_position': point})

at.normalize(DATA)
polys = {s['id']: Polygon(s['polygon_px']) for s in DATA['spaces']}
distances = []
for r in DATA['relations']:
    for o in r.get('openings', []):
        p = Point(o['position_px'])
        da = polys[r['source']].boundary.distance(p)
        db = polys[r['target']].boundary.distance(p)
        distances.append({'opening': o['id'], 'relation': r['id'], 'source': r['source'],
                          'target': r['target'], 'source_distance_px': round(da, 3),
                          'target_distance_px': round(db, 3)})

graph = defaultdict(set)
roots = []
for r in DATA['relations']:
    if r['type'] == 'access':
        graph[r['source']].add(r['target'])
        graph[r['target']].add(r['source'])
    elif r['type'] == 'entrance':
        roots.append(r['target'])
visited = set(roots)
queue = deque(roots)
while queue:
    for target in graph[queue.popleft()] - visited:
        visited.add(target)
        queue.append(target)
indoor = {s['id'] for s in DATA['spaces'] if at.indoor(s)}
coverage = {'reachable_from_any_entrance': sorted(visited),
            'indoor_unreachable': sorted(indoor - visited),
            'excluded_from_reachability': ['S091'],
            'note': '外部null不是共享室外节点；按各独立入口为起点做并集覆盖。'}

STATE['connectivity_audit'] = {
    'date': '2026-11-06', 'work_dir': WORK.name,
    'basis': '原图逐区01—14及用户补充照片；布局推断与可定位门洞分别保存。',
    'relation_changes': [v for v in AUDIT if 'before' in v],
    'conceptual_without_openings': [
        {'relation': r['id'], 'source': r['source'], 'target': r['target'],
         'basis': CONCEPT_REASONS.get(r['id'], next((c[2] for c in CONCEPTUAL
                      if {c[0], c[1]} == {r['source'], r['target']}), '详见逐区记录'))}
        for r in DATA['relations'] if r['type'] == 'access' and not r.get('openings')],
    'not_required': [
        '交通核内电梯、楼梯、消防前室保持整体节点，不细分内部通道。',
        'S009进入S010轮廓内共用前室；不继续分割卫生间隔间，不表达需穿越男厕厕位。',
        'S063南东角小管井留在既有功能块内，不细分检修路线。',
        '药房窗口未清楚显示时不推定人员门；S032/S033/S062服务关系不代替人员连接。',
        'S067设备机房南侧未见门，不凭邻接补CT或MR连接。',
        'S041保留独立外门，不跨已排除户外范围连接主楼。',
    ],
    'coverage': coverage,
}
STATE['checks']['connectivity_reviewed'] = True
STATE['checks']['visual_reviewed'] = False
(PROJECT / 'annotation.json').write_text(json.dumps(DATA, ensure_ascii=False, indent=2) + '\n')
(REVIEW / 'review_state.json').write_text(json.dumps(STATE, ensure_ascii=False, indent=2) + '\n')
(WORK / '逐门判读与关系依据.json').write_text(json.dumps(AUDIT, ensure_ascii=False, indent=2) + '\n')
(WORK / '门洞端点距离审计.json').write_text(json.dumps(distances, ensure_ascii=False, indent=2) + '\n')
(WORK / '入口可达性.json').write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'spaces': len(DATA['spaces']), 'relations': len(DATA['relations']),
                  'openings': opening_number, 'max_endpoint_distance': max(max(v['source_distance_px'], v['target_distance_px']) for v in distances),
                  'indoor_unreachable': coverage['indoor_unreachable'],
                  'distance_outliers': [v for v in distances if max(v['source_distance_px'], v['target_distance_px']) > 16]},
                 ensure_ascii=False, indent=2))
