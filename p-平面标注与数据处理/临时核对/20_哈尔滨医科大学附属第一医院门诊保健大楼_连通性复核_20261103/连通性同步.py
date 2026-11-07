from pathlib import Path
from collections import Counter, defaultdict
import copy
import importlib.util
import json
import xml.etree.ElementTree as ET

from shapely.geometry import Point, Polygon
import 开口与关系判读 as C

OUT = Path(__file__).resolve().parent
PROJECT = OUT.parents[2] / 'p-平面标注与数据处理/标注试样/20_哈尔滨医科大学附属第一医院门诊保健大楼'
PHOTOS = OUT.parent / '20_哈尔滨医科大学附属第一医院门诊保健大楼_照片补充_20261103'
SPEC = importlib.util.spec_from_file_location('annotation_tools', '/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts/annotation_tools.py')
H = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(H)


def original_position(uv):
    u, v = uv
    return [2444 - v, u]


def build():
    data = json.loads((OUT / '名称范围落实.json').read_text())
    result = []
    evidence = []
    counter = 0
    for relation in data['relations']:
        r = copy.deepcopy(relation)
        rid = r['id']
        if rid in C.REMOVE:
            evidence.append(dict(id=rid, action='removed', reason=C.REMOVE[rid]))
            continue
        if rid in C.REASSIGN:
            r['source'], r['target'] = C.REASSIGN[rid]
        if rid in C.SERVICE:
            r['type'] = 'service'
            evidence.append(dict(id=rid, action='service', reason=C.SERVICE[rid]))
        elif r['type'] == 'access':
            evidence.append(dict(id=rid, action='door' if rid in C.DOORS else 'concept', reason=C.CONCEPT.get(rid, '本图原图和用户照片可见清晰门洞，逐点目检')))
            assert rid in C.DOORS or rid in C.CONCEPT, rid
        if rid in C.DOORS:
            r['openings'] = []
            for uv in C.DOORS[rid]:
                counter += 1
                r['openings'].append(dict(id=f'P{counter:03d}', kind='door', position_px=original_position(uv)))
        result.append(r)
    for rid, source, target, typ, points, reason in C.NEW:
        r = dict(id=rid, source=source, target=target, type=typ)
        if points:
            r['openings'] = []
            for uv in points:
                counter += 1
                r['openings'].append(dict(id=f'P{counter:03d}', kind='door', position_px=original_position(uv)))
        result.append(r)
        evidence.append(dict(id=rid, action='new_' + typ, reason=reason))
    for entrance in C.ENTRANCES:
        r = dict(entrance)
        r['position_px'] = original_position(r.pop('position_rotated'))
        result.append(r)
    data['relations'] = result
    H.normalize(data)
    check, code = H.check(data, PROJECT / 'annotation.json')
    (OUT / '写入前结构校验.json').write_text(json.dumps(check, ensure_ascii=False, indent=2) + '\n')
    assert code == 0, check
    (OUT / '连通性拟定数据.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    (OUT / '逐关系复核依据.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
    return data


def render(data, output):
    display = copy.deepcopy(data)
    display['image'] = dict(file='原图转正.png', width=3260, height=2444)
    for s in display['spaces']:
        s['polygon_px'] = [[y, 2444-x] for x, y in s['polygon_px']]
    for r in display['relations']:
        if 'position_px' in r:
            x, y = r['position_px']; r['position_px'] = [y, 2444-x]
        for opening in r.get('openings', []):
            x, y = opening['position_px']; opening['position_px'] = [y, 2444-x]
    H.render(display, PHOTOS / '显示数据.json', output)
    tree = ET.parse(output)
    root = tree.getroot()
    root.set('data-source-coordinate-system', 'original-image-2444x3260')
    root.set('data-display-transform', 'x_display=y_original;y_display=2444-x_original')
    openings = {o['id']: o for r in data['relations'] for o in r.get('openings', [])}
    ns = '{http://www.w3.org/2000/svg}'
    for group in root.iter(ns + 'g'):
        oid = group.get('data-opening-id')
        if not oid:
            continue
        point = openings[oid]['position_px']
        circle = group.find(ns + 'circle')
        # 子circle保留JSON原坐标；绘制变换单独旋转，校验与显示均可回查。
        circle.set('cx', str(point[0])); circle.set('cy', str(point[1]))
        circle.set('transform', 'matrix(0 -1 1 0 0 2444)')
        label = group.find(ns + 'text')
        for attribute in ['stroke', 'stroke-width', 'paint-order']:
            label.attrib.pop(attribute, None)
        label.set('fill', '#991b1b')
        label.set('font-size', '8.5')
        x, y = float(label.get('x')), float(label.get('y'))
        if oid in ['P044', 'P049', 'P065']:
            y -= 17
            label.set('y', str(y))
        backdrop = ET.Element(ns + 'rect', {
            'x': str(x-1), 'y': str(y-8), 'width': '23', 'height': '10',
            'fill': '#ffffff', 'opacity': '0.92', 'rx': '1',
        })
        group.insert(list(group).index(label), backdrop)
    entrance = next(g for g in root.iter(ns + 'g') if g.get('id') == 'E09')
    entrance.find(ns + 'rect').set('x', '2870')
    entrance.find(ns + 'text').set('x', '2877')
    entrance.find(ns + 'line').set('x2', '2970')
    root[1].text = '20号｜哈尔滨医科大学附属第一医院门诊保健大楼'
    tree.write(output, encoding='unicode')


def audit(data):
    polygons = {s['id']: Polygon(s['polygon_px']) for s in data['spaces']}
    distances = []
    graph = defaultdict(set)
    for r in data['relations']:
        if r['type'] == 'access':
            graph[r['source']].add(r['target']); graph[r['target']].add(r['source'])
        for opening in r.get('openings', []):
            p = Point(opening['position_px'])
            ds = [polygons[r['source']].distance(p), polygons[r['target']].distance(p)]
            distances.append(dict(opening=opening['id'], relation=r['id'], source=r['source'], target=r['target'], position_px=opening['position_px'], polygon_distances=[round(d, 2) for d in ds]))
    (OUT / '开口与空间定位核验.json').write_text(json.dumps(distances, ensure_ascii=False, indent=2) + '\n')
    isolated = [dict(id=s['id'], name=s['name'], type=s['type']) for s in data['spaces'] if not graph[s['id']]]
    print('RELATIONS', dict(Counter(r['type'] for r in data['relations'])), 'OPENINGS', len(distances))
    print('ISOLATED', isolated)
    print('POINT_DISTANCE_OVER_15', [x for x in distances if max(x['polygon_distances']) > 15])


if __name__ == '__main__':
    data = build()
    render(data, OUT / '连通性复核预览.svg')
    audit(data)
