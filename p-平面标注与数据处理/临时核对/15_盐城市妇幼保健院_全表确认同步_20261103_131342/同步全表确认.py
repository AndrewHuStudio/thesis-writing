from pathlib import Path
from collections import Counter
import html
import importlib.util
import json
import re
import xml.etree.ElementTree as ET
import pymupdf

R = Path(__file__).resolve().parent
B = R / '修改前备份'
P = R / '待核验成果'
skill = Path('/Users/hushili/.codex/skills/outpatient-plan-annotation')
spec = importlib.util.spec_from_file_location('annotation_tools', skill / 'scripts/annotation_tools.py')
at = importlib.util.module_from_spec(spec)
spec.loader.exec_module(at)
original = json.loads((B / 'annotation.json').read_text())
data = json.loads((B / 'annotation.json').read_text())
spaces = {s['id']: s for s in data['spaces']}
answers = {'S222': ('辅助用房', 'auxiliary_room'), 'S245': ('候诊区', 'hall'),
    'S205': ('尿常规', 'laboratory'), 'S206': ('便常规', 'laboratory'),
    'S274': ('中庭', 'courtyard')}
for sid, (name, typ) in answers.items():
    spaces[sid].update(name=name, type=typ)
assert not at.unresolved(data)
assert 'area_ratio' not in spaces['S274']
assert data['relations'] == original['relations']
for old, new in zip(original['spaces'], data['spaces']):
    assert old['polygon_px'] == new['polygon_px']
    assert old.get('area_ratio') == new.get('area_ratio')
    if old['id'] not in answers:
        assert old == new
