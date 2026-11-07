from pathlib import Path
from collections import Counter
import hashlib
import html
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET

import markdown
from PIL import Image
from shapely.geometry import Point, Polygon

WORK = Path(__file__).resolve().parent / ('用户确认同步_20261103_' + uuid.uuid4().hex[:8])
PROJECT = Path(__file__).resolve().parents[2] / '标注试样/11_寿县县医院新区'
SKILL = Path('/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts/annotation_tools.py')
BACKUP = WORK / '修改前备份'
STAGE = WORK / '待核验成果'
BACKUP.mkdir(parents=True)
STAGE.mkdir()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert len(list(PROJECT.iterdir())) == 4
for path in PROJECT.iterdir():
    shutil.copy2(path, BACKUP / path.name)
    shutil.copy2(path, STAGE / path.name)
text = (BACKUP / '标注说明.md').read_text()
decoded = html.unescape(text)
answers = {}
for key in ['A01', 'A02', 'K01']:
    section = decoded.split('### ' + key + '｜', 1)[1].split('\n##', 1)[0]
    answers[key] = section.split('**我的确认／备注：**', 1)[1].strip()
assert answers == {'A01': '属于室内空间', 'A02': '是的，可以步入', 'K01': '连接的是左边‘'}, answers
data = json.loads((STAGE / 'annotation.json').read_text())
original = json.loads((BACKUP / 'annotation.json').read_text())
spaces = {s['id']: s for s in data['spaces']}
spaces['S001']['type'] = 'hall'
spaces['S035']['type'] = 'staff_support'
spaces['S035']['level'] = 'functional_block'
# S001 remains an indoor open hall, consistent with the other hall units.
# The west connection is the existing exterior interface E15, not a new indoor edge.
assert [r['id'] for r in data['relations'] if r['type'] == 'entrance' and r['target'] == 'S168'] == ['E15']
assert not any(r['type'] == 'access' and 'S168' in [r['source'], r['target']] for r in data['relations'])
spec = importlib.util.spec_from_file_location('annotation_tools', SKILL)
annotation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(annotation)
annotation.normalize(data)
assert data['relations'] == original['relations']
for s, before in zip(data['spaces'], original['spaces']):
    assert s['id'] == before['id'] and s['name'] == before['name']
    assert s['polygon_px'] == before['polygon_px']
    assert s.get('area_ratio') == before.get('area_ratio')
