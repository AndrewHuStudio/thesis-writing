"""Apply explicit name answers and manually inspected connections for plan 25."""
from pathlib import Path
from collections import Counter, deque
import copy
import hashlib
import html
import json
import re
import sys
import xml.etree.ElementTree as ET

OUT = Path(__file__).resolve().parent
PROJECT = OUT.parents[1] / '标注试样' / '25_上海市第十人民医院内科病房综合楼'
sys.path.insert(0, '/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts')
import annotation_tools as at
from shapely.geometry import Point, Polygon

JSON = PROJECT / 'annotation.json'
MD = PROJECT / '标注说明.md'
old = json.loads(JSON.read_text())
old_md = MD.read_text()
data = copy.deepcopy(old)
spaces = {s['id']: s for s in data['spaces']}
answers = {}
rows = []
for line in old_md.splitlines():
    if not re.match(r'^\|\s*\d+\s*\|\s*S\d+', line):
        continue
    cols = [html.unescape(c.strip()) for c in line.split('|')[1:-1]]
    assert len(cols) == 7 and cols[0] == cols[-1]
    rows.append(line)
    if cols[5] not in ('', '待确认', '待填写', '待定'):
        answers[cols[1]] = cols[2] if cols[5] in ('已确认', '确认', '同意') else cols[5]
assert len(rows) == 18 and len(answers) == 17
types = {
    '管井': 'building_services', '化验': 'laboratory', '收费、药房': 'pharmacy',
    '洗镜、储镜': 'sterile_supply', '咖啡水吧台': 'retail_service',
    'TPS工作室': 'office', '储藏': 'storage', '洗片': 'auxiliary_room',
    '贵宾接待': 'staff_support', '衣帽、问询': 'service', '600座多功能教室': 'conference',
}
for sid, name in answers.items():
    assert spaces[sid]['type'] == 'unknown'
    spaces[sid].update(name=name, type=types[name])
    if name == '管井':
        spaces[sid]['scope'] = 'building_support'
spaces['S046']['scope'] = 'public_service'
assert spaces['S069']['type'] == 'unknown'
(OUT / '本轮明确填写.json').write_text(json.dumps(answers, ensure_ascii=False, indent=2) + '\n')

# Upright display coordinates are only a reading aid; core JSON uses original pixels.
def orig(x, y):
    return [round(2472 - y, 2), round(x, 2)]

# Include the visible entrance landing above the west core, excluding outdoor steps.
spaces['S010']['polygon_px'] = [orig(x, y) for x, y in [
    (351.3, 659.05), (418, 659.05), (418, 611.27),
    (538.2, 611.27), (538.2, 800.97), (351.3, 800.97),
]]
relations = {r['id']: r for r in data['relations']}
relations['R008']['target'] = 'S009'
relations['R015']['target'] = 'S013'
relations['R074']['target'] = 'S071'
removed = {'R029', 'R030', 'R043'}
data['relations'] = [r for r in data['relations'] if r['id'] not in removed]
for rid, a, b, typ in [
    ('R128', 'S019', 'S025', 'access'),
    ('R129', 'S020', 'S026', 'access'),
    ('R130', 'S079', 'S080', 'access'),
    ('R131', 'S046', 'S094', 'service'),
]:
    r = dict(id=rid, source=a, target=b, type=typ)
    data['relations'].append(r)
    relations[rid] = r

