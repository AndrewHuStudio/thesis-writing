import json, re, hashlib
from pathlib import Path
import xml.etree.ElementTree as ET
import fitz

root = Path('/Users/hushili/Documents/研究-论文写作/大论文')
w = Path('/tmp/outpatient13_sync_workdir').read_text()
w = Path(w)
p = w/'待核验成果'
final = root/'p-平面标注与数据处理/标注试样/13_天津市中心妇产科医院迁址新建工程'
a = json.loads((w/'修改前备份'/'annotation.json').read_text())
b = json.loads((p/'annotation.json').read_text())
assert a['image'] == b['image'] and a['relations'] == b['relations']
changed = []
for old, new in zip(a['spaces'], b['spaces']):
    assert old['id'] == new['id']
    for k in set(old)-{'name','type'}:
        assert old[k] == new[k], (new['id'],k)
    if old != new:changed.append(new['id'])
assert len(changed) == 19
assert (w/'修改前备份'/b['image']['file']).read_bytes() == (p/b['image']['file']).read_bytes()

def rows(md):
    result = {}
    for line in md.splitlines():
        c = [s.strip() for s in line.strip().strip('|').split('|')]
        if len(c) == 8 and re.fullmatch(r'\d{2}', c[0]):
            assert c[0] == c[-1]
            assert c[0] not in result
            result[c[0]] = c
    return result
oldrows = rows((w/'修改前备份'/'标注说明.md').read_text())
md = (p/'标注说明.md').read_text()
newrows = rows(md)
assert len(oldrows) == len(newrows) == 66
for n, row in oldrows.items():
    other = newrows[n]
    assert row[:6] == other[:6] and row[-1] == other[-1]
    assert row[6] in other[6], (n, row[6], other[6])
links = re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', md)
missing = [link for link in links if not (final/link).exists() and not link.startswith('http')]
assert not missing, missing
ns = {'s':'http://www.w3.org/2000/svg'}
svg = ET.parse(p/'标注.svg')
types = json.loads(Path('/Users/hushili/.codex/skills/outpatient-plan-annotation/references/space-types.json').read_text())
for space in b['spaces']:
    group = svg.find('.//s:g[@id="'+space['id']+'"]',ns)
    assert group is not None
    assert group.get('data-space-name') == space['name']
    assert group.get('data-space-type') == space['type']
    visible = ''.join(e.text or '' for e in group.findall('s:text',ns))
    assert space['id'] in visible and space['name'] in visible
    if space['type'] != 'unknown':
        assert types[space['type']] in visible, (space['id'],visible)
report = {
    'changed_name_type_ids': changed,
    'stable_geometry_area_scope_levels': True,
    'stable_relations': True,
    'source_bytes_unchanged': True,
    'all_66_mappings_and_user_answers_preserved': True,
    'md_links_checked': len(links),
    'missing_links': missing,
    'svg_visible_labels_match': True,
    'pending_name_ids': [s['id'] for s in b['spaces'] if s['type']=='unknown'],
}
(w/'同步一致性核验.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
doc=fitz.open(p/'标注.svg')
page=doc[0]
page.get_pixmap(matrix=fitz.Matrix(.7,.7)).save(w/'同步后整图.png')
for title, box in [
    ('放射科与药房', (310,800,1330,1810)),
    ('急诊', (350,1640,945,2070)),
    ('门诊西段', (1610,1280,2060,1910)),
    ('门诊东段', (1650,2230,2060,2980)),
]:
    page.get_pixmap(matrix=fitz.Matrix(1.8,1.8),clip=fitz.Rect(box)).save(w/(title+'.png'))
print(json.dumps(report,ensure_ascii=False,indent=2))
