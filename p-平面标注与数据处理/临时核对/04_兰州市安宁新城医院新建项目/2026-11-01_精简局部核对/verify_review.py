from pathlib import Path
from collections import Counter
import hashlib
import json
import re
import xml.etree.ElementTree as ET

import markdown
import pymupdf


OUT = Path(__file__).resolve().parent
PROJECT = OUT.parents[2] / '标注试样/04_兰州市安宁新城医院新建项目'
BACKUP = OUT / '修改前备份'
data = json.loads((PROJECT / 'annotation.json').read_text())
old = json.loads((BACKUP / 'annotation.json').read_text())
md = (PROJECT / '标注说明.md').read_text()
assert data['spaces'] == old['spaces'], '空间、名称、编号和轮廓须完整保留'
assert data['image'] == old['image']
assert data['relations'][:-1] == old['relations'], '既有连接和门点须原样保留'
assert data['relations'][-1] == {
    'id': 'R281', 'source': 'S134', 'target': 'S136', 'type': 'access'
}
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
assert sha(PROJECT / data['image']['file']) == sha(BACKUP / data['image']['file'])
assert len(list(PROJECT.iterdir())) == 4
links = re.findall(r'\]\(([^)]+)\)', md)
for link in links:
    assert (PROJECT / link).is_file(), link
assert len(re.findall(r'!\[', md)) == 3
assert re.findall(r'我的确认／备注（(\d+)）', md) == ['04', '05', '13', '14']

# The only visible SVG change is the status; the new conceptual edge has no point.
svg = (PROJECT / '标注.svg').read_text()
old_svg = (BACKUP / '标注.svg').read_text()
plain = re.sub(r'<desc id="conceptual-connectivity-note">.*?</desc>', '', svg)
plain = plain.replace('246 个具名空间；概念连通复核剩 4 项关键疑点待确认',
                      '246 个具名空间；本轮开口复核有 14 组连通疑点待确认')
assert plain == old_svg
root = ET.fromstring(svg)
assert len([x for x in root.iter() if x.get('data-opening-id')]) == 233

doc = pymupdf.open(PROJECT / '标注.svg')
page = doc[0]
page.get_pixmap(matrix=pymupdf.Matrix(.5, .5)).save(OUT / '标注_全图预览.png')
page.get_pixmap(matrix=pymupdf.Matrix(1.4, 1.4),
               clip=pymupdf.Rect(660, 2905, 930, 3115)).save(OUT / '标注_更衣局部.png')

sections = md.split('### ')
css = '''body{font-family:Arial,"Arial Unicode MS",sans-serif;font-size:18px;
line-height:1.65;color:#21334a;margin:28px auto;max-width:1080px;padding:0 24px}
img{max-width:100%;height:auto;display:block;border:1px solid #d6dce5}
p{margin:13px 0}h3{font-size:25px}strong{color:#18314c}'''
for name, part in zip(['04-05', '13', '14'], sections[1:]):
    body = markdown.markdown('### ' + part)
    html = ('<!doctype html><meta charset="UTF-8"><base href="'
            + PROJECT.as_uri() + '/"><style>' + css + '</style>' + body)
    (OUT / f'预览_{name}.html').write_text(html)

report = {
    'spaces_unchanged': True, 'original_unchanged': True,
    'previous_relations_and_openings_preserved': True,
    'svg_only_status_and_conceptual_note_changed': True,
    'formal_files': sorted(p.name for p in PROJECT.iterdir()),
    'relations': dict(Counter(r['type'] for r in data['relations'])),
    'md_links_valid': len(links), 'embedded_local_figures': 3,
    'pending_questions': ['04', '05', '13', '14'],
}
(OUT / '本轮核验结果.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(report, ensure_ascii=False, indent=2))