(STAGE / 'annotation.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

# Update only the two affected groups; preserve all previously reviewed labels.
tree = ET.parse(STAGE / '标注.svg')
root = tree.getroot()
ns = {'s': annotation.NS}
palette = ['#2563eb', '#0f766e', '#7c3aed', '#15803d', '#b45309', '#0369a1', '#a21caf', '#475569']
for sid in ['S001', 'S035']:
    s = spaces[sid]
    group = root.find('.//s:g[@id="' + sid + '"]', ns)
    color = palette[int(hashlib.sha256(s['type'].encode()).hexdigest()[:4], 16) % len(palette)]
    group.set('data-space-type', s['type'])
    group.set('data-space-type-name', annotation.TYPE_NAMES[s['type']])
    group.find('s:title', ns).text = f'{sid} | {s["name"]} | {annotation.TYPE_NAMES[s["type"]]}'
    polygon = group.find('s:polygon', ns)
    polygon.set('fill', color)
    polygon.set('stroke', color)
    polygon.attrib.pop('stroke-dasharray', None)
    for child in list(group):
        if child.tag in ['{' + annotation.NS + '}rect', '{' + annotation.NS + '}text']:
            group.remove(child)
    x, y, width, height, font, lines = annotation.place_label(Polygon(s['polygon_px']), s)
    group.append(annotation.element('rect', {
        'x': x, 'y': y, 'width': width, 'height': height, 'rx': 2,
        'fill': 'white', 'fill-opacity': '.94', 'stroke': color, 'stroke-width': '.8',
    }))
    for i, line in enumerate(lines):
        group.append(annotation.txt(x + 4, y + font + 2 + i * (font + 2), line, font, color, True))
texts = root.findall('s:text', ns)
texts[1].text = '194个具名空间／区域；室内外属性及关键连通已核对'
texts[1].set('fill', '#166534')
texts[-1].text = '标签：S编号＋具体名称＋〔标准功能类别〕；P红点：门洞／无门开口；E粉圈：建筑入口。'
tree.write(STAGE / '标注.svg', encoding='unicode')

annotation.summary(data, STAGE / '标注说明.md')
summary = (STAGE / '标注说明.md').read_text()
summary = summary.replace('# 平面标注概览', '# 11_寿县县医院新区｜一层平面标注')
summary = summary.replace('空间名称已齐；结构与关系仍以原图及人工核对为依据。',
    '**当前状态（2026-11-03）：**房名、室内外／面积属性及关键连通已同步；本图按概念级精度完成。')
archive = '../../临时核对/' + WORK.parent.name + '/' + WORK.name + '/修改前备份/标注说明.md'
intro = f'''\n**范围：**仅本图一层。194个空间／区域，稳定S编号不重排；S029已按原填写并入S032职工餐厅，原编号停用。\n
[查看原图]({data['image']['file']})｜[查看标注与红点](标注.svg)｜[完整填写及同步前备份]({archive})\n
**本次确认与落实：**\n
| 核对号 | 用户原文 | 同步结果 |
| --- | --- | --- |
| A01／S001 | {answers['A01']} | 门厅归为大厅（hall），计入室内面积；open_space表示开放大厅单元。 |
| A02／S035 | {answers['A02']} | 营养食堂按室内工作人员支持用房（staff_support）归类，功能块层级，与职工餐厅口径一致。 |
| K01／S168 | {answers['K01']} | 结合局部图将“左边”理解为西侧对外入口E15；沿用既有入口，不新增跨挂号等房间的室内连接。 |\n
S001、S035原草稿已纳入面积分母；确认后重新归一化，占比未改变。三个内院S137—S139仍以courtyard排除室内面积。\n'''
summary = summary.replace('\n\n**标注规模：**', intro + '\n**标注规模：**', 1)
concepts = decoded.split('### 未定位门位的概念连接及依据', 1)[1].split('### 核验口径', 1)[0].strip()
summary += '\n**连通与精度：**共墙、服务窗口不等于人员通行；入口按独立E编号保存，不借室外或内院节点构造室内捷径。未记录关系不表示不相通，也不能作为负例。\n'
summary += '\n**本轮不细究的内部细节：**餐车清洗S028内部小门、卫生间S185与相邻更衣间的具体开门、交通核内部路线及半开放柜台缺口。证据不足处不补关系或虚构门位。\n'
summary += '\n### 未定位门位的概念连接及依据\n\n' + concepts + '\n'
summary += '\n**核验：**正式`validate --check-dir`应为valid=true、names_complete=true、pending_name_ids=[]、errors=[]、退出码0。写回前后分别校验；另检查可见标签、红点对应、原图哈希及整图和局部实际渲染。核验结果保存在外部核对目录。\n'
(STAGE / '标注说明.md').write_text(summary)

for target in re.findall(r'\]\(([^)]+)\)', summary):
    assert (PROJECT / target).is_file(), target
for s in data['spaces']:
    group = root.find('.//s:g[@id="' + s['id'] + '"]', ns)
    assert group.get('data-space-type') == s['type']
    visible = ''.join(t.text or '' for t in group.findall('s:text', ns))
    assert s['name'] in visible and '〔' in visible and '〕' in visible
for r in data['relations']:
    for o in r.get('openings', []):
        assert max(Polygon(spaces[r[k]]['polygon_px']).boundary.distance(Point(o['position_px'])) for k in ['source', 'target']) <= 6
result = subprocess.run([sys.executable, str(SKILL), 'validate', str(STAGE / 'annotation.json'), '--check-dir'], capture_output=True, text=True)
assert result.returncode == 0, result.stdout + result.stderr
report = {'answers': answers, 'formal_validation': json.loads(result.stdout),
          'relations_unchanged': True, 'polygons_and_area_ratios_unchanged': True,
          'opening_count': sum(len(r.get('openings', [])) for r in data['relations']),
          'type_counts': dict(Counter(s['type'] for s in data['spaces']))}
(WORK / '写回前核验.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
body = markdown.markdown(summary, extensions=['tables'])
preview = '<!doctype html><meta charset="utf-8"><base href="' + html.escape(PROJECT.as_uri() + '/') + '"><style>body{max-width:1000px;margin:28px auto;font:17px/1.65 -apple-system,sans-serif;color:#182b3a}table{border-collapse:collapse}td,th{border:1px solid #ddd;padding:8px}a{color:#086b9b}</style>' + body
(WORK / 'MD_预览.html').write_text(preview)
print(json.dumps({'work': str(WORK), **report}, ensure_ascii=False, indent=2))