# Coordinates below were read from this plan, never generated from centroids or walls.
# d = visible door, o = visible open passage / continuous circulation boundary.
locations = {
    'R001': [('d', 538, 553)],
    'R002': [('d', 624, 611)],
    'R003': [('d', 760, 611)],
    'R004': [('d', 673, 611)],
    'R005': [('d', 849, 611)],
    'R006': [('d', 893, 611)],
    'R007': [('d', 982, 611)],
    'R008': [('d', 1131, 587)],
    'R009': [('d', 1131, 630)],
    'R010': [('d', 538, 634)],
    'R011': [('d', 597, 696)],
    'R012': [('d', 597, 755)],
    'R013': [('d', 597, 824)],
    'R014': [('d', 687, 659)],
    'R015': [('d', 711, 779)],
    'R016': [('d', 783, 685)],
    'R017': [('d', 783, 817)],
    'R018': [('d', 867, 712)],
    'R019': [('d', 867, 818)],
    'R020': [('d', 1047, 711)],
    'R021': [('d', 1047, 818)],
    'R022': [('d', 1131, 715)],
    'R023': [('d', 1131, 753)],
    'R024': [('d', 1131, 820)],
    'R025': [('d', 935, 735)],
    'R026': [('d', 978, 735)],
    'R027': [('o', 825, 659)],
    'R028': [('o', 1088, 659)],
    'R031': [('o', 567, 878)],
    'R032': [('o', 825, 878)],
    'R033': [('o', 1088, 878)],
    'R034': [('o', 1265, 878)],
    'R035': [('o', 1131, 905)],
    'R036': [('d', 538, 968)],
    'R037': [('d', 369, 878)],
    'R038': [('d', 339, 930), ('d', 339, 970)],
    'R039': [('d', 1175, 934)],
    'R040': [('d', 1218, 973)],
    'R041': [('d', 1218, 1018)],
    'R042': [('d', 1314, 900)],
    'R044': [('d', 1412, 801)],
    'R045': [('d', 1720, 801), ('d', 1768, 801)],
    'R046': [('d', 1314, 1087), ('d', 1314, 1240)],
    'R048': [('o', 1576, 801)],
    'R049': [('d', 1576, 548)],
    'R050': [('d', 1518, y) for y in (579, 640, 703, 764)],
    'R051': [('d', 1634, y) for y in (579, 640, 703, 764)],
    'R052': [('d', 1810, 801)],
    'R053': [('d', 2089, 611)],
    'R054': [('d', 2139, 611)],
    'R055': [('d', 2260, 611)],
    'R056': [('d', 2309, 611)],
    'R057': [('d', 2430, 611)],
    'R058': [('d', 2485, 611)],
    'R059': [('d', 2597, 548)],
    'R060': [('d', 2122, 658)],
    'R061': [('d', 2185, 658)],
    'R062': [('d', 2272, 658)],
    'R063': [('d', 2298, 658)],
    'R064': [('d', 2473, 658)],
    'R065': [('d', 2542, 694)],
    'R066': [('d', 2542, 770)],
    'R067': [('d', 2542, 835)],
    'R068': [('d', 2597, 769)],
    'R069': [('d', 2380, 715)],
    'R070': [('d', 2430, 715)],
    'R071': [('d', 2164, 878)],
    'R072': [('d', 2340, 878)],
    'R073': [('d', 2410, 878)],
    'R074': [('d', 2708, 815)],
    'R075': [('d', 2732, 878)],
    'R076': [('d', 2799, 943), ('d', 2799, 984)],
    'R077': [('d', 1901, 512), ('d', 1901, 773)],
    'R078': [('o', 1901, 833)],
    'R079': [('o', 1852, 837)],
    'R080': [('d', 2024, 831)],
    'R081': [('d', 2050, 878), ('o', 2570, 878)],
    'R082': [('d', x, 933) for x in (1882, 1939, 1998)],
    'R083': [('d', 1852, 993)],
    'R084': [('o', 2024, 993)],
    'R085': [('o', 2095, 1054)],
    'R086': [('d', 1939, 1178)],
    'R087': [('d', 1948, 1054)],
    'R088': [('d', 2175, 1087)],
    'R089': [('d', 2543, 1087)],
    'R090': [('d', 2564, 1164)],
    'R091': [('d', 2674, 1164)],
    'R092': [('d', 2193, 1164)],
    'R093': [('d', 2355, 1164)],
    'R094': [('o', 2210, 1269), ('o', 2700, 1269)],
    'R095': [('d', 2175, 1293), ('d', 2175, 1620)],
    'R096': [('d', 2252, 1778)],
    'R097': [('d', 2342, 1778)],
    'R098': [('o', 2297, 1778)],
    'R099': [('d', 2458, 1778)],
    'R100': [('d', 2568, 1778)],
    'R101': [('d', 2622, 1778)],
    'R103': [('d', 2615, 1848)],
    'R104': [('d', 2656, 1848)],
    'R105': [('d', 2768, 1848)],
    'R106': [('d', 2297, 1706)],
    'R128': [('d', 935, 801)],
    'R129': [('d', 978, 801)],
    'R130': [('d', 2319, 1146)],
}
next_p = 1
for r in data['relations']:
    if r['id'] not in locations:
        continue
    assert r['type'] == 'access'
    r['openings'] = []
    for kind, x, y in locations[r['id']]:
        r['openings'].append(dict(id=f'P{next_p:03d}',
            kind='door' if kind == 'd' else 'open_passage', position_px=orig(x, y)))
        next_p += 1
