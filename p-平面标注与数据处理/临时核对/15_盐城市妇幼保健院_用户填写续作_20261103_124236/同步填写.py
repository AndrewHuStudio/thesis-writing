from pathlib import Path
from collections import Counter
import html
import importlib.util
import json
import re
import xml.etree.ElementTree as ET
from shapely.geometry import Polygon
from shapely.ops import unary_union

R = Path(__file__).resolve().parent
P = R / '待核验成果'
B = R / '修改前备份'
SKILL = Path('/Users/hushili/.codex/skills/outpatient-plan-annotation')
spec = importlib.util.spec_from_file_location('annotation_tools', SKILL / 'scripts/annotation_tools.py')
at = importlib.util.module_from_spec(spec)
spec.loader.exec_module(at)
data = json.loads((B / 'annotation.json').read_text())
old = {s['id']: dict(s) for s in data['spaces']}
spaces = {s['id']: s for s in data['spaces']}
md = html.unescape((B / '标注说明.md').read_text())
rows = []
for line in md.splitlines():
    cells = [v.strip() for v in line.strip().strip('|').split('|')]
    if len(cells) == 7 and re.fullmatch(r'S\d+', cells[1]):
        rows.append(cells)
assert len(rows) == 336
types = {
    '休息区': 'hall', '等候区': 'hall', '候诊区': 'hall',
    '风机室': 'building_services', '值班室': 'staff_support',
    '诊室': 'consultation', '值班更衣': 'staff_support',
    '会议室': 'conference', '资料室': 'storage',
    'VIP休息室': 'hall', '专科检查': 'examination',
    '教室': 'education', '库房': 'storage', '公共大厅': 'hall', '厕所': 'toilet',
}
direct = {}
for cells in rows:
    answer = cells[5]
    if answer in types:
        sid = cells[1]
        spaces[sid].update(name=answer, type=types[answer])
        direct[sid] = answer

# The user explicitly confirmed both corner boundaries in this conversation.
# Repartition only the service room portion; retain each adjacent toilet.
spaces['S018'].update(name='污洗间', type='waste_handling',
    polygon_px=[[188, 304], [237, 304], [237, 413], [188, 413]])
spaces['S019']['polygon_px'] = [[237, 304], [284, 304], [284, 413], [237, 413]]
spaces['S070'].update(name='污染清洗区', type='waste_handling',
    polygon_px=[[2171, 305], [2213, 305], [2213, 415], [2171, 415]])
spaces['S069']['polygon_px'] = [[2125, 305], [2171, 305], [2171, 415], [2125, 415]]
for ids in [('S018', 'S019'), ('S069', 'S070')]:
    before = unary_union([Polygon(old[i]['polygon_px']) for i in ids])
    after = unary_union([Polygon(spaces[i]['polygon_px']) for i in ids])
    assert before.symmetric_difference(after).area == 0

merges = {'S368': 'S367', 'S401': 'S400', 'S403': 'S402', 'S416': 'S415'}
for removed, kept in merges.items():
    shape = unary_union([Polygon(spaces[i]['polygon_px']) for i in (removed, kept)])
    assert shape.geom_type == 'Polygon' and not shape.interiors
    spaces[kept]['polygon_px'] = [list(v) for v in list(shape.exterior.coords)[:-1]]
    name = '大会议厅' if kept == 'S367' else '休息区'
    spaces[kept].update(name=name, type='conference' if kept == 'S367' else 'hall')
    del spaces[removed]
data['spaces'] = list(spaces.values())
relation_changes = []
relations = []
seen = set()
for r in data['relations']:
    original = dict(r)
    r['source'] = merges.get(r['source'], r['source'])
    r['target'] = merges.get(r['target'], r['target'])
    key = tuple(sorted((str(r['source']), str(r['target'])))) + (r['type'],)
    if r['source'] == r['target'] or key in seen:
        relation_changes.append({'before': original, 'action': '删除合并后自连接或重复关系'})
        continue
    if r != original:
        relation_changes.append({'before': original, 'after': dict(r), 'action': '重定向合并端点'})
    seen.add(key)
    relations.append(r)
