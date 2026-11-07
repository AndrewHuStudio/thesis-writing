"""Apply manually inspected plan-12 connectivity; preserve the original review table."""
from pathlib import Path
import collections
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parent
BACKUP = ROOT / '修改前备份'
STAGE = ROOT / '待核验成果'
STAGE.mkdir(exist_ok=True)
data = json.loads((BACKUP / 'annotation.json').read_text())
before = json.loads((BACKUP / 'annotation.json').read_text())
spaces = {s['id']: s for s in data['spaces']}
rels = {r['id']: r for r in data['relations']}

# Every coordinate below was read from this plan's original, not generated
# from polygon centroids or shared-wall midpoints.
retarget = {
    'R007': 'S011', 'R020': 'S022', 'R034': 'S041', 'R046': 'S021',
    'R083': 'S103', 'R085': 'S096', 'R096': 'S115', 'R099': 'S109',
    'R129': 'S172', 'R148': 'S170',
}
for rid, target in retarget.items():
    rels[rid]['target'] = target

removed = {
    'R025': 'S024南侧无清晰门洞，改经S025前室进入。',
    'R100': 'S113护士站与S104之间未见人员开口，列K02。',
    'R117': 'S121与S140仅角点接触，未见内部门洞，列K03。',
    'R120': 'S137南侧未见门洞，合并功能块内部入口本轮不细究。',
    'R175': 'S165西侧未见门洞，中央符号性质列K01。',
    'R176': 'S165东侧未见门洞，中央符号性质列K01。',
    'R177': 'S182与收费区内部小门不清，本轮不细究。',
    'R182': 'S190与S193之间为连续实线，未见直接门洞。',
}
for rid in removed:
    del rels[rid]
rels['R180']['type'] = 'service'

# The existing S091 omitted the visible eastward passage between S099/S107.
# Extend the same corridor node; no new room or renumbering is introduced.
spaces['S021']['polygon_px'] = [
    [1018.0, 510.0], [1496.0, 510.0], [1496.0, 573.0],
    [1551.0, 573.0], [1551.0, 710.0], [1018.0, 710.0],
]
spaces['S091']['polygon_px'] = [
    [666.0, 1598.0], [706.0, 1598.0], [706.0, 1789.0],
    [789.0, 1789.0], [789.0, 1826.0], [706.0, 1826.0],
    [706.0, 2024.0], [666.0, 2024.0],
]

# Existing relations with visually located personnel openings.
# Semicolon-separated positions mean multiple doors for the same space pair.
door_rows = '''
R001 385,673
R002 461,673
R003 531,673
R004 563,673
R005 750,673
R007 430,768
R008 444,714
R009 648,714
R010 737,714
R011 514,651
R012 695,585
R013 681,673
R014 789,696
R015 905,697;905,806
R016 789,862
R017 789,934
R018 789,991
R019 905,1001
R020 982,881
R026 1468,841
R027 1220,710
R028 1465,710
R029 1018,860
R031 1772,841;1826,841
R032 1857,841
R033 2075,841
R034 2294,841
R035 1529,881;1780,905
R036 2154,922;2231,922
R037 2295,922
R038 1825,922
R039 1855,922
R040 1942,922
R041 1972,922
R042 2059,922
R043 2087,922
R044 1933,811
R045 1496,860
R046 1551,698
R047 2063,670;2170,670
R048 2205,670;2293,670
R049 2236,728
R052 2205,841
R057 521,1102
R058 595,1102
R059 620,1102
R060 714,1102
R061 742,1102
R062 450,1142
R063 515,1142;515,1266
R064 569,1142;569,1266
R065 682,1142
R066 721,1142;721,1266
R067 398,1205
R068 398,1343
R069 398,1390
R070 398,1414
R071 431,1042
R072 398,1528
R073 412,1448
R074 445,1569
R075 532,1569
R076 560,1569
R077 649,1569
R078 679,1569
R079 768,1569
R080 390,1690
R081 390,1716
R082 390,1773
R084 608,1789
R085 489,1736
R086 489,1775
R091 706,1650
R092 706,1774
R093 706,1837
R094 706,1954
R095 706,1979
R096 706,2050
R097 489,1826
R098 608,1826
R099 489,1955
R101 534,1967
R102 574,2024
R103 217,2024
R109 353,2148
R110 385,2148
R111 473,2148
R112 504,2148
R113 573,2148
R114 706,2121
R115 706,2224
R116 706,2254
R118 906,2257
R119 1016,2280
R121 1362,2280;1431,2280
R122 1550,2280
R123 1077,2280
R124 1162,2280
R125 1194,2280
R126 1278,2280
R127 255,2290
R128 255,2415
R129 255,2474
R130 312,2415
R131 387,2432
R132 475,2432
R133 505,2432
R134 593,2432
R135 623,2432
R136 682,2432
R137 776,2432
R138 986,2320
R139 1018,2320
R140 1104,2320
R141 1136,2320
R142 1220,2320
R143 1252,2320
R144 1336,2320
R145 1368,2320
R146 1508,2320
R147 1539,2320
R148 1465,2446
R168 666,2744
R169 1062,2755
R170 698,2780;864,2780;1036,2780
R178 594,2710
R181 1250,2594
'''
points = []
for row in door_rows.strip().splitlines():
    rid, coords = row.split()
    for xy in coords.split(';'):
        points.append((rid, 'door', list(map(int, xy.split(',')))))
