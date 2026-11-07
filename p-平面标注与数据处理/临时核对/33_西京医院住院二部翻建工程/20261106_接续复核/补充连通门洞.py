import json
from pathlib import Path
from shapely.geometry import Polygon, Point

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parents[2]
PLAN = BASE / '标注试样/33_西京医院住院二部翻建工程'
REVIEW = BASE / '临时核对/31-35_名称核对_20261106/33_西京医院住院二部翻建工程'
path = PLAN / 'annotation.json'
data = json.loads((ROOT / '接续前备份/annotation.json').read_text())
relations = {r['id']: r for r in data['relations']}
changes = []


def endpoints(rid, source, target, reason):
    r = relations[rid]
    changes.append({'id': rid, 'before': dict(r), 'reason': reason})
    r.update(source=source, target=target)


endpoints('R010', 'S004', 'S009', '卫生间西侧门直接开向西侧通道，不经会议室。')
endpoints('R013', 'S013', 'S012', '低温灭菌间东侧门通向高温灭菌区；该处不与南侧检查包装区直接相接。')
endpoints('R091', 'S118', 'S098', '电梯厅南侧双门直接面向普通住院门厅。')
endpoints('R092', 'S118', 'S099', '消防楼梯前室南侧双门直接面向普通住院门厅。')
for rid, sid in [('R063', 'S078'), ('R064', 'S079'), ('R072', 'S081')]:
    endpoints(rid, 'S072', sid, '北侧门直接开向摆药准备／成品调剂包装区，非西侧支持通道。')
endpoints('R080', 'S083', 'S072', '调配操作间北侧传递窗面向成品调剂包装区，仅保留service。')
for rid, sid in [('R083', 'S088'), ('R084', 'S089'), ('R085', 'S090')]:
    endpoints(rid, 'S096', sid, '南侧门开向护士站背后的狭长工作带；S096现有轮廓包含该工作带。')

# 缓冲间西侧未见人员门洞，撤回旧稿中仅因相邻而保存的连接。
retired = relations.pop('R027')
data['relations'] = [r for r in data['relations'] if r['id'] != 'R027']
changes.append({'id': 'R027', 'before': retired, 'reason': 'S026与S025西侧边界未见人员开口；S026仍由东侧S047进入。证据不足撤回，并非用户确认不相通。'})
for rid, reason in [('R073', '南排清洗间与一更之间为连续实墙，未见门洞；辅助小间不据相邻补连接。'),
                    ('R081', '门诊西楼梯南侧为实墙，未见通候诊区的门；其西侧有独立外门。')]:
    retired = relations.pop(rid)
    data['relations'] = [r for r in data['relations'] if r['id'] != rid]
    changes.append({'id': rid, 'before': retired, 'reason': reason})

new_relations = [
    ('R115', 'S009', 'S016', '缓冷间西侧可见单门。'),
    ('R116', 'S010', 'S011', '出炉间西侧可见单门。'),
    ('R117', 'S018', 'S023', '缓冲间西侧可见单门。'),
    ('R118', 'S022', 'S024', '洁车清洗东侧可见单门。'),
    ('R119', 'S037', 'S041', '电梯厅北侧可见双门。'),
    ('R120', 'S037', 'S042', '消防合用前室北侧可见双门。'),
    ('R121', 'S068', 'S072', '脱包暂存室东侧可见双门。'),
    ('R122', 'S117', 'S118', '便民站西侧可见双门，直接通住院门厅。'),
    ('R123', 'S054', 'S058', '西侧库房南侧可见双门。'),
    ('R124', 'S072', 'S073', '分装备药室西侧可见双门。'),
]
for rid, source, target, reason in new_relations:
    r = {'id': rid, 'source': source, 'target': target, 'type': 'access'}
    data['relations'].append(r)
    relations[rid] = r
    changes.append({'id': rid, 'after': dict(r), 'reason': reason})

