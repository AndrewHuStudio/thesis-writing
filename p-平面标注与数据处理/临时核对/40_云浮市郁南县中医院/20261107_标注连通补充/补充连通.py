from pathlib import Path
import json
import sys
from shapely.geometry import Polygon, Point

ROOT = Path(__file__).resolve().parents[3]
SAMPLE = ROOT / '标注试样/40_云浮市郁南县中医院'
OUT = Path(__file__).resolve().parent
STATE = OUT.parent / 'review_state.json'
sys.path.insert(0, '/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts')
from annotation_tools import normalize
from review_workflow import load_state, save_state

# Always derive from this run's immutable baseline, preserving S/R/E identifiers.
data = json.loads((OUT / '接续前四文件备份/annotation.json').read_text())
spaces = {s['id']: s for s in data['spaces']}
for sid in ('S015', 'S022'):
    spaces[sid]['polygon_px'] = [
        [x, 370 if y == 353 and 1710 <= x <= 1830 else y]
        for x, y in spaces[sid]['polygon_px']]
    pts = spaces[sid]['polygon_px']
    spaces[sid]['polygon_px'] = [p for i, p in enumerate(pts) if p != pts[i - 1]]
# The northern porch and lobby meet at the visible double door, y=2047.
pts = spaces['S050']['polygon_px']
idx = pts.index([1070.0, 2062.0])
pts[idx:idx + 1] = [[1070, 2047], [955, 2047], [955, 2062]]
# Include the small vestibule of the second private dining block.
spaces['S009']['polygon_px'] = [[x, 326 if y == 337 else y]
                                for x, y in spaces['S009']['polygon_px']]

deleted = {'R013': '东交通核经独立电梯前室S018接入特殊发热门诊，原直接跨前室边删除。',
           'R034': '北楼梯S051可见门朝西侧室外；东侧为背墙，删除无门依据的大厅直连。'}
data['relations'] = [r for r in data['relations'] if r['id'] not in deleted]
rels = {r['id']: r for r in data['relations']}
for rid in ('R048', 'R049'):
    rels[rid]['type'] = 'access'
rels['R043']['source'] = 'S072'

# Points are individually read from this floor plan, in its source pixels.
doors = {
    'R001': [(294, 266)],
    'R003': [(438, 283)],
    'R004': [(565, 246), (688, 246)],
    'R005': [(504, 246)],
    'R006': [(720, 283), (790, 283)],
    'R007': [(622, 283)],
    'R008': [(734, 310)],
    'R009': [(790, 310)],
    'R010': [(1473, 268)],
    'R011': [(1820, 370)],
    'R014': [(1165, 1080)],
    'R015': [(1230, 1080)],
    'R016': [(1665, 1080)],
    'R017': [(1780, 1047)],
    'R018': [(1825, 1047)],
    'R019': [(1805, 1100)],
    'R020': [(1275, 1135)],
    'R022': [(1073, 1340), (1073, 1460)],
    'R023': [(1073, 1527)],
    'R024': [(950, 1730), (950, 1808)],
    'R025': [(1010, 1888)],
    'R026': [(585, 1265)],
    'R027': [(845, 1265), (914, 1265)],
    'R028': [(455, 1405)],
    'R029': [(285, 1391)],
    'R030': [(350, 1795)],
    'R032': [(1012, 2047)],
    'R033': [(1070, 2145), (1168, 2192)],
    'R035': [(758, 2310)],
    'R036': [(390, 2350)],
    'R037': [(376, 2365)],
    'R038': [(1268, 2280)],
    'R041': [(758, 2630)],
    'R042': [(1268, 2617)],
    'R043': [(1580, 2534), (1640, 2534)],
    'R044': [(1680, 2310)],
    'R045': [(1690, 2563), (1690, 2690)],
}
open_passages = {'R031': [(868, 2062), (910, 2062), (945, 2062)],
                 'R047': [(1092, 2320)]}
added = []