for rid, x, y in [('E007', 1286, 548), ('E008', 1876, 548), ('E010', 2737, 1297)]:
    relations[rid]['position_px'] = orig(x, y)
at.normalize(data)
JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

# Render upright labels, while retaining original-pixel marker coordinates for validation.
upright = copy.deepcopy(data)
upright['image'].update(width=3232, height=2472)
for s in upright['spaces']:
    s['polygon_px'] = [[y, 2472-x] for x, y in s['polygon_px']]
for r in upright['relations']:
    if r['type'] == 'entrance':
        x, y = r['position_px']
        r['position_px'] = [y, 2472-x]
    for o in r.get('openings', []):
        x, y = o['position_px']
        o['position_px'] = [y, 2472-x]
at.render(upright, JSON, PROJECT / '标注.svg')
tree = ET.parse(PROJECT / '标注.svg')
root = tree.getroot()
ns = {'s': at.NS}
im = root.find('.//s:image', ns)
im.set('width', '2472')
im.set('height', '3232')
im.set('transform', 'matrix(0 -1 1 0 0 2472)')
original_openings = {o['id']: o for r in data['relations'] for o in r.get('openings', [])}
for e in root.iter():
    oid = e.get('data-opening-id')
    if oid:
        circle = e.find('s:circle', ns)
        x, y = original_openings[oid]['position_px']
        circle.set('cx', str(x))
        circle.set('cy', str(y))
        circle.set('transform', 'matrix(0 -1 1 0 0 2472)')
        label = e.find('s:text', ns)
        for key in ('stroke', 'stroke-width', 'paint-order'):
            label.attrib.pop(key, None)
        lx, ly = float(label.get('x')), float(label.get('y'))
        bg = at.element('rect', {'x': lx-1, 'y': ly-8.5, 'width': 25,
            'height': 10.5, 'rx': 1, 'fill': 'white', 'fill-opacity': '.95'})
        e.insert(list(e).index(label), bg)
    if e.tag == '{'+at.NS+'}text':
        e.set('font-family', 'Hiragino Sans GB, PingFang SC, Microsoft YaHei, sans-serif')
titles = root.findall('s:text', ns)
titles[0].text = '25 上海市第十人民医院内科病房综合楼｜连通复核'
titles[1].text = f'97个空间；1项名称待确认；连通性已复核；{next_p-1}个室内门洞／开口定位点'
tree.write(PROJECT / '标注.svg', encoding='unicode')

at.summary(data, OUT / '复核后概览.md')
summary = (OUT / '复核后概览.md').read_text()
summary = summary.replace('# 平面标注概览', '# 25 上海市第十人民医院内科病房综合楼｜一层标注')
summary = summary.replace('未完成：1 个空间名称尚未确认。',
    '**状态：17项名称填写已同步；人员连通与清晰门洞已复核。仍有1项房名待确认（16／S069），整图暂未完成。**')
scope = html.unescape(old_md.split('**图面范围：**', 1)[1].split('\n\n', 1)[0])
scope = scope.replace('化注候选区', '化验区').replace('制作支持', '制作及储藏支持')
prefix = summary + '\n**图面范围：**' + scope + '\n\n'
review = old_md[old_md.index('## 房名与范围核对（2026-11-05）'):]
review = review.replace('本轮 18 项待确认。沿用历史核对号与当前 S 编号；下列候选来自旧稿，尚未视为本轮确认。',
    '本轮17项明确填写已同步至JSON和SVG；仅16／S069仍为“待确认”。以下18行填写原文、核对号和S编号全部保留；已同步项以“我的确认／备注”中的实际名称为准，旧候选及依据仅作历史记录。')
review = review.replace('`21号 01=名称`', '`25号 01=名称`')
review = review.replace('先核对名称、类别和空间范围；名称确认后，再逐张复核人员连通与可定位门洞。当前五图均无门洞红点，既有关系仍需复核。',
    '25号本轮已复核人员连通与清晰门洞；当前仅16／S069用途待确认，原候选不自动采用。连通记录不代表允许公众进入管井、设备间或办公区域。')
