"""Apply only the nineteen explicit confirmations in the current 21 Markdown."""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import base64
import hashlib
import html
import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1] / '标注试样'
PROJECT = next(ROOT.glob('21_*'))
SKILL = Path('/Users/hushili/.codex/skills/outpatient-plan-annotation')
sys.path.insert(0, str(SKILL / 'scripts'))
import annotation_tools as at

directory = BASE / PROJECT.name / ('20261105_名称同步_' + datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%H%M%S'))
directory.mkdir()
backup = directory / '同步前四文件与用户填写'
backup.mkdir()
for file in PROJECT.iterdir():
    if file.is_file():
        shutil.copy2(file, backup / file.name)

mdfile = PROJECT / '标注说明.md'
old_md = mdfile.read_text()
old_data = json.loads((PROJECT / 'annotation.json').read_text())
data = json.loads(json.dumps(old_data))
spaces = {s['id']:s for s in data['spaces']}
mapping = json.loads((BASE / PROJECT.name / '固定核对映射.json').read_text())
expected = {r['number']:r['id'] for r in mapping}
answers = {}
raw_rows = []
for line in old_md.splitlines():
    if not re.match(r'^\|\s*\d+\s*\|\s*S\d+', line):
        continue
    cols = [html.unescape(x.strip()) for x in line.split('|')[1:-1]]
    assert len(cols) == 7 and cols[0] == cols[-1]
    assert expected[cols[0]] == cols[1]
    assert cols[5] not in ['', '待确认', '待填写', '待定']
    answer = cols[2] if cols[5] in ['已确认', '同意', '确认'] else cols[5]
    answers[cols[1]] = answer
    raw_rows.append(line)
assert len(answers) == 19 and set(answers) == {s['id'] for s in data['spaces'] if s['type'] == 'unknown'}

types = {
    '观察室':'observation', 'EICU':'observation', '器械':'equipment_room',
    '手术准备间':'patient_preparation', '库房':'storage', '辅料':'storage',
    '检查室':'examination', '贵宾':'service', '茶水间':'staff_support',
    '肺功能':'examination', '心电':'examination', '煤表间':'building_services',
    '首长电梯以及前室':'vertical_core',
}
for sid,name in answers.items():
    assert spaces[sid]['type'] == 'unknown'
    spaces[sid].update(name=name, type=types[name])
spaces['S111']['scope'] = 'building_support'
spaces['S115'].update(level='core_block', scope='vip_service')
at.normalize(data)
assert data['image'] == old_data['image'] and data['relations'] == old_data['relations']
for old,new in zip(old_data['spaces'], data['spaces']):
    assert old['id'] == new['id'] and old['polygon_px'] == new['polygon_px']
    if old['id'] not in answers:
        assert old == new
jsonfile = PROJECT / 'annotation.json'
jsonfile.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
at.render(data, jsonfile, PROJECT / '标注.svg')
at.summary(data, directory / '更新概览.md')
summary = (directory / '更新概览.md').read_text().replace('# 平面标注概览', '# 21_海军总医院外科医疗大楼｜标注概览')
summary = summary.replace('空间名称已齐；结构与关系仍以原图及人工核对为依据。',
    '**房名与类别已同步：本轮19项均采用用户填写，当前名称待确认0项。整图仍待连通与门洞复核。**')
custom = []
for paragraph in old_md.split('\n\n'):
    if paragraph.startswith(('**本张范围：**','**判读与精度：**','**核对方式：**')):
        paragraph = html.unescape(paragraph)
        paragraph = paragraph.replace('以清晰原图文字记录可确定名称；19项模糊名称继续保持 unknown。',
            '原图可辨名称与本轮19项用户填写已同步；当前不存在 unknown 名称。')
        custom.append(paragraph)
review_title = '## 房名与范围核对（2026-11-05）'
review = old_md[old_md.index(review_title):]
review = review.replace('本轮 19 项待确认。沿用历史核对号与当前 S 编号；下列候选来自旧稿，尚未视为本轮确认。',
    '本轮19项已按“我的确认／备注”栏全部同步。核对号与S编号保持不变；预估名称及旧稿依据保留作历史记录，以填写栏的实际名称为准。')
review = review.replace('先核对名称、类别和空间范围；名称确认后，再逐张复核人员连通与可定位门洞。当前五图均无门洞红点，既有关系仍需复核。',
    '21号名称与类别已同步；下一阶段复核人员连通与可定位门洞。当前保留原146条关系，尚无已定位门洞红点，本轮未据改名自动新增连通关系。')
extra = ('**本轮类别与范围：**EICU归入留观类；“贵宾”按服务区记录；“煤表间”保留用户原名，归入建筑设备用房并调整为建筑支持范围；'
         '“首长电梯以及前室”作为交通核整体保存，归入首长专用服务范围。空间轮廓与编号未变。\n\n'
         '**门洞与连通状态：**当前122条人员可达关系均无定位红点；3条服务联系、15条共墙、6条入口连接保持原稿。'
         '本轮仅完成房名与类别同步，现有关系列入下一阶段图面复核。')
new_md = summary.rstrip() + '\n\n' + '\n\n'.join(custom) + '\n\n' + extra + '\n\n' + review
assert all(row in new_md for row in raw_rows), 'User-entered rows changed'
mdfile.write_text(new_md)

root = ET.parse(PROJECT / '标注.svg').getroot()
for sid,name in answers.items():
    group = next(e for e in root.iter() if e.get('id') == sid)
    visible = ''.join(e.text or '' for e in group.iter() if e.tag == '{'+at.NS+'}text')
    assert name in visible and group.get('data-space-type') == spaces[sid]['type'], sid
source = PROJECT / data['image']['file']
assert source.read_bytes() == (backup / source.name).read_bytes()
embedded = root.find('.//{'+at.NS+'}image').get('{'+at.XL+'}href')
assert base64.b64decode(embedded.split(',',1)[1]) == source.read_bytes()
for relative in re.findall(r'!\[[^\]]*\]\(([^)]+)\)', new_md):
    assert (PROJECT / relative).is_file(), relative
report,code = at.check(data,jsonfile,check_dir=True)
assert code == 0, report
(directory / '正式校验.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
(directory / '同步名称.json').write_text(json.dumps(answers,ensure_ascii=False,indent=2))
(directory / '用户原始填写.md').write_text(old_md)
print(json.dumps(dict(directory=str(directory),changed=len(answers),**report),ensure_ascii=False,indent=2))