# 坐标逐处按原图门扇／门洞判读，非从几何边界自动产生。
points = {
    'R001': [(772, 486)], 'R002': [(798, 519)],
    'R003': [(744, 612)], 'R004': [(744, 652)],
    'R005': [(744, 818)], 'R006': [(625, 943), (625, 984)],
    'R007': [(660, 1001)], 'R008': [(716, 1001)], 'R009': [(775, 1001)],
    'R010': [(798, 611)], 'R011': [(548, 799)], 'R012': [(543, 1001)],
    'R013': [(1141, 602)], 'R015': [(864, 746)],
    'R016': [(864, 825), (864, 988)], 'R017': [(944, 723)],
    'R018': [(1304, 1042)], 'R019': [(1000, 628)], 'R020': [(1304, 467)],
    'R021': [(776, 1124)], 'R022': [(858, 1124)], 'R023': [(900, 1124)],
    'R024': [(590, 1253)], 'R025': [(422, 1187)], 'R026': [(1372, 908)],
    'R029': [(1896, 798)], 'R030': [(2094, 798)],
    'R031': [(2220, 646)], 'R032': [(2220, 715)], 'R033': [(2220, 746)],
    'R034': [(2220, 880)], 'R035': [(1989, 873)],
    'R036': [(2132, 903)], 'R037': [(2190, 903)],
    'R039': [(2183, 494)], 'R040': [(2156, 611)],
    'R041': [(1968, 1081)], 'R042': [(2132, 1081)],
    'R043': [(2200, 1186)], 'R044': [(2300, 1186)],
    'R045': [(1656, 883)], 'R046': [(1656, 1028)],
    'R047': [(459, 1660)], 'R048': [(575, 1627)],
    'R049': [(655, 1627)], 'R050': [(1110, 1627)],
    'R051': [(606, 1698)], 'R052': [(698, 1698)], 'R053': [(784, 1698)],
    'R054': [(942, 1698)], 'R055': [(1035, 1698)], 'R056': [(1073, 1698)],
    'R057': [(531, 1845)], 'R058': [(460, 1819), (460, 1948)],
    'R059': [(625, 2109)], 'R060': [(442, 2150)],
    'R061': [(517, 2150)], 'R062': [(562, 2150)],
    'R063': [(732, 2150)], 'R064': [(949, 2150)],
    'R065': [(806, 1384)], 'R066': [(362, 2018)], 'R067': [(393, 2120)],
    'R068': [(1105, 1891)], 'R069': [(1068, 1825)], 'R070': [(1137, 1861)],
    'R071': [(1168, 1794)], 'R072': [(1049, 2150)],
    'R074': [(1090, 2178)], 'R075': [(1146, 2182)],
    'R076': [(1310, 2190)], 'R077': [(1411, 2150)],
    'R078': [(1485, 2106)],
    'R082': [(486, 2375)],
    'R083': [(605, 2375)], 'R084': [(644, 2375)], 'R085': [(733, 2375)],
    'R086': [(821, 2375)], 'R087': [(906, 2375)],
    'R088': [(989, 2375)], 'R089': [(1053, 2375)],
    'R091': [(1220, 2429)], 'R092': [(1418, 2429)],
    'R094': [(1145, 2465)],
    'R095': [(301, 2498)], 'R096': [(435, 2498)],
    'R097': [(472, 2498)], 'R098': [(606, 2498)],
    'R099': [(642, 2498)], 'R100': [(774, 2498)],
    'R101': [(818, 2498)], 'R102': [(953, 2498)],
    'R105': [(1739, 2045), (1637, 2168)],
    'R106': [(1637, 2283), (1637, 2338), (1637, 2404)],
    'R108': [(2241, 1545), (2241, 1688)], 'R109': [(2075, 2116)],
    'R115': [(798, 746)], 'R116': [(1035, 518)],
    'R117': [(1304, 963)], 'R118': [(1474, 927)],
    'R119': [(1896, 628)], 'R120': [(2094, 628)],
    'R121': [(805, 2014)], 'R122': [(1637, 2465)],
    'R123': [(368, 1703)], 'R124': [(1403, 2106)],
}
pid = 0
for rid, positions in points.items():
    r = relations[rid]
    assert r['type'] == 'access'
    r['openings'] = []
    for pos in positions:
        pid += 1
        r['openings'].append({'id': f'P{pid:03}', 'kind': 'door', 'position_px': list(pos)})