(P / 'annotation.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
md = html.unescape((B / '标注说明.md').read_text())
start = md.index('## 名称核对填写表')
end = md.index('**类型与数量：**', start)
tables = md[start:end]
tables = tables.replace('## 名称核对填写表', '## 名称核对表与原填写留存', 1)
first_heading = tables.index('### 01 ')
old_overview = tables[:first_heading]
table_links = re.search(r'\[原图\].*?(?=\n\| 片区)', old_overview, re.S).group(0)
group_table = old_overview[old_overview.index('| 片区'):]
tables = ('## 名称核对表与原填写留存\n\n'
    '原336项固定核对表已全部确认；4个旧空间编号已合并退出核心数据，表中保留原映射与填写。'
    '“照片识读已同步；非用户填写”和前次候选依据为历史过程记录；本次用户已在聊天中确认全表信息。'
    '下方局部图及原总图继续用于追溯，无需重复填写。\n\n'
    + table_links + '\n' + group_table + tables[first_heading:])
lines = []
for line in tables.splitlines():
    cells = [v.strip() for v in line.strip().strip('|').split('|')]
    if len(cells) == 7 and cells[1] in answers:
        sid = cells[1]
        name = answers[sid][0]
        cells[2] = name
        cells[4] = '本次用户确认已同步。前次判读：' + cells[4]
        if sid == 'S274':
            cells[4] = '用户已在聊天中确认全表信息，采用原预估“中庭”；作为外部露天／挑空区域，不计首层室内空间和面积。'
            cells[5] = '已确认：中庭；面积排除已按用户口径落实（聊天确认）'
        line = '| ' + ' | '.join(cells) + ' |'
    lines.append(line)
tables = '\n'.join(lines) + '\n\n'
tables = re.sub(r'（(\d+)项；剩余\d+项）', r'（\1项；名称已确认）', tables)
rel = '../../临时核对/' + R.name
prefix = '''# 15_盐城市妇幼保健院｜首层标注

**名称信息已全部确认并同步：422个空间／区域，名称未确认项为0。** 图纸楼层按用户明确说明记为首层；门诊大厅上空作为外部区域，不计首层室内空间及面积。全图门洞／主要连通尚待图面复核，因此不将本次名称收尾记为整图标注完成。

## 全表确认同步（2026-11-03）

用户已确认全部信息。本轮采用核对123／S222“辅助用房”、139／S245“候诊区”、199／S205“尿常规”、200／S206“便常规”；252／S274按本次全表确认采用原预估“中庭”。S274保留轮廓及稳定编号，归为外部露天／挑空区域，不计首层室内面积。已有11处绿化也继续排除，不因本轮确认改入室内空间。

**用户楼层与范围原话：**“别管这就是首层，门诊大厅上空都作为外部区域不计入首层空间”。该说明作为本图楼层和范围依据，不再重复询问。

此前已确认的两处污洗间范围，以及大会议厅、两组西南休息区和最南端休息区的合并全部沿用；S368、S401、S403、S416不再作为独立节点，旧编号不复用。全部原填写和固定核对号继续保留在下表及修改前备份中。

'''
counts = Counter(s['type'] for s in data['spaces'])
rels = Counter(r['type'] for r in data['relations'])
indoor = sum(at.indoor(s) for s in data['spaces'])
tail = '**类型与数量：**' + '、'.join(f'{at.TYPE_NAMES[k]} {v}个' for k, v in counts.items()) + '。\n\n'
tail += f'**面积与范围：**{indoor}个首层室内空间／区域参与面积归一化，另有11处绿化及1处外部中庭／挑空区域，不参与室内面积；占比合计为1。本轮未改轮廓、面积、编号或既有关系。\n\n'
tail += f'**连接关系：**{len(data["relations"])}条，其中人员可达{rels["access"]}条、共墙{rels["shared_wall"]}条；定位开口为0，未录入外部入口。名称和楼层确认不替代图面连通复核。\n\n'
tail += '**当前状态：**名称、楼层和面积口径已收尾；全图门洞／主要连通尚未完成逐片区复核。后续由助手先回看图面，补充清晰可辨门洞及无门开口，与SVG红点同步；小设备间内部细节不逐项追问，仅保留影响主要通行组织的关键疑点。未记关系不是不相通，也不是负例。\n\n'
tail += f'**备份：**[本轮修改前四文件及原填写]({rel}/修改前备份/)。\n'
(P / '标注说明.md').write_text(prefix + tables + tail)
at.render(data, P / 'annotation.json', P / '标注.svg')
tree = ET.parse(P / '标注.svg')
oldtree = ET.parse(B / '标注.svg')
oldgroups = {g.get('id'): g for g in oldtree.iter() if g.get('data-space-name') is not None}
plan = next(g for g in tree.iter() if g.get('id') == 'plan')
for index, g in enumerate(list(plan)):
    sid = g.get('id')
    if sid in spaces and sid not in answers:
        plan.remove(g)
        plan.insert(index, oldgroups[sid])
# Keep the tiny auxiliary room's complete visible label inside its boundary.
aux = next(g for g in plan if g.get('id') == 'S222')
for child in list(aux):
    if child.tag.endswith('}text') or child.tag.endswith('}rect'):
        aux.remove(child)
aux.append(at.element('rect', {'x': 1471, 'y': 1010.25, 'width': 45,
    'height': 25.5, 'rx': 2, 'fill': 'white', 'fill-opacity': '.94',
    'stroke': '#15803d', 'stroke-width': '.8'}))
for y, label in zip([1017, 1025, 1033], ['S222', '辅助用房', '〔辅助用房〕']):
    aux.append(at.txt(1474, y, label, 6.5, '#15803d', True))
tree.write(P / '标注.svg', encoding='unicode')
document = pymupdf.open(P / '标注.svg')
page = document[0]
page.get_pixmap(matrix=pymupdf.Matrix(.5, .5), alpha=False).save(R / '全图检查.png')
for name, rect in {'检验两项': (1090, 1180, 1250, 1320),
    '辅助用房与候诊区': (1560, 940, 1730, 1430),
    '中庭': (1080, 1580, 1370, 1850)}.items():
    # SVG header is 122.2 px above plan coordinates.
    x0, y0, x1, y1 = rect
    page.get_pixmap(matrix=pymupdf.Matrix(2, 2),
        clip=pymupdf.Rect(x0, y0+122.2, x1, y1+122.2), alpha=False).save(R / (name + '.png'))
print(json.dumps({'names_complete': True, 'spaces': len(spaces),
    'indoor_spaces': indoor, 'relations': len(data['relations']), 'names_updated': answers}, ensure_ascii=False))
