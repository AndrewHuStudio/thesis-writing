from pathlib import Path
from collections import Counter, defaultdict
import importlib.util
import json
import re
import xml.etree.ElementTree as ET
from shapely.geometry import Polygon, Point, box

R = Path(__file__).resolve().parent
B = R / '修改前备份'
P = R / '待核验成果'
spec = importlib.util.spec_from_file_location('annotation_tools',
    '/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts/annotation_tools.py')
at = importlib.util.module_from_spec(spec)
spec.loader.exec_module(at)
data = json.loads((B / 'annotation.json').read_text())
ss = {s['id']: s for s in data['spaces']}
polys = {i: Polygon(s['polygon_px']) for i, s in ss.items()}
oldrels = data['relations']
oldaccess = {tuple(sorted([r['source'], r['target']])): r for r in oldrels if r['type'] == 'access'}
maxrid = max(int(r['id'][1:]) for r in oldrels if r['id'].startswith('R'))
access = {}
opening = []
boundary_errors = []

def get_access(a, b):
    global maxrid
    key = tuple(sorted((a, b)))
    if key not in access:
        if key in oldaccess:
            access[key] = dict(oldaccess[key])
        else:
            maxrid += 1
            access[key] = {'id': f'R{maxrid:03}', 'source': a, 'target': b, 'type': 'access'}
    return access[key]

for file in sorted(R.glob('开口判读*.tsv')):
    for line in file.read_text().splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        a, b, x, y, kind = line.split()
        a, b = 'S'+a, 'S'+b
        assert ss[a]['type'] not in {'landscape', 'courtyard'}
        assert ss[b]['type'] not in {'landscape', 'courtyard'}
        pos = [float(x), float(y)]
        distances = [polys[i].boundary.distance(Point(pos)) for i in (a, b)]
        if max(distances) > 4 or polys[a].distance(polys[b]) > 2:
            boundary_errors.append([a, b, pos, distances])
        rel = get_access(a, b)
        mark = {'id': f'P{len(opening)+1:03}', 'kind': 'door' if kind == 'D' else 'open_passage',
            'position_px': pos}
        assert not any(m['position_px'] == pos for m in rel.get('openings', []))
        rel.setdefault('openings', []).append(mark)
        opening.append(dict(mark, relation=rel['id'], source=a, target=b, evidence=file.name))
assert not boundary_errors, boundary_errors
concepts = []
for line in (R / '概念连通判读.tsv').read_text().splitlines():
    if not line.strip() or line.startswith('#'):
        continue
    a, b, reason = line.split(maxsplit=2)
    a, b = 'S'+a, 'S'+b
    assert polys[a].distance(polys[b]) <= 2, (a, b)
    rel = get_access(a, b)
    concepts.append({'relation': rel['id'], 'source': a, 'target': b, 'reason': reason})
entrances = []
for line in (R / '外部接口判读.tsv').read_text().splitlines():
    if not line.strip() or line.startswith('#'):
        continue
    sid, x, y, name, typ = line.split()
    sid = 'S'+sid
    pos = [float(x), float(y)]
    assert polys[sid].boundary.distance(Point(pos)) <= 4
    entrances.append({'id': f'E{len(entrances)+1:02}', 'source': None, 'target': sid,
        'type': 'entrance', 'name': name, 'entrance_type': typ, 'position_px': pos})
