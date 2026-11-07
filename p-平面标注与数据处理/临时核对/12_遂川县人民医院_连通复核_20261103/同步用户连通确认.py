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
from shapely.geometry import Polygon
from shapely.ops import unary_union

BASE = Path(__file__).resolve().parents[2]
PROJECT = BASE / '标注试样/12_遂川县人民医院'
WORK = Path(__file__).resolve().parent / ('用户确认同步_20261103_' + uuid.uuid4().hex[:8])
BACKUP = WORK / '修改前备份'
STAGE = WORK / '待核验成果'
SKILL = Path('/Users/hushili/.codex/skills/outpatient-plan-annotation/scripts/annotation_tools.py')
BACKUP.mkdir(parents=True)
STAGE.mkdir()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert len(list(PROJECT.iterdir())) == 4
for path in PROJECT.iterdir():
    shutil.copy2(path, BACKUP / path.name)
    shutil.copy2(path, STAGE / path.name)
original_text = (BACKUP / '标注说明.md').read_text()
decoded = html.unescape(original_text)
answers = {}
for key in ['K01', 'K02', 'K03']:
    section = decoded.split('### ' + key + '｜', 1)[1].split('\n###', 1)[0]
    answer_line = next(line for line in section.splitlines() if line.startswith('**我的确认／备注：'))
    answers[key] = answer_line.split('：', 1)[1].replace('**', '').strip()
assert answers == {'K01': '165室一个图案，就是大厅的一部分', 'K02': '从104', 'K03': '是的联通123'}, answers
data = json.loads((BACKUP / 'annotation.json').read_text())
original = json.loads((BACKUP / 'annotation.json').read_text())
spaces = {s['id']: s for s in data['spaces']}
merged = unary_union([Polygon(spaces['S165']['polygon_px']), Polygon(spaces['S167']['polygon_px'])])
assert merged.geom_type == 'Polygon' and merged.is_valid
spaces['S167']['polygon_px'] = [list(p) for p in list(merged.exterior.coords)[:-1]]
data['spaces'] = [s for s in data['spaces'] if s['id'] != 'S165']
spaces.pop('S165')
spaces['S164']['name'] = '门诊中央大厅西侧通道'
spaces['S166']['name'] = '门诊中央大厅东侧通道'
assert not any('S165' in [r['source'], r['target']] for r in data['relations'])
max_rid = max(int(r['id'][1:]) for r in data['relations'] if r['id'].startswith('R'))
added = []
for source, target in [('S113', 'S104'), ('S121', 'S123')]:
    assert not any(r['type'] == 'access' and {r['source'], r['target']} == {source, target} for r in data['relations'])
    max_rid += 1
    relation = {'id': f'R{max_rid:03d}', 'source': source, 'target': target, 'type': 'access'}
    data['relations'].append(relation)
    added.append(relation)

