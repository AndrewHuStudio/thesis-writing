from pathlib import Path
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon
from shapely.ops import unary_union
import pymupdf

R = Path(__file__).resolve().parent
P = R / '待核验成果'
B = R / '修改前备份'
old = json.loads((B / 'annotation.json').read_text())
data = json.loads((P / 'annotation.json').read_text())
before = {s['id']: s for s in old['spaces']}
spaces = {s['id']: s for s in data['spaces']}
record = json.loads((R / '同步记录.json').read_text())
assert set(before) - set(spaces) == set(record['merged_ids'])
assert data['image'] == old['image']
source = data['image']['file']
assert (P / source).read_bytes() == (B / source).read_bytes()
assert unary_union([Polygon(s['polygon_px']) for s in old['spaces']]).symmetric_difference(
    unary_union([Polygon(s['polygon_px']) for s in data['spaces']])).area == 0
changed_shapes = {'S018', 'S019', 'S069', 'S070', 'S367', 'S400', 'S402', 'S415'}
for sid, s in spaces.items():
    if sid not in changed_shapes:
        assert s['polygon_px'] == before[sid]['polygon_px']
    if sid not in record['direct_names'] and sid not in changed_shapes:
        assert (s['name'], s['type'], s['level'], s['scope']) == (
            before[sid]['name'], before[sid]['type'], before[sid]['level'], before[sid]['scope'])

def rows(text):
    result = []
    for line in text.splitlines():
        cells = [v.strip() for v in line.strip().strip('|').split('|')]
        if len(cells) == 7 and re.fullmatch(r'S\d+', cells[1]):
            result.append(cells)
    return result

md = (P / '标注说明.md').read_text()
oldrows = rows((B / '标注说明.md').read_text())
newrows = rows(md)
assert len(oldrows) == len(newrows) == 336
assert [(r[0], r[1], r[5], r[6]) for r in oldrows] == [(r[0], r[1], r[5], r[6]) for r in newrows]
for link in re.findall(r'!\[[^\]]*\]\(([^)]+)\)', md):
    # Staged directory has a different depth; resolve final-sample relative links.
    final_sample = R.parent.parent / '标注试样/15_盐城市妇幼保健院'
    assert (final_sample / link).resolve().is_file(), link
assert abs(sum(s.get('area_ratio', 0) for s in spaces.values()) - 1) < 1e-6
assert 'area_ratio' not in spaces['S274']
svg = ET.parse(P / '标注.svg')
groups = {g.get('id'): g for g in svg.iter() if g.get('data-space-name') is not None}
assert set(groups) == set(spaces)
for sid, s in spaces.items():
    g = groups[sid]
    assert g.get('data-space-name') == s['name'] and g.get('data-space-type') == s['type']
    text = ''.join(e.text or '' for e in g if e.tag.endswith('}text'))
    assert sid in text and s['name'] in text, (sid, text)

result = {'source_unchanged': True, 'review_rows_and_answers_preserved': 336,
    'total_coverage_unchanged': True, 'unrelated_shapes_preserved': True,
    'visible_svg_labels_match': True, 'spaces': len(spaces),
    'relations': len(data['relations']), 'remaining_name_ids': record['remaining'],
    'area_ratio_sum': sum(s.get('area_ratio', 0) for s in spaces.values())}
(R / '增量核验结果.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(result, ensure_ascii=False, indent=2))
