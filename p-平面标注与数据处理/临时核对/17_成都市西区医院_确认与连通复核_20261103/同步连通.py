from pathlib import Path
from collections import Counter, deque
import importlib.util
import json


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SAMPLE = ROOT / 'p-平面标注与数据处理/标注试样/17_成都市西区医院'
SKILL = Path('/Users/hushili/.codex/skills/outpatient-plan-annotation')
spec = importlib.util.spec_from_file_location('annotation_tools', SKILL / 'scripts/annotation_tools.py')
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)
data = json.loads((SAMPLE / 'annotation.json').read_text())
spaces = {s['id']: s for s in data['spaces']}
assert not api.unresolved(data)
assert not any(r.get('openings') for r in data['relations'])

# The half-height nurse-station wall ends near y=1310. Its southern
# circulation strip belongs to the public emergency hall, up to the ER door.
spaces['S028']['polygon_px'] = [[1282, 1173], [1334, 1173], [1366, 1203],
                                  [1366, 1310], [1282, 1310]]
spaces['S030']['polygon_px'] = [[944, 1094], [1701, 1094], [1701, 1358],
                                  [1282, 1358], [1282, 1314], [1370, 1314],
                                  [1370, 1170], [1154, 1170], [1046, 1170], [944, 1170]]
removed = [r for r in data['relations'] if r['id'] == 'R052']
assert len(removed) == 1
data['relations'] = [r for r in data['relations'] if r['id'] != 'R052']
added = [
    {'id': 'R088', 'source': 'S044', 'target': 'S049', 'type': 'access'},
    {'id': 'R089', 'source': 'S035', 'target': 'S036', 'type': 'access'},
    {'id': 'R090', 'source': 'S047', 'target': 'S049', 'type': 'access'},
    {'id': 'R091', 'source': 'S041', 'target': 'S049', 'type': 'access'},
]
data['relations'] += added

# Pixel locations are manually read from this sample's original image.
# Values describe door thresholds rather than hinges or door-swing arc ends.
located = [
    ('R001', 'door', (385, 1089), '西卫生间南侧单门'),
    ('R002', 'door', (565, 1089), '东卫生间南侧单门'),
    ('R003', 'door', (315, 1089), '汇流排间南侧门'),
    ('R004', 'door', (490, 1090), '无障碍卫生间南侧门'),
    ('R005', 'door', (797, 1092), '西北交通核南侧双门'),
    ('R006', 'door', (360, 1169), 'CT北侧双门'),
    ('R007', 'door', (517, 1169), '控制室北侧单门'),
    ('R008', 'door', (730, 1169), 'X光北侧双门'),
    ('R012', 'door', (597, 1586), '社保出院结算南侧单门'),
    ('R013', 'door', (700, 1586), 'S012值班南侧单门'),
    ('R014', 'door', (727, 1464), 'S013值班西南侧门，接值班区通道'),
    ('R015', 'door', (788, 1486), '更衣北侧单门，接值班区通道'),
    ('R016', 'door', (744, 1587), '值班区通道南侧单门'),
    ('R017', 'door', (943, 817), '消防控制室西北侧门'),
    ('R018', 'door', (1365, 874), '五官东侧单门'),
    ('R019', 'door', (1433, 919), '清创室西南侧单门'),
    ('R020', 'door', (1519, 940), '清创室与外科之间右端单门'),
    ('R021', 'door', (1644, 1093), '东北交通核南侧双门'),
    ('R022', 'door', (1190, 1090), '急诊检验南侧人员门'),
    ('R023', 'door', (1365, 970), 'S021内科东侧单门'),
    ('R024', 'door', (1433, 1068), '外科西南侧单门'),
    ('R025', 'door', (1365, 1066), 'S023内科东侧单门'),
    ('R026', 'open_passage', (1399, 1095), '急诊诊室通道南端明确无门开口'),
    ('R027', 'door', (1007, 1169), 'B超北侧单门'),
    ('R028', 'door', (1130, 1169), '妇科检查北侧单门'),
    ('R029', 'door', (1279, 1243), '北治疗室东侧门通护士站'),
    ('R030', 'door', (1279, 1284), '南治疗室东侧门通护士站'),
    ('R034', 'door', (1321, 1362), '抢救室北侧双门通急诊门厅通行带'),
    ('R035', 'door', (1093, 1536), '洗胃东侧门通抢救室'),
    ('R036', 'door', (1228, 1587), '抢救室南侧双门'),
    ('R037', 'door', (943, 1567), '洗胃西南侧单门通后勤通道'),
    ('R043', 'door', (650, 1719), '中部交通核西北门'),
    ('R046', 'door', (1307, 1719), '中部交通核东北门'),
    ('R047', 'door', (1308, 1917), '中部交通核东南门'),
    ('R048', 'door', (714, 1957), '西侧电梯组北梯东向厅门'),
    ('R048', 'door', (714, 2030), '西侧电梯组中梯东向厅门'),
    ('R048', 'door', (714, 2105), '西侧电梯组南梯东向厅门'),
    ('R049', 'door', (1608, 1934), '住院手续西侧人员门'),
    ('R050', 'door', (1608, 2211), '门诊药房东翼西侧人员门'),
    ('R051', 'door', (881, 2064), '中部电梯组第1梯北向厅门'),
    ('R051', 'door', (983, 2064), '中部电梯组第2梯北向厅门'),
    ('R051', 'door', (1063, 2064), '中部电梯组第3梯北向厅门'),
    ('R051', 'door', (1166, 2064), '中部电梯组第4梯北向厅门'),
    ('R051', 'door', (1250, 2064), '中部电梯组第5梯北向厅门'),
    ('R051', 'door', (1337, 2064), '中部电梯组第6梯北向厅门'),
    ('R056', 'door', (355, 2580), '门诊收费南端东侧人员门'),
    ('R088', 'door', (1111, 2578), '门诊药房西南侧人员门通门诊门厅'),
]
relations = {r['id']: r for r in data['relations']}
evidence = []
for number, (rid, kind, xy, basis) in enumerate(located, 1):
    r = relations[rid]
    assert r['type'] == 'access'
    opening = {'id': f'P{number:03d}', 'kind': kind, 'position_px': list(xy)}
    r.setdefault('openings', []).append(opening)
    evidence.append({'opening': opening['id'], 'relation': rid,
                     'source': r['source'], 'target': r['target'],
                     'position_px': list(xy), 'kind': kind, 'basis': basis})

