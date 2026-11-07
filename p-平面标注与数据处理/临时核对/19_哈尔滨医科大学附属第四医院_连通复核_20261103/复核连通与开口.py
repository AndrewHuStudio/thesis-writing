from pathlib import Path
import importlib.util
import json
from shapely.geometry import Polygon, Point

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SAMPLE = ROOT / 'p-平面标注与数据处理/标注试样/19_哈尔滨医科大学附属第四医院门诊外科楼'
data = json.loads((OUT / '名称同步后.json').read_text())
spaces = {s['id']: s for s in data['spaces']}

# 原图可见公共地面与药房门口的两段走道，补入原有通道节点。
# 这里只补原草稿遗漏的连续地面，不新增编号、不吞并已有房间。
spaces['S029']['polygon_px'] = [[336, 870], [837, 870], [837, 714], [973, 714], [973, 931], [336, 931]]
spaces['S064']['polygon_px'] = [[434, 1076], [536, 1076], [536, 1112], [467, 1112], [467, 1415], [272, 1415], [272, 1380], [434, 1380]]
spaces['S027']['polygon_px'] = [[229, 870], [267, 870], [267, 1566], [229, 1566]]

# 修改有明确图面反证的旧关系；未见门不自动等于永不连通。
revised = {
    'R013': ('S011', 'S001'),
    'R023': ('S030', 'S029'),
    'R042': ('S051', 'S071'),
    'R051': ('S120', 'S027'),
    'R058': ('S043', 'S108'),
    'R066': ('S131', 'S112'),
    'R074': ('S148', 'S149'),
    'R103': ('S079', 'S091'),
    'R106': ('S082', 'S091'),
    'R095': ('S037', 'S024'),
    'R116': ('S124', 'S027'),
}
removed = {'R034', 'R047', 'R048', 'R110', 'R111', 'R112'}
data['relations'] = [r for r in data['relations'] if r['id'] not in removed]
for relation in data['relations']:
    rid = relation['id']
    if rid in revised:
        relation['source'], relation['target'] = revised[rid]
    if rid in {'R004', 'R005'}:
        relation['type'] = 'service'

def pair(a, b, kind='access'):
    return kind, tuple(sorted((a, b)))

relations = {pair(r['source'], r['target'], r['type']): r for r in data['relations'] if r['source'] is not None}
next_relation = max(int(r['id'][1:]) for r in data['relations'] if r['id'].startswith('R')) + 1
new_relations = []

def ensure(a, b, kind='access'):
    global next_relation
    key = pair(a, b, kind)
    if key not in relations:
        relation = {'id': f'R{next_relation:03d}', 'source': a, 'target': b, 'type': kind}
        next_relation += 1
        relations[key] = relation
        data['relations'].append(relation)
        new_relations.append(relation['id'])
    return relations[key]

