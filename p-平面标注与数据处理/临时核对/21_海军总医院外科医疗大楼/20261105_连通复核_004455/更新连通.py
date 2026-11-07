"""21 only: visually audited openings in the upright reading coordinates."""
import json
import sys
from collections import Counter
from pathlib import Path
from shapely.geometry import Polygon, box, Point
from shapely.ops import unary_union

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2] / '标注试样'
PROJECT = next(ROOT.glob('21_*'))
SKILL = Path('/Users/hushili/.codex/skills/outpatient-plan-annotation')
sys.path.insert(0, str(SKILL / 'scripts'))
import annotation_tools as at

data = json.loads((WORK / '复核前四文件与用户填写' / 'annotation.json').read_text())
original = json.loads(json.dumps(data))
spaces = {s['id']:s for s in data['spaces']}
relations = {r['id']:r for r in data['relations']}
audit = []


def reading(sid):
    return Polygon([(y,2443-x) for x,y in spaces[sid]['polygon_px']])


def geometry(sid, shape):
    assert shape.geom_type == 'Polygon' and shape.is_valid and not shape.interiors
    spaces[sid]['polygon_px'] = [[round(2443-y,2),round(x,2)] for x,y in list(shape.exterior.coords)[:-1]]


def new_space(sid,name,shape,scope):
    node = dict(id=sid,name=name,type='corridor',level='open_space',scope=scope,polygon_px=[])
    data['spaces'].append(node)
    spaces[sid] = node
    geometry(sid,shape)


def remove(rid,reason):
    old = relations.pop(rid)
    audit.append(dict(action='remove',old=old,reason=reason))


def correct(rid,source,target,reason):
    old = relations[rid].copy()
    relations[rid].update(source=source,target=target)
    audit.append(dict(action='correct',old=old,new=relations[rid].copy(),reason=reason))


def relation(source,target,typ='access'):
    for row in relations.values():
        if row['type'] == typ and {row['source'],row['target']} == {source,target}:
            return row
    index = max(int(k[1:]) for k in relations if k.startswith('R')) + 1
    row = dict(id=f'R{index:03d}',source=source,target=target,type=typ)
    relations[row['id']] = row
    audit.append(dict(action='add',new=row.copy()))
    return row


# Corridors are individually traced from this plan, not generated from adjacency.
g155 = unary_union([box(745,532,797,691),box(765,651,932,691),box(670,531,745,572)])
g155 = g155.difference(unary_union([reading(sid) for sid in spaces]))
new_space('S155','急诊北侧后勤通道',g155,'emergency')
new_space('S156','中央西侧交通厅',box(1108,502,1286,863),'public_service')
new_space('S157','体检西侧过道',box(2144,1227,2208,1333),'health_examination')
new_space('S158','整形北侧后勤通道',box(2338,544,2420,571),'plastic_surgery')
geometry('S068',box(1108,386,1975,500))
geometry('S075',unary_union([reading('S075'),box(2072,1402,2142,1456)]))
geometry('S112',unary_union([reading('S112'),box(2442,1056,2482,1095)]))