def relation(rid, a, b, kind='access', positions=None, opening_kind='door', reason=''):
    r = {'id': rid, 'source': a, 'target': b, 'type': kind}
    data['relations'].append(r)
    rels[rid] = r
    if positions:
        (doors if opening_kind == 'door' else open_passages)[rid] = positions
    added.append({'relation_id': rid, 'source': a, 'target': b,
                  'type': kind, 'reason': reason})

relation('R058', 'S006', 'S008', reason='布局推断：包间功能块经北侧小前室接餐饮入口厅，不细分内部小门。')
relation('R059', 'S006', 'S009', reason='布局推断：第二包间上侧前室通向餐饮入口厅，保留功能块级连接。')
relation('R060', 'S007', 'S002', positions=[(417, 207), (417, 263)], reason='卫生间东侧两处可见开门。')
relation('R061', 'S033', 'S032', positions=[(1193, 1220)], reason='高压氧舱北侧配套单元与舱室之间可见门。')
relation('R062', 'S041', 'S045', positions=[(318, 1488)], reason='设备电梯厅南侧双扇门通影像内部走道。')
relation('R063', 'S039', 'S042', positions=[(455, 1430)], reason='库区南侧配套单元东侧可见门。')
relation('R064', 'S065', 'S066', reason='图面连续：候药厅东缘与大厅扶梯西侧片区无分隔。')
relation('R065', 'S065', 'S067', reason='图面连续：候药厅东缘与主大厅连续，原图无实体分隔。')
relation('R066', 'S060', 'S052', reason='布局推断：北端卫生间功能块包含入口小厅，向南接医护区公共通道。')
relation('R067', 'S053', 'S059', positions=[(340, 2252), (430, 2252)], reason='药房北侧两间配套单元南侧可见门。')
relation('R068', 'S060', 'S061', positions=[(284, 2340)], opening_kind='open_passage', reason='电梯门向东面医护通道。')
relation('R069', 'S070', 'S071', positions=[(305, 2610)], reason='西南楼梯东侧门接儿科门诊。')
relation('R070', 'S062', 'S067', positions=[(920, 2384)], opening_kind='open_passage', reason='扶梯下侧梯口朝向主大厅。')
relation('R071', 'S064', 'S073', positions=[(1745, 2534)], reason='东交通核南侧门直接接输液区北端。')
relation('R072', 'S059', 'S065', kind='service', reason='长排取药柜台的服务界面在工作人员区与候药厅之间。')
relation('R073', 'S015', 'S018', reason='图面连续：特殊发热门诊走道东端进入独立电梯前室。')
relation('R074', 'S018', 'S016', positions=[(1935, 282)], reason='前室东侧门进入东楼梯，北侧电梯门另记开口。')
open_passages['R074'] = [(1855, 246), (1900, 246)]
relation('R075', 'S031', 'S029', kind='service', reason='住院药房西侧可见连续服务柜台；人员入口另列K02。')
relation('R076', 'S019', 'S022', positions=[(1575, 415)], reason='影像配套组西南侧可见门通普通发热门诊走道；用途仍保留unknown。')
relation('R077', 'S017', 'S021', reason='布局推断：西侧配套组北侧出入朝向医护厅；保留组级连接，不展开内部小间路线。')

opening_number = 0
for r in data['relations']:
    for kind, mapping in [('door', doors), ('open_passage', open_passages)]:
        for position in mapping.get(r['id'], []):
            opening_number += 1
            r.setdefault('openings', []).append({'id': f'P{opening_number:03}',
                                                 'kind': kind, 'position_px': list(position)})

# Refine existing entrance centers where the source shows separate actual doorways.
for eid, pos in {'E03': (680, 425), 'E08': (2035, 400),
                 'E10': (1390, 1295), 'E13': (850, 2736)}.items():
    rels[eid]['position_px'] = list(pos)

