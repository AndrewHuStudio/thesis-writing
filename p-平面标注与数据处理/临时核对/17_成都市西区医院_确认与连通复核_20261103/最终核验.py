from pathlib import Path
from collections import Counter, deque
import hashlib
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

import pymupdf
from PIL import Image
from shapely.geometry import Polygon, Point, box


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SAMPLE = ROOT / 'p-平面标注与数据处理/标注试样/17_成都市西区医院'
BACKUP = next(OUT.glob('修改前备份_*'))
data = json.loads((SAMPLE / 'annotation.json').read_text())
old = json.loads((BACKUP / 'annotation.json').read_text())
assert set(data) == {'image', 'spaces', 'relations'}
assert [s['id'] for s in data['spaces']] == [s['id'] for s in old['spaces']]
assert len(data['spaces']) == 49
assert not any(s['type'] == 'unknown' for s in data['spaces'])
assert {p.name for p in SAMPLE.iterdir()} == {data['image']['file'], 'annotation.json', '标注.svg', '标注说明.md'}
source = SAMPLE / data['image']['file']
assert source.read_bytes() == (BACKUP / source.name).read_bytes()
assert (OUT / '用户确认原文.md').read_bytes() == (BACKUP / '标注说明.md').read_bytes()
expected = {'S001': '管井', 'S004': '汇流排间', 'S012': '值班',
            'S013': '值班', 'S018': '清创室', 'S021': '内科'}
for sid, name in expected.items():
    assert next(s for s in data['spaces'] if s['id'] == sid)['name'] == name
assert [s['id'] for s in data['spaces'] if s['polygon_px'] != next(b for b in old['spaces'] if b['id'] == s['id'])['polygon_px']] == ['S028', 'S030']

ns = {'s': 'http://www.w3.org/2000/svg'}
svg = ET.parse(SAMPLE / '标注.svg').getroot()
polygons = {s['id']: Polygon(s['polygon_px']) for s in data['spaces']}
labels = {}
for s in data['spaces']:
    g = svg.find(f'.//s:g[@id="{s["id"]}"]', ns)
    assert g is not None and g.get('data-space-name') == s['name'] and g.get('data-space-type') == s['type']
    text = ''.join(e.text or '' for e in g.findall('s:text', ns))
    assert s['id'] in text and s['name'] in text
    r = g.find('s:rect', ns)
    x, y, w, h = [float(r.get(k)) for k in ['x', 'y', 'width', 'height']]
    labels[s['id']] = box(x, y, x+w, y+h)
for r in data['relations']:
    if r['type'] == 'entrance':
        g = svg.find(f'.//s:g[@id="{r["id"]}"]', ns)
        rect = g.find('s:rect', ns)
        x, y, w, h = [float(rect.get(k)) for k in ['x', 'y', 'width', 'height']]
        labels[r['id']] = box(x, y, x+w, y+h)

opening_ids = set()
clashes = []
for r in data['relations']:
    for o in r.get('openings', []):
        assert o['id'] not in opening_ids
        opening_ids.add(o['id'])
        g = svg.find(f'.//s:g[@id="{o["id"]}"]', ns)
        assert g is not None
        assert [g.get('data-source'), g.get('data-target'), g.get('data-relation-id')] == [r['source'], r['target'], r['id']]
        assert max(Point(o['position_px']).distance(polygons[r[k]]) for k in ['source', 'target']) < 30
        rect = g.find('s:rect', ns)
        x, y, w, h = [float(rect.get(k)) for k in ['x', 'y', 'width', 'height']]
        pbox = box(x, y, x+w, y+h)
        for sid, label in labels.items():
            if pbox.intersection(label).area > 1:
                clashes.append([o['id'], sid])
assert not clashes, clashes
assert len(opening_ids) == 47
graph = {s['id']: set() for s in data['spaces']}
for r in data['relations']:
    if r['type'] == 'access':
        graph[r['source']].add(r['target'])
        graph[r['target']].add(r['source'])
reached = {r['target'] for r in data['relations'] if r['type'] == 'entrance'}
q = deque(reached)
while q:
    for sid in graph[q.popleft()]:
        if sid not in reached:
            reached.add(sid)
            q.append(sid)
assert set(graph) - reached == {'S001'}

md = (SAMPLE / '标注说明.md').read_text()
links = re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', md)
assert all((SAMPLE / link).exists() for link in links)
assert len(re.findall(r'^\| 0[1-6] \| S\d+', md, re.M)) == 6
result = subprocess.run([sys.executable, '/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts/annotation_tools.py',
                         'validate', str(SAMPLE / 'annotation.json'), '--check-dir'], capture_output=True, text=True)
validation = json.loads(result.stdout)
assert result.returncode == 0 and validation['valid'] and validation['names_complete'] and not validation['errors']
(OUT / '正式校验.json').write_text(json.dumps({'exit_code': result.returncode, **validation}, ensure_ascii=False, indent=2)+'\n')
report = {'source_unchanged': True, 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'original_answers_preserved': True, 'stable_space_ids': 49, 'fixed_review_mapping_preserved': 6,
          'relation_types': Counter(r['type'] for r in data['relations']), 'openings': 47,
          'opening_types': Counter(o['kind'] for r in data['relations'] for o in r.get('openings', [])),
          'located_access_relations': sum(bool(r.get('openings')) for r in data['relations'] if r['type'] == 'access'),
          'conceptual_access_relations': sum(not r.get('openings') for r in data['relations'] if r['type'] == 'access'),
          'opening_label_room_label_clashes': clashes, 'reachable_spaces': len(reached),
          'non_pedestrian_isolated': ['S001'], 'indoor_area_ratio_sum': sum(s.get('area_ratio', 0) for s in data['spaces']),
          'links_checked': len(links), 'key_pending_questions': 0, 'validation': validation}
(OUT / '最终核验.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
page = pymupdf.open(SAMPLE / '标注.svg')[0]
page.get_pixmap(matrix=pymupdf.Matrix(1, 1)).save(OUT / '最终SVG_全图.png')
im = Image.open(OUT / '最终SVG_全图.png')
im.thumbnail((1222, 1800))
im.save(OUT / '最终SVG_全图预览.jpg')
for name, bounds in [('西北', (225, 880, 950, 1320)), ('东北', (915, 880, 1740, 1320)),
                     ('值班', (565, 1470, 900, 1750)), ('急诊', (920, 1240, 1725, 1850)),
                     ('交通核', (590, 1780, 1420, 2370)), ('南部', (225, 2260, 1775, 2820))]:
    page.get_pixmap(matrix=pymupdf.Matrix(2, 2), clip=pymupdf.Rect(bounds)).save(OUT / ('最终SVG_'+name+'.png'))
print(json.dumps(report, ensure_ascii=False, indent=2))