correct('R011','S005','S057','第五间观察室的北门直接通办公前通道，未穿过前四间观察室前通道。')
correct('R012','S020','S155','收费窗口前为补齐的后勤通道；服务联系不代替人员通行。')
correct('R013','S021','S155','药房柜台朝向补齐的通道，原大厅关系跨过该通道。')
correct('R014','S034','S014','骨科北门开向急诊大厅；向中部通道需经过外科，分步建连。')
correct('R019','S046','S048','贵宾室的可见东门通急诊东侧通道。')
correct('R053','S073','S076','咖啡楼梯南门进入当前S076所含的前室通行区，不跨楼梯西侧实墙。')
correct('R059','S083','S157','体检候诊廊先经西侧过道，再接内部通道。')
correct('R077','S081','S075','抽血北门前属补齐的候诊及导医开放区，未跨过耳鼻喉房间。')
correct('R116','S134','S158','污物间南门先接后勤小通道。')
correct('R117','S138','S158','库房西门先接后勤小通道。')
correct('R123','S141','S117','医办的西南门朝向主通道，原东侧通道关系跨过卫生间。')
correct('R100','S131','S125','点痣西侧门进入相邻皮护S125，并非越过其直接进入主通道。')
correct('R101','S130','S125','激光S130的西侧门进入皮护S125，按实际房间顺序建连。')
for rid,reason in {
    'R029':'值班S059未见清楚通会议区的门，属本轮不细究的内部支持房间。',
    'R060':'S084与S101之间不能直接穿越卫生间；移除跨中间空间的连接。',
    'R066':'整形厅与东侧通道之间有连续墙线；实际通道接口另列K04-A复核，不保留无依据捷径。',
    'R067':'主通道与东侧处置通道的门线归属列K04-A待确认，不把卫生间门误作通道门。',
    'R068':'首长门厅到公共楼梯核跨过S115；S115的对外连接列K02待确认。',
    'R083':'煤表间S111不直接面对候诊廊，原连接跨过开水间S110。',
    'R105':'护发S123的直接入口列K03，不把邻接当作门。',
    'R107':'纹眉S128的直接入口列K03，不把邻接当作门。',
    'R121':'处理室S147的直接入口列K04，暂不认定直通东侧通道。',
    'R111':'更衣S122朝主通道的门未清楚显示，本轮不细究内部工作人员支持细节。',
}.items():
    remove(rid,reason)

# Region continuity and counters: concept relations, without fabricated points.
concepts = [
    ('S014','S155','急诊大厅与后勤通道南端图面连续。'),
    ('S022','S155','收费药房外侧通道与检验前通道连续。'),
    ('S014','S022','检验前通道的南端向大厅开放。'),
    ('S156','S066','西侧交通厅南端连续进入住院大厅。'),
    ('S039','S025','布局推断：护士站南侧工作入口接候诊周边通道；不标精确门位。'),
    ('S084','S157','体检内部通道南端经西侧过道延续。'),
    ('S101','S097','检查区小过道北端与卫生间外侧共用前区连续，不推断厕位内部路线。'),
    ('S117','S158','整形后勤小通道接主通道北侧支段。'),
]
for a,b,why in concepts:
    row = relation(a,b)
    audit.append(dict(action='concept_evidence',relation=row['id'],source=a,target=b,reason=why))
for a,b in [('S028','S014'),('S039','S026'),('S069','S066'),('S078','S077')]:
    relation(a,b,'service')