points.extend([
    ('R006', 'open_passage', [371, 725]),
    ('R056', 'open_passage', [398, 1105]),
    ('R083', 'open_passage', [478, 1789]),
    ('R154', 'door', [1437, 2432]),
])

# New direct relations. Empty coordinates mean visible circulation continuity,
# not a fabricated physical opening at an arbitrary segmentation boundary.
new_rows = [
    ('S003', 'S005', '550,612'),
    ('S007', 'S022', '867,673;893,673'),
    ('S017', 'S018', '966,1001'),
    ('S022', 'S032', ''),
    ('S032', 'S065', '833,1015'),
    ('S024', 'S025', '1200,737'),
    ('S021', 'S042', '1515,710'),
    ('S033', 'S034', '1724,596'),
    ('S035', 'S038', '2012,690'),
    ('S046', 'S041', '2188,825'),
    ('S067', 'S065', '789,1124'),
    ('S065', 'S118', '824,1569'),
    ('S078', 'S085', ''),
    ('S085', 'S118', ''),
    ('S085', 'S091', ''),
    ('S091', 'S115', ''),
    ('S104', 'S115', ''),
    ('S087', 'S118', '866,1618'),
    ('S093', 'S118', '866,1664'),
    ('S094', 'S118', '866,1833'),
    ('S091', 'S118', '789,1804'),
    ('S112', 'S102', '290,1973'),
    ('S169', 'S167', ''),
    ('S170', 'S167', ''),
    ('S172', 'S174', ''),
    ('S175', 'S177', ''),
    ('S181', 'S172', '297,2540'),
    ('S181', 'S174', '357,2540;477,2540'),
    ('S183', 'S174', '611,2540'),
    ('S183', 'S195', '637,2720'),
    ('S185', 'S184', ''),
    ('S185', 'S186', ''),
    ('S185', 'S194', ''),
    ('S178', 'S185', ''),
    ('S187', 'S175', '1213,2540'),
    ('S187', 'S194', '1062,2708'),
    ('S187', 'S196', '1105,2720'),
    ('S188', 'S175', '1250,2540'),
    ('S188', 'S187', '1236,2576'),
    ('S188', 'S189', '1294,2576'),
    ('S189', 'S175', '1303,2540'),
    ('S189', 'S177', '1446,2540'),
    ('S193', 'S187', '1236,2708'),
    ('S193', 'S189', '1294,2710'),
]
for number, (source, target, coords) in enumerate(new_rows, 183):
    rid = f'R{number:03d}'
    rels[rid] = {'id': rid, 'source': source, 'target': target, 'type': 'access'}
    if coords:
        for xy in coords.split(';'):
            points.append((rid, 'door', list(map(int, xy.split(',')))))
rels['R227'] = {
    'id': 'R227', 'source': 'S187', 'target': 'S186', 'type': 'service',
}

for n, (rid, kind, position) in enumerate(
        sorted(points, key=lambda x: (x[2][1], x[2][0], x[0])), 1):
    rels[rid].setdefault('openings', []).append({
        'id': f'P{n:03d}', 'kind': kind, 'position_px': position,
    })

# These are exterior interfaces and deliberately use E IDs, not indoor P IDs.
for n, (target, name, position) in enumerate([
    ('S065', '中段北东侧平台入口', [866, 1355]),
    ('S059', '中段西北楼梯北侧入口', [445, 1016]),
    ('S005', '西北交通核北侧入口', [573, 575]),
    ('S077', '中段西楼梯西侧入口', [308, 1550]),
    ('S087', '中段东楼梯北侧平台入口', [895, 1569]),
], 11):
    rid = f'E{n:02d}'
    rels[rid] = {'id': rid, 'source': None, 'target': target,
                 'type': 'entrance', 'name': name,
                 'entrance_type': 'side', 'position_px': position}

data['relations'] = sorted(
    rels.values(), key=lambda r: (r['type'] == 'entrance', int(r['id'][1:])))
(STAGE / 'annotation.json').write_text(
    json.dumps(data, ensure_ascii=False, indent=2) + '\n')
shutil.copy2(BACKUP / data['image']['file'], STAGE / data['image']['file'])

changes = {
    'retargeted': {k: {'old': next(r for r in before['relations'] if r['id'] == k),
                       'new': rels[k]} for k in retarget},
    'removed': removed,
    'converted_to_service': ['R180'],
    'new_relation_ids': [f'R{i:03d}' for i in range(183, 228)],
    'new_entrance_ids': [f'E{i:02d}' for i in range(11, 16)],
    'geometry_change': 'S021补入北侧大厅东侧门前蓝色缺口；S091补入S099与S107之间可见横通道，延伸至S118门洞。',
    'source_sha256': {f.name: hashlib.sha256(f.read_bytes()).hexdigest()
                      for f in BACKUP.iterdir() if f.is_file()},
}
(ROOT / '复核变更记录.json').write_text(json.dumps(changes, ensure_ascii=False, indent=2))
print(json.dumps({'spaces': len(data['spaces']),
                  'relations': collections.Counter(r['type'] for r in rels.values()),
                  'openings': len(points)}, ensure_ascii=False))
