"""Finalize the explicit S069 answer and verify plan 25 without changing its graph."""
from collections import Counter, deque
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import copy
import hashlib
import html
import json
import os
import re
import shutil
import sys
import xml.etree.ElementTree as ET

from PIL import Image
from shapely.geometry import Point, Polygon
import pymupdf

BASE = Path(__file__).resolve().parent
PROJECT = BASE.parents[1] / '标注试样' / '25_上海市第十人民医院内科病房综合楼'
sys.path.insert(0, '/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts')
import annotation_tools as at

OUT = BASE / ('最终收尾_' + datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d_%H%M%S'))
OUT.mkdir()
backup = OUT / '用户填写与收尾前备份'
backup.mkdir()
for f in PROJECT.iterdir():
    if f.is_file():
        shutil.copy2(f, backup / f.name)
jsonfile = PROJECT / 'annotation.json'
mdfile = PROJECT / '标注说明.md'
old = json.loads(jsonfile.read_text())
old_md = mdfile.read_text()
rows = []
answers = {}
for line in old_md.splitlines():
    if not re.match(r'^\|\s*\d+\s*\|\s*S\d+', line):
        continue
    c = [html.unescape(v.strip()) for v in line.split('|')[1:-1]]
    assert len(c) == 7 and c[0] == c[-1]
    assert c[5] not in ('', '待确认', '待填写', '待定')
    answers[c[1]] = c[2] if c[5] in ('已确认', '确认', '同意') else c[5]
    rows.append(line)
assert len(answers) == 18 and answers['S069'] == '管井'
data = copy.deepcopy(old)
spaces = {s['id']: s for s in data['spaces']}
spaces['S069'].update(name=answers['S069'], type='building_services')
assert all(spaces[k]['name'] == v for k, v in answers.items())
at.normalize(data)
assert data['relations'] == old['relations'] and data['image'] == old['image']
assert all(s == spaces[s['id']] for s in old['spaces'] if s['id'] != 'S069')
assert not at.unresolved(data)
jsonfile.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

# Replace only the changed room's visible label, preserving every opening and entry.
upright = copy.deepcopy(data)
upright['image'].update(width=3232, height=2472)
for s in upright['spaces']:
    s['polygon_px'] = [[y, 2472-x] for x, y in s['polygon_px']]
at.render(upright, jsonfile, OUT / '标签重绘中间稿.svg')
ns = {'s': at.NS}
tree = ET.parse(PROJECT / '标注.svg')
root = tree.getroot()
fresh = ET.parse(OUT / '标签重绘中间稿.svg').find('.//s:g[@id="S069"]', ns)
for e in fresh.iter():
    if e.tag == '{' + at.NS + '}text':
        e.set('font-family', 'Hiragino Sans GB, PingFang SC, Microsoft YaHei, sans-serif')
plan = root.find('s:g[@id="plan"]', ns)
previous = plan.find('s:g[@id="S069"]', ns)
index = list(plan).index(previous)
plan.remove(previous)
plan.insert(index, fresh)
titles = root.findall('s:text', ns)
titles[0].text = '25 上海市第十人民医院内科病房综合楼｜一层标注完成'
titles[1].text = '97个具名空间；106条人员可达关系；120个室内门洞／开口定位点；连通性复核完成'
titles[1].set('fill', '#166534')
titles[-1].text = '空间编号＋名称＋〔标准功能类别〕；红点P：室内门洞／无门开口；粉圈E：建筑入口；坐标和编号与JSON对应。'
tree.write(PROJECT / '标注.svg', encoding='unicode')

# Preserve the exact answer rows and repair relative links in the archived reading copy.
def archive_link(match):
    target = match.group(2)
    if '://' in target or target.startswith('#'):
        return match.group(0)
    absolute = (PROJECT / target).resolve()
    return match.group(1) + os.path.relpath(absolute, OUT) + ')'
archive = re.sub(r'(!?\[[^\]]*\]\()([^\)]+)\)', archive_link, old_md)
archive = ('> 收尾前填写与复核记录快照。18行用户填写已全部采纳；最新完成状态见正式标注说明。\n\n'
    + archive)
(OUT / '填写与复核原文留存.md').write_text(archive)
assert all(row in archive for row in rows)
at.summary(data, OUT / '完成概览.md')
summary = (OUT / '完成概览.md').read_text()
summary = summary.replace('# 平面标注概览', '# 25 上海市第十人民医院内科病房综合楼｜一层标注完成')
summary = summary.replace('空间名称已齐；结构与关系仍以原图及人工核对为依据。',
    '**状态：已按概念级精度完成。名称及属性待确认0项，关键连通待确认0项。18项用户填写均已同步。**')
scope = html.unescape(old_md.split('**图面范围：**', 1)[1].split('\n\n', 1)[0])
retained = os.path.relpath(OUT / '填写与复核原文留存.md', PROJECT)
mdfile.write_text(summary + '\n**图面范围：**' + scope + '\n\n'
    '**连通性结果：**97个空间形成1个人员可达连通分量，均可沿室内记录通路到达至少1个入口；'
    '27个交通节点形成独立连通的交通网络，无需借道诊室等功能房。服务联系和共墙不参与寻路。\n\n'
    '**精度与依据：**JSON保持原图2472×3232像素坐标，SVG仅显示时转正。'
    'P001—P120表示近似门洞／无门开口位置；E001—E012为独立建筑入口。'
    'R047（S047—S044）、R102（S093—S094）按门斗朝向与完整布局保留为布局推断，'
    '无精确门位，不编造红点。交通核内部路线、卫生间隔间和设备内部构造不展开。'
    '管井检修门不作为公共交通节点；关系不表达门禁权限。\n\n'
    f'**核对材料：**[18项填写原文与前轮复核记录（收尾前快照）]({retained})。原图和已有编号保持不变。\n\n'
    '[原图](25_上海市第十人民医院内科病房综合楼_原图.jpg) · [标注SVG](标注.svg) · [结构化数据](annotation.json)\n')

# Fresh graph, geometric, and SVG consistency checks.
adj = {k: set() for k in spaces}
for r in data['relations']:
    if r['type'] == 'access':
        adj[r['source']].add(r['target'])
        adj[r['target']].add(r['source'])
def reach(seeds, allowed):
    seen = set(seeds)
    todo = deque(seeds)
    while todo:
        for node in adj[todo.popleft()] & allowed:
            if node not in seen:
                seen.add(node)
                todo.append(node)
    return seen
traffic = {k for k, s in spaces.items() if s['type'] in ('hall','corridor','entrance','vertical_core')}
assert len(reach(['S044'], set(spaces))) == 97
assert reach(['S044'], traffic) == traffic and len(traffic) == 27
entrances = [r['target'] for r in data['relations'] if r['type'] == 'entrance']
assert reach(entrances, set(spaces)) == set(spaces)
polys = {k: Polygon(s['polygon_px']) for k, s in spaces.items()}
distances = []
for r in data['relations']:
    for o in r.get('openings', []):
        point = Point(o['position_px'])
        dist = max(polys[r[k]].distance(point) for k in ('source','target'))
        assert dist < 8
        distances.append(dist)
for sid, s in spaces.items():
    g = root.find('.//s:g[@id="'+sid+'"]', ns)
    text = ''.join(e.text or '' for e in g.findall('s:text', ns)).replace(' ', '')
    assert s['name'].replace(' ', '') in text and sid in text
    assert g.get('data-space-name') == s['name'] and g.get('data-space-type') == s['type']
result, status = at.check(data, jsonfile, check_dir=True)
assert status == 0, result
source = PROJECT / data['image']['file']
assert source.read_bytes() == (backup / source.name).read_bytes()
for link in re.findall(r'!?\[[^\]]*\]\(([^\)]+)\)', mdfile.read_text()):
    assert (PROJECT / link).exists(), link
report = dict(validation=result, exit_code=status, spaces=97,
    relation_types=Counter(r['type'] for r in data['relations']),
    components=1, traffic_nodes=27, traffic_components=1,
    unreachable_from_entrances=[], openings=len(distances),
    located_access=sum(bool(r.get('openings')) for r in data['relations'] if r['type']=='access'),
    maximum_opening_distance_px=round(max(distances),3),
    preserved_answer_rows=len(rows), pending_names=[],
    sha256={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in PROJECT.iterdir() if f.is_file()})
(OUT / '最终连通性与四文件校验.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
doc = pymupdf.open(PROJECT / '标注.svg')
doc[0].get_pixmap().save(OUT / 'SVG最终完整渲染.png')
im = Image.open(OUT / 'SVG最终完整渲染.png')
im.crop((2350,765,2610,1020)).resize((780,765)).save(OUT / 'S069最终局部.png')
print('OUTPUT', OUT)
print(json.dumps(report,ensure_ascii=False,indent=2))