data['relations'] = relations
at.normalize(data)
(P / 'annotation.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
pending = at.unresolved(data)
assert {s['id'] for s in pending} == {'S222', 'S245', 'S205', 'S206', 'S274'}
result_by_id = {sid: f'用户填写已同步：{name}' for sid, name in direct.items()}
result_by_id.update({'S018': '聊天确认已同步：与下方污洗小间合并；右侧厕所S019单独保留',
    'S070': '聊天确认已同步：与下方小间合并为污染清洗区；左侧厕所S069单独保留'})
for removed, kept in merges.items():
    result_by_id[removed] = f'合并已同步：并入{kept} {spaces[kept]["name"]}，旧编号不再复用'
for sid in ('S367', 'S400', 'S402', 'S415'):
    result_by_id[sid] = f'合并后保留：{spaces[sid]["name"]}'

start = md.index('## 名称核对填写表')
end = md.index('**类型与数量：**', start)
table_part = md[start:end]
table_part = re.sub(r'\*\*固定核对表共336项：.*?\*\*',
    '**固定核对表共336项：沿用原映射及全部填写；其中4项已合并到保留编号，现剩5项名称未确认。**', table_part)
table_part = table_part.replace('S274的中庭面积类别已确认，名称仍待定。',
    'S274的中庭面积类别已确认，名称仍待定。已合并的旧S编号仅在此表保留追溯，不再作为独立空间。')
table_part = table_part.replace('原 S 编号全部保留。',
    '核对表保留原S编号映射；已合并的4个旧S编号只作历史追溯，不再作为独立空间。')
updated_lines = []
for line in table_part.splitlines():
    cells = [v.strip() for v in line.strip().strip('|').split('|')]
    if len(cells) == 7 and re.fullmatch(r'S\d+', cells[1]):
        sid = cells[1]
        if sid in result_by_id:
            if sid in spaces:
                cells[2] = spaces[sid]['name']
            else:
                cells[2] = f'已并入{merges[sid]} {spaces[merges[sid]]["name"]}'
            cells[4] = result_by_id[sid] + '。前次判读：' + cells[4]
        line = '| ' + ' | '.join(cells) + ' |'
    updated_lines.append(line)
table_part = '\n'.join(updated_lines) + '\n\n'
sections = re.split(r'(?=^### \d{2} )', table_part, flags=re.M)
for i, section in enumerate(sections):
    ids = re.findall(r'\|\s*(S\d+)\s*\|', section)
    count = sum(s['id'] in ids for s in pending)
    sections[i] = re.sub(r'（(\d+)项；剩余\d+项）', rf'（\1项；剩余{count}项）', section, count=1)
table_part = ''.join(sections)

prefix = '''# 15_盐城市妇幼保健院｜标注草稿

本轮已同步您在MD中的明确房名和合并意见，并落实聊天确认的两处污洗间范围。现有422个空间／区域，剩5项名称未确认；图纸楼层和全图门洞／主要连通复核仍未收尾。

## 用户填写同步结果（2026-11-03）

本轮解决原39项中的34项，另将核对10的“风机房”按填写改为“风机室”，核对13的“污洗”改为“诊室”。用户原填写、固定核对号01—336及各片区图片均保留在下方原表。前一轮照片识读的297项属于助手图面判读，本轮仅按明确填写修正，不冒称逐项用户确认。

| 原核对号／空间 | 本轮结果 |
| --- | --- |
| 11／S018、S019 | S018与正下方污洗小间合为“污洗间”；S019只保留右侧厕所。范围已由聊天确认。 |
| 53／S070、S069 | S070与正下方小间合为“污染清洗区”；S069只保留左侧厕所。范围已由聊天确认。 |
| 294—295／S367、S368 | S368并入S367“大会议厅”。 |
| 319—320／S400、S401 | S401并入S400“休息区”。 |
| 321—322／S402、S403 | S403并入S402“休息区”。 |
| 329—330／S415、S416 | 按合并意见保留S415，合并后名称为“休息区”；原329填写“公共大厅”保留在原表供追溯。 |

合并后的S368、S401、S403、S416退出核心JSON及SVG，旧编号不再复用；其余编号保持稳定。仅清理或重定向合并所涉及的关系，不从共墙推断通行。休息区、等候区和候诊区采用共享类别“大厅”，保留用户具体名称及原有空间层级。

### 剩余名称与图纸信息

原核对123／S222、139／S245、199／S205、200／S206、252／S274共5项仍未得到明确名称。各项的候选、局部图及唯一填写位置仍在下方原表；S274的露天／挑空面积排除口径已落实，仅名称待定，不再询问是否计面积。

![剩余5项原号定位](剩余定位链接)

**资料01｜图纸楼层。**仍缺能读清项目名称及楼层／平面图名称的图题。“门诊大厅上空”不能单独证明楼层，本图暂不认定为首层。

**我的确认／备注：**待填写（填写实际图题或楼层即可）

'''
relpath = '../../临时核对/' + R.name
prefix = prefix.replace('剩余定位链接', relpath + '/剩余5项定位总图.png')
counts = Counter(s['type'] for s in data['spaces'])
levels = Counter(s['level'] for s in data['spaces'])
rc = Counter(r['type'] for r in relations)
tail = '\n**类型与数量：**' + '、'.join(f'{at.TYPE_NAMES[k]} {v}个' for k, v in counts.items()) + '。\n\n'
tail += '**空间层级：**' + '、'.join(f'{at.LEVEL_NAMES[k]} {v}个' for k, v in levels.items()) + '。\n\n'
tail += f'**连接关系：**{len(relations)}条，其中人员可达{rc["access"]}条、共墙{rc["shared_wall"]}条。合并只重定向相关端点，去除自连接与重复关系；既有关系未作全图语义复核。\n\n'
tail += '**入口与开口：**当前未录入外部入口，定位开口为0。此次未开展全图门洞识别，不以名称同步或结构校验代表主要连通已完成。后续须逐片区回看清晰图面，记录可辨门洞／无门开口并同步SVG红点；共墙和服务窗口不作为人员通行依据。\n\n'
indoor = sum(at.indoor(s) for s in data['spaces'])
tail += f'**相对规模：**{indoor}个室内空间／区域参与归一化，面积占比合计为1；11处绿化及S274露天／挑空区域不计室内面积，不保存实测平方米。污洗间范围重分及四组合并前后的总覆盖范围一致，无新增占地。\n\n'
tail += '**范围与状态：**仅处理15号本张原图；scope和图纸楼层状态沿用现有信息。已同步34项原待确认项及2项既有房名修正，剩5项名称待确认；楼层与门洞／主要连通尚未收尾，因此仍为标注草稿。未记录关系不表示不相通，也不是负例。\n\n'
tail += f'**备份：**本轮修改前四文件及用户填写位于[修改前备份]({relpath}/修改前备份/)。原图不改动。\n'
(P / '标注说明.md').write_text(prefix + table_part + tail)

# Reuse unchanged label groups to preserve previously checked dense-room layout.
at.render(data, P / 'annotation.json', P / '标注.svg')
newtree = ET.parse(P / '标注.svg')
oldtree = ET.parse(B / '标注.svg')
oldgroups = {g.get('id'): g for g in oldtree.iter() if g.get('data-space-name') is not None}
plan = next(g for g in newtree.iter() if g.get('id') == 'plan')
for index, group in enumerate(list(plan)):
    sid = group.get('id')
    if sid in spaces and spaces[sid] == old[sid]:
        plan.remove(group)
        plan.insert(index, oldgroups[sid])
newtree.write(P / '标注.svg', encoding='unicode')
(R / '同步记录.json').write_text(json.dumps({
    'direct_names': direct, 'merged_ids': merges,
    'corner_repartition_confirmed_in_chat': True,
    'resolved_previous_pending': 34, 'remaining': [s['id'] for s in pending],
    'relation_changes': relation_changes,
}, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'spaces': len(spaces), 'relations': len(relations),
    'direct_names': len(direct), 'pending': [s['id'] for s in pending]}, ensure_ascii=False))