conceptual = {
    'R011': '影像区通道与后勤通道在图面相接，虚线为概念分界；连续区域不指定单个门位。',
    'R031': '布局推断：护士站半墙南端可绕行，接南侧急诊门厅通行带；不编造小门。',
    'R032': '急诊门厅与后勤通道在检验、B超之间连续相接，无实体分隔。',
    'R033': '急诊门厅与急诊入口过厅在右侧连续，点状横线不视作封闭墙。',
    'R038': '后勤通道向南接西侧通道，无实体分隔。',
    'R039': '后勤通道与北侧通道在抢救室西南侧转角连续。',
    'R040': '急诊入口过厅与住院入口过厅沿东侧纵向公共空间连续。',
    'R041': '住院入口过厅向西接北侧通道，无实体分隔。',
    'R042': '住院入口过厅向南接电梯厅，无实体分隔。',
    'R044': '布局推断：西侧自动扶梯整体交通节点由西侧通道一侧进入其公共候梯及到达区。',
    'R045': '西侧通道向南接门诊门厅，无实体分隔。',
    'R053': '电梯厅从中部电梯组两端绕行接候药厅；不穿越电梯井或后侧实墙。',
    'R055': '候药厅与门诊门厅在问讯台东侧及药房北侧连续。',
    'R089': '布局推断：导诊为半开放服务台，后方工作区从住院入口过厅一侧可进入；不指定小门。',
    'R090': '布局推断：问讯台为半开放服务台，北端开口及周边通行带可接门诊门厅；不指定小门。',
    'R091': '布局推断：西侧自动扶梯整体节点南端到达区接门诊门厅，不细分其内部路线。',
}
assert set(conceptual) == {r['id'] for r in data['relations'] if r['type'] == 'access' and not r.get('openings')}
for rid, basis in conceptual.items():
    r = relations[rid]
    evidence.append({'relation': rid, 'source': r['source'], 'target': r['target'],
                     'kind': 'conceptual_access', 'basis': basis})

api.normalize(data)
(SAMPLE / 'annotation.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
api.render(data, SAMPLE / 'annotation.json', SAMPLE / '标注.svg')
api.summary(data, OUT / '正式概览_供合并.md')
(OUT / '开口与连通判读依据.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2)+'\n')
(OUT / '关系调整.json').write_text(json.dumps({'removed': removed, 'added': added,
    'removed_basis': 'R052：中部电梯组南侧为连续实墙及座椅，不直接连候药厅；由电梯厅绕行。',
    'range_adjustment': 'S028南端缩至半墙终点，南侧无墙通行带划入S030；保留S编号并重算面积比例。'}, ensure_ascii=False, indent=2)+'\n')

# Isolated pipe shaft is deliberately not treated as a pedestrian destination.
graph = {sid: set() for sid in spaces}
for r in data['relations']:
    if r['type'] == 'access':
        graph[r['source']].add(r['target'])
        graph[r['target']].add(r['source'])
entrances = [r['target'] for r in data['relations'] if r['type'] == 'entrance']
reached = set(entrances)
queue = deque(entrances)
while queue:
    for target in graph[queue.popleft()]:
        if target not in reached:
            reached.add(target)
            queue.append(target)
unreachable = set(spaces) - reached
assert unreachable == {'S001'}, unreachable
print(json.dumps({'spaces': len(spaces), 'relation_types': Counter(r['type'] for r in data['relations']),
    'openings': len(located), 'located_access_relations': len(set(r[0] for r in located)),
    'conceptual_access': len(conceptual), 'unreachable': sorted(unreachable)}, ensure_ascii=False, indent=2))
