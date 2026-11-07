"""Synchronize the user's explicit room, merge, deletion and circulation decisions."""
from pathlib import Path
from collections import Counter
import copy
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import markdown
from PIL import Image
from shapely.geometry import Polygon
from shapely.ops import unary_union

ROOT = Path.cwd()
BASE = ROOT / 'p-平面标注与数据处理'
PROJECT = BASE / '标注试样/12_遂川县人民医院'
OUT = Path(__file__).resolve().parent
STAGE = OUT / '待核验成果'
BACKUP = OUT / '修改前备份'
sys.path.insert(0, str(BASE / '临时核对/09-10_连通复核_20261102'))
from 连通工具 import annotation, fit_labels

CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
NAMES = {
    'S008': ('农医保', 'office'),
    'S016': ('消控室', 'building_control'),
    'S036': ('验收区', 'service_work_area'),
    'S052': ('办公室', 'office'),
    'S055': ('临床药学室', 'pharmacy'),
    'S061': ('打片室', 'imaging'),
    'S105': ('重症监察室', 'observation'),
    'S106': ('重症监察室', 'observation'),
    'S145': ('灌肠', 'treatment'),
    'S182': ('收费储藏', 'storage'),
    'S190': ('休憩', 'staff_support'),
    'S191': ('更衣休息', 'staff_support'),
    'S193': ('药物入口的前室', 'vestibule'),
}
MERGES = {
    'S031': 'S032', 'S086': 'S118', 'S090': 'S085', 'S119': 'S118',
    'S130': 'S140', 'S173': 'S174', 'S176': 'S175', 'S192': 'S191',
}
DELETED = {'S043'}
GRID = {'S031', 'S065', 'S086', 'S090', 'S119', 'S130', 'S173', 'S176'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def formal(path, output):
    p = subprocess.run([sys.executable, str(annotation.__file__), 'validate',
                        str(path), '--check-dir'], capture_output=True, text=True)
    output.write_text(p.stdout + '\n' + p.stderr)
    result = json.loads(p.stdout)
    assert p.returncode == 2 and result['valid'] and not result['errors'], result
    assert result['pending_name_ids'] == ['S040'], result
    return result


def rebase(text, source, target):
    return re.sub(r'\]\(([^)]+)\)',
                  lambda m: '](' + os.path.relpath((source / m[1]).resolve(), target) + ')', text)


def update_data(before):
    data = copy.deepcopy(before)
    spaces = {s['id']: s for s in data['spaces']}
    for sid, (name, kind) in NAMES.items():
        spaces[sid].update(name=name, type=kind)
    spaces['S065'].update(name='中段北东侧通道', type='corridor', level='open_space')
    spaces['S085'].update(name='中段南北联络通道及大厅', type='hall', level='open_space')
    spaces['S118']['name'] = '中段南公共通道及东侧通道'
    targets = {}
    for source, target in MERGES.items():
        targets.setdefault(target, [target]).append(source)
    for target, ids in targets.items():
        poly = unary_union([Polygon(spaces[sid]['polygon_px']) for sid in ids])
        assert poly.geom_type == 'Polygon' and poly.is_valid and not poly.interiors, ids
        spaces[target]['polygon_px'] = [list(p) for p in poly.exterior.coords[:-1]]
    data['spaces'] = [s for s in data['spaces'] if s['id'] not in MERGES and s['id'] not in DELETED]
    dropped_relations, duplicate_relations = [], []
    relations, seen = [], {}
    for r in data['relations']:
        if r['source'] in DELETED or r['target'] in DELETED:
            dropped_relations.append(r)
            continue
        r['source'] = MERGES.get(r['source'], r['source'])
        r['target'] = MERGES.get(r['target'], r['target'])
        if r['source'] == r['target']:
            dropped_relations.append(r)
            continue
        key = (r['id'],) if r['type'] == 'entrance' else (r['type'], *sorted([r['source'], r['target']]))
        if key in seen:
            assert not r.get('openings'), 'No opening may be discarded by deduplication'
            duplicate_relations.append({'removed': r, 'kept': seen[key]})
            continue
        seen[key] = r['id']
        relations.append(r)
    data['relations'] = relations
    annotation.normalize(data)
    old_union = unary_union([Polygon(s['polygon_px']) for s in before['spaces'] if s['id'] not in DELETED])
    new_union = unary_union([Polygon(s['polygon_px']) for s in data['spaces']])
    assert old_union.symmetric_difference(new_union).area < 1e-6
    assert len(data['spaces']) == 188 and len(data['relations']) == 191
    assert [s['id'] for s in annotation.unresolved(data)] == ['S040']
    assert not any(r.get('openings') for r in data['relations'])
    assert [r for r in before['relations'] if r['type'] == 'entrance'] == [
        r for r in data['relations'] if r['type'] == 'entrance']
    return data, dropped_relations, duplicate_relations


def update_md(original, before, data):
    mapped = json.loads((BASE / '临时核对/12_遂川县人民医院_名称核对_20261101/核对号映射.json').read_text())
    mapping = {r['number']: r['sid'] for r in mapped}
    spaces = {s['id']: s for s in data['spaces']}
    old_pending = {s['id'] for s in annotation.unresolved(before)}
    rows_seen, table_lines, decisions = [], [], {}
    table = original[original.index('## 房间名称与区域性质固定核对表'):]
    for line in table.splitlines():
        cells = [c.strip() for c in line.split('|')[1:-1]]
        if len(cells) == 7 and cells[0].isdigit():
            number, sid = cells[:2]
            assert mapping[number] == sid and cells[-1] == number
            rows_seen.append(number)
            if sid in old_pending:
                if sid in DELETED:
                    name, state = '已删除（不纳入本轮标注）', '用户要求删除；已移出JSON和SVG，原图未改'
                elif sid in MERGES:
                    target = MERGES[sid]
                    name = spaces[target]['name']
                    state = f'已并入{target}；原{sid}退役，核对号保留追溯'
                elif sid == 'S065':
                    name, state = spaces[sid]['name'], '已确认室内通道；保留分段，计室内面积'
                elif sid == 'S040':
                    name, state = cells[2], '名称仍未确认；交通核旁辅助功能块，本轮暂不细究，不追加填写问题'
                else:
                    name, state = spaces[sid]['name'], '用户填写已同步'
                evidence = ('用户明确说明8处为医院走道／大厅，网格仅为铺地图案；计室内面积。'
                            if sid in GRID else '依据文档A—E中的用户明确填写及本轮同步授权。')
                if sid == 'S040':
                    evidence = cells[4]
                cells[2:6] = [name, '—', evidence, state]
                decisions[number] = {'sid': sid, 'name': name, 'result': state}
            line = '| ' + ' | '.join(cells) + ' |'
        table_lines.append(line)
    assert rows_seen == [r['number'] for r in mapped]
    table = '\n'.join(table_lines) + '\n'
    table = re.sub(r'^\*\*固定保留原130项及编号；[^\n]+',
                   '**固定保留原130项及编号。** 106项照片识别结果及本轮23项改名、属性、合并或删除处理均已落实；仅24／S040辅助功能块名称仍未定。本表含已退役编号，仅供追溯，现行边界以SVG为准。', table, flags=re.M)
    table = table.replace('尚待确认行的候选不写入核心数据。', '用户本轮填写已同步；仅未回答的24／S040继续保持unknown。')
    for group in {r['group'] for r in mapped}:
        pending = 1 if group == '东北翼部' else 0
        table = re.sub(r'(\|\s*' + re.escape(group) + r'\s*\|[^|]+\|)\s*\d+\s*(\|)',
                       lambda m: m[1] + ' ' + str(pending) + ' ' + m[2], table)
    table = re.sub(r'### 区域性质与面积口径另核[\s\S]*$',
                   '### 区域性质与当前完成边界\n\n8处纹理区域均已按用户确认纳入室内走道／大厅；7处并入既有通道，S065保留为通道分段。北侧若整体合并将形成带孔轮廓，现有单环多边形格式无法表达，因此保留分段。\n\n本轮明确确认项已同步；24／S040仍为unknown，不冒称名称全部完成。主要空间连通性及清晰门洞定位尚待下一阶段复核。\n', table)
    annotation.summary(data, OUT / '生成概览.md')
    overview = (OUT / '生成概览.md').read_text()
    overview = overview.replace('# 平面标注概览', '# 12_遂川县人民医院｜确认同步后的标注草稿', 1)
    overview = re.sub(r'^未完成：[^\n]+',
                      '本轮填写已同步：主要房名及8处区域性质已落实；仍有1个辅助功能块名称未定。连通性尚待专项复核。', overview, flags=re.M)
    archive = '../../临时核对/' + OUT.name + '/用户填写原件_可预览.md'
    summary = [
        '**范围：**原图一层北侧两翼、入院大厅、中段及南侧门诊区；25／S043按用户要求退出本轮标注，不补作其他用途。室外台阶、坡道及尺寸线不纳入室内标注。', '',
        '**完成状态：**这是名称及结构调整同步；不是连通性完成声明。仅24／S040辅助功能块名称未定，本轮不追加问题。', '',
        '## 本轮填写已落实', '',
        f'[查看完整用户填写原件及局部图]({archive})', '',
        '| 用户原始填写 | 已落实 |', '| --- | --- |',
        '| 农医保/消控室 | 06／S008=农医保；13／S016=消控室 |',
        '| 验收区、办公室、临床药学室、25 就不管了直接删掉 | 22／S036=验收区；32／S052=办公室；35／S055=临床药学室；25／S043删除 |',
        '| 是的，打片室 | 38／S061=打片室 |',
        '| 70 重症监察室 、 71 重症监察室 | S105、S106均按原填写记为重症监察室 |',
        '| 98 灌肠 100 抽血 | 98／S145=灌肠；100／S147抽血沿用 |',
        '| 122+123 合并的，叫做更衣休息 ； 120 是收费储藏 | 122+123合并，保留S191=更衣休息，S192退役；120／S182=收费储藏 |',
        '| 129就是休憩 、 130 药物入口的前室 | S190=休憩；S193=药物入口的前室 |',
        '| 18、42、58、60、81、88、118、125 这些东西其实就是医院里面的走道/大厅 只是他把平面的纹理画出来了，直接忽略， | 忽略纹理边界的房间含义，8处均计入室内交通空间；保留面积 |', '',
        '**合并映射：**S031→S032；S086、S119→S118；S090→S085；S130→S140；S173→S174；S176→S175；S192→S191。其他S编号不重排。S065改为中段北东侧通道，保留分段。', '',
        '**关系处理：**仅清理删除／合并涉及的关系及重复项；R179与R178合并后对应同一空间对，保留R178。没有新增关系或门洞定位，不代表其他空间不连通。', '',
        '**面积处理：**7处纹理区域与更衣休息合并保留完整面积；S065按室内通道计入。S043退出范围后，全部现行室内相对面积重新归一化。', '',
        '**核对图说明：**下方图片保留原核对号及历史框线，供追溯；当前空间名称和合并后的范围以具名SVG为准。', '',
    ]
    overview = overview.replace('**标注规模：**', '\n'.join(summary) + '\n**标注规模：**', 1)
    return overview + '\n' + table, decisions


def prepare():
    STAGE.mkdir(exist_ok=True)
    BACKUP.mkdir(exist_ok=True)
    hashes = {p.name: digest(p) for p in PROJECT.iterdir() if p.is_file()}
    for p in PROJECT.iterdir():
        if not p.is_file():
            continue
        if (BACKUP / p.name).exists():
            assert digest(p) == digest(BACKUP / p.name), 'Source changed after snapshot'
        else:
            shutil.copy2(p, BACKUP / p.name)
    raw = (PROJECT / '标注说明.md').read_text()
    original = html.unescape(raw)
    for phrase in ['农医保/消控室', '25 就不管了直接删掉', '122+123 合并的', '70 重症监察室',
                   '98 灌肠', '120 是收费储藏', '129就是休憩', '这些东西其实就是医院里面的走道/大厅']:
        assert phrase in original, phrase
    (OUT / '用户填写原件_可预览.md').write_text(rebase(original, PROJECT, OUT))
    before = json.loads((PROJECT / 'annotation.json').read_text())
    data, dropped, duplicates = update_data(before)
    for p in PROJECT.iterdir():
        if p.is_file():
            shutil.copy2(p, STAGE / p.name)
    (STAGE / 'annotation.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    annotation.render(data, STAGE / 'annotation.json', STAGE / '标注.svg')
    fit_labels(STAGE / '标注.svg', data)
    md, decisions = update_md(original, before, data)
    (STAGE / '标注说明.md').write_text(md)
    for link in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', md):
        assert (PROJECT / link).exists(), link
    result = formal(STAGE / 'annotation.json', OUT / '正式校验_同步前.json')
    svg = ET.parse(STAGE / '标注.svg').getroot()
    ns = '{http://www.w3.org/2000/svg}'
    for s in data['spaces']:
        g = svg.find(f'.//{ns}g[@id="{s["id"]}"]')
        visible = ''.join(t.text or '' for t in g.iter(ns + 'text'))
        assert s['id'] in visible and s['name'] in visible, s['id']
    screenshot = OUT / 'SVG实际渲染.png'
    subprocess.run([CHROME, '--headless', '--disable-gpu', '--hide-scrollbars',
                    '--user-data-dir=/tmp/plan12-sync-qa',
                    f'--window-size={svg.get("width")},{int(float(svg.get("height")))+1}',
                    '--screenshot=' + str(screenshot), (STAGE / '标注.svg').as_uri()],
                   check=True, capture_output=True)
    full = Image.open(screenshot)
    preview = full.copy()
    preview.thumbnail((1100, 1500))
    preview.save(OUT / 'SVG全图预览.jpg', quality=95)
    head = max(65, min(125, data['image']['width'] * .05))
    for name, bounds in [('北部', (350, 550, 2315, 1020)),
                         ('中段', (300, 1010, 990, 2145)),
                         ('门诊', (140, 2130, 1600, 2740))]:
        x1, y1, x2, y2 = bounds
        full.crop((x1, int(y1+head), x2, int(y2+head))).save(OUT / (name + '_标签目检.png'))
    rendered = markdown.markdown(md, extensions=['tables'])
    rendered = re.sub(r'(src|href)="([^"#][^"]*)"',
                      lambda m: m[1] + '="' + html.escape((PROJECT / html.unescape(m[2])).resolve().as_uri()) + '"', rendered)
    (OUT / 'MD预览.html').write_text('<meta charset="utf-8"><style>body{font-family:Arial,sans-serif;max-width:1500px;margin:24px}img{max-width:100%;max-height:600px}table{border-collapse:collapse}td,th{border:1px solid #aaa;padding:6px}</style>' + rendered)
    subprocess.run([CHROME, '--headless', '--disable-gpu', '--hide-scrollbars',
                    '--user-data-dir=/tmp/plan12-sync-md-qa', '--window-size=1700,2400',
                    '--screenshot=' + str(OUT / 'MD预览首屏.png'), (OUT / 'MD预览.html').as_uri()],
                   check=True, capture_output=True)
    report = {'hashes': hashes, 'spaces': len(data['spaces']), 'relations': len(data['relations']),
              'pending_name_ids': result['pending_name_ids'], 'merges': MERGES, 'deleted': sorted(DELETED),
              'removed_relations': dropped, 'duplicate_relations': duplicates,
              'decisions': decisions, 'source_image_unchanged': True,
              'geometry_coverage_preserved_except_explicit_deleted_space': True,
              'indoor_area_ratio_sum': sum(s.get('area_ratio', 0) for s in data['spaces'])}
    (OUT / '同步检查_待发布.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ['hashes', 'decisions']}, ensure_ascii=False))


def publish():
    report = json.loads((OUT / '同步检查_待发布.json').read_text())
    for name, expected in report['hashes'].items():
        assert digest(PROJECT / name) == expected, name
    for name in ['annotation.json', '标注.svg', '标注说明.md']:
        temp = PROJECT / ('.' + name + '.同步中')
        shutil.copy2(STAGE / name, temp)
        os.replace(temp, PROJECT / name)
    result = formal(PROJECT / 'annotation.json', OUT / '正式校验_同步后.json')
    image_name = json.loads((PROJECT / 'annotation.json').read_text())['image']['file']
    assert digest(PROJECT / image_name) == report['hashes'][image_name]
    assert len(list(PROJECT.iterdir())) == 4
    report.update(published=True, valid=result['valid'], names_complete=result['names_complete'],
                  visual_review='Chrome full plan, three dense detail crops and MD preview inspected')
    (OUT / '交付检查.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['spaces', 'relations', 'pending_name_ids', 'published', 'valid', 'names_complete']}, ensure_ascii=False))


if __name__ == '__main__':
    publish() if '--publish' in sys.argv else prepare()