spec = importlib.util.spec_from_file_location('annotation_tools', SKILL)
annotation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(annotation)
annotation.normalize(data)
(STAGE / 'annotation.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

# Preserve previously reviewed label positions and all P/E markers.
tree = ET.parse(STAGE / '标注.svg')
root = tree.getroot()
ns = {'s': annotation.NS}
plan = root.find('s:g[@id="plan"]', ns)
plan.remove(plan.find('s:g[@id="S165"]', ns))
palette = ['#2563eb', '#0f766e', '#7c3aed', '#15803d', '#b45309', '#0369a1', '#a21caf', '#475569']
for sid in ['S164', 'S166', 'S167']:
    s = spaces[sid]
    group = plan.find('s:g[@id="' + sid + '"]', ns)
    group.set('data-space-name', s['name'])
    group.find('s:title', ns).text = f'{sid} | {s["name"]} | {annotation.TYPE_NAMES[s["type"]]}'
    group.find('s:polygon', ns).set('points', ' '.join(f'{x},{y}' for x, y in s['polygon_px']))
    for child in list(group):
        if child.tag in ['{' + annotation.NS + '}rect', '{' + annotation.NS + '}text']:
            group.remove(child)
    color = palette[int(hashlib.sha256(s['type'].encode()).hexdigest()[:4], 16) % len(palette)]
    x, y, width, height, font, lines = annotation.place_label(Polygon(s['polygon_px']), s)
    group.append(annotation.element('rect', {
        'x': x, 'y': y, 'width': width, 'height': height, 'rx': 2,
        'fill': 'white', 'fill-opacity': '.94', 'stroke': color, 'stroke-width': '.8',
    }))
    for i, line in enumerate(lines):
        group.append(annotation.txt(x + 4, y + font + 2 + i * (font + 2), line, font, color, True))
root_texts = root.findall('s:text', ns)
root_texts[1].text = '187个空间／区域；关键连通已同步；仅S040名称未确认'
tree.write(STAGE / '标注.svg', encoding='unicode')

adjacency = {sid: set() for sid in spaces}
for r in data['relations']:
    if r['type'] == 'access':
        adjacency[r['source']].add(r['target'])
        adjacency[r['target']].add(r['source'])
reachable = {r['target'] for r in data['relations'] if r['type'] == 'entrance'}
queue = list(reachable)
while queue:
    sid = queue.pop()
    for target in adjacency[sid] - reachable:
        reachable.add(target)
        queue.append(target)
unreachable = sorted(set(spaces) - reachable)
assert unreachable == ['S040', 'S137', 'S182'], unreachable
assert len(spaces) == 187 and len(data['relations']) == 235
old_openings = {o['id']: (r['id'], r['source'], r['target'], o) for r in original['relations'] for o in r.get('openings', [])}
new_openings = {o['id']: (r['id'], r['source'], r['target'], o) for r in data['relations'] for o in r.get('openings', [])}
assert old_openings == new_openings and len(new_openings) == 175

text = original_text
text = text.replace('# 12_遂川县人民医院｜门洞定位与连通复核草稿', '# 12_遂川县人民医院｜连通确认已同步（名称仍有1项待定）')
text = text.replace('主要房名及8处区域性质已同步；本轮已对照原图补充门洞定位、修正人员可达关系并测试通行网络。仍有K01—K03三处关键疑点及S040名称未定，尚不宣布整图完成。',
    '主要房名、8处区域性质及K01—K03关键连通确认已同步。S165铺地图案并入S167大厅；新增S113—S104、S121—S123概念连接。仅S040名称仍未定，暂不宣布整图完成。')
start = text.index('**完成状态：**')
end = text.index('\n\n## ', start)
text = text[:start] + '**完成状态：**名称剩24／S040未定；关键连通待确认项为0。175个P红点保持原编号与坐标，新增两条用户确认的概念连接不虚构门位。' + text[end:]
start = text.index('**图连通测试：**')
end = text.index('### K01', start)
text = text[:start] + '''**图连通测试：**仅用access构建无向图，入口分别作为外部接口。187个节点中，184个已有通往入口的记录路径；S040、S137、S182内部小门证据不足，未补关系，不作为不连通负例。

**核验结果：**关键连通确认均已落实；正式校验结构有效，names_complete=false、退出码2，仅因S040名称未定。175个开口与SVG红点对应不变。完整用户填写及同步前四文件已备份。

''' + text[end:]
results = {
    'K01': '已同步：S165为大厅铺地图案，轮廓无损并入S167门诊大厅北段；S165编号停用，不再视作交通核。S164/S166保留编号，名称中的“中央核”改为“中央大厅”。',
    'K02': f'已同步：新增{added[0]["id"]}，S113护士站与S104通道人员可达；按用户确认记录概念连接，门位不清，不新增P点。',
    'K03': f'已同步：新增{added[1]["id"]}，S121与S123人员可达；保留E06西侧外部入口，门位不清，不新增P点。',
}
for key in ['K01', 'K02', 'K03']:
    start = text.index('### ' + key + '｜')
    next_heading = text.find('\n### ', start + 1)
    end = next_heading if next_heading != -1 else text.index('**本轮不细究', start)
    section = text[start:end]
    marker = '[查看同范围无标记原图]'
    assert marker in section
    section = section.replace(marker, '**同步结果：**' + results[key] + '\n\n' + marker, 1)
    text = text[:start] + section + text[end:]
text = text.replace('对应161条人员可达关系。其余55条', '对应161条人员可达关系。其余57条')
text = re.sub(r'\*\*标注规模：\*\*[^\n]+', '**标注规模：**187个空间／区域，房间级单元110个、开放空间45个、交通核14个、功能块18个。', text, count=1)
text = text.replace('交通核 15 个', '交通核 14 个')
text = re.sub(r'\*\*连接关系：\*\*[^\n]+', '**连接关系：**235条，人员可达218条、服务联系2条、入口连接15条。', text, count=1)
text = text.replace('S192→S191。其他S编号不重排。', 'S192→S191；S165→S167。其他S编号不重排。')
text = text.replace('主要空间连通性及清晰门洞定位尚待下一阶段复核。', '主要空间连通确认及清晰门洞定位已同步；名称S040仍待明确。')
archive = '../../临时核对/' + WORK.parent.name + '/' + WORK.name + '/修改前备份/标注说明.md'
text = text.replace('## 本轮门洞与连通复核', f'[本轮完整填写与同步前备份]({archive})\n\n## 本轮门洞与连通复核', 1)
(STAGE / '标注说明.md').write_text(text)
# All 130 fixed name-review rows and raw K answers remain intact.
table_header = '## 房间名称与区域性质固定核对表'
def rows(source):
    return [line for line in source.split(table_header, 1)[1].splitlines() if re.match(r'^\|\s*\d+\s*\|\s*S\d+', line)]
assert rows(text) == rows(original_text) and len(rows(text)) == 130
for target in re.findall(r'\]\(([^)]+)\)', text):
    assert (PROJECT / target).is_file(), target
result = subprocess.run([sys.executable, str(SKILL), 'validate', str(STAGE / 'annotation.json'), '--check-dir'], capture_output=True, text=True)
report = json.loads(result.stdout)
assert result.returncode == 2 and report['valid'] and report['pending_name_ids'] == ['S040'], result.stdout
body = markdown.markdown(text, extensions=['tables'])
preview = '<!doctype html><meta charset="utf-8"><base href="' + html.escape(PROJECT.as_uri() + '/') + '"><style>body{max-width:1000px;margin:28px auto;font:17px/1.65 -apple-system,sans-serif;color:#182b3a}img{max-width:100%}table{border-collapse:collapse;font-size:14px}td,th{border:1px solid #ddd;padding:7px}a{color:#086b9b}</style>' + body
(WORK / 'MD预览.html').write_text(preview)
audit = {'work': str(WORK), 'validation': report, 'answers': answers, 'merged': {'S165': 'S167'}, 'added_access': added, 'openings_preserved': len(new_openings), 'reachable': len(reachable), 'unreachable': unreachable, 'name_rows_preserved': 130}
(WORK / '同步核验.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(audit, ensure_ascii=False, indent=2))