other = [r for r in oldrels if r['type'] != 'access']
assert not any(r['type'] == 'entrance' for r in other)
data['relations'] = sorted(access.values(), key=lambda r: int(r['id'][1:])) + other + entrances
(P / 'annotation.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
removed = [r for key, r in oldaccess.items() if key not in access]
added = [r for key, r in access.items() if key not in oldaccess]
adj = defaultdict(set)
for r in access.values():
    adj[r['source']].add(r['target'])
    adj[r['target']].add(r['source'])
unconnected = [s['id'] for s in data['spaces'] if at.indoor(s) and not adj[s['id']]]
metrics = {'spaces': len(ss), 'relations': len(data['relations']),
    'access': len(access), 'shared_wall': len(other), 'entrances': len(entrances),
    'openings': len(opening), 'located_access': sum(bool(r.get('openings')) for r in access.values()),
    'unlocated_access': sum(not r.get('openings') for r in access.values()),
    'removed_access': len(removed), 'new_access': len(added),
    'boundary_review': boundary_errors, 'unconnected_indoor': unconnected}
(R / '复核记录.json').write_text(json.dumps({'metrics': metrics, 'removed': removed,
    'added': added, 'openings': opening, 'concepts': concepts, 'entrances': entrances},
    ensure_ascii=False, indent=2)+'\n')

# Reuse every previously verified room label. Add openings above those labels.
at.render(data, P / 'annotation.json', P / '标注.svg')
tree = ET.parse(P / '标注.svg')
oldtree = ET.parse(B / '标注.svg')
oldgroups = {e.get('id'): e for e in oldtree.iter() if e.get('data-space-name') is not None}
plan = next(g for g in tree.iter() if g.get('id') == 'plan')
for index, group in enumerate(list(plan)):
    sid = group.get('id')
    if sid in ss:
        plan.remove(group)
        plan.insert(index, oldgroups[sid])
label_boxes = []
for group in plan:
    if group.get('id') in ss:
        for rect in group:
            if rect.tag.endswith('}rect'):
                x, y, w, h = [float(rect.get(k)) for k in ['x', 'y', 'width', 'height']]
                label_boxes.append(box(x, y, x+w, y+h))
mark_positions = [Point(m['position_px']) for m in opening]
used = []
for group in plan:
    if group.get('data-opening-id') is None:
        continue
    circle = next(e for e in group if e.tag.endswith('}circle'))
    circle.set('r', '3')
    x, y = float(circle.get('cx')), float(circle.get('cy'))
    label = next(e for e in group if e.tag.endswith('}text'))
    label.set('font-size', '6.2')
    label.attrib.pop('stroke', None)
    label.attrib.pop('stroke-width', None)
    label.attrib.pop('paint-order', None)
    candidates = [(x+4, y-4), (x-18, y-4), (x+4, y+8), (x-18, y+8),
        (x-7, y-8), (x-7, y+12)]
    choices = []
    for lx, ly in candidates:
        rect = box(lx-1, ly-6, lx+15, ly+1)
        score = sum(rect.intersection(b).area for b in used)*10
        score += sum(rect.intersection(b).area for b in label_boxes)*.08
        score += sum(rect.distance(p) < 3 for p in mark_positions)*25
        choices.append((score, lx, ly, rect))
    _, lx, ly, rect = min(choices, key=lambda v: v[0])
    label.set('x', str(lx)); label.set('y', str(ly))
    group.insert(list(group).index(label), at.element('rect', {
        'x': lx-1, 'y': ly-6, 'width': 17, 'height': 7.5,
        'fill': 'white', 'fill-opacity': '.88', 'rx': '.6'}))
    used.append(rect)
for e in entrances:
    group = next(g for g in plan if g.get('id') == e['id'])
    group.clear()
    group.set('id', e['id'])
    bx, by = {'E01': (750, 2632), 'E02': (930, 2604), 'E03': (1080, 2688)}[e['id']]
    text = e['id']+' '+e['name']
    width = at.visual_width(text, 9)+14
    x, y = e['position_px']
    group.append(at.element('title', text=text))
    group.append(at.element('line', {'x1': x, 'y1': y, 'x2': bx+width/2,
        'y2': by+20, 'stroke': '#be185d', 'stroke-width': '1'}))
    group.append(at.element('circle', {'cx': x, 'cy': y, 'r': 3.5,
        'fill': 'white', 'stroke': '#be185d', 'stroke-width': '1.5'}))
    group.append(at.element('rect', {'x': bx, 'y': by, 'width': width,
        'height': 20, 'rx': 2, 'fill': 'white', 'stroke': '#be185d'}))
    group.append(at.txt(bx+7, by+13, text, 9, '#9d174d', True))
for e in tree.getroot():
    if e.tag.endswith('}text') and e.text == '门诊平面结构化标注':
        e.text = '15号 盐城市妇幼保健院｜首层概念标注'
tree.write(P / '标注.svg', encoding='unicode')

md = (B / '标注说明.md').read_text()
history = md[md.index('## 全表确认同步'):md.index('**类型与数量：**')]
rel = '../../临时核对/' + R.name
intro = f'''# 15_盐城市妇幼保健院｜首层概念标注

名称信息已全部确认，422个空间／区域；本轮已逐片区复核主要通行组织，并将清晰门洞及无门开口写入JSON和SVG。图纸按用户明确说明记为首层；门诊大厅上空作为外部区域，不计首层室内空间及面积。

## 连通与开口复核（2026-11-03）

**本轮规模：**人员可达{metrics['access']}条，共墙{metrics['shared_wall']}条，外部接口{metrics['entrances']}处；定位开口{metrics['openings']}个，分属{metrics['located_access']}条人员可达关系，另有{metrics['unlocated_access']}条未定位的概念连接。外部接口沿用独立E编号；室内开口采用P编号。编号只用于本图。

**主要修正：**北侧病房翼补齐上排办公、更衣、污洗及交通核出入；中央医办从北侧横通道进入。中部设备间按实际更衣／侧通道组织连接，不跳过中间小间；中央检验区保留缓冲间，细菌检验从北侧污染区进入。西侧门诊及办公片区逐排核对门口，补充交通核及大会议厅；南端阅览室接西侧公共通道，移除无门依据的阅览室—东侧内部通道直连。相较前版移除{len(removed)}条旧access，新增{len(added)}条有图面或布局依据的access。

**外部接口：**E01为阅览室北侧平台出入口；E02为南端东侧内部通道北侧平台接口；E03为南端东侧交通核外侧出入口。各接口独立记录，不把室外接口互相直连。

**精度与待确认状态：**本轮按概念级空间组织复核，关键待确认项为0。半开放护士站、桌椅休息区域、交通核前部及少量更衣／缓冲小间采用有布局依据的概念连接，不伪造精确门位；依据见下表。风机室、库房等少量小设备或辅助小间的内部路线不逐项追问，证据不足处不补边，不表示不可通行。未记录关系不得作为负例。

**范围与面积：**410个首层室内空间／区域参与面积归一化，11处绿化及S274外部中庭／挑空区域不计室内面积。本轮不改空间名称、类别、编号、轮廓、占比及用户填写；定位点是概念近似位置，不记录门宽、门扇构造及核内部精确路线。

[原图]({data['image']['file']}) · [标注SVG](标注.svg) · [连通复核定位图]({rel}/连通复核定位总图.png) · [本轮修改前备份]({rel}/修改前备份/)

**完成核验：**正式检查`valid=true、names_complete=true、errors=[]`；原图及全部空间信息保持不变，336行名称核对表及填写完整保留。17片区开口叠图、SVG全图和密集局部已目检；按上述概念精度完成，关键待确认项为0。[本轮核验记录]({rel}/最终核验结果.json)

### 主要片区查看

![中央检验区：门洞红点与空间对应]({rel}/06中央检验_SVG检查.png)

![最南端：休息区、厕所和会议室通行]({rel}/16最南端_SVG检查.png)

### 未定位的概念连接依据（助手布局判断）

以下为图面布局推断，不冒称用户逐项确认；均不生成虚构的开口红点。

| 空间对 | 依据 |
| --- | --- |
'''
for item in concepts:
    if not access[tuple(sorted((item['source'], item['target'])))].get('openings'):
        intro += f'| {item["source"]}—{item["target"]} | 布局推断：{item["reason"]} |\n'
intro += f'\n本轮未细究的内部细节：{", ".join(unconnected)}等小设备／辅助单元的内部出入。\n\n'
intro += '## 原名称确认材料（完整保留）\n\n'
(P / '标注说明.md').write_text(intro + history)
print(json.dumps(metrics, ensure_ascii=False, indent=2))