def entrance(eid, target, name, kind, pos):
    data['relations'].append({'id': eid, 'source': None, 'target': target,
                             'type': 'entrance', 'name': name,
                             'entrance_type': kind, 'position_px': list(pos)})

entrance('E19', 'S051', '门诊北楼梯西入口', 'egress', (830, 2162))
entrance('E20', 'S067', '门诊主入口东门', 'public', (1190, 2736))
entrance('E21', 'S071', '儿科门诊西侧南入口', 'public', (350, 2718))
entrance('E22', 'S033', '高压氧舱北侧配套区南入口', 'public', (1280, 1295))
entrance('E23', 'S029', '住院大厅南侧东入口', 'public', (1590, 1295))
normalize(data)
(SAMPLE / 'annotation.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

name_ids = ['S003', 'S018', 'S019', 'S020', 'S021', 'S025',
            'S033', 'S042', 'S053', 'S057', 'S068', 'S069']
state = {'name_items': [{'review_id': f'{i:02}', 'space_id': sid, 'status': 'pending'}
                        for i, sid in enumerate(name_ids, 1)],
         'connectivity_items': [
             {'review_id': 'K01', 'source': 'S017', 'target': 'S015', 'status': 'pending',
              'question': '医护厅是否经东侧缓冲小间进入特殊发热门诊？',
              'reason': '缓冲小间门的贯通路径不清，未建立跨区access。'},
             {'review_id': 'K02', 'source': 'S029', 'target': 'S031', 'status': 'pending',
              'question': '住院药房是否经北侧人员口直接接住院大厅？',
              'reason': '西侧服务柜台清楚，北侧人员门不清，当前只记service。'},
             {'review_id': 'K03', 'source': 'S069', 'target': 'S067', 'status': 'pending',
              'question': 'S069是否为可通行的长条空间，东接大厅、西接S060？',
              'reason': '需结合12号用途判断长条空间可达性，未仅凭相邻补边。'}],
         'checks': {'connectivity_reviewed': True, 'visual_reviewed': False},
         'mapping_source': '沿用2026-10-31首轮固定01—12映射；当前MD无已填写答案。',
         'review_scope': '73节点功能区级；不逐室拆分内部小间；独立外门不通过室外总节点互连。',
         'not_required_details': ['发热门诊、影像科、儿科、办公区等功能块内小房间路线不继续拆分。',
                                  '庭院候选先核实用途；一旦确认为庭院或挑空直接排除面积，无须再次问顶盖。'],
         'relation_changes': {'deleted': deleted, 'added': added,
             'corrected': {'R043': '留观室南端两门直接接护士站所在前区S072，经R046接急救；纠正原跨节点边。',
                           'R044': '急救经东交通核北门接入，未把留观室与交通核共墙误当通路。',
                           'R048': '药房与取药工作人员区之间无分隔，改access；柜台service移至R072。',
                           'R049': '同R048，西药房与工作人员区连续。'}},
         'layout_inferences': [a for a in added if '布局推断' in a['reason']],
         'conceptual_relations': [{'id': r['id'], 'source': r['source'], 'target': r['target']}
                                  for r in data['relations'] if r['type'] == 'access' and not r.get('openings')]}
STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')
save_state(STATE, load_state(STATE, data, SAMPLE / 'annotation.json'))
polys = {sid: Polygon(s['polygon_px']) for sid, s in spaces.items()}
audit = []
for r in data['relations']:
    for o in r.get('openings', []):
        p = Point(o['position_px'])
        distances = {sid: round(polys[sid].boundary.distance(p), 3)
                     for sid in (r['source'], r['target'])}
        audit.append({'opening_id': o['id'], 'relation_id': r['id'],
                      'position_px': o['position_px'], 'boundary_distances_px': distances})
(OUT / '门洞端点审计.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'spaces': len(spaces), 'relations': len(data['relations']),
                  'openings': opening_number,
                  'boundary_exceptions': [a for a in audit if max(a['boundary_distances_px'].values()) > .1]},
                 ensure_ascii=False, indent=2))