connection_notes = '''## 连通性复核（2026-11-05）

本轮按原图的可见门、无门开口、连续大厅／走廊复核；共墙和柜台服务联系不计入人员通路。97个节点按 access 构图时形成1个连通分量，均可沿已记录室内通路到达至少1个入口。此结论只说明图数据中的概念可达，不表达门禁、开放时段或消防合规。

### 已修正的通路

- R008：控制室 S008 经 X光 S009 进入；移除旧“控制室直接进北侧通道”的解释，门位见对应红点。
- R015：药库 S018 的门开向化验 S013；未见直接通向收费、药房 S024 的门，修正旧连接对象。
- R128、R129：补两间检查室 S019—诊室 S025、S020—诊室 S026 的可见门；各检查室保留原通向另一侧诊室的门。
- R074：衣帽、问询 S070 经管理 S071 进入会议教学中心 S077；原直接接大厅的关系改为 S070—S071。
- R130：补贵宾休息室 S079—茶水 S080 的可见侧门；保留二者各自通向主席台的门。
- 删除 R029（S028—S031，穿过检查房）、R030（S028—S032，仅角点相邻）、R043（S031—S044，实墙分隔）。特诊区通过 S034—S044 的清晰门连接住院大厅。
- 咖啡水吧台 S046 的工作人员入口经电梯厅 S076；柜台对住院大厅 S044、前厅休息厅 S094 仅记 service，不作穿行门洞。
- S010 保持原编号与交通核粒度，将图上可见的北侧入口平台纳入概念边界，保留西侧室外台阶在面积之外；其余空间轮廓不变，室内占比重新归一化。
- E007、E008、E010 的入口定位移至各自图上实际开口附近，入口编号、名称与所接空间保持不变。

### 概念连接与内部细节

两条门斗连接 R047（S047—S044）、R102（S093—S094）按门斗朝向与完整通行布局保留为**布局推断**，暂不编造精确门位；不是用户逐条确认。其他已定位开口均对应原图可见门／无门开口／连续交通区域的分界，P编号仅表示近似位置，不代表门宽或内部路线。

本轮不细究交通核内部的楼梯／电梯切换路线、卫生间隔间、管井与设备内部构造。管井外侧可见检修门保留概念连接及门位，不将其作为公共交通节点。S069 与通道的可见门可单独记录，其用途仍为 unknown。

**关键连通疑点：**本轮未留下会改变主要通行组织的待确认项。**名称遗留：**16／S069仍待填写；可在下面原表确认栏补充名称。完整原图、核对局部和已有填写继续保留。

'''
MD.write_text(prefix + connection_notes + review)
assert all(line in MD.read_text() for line in rows)

# Independent graph and geometric checks, saved outside the four-file sample.
adj = {sid: set() for sid in spaces}
for r in data['relations']:
    if r['type'] == 'access':
        adj[r['source']].add(r['target'])
        adj[r['target']].add(r['source'])
entrance_targets = {r['target'] for r in data['relations'] if r['type'] == 'entrance'}
seen = set(entrance_targets)
queue = deque(seen)
while queue:
    for v in adj[queue.popleft()]:
        if v not in seen:
            seen.add(v)
            queue.append(v)
components = []
remaining = set(spaces)
while remaining:
    seed = min(remaining)
    part = {seed}
    todo = [seed]
    while todo:
        for v in adj[todo.pop()]:
            if v not in part:
                part.add(v)
                todo.append(v)
    remaining -= part
    components.append(sorted(part))
polygons = {s['id']: Polygon(s['polygon_px']) for s in data['spaces']}
distances = []
for r in data['relations']:
    for o in r.get('openings', []):
        p = Point(o['position_px'])
        distances.append(dict(id=o['id'], relation=r['id'],
            source=r['source'], target=r['target'],
            distance_to_source=round(polygons[r['source']].distance(p), 3),
            distance_to_target=round(polygons[r['target']].distance(p), 3)))
audit = dict(spaces=len(spaces), relations=Counter(r['type'] for r in data['relations']),
    openings=next_p-1, located_access=len(locations),
    unlocated_access=[r['id'] for r in data['relations'] if r['type']=='access' and not r.get('openings')],
    components=components, unreachable_from_any_entrance=sorted(set(spaces)-seen),
    opening_distances=distances, pending_names=[s['id'] for s in at.unresolved(data)],
    original_sha256=hashlib.sha256((PROJECT / data['image']['file']).read_bytes()).hexdigest())
(OUT / '连通与门位审计.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({k:v for k,v in audit.items() if k not in ('components','opening_distances')}, ensure_ascii=False, indent=2))
print('component_sizes', [len(c) for c in components])
print('distant_openings', [d for d in distances if max(d['distance_to_source'],d['distance_to_target']) > 8])