# 东门厅两处外门，沿用E03并为第二处续号。
relations['E03']['position_px'] = [2319, 1545]
data['relations'].append({'id': 'E11', 'source': None, 'target': 'S112', 'type': 'entrance',
                          'name': '东侧门厅南侧入口', 'entrance_type': 'public', 'position_px': [2319, 1688]})
data['relations'].extend([
    {'id': 'E12', 'source': None, 'target': 'S059', 'type': 'entrance',
     'name': '药房西侧楼梯外门', 'entrance_type': 'service', 'position_px': [281, 2018]},
    {'id': 'E13', 'source': None, 'target': 'S086', 'type': 'entrance',
     'name': '门诊西侧楼梯前室外门', 'entrance_type': 'outpatient', 'position_px': [281, 2307]}
])
path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

polys = {s['id']: Polygon(s['polygon_px']) for s in data['spaces']}
distances = []
for r in data['relations']:
    for op in r.get('openings', []):
        ds = [round(polys[sid].distance(Point(op['position_px'])), 2) for sid in (r['source'], r['target'])]
        distances.append({'opening': op['id'], 'relation': r['id'], 'pair': [r['source'], r['target']],
                          'position_px': op['position_px'], 'distance_to_spaces_px': ds})
(ROOT / '门洞端点距离.json').write_text(json.dumps(distances, ensure_ascii=False, indent=2) + '\n')
(ROOT / '关系调整记录.json').write_text(json.dumps(changes, ensure_ascii=False, indent=2) + '\n')
state = json.loads((REVIEW / 'review_state.json').read_text())
state['checks']['connectivity_reviewed'] = True
state['checks']['visual_reviewed'] = False
state['connectivity_review_notes'] = {
    'date': '2026-11-06', 'evidence': '本图原图及01—13分区放大图，逐门人工判读。',
    'scope': '沿用118节点概念层级，不细分交通核内部。主要功能区连接已复核；无用户连接确认记录。',
    'conceptual_connections': [
        {'relation_id': rid, 'reason': reason} for rid, reason in [
            ('R014', '高温灭菌与检查包装之间无完整实体隔墙，南侧连续。'),
            ('R028', '军人住院门厅与西侧服务通道在交通核西侧连续。'),
            ('R038', '住院服务通道南端与医疗大厅连续。'),
            ('R090', '护士站工作带西端绕过柜台与候诊区相接，布局推断，无定位门洞。'),
            ('R093', '咨询柜台背后与候诊区连续，布局推断，无定位门洞。'),
            ('R103', '扶梯厅西边为虚线概念边界，连接大厅西区。'),
            ('R104', '医疗大厅西、东区在扶梯南北两侧连续。'),
            ('R107', '医疗大厅西区与普通住院门厅连续。'),
            ('R110', 'ATM北侧虚线边界向医疗大厅开放，布局推断。'),
            ('R111', '扶梯厅东边为虚线概念边界，连接大厅东区。'),
        ]
    ],
    'not_required': [
        'S039女卫、S020拆包间与S021仓库的内部连接未见清晰开口；保留空间，不以共墙补边。',
        'S095设备小间内部连接及交通核内部小间门位本轮不细究。',
        'S080清洗间与S081之间未见门洞，撤回旧R073；小间内部连接本轮不细究。',
        'S086南侧为实墙，撤回旧R081；保留西侧独立外门E13，不为接入主网络补边。',
        'S026与S025之间未见人员门洞，撤回旧R027；S026保留向S047的可见门。',
        '东南空白虚线范围缺少功能和边界标注，未新增室内节点或假想外部总节点。'
    ]
}
(REVIEW / 'review_state.json').write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'spaces': len(data['spaces']), 'relations': len(data['relations']),
                  'openings': pid, 'far_endpoints': [x for x in distances if max(x['distance_to_spaces_px']) > 12]}, ensure_ascii=False, indent=2))
