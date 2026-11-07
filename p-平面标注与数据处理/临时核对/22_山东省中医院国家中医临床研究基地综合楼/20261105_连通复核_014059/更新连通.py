from pathlib import Path
import json

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
PLAN = ROOT / '标注试样/22_山东省中医院国家中医临床研究基地综合楼'
FILE = PLAN / 'annotation.json'
data = json.loads(FILE.read_text())
rels = {r['id']: r for r in data['relations']}
changes = []

def revise(rid, target, reason):
    r = rels[rid]
    changes.append({'id': rid, 'before': dict(r), 'reason': reason})
    r['target'] = target

revise('R011', 'S013', '北侧大卫生间的南向出入口落在西侧候诊区S013，未直接落在起于x750的北侧通道S014。')
revise('R053', 'S054', '输液中心南侧双扇门朝南进入中部门诊大厅S054；西墙未见通往S043的门，不沿用旧稿错误端点。')

def add(source, target, reason):
    number = max(int(r['id'][1:]) for r in data['relations'] if r['id'].startswith('R')) + 1
    rid = f'R{number:03}'
    r = {'id': rid, 'source': source, 'target': target, 'type': 'access'}
    data['relations'].insert(-1, r)
    rels[rid] = r
    changes.append({'id': rid, 'after': dict(r), 'reason': reason})
    return rid

bridge = add('S054', 'S069', '中部大厅东南侧与中医文化廊北端连续，填色变化处没有实体隔墙；按区域连续补概念连接，不编造门位。')
registration = add('S052', 'S054', '挂号收费工作区北侧右端可见小门朝中部大厅；与既有柜台service分开保存。')
pipe_ids = {}
for sid, adjacent, reason in [
    ('S010', 'S014', '北部管井南侧可辨检修门。'),
    ('S026', 'S015', '西侧管井东侧可辨双扇检修门；不由此推断交通核必须经管井通行。'),
    ('S050', 'S049', '医护核旁管井北侧可辨检修门。'),
    ('S061', 'S059', '西南管井东侧可辨检修门。'),
    ('S064', 'S069', '病房核上排管井西侧可辨检修门。'),
    ('S065', 'S069', '病房核下排管井西侧可辨检修门。'),
]:
    pipe_ids[sid] = add(sid, adjacent, reason)

# 以下坐标由本图坐标局部图逐个读取；不是多边形质心或共墙中点。
doors = {
    'R011': [(716, 620)],
    'R012': [(1443, 620)],
    'R013': [(1686, 620)],
    'R014': [(1764, 620)],
    'R015': [(1820, 620), (1897, 620)],
    'R016': [(969, 620)], 'R017': [(1048, 620)],
    'R018': [(1127, 620)], 'R019': [(1206, 620)],
    'R020': [(1284, 620)], 'R021': [(1362, 620)],
    'R022': [(970, 694)], 'R023': [(1048, 694)],
    'R024': [(1127, 694)], 'R025': [(1206, 694)],
    'R026': [(1284, 694)], 'R027': [(1363, 694)],
    'R028': [(1444, 694)],
    'R033': [(1126, 1125)], 'R034': [(1205, 1125)],
    'R035': [(1283, 1125)], 'R036': [(1362, 1125)],
    'R037': [(1127, 1200)], 'R038': [(1205, 1200)],
    'R039': [(1284, 1200)], 'R040': [(1363, 1200)],
    'R041': [(1443, 1125)], 'R042': [(1444, 1200)],
    'R043': [(750, 1241)],
    'R052': [(1694, 694)], 'R053': [(1668, 1352)],
    'R054': [(1795, 1352)], 'R055': [(1848, 1330)],
    'R057': [(1757, 1498)],
    'R060': [(750, 1548)], 'R061': [(709, 1721)],
    'R062': [(765, 1754), (765, 2105)],
    'R067': [(758, 2244)],
    'R068': [(782, 2338), (1310, 2338)],
    'R069': [(1434, 2338)], 'R070': [(1530, 2370)],
    'R071': [(1530, 1767), (1530, 1801)],
    'R074': [(1724, 2096)], 'R075': [(1768, 2200)],
    'R076': [(1724, 2275)],
    registration: [(1700, 1498)],
    pipe_ids['S010']: [(1576, 620)],
    pipe_ids['S026']: [(750, 1178)],
    pipe_ids['S050']: [(1860, 1498)],
    pipe_ids['S061']: [(758, 2316)],
    pipe_ids['S064']: [(1724, 1950)],
    pipe_ids['S065']: [(1724, 2010)],
}
open_passages = {'R029': [(913, 694)]}
pid = 1
for r in data['relations']:
    for kind, mapping in [('door', doors), ('open_passage', open_passages)]:
        for point in mapping.get(r['id'], []):
            assert r['type'] == 'access'
            r.setdefault('openings', []).append({
                'id': f'P{pid:03}', 'kind': kind, 'position_px': list(point)
            })
            pid += 1

FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
(WORK / '关系调整依据.json').write_text(json.dumps(changes, ensure_ascii=False, indent=2))
concepts = [r for r in data['relations'] if r['type'] == 'access' and not r.get('openings')]
(WORK / '无定位概念连接.json').write_text(json.dumps(concepts, ensure_ascii=False, indent=2))
print(json.dumps({'relations': len(data['relations']), 'openings': pid - 1,
                  'conceptual_access': len(concepts), 'changed_or_added': len(changes)}, ensure_ascii=False))