# Individually observed door positions, expressed in the upright reading image.
# No centroid/shared-wall midpoint is used to manufacture an opening.
doors = [
    # Acute west wing, staff preparation support and central rooms.
    ('S010','S014',415,722),('S007','S025',415,1093),('S006','S025',371,1326),
    ('S001','S025',304,1399),('S002','S025',435,1399),('S003','S025',562,1399),
    ('S004','S025',717,1399),('S005','S057',838,1399),
    ('S009','S010',295,779),('S008','S007',295,959),
    ('S013','S014',445,546),('S013','S014',553,546),
    ('S016','S155',745,604),('S017','S155',671,553),('S018','S155',764,657),
    ('S019','S155',723,531),('S020','S155',799,548),('S021','S022',933,619),
    ('S024','S022',975,553),('S023','S022',975,608),
    ('S027','S025',477,1037),('S029','S032',644,1025),
    ('S030','S032',644,957),('S031','S032',644,896),
    ('S034','S014',818,789),('S034','S033',820,873),('S036','S035',862,873),
    ('S033','S032',820,979),('S035','S032',863,979),
    ('S037','S048',1039,887),('S042','S032',822,1131),('S045','S032',864,1131),
    ('S046','S048',1039,1201),('S040','S039',792,1312),('S041','S039',792,1258),
    ('S054','S048',1107,934),('S053','S048',1107,985),
    ('S052','S048',1107,1117),('S051','S048',1107,1178),
    ('S055','S066',1287,1127),('S056','S066',1287,1040),
    ('S049','S047',1107,1238),('S049','S057',1268,1361),('S050','S057',1127,1358),
    ('S060','S061',960,1475),('S062','S061',1105,1475),('S063','S061',1142,1475),
    ('S065','S061',1208,1420),
    # Central doors and traffic cores: only the block's visible exterior interfaces.
    ('S014','S156',1107,735),('S068','S156',1165,501),('S068','S066',1880,501),
    ('S067','S066',1297,739),('S067','S066',1380,739),
    ('S071','S066',1710,739),('S071','S066',1820,739),
    ('S067','S070',1464,540),('S067','S070',1464,597),
    ('S067','S070',1464,655),('S067','S070',1464,712),
    ('S071','S070',1620,539),('S071','S070',1620,597),
    ('S071','S070',1620,655),('S071','S070',1620,712),
    ('S152','S066',1454,1557),('S152','S066',1580,1557),
    ('S079','S077',2071,1016),('S073','S076',1840,1296),
    ('S076','S066',1796,1375),('S075','S066',1796,1430),('S077','S076',2125,1299),
    # Examination rooms and support spaces, using their actual facing corridor.
    ('S081','S075',2125,1457),('S082','S083',2161,1457),('S086','S083',2304,1457),
    ('S091','S083',2332,1457),('S095','S083',2474,1457),('S100','S083',2510,1457),
    ('S103','S083',2646,1457),('S105','S083',2685,1457),('S108','S083',2827,1457),
    ('S102','S083',2544,1334),('S104','S083',2598,1334),('S106','S083',2632,1334),
    ('S107','S083',2740,1334),('S109','S083',2770,1334),('S110','S083',2870,1334),
    ('S087','S083',2231,1334),('S092','S083',2372,1334),('S096','S083',2400,1334),
    ('S085','S084',2183,1054),('S090','S084',2218,1054),('S093','S084',2293,1054),
    ('S094','S084',2347,1054),('S099','S084',2407,1054),
    ('S089','S084',2191,1151),('S088','S084',2191,1193),
    ('S098','S084',2341,1117),('S097','S084',2341,1180),
    ('S097','S112',2481,1196),('S084','S112',2441,1072),
    ('S114','S112',2573,1183),('S114','S112',2840,1183),
    # Plastic surgery and its support corridor.
    ('S117','S066',1976,652),('S150','S149',2525,547),('S150','S149',2652,547),
    ('S119','S117',2058,627),('S121','S117',2080,627),('S125','S117',2220,627),
    ('S118','S117',2028,679),('S120','S117',2133,679),
    ('S124','S117',2210,679),('S129','S117',2260,679),
    ('S131','S125',2240,553),('S130','S125',2240,614),
    ('S133','S117',2337,620),('S134','S158',2345,543),
    ('S139','S158',2404,543),('S138','S158',2421,554),
    ('S126','S117',2197,856),('S127','S117',2273,856),
    ('S132','S117',2355,856),('S135','S117',2403,856),
    ('S137','S117',2394,679),('S142','S117',2461,679),('S136','S117',2370,776),
    ('S141','S117',2519,810),('S144','S151',2677,744),
    ('S145','S151',2690,627),('S148','S151',2738,674),('S146','S151',2782,819),
    ('S117','S116',2633,856),
]
passages = [
    ('S038','S048',1039,812),('S044','S047',1061,1269),('S043','S047',1061,1336),
    ('S061','S057',1185,1399),('S149','S117',2500,656),
]
distances = []
for kind,items in [('door',doors),('open_passage',passages)]:
    for source,target,x,y in items:
        row = relation(source,target)
        number = sum(len(r.get('openings',[])) for r in relations.values()) + 1
        oid = f'P{number:03d}'
        position = [2443-y,x]
        distances.append(dict(id=oid,source=source,target=target,reading=[x,y],
            source_distance=round(reading(source).distance(Point(x,y)),2),
            target_distance=round(reading(target).distance(Point(x,y)),2)))
        row.setdefault('openings',[]).append(dict(id=oid,kind=kind,position_px=position))

data['relations'] = list(relations.values())
at.normalize(data)
report,code = at.check(data,PROJECT/'annotation.json')
(WORK / '门位距离审计.json').write_text(json.dumps(distances,ensure_ascii=False,indent=2))
(WORK / '关系调整依据.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
(WORK / '连通复核候选.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
print('types',Counter(r['type'] for r in data['relations']))
print('openings',len(distances),'distance over 18', [r for r in distances if max(r['source_distance'],r['target_distance'])>18])
assert code == 0, report