# 下列是原图门扇/开口的人工逐处定位，原图像素坐标；不是质心或共墙中点。
doors = [
    ('S003', 'S002', 1201, 527), ('S006', 'S022', 337, 756),
    ('S005', 'S027', 250, 867), ('S007', 'S029', 430, 867),
    ('S008', 'S029', 500, 867), ('S009', 'S029', 570, 867),
    ('S010', 'S029', 710, 867), ('S010', 'S001', 710, 714),
    ('S011', 'S001', 800, 714), ('S026', 'S027', 226, 901),
    ('S028', 'S027', 272, 887), ('S039', 'S029', 362, 935),
    ('S040', 'S029', 505, 935), ('S030', 'S029', 977, 895),
    ('S029', 'S043', 915, 935), ('S030', 'S044', 1110, 935),
    ('S030', 'S046', 1290, 935), ('S030', 'S031', 1429, 895),
    ('S015', 'S023', 1803, 757), ('S025', 'S024', 2271, 841),
    ('S016', 'S024', 1900, 819), ('S017', 'S024', 1975, 819),
    ('S018', 'S024', 2050, 819), ('S019', 'S024', 2120, 819),
    ('S020', 'S024', 2180, 819), ('S021', 'S024', 2240, 819),
    ('S035', 'S034', 1873, 909), ('S037', 'S024', 2201, 902),
    ('S053', 'S052', 2201, 962), ('S062', 'S052', 2201, 1032),
    ('S051', 'S071', 2035, 1073), ('S059', 'S071', 1761, 1073),
    ('S060', 'S071', 1835, 1073), ('S061', 'S071', 1899, 1073),
    ('S063', 'S027', 226, 1098), ('S065', 'S027', 272, 1098),
    ('S066', 'S064', 431, 1098), ('S041', 'S064', 540, 1090),
    ('S075', 'S027', 272, 1171), ('S075', 'S027', 272, 1234),
    ('S076', 'S064', 431, 1187), ('S073', 'S064', 470, 1187),
    ('S074', 'S027', 226, 1172), ('S084', 'S027', 226, 1231),
    ('S087', 'S027', 226, 1313), ('S098', 'S027', 226, 1391),
    ('S101', 'S027', 226, 1452), ('S088', 'S027', 272, 1330),
    ('S090', 'S064', 470, 1318), ('S099', 'S064', 470, 1379),
    ('S064', 'S027', 272, 1395),
    ('S078', 'S071', 1690, 1142), ('S077', 'S078', 1605, 1225),
    ('S094', 'S078', 1648, 1340), ('S078', 'S113', 1636, 1422),
    ('S078', 'S115', 1840, 1422),
    ('S080', 'S071', 1990, 1142), ('S081', 'S071', 2070, 1142),
    ('S079', 'S091', 1910, 1272), ('S080', 'S091', 1990, 1272),
    ('S081', 'S091', 2054, 1272), ('S082', 'S091', 2114, 1272),
    ('S079', 'S080', 1945, 1245), ('S081', 'S082', 2087, 1245),
    ('S095', 'S091', 1910, 1310), ('S096', 'S091', 1990, 1310),
    ('S097', 'S091', 2090, 1310),
    ('S083', 'S052', 2201, 1176), ('S086', 'S052', 2201, 1235),
    ('S092', 'S052', 2201, 1310), ('S100', 'S052', 2201, 1379),
    ('S119', 'S052', 2201, 1461), ('S072', 'S052', 2201, 1105),
    ('S116', 'S122', 1938, 1524), ('S117', 'S122', 2055, 1524),
    ('S118', 'S122', 2117, 1524),
    ('S112', 'S122', 1576, 1545), ('S122', 'S052', 2155, 1545),
    ('S120', 'S027', 226, 1533), ('S102', 'S121', 366, 1518),
    ('S103', 'S121', 431, 1518), ('S104', 'S121', 500, 1518),
    ('S124', 'S027', 244, 1570), ('S125', 'S121', 374, 1570),
    ('S126', 'S121', 415, 1570), ('S127', 'S121', 524, 1570),
    ('S129', 'S121', 640, 1570), ('S129', 'S142', 637, 1705),
    ('S146', 'S142', 575, 1756), ('S147', 'S142', 646, 1756),
    ('S132', 'S145', 1751, 1709), ('S139', 'S145', 1986, 1709),
    ('S140', 'S145', 2040, 1709), ('S148', 'S149', 1730, 1798),
    ('S155', 'S149', 1801, 1824), ('S151', 'S145', 2055, 1758),
    ('S152', 'S145', 2130, 1758), ('S153', 'S145', 2180, 1758),
    ('S154', 'S145', 2254, 1758),
    ('S160', 'S161', 684, 2160), ('S160', 'S161', 684, 2320),
    ('S165', 'S164', 1388, 2160), ('S165', 'S164', 1388, 2320),
    ('S162', 'S161', 833, 2126), ('S167', 'S161', 833, 2334),
    ('S166', 'S162', 870, 2158), ('S168', 'S167', 868, 2318),
    ('S170', 'S172', 665, 2607), ('S173', 'S177', 1300, 2704),
    ('S067', 'S093', 1058, 1295), ('S085', 'S093', 1350, 1295),
    ('S070', 'S047', 1429, 1137), ('S069', 'S070', 1369, 1137),
    ('S055', 'S043', 977, 1046), ('S058', 'S047', 1429, 1046),
    ('S132', 'S122', 1764, 1571), ('S145', 'S052', 2178, 1709),
    ('S134', 'S139', 1980, 1645), ('S135', 'S122', 2050, 1571),
    ('S135', 'S052', 2155, 1595),
]
point_audit = []
for number, (a, b, x, y) in enumerate(doors, 1):
    relation = ensure(a, b)
    opening = {'id': f'P{number:03d}', 'kind': 'door', 'position_px': [x, y]}
    relation.setdefault('openings', []).append(opening)
    distances = [round(Polygon(spaces[s]['polygon_px']).distance(Point(x, y)), 2) for s in [a, b]]
    point_audit.append({'id': opening['id'], 'relation': relation['id'], 'pair': [a, b], 'position_px': [x, y], 'distance_to_polygons': distances})

# 连续公共地面以概念access保存；没有独立门洞就不生成定位红点。
continuity = [
    ('S002', 'S029'), ('S002', 'S014'), ('S024', 'S052'),
    ('S093', 'S109'), ('S093', 'S111'), ('S047', 'S112'),
    ('S143', 'S144'), ('S144', 'S145'), ('S143', 'S156'),
    ('S172', 'S171'), ('S177', 'S176'),
]
for a, b in continuity:
    ensure(a, b)

spec = importlib.util.spec_from_file_location('annotation_tools', '/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts/annotation_tools.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.normalize(data)
(SAMPLE / 'annotation.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
(OUT / '门洞逐点定位.json').write_text(json.dumps(point_audit, ensure_ascii=False, indent=2) + '\n')
(OUT / '连通修改记录.json').write_text(json.dumps({'removed_unsupported': sorted(removed), 'revised': revised, 'service_instead_of_access': ['R004', 'R005'], 'new_relation_ids': new_relations, 'continuous_floor': continuity, 'range_additions': ['S029:补公共走道西北段', 'S064:补药房西北门外连续通道'], 'critical_pending': 'K01:儿童输液室S049与电梯前室S050的实际对外通路，现有像素不能确定，不从共墙编造连接', 'noncritical_internal': ['S001/S004住院办理柜台后台细节', 'S032/S033/S034/S035及S105/S106的半墙服务带后台通路', 'S055/S058/S128/S133/S137/S138小井道', 'S089麻药室与S114附间的内部开门细节']}, ensure_ascii=False, indent=2) + '\n')
print({'spaces': len(data['spaces']), 'relations': len(data['relations']), 'located_doors': len(doors), 'coordinate_distance_over_12': [p for p in point_audit if max(p['distance_to_polygons']) > 12]})
