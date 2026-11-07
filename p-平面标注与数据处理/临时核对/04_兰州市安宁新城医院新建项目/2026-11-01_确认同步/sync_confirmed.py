from pathlib import Path
from collections import Counter
import hashlib
import html
import importlib.util
import json
import os
import re
import shutil
from xml.sax.saxutils import escape

import pymupdf


OUT = Path(__file__).resolve().parent
PROJECT = OUT.parents[2] / '标注试样/04_兰州市安宁新城医院新建项目'
BACKUP = OUT / '同步前备份'
BACKUP.mkdir(exist_ok=True)
assert not (BACKUP / 'annotation.json').exists(), '已有备份，禁止重跑覆盖'
raw_md = (PROJECT / '标注说明.md').read_text()
md = html.unescape(raw_md)
answers = {}
for number in ['04', '05', '13', '14']:
    line = next(line for line in md.splitlines()
                if f'我的确认／备注（{number}）' in line)
    value = line.split('：', 1)[1].replace('**', '').strip()
    answers[number] = value
assert answers == {'04': '同意', '05': '同意', '13': '南侧', '14': '同意'}, answers
for path in PROJECT.iterdir():
    if path.is_file():
        shutil.copy2(path, BACKUP / path.name)

# Keep an exact raw snapshot and a readable record with working relative links.
def archive_link(match):
    target = (PROJECT / match.group(1)).resolve()
    assert target.is_file(), target
    return '](' + os.path.relpath(target, OUT) + ')'


archive = re.sub(r'\]\(([^)]+)\)', archive_link, md)
archive += '''

## 同步结果（2026-11-01）

四项用户答案均已同步；上文问题与“待确认”状态是填写时的原始上下文。

- 04：原答“同意”，补入 S040—S038，R282。
- 05：原答“同意”，补入 S041—S039，R283。
- 13：原答“南侧”，补入 S092—S229，R284。S229 与 S231 已由 R007 连通；使用 S229 表达南侧连续通道，不据此确定门的位置或数量。
- 14：原答“同意”，补入 S102—S232，R285。

以上均为无定位门点的概念连接；没有把用户确认的通行关系转换为虚构门位。
'''
(OUT / '用户确认记录.md').write_text(archive)

data = json.loads((PROJECT / 'annotation.json').read_text())
old = json.loads((BACKUP / 'annotation.json').read_text())
new_relations = [
    {'id': 'R282', 'source': 'S040', 'target': 'S038', 'type': 'access'},
    {'id': 'R283', 'source': 'S041', 'target': 'S039', 'type': 'access'},
    {'id': 'R284', 'source': 'S092', 'target': 'S229', 'type': 'access'},
    {'id': 'R285', 'source': 'S102', 'target': 'S232', 'type': 'access'},
]
for new in new_relations:
    assert all(r['id'] != new['id'] for r in data['relations'])
    assert all(not (r['type'] == 'access'
                   and {r['source'], r['target']} == {new['source'], new['target']})
               for r in data['relations'])
    data['relations'].append(new)
