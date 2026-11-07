from pathlib import Path
import hashlib
import html
import importlib.util
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

import markdown
from shapely.geometry import Polygon

BASE = Path(__file__).resolve().parents[2]
PROJECT = BASE / '标注试样/12_遂川县人民医院'
WORK = Path(__file__).resolve().parent / '用户确认同步_20261103_752afdbc/名称收尾'
STAGE = WORK / '待核验成果'
BACKUP = WORK / '修改前备份'
SKILL = Path('/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts/annotation_tools.py')
spec = importlib.util.spec_from_file_location('annotation_tools', SKILL)
annotation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(annotation)
data = json.loads((BACKUP / 'annotation.json').read_text())
s = next(s for s in data['spaces'] if s['id'] == 'S040')
assert s['type'] == 'unknown'
s['name'] = '辅助用房'
s['type'] = 'auxiliary_room'
(STAGE / 'annotation.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
tree = ET.parse(BACKUP / '标注.svg')
root = tree.getroot()
ns = {'s': annotation.NS}
group = root.find('.//s:g[@id="S040"]', ns)
group.set('data-space-name', s['name'])
group.set('data-space-type', s['type'])
group.set('data-space-type-name', annotation.TYPE_NAMES[s['type']])
group.find('s:title', ns).text = 'S040 | 辅助用房 | 辅助用房'
palette = ['#2563eb', '#0f766e', '#7c3aed', '#15803d', '#b45309', '#0369a1', '#a21caf', '#475569']
color = palette[int(hashlib.sha256(s['type'].encode()).hexdigest()[:4], 16) % len(palette)]
poly = group.find('s:polygon', ns)
poly.set('fill', color)
poly.set('stroke', color)
poly.attrib.pop('stroke-dasharray', None)
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
texts[1].text = '187个具名空间／区域；名称及关键连通已核对'
texts[1].set('fill', '#166534')
texts[-1].text = '标签：S编号＋具体名称＋〔标准功能类别〕；P红点：门洞／无门开口；E粉圈：建筑入口。'
tree.write(STAGE / '标注.svg', encoding='unicode')

# Keep a readable full review record, including every fixed name-review row.
full = (BACKUP / '标注说明.md').read_text()
full = full.replace('# 12_遂川县人民医院｜连通确认已同步（名称仍有1项待定）', '# 12_遂川县人民医院｜历史填写与最终确认记录')
full = full.replace('\n\n主要房名', '\n\n**最终确认（2026-11-03）：**用户在聊天中确认S040采用“辅助用房”；K01—K03已同步。下文旧待定文字为历史上下文，最终状态以正式标注说明为准。\n\n主要房名', 1)
lines = full.splitlines()
for i, line in enumerate(lines):
    cells = [html.unescape(v.strip()) for v in line.strip('|').split('|')]
    if len(cells) == 8 and cells[0] == '24' and cells[1] == 'S040':
        cells[6] = '辅助用房（用户聊天确认）'
        lines[i] = '| ' + ' | '.join(cells) + ' |'
full = '\n'.join(lines) + '\n'
def rebase(match):
    url = match.group(1)
    if re.match(r'^[a-zA-Z]+:', url) or url.startswith('#'):
        return match.group(0)
    destination = (PROJECT / url).resolve()
    assert destination.is_file(), url
    return '](' + os.path.relpath(destination, WORK) + ')'
full = re.sub(r'\]\(([^)]+)\)', rebase, full)
(WORK / '完整填写_含最终确认.md').write_text(full)

annotation.summary(data, STAGE / '标注说明.md')
summary = (STAGE / '标注说明.md').read_text()
summary = summary.replace('# 平面标注概览', '# 12_遂川县人民医院｜一层平面标注')
summary = summary.replace('空间名称已齐；结构与关系仍以原图及人工核对为依据。', '**当前状态（2026-11-03）：**名称、区域性质及关键连通已同步；本图按概念级精度完成。')
archive = os.path.relpath(WORK / '完整填写_含最终确认.md', PROJECT)
intro = f'''

**范围：**原图一层北侧两翼、入院大厅、中段及南侧门诊区。S043按用户要求退出标注；室外台阶、坡道及尺寸线不纳入室内面积。

[查看原图]({data['image']['file']})｜[查看标注与红点](标注.svg)｜[完整填写与最终确认记录]({archive})

| 核对项 | 用户确认 | 已同步结果 |
| --- | --- | --- |
| 24／S040 | 辅助用房就好了 | 名称“辅助用房”，通用类别auxiliary_room；不推定具体设备或人员用途。 |
| K01／S165 | 165室一个图案，就是大厅的一部分 | 铺地图案无损并入S167大厅，S165停用；S164/S166保留编号并更新名称。 |
| K02／S113 | 从104 | R228：S113—S104概念人员可达。 |
| K03／S121 | 是的联通123 | R229：S121—S123概念人员可达，保留E06外部入口。 |

新增两条连接按用户确认记录；门位不清，不虚构红点。原175个P点编号、坐标及空间对保持不变。
'''
summary = summary.replace('\n\n**标注规模：**', intro + '\n**标注规模：**', 1)
summary += '''
**合并与编号：**S031→S032；S086、S119→S118；S090→S085；S130→S140；S173→S174；S176→S175；S192→S191；S165→S167。已退出编号不复用，其余稳定S编号不重排。此前8处纹理区域按室内通道／大厅处理，面积保留。

**连通依据与精度：**北侧联络通道—中段东侧通道—南部门诊通道及导医区周边按图面连续铺地、开口和既有分段组织连接。无实体分隔的交通区边界只记概念access；药房、收费柜台窗口保留service，不作为人员通行。交通核仅核对对外连接，不细分核内路线。未记录关系不表示不可达，也不作为负例。

**图连通检查：**187个节点中，184个已有通往至少一个入口的记录路径。S040辅助用房、S137卫生间／更衣功能块、S182收费储藏的内部小门仍不清楚，属于本轮不细究的内部细节，未凭共墙补边。入口分别作为外部接口，不借共同null端点把入口互连。S190与S193未建立无依据的直接连接，两者各经已辨房门接入网络。

**核验：**正式`validate --check-dir`结果为valid=true、names_complete=true、pending_name_ids=[]、errors=[]、退出码0。写回前后分别校验；另检查原图哈希、稳定编号、面积保留、可见标签、175个红点对应以及整图和局部实际渲染。完整填写、原始四文件和核验记录保存在外部核对目录。
'''
(STAGE / '标注说明.md').write_text(summary)
for text, folder in [(full, WORK), (summary, PROJECT)]:
    for url in re.findall(r'\]\(([^)]+)\)', text):
        assert (folder / url).is_file(), url
for space in data['spaces']:
    g = root.find('.//s:g[@id="' + space['id'] + '"]', ns)
    assert g.get('data-space-name') == space['name'] and g.get('data-space-type') == space['type']
    visible = ''.join(t.text or '' for t in g.findall('s:text', ns))
    assert space['name'] in visible and '〔' in visible and '〕' in visible, space['id']
result = subprocess.run([sys.executable, str(SKILL), 'validate', str(STAGE / 'annotation.json'), '--check-dir'], capture_output=True, text=True)
assert result.returncode == 0, result.stdout + result.stderr
(WORK / '写回前正式校验.json').write_text(result.stdout)
(WORK / '聊天确认记录.json').write_text(json.dumps({'S040': {'answer': '辅助用房就好了', 'name': '辅助用房', 'type': 'auxiliary_room'}}, ensure_ascii=False, indent=2) + '\n')
body = markdown.markdown(summary, extensions=['tables'])
(WORK / 'MD预览.html').write_text('<!doctype html><meta charset="utf-8"><base href="' + html.escape(PROJECT.as_uri() + '/') + '"><style>body{max-width:1000px;margin:28px auto;font:17px/1.65 -apple-system,sans-serif;color:#182b3a}table{border-collapse:collapse}td,th{border:1px solid #ddd;padding:8px}a{color:#086b9b}</style>' + body)
print(result.stdout)
