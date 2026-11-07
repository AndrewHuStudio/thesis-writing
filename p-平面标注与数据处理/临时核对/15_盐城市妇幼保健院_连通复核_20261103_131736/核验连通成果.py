from pathlib import Path
from collections import defaultdict
import hashlib
import html
import importlib.util
import json
import re
import xml.etree.ElementTree as ET
from shapely.geometry import Point, Polygon

R = Path(__file__).resolve().parent
P = R / '待核验成果'
B = R / '修改前备份'
final = R.parent.parent / '标注试样/15_盐城市妇幼保健院'
old = json.loads((B / 'annotation.json').read_text())
data = json.loads((P / 'annotation.json').read_text())
assert data['spaces'] == old['spaces'] and data['image'] == old['image']
assert (P / data['image']['file']).read_bytes() == (B / data['image']['file']).read_bytes()
shared = lambda d: [r for r in d['relations'] if r['type'] == 'shared_wall']
assert shared(old) == shared(data)
ss = {s['id']: s for s in data['spaces']}
polys = {i: Polygon(s['polygon_px']) for i, s in ss.items()}
svg = ET.parse(P / '标注.svg')
groups = {e.get('id'): e for e in svg.iter() if e.get('data-space-name') is not None}
assert set(groups) == set(ss)
for sid, s in ss.items():
    g = groups[sid]
    assert (g.get('data-space-name'), g.get('data-space-type')) == (s['name'], s['type'])
    visible = ''.join(e.text or '' for e in g if e.tag.endswith('}text'))
    assert sid in visible and s['name'] in visible

def rows(text):
    result = []
    for line in html.unescape(text).splitlines():
        c = [v.strip() for v in line.strip().strip('|').split('|')]
        if len(c) == 7 and re.fullmatch(r'S\d+', c[1]):
            result.append(c)
    return result

md = (P / '标注说明.md').read_text()
assert rows(md) == rows((B / '标注说明.md').read_text())
assert len(rows(md)) == 336
images = re.findall(r'!\[[^\]]*\]\(([^)]+)\)', md)
assert all((final / link).resolve().is_file() for link in images)
record = json.loads((R / '复核记录.json').read_text())
oldaccess = {tuple(sorted([r['source'], r['target']])): r for r in old['relations'] if r['type']=='access'}
seen = set()
adj = defaultdict(set)
located = 0
for rel in data['relations']:
    if rel['type'] != 'access':
        continue
    a, b = rel['source'], rel['target']
    assert ss[a]['type'] not in {'landscape', 'courtyard'}
    assert ss[b]['type'] not in {'landscape', 'courtyard'}
    assert polys[a].distance(polys[b]) <= 2
    key = tuple(sorted([a, b]))
    if key in oldaccess:
        assert rel['id'] == oldaccess[key]['id']
    adj[a].add(b); adj[b].add(a)
    for mark in rel.get('openings', []):
        point = Point(mark['position_px'])
        assert all(polys[i].boundary.distance(point) <= 4 for i in (a,b))
        assert mark['id'] not in seen
        seen.add(mark['id']); located += 1
assert located == 420
unlocated = {r['id'] for r in data['relations'] if r['type']=='access' and not r.get('openings')}
assert unlocated == {r['relation'] for r in record['concepts']}
components = []
todo = set(adj)
while todo:
    start = min(todo); stack=[start]; component=set()
    while stack:
        sid = stack.pop()
        if sid in component:
            continue
        component.add(sid); stack.extend(adj[sid]-component)
    todo -= component
    components.append(sorted(component))
interfaces = {r['target'] for r in data['relations'] if r['type']=='entrance'}
assert all(set(c) & interfaces for c in components), [c for c in components if not set(c)&interfaces]
spec = importlib.util.spec_from_file_location('annotation_tools',
    '/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts/annotation_tools.py')
at = importlib.util.module_from_spec(spec); spec.loader.exec_module(at)
validation, code = at.check(data, P / 'annotation.json', check_dir=True)
assert code == 0, validation
result = {'formal_validation': validation, 'spaces_and_names_and_area_unchanged': True,
    'source_image_unchanged': True, 'all_336_review_rows_preserved': True,
    'svg_visible_names_match': True, 'opening_count': located,
    'opening_boundary_errors': [], 'concept_access_documented': len(unlocated),
    'indoor_components_with_external_interfaces': [len(c) for c in components],
    'no_access_to_landscape_or_void': True, 'embedded_images_valid': len(images),
    'visual_review': '17片区开口叠图、SVG全图及6处密集局部已目检；不确定门位改为概念连接',
    'scope': '概念精度；4处小设备／辅助空间内部出入不细究',
    'critical_pending_questions': 0}
(R / '最终核验结果.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
print(json.dumps(result, ensure_ascii=False, indent=2))