(PROJECT / 'annotation.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

svg_path = PROJECT / '标注.svg'
svg = svg_path.read_text()
old_status = '246 个具名空间；概念连通复核剩 4 项关键疑点待确认'
new_status = '246 个具名空间；一层平面按概念精度完成，主要连通疑点已确认'
assert old_status in svg
svg = svg.replace(old_status, new_status, 1)
note = ('用户已确认：04 S040—S038（R282）；05 S041—S039（R283）；'
        '13 拍片连南侧通道，以 S092—S229（R284）表示，S229 已连 S231；'
        '14 S102—S232（R285）。四项均未定位门洞，不新增红点。'
        'R281 S134—S136 仍为布局推断。非目标内部细节不穷尽，未记录关系不表示不相通。')
svg, count = re.subn(r'<desc id="conceptual-connectivity-note">.*?</desc>',
                    '<desc id="conceptual-connectivity-note">' + escape(note) + '</desc>', svg)
assert count == 1
svg_path.write_text(svg)

# Use the shared summary without overwriting the user's confirmation record.
skill_script = Path('/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts/annotation_tools.py')
spec = importlib.util.spec_from_file_location('annotation_tools', skill_script)
annotation_tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(annotation_tools)
annotation_tools.summary(data, OUT / '自动概览.md')

prefix = md.split('## 本轮精度与处理')[0]
prefix = prefix.replace(
    '空间名称已齐；按概念级精度复核后，剩 **4 项关键连接**需要确认。请直接在下方局部图旁填写，整图尚未完成。',
    '**本张一层平面已按约定的概念精度完成。**空间名称已齐，主要连通疑点已全部确认；内部辅助小间及检修细节不要求穷尽。')
prefix = prefix.replace('262 条，服务联系 8 条、人员可达 242 条',
                        '266 条，服务联系 8 条、人员可达 246 条')
record_link = os.path.relpath(OUT / '用户确认记录.md', PROJECT)
final_md = prefix + f'''## 门洞与概念连接

233 个红点（225 个门洞、8 个无门开口），对应 211 条人员可达关系；另有 35 条无定位红点的概念连接。门位未确定的关系不增加红点。

## 本轮确认结果（2026-11-01）

- **04：同意。**S040 交通核连接北侧 S038 住院人行专用通道（R282）。
- **05：同意。**S041 交通核连接北侧 S039 门斗（R283）。
- **13：南侧。**S092 拍片连接南侧连续通道，以 S229 表达（R284）；S229 与 S231 已连通，不确定具体门位或门的数量。
- **14：同意。**S102 交通核连接西侧 S232 急诊通道（R285）。

S134 更衣与 S136 出入院结算（R281）仍为布局推断，未写成用户确认。未记录的内部小间连接保持未知，不作为不可通行负例。

[原图](04_兰州市安宁新城医院新建项目_原图.jpg) · [具名标注 SVG](标注.svg) · [用户填写与局部图记录]({record_link})

**完成范围：**当前 04 号的一层平面，按主要功能空间、通道、交通核及入口的概念可达精度交付。246 个稳定编号、名称和轮廓保留；原图未改动。正式目录仅保留原图、标注.svg、annotation.json 和本说明。核对原稿、用户填写及备份保存在目录外。
'''
(PROJECT / '标注说明.md').write_text(final_md)

# Verify incremental changes and the readable archive before rendering.
assert data['spaces'] == old['spaces']
assert data['image'] == old['image']
assert data['relations'][:-4] == old['relations']
assert data['relations'][-4:] == new_relations
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(PROJECT / data['image']['file']) == sha(BACKUP / data['image']['file'])
for docpath in [PROJECT / '标注说明.md', OUT / '用户确认记录.md']:
    for link in re.findall(r'\]\(([^)]+)\)', docpath.read_text()):
        assert (docpath.parent / link).is_file(), (docpath.name, link)

svg_doc = pymupdf.open(svg_path)
page = svg_doc[0]
page.get_pixmap(matrix=pymupdf.Matrix(.5, .5)).save(OUT / '标注_全图预览.png')
for name, box in [
    ('北部交通核', (1600, 1255, 2420, 1705)),
    ('急诊拍片及东南核', (1690, 3235, 2410, 3825)),
    ('放射密集局部', (570, 2075, 1620, 2800)),
]:
    page.get_pixmap(matrix=pymupdf.Matrix(1.2, 1.2),
                   clip=pymupdf.Rect(box)).save(OUT / f'标注_{name}.png')

report = {
    'answers': answers, 'added_relations': new_relations,
    'spaces': len(data['spaces']), 'relations': dict(Counter(r['type'] for r in data['relations'])),
    'opening_count': sum(len(r.get('openings', [])) for r in data['relations']),
    'previous_spaces_and_relations_preserved': True,
    'original_sha256': sha(PROJECT / data['image']['file']),
    'pending_key_questions': [],
}
(OUT / '确认同步核验.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(report, ensure_ascii=False, indent=2))
